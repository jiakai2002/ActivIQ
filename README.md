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
- Look up calories, protein, carbohydrates, and fat for foods
- Remember preferences such as level, equipment, goal, and workout duration
- Handle follow-up questions using the current session profile
- Respond safely to medical and unsupported requests

Responses are grounded in local datasets and controlled application logic. The
app does not call an external LLM API or provide medical advice.

Supported request types include workout plans, exercise instructions, nutrition
information, workout-feeling check-ins, general fitness conversation, and
out-of-scope requests.

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
