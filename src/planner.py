"""Deterministic, constraint-preserving workout templates."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from src.knowledge_base import KnowledgeBase
from src.vocabulary import MUSCLE_GROUPS


# Application heuristics, not a validated coaching or progression model.
PRESCRIPTIONS = {
    "muscle gain": (3, "8-12", 75, 36),
    "strength": (3, "4-6", 120, 24),
    "fat loss": (3, "10-15", 45, 45),
    "endurance": (2, "15-20", 30, 60),
    "flexibility": (2, "20-30 seconds", 20, 30),
}


def duration_minutes(duration: str | None) -> float | None:
    if not duration:
        return None
    matches = re.findall(r"(-?\d+(?:\.\d+)?)(?:\s|-)*(seconds?|minutes?|mins?|hours?)\b", duration)
    if not matches:
        raise ValueError("Please give the session duration in minutes or hours.")
    total = sum(float(value) * (60 if unit.startswith("hour") else 1 / 60 if unit.startswith("second") else 1)
                for value, unit in matches)
    if total <= 0 or any(float(value) <= 0 for value, _ in matches):
        raise ValueError("Please give a session duration greater than zero.")
    return total


def build_plan(
    knowledge_base: KnowledgeBase,
    level: str = "beginner",
    equipment: str | list[str] | None = None,
    body_part: str | list[str] | None = None,
    days: int = 3,
    goal: str | None = None,
    duration: str | None = None,
) -> list[dict[str, Any]]:
    """Keep every requested filter; shortages never widen the candidate pool.

    Prefer less-used exercises and different primary muscles within each day.
    Reuse across days is explicit in the response, never within the same day.
    """
    day_count = int(days)
    if not 1 <= day_count <= 7:
        raise ValueError("Please choose between 1 and 7 workout days.")
    budget = duration_minutes(duration)
    pool = knowledge_base.find_exercises(body_part=body_part, equipment=equipment, level=level,
                                         limit=len(knowledge_base.exercises))
    if goal == "flexibility":
        pool = [item for item in pool if item.get("category") == "stretching"]
    else:
        pool = [item for item in pool if item.get("category") != "stretching"]

    sets, repetitions, rest, work_seconds = PRESCRIPTIONS.get(goal, (3, "8-12", 75, 36))
    sets += int(level != "beginner")
    warmup_minutes = 5
    exercise_minutes = (sets * work_seconds + (sets - 1) * rest + 60) / 60
    count = 3 if budget is None else min(6, max(0, math.floor((budget - warmup_minutes) / exercise_minutes)))
    usage = {str(item["id"]): 0 for item in pool}
    group_usage: Counter[str] = Counter()

    def groups(item):
        primary = set(item.get("primary_muscles", []))
        return {group for group in ("chest", "back", "shoulders", "arms", "legs", "core")
                if MUSCLE_GROUPS[group] & primary} or primary

    plan = []
    for index in range(day_count):
        chosen = []
        muscles: set[str] = set()
        candidates = list(pool)
        while candidates and len(chosen) < count:
            item = min(candidates, key=lambda candidate: (
                usage[str(candidate["id"])],
                sum(group_usage[group] for group in groups(candidate)),
                -len(set(candidate.get("primary_muscles", [])) - muscles),
                str(candidate.get("name", "")),
            ))
            candidates.remove(item)
            chosen.append(item)
            muscles.update(item.get("primary_muscles", []))
            usage[str(item["id"])] += 1
            group_usage.update(groups(item))
        plan.append({
            "day": index + 1,
            "estimated_minutes": round(warmup_minutes + len(chosen) * exercise_minutes, 1) if chosen else 0,
            "limitation": "duration" if count == 0 else "no_matches" if not pool else None,
            "exercises": [{
                "name": item["name"], "sets": sets, "repetitions": repetitions,
                "rest": f"{rest} seconds",
            } for item in chosen],
        })
    return plan


def build_three_day_plan(
    knowledge_base: KnowledgeBase,
    level: str = "beginner",
    equipment: str | list[str] | None = None,
    body_part: str | list[str] | None = None,
) -> list[dict[str, Any]]:
    """Backward-compatible three-day plan helper."""
    return build_plan(knowledge_base, level, equipment, body_part, days=3)
