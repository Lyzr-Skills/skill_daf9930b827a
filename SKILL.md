---
name: neo4j-kg-extractor
description: >
  Dynamically extracts, queries, and analyzes data from a Neo4j Knowledge Graph for AI-powered analysis.
  Use this skill whenever the user wants to: explore graph structure, fetch nodes or relationships,
  run Cypher queries, investigate compliance/vendor/AI governance data, find paths between entities,
  get schema summaries, count nodes or relationships, filter by properties, run aggregations,
  investigate findings/controls/obligations/AI agents/vendors, or do any kind of knowledge graph
  data retrieval and analysis. Always use this skill when Neo4j, knowledge graph, Cypher, graph
  database, or graph query is mentioned, even implicitly (e.g. "show me all vendors", "what AI models
  are registered", "which controls are failing", "tell me about obligations").
compatibility:
  tools:
    - e2b_bash
    - e2b_file_write
    - e2b_file_read
    - create_artifact
  python_packages:
    - neo4j
---

# Neo4j Knowledge Graph Extractor

A dynamic skill for connecting to a Neo4j knowledge graph, exploring its schema, extracting data,
running Cypher queries, and preparing results for AI analysis.

## Connection Configuration

Credentials are **NEVER hardcoded**. Always load from environment variables:

```bash
export NEO4J_URI="neo4j+s://<your-host>.databases.neo4j.io"
export NEO4J_USER="<your-username>"
export NEO4J_PASSWORD="<your-password>"
export NEO4J_DATABASE="<your-database>"   # optional — defaults to "neo4j"
```

When running inside e2b_bash, inject them inline:

```bash
NEO4J_URI="neo4j+s://..." \
NEO4J_USER="..." \
NEO4J_PASSWORD="..." \
NEO4J_DATABASE="..." \
python3 /home/user/neo4j-kg-extractor/scripts/kg_query.py --mode schema
```

> ⚠️ Never write credential values into any file, artifact, script, or log output.
> Always pass them as environment variables at runtime.

---

## Workflow

When the user asks anything about the knowledge graph, follow this process:

### Step 1 — Understand Intent

Parse what the user wants into one of these extraction modes:

| Mode | Trigger phrases |
|------|----------------|
| **SCHEMA** | "what's in the graph", "describe the graph", "show me labels", "graph overview" |
| **NODES** | "fetch nodes", "show me all X", "list all Y", "get nodes of type Z" |
| **RELATIONSHIPS** | "show relationships", "how are X and Y connected", "relationship types" |
| **CYPHER** | "run this query", "execute", "I want to find...", custom query |
| **PATHS** | "path between X and Y", "how is X connected to Z" |
| **AGGREGATION** | "count", "how many", "average", "summary statistics" |
| **NEIGHBORHOOD** | "tell me everything about node X", "neighbors of X", "expand X" |
| **FULL EXPORT** | "export the graph", "dump all data", "extract everything" |
| **AI ANALYSIS** | "analyze the graph", "find patterns", "insights", "what's notable" |

You can combine multiple modes in one run if the user's question spans them.

---

### Step 2 — Execute with the Query Script

Always install neo4j driver first, then run extraction with env vars injected at runtime.

```bash
pip install neo4j -q

NEO4J_URI="$NEO4J_URI" \
NEO4J_USER="$NEO4J_USER" \
NEO4J_PASSWORD="$NEO4J_PASSWORD" \
NEO4J_DATABASE="$NEO4J_DATABASE" \
python3 /home/user/neo4j-kg-extractor/scripts/kg_query.py \
  --mode <MODE> \
  [--label <NodeLabel>] \
  [--rel <RELATIONSHIP_TYPE>] \
  [--cypher "<Cypher query>"] \
  [--node-id <neo4j_element_id_or_id_prop>] \
  [--limit <N>] \
  [--output /tmp/kg_result.json]
```

Or write inline Python when you need custom logic — always read credentials from `os.environ`:

```python
from neo4j import GraphDatabase
import json, os

URI      = os.environ["NEO4J_URI"]
USER     = os.environ["NEO4J_USER"]
PASSWORD = os.environ["NEO4J_PASSWORD"]
DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

with driver.session(database=DATABASE) as session:
    results = session.run("<your cypher>")
    data = [dict(r) for r in results]

driver.close()
print(json.dumps(data, indent=2, default=str))
```

---

### Step 3 — Choose the Right Cypher Pattern

Use the reference below to construct correct, efficient Cypher queries.

See `references/cypher_patterns.md` for the complete Cypher library.

Key patterns at a glance:

```cypher
-- Schema
CALL db.labels()
CALL db.relationshipTypes()
CALL db.propertyKeys()
CALL apoc.meta.stats()

-- Count nodes per label
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total ORDER BY total DESC

-- Fetch nodes of a type
MATCH (n:Vendor) RETURN n LIMIT 25

-- Fetch with properties
MATCH (n:AIAgent) RETURN n.name, n.status, n.risk_tier, n.oversight_tier LIMIT 50

-- Relationships between two types
MATCH (a:Vendor)-[r]->(b:Control) RETURN a.name, type(r), b.name LIMIT 50

-- Neighborhood (everything around a node)
MATCH (n {name: $name})-[r]-(neighbor)
RETURN n, type(r), neighbor LIMIT 100

-- Path finding
MATCH path = shortestPath((a:Vendor {name: $v})-[*..6]-(b:Control {name: $c}))
RETURN path

-- Aggregations
MATCH (f:Finding) RETURN f.severity, count(f) AS total ORDER BY total DESC

-- Full export (paginated)
MATCH (n) OPTIONAL MATCH (n)-[r]->(m)
RETURN n, r, m SKIP $skip LIMIT 500
```

---

### Step 4 — Format Results for AI Analysis

After fetching data, always structure the output clearly:

#### For SCHEMA mode:
Present a markdown table with:
- Node labels + counts
- Relationship types + counts
- Key property keys per label
- A brief "graph fingerprint" description

#### For NODES mode:
Present as a structured table or JSON. Highlight key properties.
Group by label if multiple types returned.

#### For RELATIONSHIPS mode:
Show as `(NodeA)-[RELATIONSHIP]->(NodeB)` triplets.
Include property highlights where relevant.

#### For AI ANALYSIS mode:
Write a structured narrative covering:
1. **Graph Overview** — what kind of domain this graph represents
2. **Entity Inventory** — all node types and counts
3. **Key Relationships** — dominant relationship patterns
4. **Notable Observations** — anomalies, highly connected nodes, isolated nodes
5. **Data Quality Signals** — missing properties, orphan nodes, duplicate candidates
6. **AI-Ready Insights** — patterns useful for downstream AI tasks (classification, risk scoring, etc.)

---

### Step 5 — Save and Present

- For large results (>50 rows), save to an artifact (JSON, CSV, or markdown)
- Always show a summary in the chat, not just raw data
- Offer follow-up actions: "Would you like to drill deeper into any of these nodes?"

---

## This Graph's Domain (Pre-analyzed)

This knowledge graph models an **AI Governance & Compliance** system with:

| Node Type | What It Represents |
|-----------|-------------------|
| `Institution` | Regulated organizations |
| `Vendor` / `VendorService` | Third-party suppliers and services |
| `AIModel` / `AIAgent` | Registered AI models and autonomous agents |
| `Control` / `ControlState` | Compliance controls and their current state |
| `Framework` / `Obligation` | Regulatory frameworks and specific duties |
| `Finding` / `Exposure` | Audit findings and risk exposures |
| `Remediation` / `Exception` | Corrective actions and approved exceptions |
| `EvidenceDoc` | Supporting evidence documents |
| `Assessment` / `Exam` / `ExamItem` | Assessment records and exam questions |
| `Decision` / `AgentRun` | AI agent decisions and execution logs |
| `Contract` | Vendor contracts |
| `User` | System users and their roles |
| `BusinessProcess` | Business processes linked to applications |
| `Application` | Software applications in scope |

**Key relationship clusters:**
- Vendor → provides → VendorService → runs → Application
- AIAgent → runs_on → Application → supports → BusinessProcess
- Control → has_state → ControlState → satisfies → Obligation → in_framework → Framework
- Finding → on_control → Control → remediated_by → Remediation
- Assessment → covers → Control / Vendor

---

## Common Analysis Queries

These are ready-to-run queries for frequent user requests:

### "Show me all AI agents and their risk status"
```cypher
MATCH (a:AIAgent)
RETURN a.name, a.risk_tier, a.oversight_tier, a.status,
       a.kill_switch_enabled, a.eu_ai_act_tier
ORDER BY a.risk_tier
```

### "What vendors do we use and are they critical?"
```cypher
MATCH (v:Vendor)
RETURN v.name, v.tier, v.is_critical_or_important, v.status, v.onboarded_on
ORDER BY v.tier
```

### "Show me open findings and their severity"
```cypher
MATCH (f:Finding)
WHERE f.closure_state IS NULL OR f.closure_state <> 'closed'
RETURN f.title, f.severity, f.finding_type, f.due_date, f.routed_at
ORDER BY f.severity, f.due_date
```

### "What controls are failing?"
```cypher
MATCH (c:Control)-[:HAS_STATE]->(cs:ControlState)
WHERE cs.state IN ['failing', 'non_compliant', 'at_risk']
RETURN c.name, c.control_type, c.family, cs.state, cs.observed_at
ORDER BY cs.observed_at DESC
```

### "Show obligations from a specific framework"
```cypher
MATCH (o:Obligation)-[:IN_FRAMEWORK]->(f:Framework)
RETURN f.name, o.ref, o.title, o.obligation_type, o.jurisdiction
ORDER BY f.name, o.ref
```

### "What evidence documents exist?"
```cypher
MATCH (e:EvidenceDoc)
RETURN e.doc_ref, e.doc_type, e.ingested_at, e.source_uri, e.page_count
ORDER BY e.ingested_at DESC
LIMIT 50
```

### "Show the full compliance path for a vendor"
```cypher
MATCH (v:Vendor {name: $vendor_name})
OPTIONAL MATCH (v)-[:HAS_CONTRACT]->(c:Contract)
OPTIONAL MATCH (v)-[:ASSESSED_BY]->(a:Assessment)
OPTIONAL MATCH (s:VendorService)-[:PROVIDED_BY]->(v)
OPTIONAL MATCH (f:Finding)-[:ON_VENDOR]->(v)
RETURN v, c, a, collect(distinct s) AS services, collect(distinct f) AS findings
```

---

## Error Handling

| Error | Response |
|-------|----------|
| Auth failure | Report credentials issue, ask user to verify env vars |
| Node label not found | Suggest correct label from `CALL db.labels()` |
| Property not found | Suggest using `CALL db.propertyKeys()` to verify |
| Timeout on large query | Add `LIMIT`, use pagination (`SKIP`/`LIMIT`) |
| Empty result | Confirm label spelling, check if data exists with a count query |
| Missing env vars | Print clear error listing which env vars are missing |

---

## Output Quality Rules

- **Never dump raw Neo4j driver objects** — always convert to plain dicts/lists
- **Always use `default=str`** in `json.dumps()` to handle datetime/UUID types
- **Paginate** results larger than 500 nodes
- **Denote units** in property values where known (dates, currencies, booleans)
- **Flag nulls** — when key properties are missing, call it out in the analysis
- Offer to **export to CSV or JSON** for any tabular result
- **Never log or print credentials** — not in stdout, not in artifacts, not in chat
