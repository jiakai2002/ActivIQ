# Colab handoff: auto-labelling and LoRA experiment

**Status: done.** The full experiment was run in one session with
`notebooks/activiq_end_to_end.ipynb` on a Colab A100. Results, tables and caveats are in
[HANDOFF.md](HANDOFF.md) ("Experiment results"); raw outputs are in `ActivIQ_runs/`.
Read this file only to rerun or extend the experiment.

## Rerun

1. Open `notebooks/activiq_end_to_end.ipynb` in a fresh Colab A100 runtime.
   The notebook clones `main` and downloads the Qwen revisions in
   `ActivIQ_runs/model_revisions.json`.
2. Read `prompts/auto_labelling/baseline.txt`. Set `PROMPT_FROZEN = True` in the
   first code cell once the team has approved that prompt, then select Run all
   (the original A100 run took about two hours).
3. New results go to `MyDrive/ActivIQ_runs_pinned`. Use the same project revision
   and run directory to resume after a disconnect. Change the Drive directory
   for a new experiment. The saved notebook outputs and tracked `ActivIQ_runs/`
   document the original run.

The notebook stages: zero-shot 9B benchmark, APE `propose` and `score` (10 reviewed
seeds, 100 reviewed validation rows), `label` the 960 training rows, LoRA-train Qwen3.5-2B,
evaluate on the 120 test rows against DistilBERT + spaCy. Commands are in
`data/auto_labelling/README.md`.

`notebooks/activiq_lora_pipeline.ipynb` and `notebooks/qwen9b_benchmark.ipynb` are
earlier, partial versions superseded by the end-to-end notebook.

## Not in Git (keep on the team Drive)

- LoRA adapter weights `ActivIQ_runs/lora/adapter_v1/adapter_model.safetensors` (93 MB).
  Share the full adapter directory with reviewers or provide the rerun instructions
  above so they can regenerate it.
- DistilBERT weights `models/intent_classifier/` (retrain with `scripts/train_intent.py`).
- Qwen checkpoints (downloaded by the notebook; revisions in `ActivIQ_runs/model_revisions.json`).

## Rules that still apply

- Never use the test split for training, prompt selection or rule tuning.
- Disclose that seed, validation and test entity labels were AI-drafted then human reviewed.
- Validation scores are selection scores, not held-out performance.
- Invalid model output counts as a wrong intent and missed entities.
- Qwen latency is GPU timing and is not comparable to DistilBERT's.
