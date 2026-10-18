"""Minimal multi-turn profile state for ActivIQ."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DialogueState:
    profile: dict[str, Any] = field(default_factory=dict)
    last_intent: str | None = None
    last_entities: dict[str, list[str]] = field(default_factory=dict)

    def update(self, intent: str, entities: dict[str, list[str]]) -> dict[str, Any]:
        self.last_intent = intent
        self.last_entities = entities
        for key, values in entities.items():
            if values:
                self.profile[key] = values if len(values) > 1 else values[0]
        return self.snapshot()

    def inherit(self, entities: dict[str, list[str]]) -> dict[str, list[str]]:
        merged = {key: list(values) for key, values in entities.items()}
        for key, value in self.profile.items():
            if not merged.get(key):
                merged[key] = value if isinstance(value, list) else [value]
        return merged

    def reset(self) -> None:
        self.profile.clear()
        self.last_intent = None
        self.last_entities.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "profile": dict(self.profile),
            "last_intent": self.last_intent,
            "last_entities": dict(self.last_entities),
        }

