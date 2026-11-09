# ActivIQ

ActivIQ is an offline personal fitness chatbot based on the project proposal.
It classifies fitness questions, extracts fitness entities, maintains a small
user profile, retrieves local fitness data, and responds with controlled
templates.

## App overview

ActivIQ is a local-first fitness assistant for workout planning, exercise
guidance, nutrition lookup, and simple workout check-ins. It uses a Streamlit
chat interface and keeps conversation preferences in the current session.

The app can:

- Create personalized 1–7 day workout plans
- Explain exercises using local exercise data and step-by-step instructions
- Look up calories, macronutrients, vitamins and minerals where source values exist
- Remember preferences such as level, equipment, goal, and workout duration
- Handle follow-up questions using the current session profile
- Respond safely to medical and unsupported requests

## Task behaviour and limits

Workout requests accept numeric or written day counts from 1 to 7 (including
`one-day`). Muscle groups such as legs, arms, back and core map to the exercise
database's individual muscles. Specific requests such as quads remain specific.
Equipment choices and difficulty are preserved even when only a few matching
exercises exist: the bot returns fewer exercises or asks which constraint to
change, rather than silently substituting other equipment or levels.

Plans use goal-specific sets, repetitions and rest rules. A session duration
sets an estimated time budget, including a five-minute warm-up and transitions;
up to six distinct exercises are selected per day. Exercises may repeat across
days when needed, with an explicit note. Bodyweight is the stated default when
equipment is omitted. These are deterministic application heuristics, not a
validated coaching model, and estimated times need not fill the entire budget.

Nutrition requests separate the food, nutrient and serving weight. Ambiguous
foods prompt for a preparation or exact description. Gram, kilogram and ounce
weights scale the database's values per 100 g; household measures such as cups
prompt for a gram weight. Missing nutrients are reported as unavailable, never
replaced with unrelated macro values or inferred from another food.

The nutrition JSON contains 7,793 foods and 149 distinct nutrient fields from
the official SR Legacy source, including vitamins and minerals. Source units
are retained; missing values remain unavailable rather than being inferred.
The preparation script writes one food per line and uses JSON `null` for missing
portion fields. The runtime also accepts the older macro-only JSON format.

Conversation preferences persist within the session. Short follow-ups such as
`Make it 5 days`, `What about chest?`, `And vitamin K?`, or `200g` reuse the
relevant task context. Changing the muscle clears the previous exercise filter;
changing tasks does not carry food or exercise slots into the new task.

Run the task regression suite without a trained classifier or Streamlit server:

```powershell
python -m unittest discover -s tests -v
```

These tests use a controlled classifier and local fixtures to verify routing,
extraction, retrieval, planning, nutrition and conversation behaviour. They do
not measure trained-model accuracy, entity F1, or full-system latency. Normal
application startup still requires a trained model in `models/intent_classifier/`.

Responses are grounded in local datasets and controlled application logic. The
app does not call an external LLM API or provide medical advice.

Supported request types include workout plans, exercise instructions, nutrition
information, workout-feeling check-ins, general fitness conversation, and
out-of-scope requests.

## Model results

The current intent-classification model was evaluated on the untouched test
split with six supported intent categories:

| Metric | Result |
| --- | ---: |
| Accuracy | 91.67% |
| Macro-F1 | 91.62% |

The latest training/evaluation run reported these correct predictions per class:

| Intent | Correct / test utterances |
| --- | ---: |
| find_exercise | 17 / 20 |
| general_chat | 16 / 20 |
| generate_plan | 20 / 20 |
| get_nutrition_info | 19 / 20 |
| log_feeling | 20 / 20 |
| out_of_scope | 18 / 20 |

Evaluation can be reproduced after preparing the local datasets and trained
model with:

```powershell
python scripts/evaluate_intent.py
```

## System evaluation

Run entity, multi-turn task, safety and CPU latency evaluations with:

```powershell
python scripts/evaluate_system.py
```

The trained local model is required for conversation, safety and latency runs.
Each run saves a JSON report and a readable Markdown report with conversation
transcripts under `reports/evaluation/`. This machine-specific output directory
is ignored by Git. Input, model and code hashes, package versions, hardware and
thread settings are recorded so results can be reproduced.

The supplied suites include 20 development conversation scenarios and 34 safety
cases. Scenario success requires every turn to pass; the proposal's task-success
threshold is checked only over multi-turn scenarios. Plans are checked against
actual exercise database properties. Safety reports medical misses, unrelated
requests and false refusals separately. These assistant-authored development
examples are not an independent held-out benchmark, even when all cases pass.

