"""Rule-based nutrition slots; nutrient names use USDA's canonical labels."""

import re

from src.vocabulary import tokens


NUTRIENT_ALIASES = {
    "Energy": ["calories", "calorie", "energy", "kcal"],
    "Energy (kJ)": ["kilojoules", "kilojoule", "kj"],
    "Protein": ["protein"],
    "Total lipid (fat)": ["fat", "fats", "total fat"],
    "Carbohydrate, by difference": ["carbohydrate", "carbohydrates", "carbs", "carb"],
    "Fiber, total dietary": ["fiber", "fibre", "dietary fiber"],
    "Sugars, Total": ["sugar", "sugars"],
    "Vitamin K (phylloquinone)": ["vitamin k"],
    "Vitamin C, total ascorbic acid": ["vitamin c"],
    "Vitamin D (D2 + D3)": ["vitamin d"],
    "Vitamin A, RAE": ["vitamin a"],
    "Vitamin E (alpha-tocopherol)": ["vitamin e"],
    "Vitamin B-12": ["vitamin b12", "vitamin b-12", "b12"],
    "Vitamin B-6": ["vitamin b6", "vitamin b-6", "b6"],
    "Calcium, Ca": ["calcium"],
    "Iron, Fe": ["iron"],
    "Magnesium, Mg": ["magnesium"],
    "Potassium, K": ["potassium"],
    "Sodium, Na": ["sodium"],
    "Zinc, Zn": ["zinc"],
}

GRAM_PATTERN = re.compile(r"(?<![\w.])(-?\d+(?:\.\d+)?)\s*(kg|kilograms?|g|grams?|oz|ounces?)\b", re.I)
SERVING_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?\s*|(?:a|an|one|half)\s+)(?:(?:single|standard)\s+)?"
    r"(?:cups?|servings?|tablespoons?|teaspoons?|slices?|pieces?|(?:cans?|pints?|shots?)(?=\s+of\b))\b",
    re.I,
)
NUTRITION_TERMS = re.compile(r"\b(?:nutrition(?:al)?|nutrients?|macros?|macronutrients?)\b")
MACROS = ("Protein", "Total lipid (fat)", "Carbohydrate, by difference")
FOOD_SUBJECT = re.compile(
    r"^(?:is|are)\s+(.+?)\s+(?:an?\s+(?:(?:good|rich|poor|excellent)\s+)?source\s+of\b"
    r"|(?:high|low|rich)\s+in\b|(?:healthy|unhealthy)\b)"
)


def nutrient_key(name: str, unit: str) -> str:
    """USDA has separate kcal and kJ rows named Energy; keep both."""
    return "Energy (kJ)" if name == "Energy" and unit.casefold() == "kj" else name


def extract_nutrition(text: str, food_names: set[frozenset[str]],
                      nutrient_names: set[str] | None = None) -> dict[str, list[str]]:
    lowered = text.casefold().replace("’", "'").strip(" ?.!,")
    result = {key: [] for key in ("food", "nutrient", "quantity_g", "serving")}
    # A training goal is not a request for dietary fat.
    nutrient_text = re.sub(r"\b(?:(?:fat|weight)[ -]loss|lose (?:fat|weight))\b", "", lowered)
    if NUTRITION_TERMS.search(nutrient_text) or re.search(r"\b(?:how much|how many)\b", nutrient_text):
        nutrient_text = re.split(r"\b(?:in|for|of)\b", nutrient_text, maxsplit=1)[0]
    contains_nutrient = re.search(r"\b(?:have|contain)\s+(.+)$", lowered)
    if contains_nutrient:
        nutrient_text = contains_nutrient[1]
    aliases_by_name = dict(NUTRIENT_ALIASES)
    legacy_sugar_key = "Sugars, total including NLEA"
    if nutrient_names and "Sugars, Total" not in nutrient_names and legacy_sugar_key in nutrient_names:
        aliases_by_name[legacy_sugar_key] = aliases_by_name.pop("Sugars, Total")
    for name in sorted(nutrient_names or set()):
        if name not in aliases_by_name:
            aliases_by_name[name] = [name.casefold(), name.split(",")[0].casefold()]
    for canonical, aliases in aliases_by_name.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", nutrient_text) for alias in aliases):
            result["nutrient"].append(canonical)
    for vitamin in re.findall(r"\bvitamin\s+[a-z](?:-?\d+)?\b", nutrient_text):
        if not any(vitamin in aliases for aliases in aliases_by_name.values()):
            result["nutrient"].append(vitamin)
    if re.search(r"\b(?:macros?|macronutrients?)\b", nutrient_text):
        result["nutrient"] = list(dict.fromkeys([*result["nutrient"], *MACROS]))

    quantity = GRAM_PATTERN.search(lowered)
    if quantity:
        amount = float(quantity[1])
        if quantity[2].startswith("k"):
            amount *= 1000
        elif quantity[2].startswith(("oz", "ounce")):
            amount *= 28.349523125
        result["quantity_g"] = [f"{amount:g}"]
    serving = SERVING_PATTERN.search(lowered)
    if serving:
        result["serving"] = [serving[0]]

    # Preserve preparation words instead of selecting a food by partial overlap.
    candidate = lowered
    relation = re.fullmatch(r"(.+?)\s+(?:in|for|of)\s+(.+)", candidate)
    contains = re.search(r"^(?:does|do)\s+(.+?)\s+(?:have|contain)\b", candidate)
    subject = FOOD_SUBJECT.match(candidate)
    framing = relation[1] if relation else ""
    facts_request = NUTRITION_TERMS.search(framing) and re.match(
        r"^(?:what|how|tell|show|give|can|could|please|nutrition|macros?|nutrients?)\b", framing
    )
    nutrient_request = result["nutrient"] and (
        re.search(r"\b(?:how much|how many|content|amount)\b", framing)
        or any(framing in aliases for aliases in aliases_by_name.values())
    )
    explicit_target = bool(result["nutrient"] and subject)
    if subject:
        candidate = subject[1]
    elif contains and result["nutrient"]:
        candidate = contains[1]
        explicit_target = True
    elif relation and (facts_request or nutrient_request):
        candidate = relation[2]
        explicit_target = True
    else:
        candidate = re.sub(r"^(?:what about|how about|and|instead|actually)\s+", "", candidate)
        candidate = re.sub(r"\s+(?:nutrition(?:al)?(?: facts| information)?|nutrients?|macros?)$", "", candidate)
    candidate = GRAM_PATTERN.sub("", candidate)
    candidate = SERVING_PATTERN.sub("", candidate)
    if quantity or serving:
        candidate = re.sub(r"^\s*of\s+", "", candidate)
    candidate = re.sub(r"^(?:a|an|the)\s+", "", candidate.strip())
    candidate = re.sub(r"\s+", " ", candidate).strip(" ?.!,")
    candidate = re.split(r"\s+for my (?:workout|training|fitness|diet|meal)\b", candidate, maxsplit=1)[0]
    candidate_tokens = frozenset(tokens(candidate))
    known_food = bool(candidate_tokens) and any(candidate_tokens <= name for name in food_names)
    if candidate and (explicit_target or known_food):
        result["food"] = [candidate]
    return result
