"""Session preferences and task-scoped multi-turn context."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.vocabulary import tokens


PREFERENCES = {"goal", "level", "equipment", "duration", "days"}
TASK_SLOTS = {
    "generate_plan": {"body_part"},
    "find_exercise": {"exercise", "body_part"},
    "get_nutrition_info": {"food", "nutrient", "quantity_g", "serving"},
}


@dataclass
class DialogueState:
    profile: dict[str, Any] = field(default_factory=dict)
    last_intent: str | None = None
    last_entities: dict[str, list[str]] = field(default_factory=dict)

    def update(self, intent: str, entities: dict[str, list[str]]) -> dict[str, Any]:
        self.last_intent = intent
        allowed = TASK_SLOTS.get(intent, set()) | PREFERENCES
        self.last_entities = {key: list(values) for key, values in entities.items() if key in allowed and values}
        for key in PREFERENCES:
            values = entities.get(key, [])
            if values:
                self.profile[key] = list(values) if len(values) > 1 else values[0]
        return self.snapshot()

    def inherit(self, entities: dict[str, list[str]], intent: str | None = None,
                followup: bool = False) -> dict[str, list[str]]:
        intent = intent or self.last_intent
        merged = {key: list(values) for key, values in entities.items()}
        if intent != "get_nutrition_info":
            for key, value in self.profile.items():
                if not merged.get(key):
                    merged[key] = list(value) if isinstance(value, list) else [value]
        if followup and intent == self.last_intent:
            for key in TASK_SLOTS.get(intent, set()):
                if not merged.get(key) and self.last_entities.get(key):
                    merged[key] = list(self.last_entities[key])
            # A new muscle request replaces the old exercise; a new exercise
            # replaces the old muscle filter unless the user supplies both.
            if intent == "find_exercise":
                if entities.get("body_part") and not entities.get("exercise"):
                    merged.pop("exercise", None)
                if entities.get("exercise") and not entities.get("body_part"):
                    merged.pop("body_part", None)
            if intent == "get_nutrition_info":
                old_food = self.last_entities.get("food", [])
                new_food = entities.get("food", [])
                refining_food = bool(old_food and new_food and tokens(old_food[0]).issubset(tokens(new_food[0])))
                if new_food and not entities.get("quantity_g") and not refining_food:
                    merged.pop("quantity_g", None)
                    merged.pop("serving", None)
                if entities.get("quantity_g"):
                    merged.pop("serving", None)
        return merged

    def reset(self) -> None:
        self.profile.clear()
        self.last_intent = None
        self.last_entities.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "profile": {key: list(value) if isinstance(value, list) else value for key, value in self.profile.items()},
            "last_intent": self.last_intent,
            "last_entities": {key: list(value) for key, value in self.last_entities.items()},
        }
