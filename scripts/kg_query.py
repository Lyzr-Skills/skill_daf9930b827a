#!/usr/bin/env python3
"""
Neo4j Knowledge Graph Extractor — Main Query Script
Supports multiple extraction modes for dynamic AI analysis.

Credentials are loaded from environment variables (never hardcoded).
Set these before running:

  export NEO4J_URI="neo4j+s://<your-host>.databases.neo4j.io"
  export NEO4J_USER="<your-username>"
  export NEO4J_PASSWORD="<your-password>"
  export NEO4J_DATABASE="<your-database>"

Or place them in a .env file and load with: source .env
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from neo4j import GraphDatabase

# ── Credentials from environment variables ONLY ────────────────────────────────
NEO4J_URI      = os.environ.get("NEO4J_URI")
NEO4J_USER     = os.environ.get("NEO4J_USER")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")  # default db name


def _check_credentials(uri, user, password):
    """Validate that credentials are present before attempting connection."""
    missing = []
    if not uri:      missing.append("NEO4J_URI")
    if not user:     missing.append("NEO4J_USER")
    if not password: missing.append("NEO4J_PASSWORD")
    if missing:
        print(
            f"ERROR: Missing required environment variables: {', '.join(missing)}\n"
            "Please set them before running:\n"
            "  export NEO4J_URI='neo4j+s://...'\n"
            "  export NEO4J_USER='<user>'\n"
            "  export NEO4J_PASSWORD='<password>'\n"
            "  export NEO4J_DATABASE='<database>'  # optional, defaults to 'neo4j'",
            file=sys.stderr
        )
        sys.exit(1)


def safe_serialize(obj):
    """Handle Neo4j and Python types that aren't JSON-serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, '__class__') and obj.__class__.__name__ in ('Node', 'Relationship', 'Path'):
        return str(obj)
    return str(obj)


def node_to_dict(node):
    """Convert a Neo4j Node to a plain dict with labels and properties."""
    return {
        "_labels": list(node.labels),
        "_element_id": node.element_id,
        **dict(node.items())
    }


def rel_to_dict(rel):
    """Convert a Neo4j Relationship to a plain dict."""
    return {
        "_type": rel.type,
        "_element_id": rel.element_id,
        "_start_node_id": rel.start_node.element_id if rel.start_node else None,
        "_end_node_id": rel.end_node.element_id if rel.end_node else None,
        **dict(rel.items())
    }


def record_to_dict(record):
    """Recursively convert a Neo4j record to plain Python."""
    result = {}
    for key in record.keys():
        val = record[key]
        if hasattr(val, 'labels'):          # Node
            result[key] = node_to_dict(val)
        elif hasattr(val, 'type') and hasattr(val, 'start_node'):  # Relationship
            result[key] = rel_to_dict(val)
        elif isinstance(val, list):
            result[key] = [
                node_to_dict(v) if hasattr(v, 'labels') else
                rel_to_dict(v) if (hasattr(v, 'type') and hasattr(v, 'start_node')) else v
                for v in val
            ]
        else:
            result[key] = val
    return result


