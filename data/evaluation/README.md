# Evaluation protocol

This directory separates development diagnostics from the human-labelled test
evidence needed by the proposal. Benchmark expectations must be written before
viewing the system's predictions. Keep failed cases in the suite and report them.

## Inputs

| File | Purpose | Initial status |
| --- | --- | --- |
| `entities_validation.jsonl` | 100 sampled utterances from the original validation split | AI draft annotations, now human reviewed (AI-assisted); ready for APE prompt selection |
| `entities_test.jsonl` | All 120 utterances from the original test split | Unlabelled; keep held out from rule/prompt tuning |
| `entities_dev.jsonl` | 20 assistant-authored entity examples, including known challenges | Draft development expectations, not human gold |
| `conversations_dev.jsonl` | 20 observable task scenarios, including multi-turn refinement | Draft development suite, not held-out evaluation |
| `safety_dev.jsonl` | 16 medical, 10 unrelated and 8 ordinary/negated fitness requests | Draft development suite, not a safety guarantee |
| `safety_hardening_dev.jsonl` | 20 medical, 16 unrelated and 16 ordinary/negated fitness requests, specified before hardening | Additional development/regression cases, not held-out evidence |
| `annotation_manifest.json` | Original split hashes, sampling seed and selected counts | Provenance for the blank templates |

Source row numbers are one-based data-row numbers, excluding the CSV header.
Validation sampling uses seed 42. No entity labels were generated from the
extractor or trained model. The existing intent label is retained as source
context, not inferred by this workflow.

To create another set of blank sheets, use a new output directory:

```powershell
python scripts/prepare_entity_annotations.py --output-dir data/evaluation/new_annotations
```

The script refuses to overwrite existing annotation files.

## Human entity annotation

For validation, review/correct the existing AI drafts using the
[review sheet](../auto_labelling/ANNOTATION_REVIEW.md). Preserve their AI
provenance after review and disclose AI assistance in the report. The original
test templates remain unlabelled: independently annotate them without viewing
extractor predictions or AI draft answers. AI drafts are excluded by default;
`--allow-draft` permits provisional diagnostics only (see script help).

Replace `entities: null` in each unlabelled annotation record with a dictionary explicitly
containing all eight proposal slots, using lists of strings. Use `[]` for an
absent slot. Mark the record `label_status: "human_reviewed"` and enter the
responsible person's name in `annotator` only after a person has labelled and
reviewed it. A second reviewer should resolve ambiguous examples before freezing
the test file. Do not approve the model's own guesses as reference labels.

For example, for `How much vitamin K is in 200 g kale raw?`:

```json
{
  "exercise": [],
  "body_part": [],
  "equipment": [],
  "goal": [],
  "level": [],
  "duration": [],
  "food": ["kale raw"],
  "nutrient": ["Vitamin K (phylloquinone)"]
}
```

Annotation conventions:

- Exercise: lowercase exercise name or explicit family, with common forms
  normalised (`squats` -> `squat`, `push-ups` -> `push up`). Preserve a named
  variant such as `cossack squat`; do not label it as a generic squat.
- Body part: broad group (`legs`, `arms`, `core`, `back`, `chest`, `shoulders`,
  `glutes`) or a more specific named muscle (`quadriceps` for `quads`, `lats`,
  `lower back`, etc.). Label what the user requests, not every muscle an exercise
  might use.
- Equipment: canonical names such as `bodyweight`, `dumbbell`, `barbell`,
  `resistance band`, `kettlebell`, `cable` or `machine`. `No equipment` means
  `bodyweight`; `no dumbbells` does not mean that dumbbells are available.
- Goal: `muscle gain`, `fat loss`, `strength`, `endurance` or `flexibility`.
- Level: `beginner`, `intermediate` or `expert` (`advanced` -> `expert`). Do not
  label a level that is explicitly negated.
- Duration: lowercased session-time phrase. Keep explicit units/spelling, e.g.
  `30 minutes` or `1 hour`; use separate entries for `1 hour 30 minutes`. Do not
  confuse workout days or a programme lasting weeks with session time. If an
  implicit duration is annotated, use a written convention such as `half an
  hour` -> `30 minutes` consistently across validation and test.
- Food: food phrase in the user's word order, with question framing, nutrient
  names and quantities removed; retain preparation/cut descriptors. Annotate
  multiple requested foods separately. Do not pick a USDA record on the user's
  behalf when the food is ambiguous.
- Nutrient: USDA name, e.g. `Protein`, `Energy`, `Calcium, Ca`, or
  `Vitamin K (phylloquinone)`. Record dietary facts requested, not mentions of
  `fat loss` as a workout goal.

`days`, `quantity_g` and `serving` may also be annotated, but are not included in
the proposal's eight-slot entity F1. Their behaviour is checked by task scenarios.
These labels describe independent utterances: do not inherit an entity from a
previous example. An unknown exercise can still be an entity even if the KB has
no instructions for it.

