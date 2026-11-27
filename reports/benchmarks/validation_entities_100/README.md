# Production extractor validation diagnostics

These archived results use the same 100 original validation utterances in
`data/evaluation/entities_validation.jsonl`:

- `before.json`: earlier extractor metrics, micro-F1 **0.469565**.
- `system_evaluation.json` / `.md`: revised extractor, micro-F1 **0.892308**,
  with per-query predictions and run metadata.

This is a development comparison on validation data used to improve the rules.
It does not certify the proposal's held-out 85% target. It is separate from
Qwen APE prompt scoring, whose saved best entity micro-F1 remains **0.700**.
The earlier metrics file contains no per-query outputs or run metadata; the
revised JSON contains the recorded metadata. Do not infer missing provenance.

To rerun the current extractor without loading the trained classifier:

```powershell
python scripts/evaluate_system.py --component entities --entity-data data/evaluation/entities_validation.jsonl --output-dir reports/evaluation/validation_replay
```
