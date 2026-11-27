import unittest

from scripts.train_lora import encode
from scripts.evaluate_lora import entity_metrics
from src.auto_labelling.core import parse_annotation
from src.evaluation import ENTITY_SLOTS
from src.lora import target_json


class FakeTokenizer:
    eos_token = "<eos>"

    def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False):
        return "P:" + msgs[-1]["content"]

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": [ord(c) for c in text]}


class LoraFormatTests(unittest.TestCase):
    def test_target_round_trips_through_strict_parser(self):
        entities = {slot: [] for slot in ENTITY_SLOTS}
        entities["exercise"] = ["squat"]
        parsed = parse_annotation(target_json("find_exercise", entities))
        self.assertEqual(parsed, {"intent": "find_exercise", "entities": entities})

    def test_loss_masks_prompt_only(self):
        entities = {slot: [] for slot in ENTITY_SLOTS}
        row = {"text": "hi", "intent": "general_chat", "entities": entities}
        item = encode(FakeTokenizer(), row, 1000)
        prompt_len = len("P:hi")
        self.assertTrue(all(x == -100 for x in item["labels"][:prompt_len]))
        self.assertTrue(all(x != -100 for x in item["labels"][prompt_len:]))
        self.assertEqual(len(item["input_ids"]), len(item["labels"]))


class LoraEntityEvaluationTests(unittest.TestCase):
    def record(self, identifier, **entities):
        return {"id": identifier, "label_status": "human_reviewed", "annotator": "Reviewer",
                "entities": {slot: entities.get(slot, []) for slot in ENTITY_SLOTS}}

    def test_invalid_output_cannot_match_an_empty_reference(self):
        records = [self.record("empty"), self.record("exercise", exercise=["squat"])]
        result = entity_metrics(records, {"exercise": records[1]["entities"]}, False)
        self.assertEqual(result["exact_match_rate"], 0.5)
        self.assertEqual(result["micro"]["f1"], 1.0)
        self.assertEqual(result["status"], "complete")
        self.assertFalse(result["provisional"])

    def test_blank_reviewer_does_not_authorize_scoring(self):
        record = self.record("draft")
        record["annotator"] = "  "
        result = entity_metrics([record], {"draft": record["entities"]}, False)
        self.assertEqual(result["status"], "pending_human_annotation")
        self.assertNotIn("micro", result)

    def test_draft_scoring_remains_provisional(self):
        record = self.record("draft", food=["apple"])
        record.update(label_status="ai_draft", annotator=None)
        result = entity_metrics([record], {"draft": record["entities"]}, True)
        self.assertEqual(result["micro"]["f1"], 1.0)
        self.assertTrue(result["provisional"])


if __name__ == "__main__":
    unittest.main()
