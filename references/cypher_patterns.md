# Cypher Pattern Library

A complete reference of Cypher queries optimized for the AI Governance Knowledge Graph.

---

## 1. Schema Discovery

```cypher
-- All node labels
CALL db.labels() YIELD label RETURN label ORDER BY label

-- All relationship types
CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType

-- All property keys
CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey ORDER BY propertyKey

-- Node counts per label
MATCH (n) RETURN labels(n)[0] AS label, count(n) AS total ORDER BY total DESC

-- Relationship counts per type
MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS total ORDER BY total DESC

-- Graph statistics summary
MATCH (n) WITH count(n) AS nodes
MATCH ()-[r]->() WITH nodes, count(r) AS rels
RETURN nodes, rels

-- Properties used per label (sample-based)
MATCH (n:Vendor) RETURN keys(n) AS properties LIMIT 1
```

---

## 2. Node Fetching

```cypher
-- All nodes of a label
MATCH (n:AIAgent) RETURN n LIMIT 50

-- Nodes with specific property filter
MATCH (n:Vendor) WHERE n.is_critical_or_important = true RETURN n

-- Nodes with property projection (faster, cleaner)
MATCH (n:Control)
RETURN n.name AS name, n.control_type AS type, n.family AS family, n.frequency AS frequency
ORDER BY n.family, n.name
LIMIT 100

-- Nodes created recently
MATCH (n) WHERE n.created_at IS NOT NULL
RETURN labels(n)[0] AS label, n.name, n.created_at
ORDER BY n.created_at DESC LIMIT 20

-- Search nodes by name (case-insensitive)
MATCH (n) WHERE toLower(n.name) CONTAINS toLower($search_term)
RETURN labels(n)[0] AS label, n.name, n.id LIMIT 50

-- Nodes missing key property
MATCH (n:Vendor) WHERE n.name IS NULL RETURN n LIMIT 20

-- Orphan nodes (no relationships)
MATCH (n) WHERE NOT (n)--() RETURN labels(n)[0] AS label, n.name, n.id LIMIT 50
```

---

## 3. Relationship Fetching

```cypher
-- All relationships (sampled)
MATCH (a)-[r]->(b)
RETURN labels(a)[0] AS from, a.name AS from_name,
       type(r) AS rel,
       labels(b)[0] AS to, b.name AS to_name
LIMIT 100

-- Relationships of a specific type
MATCH (a)-[r:ASSESSED_BY]->(b)
RETURN a.name AS assessed, b.name AS assessor, properties(r) AS rel_props
LIMIT 50

-- Outgoing relationships from a node
MATCH (v:Vendor {name: "Acme Corp"})-[r]->(target)
RETURN type(r) AS relationship, labels(target)[0] AS target_type, target.name AS target_name

-- Incoming relationships to a node
MATCH (source)-[r]->(v:Vendor {name: "Acme Corp"})
RETURN labels(source)[0] AS source_type, source.name AS source_name, type(r) AS relationship

-- Relationship property inspection
MATCH ()-[r:HAS_CONTRACT]->()
RETURN keys(r) AS contract_properties LIMIT 1

-- Count relationships per node
MATCH (n:AIAgent)
OPTIONAL MATCH (n)-[r]-()
RETURN n.name, count(r) AS degree ORDER BY degree DESC
```

---

## 4. AI Governance Specific Queries

### AI Models & Agents
```cypher
-- All AI agents with risk profile
MATCH (a:AIAgent)
RETURN a.name, a.risk_tier, a.oversight_tier, a.status,
       a.kill_switch_enabled, a.eu_ai_act_tier, a.guardrails,
       a.tools_allowed, a.decision_surface
ORDER BY a.risk_tier

-- AI agent runs (execution history)
MATCH (ar:AgentRun)-[:BY]->(a:AIAgent)
RETURN a.name AS agent, ar.started_at, ar.ended_at,
       ar.groundedness_score, ar.guardrails_fired, ar.model_name
ORDER BY ar.started_at DESC LIMIT 50

-- Which applications run AI agents?
MATCH (a:AIAgent)-[:RUNS_ON]->(app:Application)
RETURN a.name AS agent, app.name AS application, app.hosting, app.app_type

-- AI models and their agents
MATCH (m:AIModel)<-[:RUNS_ON]-(a:AIAgent)
RETURN m.name AS model, m.current_version, collect(a.name) AS agents
```