Primary scoring is exact canonical-value **micro-F1**, using per-utterance,
per-slot sets. Case/whitespace and duplicate labels are normalised. Extra entities
are false positives; missed entities are false negatives; an incorrect value
contributes both. This is not character-span NER F1. Macro-F1, per-slot metrics,
gold support and whole-utterance exact match are also reported. A slot with no
gold or predicted entities has undefined F1, not a perfect score.

The entity target is not marked verified unless all records are reviewed test
labels, all eight entity types have positive gold support and micro-F1 >= 0.85.
Partial labels can be inspected, but cannot establish the target. If the original
120 queries do not cover a slot, disclose the gap and collect an independently
labelled supplementary test set; do not silently drop that slot.

## Running the evaluations

```powershell
# Default: real trained classifier, all four components
python scripts/evaluate_system.py

# Human-labelled validation or test entity data; no trained classifier needed
python scripts/evaluate_system.py --component entities --entity-data data/evaluation/entities_validation.jsonl
python scripts/evaluate_system.py --component entities --entity-data data/evaluation/entities_test.jsonl

# Provisional diagnostics on assistant-authored entity examples
python scripts/evaluate_system.py --component entities --entity-data data/evaluation/entities_dev.jsonl --allow-draft --output-dir reports/evaluation/entity_dev

# Individual components with the trained classifier
python scripts/evaluate_system.py --component conversations
python scripts/evaluate_system.py --component safety
python scripts/evaluate_system.py --component safety --safety-data data/evaluation/safety_hardening_dev.jsonl --output-dir reports/evaluation/safety_hardening/regression
python scripts/evaluate_system.py --component latency --latency-repeats 3 --warmup 12
```

Each run writes `system_evaluation.json` and a readable `system_evaluation.md` to
the selected directory. Use distinct `--output-dir` values to preserve runs;
otherwise the previous files are replaced. JSON includes full predictions,
expected outcomes, responses and failures. Markdown includes conversation
transcripts and safety outcomes for qualitative analysis. Default run artifacts
under `reports/evaluation/` are ignored by Git; benchmark inputs are tracked.
Select the final results deliberately for your submission.

## Task and safety success

Each scenario starts with a fresh profile. A scenario passes only if **every
turn** satisfies its predeclared outcomes. The main >=80% task-success target
uses only multi-turn scenarios; overall scenario and turn rates are separately
reported. Single-turn successes cannot hide failed multi-turn tasks.

Plan checks parse the returned exercise names and check their actual database
equipment, difficulty and muscles, day count, duplicates and estimated time
budget. They do not accept a plan's introductory claim as proof. These checks do
not measure physiological suitability or actual workout duration. Other checks
cover answers, clarification, slot retention and task transitions. Response-format
changes may require updating the plan parser; review those changes explicitly.

Safety runs the complete chatbot and also records the keyword layer's route.
It measures strict fixed medical refusals, fitness-scope responses to unrelated
questions, and inappropriate refusals of ordinary/negated fitness requests.
The 100% handling target applies to the medical and unrelated cases; both types
must be present. Ordinary fitness false refusals are reported separately.
These tests measure expected routing, not a comprehensive medical safety audit.

Assistant-authored development suites remain provisional even when they pass.
For a defensible final task/safety benchmark, have teammates write/review fresh
scenarios independently, freeze them before evaluation, and record `split:
"test"`, `label_status: "human_reviewed"` and the actual annotator. Do not simply
rename an already-used development suite to claim it was held out. The software
records declared provenance; it cannot verify that a human review occurred.

## CPU timing and reproducibility

Latency uses all 120 original intent-test queries, balanced at 20 per intent,
three measured repeats and 12 excluded warm-up queries by default. State resets
happen outside the timer. Measurements cover wall-clock `respond()` calls,
including classification, extraction, retrieval and generation; they exclude
Streamlit/browser rendering. Safety shortcuts and classifier-path timings are
reported separately so fixed refusals cannot hide slower model inference.
Classifier-use metadata distinguishes an early refusal from a scope rejection
that happened after inference; an `out_of_scope` route alone does not imply that
the model was skipped. Other control responses are recorded separately.

Reports include mean, median, p95, p99, maximum and fraction below one second,
plus per-intent breakdowns and every sample. The <1-second target is checked
strictly using the maximum observed measured response, not only the average.
Warm-up and model/KB constructor time are separate. Constructor time excludes
Python interpreter startup and imports that precede the timer; it is not a fresh
machine cold-start benchmark. Latency is specific to the recorded hardware and
settings, not a guarantee for all laptops or request lengths.

Metadata captures Python/package versions, processor, logical CPUs, actual torch
thread counts, CPU device, model/tokenizer hashes, application-source hashes,
dataset hashes and Git revision/dirty status. Keep this information with the
report. Benchmark sequentially without other heavy jobs for comparable timing.
Do not adjust thread counts or optimise the system based on final test failures
and then continue describing that test set as untouched.
