# Phase 1 Baseline Report

## Source and lineage

- Source: Crossref REST API
- Query: `agentic retrieval augmented generation large language model`
- Filter: `from-pub-date:2026-03-30,has-abstract:true`
- Raw records: 24
- Clean records: 24
- Evaluation questions: 10
- Run time (UTC): 2026-09-26T15:33:25.453219+00:00

## Baseline RAG evaluation

| Metric | Value |
| --- | ---: |
| Samples | 10 |
| Retrieval hit rate | 1.0000 |
| Mean token F1 | 1.0000 |
| Judge accuracy | 1.0000 |
| Mean judge score | 5.0000 |

Ragas: Set RUN_RAGAS=1 to enable the slower Ragas pass.

## Data quality gate

- Overall success: **True**
- Great Expectations success: True
- GX validations executed: 6

## Freshness SLA

- Fresh: **True**
- Threshold: 180 days
- Stale rows: 0 / 24
- Stale ratio: 0.00%
- Oldest publication: 2026-04-01
- Latest publication: 2026-09-15
