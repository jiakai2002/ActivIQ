# ActivIQ Team Handoff

This document is the starting point for a teammate or AI assistant continuing
work on ActivIQ. Read it before changing code, then inspect the relevant files
and current Git status.

## Project in one sentence

ActivIQ is an offline, deterministic fitness chatbot that classifies user
messages, extracts fitness entities, keeps a session profile, retrieves local
exercise and nutrition data, and renders controlled responses in Streamlit.

Repository: https://github.com/jiakai2002/ActivIQ.git  
Primary branch: `main`

## Current state

- Phase 1 data preparation is complete.
- Phase 2 baseline intent classification, entity extraction, safety routing,
  and dialogue state are complete.
- Phase 3 knowledge-base retrieval, response templates, configurable workout
  plans, pipeline integration, and the Streamlit UI are complete.
- The app branding is `ActivIQ`.
- Workout plans support 1–7 days and up to six distinct exercises per day,
  constrained by equipment, difficulty, focus, goal and estimated session time.
- Task regression tests live in `tests/test_task_correctness.py` and run with
  `python -m unittest discover -s tests -v` without trained model weights.
- System evaluation is available through `python scripts/evaluate_system.py`:
  real-model task/safety transcripts and CPU timings, plus entity metrics once
  human annotations exist. Development examples and the human-reviewed entity
  annotations live in `data/evaluation/`; read its README before scoring.
  Draft/development labels must not be presented as held-out results.
- Medical rules now handle bounded clause-local negation, spelling variants and
  explicit medical concerns. `src/scope.py` supplies independent domain evidence
  and unsupported-task checks so a confident model label cannot invent a task.
  The unchanged original safety suite and 52 additional development cases are
  both used for regression checks. Complex/unseen language still requires review.
- Auto-labelling/APE and LoRA experiment (proposal section 4.6) has been **run on
  Colab and the results are committed** under `ActivIQ_runs/`. See "Experiment
  results" below. The ten training seeds, 100 validation records and all 120 test
  records were AI-drafted, then human reviewed (`label_status: human_reviewed`).
  Disclose the AI assistance in the report.
- Nutrition preparation now retains micronutrients and source units. The tracked
  nutrition JSON was rebuilt from official SR Legacy CSVs and contains 7,793
  foods, 149 distinct nutrient fields and 644,125 nutrient values.
- The internal pipeline class is still named `FitBuddyPipeline` for import/API
  stability. Do not rename it casually without checking all callers.
- The last committed change is the branding update. The working tree should be
  clean before starting new work.

## Experiment results (captured)

Everything below was produced by `notebooks/activiq_end_to_end.ipynb` on a Colab
A100-SXM4-40GB (about 117 minutes in total; 9B in bf16, 2B in bf16). Raw outputs
are in `ActivIQ_runs/`. Pinned model revisions are in `ActivIQ_runs/model_revisions.json`
(Qwen3.5-9B `c202236...`, Qwen3.5-2B `15852e8...`).

### Scorecard against the proposal targets

| Target (proposal section 5) | Result | Met? |
| --- | --- | --- |
| Intent accuracy and macro-F1 >= 0.90 | 0.917 / 0.916 (DistilBERT, test) | Yes |
| Entity F1 >= 0.85 (spaCy rules) | **0.455** (test, human-reviewed labels) | **No** |
| Auto-labelling entity F1 >= 0.80 (validation) | 0.700 (best prompt `ape-002`) | No |
| Auto-labelling intent agreement >= 0.85 | 0.904 on 960 training rows | Yes |
| LoRA vs DistilBERT + spaCy comparison | Done, table below | Report only |
| End-to-end task success >= 80%, safety 100%, latency < 1 s | Not yet measured on an independent held-out set | Open |

### Test-set comparison (120 utterances, human-reviewed entity labels)

| System | Intent acc | Intent macro-F1 | Entity micro-F1 | Median latency | Invalid outputs |
| --- | ---: | ---: | ---: | ---: | ---: |
| DistilBERT + spaCy | 0.917 | 0.916 | 0.455 | 0.018 s | 0 |
| Qwen3.5-2B + LoRA (machine labels) | 0.917 | 0.919 | 0.571 | 2.9 s | 0 |
| Qwen3.5-9B zero-shot | 0.800 | 0.808 | 0.408 | 4.1 s | 5 |

