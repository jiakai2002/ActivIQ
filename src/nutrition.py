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
    "Sugars, total including NLEA": ["sugar", "sugars"],
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
SERVING_PATTERN = re.compile(r"\b(?:\d+(?:\.\d+)?|a|an|one|half)\s*(?:cups?|servings?|tablespoons?|teaspoons?|slices?|pieces?)\b", re.I)


def nutrient_key(name: str, unit: str) -> str:
    """USDA has separate kcal and kJ rows named Energy; keep both."""
    return "Energy (kJ)" if name == "Energy" and unit.casefold() == "kj" else name


def extract_nutrition(text: str, food_names: set[frozenset[str]],
                      nutrient_names: set[str] | None = None) -> dict[str, list[str]]:
    lowered = text.casefold().strip(" ?.!,")
    result = {key: [] for key in ("food", "nutrient", "quantity_g", "serving")}
    # A training goal is not a request for dietary fat.
    nutrient_text = re.sub(r"\b(?:(?:fat|weight)[ -]loss|lose (?:fat|weight))\b", "", lowered)
    if re.search(r"\b(?:how much|how many|nutrition|nutrients|macros)\b", nutrient_text):
        nutrient_text = re.split(r"\b(?:in|for|of)\b", nutrient_text, maxsplit=1)[0]
    contains_nutrient = re.search(r"\b(?:have|contain)\s+(.+)$", lowered)
    if contains_nutrient:
        nutrient_text = contains_nutrient[1]
    aliases_by_name = dict(NUTRIENT_ALIASES)
    for name in sorted(nutrient_names or set()):
        if name not in aliases_by_name:
            aliases_by_name[name] = [name.casefold(), name.split(",")[0].casefold()]
    for canonical, aliases in aliases_by_name.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", nutrient_text) for alias in aliases):
            result["nutrient"].append(canonical)
    for vitamin in re.findall(r"\bvitamin\s+[a-z](?:-?\d+)?\b", nutrient_text):
        if not any(vitamin in aliases for aliases in aliases_by_name.values()):
            result["nutrient"].append(vitamin)
    nutritional = bool(result["nutrient"] or re.search(r"\b(nutrition|nutrients?|macros?)\b", lowered))

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
    relation = re.search(r"\b(?:in|for|of)\s+(.+)$", candidate)
    contains = re.search(r"^(?:does|do)\s+(.+?)\s+(?:have|contain)\b", candidate)
    if nutritional and contains:
        candidate = contains[1]
    elif nutritional and relation:
        candidate = relation[1]
    else:
        candidate = re.sub(r"^(?:what about|how about|and|instead|actually)\s+", "", candidate)
        candidate = re.sub(r"\s+(?:nutrition(?: facts| information)?|nutrients?|macros?)$", "", candidate)
        if nutritional:
            for aliases in aliases_by_name.values():
                for alias in sorted(aliases, key=len, reverse=True):
                    candidate = re.sub(rf"\b{re.escape(alias)}\b", "", candidate)
            candidate = re.sub(r"\b(?:how much|how many|what|is|are|does|do|have|contain|nutrition|facts|information|nutrients|macros)\b", "", candidate)
    candidate = GRAM_PATTERN.sub("", candidate)
    candidate = SERVING_PATTERN.sub("", candidate)
    candidate = re.sub(r"^(?:a|an|the)\s+", "", candidate.strip())
    candidate = re.sub(r"\s+", " ", candidate).strip(" ?.!,")
    candidate = re.split(r"\s+for my (?:workout|training|fitness|diet|meal)\b", candidate, maxsplit=1)[0]
    candidate_tokens = frozenset(tokens(candidate))
    known_food = bool(candidate_tokens) and any(candidate_tokens <= name for name in food_names)
    if candidate and (nutritional or known_food):
        result["food"] = [candidate]
    return result