Entity scoring needs human labels. Blank annotation templates contain 100
validation utterances and all 120 original test utterances. Unlabelled data is
reported as pending, rather than used to invent an F1 result. A separate set of
20 draft entity examples can be scored provisionally with `--allow-draft`.

```powershell
python scripts/evaluate_system.py --component entities --entity-data data/evaluation/entities_dev.jsonl --allow-draft --output-dir reports/evaluation/entity_dev
```

Latency uses 120 queries, three measured repeats, excluded warm-up and separate
startup reporting by default. Median, p95, p99, maximum and per-intent results
are saved. The sub-second target uses the maximum measured response, including
all pipeline work but excluding Streamlit/browser rendering.

See [the evaluation and annotation protocol](data/evaluation/README.md) for label
conventions, component commands, benchmark limitations and human review steps.

## Local auto-labelling and APE infrastructure

The separate research workflow prepares ten training-seed annotations, generates
candidate labelling instructions with a local model, compares them and a baseline
against 100 reviewed validation examples, and labels the original training split
with the selected prompt. It uses direct local Transformers inference, including
optional CUDA NF4 4-bit loading, with no LLM API/server.

```powershell
python scripts/auto_label.py check
```

Ten seed records are in `data/auto_labelling/seeds.jsonl`. These seeds and the
100 validation entity annotations started as AI drafts and have been reviewed by
a team member (`label_status: human_reviewed`); disclose the AI assistance in the
report. Preflight reports missing labels without loading a model. The baseline prompt is an assistant-authored starting
template for team review, not an already-validated manual prompt.

`propose`, `score` and `label` subcommands provide strict JSON/schema validation,
bounded format retries, raw attempt logs, input/model/code fingerprints, atomic
per-query checkpoints and explicit resume. Scoring keeps invalid generations in
the measurements. Training export preserves original intents alongside model
predictions and marks accepted output as machine-generated; it never overwrites
human gold or annotates validation/test data as training data.

Qwen3.5 uses the separate `requirements-llm.txt` / `requirements-llm-4bit.txt`
environment; the baseline application dependency file is retained. Local model
weights must be supplied explicitly. No Qwen quality results or LoRA training
are implied by the infrastructure tests. Read the
[setup, experiment and provenance guide](data/auto_labelling/README.md) before
running the experiment.

## Data sources

ActivIQ uses the following public datasets:

