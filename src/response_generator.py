"""Controlled response generation for supported intents."""

from __future__ import annotations

import json
from typing import Any
from pathlib import Path
import re

from src.knowledge_base import KnowledgeBase
from src.planner import build_plan


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "responses.json"
TEMPLATES = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8")) if TEMPLATE_PATH.exists() else {}


class ResponseGenerator:
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    def generate(self, intent: str, entities: dict[str, list[str]], profile: dict[str, Any]) -> str:
        if intent in TEMPLATES:
            # Deterministic responses make demos and evaluation reproducible.
            options = TEMPLATES[intent]
            return options[0] if options else "How can I help with your fitness goal?"
        if intent == "find_exercise":
            return self._exercise_response(entities, profile)
        if intent == "get_nutrition_info":
            return self._nutrition_response(entities)
        if intent == "generate_plan":
            return self._plan_response(entities, profile)
        return "Could you rephrase that as a fitness or nutrition question?"

    def _exercise_response(self, entities, profile) -> str:
        exercise = (entities.get("exercise") or [None])[0]
        body_part = (entities.get("body_part") or [None])[0]
        equipment = (entities.get("equipment") or [None])[0]
        level = (entities.get("level") or ["beginner"])[0]
        results = self.knowledge_base.find_exercises(exercise, body_part, equipment, level, limit=1)
        # An explicit exercise request should still return instructions when
        # the database labels that exercise intermediate/advanced.
        if not results and exercise:
            results = self.knowledge_base.find_exercises(exercise, body_part, equipment, None, limit=1)
        if not results:
            return "I could not find that exercise. Could you provide another exercise name or muscle group?"
        item = results[0]
        instructions = item.get("instructions", [])
        steps = " ".join(f"{index + 1}. {step}" for index, step in enumerate(instructions[:4]))
        target = ", ".join(item.get("primary_muscles", [])) or "the requested muscles"
        return f"{item['name']} targets {target}. {steps or 'Use controlled form and a comfortable range of motion.'}"

    def _nutrition_response(self, entities) -> str:
        query = " ".join(entities.get("food", []) or entities.get("exercise", []))
        query = re.sub(
            r"\b(?:how many calories are in|how much protein is in|nutrition facts for|nutrition information for|what are the nutrients in)\b",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip(" ?.!,")
        query = re.sub(r"^(?:a|an|the)\s+", "", query, flags=re.IGNORECASE)
        if not query:
            return "Which food would you like nutrition information for?"
        results = self.knowledge_base.search_food(query, limit=1)
        if not results:
            return "I could not find that food in the local nutrition database."
        item = results[0]
        values = item.get("nutrients", {})
        energy = values.get("Energy", {}).get("amount", "unknown")
        protein = values.get("Protein", {}).get("amount", "unknown")
        fat = values.get("Total lipid (fat)", {}).get("amount", "unknown")
        carbs = values.get("Carbohydrate, by difference", {}).get("amount", "unknown")
        return f"{item['description']}: {energy} kcal, {protein} g protein, {carbs} g carbohydrates, and {fat} g fat per 100 g."

    def _plan_response(self, entities, profile) -> str:
        level = (entities.get("level") or [profile.get("level", "beginner")])[0]
        equipment = (entities.get("equipment") or [profile.get("equipment")])[0]
        body_part = (entities.get("body_part") or [None])[0]
        requested_days = (entities.get("days") or [profile.get("days", "3")])[0]
        try:
            number_of_days = max(1, min(int(requested_days), 7))
        except (TypeError, ValueError):
            number_of_days = 3
        plan = build_plan(self.knowledge_base, level, equipment, body_part, number_of_days)
        lines = [f"Here is a {number_of_days}-day {level} full-body plan:"]
        for day in plan:
            names = ", ".join(exercise["name"] for exercise in day["exercises"])
            if not names:
                names = "No matching local exercises found"
            sets = day["exercises"][0]["sets"] if day["exercises"] else (3 if level == "beginner" else 4)
            lines.append(f"Day {day['day']}: {names} — {sets} sets of 8-12 reps, 60-90 seconds rest.")
        lines.append("Warm up first, use controlled form, and stop if you feel pain.")
        return "\n".join(lines)
