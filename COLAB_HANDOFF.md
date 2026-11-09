# Colab handoff: Qwen3.5-9B benchmark for ActivIQ

You are continuing an experiment on a fitness-chatbot NLU project. Read this
file first, then `data/auto_labelling/README.md` and `data/evaluation/README.md`.

## Goal

Benchmark **Qwen3.5-9B** (zero-shot, bare base model, no adapter) as a
single-pass labeller on the 120-utterance held-out test split, and report the
full metric set next to the existing DistilBERT + spaCy baseline:

- intent: accuracy, macro-F1, weighted-F1, per-class precision/recall/F1, confusion matrix
- entities: micro precision/recall/F1, macro-F1, per-slot P/R/F1, exact-match rate
- LLM output validity (invalid JSON count) and per-utterance latency (median/p95)

The script already computes all of this: `scripts/evaluate_lora.py`
(`--adapter` is optional; omit it to score the bare 9B).

## Simplest path: `notebooks/qwen9b_benchmark.ipynb`
Commit/push the repo, open the notebook in Colab (File > Open > GitHub), run all cells. It clones the repo, downloads Qwen, runs the benchmark with `--skip-baseline` (DistilBERT weights are gitignored) and prints the metrics. The zip route below is the alternative.

## What is in the zip

`src/`, `scripts/`, `data/` (processed intents, evaluation sets, auto-labelling
seeds), `prompts/`, `tests/`, requirements files, and
`models/intent_classifier/` (final DistilBERT weights only, ~255 MB; no
checkpoints). **Not included:** any Qwen weights (download in Colab) and any venv.

## Colab setup

Runtime: GPU. Qwen3.5-9B in bf16 needs ~19 GB, so it will not fit a 15 GB T4.
Use an L4/A100, or add `--quantization 4bit` (needs `bitsandbytes`, CUDA only).

```python
from google.colab import files
files.upload()                      # activiq_colab.zip
!unzip -q activiq_colab.zip -d ActivIQ
%cd ActivIQ
!pip install -q -r requirements-llm-4bit.txt     # torch already on Colab; keep Colab's build
!pip install -q spacy pandas      # baseline only; it uses spacy.blank("en"), no model download

from huggingface_hub import snapshot_download
snapshot_download("Qwen/Qwen3.5-9B", local_dir="models/qwen3.5-9b")      # note the revision hash
```

The code loads with `local_files_only=True`, so the checkpoint must be a local
folder. It never calls a hosted API.

## Run the benchmark

```bash
python scripts/evaluate_lora.py \
  --model-path models/qwen3.5-9b \
  --device cuda --quantization 4bit \
  --allow-draft \
  --output-dir reports/evaluation/qwen9b_zeroshot
# add --skip-baseline if the DistilBERT/spaCy baseline can't load in Colab
```

Output: `reports/evaluation/qwen9b_zeroshot/lora_comparison.json` (all metrics;
the key is named `lora` for historical reasons but with no adapter it is the
bare 9B). Print the intent and entity tables for the user.

## Known caveats (state these in the report, do not hide them)

1. `data/evaluation/entities_test.jsonl` is entirely `unlabelled`, so **entity
   F1 on the test split is `pending_human_annotation`**. Intent metrics are
   valid now. Do not fabricate or auto-fill test entity labels.
2. `entities_validation.jsonl` (100 rows) and `seeds.jsonl` (10 rows) were AI
   drafted, then human reviewed (`label_status: human_reviewed`, reviewer in
   `annotator`). Disclose the AI assistance in the report. Scores against the
   validation rows are "validation selection scores", not held-out performance.
   `scripts/auto_label.py check` now passes; never bypass the preflight.
3. The prompt in `src/lora.py` (`SYSTEM_PROMPT`) is a zero-shot instruction. A
   few-shot or APE-selected prompt (`prompts/auto_labelling/baseline.txt`,
   `scripts/auto_label.py propose/score`) is a separate experiment.
4. Invalid model output counts as a wrong intent and missed entities.
5. Latency is generate-only timing on Colab hardware, not comparable to the
   CPU latency of the baseline.
6. Never use the test split for training or prompt selection.

## Optional follow-ups

- 2B LoRA comparison: `scripts/train_lora.py` then `evaluate_lora.py --adapter <dir>`
  (needs `machine_labels.jsonl` from `auto_label.py label`, which needs reviewed seeds).
- Sanity tests: `python -m unittest discover -s tests -v`.
- Download `reports/evaluation/` back to the user when finished.
