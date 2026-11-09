# APE validation comparison

Prompt selection on validation data; not held-out test performance. Invalid generations are not dropped.

Real local-model run: True

| Prompt | Entity micro-F1 | Intent agreement | Valid output rate |
|---|---:|---:|---:|
| ape-002 | 0.7 | 0.9200 | 1.0000 |
| ape-003 | 0.6707317073170732 | 0.9300 | 1.0000 |
| baseline | 0.6586826347305389 | 0.9200 | 1.0000 |
| ape-004 | 0.6467065868263473 | 0.9200 | 1.0000 |
| ape-001 | 0.6428571428571429 | 0.9200 | 1.0000 |

Selected: ape-002
