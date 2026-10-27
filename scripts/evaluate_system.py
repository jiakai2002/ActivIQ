"""Evaluate entities, conversations, safety and CPU response latency."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODEL_DIR, PROCESSED_DATA_DIR
from src.entity_extractor import FitnessEntityExtractor
from src.evaluation import (evaluate_conversations, evaluate_entities, evaluate_latency,
                            evaluate_safety, file_hash, read_jsonl)
from src.pipeline import FitBuddyPipeline


def git_output(*args):
    try:
        return subprocess.check_output(["git", *args], cwd=PROJECT_ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def environment_metadata() -> dict:
    packages = {}
    for name in ("torch", "transformers", "spacy", "numpy"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    torch = sys.modules.get("torch")
    return {"python": sys.version, "platform": platform.platform(), "processor": platform.processor(),
            "logical_cpus": os.cpu_count(), "packages": packages,
            "torch_intraop_threads": torch.get_num_threads() if torch else None,
            "torch_interop_threads": torch.get_num_interop_threads() if torch else None,
            "git_commit": git_output("rev-parse", "HEAD"),
            "git_tracked_changes": git_output("status", "--short", "--untracked-files=no")}


def render_markdown(report: dict) -> str:
    lines = ["# ActivIQ system evaluation", "", f"Run: {report['created_utc']}", "",
             "Draft/development suites are provisional, not held-out performance claims. "
             "Check each component's provenance status. Entity targets require reviewed human test labels; "
             "the supplied conversation/safety cases were authored with knowledge of the implementation.", ""]
    for name, result in report["components"].items():
        summary = {key: value for key, value in result.items()
                   if key not in {"predictions", "transcripts", "results", "samples", "pending_ids"}}
        lines.extend([f"## {name}", "", "```json", json.dumps(summary, indent=2), "```", ""])
        if name == "conversations":
            for scenario in result["transcripts"]:
                lines.extend([f"### {scenario['id']}: {'PASS' if scenario['passed'] else 'FAIL'}", ""])
                for turn in scenario["turns"]:
                    lines.extend([f"User: {turn['input']}", "", "Assistant:", "", "```text",
                                  turn["response"].get("text", ""), "```", ""])
                    for failure in turn["failures"]:
                        lines.append(f"- Failure: {failure}")
                    lines.append("")
        if name == "safety":
            lines.extend(["| Case | Expected | Keyword route | Result |", "|---|---|---|---|"])
            for row in result["results"]:
                lines.append(f"| {row['id']} | {row['expected']} | {row['keyword_route']} | {'PASS' if row['passed'] else 'FAIL'} |")
            lines.append("")
    lines.extend(["## Reproducibility metadata", "", "```json", json.dumps(report["metadata"], indent=2), "```", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", choices=("all", "entities", "conversations", "safety", "latency"), default="all")
    parser.add_argument("--entity-data", type=Path, default=PROJECT_ROOT / "data/evaluation/entities_test.jsonl")
    parser.add_argument("--conversation-data", type=Path, default=PROJECT_ROOT / "data/evaluation/conversations_dev.jsonl")
    parser.add_argument("--safety-data", type=Path, default=PROJECT_ROOT / "data/evaluation/safety_dev.jsonl")
    parser.add_argument("--latency-data", type=Path, default=PROCESSED_DATA_DIR / "intents/test.csv")
    parser.add_argument("--latency-repeats", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=12)
    parser.add_argument("--allow-draft", action="store_true", help="Score draft entity labels provisionally; never certify a proposal target")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "reports/evaluation")
    args = parser.parse_args()
    if args.latency_repeats < 1 or args.warmup < 0:
        parser.error("latency-repeats must be positive and warmup nonnegative")
    components = ("entities", "conversations", "safety", "latency") if args.component == "all" else (args.component,)
    paths = {"entities": args.entity_data, "conversations": args.conversation_data,
             "safety": args.safety_data, "latency": args.latency_data}
    # Validate input files before loading the model or executing any test turns.
    inputs = {}
    for name in components:
        try:
            if name == "latency":
                with paths[name].open(encoding="utf-8", newline="") as stream:
                    rows = list(csv.DictReader(stream))
                if not rows or any(not row.get("text") or not row.get("label") for row in rows):
                    raise ValueError("Latency CSV needs nonempty text and label columns")
                inputs[name] = [{"id": f"latency-{index:03d}", **row} for index, row in enumerate(rows, 1)]
            else:
                inputs[name] = read_jsonl(paths[name])
        except (OSError, ValueError) as error:
            parser.error(str(error))
    start = time.perf_counter()
    bot = None
    if any(name != "entities" for name in components):
        if not (MODEL_DIR / "config.json").exists():
            parser.error("Trained model missing. Run scripts/train_intent.py; entities-only evaluation does not require model weights.")
        print("Loading local classifier and knowledge bases...", flush=True)
        bot = FitBuddyPipeline()
        extractor = bot.extractor
    else:
        extractor = FitnessEntityExtractor()
    startup = time.perf_counter() - start
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "metadata": environment_metadata(),
              "components": {}}
    source_paths = sorted(list((PROJECT_ROOT / "src").glob("*.py")) + list((PROJECT_ROOT / "scripts").glob("*.py")))
    model_paths = [MODEL_DIR / name for name in (
        "config.json", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "vocab.txt")]
    report["metadata"].update({"startup_seconds_this_process": startup,
        "extractor_backend": "spacy_phrase_matcher" if extractor.matcher is not None else "regex",
        "classifier_device": str(bot.classifier.predictor.device) if bot else None,
        "input_files": {name: {"path": str(paths[name]), "sha256": file_hash(paths[name])} for name in components},
        "source_sha256": {str(path.relative_to(PROJECT_ROOT)): file_hash(path) for path in source_paths},
        "requirements_sha256": file_hash(PROJECT_ROOT / "requirements.txt"),
        "data_sha256": {name: file_hash(PROCESSED_DATA_DIR / name) for name in ("exercises.json", "nutrition.json")},
        "model_sha256": {path.name: file_hash(path) for path in model_paths if bot and path.exists()}})
    for name in components:
        print(f"Evaluating {name}...", flush=True)
        if name == "entities":
            result = evaluate_entities(inputs[name], extractor, args.allow_draft)
        elif name == "conversations":
            result = evaluate_conversations(inputs[name], bot)
        elif name == "safety":
            result = evaluate_safety(inputs[name], bot)
        else:
            result = evaluate_latency(inputs[name], bot, args.latency_repeats, args.warmup,
                                      progress=lambda message: print(message, flush=True))
        report["components"][name] = result
        summary = {key: value for key, value in result.items() if key not in {"predictions", "transcripts", "results", "samples", "pending_ids"}}
        print(json.dumps({name: summary}, indent=2), flush=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = args.output_dir / "system_evaluation.json", args.output_dir / "system_evaluation.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(f"Saved {json_path}\nSaved {markdown_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
