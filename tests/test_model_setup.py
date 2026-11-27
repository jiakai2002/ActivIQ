"""Check missing-checkpoint handling and offline loading without real weights."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.intent_classifier import IntentClassifier


class ModelSetupTests(unittest.TestCase):
    def test_incomplete_checkpoint_fails_before_loading_or_network_access(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("src.intent_classifier.AutoTokenizer.from_pretrained") as tokenizer:
                for config_present in (False, True):
                    if config_present:
                        (root / "config.json").write_text("{}", encoding="utf-8")
                    with self.assertRaisesRegex(FileNotFoundError, "scripts/train_intent.py"):
                        IntentClassifier(root)
                tokenizer.assert_not_called()

    def test_complete_checkpoint_loads_local_files_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config.json").write_text("{}", encoding="utf-8")
            (root / "model.safetensors").touch()
            with patch("src.intent_classifier.AutoTokenizer.from_pretrained") as tokenizer, \
                 patch("src.intent_classifier.AutoModelForSequenceClassification.from_pretrained") as model, \
                 patch("src.intent_classifier.pipeline"):
                IntentClassifier(root)
                tokenizer.assert_called_once_with(root, local_files_only=True)
                model.assert_called_once_with(root, local_files_only=True)


if __name__ == "__main__":
    unittest.main()