Per-slot entity F1 (test support in brackets):

| Slot | DistilBERT + spaCy | LoRA 2B | 9B zero-shot |
| --- | ---: | ---: | ---: |
| exercise (25) | 0.34 | 0.63 | 0.49 |
| body_part (8) | 0.77 | 0.56 | 0.71 |
| equipment (4) | 0.00 | 0.50 | 0.00 |
| goal (8) | 0.84 | 0.60 | 0.30 |
| level (2) | 1.00 | 0.50 | 0.00 |
| duration (3) | 0.00 | 0.60 | 0.00 |
| food (17) | 0.12 | 0.88 | 0.65 |
| nutrient (11) | 0.75 | 0.31 | 0.17 |

Reading the table: the LoRA 2B ties DistilBERT on intent and beats the spaCy rules
on entity F1, but is far slower (different hardware, so not a like-for-like timing), so the chatbot keeps DistilBERT + spaCy.
The spaCy extractor misses its 0.85 target by a wide margin, mostly on `food`,
`exercise`, `equipment` and `duration`. Some of this may be label-convention
mismatch (how a phrase is worded) rather than a missing rule. The LoRA comparison
JSON contains aggregate entity scores. Use the system entity evaluation's
per-utterance predictions on validation data to develop extractor changes.

### APE prompt selection (100 validation rows; selection scores, not held-out)

| Prompt | Entity micro-F1 | Valid output | Intent agreement |
| --- | ---: | ---: | ---: |
| ape-002 (selected) | 0.700 | 1.00 | 0.92 |
| ape-003 | 0.671 | 1.00 | 0.93 |
| baseline (assistant-authored prompt) | 0.659 | 1.00 | 0.92 |
| ape-004 | 0.647 | 1.00 | 0.92 |
| ape-001 | 0.643 | 1.00 | 0.92 |

The best APE prompt beat the baseline by about 0.04 F1. Validation has no `duration`
examples, so that slot is not covered by the selection score.

### Auto-labelling and LoRA training

- The selected prompt labelled all 960 training utterances: 960 accepted, 0 rejected,
  intent agreement 0.904 (0.903 excluding the ten seeds). Training entity accuracy is
  unknown because there are no independent human labels for the training split.
- LoRA: Qwen3.5-2B, 960 machine-labelled examples, 3 epochs, batch size 8, learning
  rate 2e-4, rank 16, alpha 32, dropout 0.05, bf16, about 275 s. Mean epoch loss
  0.063, 0.020, 0.0085. The adapter weights (93 MB) are **not in Git**: keep them on
  the team Drive (`ActivIQ_runs/lora/adapter_v1/`).

### Caveats to state in the report

- Seeds, validation and test entity labels were AI-drafted and then human reviewed
  (reviewers recorded in `annotator`). State this once, separately.
- Validation scores are prompt-selection scores. The test set was never used for
  prompt selection, rule tuning or training.
- The test set is small (120 rows; as few as 2 to 4 examples for `level`,
  `equipment` and `duration`), so per-slot scores are noisy.
- The DistilBERT baseline in the Colab run was retrained with `scripts/train_intent.py`
  (one-line argument patch), not loaded from the team's original weights. Its intent
  numbers equal the README's.
- Qwen latency is GPU time on an A100; DistilBERT latency is not comparable hardware.
  Do not present it as a like-for-like speed test.
- The baseline labelling prompt (`prompts/auto_labelling/baseline.txt`) was
  assistant-authored; confirm the team reviewed it before calling it the team's prompt.
- The `note` field inside `lora_comparison.json` still says entity scores are pending;
  that text is stale, as the test labels are human reviewed.

## Start here

