"""Transparent spaCy rule-based fitness entity extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    import spacy
    from spacy.matcher import PhraseMatcher
except (ImportError, OSError):
    spacy = None
    PhraseMatcher = None

from src.config import PROCESSED_DATA_DIR


ENTITY_TYPES = ("exercise", "body_part", "equipment", "goal", "level", "duration", "days")

BODY_PARTS = {
    "chest": ["chest", "pecs", "pectorals"],
    "back": ["back", "lats", "latissimus"],
    "shoulders": ["shoulders", "delts", "deltoids"],
    "arms": ["arms", "biceps", "triceps"],
    "legs": ["legs", "quads", "quadriceps", "hamstrings", "calves"],
    "glutes": ["glutes", "gluteus"],
    "core": ["core", "abs", "abdominals"],
}
EQUIPMENT = {
    "bodyweight": ["bodyweight", "body weight", "no equipment"],
    "dumbbell": ["dumbbell", "dumbbells"],
    "barbell": ["barbell", "barbells"],
    "resistance band": ["resistance band", "resistance bands", "bands"],
    "kettlebell": ["kettlebell", "kettlebells"],
    "cable": ["cable", "cables"],
    "machine": ["machine", "machines"],
}
GOALS = {
    "muscle gain": ["muscle gain", "build muscle", "hypertrophy", "bulk"],
    "fat loss": ["fat loss", "lose fat", "weight loss", "lose weight", "cut"],
    "strength": ["strength", "get stronger"],
    "endurance": ["endurance", "stamina", "conditioning"],
    "flexibility": ["flexibility", "mobility", "stretching"],
}
LEVELS = {
    "beginner": ["beginner", "beginners", "new to training", "novice"],
    "intermediate": ["intermediate"],
    "expert": ["expert", "advanced"],
}


def _load_exercise_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    return [record["name"] for record in records if record.get("name")]


class FitnessEntityExtractor:
    def __init__(self, exercise_path: Path = PROCESSED_DATA_DIR / "exercises.json"):
        self.nlp = spacy.blank("en") if spacy is not None else None
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER") if self.nlp else None
        self.canonical: dict[str, dict[str, str]] = {}
        self.fallback_patterns: list[tuple[str, str, str]] = []

        self._add_phrases("exercise", _load_exercise_names(exercise_path))
        for entity_type, groups in (
            ("body_part", BODY_PARTS),
            ("equipment", EQUIPMENT),
            ("goal", GOALS),
            ("level", LEVELS),
        ):
            for canonical, aliases in groups.items():
                self._add_phrases(entity_type, aliases, canonical)

    def _add_phrases(self, entity_type: str, phrases: list[str], canonical: str | None = None):
        key = f"{entity_type}"
        if self.matcher is not None:
            self.matcher.add(key, [self.nlp.make_doc(phrase) for phrase in phrases if phrase])
        for phrase in phrases:
            normalized = canonical or phrase.casefold()
            self.canonical[f"{entity_type}:{phrase.casefold()}"] = normalized
            self.fallback_patterns.append((entity_type, phrase, normalized))

    def extract(self, text: str) -> dict[str, list[str]]:
        found: dict[str, list[tuple[int, int, str]]] = {kind: [] for kind in ENTITY_TYPES}
        if self.matcher is not None:
            doc = self.nlp(text)
            for match_id, start, end in self.matcher(doc):
                entity_type = self.nlp.vocab.strings[match_id]
                phrase = doc[start:end].text.casefold()
                value = self.canonical.get(f"{entity_type}:{phrase}", phrase)
                found[entity_type].append((start, end, value))
        else:
            lowered = text.casefold()
            for entity_type, phrase, value in sorted(
                self.fallback_patterns, key=lambda item: len(item[1]), reverse=True
            ):
                for match in re.finditer(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", lowered):
                    found[entity_type].append((match.start(), match.end(), value))

        entities = {
            kind: self._deduplicate(sorted(values, key=lambda item: (item[0], -(item[1] - item[0]))))
            for kind, values in found.items()
        }
        duration_matches = re.findall(
            r"\b\d+(?:\.\d+)?\s*(?:seconds?|minutes?|mins?|hours?|days?|weeks?|months?)\b",
            text.casefold(),
        )
        entities["duration"] = list(dict.fromkeys(duration_matches))
        day_matches = re.findall(r"\b([2-7])(?:\s|-)*days?\b", text.casefold())
        entities["days"] = list(dict.fromkeys(day_matches))
        return entities

    @staticmethod
    def _deduplicate(matches: list[tuple[int, int, str]]) -> list[str]:
        values: list[str] = []
        occupied: list[tuple[int, int]] = []
        for start, end, value in matches:
            if any(start >= left and end <= right for left, right in occupied):
                continue
            occupied.append((start, end))
            if value not in values:
                values.append(value)
        return values