class KGExtractor:
    def __init__(self, uri=None, user=None, password=None, database=None):
        # Prefer explicitly passed args, then fall back to env vars
        uri      = uri      or NEO4J_URI
        user     = user     or NEO4J_USER
        password = password or NEO4J_PASSWORD
        database = database or NEO4J_DATABASE

        _check_credentials(uri, user, password)

        self.driver   = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self):
        self.driver.close()

    def run(self, cypher, params=None):
        with self.driver.session(database=self.database) as session:
            result = session.run(cypher, params or {})
            return [record_to_dict(r) for r in result]

    # ── SCHEMA ──────────────────────────────────────────────────────────────────
    def get_schema(self):
        labels_raw    = self.run("CALL db.labels() YIELD label RETURN label")
        rel_types_raw = self.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        prop_keys_raw = self.run("CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey")

        labels    = [r["label"]            for r in labels_raw]
        rel_types = [r["relationshipType"] for r in rel_types_raw]
        prop_keys = [r["propertyKey"]      for r in prop_keys_raw]

        counts = {}
        for label in labels:
            c = self.run(f"MATCH (n:`{label}`) RETURN count(n) AS total")
            counts[label] = c[0]["total"] if c else 0

        rel_counts = {}
        for rt in rel_types:
            c = self.run(f"MATCH ()-[r:`{rt}`]->() RETURN count(r) AS total")
            rel_counts[rt] = c[0]["total"] if c else 0

        total_nodes = self.run("MATCH (n) RETURN count(n) AS total")[0]["total"]
        total_rels  = self.run("MATCH ()-[r]->() RETURN count(r) AS total")[0]["total"]

        return {
            "mode": "schema",
            "summary": {
                "total_nodes":              total_nodes,
                "total_relationships":      total_rels,
                "label_count":              len(labels),
                "relationship_type_count":  len(rel_types),
                "property_key_count":       len(prop_keys)
            },
            "node_labels":        [{"label": l, "count": counts.get(l, 0)} for l in labels],
            "relationship_types": [{"type": rt, "count": rel_counts.get(rt, 0)} for rt in rel_types],
            "property_keys":      prop_keys
        }

    # ── NODES ───────────────────────────────────────────────────────────────────
    def get_nodes(self, label=None, limit=50, filters=None):
        if label:
            cypher = f"MATCH (n:`{label}`) RETURN n LIMIT {limit}"
        else:
            cypher = f"MATCH (n) RETURN n, labels(n) AS lbls LIMIT {limit}"
        rows = self.run(cypher)
        return {"mode": "nodes", "label": label, "count": len(rows), "nodes": rows}

    # ── RELATIONSHIPS ────────────────────────────────────────────────────────────
    def get_relationships(self, rel_type=None, from_label=None, to_label=None, limit=50):
        src = f"(a:`{from_label}`)" if from_label else "(a)"
        tgt = f"(b:`{to_label}`)"   if to_label   else "(b)"
        rel = f"[r:`{rel_type}`]"   if rel_type   else "[r]"
        cypher = f"""
            MATCH {src}-{rel}->{tgt}
            RETURN labels(a)[0] AS from_label,
                   a.name AS from_name,
                   type(r) AS relationship,
                   labels(b)[0] AS to_label,
                   b.name AS to_name,
                   properties(r) AS rel_props
            LIMIT {limit}
        """
        rows = self.run(cypher)
        return {"mode": "relationships", "count": len(rows), "relationships": rows}

    # ── CYPHER ───────────────────────────────────────────────────────────────────
    def run_cypher(self, cypher, params=None, limit=None):
        if limit and "LIMIT" not in cypher.upper():
            cypher = cypher.rstrip(";") + f" LIMIT {limit}"
        rows = self.run(cypher, params)
        return {"mode": "cypher", "query": cypher, "count": len(rows), "results": rows}

    # ── PATHS ────────────────────────────────────────────────────────────────────
    def get_paths(self, from_name, to_name, max_depth=6):
        cypher = f"""
            MATCH (a), (b)
            WHERE (a.name = $from_name OR a.id = $from_name)
              AND (b.name = $to_name OR b.id = $to_name)
            MATCH path = shortestPath((a)-[*..{max_depth}]-(b))
            UNWIND nodes(path) AS n
            WITH collect(distinct {{id: n.element_id, labels: labels(n), name: n.name}}) AS ns,
                 [r IN relationships(path) | type(r)] AS rel_types
            RETURN ns AS path_nodes, rel_types
            LIMIT 5
        """
        rows = self.run(cypher, {"from_name": from_name, "to_name": to_name})
        return {"mode": "paths", "from": from_name, "to": to_name, "paths": rows}

    # ── AGGREGATION ──────────────────────────────────────────────────────────────
    def get_aggregations(self, label=None, group_by=None):
        if label and group_by:
            cypher = f"""
                MATCH (n:`{label}`)
                RETURN n.{group_by} AS group_value, count(n) AS total
                ORDER BY total DESC
            """
        elif label:
            cypher = f"MATCH (n:`{label}`) RETURN count(n) AS total"
        else:
            cypher = """
                MATCH (n)
                RETURN labels(n)[0] AS label, count(n) AS total
                ORDER BY total DESC
            """
        rows = self.run(cypher)
        return {"mode": "aggregation", "results": rows}

    # ── NEIGHBORHOOD ─────────────────────────────────────────────────────────────
    def get_neighborhood(self, node_id_or_name, depth=1, limit=100):
        cypher = f"""
            MATCH (center)
            WHERE center.name = $id OR center.id = $id OR toString(id(center)) = $id
            OPTIONAL MATCH (center)-[r*1..{depth}]-(neighbor)
            RETURN center,
                   collect(distinct {{
                       rel_type: [rel IN r | type(rel)],
                       neighbor_labels: labels(neighbor),
                       neighbor_name: neighbor.name,
                       neighbor_id: neighbor.id,
                       neighbor_props: properties(neighbor)
                   }}) AS neighbors
            LIMIT {limit}
        """
        rows = self.run(cypher, {"id": str(node_id_or_name)})
        return {"mode": "neighborhood", "center": node_id_or_name, "results": rows}

    # ── FULL EXPORT ──────────────────────────────────────────────────────────────
    def full_export(self, limit_per_page=500, page=0):
        skip = page * limit_per_page
        node_rows = self.run(f"MATCH (n) RETURN n SKIP {skip} LIMIT {limit_per_page}")
        rel_rows  = self.run(f"""
            MATCH (a)-[r]->(b)
            RETURN labels(a)[0] AS from_label, a.name AS from_name,
                   type(r) AS relationship, properties(r) AS rel_props,
                   labels(b)[0] AS to_label, b.name AS to_name
            SKIP {skip} LIMIT {limit_per_page}
        """)
        return {
            "mode":       "full_export",
            "page":       page,
            "nodes":      node_rows,
            "relationships": rel_rows,
            "node_count": len(node_rows),
            "rel_count":  len(rel_rows)
        }

    # ── AI ANALYSIS ──────────────────────────────────────────────────────────────
    def ai_analysis_data(self):
        """Collect a comprehensive analysis bundle for AI interpretation."""
        schema = self.get_schema()

        top_connected = self.run("""
            MATCH (n)
            OPTIONAL MATCH (n)-[r]-()
            RETURN labels(n)[0] AS label, n.name AS name, count(r) AS degree
            ORDER BY degree DESC LIMIT 20
        """)

        isolated = self.run("""
            MATCH (n) WHERE NOT (n)--()
            RETURN labels(n)[0] AS label, n.name AS name
            LIMIT 20
        """)

        rel_dist = self.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS rel_type, count(r) AS total
            ORDER BY total DESC
        """)

        no_name = self.run("""
            MATCH (n) WHERE n.name IS NULL
            RETURN labels(n)[0] AS label, count(n) AS count
            ORDER BY count DESC
        """)

        recent = self.run("""
            MATCH (n) WHERE n.created_at IS NOT NULL
            RETURN labels(n)[0] AS label, n.name AS name, n.created_at AS created_at
            ORDER BY n.created_at DESC LIMIT 10
        """)

        findings = self.run("""
            MATCH (f:Finding)
            RETURN f.severity AS severity, f.finding_type AS type,
                   f.closure_state AS closure_state, count(f) AS total
            ORDER BY total DESC
        """)

        control_states = self.run("""
            MATCH (c:Control)-[:HAS_STATE]->(cs:ControlState)
            RETURN cs.state AS state, count(c) AS total
            ORDER BY total DESC
        """)

        ai_agents = self.run("""
            MATCH (a:AIAgent)
            RETURN a.name, a.risk_tier, a.oversight_tier, a.status,
                   a.kill_switch_enabled, a.eu_ai_act_tier
            ORDER BY a.risk_tier
        """)

        vendors = self.run("""
            MATCH (v:Vendor)
            RETURN v.name, v.tier, v.is_critical_or_important, v.status
            ORDER BY v.tier
        """)

        return {
            "mode":                     "ai_analysis",
            "schema":                   schema,
            "top_connected_nodes":      top_connected,
            "isolated_nodes":           isolated,
            "relationship_distribution": rel_dist,
            "nodes_missing_name":       no_name,
            "recent_activity":          recent,
            "findings_summary":         findings,
            "control_states_summary":   control_states,
            "ai_agents":                ai_agents,
            "vendors":                  vendors
        }


def main():
    parser = argparse.ArgumentParser(description="Neo4j Knowledge Graph Extractor")
    parser.add_argument("--mode", default="schema",
                        choices=["schema", "nodes", "relationships", "cypher",
                                 "paths", "aggregation", "neighborhood",
                                 "full_export", "ai_analysis"],
                        help="Extraction mode")
    parser.add_argument("--label",    help="Node label to filter")
    parser.add_argument("--rel",      help="Relationship type to filter")
    parser.add_argument("--cypher",   help="Custom Cypher query to run")
    parser.add_argument("--node-id",  help="Node name or ID for neighborhood/path")
    parser.add_argument("--to-node",  help="Target node name for path finding")
    parser.add_argument("--group-by", help="Property to group by in aggregation")
    parser.add_argument("--limit",    type=int, default=50,  help="Max results")
    parser.add_argument("--depth",    type=int, default=1,   help="Depth for neighborhood/path")
    parser.add_argument("--page",     type=int, default=0,   help="Page for full_export")
    parser.add_argument("--output",   help="Save JSON output to file path")

    # Connection args — fall back to environment variables if not supplied
    parser.add_argument("--uri",      default=None, help="Neo4j URI (or set NEO4J_URI env var)")
    parser.add_argument("--user",     default=None, help="Neo4j username (or set NEO4J_USER env var)")
    parser.add_argument("--password", default=None, help="Neo4j password (or set NEO4J_PASSWORD env var)")
    parser.add_argument("--database", default=None, help="Neo4j database (or set NEO4J_DATABASE env var)")

    args = parser.parse_args()

    extractor = KGExtractor(args.uri, args.user, args.password, args.database)

    try:
        if args.mode == "schema":
            result = extractor.get_schema()

        elif args.mode == "nodes":
            result = extractor.get_nodes(label=args.label, limit=args.limit)

        elif args.mode == "relationships":
            result = extractor.get_relationships(rel_type=args.rel, limit=args.limit)

        elif args.mode == "cypher":
            if not args.cypher:
                print("Error: --cypher is required for mode=cypher", file=sys.stderr)
                sys.exit(1)
            result = extractor.run_cypher(args.cypher, limit=args.limit)

        elif args.mode == "paths":
            if not args.node_id or not args.to_node:
                print("Error: --node-id and --to-node required for paths mode", file=sys.stderr)
                sys.exit(1)
            result = extractor.get_paths(args.node_id, args.to_node, args.depth)

        elif args.mode == "aggregation":
            result = extractor.get_aggregations(label=args.label, group_by=args.group_by)

        elif args.mode == "neighborhood":
            if not args.node_id:
                print("Error: --node-id required for neighborhood mode", file=sys.stderr)
                sys.exit(1)
            result = extractor.get_neighborhood(args.node_id, args.depth, args.limit)

        elif args.mode == "full_export":
            result = extractor.full_export(page=args.page)

        elif args.mode == "ai_analysis":
            result = extractor.ai_analysis_data()

        else:
            result = {"error": f"Unknown mode: {args.mode}"}

    finally:
        extractor.close()

    output_json = json.dumps(result, indent=2, default=safe_serialize)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json)
        print(f"Results saved to {args.output}")
        if "count" in result:
            print(f"Records returned: {result['count']}")
        elif "summary" in result:
            print(json.dumps(result["summary"], indent=2))
    else:
        print(output_json)


if __name__ == "__main__":
    main()
