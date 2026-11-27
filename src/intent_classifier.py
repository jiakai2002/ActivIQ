"""DistilBERT intent classification for ActivIQ."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

from src.config import INTENT_LABELS, MODEL_DIR


class IntentClassifier:
    """Load a locally trained classifier and return intent probabilities."""

    def __init__(self, model_dir: Path = MODEL_DIR):
        self.model_dir = Path(model_dir)
        weight_files = ("model.safetensors", "pytorch_model.bin",
                        "model.safetensors.index.json", "pytorch_model.bin.index.json")
        if not (self.model_dir / "config.json").is_file() or not any(
            (self.model_dir / name).is_file() for name in weight_files
        ):
            raise FileNotFoundError(
                f"Trained intent checkpoint missing or incomplete at {self.model_dir}. "
                "Run python scripts/train_intent.py or restore the complete trained checkpoint there."
            )
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_dir, local_files_only=True)
        self.predictor = pipeline(
            "text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            device=-1,
        )

    def predict(self, text: str) -> dict[str, Any]:
        # Match the training token limit and avoid positional-embedding errors
        # on long messages. Safety checks inspect the complete text first.
        result = self.predictor(text, top_k=1, truncation=True, max_length=64)[0]
        label = result["label"]
        if label.startswith("LABEL_"):
            label = self.model.config.id2label[int(label.split("_")[-1])]
        return {"intent": label, "confidence": float(result["score"])}


def label_mappings() -> tuple[dict[str, int], dict[int, str]]:
    label_to_id = {label: index for index, label in enumerate(INTENT_LABELS)}
    id_to_label = {index: label for label, index in label_to_id.items()}
    return label_to_id, id_to_label

