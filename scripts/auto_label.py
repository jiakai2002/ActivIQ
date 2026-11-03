"""Prepare/check, propose APE prompts, score validation, or label training locally."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.auto_labelling.core import ExperimentData
from src.auto_labelling.engine import LocalTransformersEngine
from src.auto_labelling.workflow import label_training, propose, score


def make_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "propose", "score", "label"):
        command = commands.add_parser(name)
        command.add_argument("--source-dir", type=Path, default=ROOT / "data/processed/intents")
        command.add_argument("--seeds", type=Path, default=ROOT / "data/auto_labelling/seeds.jsonl")
        if name in {"check", "score", "label"}:
            command.add_argument("--validation", type=Path, default=ROOT / "data/evaluation/entities_validation.jsonl")
        if name != "check":
            command.add_argument("--model-path", type=Path, required=True)
            command.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
            command.add_argument("--quantization", choices=("none", "4bit"), default="none")
            command.add_argument("--max-input-tokens", type=int, default=8192)
            command.add_argument("--max-new-tokens", type=int, default=512)
            command.add_argument("--run-dir", type=Path, required=True)
            command.add_argument("--seed", type=int, default=42)
            command.add_argument("--attempts", type=int, choices=(1, 2, 3), default=2)
            command.add_argument("--resume", action="store_true")
        if name == "propose":
            command.add_argument("--candidate-count", type=int, default=4)
        if name == "score":
            command.add_argument("--candidates", type=Path, required=True)
            command.add_argument("--baseline", type=Path, default=ROOT / "prompts/auto_labelling/baseline.txt")
        if name == "label":
            command.add_argument("--selection", type=Path, required=True)
    return parser


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    try:
        data = ExperimentData(args.source_dir)
        readiness = {}
        checks = [("seeds", args.seeds, "train", 10)]
        if args.command != "propose":
            checks.append(("validation", args.validation, "validation", 100))
        for name, path, split, count in checks:
            try:
                rows = data.reviewed(path, split, count)
                readiness[name] = {"ready": True, "reviewed": len(rows)}
            except (OSError, ValueError) as error:
                readiness[name] = {"ready": False, "reason": str(error)}
        ready = all(value["ready"] for value in readiness.values())
        if args.command == "check":
            print(json.dumps({"ready": ready, "checks": readiness, "source_counts": {
                name: len(rows) for name, rows in data.rows.items()}, "model_loaded": False}, indent=2))
            return 0 if ready else 2
        if not ready:
            parser.error("Human reference data is not ready:\n" + json.dumps(readiness, indent=2))
        if args.command == "score" and (not args.candidates.is_file() or not args.baseline.is_file()):
            parser.error("Candidate and baseline files must exist before loading the model")
        if args.command == "label" and not args.selection.is_file():
            parser.error("Selection file must exist before loading the model")
        if args.run_dir.exists() and not args.resume:
            parser.error("Run directory already exists; use a new directory or --resume")
        engine = LocalTransformersEngine(args.model_path, args.device, args.quantization,
                                         args.max_input_tokens, args.max_new_tokens,
                                         progress=lambda message: print(message, flush=True))
        shared = {"seed": args.seed, "attempts": args.attempts, "resume": args.resume}
        if args.command == "propose":
            result = propose(data, args.seeds, engine, args.run_dir, args.candidate_count, **shared)
        elif args.command == "score":
            result = score(data, args.seeds, args.validation, args.candidates, args.baseline, engine, args.run_dir, **shared)
            result = {key: result[key] for key in ("research_run", "selected_prompt", "validation_entity_target_met", "metrics")}
        else:
            result = label_training(data, args.seeds, args.validation, args.selection, engine, args.run_dir, **shared)
    except (OSError, ValueError, ImportError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
