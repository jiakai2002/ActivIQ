# Local auto-labelling and Automatic Prompt Engineering

This is an offline research experiment alongside the existing chatbot. It uses
direct Transformers inference on a **local checkpoint**, with no LLM API/server,
and never changes the chatbot's production classifier or human reference labels.
Implementation is infrastructure, not completed Qwen/APE/LoRA research results.

## What is ready

1. Ten AI-draft training-seed annotations in `seeds.jsonl`, sampled with seed 42 and
   covering all six intents. Sampling metadata and original split hashes are in
   `seed_manifest.json`. These labels require human review before use.
2. Direct local inference, greedy annotation, optional CUDA NF4 4-bit loading,
   disabled thinking in the chat template, explicit context limits and full
   checkpoint/tokenizer fingerprints.
3. Model-generated candidate instructions from the **ten reviewed seeds only**.
4. Comparison of those instructions and a baseline on **100 reviewed validation
   examples**, using the same seed examples and query settings for every prompt.
5. Selection by entity micro-F1, with explicit validity/intent-agreement tie
   breaks; baseline wins a complete tie. If baseline is better, it stays selected.
6. Training-only annotation, with malformed rows quarantined, source intents
   preserved and machine provenance attached to every accepted label.
7. Per-query atomic checkpoints, resumable runs, raw attempts/errors, checksums
   and readable summaries. Saved completed generations are reused after an
   interruption; changed inputs, model, contract or experiment code invalidate
   resume rather than mixing experiments.

The pipeline is:

```text
10 human training seeds -> local model proposes instructions
                       -> baseline + candidates label 100 validation queries
                       -> score against human validation labels
                       -> freeze selected prompt
                       -> label original 960 training utterances
                       -> report agreement and export accepted machine labels
```

## Human inputs needed first

Review and correct the ten AI-draft `entities` dictionaries in `seeds.jsonl`, following the
[existing annotation conventions](../evaluation/README.md). Keep each source
intent and text unchanged. Record the actual annotator and set `label_status` to
`human_reviewed` only after a person has reviewed the labels.

The existing `data/evaluation/entities_validation.jsonl` also needs 100 reviewed
entity annotations before prompt scoring. Candidate generation can start once
the ten seeds are ready; it does not require the validation labels yet.

AI-assisted drafts now exist for all 110 seed/validation records. Use
[ANNOTATION_REVIEW.md](ANNOTATION_REVIEW.md) for the row-by-row review sheet,
ambiguous decisions, and draft coverage. `annotation_draft_manifest.json` records
file hashes and authorship; each JSONL record retains its original draft labels
in `annotation_provenance`. Keep this provenance after human correction/review.
`annotator` remains null and `label_status` remains `ai_draft` until a person
reviews that individual record. The preflight still rejects these drafts.
The held-out test annotations remain untouched. These are annotations of existing
utterances, not newly generated synthetic utterances or completed quality results.

```powershell
python scripts/auto_label.py check
```

This preflight uses no model and returns exit code 2 while human inputs are
incomplete. Actual experiment commands also stop before loading model weights
when their required human inputs are missing. Do not convert extractor guesses
or the assistant-authored development examples into supposedly human gold.

To create new seed templates elsewhere:

```powershell
python scripts/prepare_autolabelling.py --output-dir data/auto_labelling/new_seeds
```

Existing templates are never overwritten. The ten seeds must belong to the
training split; scoring annotations must belong to validation. The original
test split participates only in split-integrity checks and hashes: its examples
are never given to candidate generation, selection or training annotation.

## Separate model environment

