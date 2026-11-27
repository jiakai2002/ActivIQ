# ActivIQ submission guide

Verification date: **27 November 2026**. The application code is runnable with a
local trained intent checkpoint. The repository includes prepared datasets,
reviewed annotations, regression tests and captured research results. Model
weights remain separate, as described below.

## Run from a fresh checkout

Use Python 3.12 (the final checks also passed on Python 3.13.1):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/train_intent.py
streamlit run app.py
```

Training can download `distilbert-base-uncased` and uses only the original
training and validation splits. Alternatively, restore the team's complete
trained directory into `models/intent_classifier/` before launching. Include
its config, weights and tokenizer files. Retraining reproduces the recipe;
exact scores can vary with initialization, package versions and hardware.

Normal inference uses local files only. The chatbot does not need Qwen or an
LLM API. Without a trained intent checkpoint, the UI shows setup instructions.
Prepared intent, exercise and nutrition datasets are already included; running
`scripts/prepare_data.py` is necessary only to rebuild from raw downloads.

The research workflow uses a separate environment and GPU. See
[COLAB_HANDOFF.md](COLAB_HANDOFF.md) and
[the auto-labelling guide](data/auto_labelling/README.md). Installing the research
requirements over the baseline environment is not recommended.

## Final verification results

| Check | Result | Evidence |
| --- | --- | --- |
| Automated regression suite | 139 tests passed | [Test log](reports/submission/unit_tests.txt) |
| Python and notebook syntax | 37 Python files; 57 notebook code cells passed | [Static checks](reports/submission/static_checks.json) |
| Intent evaluation, original 120-query test split | Accuracy 0.9167; macro-F1 0.9162 | [Intent output](reports/submission/intent_evaluation.txt) |
| Revised extractor, original 120-query test split | Entity micro-F1 0.6434 | [System report](reports/submission/system_evaluation.md) |
| Development conversation scenarios | 20/20; multi-turn subset 11/11 | [System report](reports/submission/system_evaluation.md) |
| Original development safety suite | 34/34; zero medical false refusals among ordinary fitness controls | [System report](reports/submission/system_evaluation.md) |
| Additional safety regression suite | 52/52 | [Safety report](reports/submission/safety_hardening/system_evaluation.md) |
| Warm CPU response timing, 360 measurements | Median 0.0433 s; p95 0.1644 s; maximum 0.2833 s | [Raw system report](reports/submission/system_evaluation.json) |
| Streamlit integration smoke test | 9 checks passed, including missing-model setup, real-model chat, follow-ups, safety and reset | [UI checks](reports/submission/ui_smoke.json) |
| Auto-labelling preflight | 10 reviewed seeds and 100 reviewed validation records ready | [Preflight](reports/submission/auto_labelling_preflight.json) |

The original intent splits remain 960/120/120 with no normalized exact text
overlap. All 876 exercises and 7,793 foods load. Frozen supplementary labels
match their manifest hash and have no normalized exact overlap with the source
splits. A basic credential-pattern scan found no matches in the tracked text
files; this is not a full security audit. No tracked file exceeds 50 MiB.

The CPU timing excludes startup, warm-up and Streamlit/browser rendering.
Measured pipeline initialization in this process was **58.1 seconds**, separately
reported. Timing is specific to this machine and environment. Development task
and safety examples were authored with knowledge of the implementation; their
passing scores do not establish independent held-out performance or universal
safety. The original test has already been inspected, so this final rerun is a
known-benchmark regression check.

## Which entity results belong together?

| Corpus / experiment | Earlier extractor | Revised extractor | Use |
| --- | ---: | ---: | --- |
| Original 120 Hugging Face test queries | 0.4552 in the historical Colab comparison | 0.6434 in the final local check | Primary source benchmark; separate run contexts |
| Original validation sample, 100 queries | 0.4696 | 0.8923 | Development diagnostics |
| Supplementary AI-authored, human-reviewed corpus, 100 queries | 0.7059 | 0.8382 | Paired supplementary comparison |

The **85% production entity target remains unmet**. Do not describe 45.52% to
83.82% as a paired improvement: those numbers use different corpora. Intent
macro-F1 and entity micro-F1 measure different tasks and are not interchangeable.

Historical LoRA entity F1 remains **0.5714**, Qwen 9B zero-shot remains **0.4076**,
and the best APE validation prompt remains **0.7000**, below its separate 0.80
target. Training intent agreement was **0.9042**, above its 0.85 target. Production
rule fixes do not alter those machine labels or retrain the adapter. No revised
Qwen/LoRA GPU run was performed during submission cleanup.

Original Hugging Face utterances are used for intent training and the machine
labelling experiment. The LLM labels those existing training utterances; it does
not generate a replacement training corpus. Seed, validation and original-test
entity annotations were AI-drafted and human reviewed. The supplementary corpus
has AI-authored utterances as well as AI-drafted, human-reviewed labels; disclose
both facts. Its reviewed labels were accepted without saved corrections.

## Files and artifacts for reviewers

- Main app and prepared data: `app.py`, `src/`, `templates/`, `data/processed/`.
- Evaluation inputs and annotation provenance: `data/evaluation/`,
  `data/auto_labelling/`.
- Historical Qwen/APE/LoRA outputs and machine training labels: `ActivIQ_runs/`.
- Preserved validation and supplementary evidence: `reports/benchmarks/`.
- Final local checks: `reports/submission/`.
- Proposal and course requirements: `CS425_G1T3_Proposal_Submission.pdf` and
  `project_guidelines.pdf`.

DistilBERT weights, Qwen base checkpoints and the 93 MB LoRA adapter weights are
ignored by Git. Supply the team's checkpoint/adapter artifact separately if
reviewers need the exact trained models, or direct them to the training/Colab
instructions. The tracked adapter configuration alone is insufficient for LoRA
inference. Pinned Qwen revisions are in `ActivIQ_runs/model_revisions.json`.

The final written report and peer-evaluation form were not present among the
repository files checked. Submit those course deliverables separately, ensuring
the report uses the result distinctions and limitations above. Independent task
and safety evaluation also remains outstanding.

## Repeat the checks

With the baseline environment active and the local checkpoint available:

```powershell
python -m unittest discover -s tests -v
python scripts/evaluate_intent.py
python scripts/evaluate_system.py --output-dir reports/evaluation/submission_recheck
python scripts/evaluate_system.py --component safety --safety-data data/evaluation/safety_hardening_dev.jsonl --output-dir reports/evaluation/submission_safety_recheck
python scripts/auto_label.py check
git diff --check
```

The [supplementary guide](data/evaluation/supplementary/README.md) includes the
entities-only replay command, which requires no trained classifier. Write new
runs into ignored `reports/evaluation/` directories; preserve the submitted
historical and final-check reports unchanged.
