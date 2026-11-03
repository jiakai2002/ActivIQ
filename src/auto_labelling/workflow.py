"""Resumable APE selection and training-only machine annotation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from src.auto_labelling.core import (CONTRACT, annotation_messages, candidate_messages, digest,
                                     parse_annotation, parse_instruction, validate_entities)
from src.evaluation import ENTITY_SLOTS, file_hash, read_jsonl, score_entities, timing_summary
from src.auto_labelling.engine import PromptBudgetError


def atomic_json(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: list[dict]):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("".join(json.dumps(row, ensure_ascii=True, allow_nan=False) + "\n" for row in rows), encoding="utf-8")
    temporary.replace(path)


def source_hashes():
    root = Path(__file__).resolve().parents[2]
    paths = [*Path(__file__).parent.glob("*.py"), root / "src/evaluation.py", root / "src/config.py",
             root / "scripts/auto_label.py", root / "scripts/prepare_autolabelling.py"]
    return {str(path.relative_to(root)): file_hash(path) for path in sorted(paths)}


class RunStore:
    def __init__(self, path: Path, identity: dict, resume: bool = False):
        self.path = Path(path)
        identity = {**identity, "code_hashes": source_hashes(), "contract_sha256": digest(CONTRACT)}
        self.identity = identity
        self.signature = digest(identity)
        if self.path.exists():
            if not resume:
                raise FileExistsError("Run directory exists; choose a new directory or explicitly --resume")
            manifest = json.loads((self.path / "manifest.json").read_text())
            if manifest.get("identity_sha256") != self.signature or manifest.get("identity") != identity:
                raise ValueError("Resume refused: inputs, model, prompt, settings or experiment code changed")
        else:
            self.path.mkdir(parents=True)
            atomic_json(self.path / "manifest.json", {"created_utc": datetime.now(timezone.utc).isoformat(),
                                                       "identity_sha256": self.signature, "identity": identity})
        (self.path / "records").mkdir(exist_ok=True)

    def query(self, key: str, messages: list[dict], engine, parser, seed: int, sample: bool, attempts: int) -> dict:
        if attempts < 1 or attempts > 3:
            raise ValueError("Use between one and three bounded attempts")
        request_hash = digest({"messages": messages, "seed": seed, "sample": sample, "attempts": attempts})
        path = self.path / "records" / (digest(key) + ".json")
        if path.exists():
            cached = json.loads(path.read_text())
            checksum = cached.pop("record_sha256", None)
            if digest(cached) != checksum or cached.get("key") != key or cached.get("request_sha256") != request_hash:
                raise ValueError("Cached record is corrupted or belongs to another request")
            if cached["valid"]:
                parser(json.dumps(cached["payload"]))
            return {**cached, "record_sha256": checksum}
        conversation, history, payload = list(messages), [], None
        for attempt in range(attempts):
            try:
                generated = engine.generate(conversation, seed + attempt, sample=sample)
            except PromptBudgetError as error:
                # Context-budget errors are deterministic. Infrastructure errors
                # such as OOM propagate instead of becoming 960 rejected rows.
                history.append({"attempt": attempt + 1, "error": str(error), "generation": None})
                break
            failure = None
            try:
                if generated.finish_reason == "length":
                    raise ValueError("Generation reached its token budget before EOS")
                payload = parser(generated.text)
            except (ValueError, RecursionError) as error:
                failure = str(error)
            history.append({"attempt": attempt + 1, "seed": seed + attempt,
                            "generation": generated.to_dict(), "error": failure})
            if failure is None:
                break
            conversation += [{"role": "assistant", "content": generated.text},
                             {"role": "user", "content": "Return one complete JSON object in the required schema, without reasoning or prose. Validation error: " + failure}]
        result = {"key": key, "request_sha256": request_hash, "valid": payload is not None,
                  "payload": payload, "attempts": history}
        atomic_json(path, {**result, "record_sha256": digest(result)})
        return result


def _identity(stage, data, seeds_path, engine, settings):
    return {"stage": stage, "source_split_hashes": data.hashes, "seeds_sha256": file_hash(seeds_path),
            "engine": engine.metadata, "settings": settings}


def _verify_frozen(store, data, seeds_path, extra_files=()):
    checks = [(Path(seeds_path), store.identity["seeds_sha256"])]
    checks.extend((data.source_dir / f"{split}.csv", checksum) for split, checksum in data.hashes.items())
    checks.extend(extra_files)
    if source_hashes() != store.identity["code_hashes"] or any(file_hash(path) != checksum for path, checksum in checks):
        raise ValueError("Experiment inputs or code changed during generation; final export refused. Restore the frozen inputs or start a new run.")


def propose(data, seeds_path: Path, engine, run_dir: Path, candidate_count=4, seed=42, attempts=2, resume=False):
    if not 1 <= candidate_count <= 20:
        raise ValueError("candidate_count must be between 1 and 20")
    seeds = data.reviewed(seeds_path, "train", 10)
    store = RunStore(run_dir, _identity("propose", data, seeds_path, engine,
                     {"candidate_count": candidate_count, "seed": seed, "attempts": attempts}), resume)
    atomic_json(store.path / "seed_snapshot.json", seeds)
    accepted, rejected, seen = [], [], set()
    for index in range(1, candidate_count + 1):
        result = store.query(f"candidate-{index}", candidate_messages(seeds, index), engine,
                             parse_instruction, seed + index * 10, True, attempts)
        if not result["valid"]:
            rejected.append({"id": f"ape-{index:03d}", "reason": "invalid_generation", "attempts": result["attempts"]})
            continue
        instruction = result["payload"]["instruction"]
        canonical = " ".join(instruction.casefold().split())
        if canonical in seen:
            rejected.append({"id": f"ape-{index:03d}", "reason": "duplicate_instruction"})
            continue
        seen.add(canonical)
        accepted.append({"id": f"ape-{index:03d}", "instruction": instruction, "sha256": digest(instruction),
                         "source": "local_model_generated", "engine_signature": engine.metadata["signature"],
                         "seeds_sha256": store.identity["seeds_sha256"], "contract_sha256": digest(CONTRACT)})
    _verify_frozen(store, data, seeds_path)
    write_jsonl(store.path / "candidates.jsonl", accepted)
    write_jsonl(store.path / "rejected_candidates.jsonl", rejected)
    summary = {"requested": candidate_count, "accepted": len(accepted), "rejected": len(rejected),
               "research_run": engine.metadata["backend"] == "transformers_local"}
    atomic_json(store.path / "summary.json", summary)
    if not accepted:
        raise ValueError("No valid unique candidate instructions; inspect the saved attempts")
    return summary


def _prompt_candidates(path: Path, baseline_path: Path, seeds_path: Path, engine):
    baseline = baseline_path.read_text(encoding="utf-8").strip()
    parse_instruction(json.dumps({"instruction": baseline}))
    prompts = [{"id": "baseline", "instruction": baseline, "sha256": digest(baseline), "source": "baseline_template"}]
    for row in read_jsonl(path):
        instruction = parse_instruction(json.dumps({"instruction": row.get("instruction")}))["instruction"]
        if row["id"] == "baseline" or row.get("sha256") != digest(instruction) or row.get("source") != "local_model_generated":
            raise ValueError("Candidate id, instruction checksum or provenance is invalid")
        if (row.get("engine_signature") != engine.metadata["signature"] or row.get("seeds_sha256") != file_hash(seeds_path)
            or row.get("contract_sha256") != digest(CONTRACT)):
            raise ValueError("Candidate generator model/settings or seed annotations differ from this scoring run")
        prompts.append(row)
    return prompts


def _label_rows(rows, seeds, instruction, engine, store, namespace, seed, attempts):
    predictions = []
    for index, row in enumerate(rows):
        result = store.query(f"{namespace}/{row['id']}", annotation_messages(instruction, seeds, row["text"]),
                             engine, parse_annotation, seed + index * 10, False, attempts)
        predictions.append({"id": row["id"], "text": row["text"], "source_intent": row["intent"],
                            "valid": result["valid"], "prediction": result["payload"], "attempts": result["attempts"]})
        if (index + 1) % 10 == 0 or index + 1 == len(rows):
            print(f"{namespace}: {index + 1}/{len(rows)} complete", flush=True)
    return predictions


def _metrics(gold, predictions):
    empty = {slot: [] for slot in ENTITY_SLOTS}
    metrics = score_entities([row["entities"] for row in gold],
                             [row["prediction"]["entities"] if row["valid"] else empty for row in predictions])
    # Invalid JSON counts as a failed utterance even when its reference has no entities.
    correct = 0
    for reference, result in zip(gold, predictions):
        if result["valid"] and all(
            {value.casefold() for value in reference["entities"][slot]} ==
            {value.casefold() for value in result["prediction"]["entities"][slot]} for slot in ENTITY_SLOTS
        ):
            correct += 1
    metrics["exact_match_rate"] = correct / len(gold)
    metrics["valid_output_rate"] = sum(row["valid"] for row in predictions) / len(gold)
    metrics["invalid_outputs"] = sum(not row["valid"] for row in predictions)
    metrics["intent_agreement"] = sum(row["valid"] and row["prediction"]["intent"] == row["source_intent"] for row in predictions) / len(gold)
    metrics["generation_timing"] = timing_summary([attempt["generation"]["seconds"] for row in predictions
        for attempt in row["attempts"] if attempt.get("generation")])
    return metrics


def score(data, seeds_path: Path, validation_path: Path, candidates_path: Path, baseline_path: Path,
          engine, run_dir: Path, seed=42, attempts=2, resume=False):
    seeds = data.reviewed(seeds_path, "train", 10)
    validation = data.reviewed(validation_path, "validation", 100)
    prompts = _prompt_candidates(candidates_path, baseline_path, seeds_path, engine)
    settings = {"seed": seed, "attempts": attempts, "validation_sha256": file_hash(validation_path),
                "candidates_sha256": file_hash(candidates_path), "baseline_sha256": file_hash(baseline_path)}
    store = RunStore(run_dir, _identity("score", data, seeds_path, engine, settings), resume)
    atomic_json(store.path / "seed_snapshot.json", seeds)
    atomic_json(store.path / "prompts.json", prompts)
    results = []
    for prompt in prompts:
        print(f"Scoring {prompt['id']} on {len(validation)} validation utterances...", flush=True)
        predictions = _label_rows(validation, seeds, prompt["instruction"], engine, store, prompt["id"], seed, attempts)
        metrics = _metrics(validation, predictions)
        results.append({"id": prompt["id"], "source": prompt["source"], "metrics": metrics})
        # Hash filenames rather than accepting candidate ids as filesystem paths.
        write_jsonl(store.path / f"predictions-{digest(prompt['id'])[:16]}.jsonl", predictions)
    def rank(row):
        f1 = row["metrics"]["micro"]["f1"]
        return (-(f1 if f1 is not None else -1), -row["metrics"]["valid_output_rate"],
                -row["metrics"]["intent_agreement"], row["id"] != "baseline", row["id"])
    ranking = sorted(results, key=rank)
    winner = ranking[0]
    prompt = next(row for row in prompts if row["id"] == winner["id"])
    best_ape = min([row for row in results if row["id"] != "baseline"], key=rank)
    baseline = next(row for row in results if row["id"] == "baseline")
    real = engine.metadata["backend"] == "transformers_local"
    _verify_frozen(store, data, seeds_path, [(validation_path, settings["validation_sha256"]),
        (candidates_path, settings["candidates_sha256"]), (baseline_path, settings["baseline_sha256"])])
    metrics = winner["metrics"]
    entity_target = (metrics["micro"]["f1"] is not None and metrics["micro"]["f1"] >= 0.8
                     and len(metrics["covered_slots"]) == len(ENTITY_SLOTS))
    selection = {"schema_version": 1, "selection_metric": "validation_entity_micro_f1",
                 "tie_breaks": ["valid_output_rate", "intent_agreement", "baseline_then_id"],
                 "selected_prompt": prompt, "engine_signature": engine.metadata["signature"],
                 "seeds_sha256": file_hash(seeds_path), "validation_sha256": file_hash(validation_path),
                 "source_split_hashes": data.hashes, "contract_sha256": digest(CONTRACT),
                 "experiment_code_hashes": store.identity["code_hashes"],
                 "validation_rows": len(validation), "research_run": real,
                 "validation_entity_target_met": entity_target, "metrics": metrics,
                 "baseline": baseline, "best_ape": best_ape, "ranking": ranking,
                 "interpretation": "Prompt selection on validation data; not held-out test performance. Invalid generations are not dropped."}
    atomic_json(store.path / "selection.json", selection)
    table = ["# APE validation comparison", "", selection["interpretation"], "",
             f"Real local-model run: {real}", "", "| Prompt | Entity micro-F1 | Intent agreement | Valid output rate |",
             "|---|---:|---:|---:|"]
    for row in ranking:
        value = row["metrics"]
        table.append(f"| {row['id']} | {value['micro']['f1']} | {value['intent_agreement']:.4f} | {value['valid_output_rate']:.4f} |")
    table.extend(["", f"Selected: {winner['id']}", ""])
    (store.path / "summary.md").write_text("\n".join(table), encoding="utf-8")
    return selection


def label_training(data, seeds_path: Path, validation_path: Path, selection_path: Path, engine,
                   run_dir: Path, seed=42, attempts=2, resume=False):
    seeds = data.reviewed(seeds_path, "train", 10)
    data.reviewed(validation_path, "validation", 100)
    selection = json.loads(selection_path.read_text())
    prompt = selection.get("selected_prompt", {})
    if (selection.get("schema_version") != 1 or selection.get("selection_metric") != "validation_entity_micro_f1"
        or selection.get("engine_signature") != engine.metadata["signature"]
        or selection.get("seeds_sha256") != file_hash(seeds_path)
        or selection.get("validation_sha256") != file_hash(validation_path)
        or selection.get("source_split_hashes") != data.hashes
        or selection.get("contract_sha256") != digest(CONTRACT)
        or selection.get("experiment_code_hashes") != source_hashes()
        or prompt.get("sha256") != digest(prompt.get("instruction"))):
        raise ValueError("Selection provenance mismatch: rescore with these exact inputs, model and contract")
    parse_instruction(json.dumps({"instruction": prompt["instruction"]}))
    settings = {"seed": seed, "attempts": attempts, "selection_sha256": file_hash(selection_path)}
    store = RunStore(run_dir, _identity("label_training", data, seeds_path, engine, settings), resume)
    atomic_json(store.path / "selection_snapshot.json", selection)
    rows = _label_rows(data.rows["train"], seeds, prompt["instruction"], engine, store, "train", seed, attempts)
    seed_ids = {row["source_id"] for row in seeds}
    real = engine.metadata["backend"] == "transformers_local"
    accepted, rejected = [], []
    for row in rows:
        if row["valid"]:
            accepted.append({"id": row["id"], "split": "train", "text": row["text"],
                "source_intent": row["source_intent"], **row["prediction"],
                "label_status": "machine_generated" if real else "machine_generated_fixture", "annotator": None,
                "seed_example": row["id"] in seed_ids,
                "intent_matches_source": row["prediction"]["intent"] == row["source_intent"],
                "provenance": {"run_signature": store.signature, "engine_signature": engine.metadata["signature"],
                               "prompt_sha256": prompt["sha256"], "contract_sha256": digest(CONTRACT)}})
        else:
            rejected.append(row)
    _verify_frozen(store, data, seeds_path, [(validation_path, selection["validation_sha256"]),
        (selection_path, settings["selection_sha256"])])
    write_jsonl(store.path / "machine_labels.jsonl", accepted)
    write_jsonl(store.path / "rejected.jsonl", rejected)
    nonseed = [row for row in rows if row["id"] not in seed_ids]
    agreement = sum(row["valid"] and row["prediction"]["intent"] == row["source_intent"] for row in rows) / len(rows)
    summary = {"research_run": real, "split": "train", "requested": len(rows), "accepted": len(accepted),
        "rejected": len(rejected), "valid_output_rate": len(accepted) / len(rows),
        "intent_agreement_all_training": agreement,
        "nonseed_training_rows": len(nonseed), "intent_agreement_excluding_seeds": (
            sum(row["valid"] and row["prediction"]["intent"] == row["source_intent"] for row in nonseed) / len(nonseed) if nonseed else None),
        "intent_agreement_target": 0.85, "intent_agreement_target_met": real and agreement >= 0.85,
        "validation_entity_target_met": real and selection["validation_entity_target_met"],
        "proposal_training_size": len(rows) == 960,
        "quality_targets_met": real and agreement >= 0.85 and selection["validation_entity_target_met"] and not rejected,
        "training_entity_f1": None, "meaning": "Training entity accuracy is unknown without independent human labels. Machine labels are not human reference data."}
    atomic_json(store.path / "summary.json", summary)
    (store.path / "summary.md").write_text("# Training auto-labelling\n\n```json\n" + json.dumps(summary, indent=2) + "\n```\n", encoding="utf-8")
    return summary
