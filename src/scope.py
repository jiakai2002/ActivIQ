"""Transparent evidence for the chatbot's supported domain and task types."""

from __future__ import annotations

import re

from src.vocabulary import BODY_PARTS, EQUIPMENT, tokens


CLARIFICATION_RESPONSE = (
    "I’m not sure I understood. Are you asking for a workout plan, "
    "exercise instructions, or nutrition information?"
)

_CONTRACTIONS = {
    "can't": "cannot", "cannot": "cannot", "don't": "do not", "doesn't": "does not",
    "didn't": "did not", "haven't": "have not", "hasn't": "has not", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not", "i'm": "i am",
    "i've": "i have", "won't": "will not", "wouldn't": "would not",
}
_CONTRACTION_PATTERN = re.compile(r"\b(?:" + "|".join(map(re.escape, _CONTRACTIONS)) + r")\b")

FITNESS_LANGUAGE = re.compile(
    r"\b(?:workouts?|fitness|exercises?|gym|bodybuilding|bodyweight|weightlifting|"
    r"lifting|cardio|warm\s*ups?|cool\s*downs?|repetitions?|reps|squats?|lunges?|"
    r"planks?|deadlifts?|push\s*ups?|pull\s*ups?|bench press|stretch(?:ing|es)?|"
    r"nutrition|nutrients?|macros?|macronutrients?|calories?|kcal|protein|carbs?|"
    r"carbohydrates?|vitamins?|minerals?|medicine balls?)\b|"
    r"\b(?:strength|resistance|endurance|flexibility|weight) training\b|"
    r"\btraining (?:plans?|routines?|weeks?|sessions?|programs?|splits?|schedules?)\b"
)
_TOPICS = re.compile(
    r"\b(?:weather|forecasts?|politics?|elections?|stock market|bitcoin|cryptocurrency|"
    r"crypto|programming|algorithms?|poems?|poetry|lyrics|movies?|films?|joan of arc|cs\d{3})\b"
)
_UNSUPPORTED_TASKS = re.compile(
    r"\b(?:write|compose|generate|create|tell)\b[^.!?;]{0,100}\b(?:poems?|poetry|lyrics|stories|novels|jokes?|code|scripts?|python)\b|"
    r"\b(?:recommend|suggest|review)\b[^.!?;]{0,60}\b(?:movies?|films?)\b|"
    r"\b(?:python|javascript|typescript|java|sql)\b[^.!?;]{0,60}\b(?:code|scripts?|programs?|trackers?|algorithms?)\b|"
    r"\b(?:print|code|debug)\b[^.!?;]{0,100}\b(?:python|javascript|sql)\b|"
    r"\b(?:train|training)\b[^.!?;]{0,40}\b(?:dogs?|puppies|pets?|horses?)\b|"
    r"\b(?:history of|capital of|stock market|password|investment)\b|"
    r"\b(?:give|write|create)\b[^.!?;]{0,60}\brecipes?\b"
)
_DIRECT_TOPIC_REQUEST = re.compile(
    r"\b(?:tell me|explain|predict|forecast|who was|who is|what is|what are)\s+"
    r"(?:(?:about|the|a|an|tomorrow|today|price|of|in|for|happening|with)\s+){0,6}"
    r"(?:weather|forecast|politics|elections?|stock market|bitcoin|cryptocurrency|"
    r"crypto|programming|poems?|poetry|movies?|films?|joan of arc)\b"
)
_REQUEST_WORDS = re.compile(r"\b(?:write|create|generate|design|make|tell|explain|predict|recommend|teach|show|who|what|how|where|when)\b")


def normalise_text(text: str) -> str:
    text = text.casefold().translate(str.maketrans({"’": "'", "‘": "'", "–": "-", "—": "-", "‑": "-"}))
    text = _CONTRACTION_PATTERN.sub(lambda match: _CONTRACTIONS[match[0]], text)
    return re.sub(r"\s+", " ", text.replace("-", " ")).strip()


