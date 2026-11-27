# Fresh human-reviewed entity evaluation

**The revised extractor improved from 70.59% to 83.82% entity micro-F1. The 85% proposal target was not met on this set.**

Both versions scored the same 100 new AI-authored utterances and 181 entity mentions. Michael Suteja confirmed human review before the labels were frozen and scored. All eight slots had positive support. The labels were accepted without saved corrections. The set is separate from the historical test, validation, and earlier AI challenge.

| Metric | Original | Revised |
|---|---:|---:|
| Entity micro-precision | 75.47% | 87.88% |
| Entity micro-recall | 66.30% | 80.11% |
| Entity micro-f1 | 70.59% | 83.82% |
| Exact match across all eight slots | 45% | 66% |

| Slot | Reviewed mentions | Original F1 | Revised F1 |
|---|---:|---:|---:|
| exercise | 32 | 38.46% | 45.61% |
| body part | 32 | 90.32% | 92.06% |
| equipment | 32 | 81.36% | 85.25% |
| goal | 16 | 89.66% | 93.33% |
| level | 11 | 95.65% | 95.65% |
| duration | 17 | 57.14% | 91.43% |
| food | 19 | 30.77% | 84.85% |
| nutrient | 22 | 87.80% | 100.00% |

Exercise names remain the largest source of errors. The revised rules missed 19 of the 32 reviewed exercise mentions and produced 12 extra exercise predictions.

## Presentation wording

> On 100 fresh AI-authored, human-reviewed queries, the production extractor improved from 70.59% to 83.82% entity micro-F1. Food and duration improved the most. The revised extractor fell 1.18 percentage points short of our 85% target. Exercise names remain the main weakness.

## Reproducibility

- Original extractor commit: `17db77ea5540909fcea695f9f78204ae4ea828b2`.
- Revised extractor commit: `046368ba3bec2af549ca53745f91048cde56b65d`.
- Frozen reviewed labels SHA-256: `6b687dc544fe5b071caabed287cf4da94327b505525b2893abb9aa08fd6b7887`.
- The same local knowledge bases and spaCy backend were used. The standard evaluator scored all 100 rows without draft mode.
- The benchmark author generated the queries and draft labels before running either version on this set. Results describe the reviewed, AI-authored corpus.

This is a supplementary diagnostic corpus. The primary experiment uses the original 120 Hugging Face test utterances; the two corpora must not be combined into one before/after claim. The historical LoRA comparison still uses the earlier extractor, and no Qwen or LoRA rerun is implied by these results.

[Frozen reviewed labels](../../../data/evaluation/supplementary/entities_fresh_reviewed_frozen.jsonl) · [Original report](original/system_evaluation.md) · [Revised report](revised/system_evaluation.md) · [Manifest](../../../data/evaluation/supplementary/manifest.json)