### Vendors & Contracts
```cypher
-- Critical vendors
MATCH (v:Vendor)
WHERE v.is_critical_or_important = true OR v.tier IN ['1', '2', 1, 2]
RETURN v.name, v.tier, v.status, v.onboarded_on, v.jurisdictions

-- Vendor services overview
MATCH (vs:VendorService)-[:PROVIDED_BY]->(v:Vendor)
RETURN v.name AS vendor, vs.name AS service, vs.service_type,
       vs.use_case, vs.risk_tier, vs.status
ORDER BY v.name

-- Contracts expiring
MATCH (c:Contract)
WHERE c.end_date IS NOT NULL
RETURN c.contract_ref, c.annual_value_usd, c.start_date, c.end_date,
       c.exit_plan_exists, c.audit_rights_present
ORDER BY c.end_date ASC

-- Vendors with no recent assessment
MATCH (v:Vendor)
WHERE NOT (v)-[:ASSESSED_BY]->(:Assessment)
RETURN v.name, v.tier, v.status
```

### Controls & Compliance
```cypher
-- Control states summary
MATCH (c:Control)-[:HAS_STATE]->(cs:ControlState)
RETURN c.name, c.family, c.control_type, cs.state, cs.observed_at, cs.source
ORDER BY cs.state, c.family

-- Failing controls
MATCH (c:Control)-[:HAS_STATE]->(cs:ControlState)
WHERE cs.state IN ['failing', 'non_compliant', 'at_risk', 'fail']
RETURN c.name, c.family, c.control_type, cs.state, cs.rationale
ORDER BY c.family

-- Controls without any state
MATCH (c:Control) WHERE NOT (c)-[:HAS_STATE]->()
RETURN c.name, c.family, c.control_type

-- Control → Obligation → Framework chain
MATCH (c:Control)-[:SATISFIES]->(o:Obligation)-[:IN_FRAMEWORK]->(f:Framework)
RETURN c.name AS control, o.ref AS obligation_ref, o.title AS obligation,
       f.name AS framework, f.jurisdiction
ORDER BY f.name, o.ref
```

### Findings & Remediations
```cypher
-- Open findings by severity
MATCH (f:Finding)
WHERE f.closure_state IS NULL OR f.closure_state <> 'closed'
RETURN f.title, f.severity, f.finding_type, f.due_date, f.routed_at,
       f.signal, f.external_ref
ORDER BY CASE f.severity
  WHEN 'critical' THEN 1
  WHEN 'high' THEN 2
  WHEN 'medium' THEN 3
  WHEN 'low' THEN 4
  ELSE 5 END, f.due_date

-- Findings on controls
MATCH (f:Finding)-[:ON_CONTROL]->(c:Control)
RETURN f.title AS finding, f.severity, c.name AS control, c.family
ORDER BY f.severity

-- Findings with remediations
MATCH (f:Finding)-[:REMEDIATED_BY]->(r:Remediation)
RETURN f.title AS finding, f.severity, r.priority AS priority,
       r.due_date AS due, r.closed_at AS closed, r.closure_state
ORDER BY r.due_date

-- Exceptions (accepted risk)
MATCH (ex:Exception)
RETURN ex.title, ex.severity, ex.expiry, ex.accepted_at, ex.rationale
ORDER BY ex.expiry
```

### Obligations & Frameworks
```cypher
-- All frameworks
MATCH (f:Framework)
RETURN f.name, f.jurisdiction, f.issuer, f.effective_from
ORDER BY f.jurisdiction, f.name

-- Obligations per framework
MATCH (o:Obligation)-[:IN_FRAMEWORK]->(f:Framework)
RETURN f.name AS framework, o.ref, o.title, o.obligation_type,
       o.article, o.source_location
ORDER BY f.name, o.ref

-- Unaddressed obligations (no satisfying control)
MATCH (o:Obligation)-[:IN_FRAMEWORK]->(f:Framework)
WHERE NOT (:Control)-[:SATISFIES]->(o)
RETURN o.ref, o.title, f.name AS framework, o.obligation_type

-- Obligation duty owners
MATCH (u:User)-[:DUTY_OWNER]->(o:Obligation)
RETURN u.full_name AS owner, u.email, collect(o.ref) AS obligations
```

### Evidence & Assessments
```cypher
-- Evidence documents
MATCH (e:EvidenceDoc)
RETURN e.doc_ref, e.doc_type, e.ingested_at, e.page_count,
       e.source_uri, e.injection_screened
ORDER BY e.ingested_at DESC

-- Recent assessments
MATCH (a:Assessment)
RETURN a.assessment_type, a.outcome, a.completed_on, a.next_due_on
ORDER BY a.completed_on DESC LIMIT 20

-- Exam items and conclusions
MATCH (ei:ExamItem)-[:IN_EXAM]->(ex:Exam)
OPTIONAL MATCH (d:Decision)-[:DECIDES]->(ei)
RETURN ex.exam_type, ex.exam_date, ei.item_ref, ei.page,
       d.result, d.conclusion, d.decided_at
ORDER BY ex.exam_date DESC, ei.item_ref
```

