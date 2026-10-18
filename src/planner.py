"""Simple deterministic workout-plan generation."""

from __future__ import annotations

from typing import Any

from src.knowledge_base import KnowledgeBase


def build_plan(
    knowledge_base: KnowledgeBase,
    level: str = "beginner",
    equipment: str | None = None,
    body_part: str | None = None,
    days: int = 3,
) -> list[dict[str, Any]]:
    """Create a configurable multi-day full-body plan from local exercises."""

    day_count = max(1, min(int(days), 7))

    pool = knowledge_base.find_exercises(
        body_part=body_part,
        equipment=equipment,
        level=level,
        limit=24,
    )
    if len(pool) < day_count * 3:
        pool = knowledge_base.find_exercises(equipment=equipment, level=level, limit=24)
    if len(pool) < day_count * 3:
        pool = knowledge_base.find_exercises(limit=24)

    selected = []
    seen_muscles: set[str] = set()
    for item in pool:
        muscles = set(item.get("primary_muscles", []))
        if muscles - seen_muscles or len(selected) < 6:
            selected.append(item)
            seen_muscles.update(muscles)
        if len(selected) == day_count * 3:
            break

    # Repeat only when the local database has fewer than nine suitable
    # records. This keeps the UI useful with small test fixtures while still
    # preferring distinct exercises for the normal dataset.
    if selected and len(selected) < day_count * 3:
        selected = (selected * ((day_count * 3 + len(selected) - 1) // len(selected)))[: day_count * 3]

    plan = []
    for index in range(day_count):
        exercises = selected[index * 3 : (index + 1) * 3]
        plan.append(
            {
                "day": index + 1,
                "exercises": [
                    {
                        "name": item.get("name"),
                        "sets": 3 if level == "beginner" else 4,
                        "repetitions": "8-12",
                        "rest": "60-90 seconds",
                    }
                    for item in exercises
                ],
            }
        )
    return plan


def build_three_day_plan(
    knowledge_base: KnowledgeBase,
    level: str = "beginner",
    equipment: str | None = None,
    body_part: str | None = None,
) -> list[dict[str, Any]]:
    """Backward-compatible three-day plan helper."""

    return build_plan(knowledge_base, level, equipment, body_part, days=3)
