"""Shared canonical vocabulary for extraction and local retrieval."""

import re


MUSCLE_GROUPS = {
    "chest": {"chest"},
    "back": {"lats", "lower back", "middle back", "traps"},
    "shoulders": {"shoulders"},
    "arms": {"biceps", "triceps", "forearms"},
    "legs": {"quadriceps", "hamstrings", "calves", "adductors", "abductors", "glutes"},
    "core": {"abdominals"},
    "glutes": {"glutes"},
}

BODY_PARTS = {
    "chest": ["chest", "pecs", "pectorals"],
    "back": ["back"],
    "lats": ["lats", "latissimus"],
    "lower back": ["lower back"],
    "middle back": ["middle back"],
    "shoulders": ["shoulders", "delts", "deltoids"],
    "arms": ["arms"],
    "biceps": ["biceps"],
    "triceps": ["triceps"],
    "forearms": ["forearms"],
    "legs": ["legs"],
    "quadriceps": ["quads", "quadriceps"],
    "hamstrings": ["hamstrings"],
    "calves": ["calves"],
    "glutes": ["glutes", "gluteus"],
    "core": ["core", "abs", "abdominals"],
}

EQUIPMENT = {
    "bodyweight": ["bodyweight", "body weight", "body only", "no equipment", "without equipment"],
    "dumbbell": ["dumbbell", "dumbbells"],
    "barbell": ["barbell", "barbells"],
    "resistance band": ["resistance band", "resistance bands", "band", "bands"],
    "kettlebell": ["kettlebell", "kettlebells"],
    "cable": ["cable", "cables"],
    "machine": ["machine", "machines"],
}

EXERCISE_ALIASES = {
    "squat": ["squat", "squats"],
    "push up": ["push up", "push ups", "push-up", "push-ups", "pushup", "pushups"],
    "pull up": ["pull up", "pull ups", "pull-up", "pull-ups", "pullup", "pullups"],
    "lunge": ["lunge", "lunges"],
    "plank": ["plank", "planks"],
    "deadlift": ["deadlift", "deadlifts"],
    "bench press": ["bench press", "bench presses"],
}


def tokens(text: str) -> set[str]:
    """Small, explicit inflection normalisation shared by both knowledge bases."""
    result = set()
    text = re.sub(r"\b(push|pull|sit)[ -]?ups?\b", r"\1 up", text.casefold())
    for word in re.findall(r"[a-z0-9]+", text):
        if len(word) > 4 and word.endswith("ies"):
            word = word[:-3] + "y"
        elif word == "presses":
            word = "press"
        elif len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us")):
            word = word[:-1]
        result.add(word)
    return result


def canonical_equipment(value: str | None) -> str:
    if not value or value.casefold() in {"none", "body only"}:
        return "bodyweight"
    lowered = value.casefold()
    for canonical, aliases in EQUIPMENT.items():
        if lowered in aliases:
            return canonical
    return lowered


def as_list(value: str | list[str] | None) -> list[str]:
    return [value] if isinstance(value, str) else list(value or [])