def is_social_message(text: str) -> bool:
    lowered = normalise_text(text)
    if re.fullmatch(r"(?:hello|hi|hey|good morning|good evening|how are you|how is it going)[!.? ]*", lowered):
        return True
    return bool(re.match(r"^(?:thanks|thank you)\b", lowered)
                and not _REQUEST_WORDS.search(lowered) and "?" not in lowered
                and not re.search(r"\b(?:can you|could you|would you|please)\b", lowered))


def explicit_out_of_scope(text: str) -> bool:
    """Reject unsupported tasks even if they contain fitness vocabulary.

    A topic mentioned as background ('bad weather; create an indoor workout')
    does not by itself turn a valid fitness task into a weather request.
    """
    lowered = normalise_text(text)
    if _UNSUPPORTED_TASKS.search(lowered) or _DIRECT_TOPIC_REQUEST.search(lowered):
        return True
    return bool(_TOPICS.search(lowered) and not FITNESS_LANGUAGE.search(lowered))


def _slot_fragment(text: str, entities: dict, followup: bool) -> bool:
    if followup and entities.get("quantity_g") and re.fullmatch(r"-?\d+(?:\.\d+)?\s*(?:g|grams?|kg|kilograms?|oz|ounces?)[?.!]*", text):
        return True
    slots = ("body_part", "equipment", "goal", "level", "duration", "days", "nutrient")
    values = [value for slot in slots for value in entities.get(slot, [])]
    if not values:
        return False
    allowed = tokens(" ".join(values))
    # Accept explicit aliases without letting arbitrary free-text exercise/food
    # slots justify their own scope (e.g. 'how to bake a cake').
    for slot, vocabulary in (("body_part", BODY_PARTS), ("equipment", EQUIPMENT)):
        for value in entities.get(slot, []):
            allowed.update(tokens(" ".join(vocabulary.get(value, []))))
    allowed.update(tokens(
        "i am a an the have has only my available equipment is are no with use using instead for about "
        "what how much many and please want to do can you get stronger build lose weight fat muscle gain "
        "level new training beginner beginners advanced novice it make actually minutes minute mins hours "
        "hour seconds second days day per week one two three four five six seven"
    ))
    return tokens(text).issubset(allowed)


def fitness_scope_evidence(text: str, entities: dict, knowledge_base, followup: bool = False) -> str | None:
    lowered = normalise_text(text)
    if FITNESS_LANGUAGE.search(lowered):
        return "fitness_or_nutrition_language"
    if is_social_message(lowered):
        return "supported_social_message"
    if _slot_fragment(lowered, entities, followup):
        return "fitness_slots_or_followup"
    if re.search(r"\b(?:i (?:am|feel)|that (?:was|felt))\b.{0,40}\b(?:tired|exhausted|great|energised|energized|sore|hard|challenging|easy)\b", lowered):
        return "workout_feeling_language"
    if any(knowledge_base.find_exercises(exercise=name, limit=1) for name in entities.get("exercise", [])):
        return "known_exercise"
    if any(knowledge_base.search_food(name, limit=1) for name in entities.get("food", [])):
        return "known_food"
    return None


def ambiguous_fragment(text: str) -> bool:
    lowered = normalise_text(text)
    return len(lowered.split()) <= 4 and "?" not in lowered and not _REQUEST_WORDS.search(lowered)


def workout_plan_request(text: str, entities: dict, contextual_plan: bool) -> bool:
    lowered = normalise_text(text)
    if contextual_plan and _slot_fragment(lowered, entities, True):
        return True
    if re.search(r"\b(?:plan|routine|schedule|program|split)\b", lowered):
        return bool(FITNESS_LANGUAGE.search(lowered) or re.search(r"\btraining\b", lowered)
                    or _slot_fragment(lowered, entities, False))
    return bool(re.search(r"\b(?:create|design|make|generate|need|want)\b.{0,40}\bworkouts?\b", lowered))
