"""Verify metric calculations, outcome checking and honest benchmark status."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.prepare_entity_annotations import prepare_annotations
from src.evaluation import (ENTITY_SLOTS, check_response, evaluate_conversations, evaluate_entities,
                            evaluate_latency, evaluate_safety, percentile, read_jsonl,
                            score_entities, timing_summary)
from src.safety import MEDICAL_RESPONSE


def gold(**values):
    return {slot: values.get(slot, []) for slot in ENTITY_SLOTS}


class Extractor:
    matcher = None

    def __init__(self, output=None):
        self.output = output
        self.calls = 0

    def extract(self, text):
        self.calls += 1
        return self.output


class Bot:
    def __init__(self, responses):
        self.responses = responses
        self.resets = 0
        self.calls = 0
        self.state = SimpleNamespace(reset=self.reset)
        self.knowledge_base = SimpleNamespace(exercises=[
            {"name": "Machine press", "level": "intermediate", "equipment": "machine",
             "primary_muscles": ["chest"], "secondary_muscles": []},
            {"name": "Squat", "level": "beginner", "equipment": "body only",
             "primary_muscles": ["quadriceps"], "secondary_muscles": []},
        ])

    def reset(self):
        self.resets += 1

    def respond(self, text):
        self.calls += 1
        response = self.responses[text]
        if isinstance(response, Exception):
            raise response
        return response


class EntityMetricTests(unittest.TestCase):
    def test_micro_counts_include_false_positives_and_missed_entities(self):
        result = score_entities([gold(exercise=["squat"], equipment=["dumbbell"])],
                                [{"exercise": ["squat", "lunge"]}])
        self.assertEqual(result["micro"]["tp"], 1)
        self.assertEqual(result["micro"]["fp"], 1)
        self.assertEqual(result["micro"]["fn"], 1)
        self.assertEqual(result["micro"]["f1"], 0.5)
        self.assertEqual(result["exact_match_rate"], 0)

    def test_case_whitespace_and_duplicate_values_do_not_change_score(self):
        result = score_entities([gold(exercise=["bench press"])],
                                [{"exercise": [" Bench   PRESS ", "bench press"]}])
        self.assertEqual(result["micro"]["f1"], 1)
        self.assertEqual(result["exact_match_rate"], 1)

    def test_no_entities_does_not_receive_perfect_f1(self):
        result = score_entities([gold()], [{}])
        self.assertIsNone(result["micro"]["f1"])
        self.assertEqual(result["covered_slots"], [])

    def test_missing_gold_slots_is_an_annotation_error(self):
        with self.assertRaises(ValueError):
            score_entities([{"exercise": ["squat"]}], [{}])

    def test_scalar_labels_are_rejected(self):
        with self.assertRaises(ValueError):
            score_entities([gold(exercise="squat")], [{}])

    def test_mismatched_sample_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            score_entities([gold()], [])

    def test_unlabelled_data_is_not_scored(self):
        extractor = Extractor(gold())
        report = evaluate_entities([{"id": "pending", "text": "hello", "entities": None}], extractor)
        self.assertEqual(report["status"], "needs_human_annotation")
        self.assertEqual(extractor.calls, 0)
        self.assertFalse(report["proposal_target_verified"])

    def test_draft_gold_cannot_verify_proposal_target(self):
        values = {slot: [slot] for slot in ENTITY_SLOTS}
        row = {"id": "draft", "text": "example", "entities": values, "split": "development", "label_status": "draft"}
        report = evaluate_entities([row], Extractor(values), allow_draft=True)
        self.assertEqual(report["metrics"]["micro"]["f1"], 1)
        self.assertTrue(report["provisional"])
        self.assertFalse(report["proposal_target_verified"])

    def test_human_test_requires_all_slot_types_for_target(self):
        row = {"id": "test", "text": "example", "entities": gold(exercise=["squat"]),
               "split": "test", "label_status": "human_reviewed", "annotator": "Test annotator"}
        report = evaluate_entities([row], Extractor(row["entities"]))
        self.assertFalse(report["proposal_target_verified"])

    def test_complete_reviewed_test_can_verify_target(self):
        values = {slot: [slot] for slot in ENTITY_SLOTS}
        row = {"id": "test", "text": "example", "entities": values, "split": "test",
               "label_status": "human_reviewed", "annotator": "Test annotator"}
        report = evaluate_entities([row], Extractor(values))
        self.assertTrue(report["proposal_target_verified"])
        self.assertFalse(evaluate_entities([row], Extractor(values), allow_draft=True)["proposal_target_verified"])


class OutcomeTests(unittest.TestCase):
    def test_plan_checks_actual_database_constraints_not_header_claims(self):
        bot = Bot({})
        text = "Here is a beginner bodyweight plan\nDay 1 (estimated 20 minutes, including warm-up):\n- Machine press: 3 sets of 8-12; rest 75 seconds."
        failures = check_response({"text": text}, {"plan_constraints": {
            "days": 1, "level": "beginner", "equipment": ["bodyweight"], "body_parts": ["legs"], "max_minutes": 15}}, bot.knowledge_base)
        self.assertEqual(len(failures), 4)

    def test_missing_plan_does_not_pass_empty_universal_checks(self):
        self.assertTrue(check_response({"text": "No plan"}, {"plan_constraints": {"days": 3}}, Bot({}).knowledge_base))

    def test_empty_or_unknown_expectations_are_rejected(self):
        for expected in ({}, {"unknown_check": True}):
            with self.assertRaises(ValueError):
                check_response({}, expected, Bot({}).knowledge_base)

    def test_scenario_success_requires_every_turn(self):
        bot = Bot({"one": {"text": "correct"}, "two": {"text": "wrong"}})
        row = {"id": "scenario", "split": "development", "turns": [
            {"input": "one", "expect": {"text_contains": ["correct"]}},
            {"input": "two", "expect": {"text_contains": ["correct"]}}]}
        report = evaluate_conversations([row], bot)
        self.assertEqual(report["task_success_rate"], 0)
        self.assertEqual(report["turn_success_rate"], 0.5)
        self.assertEqual(bot.resets, 1)

    def test_response_exception_is_recorded_as_failure(self):
        bot = Bot({"fail": RuntimeError("fixture failure")})
        report = evaluate_conversations([{"id": "scenario", "turns": [
            {"input": "fail", "expect": {"intent": "generate_plan"}}]}], bot)
        self.assertFalse(report["transcripts"][0]["passed"])
        self.assertIn("RuntimeError", report["transcripts"][0]["turns"][0]["response"]["error"])

    def test_single_turn_passes_cannot_hide_failed_multi_turn_task(self):
        bot = Bot({"pass": {"text": "correct"}, "fail": {"text": "wrong"}})
        single = {"id": "single", "turns": [{"input": "pass", "expect": {"text_contains": ["correct"]}}]}
        multi = {"id": "multi", "turns": [{"input": "pass", "expect": {"text_contains": ["correct"]}},
                                           {"input": "fail", "expect": {"text_contains": ["correct"]}}]}
        report = evaluate_conversations([single, multi], bot)
        self.assertEqual(report["overall_task_success_rate"], 0.5)
        self.assertEqual(report["task_success_rate"], 0)
        self.assertFalse(report["target_met_on_this_suite"])

    def test_safety_reports_misses_and_false_refusals_separately(self):
        bot = Bot({"medical": {"text": "Happy to help", "intent": "general_chat"},
                   "fitness": {"text": MEDICAL_RESPONSE, "route": "medical"}})
        report = evaluate_safety([{"id": "miss", "text": "medical", "expected": "medical"},
                                  {"id": "false_alarm", "text": "fitness", "expected": "fitness"}], bot)
        self.assertEqual(report["by_expected_route"]["medical"]["rate"], 0)
        self.assertEqual(report["fitness_medical_false_refusals"], 1)
        self.assertFalse(report["target_met_on_this_suite"])


class TimingTests(unittest.TestCase):
    def test_interpolated_percentile(self):
        self.assertAlmostEqual(percentile([3, 1], 0.95), 2.9)
        self.assertEqual(percentile([2], 0.95), 2)

    def test_one_second_boundary_is_strict(self):
        self.assertEqual(timing_summary([0.2, 1.0])["fraction_below_one_second"], 0.5)

    def test_warmup_is_excluded_and_slow_sample_fails_target(self):
        bot = Bot({"hello": {"text": "Hi", "intent": "general_chat"}})
        with patch("src.evaluation.time.perf_counter", side_effect=[0, 0.2, 1, 2.2]):
            report = evaluate_latency([{"id": "q", "text": "hello", "label": "general_chat"}], bot, repeats=2, warmup=1)
        self.assertEqual(bot.calls, 3)
        self.assertEqual(report["summary"]["samples"], 2)
        self.assertFalse(report["target_met_on_this_run"])
        self.assertEqual(report["by_route"]["classifier_path"]["samples"], 2)

    def test_post_classifier_rejection_is_not_counted_as_a_safety_shortcut(self):
        bot = Bot({"unknown": {"text": "Out of scope", "route": "out_of_scope",
                              "classifier_used": True, "classifier_intent": "generate_plan"}})
        report = evaluate_latency([{"id": "q", "text": "unknown"}], bot, repeats=1, warmup=0)
        self.assertEqual(report["by_route"]["classifier_path"]["samples"], 1)
        self.assertEqual(report["by_route"]["safety_shortcut"]["samples"], 0)


class AnnotationFileTests(unittest.TestCase):
    def test_blank_templates_preserve_original_splits_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare_annotations(root)
            validation = read_jsonl(root / "entities_validation.jsonl")
            test = read_jsonl(root / "entities_test.jsonl")
            self.assertEqual(len(validation), 100)
            self.assertEqual(len(test), 120)
            self.assertTrue(all(row["entities"] is None and row["label_status"] == "unlabelled" for row in validation + test))
            self.assertFalse({row["text"].casefold() for row in validation} & {row["text"].casefold() for row in test})
            with self.assertRaises(FileExistsError):
                prepare_annotations(root)

    def test_duplicate_record_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cases.jsonl"
            path.write_text(json.dumps({"id": "same"}) + "\n" + json.dumps({"id": "same"}))
            with self.assertRaises(ValueError):
                read_jsonl(path)


if __name__ == "__main__":
    unittest.main()