---

## 5. Path & Graph Traversal

```cypher
-- Shortest path between two nodes
MATCH (a {name: $node_a}), (b {name: $node_b})
MATCH path = shortestPath((a)-[*..10]-(b))
RETURN [n IN nodes(path) | {label: labels(n)[0], name: n.name}] AS path_nodes,
       [r IN relationships(path) | type(r)] AS relationship_chain,
       length(path) AS hops

-- All paths up to N hops
MATCH (a {name: $node_a}), (b {name: $node_b})
MATCH path = (a)-[*1..4]-(b)
RETURN path LIMIT 10

-- Reachable nodes from a starting node
MATCH (start {name: $start})-[*1..3]->(reachable)
RETURN DISTINCT labels(reachable)[0] AS type, reachable.name AS name

-- Connected components (nodes in same cluster)
MATCH (n {name: $name})-[r*1..2]-(neighbor)
RETURN DISTINCT labels(neighbor)[0] AS label, neighbor.name AS name,
       [rel IN r | type(rel)] AS via_rels
```

---

## 6. Aggregations & Statistics

```cypher
-- Distribution of property values
MATCH (n:Finding)
RETURN n.severity AS value, count(n) AS total
ORDER BY total DESC

-- Average/sum numeric properties
MATCH (c:Contract) WHERE c.annual_value_usd IS NOT NULL
RETURN sum(c.annual_value_usd) AS total_contract_value,
       avg(c.annual_value_usd) AS avg_contract_value,
       min(c.annual_value_usd) AS min_val,
       max(c.annual_value_usd) AS max_val

-- Most connected nodes (hubs)
MATCH (n)-[r]-()
RETURN labels(n)[0] AS label, n.name, count(r) AS degree
ORDER BY degree DESC LIMIT 20

-- Nodes with most outgoing relationships
MATCH (n)-[r]->()
RETURN labels(n)[0] AS label, n.name, count(r) AS out_degree
ORDER BY out_degree DESC LIMIT 20

-- Property coverage (% nodes having a property)
MATCH (n:Control)
RETURN count(n) AS total,
       count(n.name) AS has_name,
       count(n.family) AS has_family,
       count(n.frequency) AS has_frequency

-- Timeline of node creation
MATCH (n) WHERE n.created_at IS NOT NULL
RETURN date(n.created_at) AS day, count(n) AS created
ORDER BY day DESC LIMIT 30
```

---

## 7. Full Graph Export (Paginated)

```cypher
-- All nodes (page N, 500 per page)
MATCH (n)
RETURN n SKIP $skip LIMIT 500

-- All relationships (page N, 500 per page)  
MATCH (a)-[r]->(b)
RETURN labels(a)[0] AS from_label, a.name AS from_name, id(a) AS from_id,
       type(r) AS relationship, properties(r) AS rel_props,
       labels(b)[0] AS to_label, b.name AS to_name, id(b) AS to_id
SKIP $skip LIMIT 500

-- Full graph as adjacency list
MATCH (n)
OPTIONAL MATCH (n)-[r]->(m)
WITH n, collect({
  rel: type(r),
  target_label: labels(m)[0],
  target_name: m.name,
  target_id: m.id
}) AS outgoing
RETURN labels(n)[0] AS label, n.name AS name, n.id AS node_id,
       properties(n) AS props, outgoing
LIMIT 1000
```

---

## 8. Data Quality & Anomaly Detection

```cypher
-- Nodes with no name property
MATCH (n) WHERE n.name IS NULL
RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC

-- Duplicate detection (same name, same label)
MATCH (n)
WITH labels(n)[0] AS label, n.name AS name, count(n) AS cnt
WHERE cnt > 1 AND name IS NOT NULL
RETURN label, name, cnt ORDER BY cnt DESC

-- Nodes with no relationships
MATCH (n) WHERE NOT (n)--()
RETURN labels(n)[0] AS label, count(n) AS isolated_count

-- Missing critical properties for AIAgent
MATCH (a:AIAgent)
WHERE a.risk_tier IS NULL OR a.oversight_tier IS NULL OR a.kill_switch_enabled IS NULL
RETURN a.name, a.risk_tier, a.oversight_tier, a.kill_switch_enabled

-- Overdue remediations
MATCH (r:Remediation)
WHERE r.due_date IS NOT NULL AND r.closure_state <> 'closed'
  AND date(r.due_date) < date()
RETURN r.priority, r.due_date, r.external_ticket_ref
ORDER BY r.due_date
```
