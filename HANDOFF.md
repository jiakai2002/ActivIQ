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
  human annotations exist. Development examples and blank validation/test
  annotation templates live in `data/evaluation/`; read its README before scoring.
  Draft/development labels must not be presented as held-out results.
- Medical rules now handle bounded clause-local negation, spelling variants and
  explicit medical concerns. `src/scope.py` supplies independent domain evidence
  and unsupported-task checks so a confident model label cannot invent a task.
  The unchanged original safety suite and 52 additional development cases are
  both used for regression checks. Complex/unseen language still requires review.
- Nutrition preparation now retains micronutrients and source units. The tracked
  nutrition JSON was rebuilt from official SR Legacy CSVs and contains 7,793
  foods, 149 distinct nutrient fields and 644,125 nutrient values.
- The internal pipeline class is still named `FitBuddyPipeline` for import/API
  stability. Do not rename it casually without checking all callers.
- The last committed change is the branding update. The working tree should be
  clean before starting new work.

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
scripts/prepare_entity_annotations.py  Blank human annotation templates
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

1. Have teammates annotate and review entity validation/test sets; use validation
   for rule/prompt development and keep the test set frozen for final scoring.
   Address safety failures found by the development suite without removing the
   failed cases. Collect independent human-authored task/safety test scenarios.
2. Keep the project documentation aligned with
   `CS425_G1T3_Proposal_Submission.pdf` as requirements evolve.
3. Improve the UI with clearer loading/error states and a small example-prompt
   panel.
4. Re-run the intent evaluation after any classifier, data, or preprocessing
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
