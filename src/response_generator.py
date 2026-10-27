"""Controlled responses that preserve user constraints and dataset limits."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from src.knowledge_base import KnowledgeBase
from src.planner import build_plan


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "templates" / "responses.json"
TEMPLATES = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8")) if TEMPLATE_PATH.exists() else {}


class ResponseGenerator:
    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    def generate(self, intent: str, entities: dict[str, list[str]], profile: dict[str, Any]) -> str:
        if intent in TEMPLATES:
            return self._template_response(intent, entities, profile)
        if intent == "find_exercise":
            return self._exercise_response(entities, profile)
        if intent == "get_nutrition_info":
            return self._nutrition_response(entities)
        if intent == "generate_plan":
            return self._plan_response(entities, profile)
        return "Could you rephrase that as a fitness or nutrition question?"

    def _template_response(self, intent: str, entities, profile) -> str:
        options = TEMPLATES.get(intent, [])
        if not options:
            return "How can I help with your fitness goal?"
        context = sum(len(str(value)) for value in profile.values()) + len(entities)
        response = options[context % len(options)]
        if intent == "log_feeling" and profile.get("level"):
            response += f" Since you’re training at a {profile['level']} level, adjust the intensity to match your recovery."
        if intent == "general_chat" and profile.get("goal"):
            response += f" I can help you work toward your {profile['goal']} goal."
        return response

    def _exercise_response(self, entities, profile) -> str:
        exercise = (entities.get("exercise") or [None])[0]
        body_parts = entities.get("body_part")
        equipment = entities.get("equipment")
        level = (entities.get("level") or ["beginner"])[0]
        if not exercise and not body_parts:
            return "Which exercise or muscle group would you like instructions for?"
        results = self.knowledge_base.find_exercises(exercise, body_parts, equipment, level, limit=1)
        if not results and exercise:
            # An explicit how-to may explain a harder exercise, but its actual
            # database level must be shown, rather than relabelled beginner.
            results = self.knowledge_base.find_exercises(exercise, body_parts, equipment, None, limit=1)
        if not results:
            return "I could not find an exercise matching those constraints. Please give another exercise name, muscle group, or equipment choice."
        item = results[0]
        target = ", ".join(item.get("primary_muscles", [])) or "unspecified muscles"
        intro = (f"{item['name']} targets {target} and uses {item.get('equipment') or 'bodyweight'}. "
                 f"The local database lists its level as {item.get('level') or 'unspecified'}.")
        instructions = item.get("instructions", [])
        steps = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(instructions))
        return f"{intro}\n\n{steps or 'No instructions are available for this record.'}\n\nKeep the movement controlled and stop if you feel pain."

    def _nutrition_response(self, entities) -> str:
        foods = entities.get("food", [])
        if not foods:
            return "Which food would you like nutrition information for? Include its preparation, such as raw or cooked."
        if len(foods) > 1:
            return "Please ask about one food at a time, including its preparation."
        if entities.get("serving"):
            return "Please give the serving weight in grams (for example, 200 g). Household serving sizes vary by food and preparation."
        try:
            grams = float((entities.get("quantity_g") or ["100"])[0])
        except (ValueError, TypeError):
            grams = 0
        if not math.isfinite(grams) or grams <= 0:
            return "Please give a food weight greater than zero in grams."
        results = self.knowledge_base.search_food(foods[0], limit=6)
        if not results:
            return "I could not find that food and preparation in the local nutrition database. Please give a more specific food name."
        if len(results) > 1:
            choices = "\n".join(f"- {item['description']}" for item in results[:5])
            return f"Several foods match. Which exact food and preparation do you mean?\n{choices}\nReply with the food name and preparation."
        item = results[0]
        values = item.get("nutrients", {})
        requested = entities.get("nutrient") or ["Energy", "Protein", "Carbohydrate, by difference", "Total lipid (fat)"]
        lines = [f"For {grams:g} g of {item['description']}:"]
        for nutrient in requested:
            value = values.get(nutrient, {})
            amount, unit = value.get("amount"), value.get("unit")
            if not isinstance(amount, (int, float)) or not math.isfinite(amount) or not unit:
                lines.append(f"- {nutrient}: not available in the local dataset.")
            else:
                display_unit = {"G": "g", "MG": "mg", "UG": "mcg", "KCAL": "kcal", "KJ": "kJ"}.get(unit.upper(), unit)
                lines.append(f"- {nutrient}: {amount * grams / 100:.4g} {display_unit}")
        lines.append("Values are scaled from the database's 100 g basis; preparation and serving size matter.")
        return "\n".join(lines)

    def _plan_response(self, entities, profile) -> str:
        for slot, label in (("level", "experience level"), ("goal", "main goal"), ("days", "number of workout days")):
            if len(entities.get(slot, [])) > 1:
                return f"Please choose one {label} for this plan."
        level = (entities.get("level") or ["beginner"])[0]
        equipment = entities.get("equipment") or ["bodyweight"]
        body_parts = entities.get("body_part")
        goal = (entities.get("goal") or [None])[0]
        duration = " ".join(entities.get("duration", [])) or None
        try:
            days = int((entities.get("days") or ["3"])[0])
        except (TypeError, ValueError):
            return "Please choose a whole number between 1 and 7 workout days."
        try:
            plan = build_plan(self.knowledge_base, level, equipment, body_parts, days, goal, duration)
        except (TypeError, ValueError) as error:
            return str(error)
        if not any(day["exercises"] for day in plan):
            if not self.knowledge_base.exercises:
                return "The local exercise database is empty. Add exercise data before creating a plan."
            if any(day["limitation"] == "duration" for day in plan):
                return "That session duration is too short for this workout template, including its warm-up. Please choose a longer session."
            return "No local exercises match all those constraints. Would you like to change the equipment, muscle focus, level, or goal?"
        focus = ", ".join(body_parts) if body_parts else "a mix of available muscle groups"
        lines = [f"Here’s a {days}-day {level} plan for {focus}, using {', '.join(equipment)}."]
        if not entities.get("equipment"):
            lines.append("I assumed bodyweight equipment; tell me if you have other equipment.")
        lines.append(f"Goal: {goal or 'general fitness'}. " + (f"Session budget: {duration}." if duration else "No session time limit specified."))
        for day in plan:
            lines.append(f"\nDay {day['day']} (estimated {day['estimated_minutes']:g} minutes, including warm-up):")
            for exercise in day["exercises"]:
                lines.append(f"- {exercise['name']}: {exercise['sets']} sets of {exercise['repetitions']}; rest {exercise['rest']}.")
        names = [exercise["name"] for day in plan for exercise in day["exercises"]]
        if len(names) != len(set(names)):
            lines.append("Some matching exercises repeat across days; each day uses distinct exercises.")
        lines.append("Estimated times include five minutes for warm-up and one minute per exercise for transitions; actual times may vary.")
        lines.append("Spread workout days across your schedule with recovery between sessions; stop if you feel pain.")
        return "\n".join(lines)
