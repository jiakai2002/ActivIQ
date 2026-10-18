"""Fine-tune DistilBERT on the untouched ActivIQ intent splits."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import INTENT_LABELS, MODEL_DIR, PROCESSED_DATA_DIR


def macro_f1(labels, predictions) -> float:
    scores = []
    for label in range(len(INTENT_LABELS)):
        true_positive = sum(y == label and p == label for y, p in zip(labels, predictions))
        false_positive = sum(y != label and p == label for y, p in zip(labels, predictions))
        false_negative = sum(y == label and p != label for y, p in zip(labels, predictions))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    return float(np.mean(scores))


def load_split(name: str) -> Dataset:
    frame = pd.read_csv(PROCESSED_DATA_DIR / "intents" / f"{name}.csv")
    frame["label"] = frame["label"].map({label: i for i, label in enumerate(INTENT_LABELS)})
    return Dataset.from_pandas(frame[["text", "label"]], preserve_index=False)


def main() -> None:
    tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")
    train = load_split("train")
    validation = load_split("validation")

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=64)

    train = train.map(tokenize, batched=True)
    validation = validation.map(tokenize, batched=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        "distilbert-base-uncased",
        num_labels=len(INTENT_LABELS),
        id2label={i: label for i, label in enumerate(INTENT_LABELS)},
        label2id={label: i for i, label in enumerate(INTENT_LABELS)},
    )

    def metrics(eval_prediction):
        predictions, labels = eval_prediction
        predicted = np.argmax(predictions, axis=-1)
        return {
            "accuracy": float(np.mean(labels == predicted)),
            "macro_f1": macro_f1(labels, predicted),
        }

    arguments = TrainingArguments(
        output_dir=str(MODEL_DIR / "checkpoints"),
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        num_train_epochs=3,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        report_to="none",
    )
    trainer = Trainer(
        model=model,
        args=arguments,
        train_dataset=train,
        eval_dataset=validation,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=metrics,
    )
    trainer.train()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(MODEL_DIR)
    tokenizer.save_pretrained(MODEL_DIR)
    print(f"Saved model to {MODEL_DIR}")


if __name__ == "__main__":
    main()
