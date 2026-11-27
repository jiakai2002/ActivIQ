# Supplementary reviewed entity benchmark

The primary benchmark remains the original 120 Hugging Face test utterances in
`../entities_test.jsonl`. This separate 100-query corpus supports the extractor
improvement analysis shown in the presentation; it replaces no source split and
is never input to training, APE seed selection or prompt scoring.

The utterances and draft labels were AI-authored. Michael Suteja confirmed review
before the frozen labels were scored. All 100 drafts were accepted without saved
corrections; each record retains that provenance. The corpus contains 181 entity
mentions across all eight slots. Review is not the same as independent human
authorship, and scores on this small supplementary corpus have that limitation.

`manifest.json` records the original/revised commits, coverage and frozen-file
SHA-256. The JSONL file is copied byte-for-byte from the reviewed packet; Git
attributes disable newline conversion for this file so its hash stays stable.

The paired results are **70.59% -> 83.82% entity micro-F1**. The 85% target was
missed. The historical **45.52%** result uses the original 120-query benchmark
and must not be described as the starting score on these 100 queries.

See the [paired comparison and archived reports](../../../reports/benchmarks/reviewed_entities_100/comparison.md).
The archived JSON includes predictions, source/data hashes, original machine
paths and package versions. Historical paths identify the original run; they
are not required directories on a reviewer's computer.

Rerun the current extractor from the repository root (no trained classifier or
Qwen checkpoint is needed):

```powershell
python scripts/evaluate_system.py --component entities --entity-data data/evaluation/supplementary/entities_fresh_reviewed_frozen.jsonl --output-dir reports/evaluation/supplementary_replay
```

To replay the original result, use a separate checkout of commit
`17db77ea5540909fcea695f9f78204ae4ea828b2` and pass the absolute path to the same
frozen annotation file with `--entity-data`. The revised reference commit is
`046368ba3bec2af549ca53745f91048cde56b65d`. Keep the same processed knowledge bases
and spaCy backend for both versions. New runs belong in the ignored
`reports/evaluation/` directory; preserve the archived reports unchanged.
