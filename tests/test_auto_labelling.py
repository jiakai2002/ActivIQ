"""Synthetic fixtures verify infrastructure, never real labelling quality."""

from contextlib import redirect_stderr, redirect_stdout
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.auto_labelling.core import (CONTRACT, ExperimentData, annotation_messages, candidate_messages,
                                     digest, parse_annotation, parse_instruction, parse_object, validate_entities)
from src.auto_labelling.engine import Generation, LocalTransformersEngine
from src.auto_labelling.workflow import RunStore, label_training, propose, score
from src.config import INTENT_LABELS
from src.evaluation import ENTITY_SLOTS, file_hash, read_jsonl


def entities(value="squat"):
    return {slot: [f"{value}-{slot}"] for slot in ENTITY_SLOTS}


class FixtureEngine:
    """No inference: deterministic synthetic answers for workflow tests only."""
    def __init__(self, answers=None, malformed=None, bad_baseline=False, fail_after=None, duplicate=False):
        self.metadata = {"backend": "fixture", "signature": "synthetic-not-a-real-model"}
        self.answers = answers or {}
        self.malformed = set(malformed or [])
        self.bad_baseline, self.fail_after, self.duplicate = bad_baseline, fail_after, duplicate
        self.calls = []

    def generate(self, messages, seed, sample=False):
        if self.fail_after is not None and len(self.calls) == self.fail_after:
            raise RuntimeError("synthetic interrupted run")
        self.calls.append({"messages": messages, "seed": seed, "sample": sample})
        if sample:
            index = 1 if self.duplicate else json.loads(messages[1]["content"])["candidate_number"]
            payload = {"instruction": f"Use exact labels and respect negation; candidate variant {index}."}
        else:
            # Retry messages never include reference labels either.
            query = next(message for message in reversed(messages)
                         if message["role"] == "user" and message["content"].startswith('{"utterance"'))
            text = json.loads(query["content"])["utterance"]
            if text in self.malformed:
                return Generation("not JSON", 0.01, 40, 3, "eos")
            payload = self.answers[text]
            if self.bad_baseline and "Baseline test instruction" in messages[0]["content"]:
                payload = {"intent": "out_of_scope", "entities": {slot: [] for slot in ENTITY_SLOTS}}
        return Generation(json.dumps(payload), 0.01, 40, 20, "eos")


class ContractTests(unittest.TestCase):
    def test_valid_label_and_single_json_fence(self):
        text = json.dumps({"intent": "find_exercise", "entities": entities()})
        self.assertEqual(parse_annotation(text)["intent"], "find_exercise")
        self.assertEqual(parse_annotation("```json\n" + text + "\n```"), parse_annotation(text))

    def test_invalid_json_duplicate_keys_nan_and_surrounding_prose(self):
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '[]', 'Here is JSON: {"x":1}', '{"x":1} trailing'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_object(text)

    def test_unknown_intent_missing_fields_and_extra_fields(self):
        for payload in ({"intent": "medical", "entities": entities()},
                        {"intent": "general_chat", "entities": {}},
                        {"intent": "general_chat", "entities": entities(), "reasoning": "secret"}):
            with self.assertRaises(ValueError):
                parse_annotation(json.dumps(payload))

    def test_entities_reject_scalars_empty_values_duplicates_and_unknown_slots(self):
        for change in ({"exercise": "squat"}, {"exercise": [""]}, {"exercise": ["Squat", "squat"]}, {"unknown": []}):
            with self.assertRaises(ValueError):
                validate_entities({**entities(), **change})

    def test_optional_human_annotation_slots_are_not_model_output_slots(self):
        extra = {**entities(), "days": ["3"]}
        self.assertNotIn("days", validate_entities(extra, allow_extra=True))
        with self.assertRaises(ValueError):
            validate_entities(extra)

    def test_candidate_contract_rejects_short_or_extra_fields(self):
        for payload in ({"instruction": "x"}, {"instruction": "Use valid labels and clear instructions", "labels": []}):
            with self.assertRaises(ValueError):
                parse_instruction(json.dumps(payload))

    def test_final_query_never_contains_source_intent_or_reference_entities(self):
        seed = {"text": "seed utterance", "intent": "find_exercise", "entities": entities("seed")}
        messages = annotation_messages("Follow the examples and label accurately.", [seed], "new utterance")
        self.assertEqual(json.loads(messages[-1]["content"]), {"utterance": "new utterance"})
        self.assertEqual(messages[-2]["role"], "assistant")
        self.assertEqual(len(messages), 4)


class DataFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "intents"
        self.source.mkdir()
        for split, count in (("train", 18), ("validation", 100), ("test", 6)):
            with (self.source / f"{split}.csv").open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["text", "label"])
                writer.writeheader()
                writer.writerows({"text": f"{split} synthetic utterance {index}", "label": INTENT_LABELS[index % 6]}
                                 for index in range(count))
        self.data = ExperimentData(self.source)
        self.seed_dir = self.root / "seeds"
        self.data.prepare_seeds(self.seed_dir)
        self.seed_path = self.seed_dir / "seeds.jsonl"
        self.validation = self.root / "validation.jsonl"
        self.answers = {}
        for split, rows in self.data.rows.items():
            for row in rows:
                self.answers[row["text"]] = {"intent": row["intent"], "entities": entities(f"{split}-gold-secret")}
        for path, rows in ((self.seed_path, read_jsonl(self.seed_path)), (self.validation, self.data.rows["validation"])):
            labelled = [{**row, "label_status": "human_reviewed", "annotator": "SYNTHETIC UNIT TEST FIXTURE",
                         "entities": self.answers[row["text"]]["entities"]} for row in rows]
            path.write_text("".join(json.dumps(row) + "\n" for row in labelled))
        self.baseline = self.root / "baseline.txt"
        self.baseline.write_text("Baseline test instruction for labelling independent fitness utterances.")


class DataTests(DataFixture):
    def test_seed_selection_uses_train_only_and_covers_all_intents(self):
        rows = read_jsonl(self.seed_path)
        self.assertEqual(len(rows), 10)
        self.assertEqual({row["intent"] for row in rows}, set(INTENT_LABELS))
        self.assertTrue(all(row["split"] == "train" for row in rows))
        with self.assertRaises(FileExistsError):
            self.data.prepare_seeds(self.seed_dir)

    def test_unlabelled_annotations_and_wrong_counts_are_rejected(self):
        rows = read_jsonl(self.seed_path)
        rows[0]["entities"] = None
        self.seed_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaisesRegex(ValueError, "human"):
            self.data.reviewed(self.seed_path, "train", 10)
        with self.assertRaisesRegex(ValueError, "Expected"):
            self.data.reviewed(self.validation, "validation", 99)

    def test_test_utterance_cannot_be_relabelled_as_a_validation_example(self):
        rows = read_jsonl(self.validation)
        rows[0]["text"] = self.data.rows["test"][0]["text"]
        rows[0]["intent"] = self.data.rows["test"][0]["intent"]
        self.validation.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaisesRegex(ValueError, "membership"):
            self.data.reviewed(self.validation, "validation", 100)

    def test_duplicate_text_and_changed_source_intent_are_rejected(self):
        rows = read_jsonl(self.validation)
        rows[0]["intent"] = "wrong_intent"
        self.validation.write_text("".join(json.dumps(row) + "\n" for row in rows))
        with self.assertRaises(ValueError):
            self.data.reviewed(self.validation, "validation", 100)
        with (self.source / "test.csv").open("a") as stream:
            stream.write("train synthetic utterance 0,generate_plan\n")
        with self.assertRaisesRegex(ValueError, "leaked"):
            ExperimentData(self.source)


