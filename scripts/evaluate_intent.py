"""Evaluate a trained ActivIQ intent classifier on the untouched test split."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PROCESSED_DATA_DIR
from src.intent_classifier import IntentClassifier


def macro_f1(labels, predictions, class_count: int) -> float:
    scores = []
    for label in range(class_count):
        true_positive = sum(y == label and p == label for y, p in zip(labels, predictions))
        false_positive = sum(y != label and p == label for y, p in zip(labels, predictions))
        false_negative = sum(y == label and p != label for y, p in zip(labels, predictions))
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
        scores.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    return sum(scores) / class_count


def main() -> None:
    data = pd.read_csv(PROCESSED_DATA_DIR / "intents" / "test.csv")
    classifier = IntentClassifier()
    predictions = [classifier.predict(text)["intent"] for text in data["text"]]
    labels = sorted(data["label"].unique())
    label_to_id = {label: index for index, label in enumerate(labels)}
    expected = [label_to_id[label] for label in data["label"]]
    actual = [label_to_id[label] for label in predictions]
    accuracy = sum(expected == actual for expected, actual in zip(expected, actual)) / len(expected)
    print(f"accuracy={accuracy:.4f}")
    print(f"macro_f1={macro_f1(expected, actual, len(labels)):.4f}")
    for label in labels:
        correct = sum(expected == actual == label_to_id[label] for expected, actual in zip(expected, actual))
        total = sum(expected == label_to_id[label] for expected in expected)
        print(f"{label}: {correct}/{total}")


if __name__ == "__main__":
    main()
