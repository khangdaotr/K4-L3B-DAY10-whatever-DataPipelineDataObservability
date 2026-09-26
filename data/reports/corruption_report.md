# Corruption Impact and Recovery Report

## Three-state performance comparison

| Metric | Baseline | Corrupted | Repaired | Corruption delta | Recovery delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 0.9000 | 1.0000 | -0.1000 | +0.1000 |
| Mean token F1 | 1.0000 | 0.9170 | 1.0000 | -0.0830 | +0.0830 |
| Judge accuracy | 1.0000 | 0.9000 | 1.0000 | -0.1000 | +0.1000 |
| Mean judge score | 5.0000 | 4.6000 | 5.0000 | -0.4000 | +0.4000 |

## Quality and freshness comparison

| Signal | Corrupted | Repaired |
| --- | ---: | ---: |
| GX quality gate | False | True |
| Overall quality + freshness | False | True |
| Freshness SLA | False | True |
| Stale rows | 6 | 0 |
| Stale ratio | 28.57% | 0.00% |

## Interpretation

The corrupted state demonstrates a silent failure: the pipeline remains executable and can still return answers, while retrieval/answer metrics and automated data-quality signals deteriorate. The repaired state is rebuilt idempotently from the preserved raw snapshot, restoring the clean schema, freshness, and baseline behavior without trusting corrupted derived artifacts.
