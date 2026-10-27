"""Conservative medical routing with bounded, clause-local negation."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.scope import explicit_out_of_scope, normalise_text

MEDICAL_TERMS = (
    "injury", "injured", "pain", "hurts", "hurt", "medication", "medicine",
    "diagnose", "diagnosis", "symptom", "swelling", "fracture", "sprain",
    "prescription", "disease", "doctor",
)
OUT_OF_SCOPE_TERMS = ("politics", "joan of arc", "weather", "stock market")
# These tuples and contains_term() remain available for older callers. The
# active policy is safety_decision(), using the contextual patterns below.

MEDICAL_RESPONSE = (
    "I can’t provide medical advice or diagnose injuries. "
    "Please consult a qualified healthcare professional."
)
OUT_OF_SCOPE_RESPONSE = (
    "I can help with fitness, exercise, nutrition facts and workout logging. "
    "Please ask a fitness-related question."
)

_MEDICAL_PATTERN = re.compile(
    r"\b(?:injur(?:y|ies|ed)|pain(?:s|ful)?|hurt(?:s|ing)?|ach(?:e|es|ing)|"
    r"medications?|medicine(?!\s+balls?\b)|drugs?|painkillers?|ibuprofen|paracetamol|"
    r"acetaminophen|aspirin|antibiotics?|insulin|steroids?|tablets?|pills?|"
    r"diagnos(?:e|is|es|ed|ing)|prescrib(?:e|ed|ing)|prescriptions?|medical (?:advice|treatment|diagnosis)|"
    r"(?:see|consult|ask)\s+(?:(?:a|my|the)\s+)?(?:doctor|physician|healthcare professional)|"
    r"(?:act|pretend)\s+(?:as|like)\s+(?:a\s+)?doctor|(?:what|which)\s+(?:dose|dosage)|"
    r"symptoms?|swelling|swollen|fractures?|sprains?|strains?|diseases?|asthma|diabetes|"
    r"dizzy|dizziness|numb(?:ness)?|tingling|bleeding|headaches?|wheez(?:e|es|ing)|faint(?:ed|ing)|"
    r"(?:feel|feeling|felt)\s+faint|torn\s+(?:ligaments?|tendons?|muscles?)|"
    r"(?:cannot|unable to|struggling to)\s+breathe|difficulty\s+breathing|"
    r"trouble\s+breathing|short(?:ness)?\s+of\s+breath)\b"
)
_CLAUSES = re.compile(
    r"[.!?;]|\b(?:but|however|yet|although)\b|,\s*(?=(?:i|my|these|this|it|there)\b)|"
    r"\band\s+(?=(?:i|my|have|feel|am)\b)"
)
_TYPO_ALIASES = {"pian": "pain", "paim": "pain", "symtoms": "symptoms", "symptons": "symptoms",
                 "injurys": "injuries", "dizyness": "dizziness", "numness": "numbness", "medecine": "medicine"}
_NEGATORS = {"no", "not", "without", "never", "deny", "denies", "denied"}
_NEGATION_BRIDGE = set((
    "any a an the of have has had having been be am is are was were feel feeling experienced "
    "experiencing experience from in my current currently unusual ongoing longer ever physical "
    "medical injuries injury symptoms symptom pain swelling or and knee knees back chest wrist "
    "joint joints arm arms leg legs shoulder shoulders neck ankle ankles want need to advice diagnosis"
).split())


@dataclass(frozen=True)
class SafetyDecision:
    route: str | None = None
    reason: str | None = None


def _negated(clause: str, start: int, end: int) -> bool:
    # Keep coordinated denials consistent for every recognised concern, e.g.
    # 'no asthma or symptoms', rather than maintaining a second medical list.
    prefix_text = _MEDICAL_PATTERN.sub("medicalmention", clause[:start])
    prefix = re.findall(r"[a-z]+", prefix_text)[-9:]
    negators = [index for index, word in enumerate(prefix) if word in _NEGATORS]
    suffix_free = bool(re.match(r"\s+free\b", clause[end:]))
    if negators:
        bridge = prefix[negators[-1] + 1:]
        # 'not only pain', 'do not ignore pain' and 'not pain-free' assert a
        # concern; a negation word anywhere in the sentence is insufficient.
        is_denial = all(word == "medicalmention" or word in _NEGATION_BRIDGE for word in bridge)
        return is_denial and not suffix_free
    return suffix_free


def medical_concern(text: str) -> bool:
    lowered = normalise_text(text)
    lowered = re.sub(r"\b(pain|injury)free\b", r"\1 free", lowered)
    lowered = re.sub(r"\b(?:" + "|".join(_TYPO_ALIASES) + r")\b", lambda match: _TYPO_ALIASES[match[0]], lowered)
    for clause in _CLAUSES.split(lowered):
        idioms = [match.span() for match in re.finditer(
            r"\ba pain to (?:schedule|organise|organize|coordinate|book)\b", clause)]
        for match in _MEDICAL_PATTERN.finditer(clause):
            if any(left <= match.start() and match.end() <= right for left, right in idioms):
                continue
            if not _negated(clause, match.start(), match.end()):
                return True
    return False


def safety_decision(text: str) -> SafetyDecision:
    # An affirmative medical concern takes precedence over an unrelated topic
    # or a healthy/negated clause elsewhere in the same message.
    if medical_concern(text):
        return SafetyDecision("medical", "affirmative_medical_concern")
    if explicit_out_of_scope(text):
        return SafetyDecision("out_of_scope", "unsupported_topic_or_task")
    return SafetyDecision()


def contains_term(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in terms)


def safety_route(text: str) -> str | None:
    """Compatibility API used by the application and evaluation tools."""
    return safety_decision(text).route