The chatbot currently uses Transformers 4.x. Qwen3.5 has native support in
[Transformers 5.3](https://huggingface.co/docs/transformers/v5.3.0/model_doc/qwen3_5).
Use a separate Python environment or Colab runtime so upgrading the research
stack does not affect DistilBERT training/application dependencies.

```powershell
py -3.12 -m venv .venv-llm
.\.venv-llm\Scripts\Activate.ps1
python -m pip install -r requirements-llm-4bit.txt
```

For CPU/unquantised experiments, install `requirements-llm.txt` instead. Colab
can use the same requirements in a GPU runtime. Choose the appropriate CUDA
PyTorch installation for that runtime. This workflow requires CUDA for its
4-bit mode and fails clearly if CUDA or bitsandbytes is unavailable.

Place an official [Qwen3.5-9B checkpoint](https://huggingface.co/Qwen/Qwen3.5-9B)
under a local directory such as `models/qwen3.5-9b/`, including its tokenizer and
safetensors shards. Downloading weights is a separate setup step; the experiment
does not download models or call a hosted model. Pin a Hub revision when obtaining
the checkpoint and retain it for reproduction; every local config/tokenizer and
weight file is fingerprinted during a run.

For the published full Qwen3.5 config, the runner uses the native
`Qwen3_5ForConditionalGeneration` class with text inputs only. It also accepts
native text-only checkpoints through `AutoModelForCausalLM`. It requires a chat
template and does not execute checkpoint-provided remote Python code. This is
not a GGUF/Ollama/API adapter. The full Qwen checkpoint's vision weights may also
be loaded; no vision inputs are used in this text experiment.

NF4, double quantisation and CUDA BF16/FP16 compute follow the
[Transformers bitsandbytes interface](https://huggingface.co/docs/transformers/main/quantization/bitsandbytes).
Without 4-bit, CPU uses FP32. Checkpoint hashing/model loading can take time and
are outside generation timing. No large model is silently substituted when a
requested checkpoint, dependency or GPU is unavailable.

## Run the experiment

Run these commands with the research environment's Python. The same model path,
quantisation and token settings must be used for all three stages. Example paths
are relative to the repository root and also work in a Colab checkout.

```powershell
python scripts/auto_label.py propose --model-path models/qwen3.5-9b --device cuda --quantization 4bit --candidate-count 4 --run-dir reports/auto_labelling/propose

python scripts/auto_label.py score --model-path models/qwen3.5-9b --device cuda --quantization 4bit --candidates reports/auto_labelling/propose/candidates.jsonl --run-dir reports/auto_labelling/score

python scripts/auto_label.py label --model-path models/qwen3.5-9b --device cuda --quantization 4bit --selection reports/auto_labelling/score/selection.json --run-dir reports/auto_labelling/train_labels
```

Each command accepts `--seeds`; scoring/labelling also accept `--validation`.
Use `--source-dir` only for a separately documented experiment on other split
files. Default generation budgets are 8,192 input tokens and 512 new tokens.
The full seed/query prompt is rejected if it cannot fit; it is never silently
truncated. Thinking is disabled through the chat-template argument. Any emitted
reasoning/prose is rejected by the output parser.

Candidate instructions use sampling with temperature 0.7 and top-p 0.9;
annotation uses greedy decoding. Seeds and per-request random seeds are logged.
Fixed seeds do not guarantee bit-identical results across hardware/library
versions. Duplicate candidate instructions are reported rather than counted as
independent candidates. The initial baseline in `prompts/auto_labelling/baseline.txt`
is an assistant-authored starting template: the team should review/edit and
freeze it before describing it as the team's manually written comparison prompt.

The stages use new run directories. To continue the exact interrupted experiment,
repeat the original command with `--resume`. To change a model, seed file, prompt,
generation budget or experiment code, choose a new run directory. Prompt selection
also checks that its candidates came from the same model/settings, seed file and
contract. Selected prompts cannot be reused after changing those inputs without
rescoring. Do not alter the run cache to force a resume.
Input files and experiment code are checked again before final export; editing
them while a long generation job runs prevents publication of a misleading
selection or label export. Generation caches remain available for investigation.

## Output validation and measurements

Annotation output must be exactly `{"intent": ..., "entities": ...}` with one
of the six intents and all eight entity fields containing lists of strings.
Unknown/missing fields, scalar values, empty/duplicate entity strings, duplicate
JSON keys, NaN, surrounding prose and incomplete token-budget outputs are
rejected. A single JSON Markdown fence is tolerated. There is no extraction of
an arbitrary JSON substring from malformed prose and no silent semantic repair.

Default maximum attempts are two (configurable from one to three). A format
retry receives only its own output and validation error, never the expected
validation label. All attempts are logged. Context-limit failures are retained
as rejected records; model/configuration/OOM failures abort for investigation
rather than being misreported as a full dataset of bad annotations.

Every candidate and the baseline is scored on the same 100 validation records.
Primary ranking uses exact canonical-value entity micro-F1 across the eight
proposal slots. Invalid responses remain in the denominator as missed reference
entities and incorrect intents. Invalid responses also fail utterance exact
match, including no-entity utterances. F1 alone does not penalise an invalid
response to an empty-entity reference; validity, exact match and intent agreement
must therefore be inspected alongside F1. Macro/per-slot scores, support and raw
predictions are saved. These are **validation selection scores**, not unbiased
held-out test performance.

`generation_timing` measures individual `model.generate()` attempts, including
GPU synchronisation; retries appear as additional attempts. It excludes prompt
formatting, tokenisation, input transfer, parsing and checkpoint loading. It is
not an end-to-end latency comparison with the chatbot; the later LoRA comparison
needs a matched timing protocol.

`selection.json` records the baseline, best APE candidate, full ranking and
selected prompt. The auto-labelling entity threshold is 0.80; this is separate
from the main extractor's proposed 0.85 target. A run may still export machine
labels if a target is missed, so failed experiments can be analysed honestly.
It does not automatically start LoRA training or approve label quality.

Training output includes:

- `machine_labels.jsonl`: accepted labels with `label_status: machine_generated`,
  original `source_intent`, model-predicted `intent`, eight entity fields,
  seed-example flag and provenance. Model intent disagreements are retained;
  source labels do not replace model predictions.
- `rejected.jsonl`: invalid rows and generation/validation errors.
- `summary.json` / `summary.md`: accepted/rejected counts, validity, intent
  agreement over **all requested training rows** and separately over non-seed
  rows. Invalid rows count as intent disagreements. The complete original split
  has 960 rows; 950 are outside the ten seed examples.

The training intent-agreement target is 0.85. Training entity accuracy remains
unknown without independent reference labels; schema validity is not semantic
accuracy. Human entity reference files are never overwritten and do not accept
these machine-generated records as reviewed gold. Review the measured quality
and errors before the later LoRA experiment.

Run artifacts, caches and machine labels under `reports/auto_labelling/` are
ignored by Git. Seed templates, baseline and code are tracked. Preserve selected
research results deliberately with the final report, including source hashes,
the manifest, prompt comparison and failure analysis.

## Infrastructure verification versus experiment results

```powershell
python -m unittest discover -s tests -p test_auto_labelling.py -v
```

These tests use explicitly synthetic fixture engines/reference records to verify
schema checking, no validation-answer leakage, split fences, prompt ranking,
resume, interruption recovery and train-only export. Fixture machine labels have
status `machine_generated_fixture` and `research_run: false`; their scores must
never be reported as Qwen performance. A separate local smoke check can verify
actual loading/generation using a tiny random checkpoint, which likewise says
nothing about Qwen or labelling quality. The real experiment needs the reviewed
human inputs, an actual checkpoint and the intended GPU environment.