```powershell
git clone https://github.com/jiakai2002/ActivIQ.git
cd ActivIQ
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Empty knowledge bases receive controlled fallback responses. The trained intent
model is required for normal application startup; missing-model fallback is not
implemented. To prepare data when raw source files are available:

```powershell
python scripts/prepare_data.py
python scripts/train_intent.py
python scripts/evaluate_intent.py
```

Use Python 3.12 on Windows. Python 3.14 is not currently assumed for the
scientific Python dependencies.

## Architecture and important files

```text
app.py                         Streamlit entry point and session UI
src/pipeline.py                End-to-end routing and response orchestration
src/safety.py                  Medical and out-of-scope fixed responses
src/scope.py                   Supported-domain evidence and task boundaries
src/intent_classifier.py       DistilBERT classifier (requires local model)
src/entity_extractor.py        spaCy rules plus transparent regex fallback
src/dialogue_manager.py        Session profile and slot inheritance
src/knowledge_base.py          Local exercise/nutrition retrieval
src/vocabulary.py             Shared muscle, equipment and exercise vocabulary
src/nutrition.py               Food, nutrient and quantity rules
src/planner.py                 Deterministic 1–7 day workout plans
src/response_generator.py      Controlled response generation
templates/responses.json       Response templates
scripts/prepare_data.py        Raw-to-processed data preparation
scripts/train_intent.py        Local intent-model training
scripts/evaluate_intent.py     Held-out evaluation
scripts/evaluate_system.py     Entity/task/safety/latency reports
scripts/prepare_entity_annotations.py  Blank annotation template generator (templates now filled and reviewed)
scripts/prepare_autolabelling.py  Ten blank, stratified training seed annotations
scripts/auto_label.py          Local candidate generation/validation selection/train labelling
src/auto_labelling/            Contracts, split fences, local inference and resumable workflow
src/evaluation.py              Metrics and observable task outcome checks
data/SOURCES.md                Dataset provenance
```

The runtime flow is:

```text
user message -> safety route -> intent classifier -> entity extraction
-> dialogue profile -> local lookup/planner -> controlled response
```

## Data and model expectations

Raw and generated artifacts are intentionally ignored by Git. Expected raw
inputs include intent parquet files, Free Exercise DB JSON, and USDA SR Legacy
nutrition CSV files under `data/raw/`. Prepared datasets go under
`data/processed/`; the trained classifier goes under
`models/intent_classifier/`.

Do not commit private data, downloaded archives, processed datasets, model
weights, secrets, or virtual-environment files. Keep dataset provenance in
`data/SOURCES.md`.

## Product and safety constraints

- Keep responses deterministic and grounded in local data or templates.
- Do not add an external LLM/API dependency without team agreement.
- Medical requests must continue to receive the fixed safety response; the app
  is not a doctor or diagnostic tool.
- Unsupported topics must remain within the fixed fitness-scope response.
- Preserve the empty-data fallback behavior.
- Prefer small, testable changes that preserve existing imports and session
  behavior.

## Validation checklist

Before committing:

```powershell
python -m compileall -q src app.py scripts
python -m unittest discover -s tests -v
git diff --check
streamlit run app.py
```

For behavior changes, manually check at least these prompts in the UI:

- `Create a 3 day beginner workout plan`
- `Create a 5 day workout plan`
- `How do I do squats?`
- `How much protein is in chicken?`
- `I have chest pain`
- `Tell me about the weather`
- `reset profile`

## Suggested next work

1. **Entity extractor (priority).** spaCy rules score 0.455 test F1 against the 0.85
   target. Inspect per-utterance errors, improve rules using the **validation** set
   only, and keep the test set frozen; a rerun on test after tuning is no longer
   untouched and must be described that way.
2. Collect independent human-authored multi-turn task and safety scenarios, then run
   `scripts/evaluate_system.py` for task success (>= 80%), safety (100%) and CPU
   latency (< 1 s) on the target laptop. Keep failed development cases in the suite.
3. Write the report: scorecard above, the caveats above, the pipeline diagram
   (seeds -> 9B + APE -> machine labels -> 2B LoRA -> compared with DistilBERT + spaCy).
4. Keep the project documentation aligned with
   `CS425_G1T3_Proposal_Submission.pdf` as requirements evolve.
5. Improve the UI with clearer loading/error states and a small example-prompt
   panel.
6. Re-run the intent evaluation after any classifier, data, or preprocessing
   change and record the result in the README.

## Git collaboration instructions

Start each session with:

```powershell
git status --short --branch
git pull --ff-only origin main
```

Use focused commits with descriptive messages. Before pushing, validate the
change, review `git diff`, and confirm that no generated or sensitive files are
included. Push feature branches for larger changes and open a pull request;
small coordinated fixes may be committed directly to `main` if that is the
team convention.

When handing work to another teammate or AI, summarize:

- what changed;
- files touched;
- commands/tests run and their results;
- known limitations or follow-up work; and
- the commit or branch containing the work.