class WorkflowTests(DataFixture):
    def run_proposal(self, engine, name="propose", **kwargs):
        with redirect_stdout(io.StringIO()):
            propose(self.data, self.seed_path, engine, self.root / name, **kwargs)
        return self.root / name / "candidates.jsonl"

    def run_score(self, engine, candidates, name="score", **kwargs):
        with redirect_stdout(io.StringIO()):
            return score(self.data, self.seed_path, self.validation, candidates, self.baseline, engine, self.root / name, **kwargs)

    def test_proposal_uses_seeds_only_and_deduplicates_candidates(self):
        engine = FixtureEngine(duplicate=True)
        path = self.run_proposal(engine, candidate_count=3)
        self.assertEqual(len(read_jsonl(path)), 1)
        self.assertEqual(len(engine.calls), 3)
        for call in engine.calls:
            self.assertNotIn("validation synthetic", json.dumps(call["messages"]))
            self.assertNotIn("test synthetic", json.dumps(call["messages"]))

    def test_validation_selects_candidate_against_baseline_without_revealing_gold(self):
        engine = FixtureEngine(self.answers, bad_baseline=True)
        candidates = self.run_proposal(engine, candidate_count=2)
        selected = self.run_score(engine, candidates)
        self.assertTrue(selected["selected_prompt"]["id"].startswith("ape-"))
        self.assertEqual(selected["metrics"]["micro"]["f1"], 1)
        self.assertFalse(selected["research_run"])
        for call in engine.calls:
            self.assertNotIn("validation-gold-secret", json.dumps(call["messages"]))
            self.assertNotIn("test synthetic", json.dumps(call["messages"]))

    def test_invalid_outputs_remain_in_metric_denominators(self):
        bad = self.data.rows["validation"][0]["text"]
        engine = FixtureEngine(self.answers, malformed=[bad])
        candidates = self.run_proposal(engine, candidate_count=1)
        selected = self.run_score(engine, candidates, attempts=1)
        self.assertEqual(selected["metrics"]["invalid_outputs"], 1)
        self.assertEqual(selected["metrics"]["intent_agreement"], 0.99)
        self.assertLess(selected["metrics"]["micro"]["f1"], 1)

    def test_resuming_uses_cached_generations_and_rejects_input_drift(self):
        engine = FixtureEngine()
        self.run_proposal(engine, candidate_count=2)
        self.run_proposal(engine, candidate_count=2, resume=True)
        self.assertEqual(len(engine.calls), 2)
        with self.assertRaisesRegex(ValueError, "Resume refused"):
            self.run_proposal(engine, candidate_count=3, resume=True)
        with self.assertRaises(FileExistsError):
            self.run_proposal(engine, candidate_count=2)

    def test_interrupted_scoring_resumes_without_repeating_completed_queries(self):
        engine = FixtureEngine(self.answers)
        candidates = self.run_proposal(engine, candidate_count=1)
        engine.fail_after = len(engine.calls) + 3
        with self.assertRaises(RuntimeError):
            self.run_score(engine, candidates)
        calls = len(engine.calls)
        engine.fail_after = None
        self.run_score(engine, candidates, resume=True)
        self.assertEqual(len(engine.calls) - calls, 197)

    def test_training_export_is_training_only_machine_labelled_and_keeps_source_intents(self):
        engine = FixtureEngine(self.answers)
        candidates = self.run_proposal(engine, candidate_count=1)
        self.run_score(engine, candidates)
        with redirect_stdout(io.StringIO()):
            summary = label_training(self.data, self.seed_path, self.validation, self.root / "score/selection.json",
                                     engine, self.root / "labels")
        labels = read_jsonl(self.root / "labels/machine_labels.jsonl")
        self.assertEqual(len(labels), 18)
        self.assertTrue(all(row["split"] == "train" and row["label_status"] == "machine_generated_fixture" for row in labels))
        self.assertEqual(sum(row["seed_example"] for row in labels), 10)
        self.assertEqual(summary["nonseed_training_rows"], 8)
        self.assertFalse(summary["quality_targets_met"])
        self.assertFalse(summary["proposal_training_size"])
        self.assertIsNone(summary["training_entity_f1"])

    def test_rejected_training_rows_are_quarantined_not_silently_overwritten(self):
        engine = FixtureEngine(self.answers)
        candidates = self.run_proposal(engine, candidate_count=1)
        self.run_score(engine, candidates)
        engine.malformed.add(self.data.rows["train"][0]["text"])
        with redirect_stdout(io.StringIO()):
            summary = label_training(self.data, self.seed_path, self.validation, self.root / "score/selection.json",
                                     engine, self.root / "labels", attempts=1)
        self.assertEqual(summary["accepted"], 17)
        self.assertEqual(summary["rejected"], 1)
        self.assertAlmostEqual(summary["intent_agreement_all_training"], 17 / 18)

    def test_changed_model_contract_or_prompt_cannot_reuse_selection(self):
        engine = FixtureEngine(self.answers)
        candidates = self.run_proposal(engine, candidate_count=1)
        self.run_score(engine, candidates)
        selected_path = self.root / "score/selection.json"
        selection = json.loads(selected_path.read_text())
        selection["selected_prompt"]["instruction"] += " changed"
        selected_path.write_text(json.dumps(selection))
        with self.assertRaisesRegex(ValueError, "provenance"):
            label_training(self.data, self.seed_path, self.validation, selected_path, engine, self.root / "labels")

    def test_corrupt_cache_cannot_be_trusted(self):
        engine = FixtureEngine()
        self.run_proposal(engine, candidate_count=1)
        path = next((self.root / "propose/records").glob("*.json"))
        cached = json.loads(path.read_text())
        cached["valid"] = False
        path.write_text(json.dumps(cached))
        with self.assertRaisesRegex(ValueError, "corrupted"):
            self.run_proposal(engine, candidate_count=1, resume=True)

    def test_format_repair_is_bounded_and_does_not_supply_gold(self):
        class RepairEngine(FixtureEngine):
            def generate(self, messages, seed, sample=False):
                if not self.calls:
                    self.calls.append({"messages": messages, "seed": seed})
                    return Generation("bad", 0.01, 5, 1, "eos")
                return super().generate(messages, seed, sample)
        engine = RepairEngine()
        self.run_proposal(engine, candidate_count=1)
        self.assertEqual(len(engine.calls), 2)
        self.assertIn("Validation error", engine.calls[1]["messages"][-1]["content"])

    def test_model_wiring_errors_abort_instead_of_becoming_invalid_annotations(self):
        class BrokenEngine(FixtureEngine):
            def generate(self, messages, seed, sample=False):
                raise ValueError("synthetic model configuration error")
        with self.assertRaisesRegex(ValueError, "model configuration"):
            self.run_proposal(BrokenEngine(), candidate_count=1)

    def test_inputs_edited_during_generation_cannot_publish_a_selection(self):
        engine = FixtureEngine(self.answers)
        candidates = self.run_proposal(engine, candidate_count=1)
        generate = engine.generate
        changed = False
        def mutate_input(messages, seed, sample=False):
            nonlocal changed
            output = generate(messages, seed, sample)
            if not changed:
                self.baseline.write_text(self.baseline.read_text() + " Changed mid-run.")
                changed = True
            return output
        engine.generate = mutate_input
        with self.assertRaisesRegex(ValueError, "changed during"):
            self.run_score(engine, candidates)
        self.assertFalse((self.root / "score/selection.json").exists())

    def test_unreviewed_references_stop_cli_before_model_loading(self):
        from scripts.auto_label import main
        rows = read_jsonl(self.seed_path)
        rows[0]["label_status"] = "unlabelled"
        self.seed_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        args = ["auto_label.py", "propose", "--source-dir", str(self.source), "--seeds", str(self.seed_path),
                "--model-path", "missing-model", "--run-dir", str(self.root / "blocked")]
        with (patch("sys.argv", args), patch("scripts.auto_label.LocalTransformersEngine") as loader,
              redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
            with self.assertRaises(SystemExit) as caught:
                main()
            self.assertEqual(caught.exception.code, 2)
            loader.assert_not_called()
        self.assertFalse((self.root / "blocked").exists())


class RunnerValidationTests(unittest.TestCase):
    def test_missing_local_model_fails_without_download(self):
        with self.assertRaisesRegex(ValueError, "local checkpoint"):
            LocalTransformersEngine(Path("a-model-that-does-not-exist"))

    def test_cpu_4bit_is_rejected_before_loading_optional_libraries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "CUDA"):
                LocalTransformersEngine(root, device="cpu", quantization="4bit")


if __name__ == "__main__":
    unittest.main()
