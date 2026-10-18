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
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_dir)
        self.predictor = pipeline(
            "text-classification",
            model=self.model,
            tokenizer=self.tokenizer,
            device=-1,
        )

    def predict(self, text: str) -> dict[str, Any]:
        result = self.predictor(text, top_k=1)[0]
        label = result["label"]
        if label.startswith("LABEL_"):
            label = self.model.config.id2label[int(label.split("_")[-1])]
        return {"intent": label, "confidence": float(result["score"])}


def label_mappings() -> tuple[dict[str, int], dict[int, str]]:
    label_to_id = {label: index for index, label in enumerate(INTENT_LABELS)}
    id_to_label = {index: label for label, index in label_to_id.items()}
    return label_to_id, id_to_label

