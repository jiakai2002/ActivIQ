"""Transparent spaCy rule-based fitness entity extraction."""

from __future__ import annotations

import json
import re
from pathlib import Path

try:
    import spacy
    from spacy.matcher import PhraseMatcher
except (ImportError, OSError):
    spacy = None
    PhraseMatcher = None

from src.config import PROCESSED_DATA_DIR
from src.nutrition import extract_nutrition
from src.vocabulary import BODY_PARTS, EQUIPMENT, EXERCISE_ALIASES, tokens


ENTITY_TYPES = ("exercise", "body_part", "equipment", "goal", "level", "duration", "days")
GOALS = {
    "muscle gain": ["muscle gain", "build muscle", "building muscle", "gain muscle", "gaining muscle",
                    "hypertrophy", "bulk"],
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
    def __init__(
        self,
        exercise_path: Path = PROCESSED_DATA_DIR / "exercises.json",
        nutrition_path: Path = PROCESSED_DATA_DIR / "nutrition.json",
    ):
        self.nlp = spacy.blank("en") if spacy is not None else None
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER") if self.nlp else None
        self.canonical: dict[str, str] = {}
        self.fallback_patterns: list[tuple[str, str, str]] = []

        self._add_phrases("exercise", _load_exercise_names(exercise_path))
        for canonical, aliases in EXERCISE_ALIASES.items():
            self._add_phrases("exercise", aliases, canonical)
        self.food_names: set[frozenset[str]] = set()
        self.nutrient_names: set[str] = set()
        if nutrition_path.exists():
            for food in json.loads(nutrition_path.read_text(encoding="utf-8")):
                description = food.get("description", "")
                self.food_names.add(frozenset(tokens(description)))
                self.food_names.add(frozenset(tokens(description.split(",")[0])))
                self.nutrient_names.update(food.get("nutrients", {}))
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
                found[entity_type].append((doc[start].idx, doc[end - 1].idx + len(doc[end - 1]), value))
        else:
            lowered = text.casefold()
            for entity_type, phrase, value in sorted(
                self.fallback_patterns, key=lambda item: len(item[1]), reverse=True
            ):
                for match in re.finditer(rf"(?<!\w){re.escape(phrase.casefold())}(?!\w)", lowered):
                    found[entity_type].append((match.start(), match.end(), value))

        entities = {
            kind: self._deduplicate(sorted(values, key=lambda item: (-(item[1] - item[0]), item[0])))
            for kind, values in found.items()
        }
        duration_matches = re.findall(
            r"(?<![\w.])(-?\d+(?:\.\d+)?)(?:\s|-)*(seconds?|minutes?|mins?|hours?)\b",
            text.casefold(),
        )
        durations = []
        for amount, unit in duration_matches:
            unit = "minute" if unit.startswith("min") else unit.rstrip("s")
            durations.append(f"{amount} {unit}{'' if abs(float(amount)) == 1 else 's'}")
        entities["duration"] = list(dict.fromkeys(durations))
        numbers = {name: str(i) for i, name in enumerate(("zero", "one", "two", "three", "four", "five", "six", "seven"))}
        day_matches = re.findall(r"(?<![\w.])(-?\d+(?:\.\d+)?|zero|one|two|three|four|five|six|seven)(?:\s|-)*days?\b", text.casefold())
        entities["days"] = list(dict.fromkeys(numbers.get(value, value) for value in day_matches))
        # Capture unknown exercise names in explicit how-to requests so they
        # produce a lookup failure rather than an arbitrary recommendation.
        explicit = re.search(
            r"\b(?:how (?:do i|to) (?:do |perform |use )|how to |demonstrate )(.+?)(?:[?.!]|$)",
            text.casefold(),
        )
        if explicit:
            name = re.sub(r"^(?:a|an|the)\s+", "", explicit[1]).strip()
            name = re.sub(r"^proper\s+", "", name)
            name = re.split(r"\s+(?:with|without|using|for)\s+", name, maxsplit=1)[0]
            name = re.sub(r"\s+(?:at home|properly|correctly|safely)$", "", name)
            for canonical, aliases in EXERCISE_ALIASES.items():
                if name in aliases:
                    name = canonical
                    break
            if name and not re.search(r"\b(plan|nutrition|protein|calories)\b", name):
                entities["exercise"] = [name]
        entities.update(extract_nutrition(text, self.food_names, self.nutrient_names))
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
