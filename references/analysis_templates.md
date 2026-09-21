# Analysis Output Templates

Use these templates when generating AI analysis reports from knowledge graph data.

---

## Template 1: Full Graph Analysis Report

```markdown
# Knowledge Graph Analysis Report
**Generated:** {timestamp}
**Graph:** {database_name}

---

## 📊 Graph Overview
- **Total Nodes:** {total_nodes} across {label_count} types
- **Total Relationships:** {total_relationships} across {rel_type_count} types
- **Domain:** {inferred_domain}

---

## 🗂 Entity Inventory

| Node Type | Count | Key Properties |
|-----------|-------|----------------|
{node_table_rows}

---

## 🔗 Relationship Map

| Relationship | Count | Connects |
|-------------|-------|---------|
{rel_table_rows}

---

## 🌟 Highly Connected Nodes (Hubs)

{top_connected_table}

---

## ⚠️ Data Quality Observations

- **Isolated nodes:** {isolated_count} nodes have no relationships
- **Nodes missing name:** {no_name_summary}
- **Potential duplicates:** {duplicate_summary}

---

## 🔍 Domain-Specific Insights

### Risk & Compliance Status
{risk_compliance_summary}

### AI Governance Posture
{ai_governance_summary}

### Vendor Landscape
{vendor_summary}

---

## 💡 Recommendations for AI Analysis

1. {recommendation_1}
2. {recommendation_2}
3. {recommendation_3}
```

---

## Template 2: Compliance Summary Report

```markdown
# Compliance Status Report
**As of:** {date}

## Control Health
| Status | Count | % |
|--------|-------|---|
| Passing | {passing} | {pct_passing}% |
| Failing | {failing} | {pct_failing}% |
| At Risk | {at_risk} | {pct_at_risk}% |
| Unknown | {unknown} | {pct_unknown}% |

## Open Findings by Severity
| Severity | Open | Overdue |
|----------|------|---------|
| Critical | {critical_open} | {critical_overdue} |
| High | {high_open} | {high_overdue} |
| Medium | {medium_open} | {medium_overdue} |
| Low | {low_open} | {low_overdue} |

## Framework Coverage
{framework_coverage_table}

## Obligations Without Controls
{unaddressed_obligations}
```

---

## Template 3: Vendor Risk Summary

```markdown
# Vendor Risk Summary

## Critical & Important Vendors ({count})

{vendor_table}

## Contracts Expiring in 90 Days
{expiring_contracts}

## Vendors Without Recent Assessment
{unassessed_vendors}
```

---

## Template 4: AI Agent Register

```markdown
# AI Agent Register

| Agent | Risk Tier | Oversight | EU AI Act | Kill Switch | Status |
|-------|-----------|-----------|-----------|-------------|--------|
{agent_rows}

## High-Risk Agents Requiring Attention
{high_risk_agents}

## Agents with Guardrails Fired Recently
{guardrails_fired}
```

---

## Narrative Templates

### For "What's notable in this graph?"

> This knowledge graph models an **{domain}** environment containing **{total_nodes} nodes** 
> across **{label_count} entity types** and **{total_relationships} relationships**.
>
> The most populated entity types are **{top_label_1}** ({count_1} nodes), 
> **{top_label_2}** ({count_2} nodes), and **{top_label_3}** ({count_3} nodes).
>
> Key structural observations:
> - The most connected nodes are: {top_connected}
> - There are {isolated_count} isolated nodes with no relationships
> - The dominant relationship patterns are: {top_rels}
>
> Domain insights:
> - {insight_1}
> - {insight_2}
> - {insight_3}

### For "What are the risks?"

> Based on the knowledge graph data:
>
> **Compliance Risks:**
> - {N} controls are in a failing/at-risk state
> - {M} findings are open, including {critical_count} critical severity
> - {K} obligations have no satisfying control mapped
>
> **Vendor Risks:**
> - {V} critical/important vendors identified
> - {X} vendors have no recent assessment on record
> - {Y} contracts expiring within 90 days
>
> **AI Governance Risks:**
> - {A} high-risk AI agents in operation
> - {B} agents with kill switch disabled
> - {C} agents where guardrails were recently fired
