# ActivIQ

ActivIQ is an offline personal fitness chatbot based on the project proposal.
It classifies fitness questions, extracts fitness entities, maintains a small
user profile, retrieves local fitness data, and responds with controlled
templates.

## Phase 1 setup

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

## Project overview

ActivIQ is designed to be reproducible and safe for student-level delivery.
It does not call an external LLM API, generate unrestricted text, or provide
medical advice.

### Objectives

- Classify six fitness intents with at least 90% accuracy and 85% macro-F1.
- Extract exercises, body parts, equipment, goals, levels, and durations with
  at least 85% F1.
- Personalise follow-up replies using a session profile.
- Respond in under one second on a laptop CPU after the model is loaded.
- Refuse medical and unsupported requests safely.

Supported intents:

```text
generate_plan
find_exercise
get_nutrition_info
log_feeling
general_chat
out_of_scope
```

## Current status

### Phase 1 - completed

- Original intent splits preserved without augmentation: 960 train, 120
  validation, and 120 test utterances.
- Six balanced intent labels with no cross-split utterance leakage.
- 876 normalized exercise records from Free Exercise DB.
- 7,793 USDA FoodData Central SR Legacy records as the primary nutrition
  dataset.
- 5,432 FNDDS records retained separately as a secondary nutrition dataset.

### Phase 2 - completed baseline

- DistilBERT intent classifier trained on CPU.
- Rule-based fitness entity extraction implemented.
- Medical and out-of-scope safety routing implemented.
- Multi-turn dialogue profile implemented.

Held-out test results:

```text
Accuracy: 91.67%
Macro-F1: 91.55%
```

### Phase 3 - completed

- Knowledge-base retrieval.
- Response templates and slot filling.
- Workout planning.
- End-to-end pipeline integration.
- Streamlit interface.

The Phase 3 pipeline is available with `streamlit run app.py`. It routes safety
requests, classifies the message, extracts and inherits session slots, queries
the local exercise/nutrition databases, and renders deterministic controlled
responses. It continues to run with empty local datasets and reports a useful
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
│   ├── processed/              # Prepared local datasets; ignored by Git
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

Medical keywords such as pain, injury, medication, diagnosis, and symptoms are
routed to a fixed refusal message. Unsupported topics receive a fixed
fitness-scope response. ActivIQ is not a doctor, diagnostic tool, or
replacement for a qualified trainer.

No intent paraphrase augmentation is currently used. SR Legacy is the primary
nutrition lookup source, while FNDDS remains separate because the datasets use
different descriptions and serving conventions. Raw source archives and
generated model/data artifacts are excluded from Git. Dataset provenance is
recorded in [data/SOURCES.md](data/SOURCES.md).