- **Intent classification:** [Fitness Intent Classification](https://huggingface.co/datasets/harshmakwana/fitness-intent), licensed as MIT by the source. The original train, validation, and test splits are preserved without augmentation.
- **Exercise knowledge base:** [Free Exercise DB](https://github.com/yuhonas/free-exercise-db), licensed under the Unlicense. Exercise names, equipment, muscle groups, and instructions are normalized for local lookup.
- **Primary nutrition data:** [USDA FoodData Central SR Legacy](https://fdc.nal.usda.gov/download-datasets/), April 2018 final SR Legacy release. Nutrition values are normalized into `data/processed/nutrition.json`.
- **Secondary nutrition data:** USDA [Food and Nutrient Database for Dietary Studies (FNDDS) 2021–2023](https://fdc.nal.usda.gov/download-datasets/), supported separately by preparation code for comparison or future integration.

Dataset provenance and preparation details are documented in
[`data/SOURCES.md`](data/SOURCES.md). Raw source archives remain excluded from
GitHub; the prepared datasets used by the app are tracked in
`data/processed/`.

## Getting started

ActivIQ currently targets Python 3.11–3.13. Create a virtual environment and
install the dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Prepare local raw data with:

```powershell
python scripts/prepare_data.py
```

Raw datasets belong under `data/raw/`. The preparation script creates cleaned
files under `data/processed/` and reports missing inputs without silently
inventing or augmenting data. Nutrition uses the complete local USDA SR Legacy
release as its primary dataset.

See `CS425_G1T3_Proposal_Submission.pdf` for the project requirements and evaluation targets.

Run the app with:

```powershell
streamlit run app.py
```

ActivIQ continues to run with empty local datasets and reports a useful
fallback instead of fabricating exercise or nutrition facts.

## Architecture

```text
User message
    v
Safety routing
    v
DistilBERT intent classifier
    v
Rule-based entity extractor
    v
Dialogue profile/state
    v
Local exercise or nutrition lookup
    v
Template response
```

The intent model uses `distilbert-base-uncased`. Entity extraction uses spaCy
phrase rules when the native spaCy package is available and a transparent
phrase/regex fallback otherwise. The chatbot stores only session-level profile
information such as goal, level, equipment, duration, and the last intent.

## Repository structure

```text
fitbuddy/
├── data/
│   ├── SOURCES.md
│   ├── raw/                    # Downloaded source data; ignored by Git
│   ├── processed/              # Prepared datasets tracked by Git
│   └── user_profiles/
├── models/
│   └── intent_classifier/      # Local trained model; ignored by Git
├── scripts/
│   ├── prepare_data.py
│   ├── train_intent.py
│   └── evaluate_intent.py
├── templates/
│   └── responses.json
├── src/
│   ├── config.py
│   ├── intent_classifier.py
│   ├── entity_extractor.py
│   ├── safety.py
│   ├── dialogue_manager.py
│   ├── knowledge_base.py
│   ├── planner.py
│   ├── response_generator.py
│   └── pipeline.py
├── app.py
├── CS425_G1T3_Proposal_Submission.pdf
├── project_guidelines.pdf
├── requirements.txt
└── README.md
```

## Environment setup

Use Python 3.12. Python 3.14 is not currently assumed for the scientific
Python stack on Windows.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run commands through the environment's Python
directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Data preparation

Raw files are intentionally separate from processed data. Place the following
sources under `data/raw/`:

```text
data/raw/intent_dataset/{train,validation,test}.parquet
data/raw/exercise_db/exercises.json
data/raw/nutrition/sr-legacy/.../food.csv
data/raw/nutrition/sr-legacy/.../food_nutrient.csv
data/raw/nutrition/sr-legacy/.../nutrient.csv
data/raw/nutrition/sr-legacy/.../food_category.csv
data/raw/nutrition/sr-legacy/.../food_portion.csv
```

Run:

```powershell
python scripts/prepare_data.py
```

The script validates labels, removes duplicate rows within a split, checks for
cross-split leakage, normalizes exercise data, and creates the primary SR
Legacy nutrition JSON. It does not augment or synthesize data.

## Training and evaluation

```powershell
python scripts/train_intent.py
python scripts/evaluate_intent.py
```

Training uses a maximum sequence length of 64 tokens, learning rate `2e-5`,
batch size 16, and three epochs. The trained model is saved under
`models/intent_classifier/`; model files are ignored by Git and can be
recreated with the training script.

## Safety and data policy

Medical routing uses explicit phrase patterns for injuries, symptoms and medical
requests, including plurals and a small documented set of spelling variants.
Clear denials are interpreted within their clause: `no pain` can proceed, while
`no pain, but my arm is numb` still receives the fixed medical response.
Uncertainty (`not sure why it hurts`) and double negation (`not pain-free`) are
not treated as denials. `Medicine ball` and limited scheduling idioms are not
treated as medical concerns. The rules are bounded language heuristics, not a
diagnostic or triage model; uncommon wording and complex negation may be missed.

Explicit requests for software, creative writing, finance and other unsupported
tasks receive a fixed fitness-scope response, even when they mention workouts.
Background context such as bad weather can accompany a valid indoor workout
request. A second scope check requires fitness language, recognised knowledge-base
content, a supported social/feeling message, or a bounded profile/follow-up
fragment. An arbitrarily confident model label cannot supply that evidence.
Unclear short fragments and low-confidence fitness messages receive clarification
without updating the profile. Workout generation also requires evidence that a
plan was requested. Routing decisions expose reason codes and whether inference
actually ran for evaluation; they do not add implementation text to chat replies.

Inference truncates to the same 64-token limit used during training. Medical and
explicit unsupported-task checks inspect the full message before inference.
Both the trained checkpoint and the fixed medical disclaimer remain in use.
ActivIQ is not a doctor, diagnostic tool, or replacement for a qualified trainer.

The original 34-case development safety suite is retained. An additional 52-case
regression suite covers mixed clauses, negation, spelling, unsupported tasks with
fitness words and ambiguous topic overlap:

```powershell
python scripts/evaluate_system.py --component safety --safety-data data/evaluation/safety_hardening_dev.jsonl --output-dir reports/evaluation/safety_hardening/regression
```

These development cases guide implementation and regression testing; results on
them do not establish safety for all queries or an independent held-out score.

No intent paraphrase augmentation is currently used. SR Legacy is the primary
nutrition lookup source, while FNDDS remains separate because the datasets use
different descriptions and serving conventions. Raw source archives and
generated model artifacts are excluded from Git. Dataset provenance is recorded
in [data/SOURCES.md](data/SOURCES.md).
