"""Local exercise and nutrition knowledge-base access."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import PROCESSED_DATA_DIR
from src.vocabulary import MUSCLE_GROUPS, as_list, canonical_equipment, tokens


def _tokens(text: str) -> set[str]:
    return tokens(text)


class KnowledgeBase:
    def __init__(self, data_dir: Path = PROCESSED_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.exercises = self._load_json("exercises.json")
        self.nutrition = self._load_json("nutrition.json")

    def _load_json(self, filename: str) -> list[dict[str, Any]]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, list) else []

    def find_exercises(
        self,
        exercise: str | None = None,
        body_part: str | list[str] | None = None,
        equipment: str | list[str] | None = None,
        level: str | None = None,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        limit = max(0, int(limit))
        query_tokens = _tokens(exercise or "")
        requested_equipment = {canonical_equipment(value) for value in as_list(equipment)}
        requested_muscles = set()
        for part in as_list(body_part):
            requested_muscles.update(MUSCLE_GROUPS.get(part.casefold(), {part.casefold()}))
        scored: list[tuple[int, dict[str, Any]]] = []
        for item in self.exercises:
            name = str(item.get("name", ""))
            score = 0
            name_tokens = _tokens(name)
            if exercise and (not query_tokens or not query_tokens.issubset(name_tokens)):
                continue
            muscles = {str(value).casefold() for value in item.get("primary_muscles", [])}
            muscles.update(str(value).casefold() for value in item.get("secondary_muscles", []))
            if requested_muscles and not (requested_muscles & muscles):
                continue
            if requested_equipment and canonical_equipment(item.get("equipment")) not in requested_equipment:
                continue
            if level and str(item.get("level") or "").casefold() != level.casefold():
                continue
            score += 100 if query_tokens and query_tokens == name_tokens else 0
            score += 10 * len(requested_muscles & set(item.get("primary_muscles", [])))
            score -= len(name_tokens) if query_tokens else 0
            scored.append((score, item))
        scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("name", ""))))
        return [item for _, item in scored[:limit]]

    def search_food(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        limit = max(0, int(limit))
        query_tokens = _tokens(query)
        if not query_tokens:
            return []
        matches: list[tuple[tuple[int, int, int], dict[str, Any]]] = []
        exact = []
        for item in self.nutrition:
            description = str(item.get("description", ""))
            description_tokens = _tokens(description)
            if query_tokens == description_tokens:
                exact.append(item)
            if query_tokens.issubset(description_tokens):
                # Prefer base foods and raw examples in clarification choices,
                # but never silently select one of several plausible records.
                first_word = _tokens(description.split(",")[0].split()[0]) if description.split() else set()
                rank = (int(first_word.isdisjoint(query_tokens)), int("raw" not in description_tokens),
                        len(description_tokens - query_tokens))
                matches.append((rank, item))
        if exact:
            return sorted(exact, key=lambda item: str(item.get("description", "")))[:limit]
        matches.sort(key=lambda pair: (pair[0], str(pair[1].get("description", ""))))
        return [item for _, item in matches[:limit]]
