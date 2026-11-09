import unittest

from scripts.train_lora import encode
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


if __name__ == "__main__":
    unittest.main()
