"""End-to-end ActivIQ conversation pipeline."""

from __future__ import annotations

import re

from src.dialogue_manager import DialogueState
from src.entity_extractor import FitnessEntityExtractor
from src.knowledge_base import KnowledgeBase
from src.response_generator import ResponseGenerator
from src.safety import MEDICAL_RESPONSE, OUT_OF_SCOPE_RESPONSE, safety_decision
from src.scope import (CLARIFICATION_RESPONSE, FITNESS_PLAN_PHRASE, ambiguous_fragment,
                       fitness_scope_evidence, is_social_message, normalise_text, workout_plan_request)


class FitBuddyPipeline:
    def __init__(self, classifier=None, knowledge_base: KnowledgeBase | None = None,
                 extractor: FitnessEntityExtractor | None = None):
        # Injection permits task-level tests without downloading/loading weights.
        # Normal application startup still requires the trained intent model.
        if classifier is None:
            from src.intent_classifier import IntentClassifier
            classifier = IntentClassifier()
        self.classifier = classifier
        self.knowledge_base = knowledge_base if knowledge_base is not None else KnowledgeBase()
        self.extractor = extractor if extractor is not None else FitnessEntityExtractor(
            self.knowledge_base.data_dir / "exercises.json", self.knowledge_base.data_dir / "nutrition.json"
        )
        self.state = DialogueState()
        self.generator = ResponseGenerator(self.knowledge_base)

    def respond(self, message: str) -> dict:
        message = message.strip()
        if not message:
            return {"text": "Please enter a fitness or nutrition question.", "route": "empty"}
        decision = safety_decision(message)
        if decision.route == "medical":
            return {"text": MEDICAL_RESPONSE, "route": decision.route, "routing_reason": decision.reason,
                    "classifier_used": False}
        if decision.route == "out_of_scope":
            return {"text": OUT_OF_SCOPE_RESPONSE, "route": decision.route, "intent": "out_of_scope",
                    "intent_source": "scope", "routing_reason": decision.reason, "classifier_used": False}
        if message.casefold() in {"reset", "reset profile", "forget my preferences"}:
            self.state.reset()
            return {"text": "Your profile has been reset.", "route": "reset"}

        prediction = self.classifier.predict(message)
        entities = self.extractor.extract(message)
        followup = self._is_followup(message, entities)
        rule_intent = self._rule_intent(message, entities)
        if rule_intent is None and entities.get("body_part") and not followup:
            rule_intent = "find_exercise"
        if followup and self.state.last_intent in {"generate_plan", "find_exercise", "get_nutrition_info"}:
            intent = rule_intent or self.state.last_intent
            source = "rule" if rule_intent else "context"
        else:
            intent = rule_intent or prediction["intent"]
            source = "rule" if rule_intent else "model"
        metadata = {"intent": intent, "intent_source": source,
                    "classifier_intent": prediction["intent"], "confidence": prediction["confidence"],
                    "classifier_used": True}
        evidence = fitness_scope_evidence(message, entities, self.knowledge_base, followup)
        if evidence is None:
            if ambiguous_fragment(message):
                return {"text": CLARIFICATION_RESPONSE, **metadata, "route": "clarification",
                        "routing_reason": "insufficient_fitness_context", "entities": entities,
                        "profile": self.state.snapshot()["profile"]}
            return {"text": OUT_OF_SCOPE_RESPONSE, **metadata, "route": "out_of_scope",
                    "intent": "out_of_scope", "intent_source": "scope",
                    "routing_reason": "no_supported_fitness_evidence", "profile": self.state.snapshot()["profile"]}
        metadata["scope_evidence"] = evidence
        # Rule/context evidence is independent of whether it happens to agree
        # with the classifier label. Rejected messages must not alter state.
        if prediction["confidence"] < 0.60 and source == "model":
            return {"text": CLARIFICATION_RESPONSE, **metadata, "route": "clarification",
                    "routing_reason": "low_model_confidence", "entities": entities,
                    "profile": self.state.snapshot()["profile"]}
        if intent == "generate_plan" and not workout_plan_request(
            message, entities, followup and self.state.last_intent == "generate_plan"
        ):
            return {"text": CLARIFICATION_RESPONSE, **metadata, "route": "clarification",
                    "routing_reason": "workout_plan_not_requested", "entities": entities,
                    "profile": self.state.snapshot()["profile"]}
        if intent == "out_of_scope":
            return {"text": OUT_OF_SCOPE_RESPONSE, **metadata, "route": "out_of_scope",
                    "routing_reason": "model_out_of_scope", "profile": self.state.snapshot()["profile"]}

        if followup and intent == "get_nutrition_info":
            modifier = re.fullmatch(r"(?:and |what about |how about |actually |instead )?(raw|cooked|boiled|grilled|roasted|steamed)[?.!]*", message.casefold())
            old_food = self.state.last_entities.get("food", [])
            if modifier and old_food:
                base = re.sub(r"\b(raw|cooked|boiled|grilled|roasted|steamed)\b", "", old_food[0]).strip(" ,")
                entities["food"] = [f"{base} {modifier[1]}"]
                for key in ("quantity_g", "serving"):
                    if self.state.last_entities.get(key):
                        entities[key] = list(self.state.last_entities[key])
        merged = self.state.inherit(entities, intent, followup)
        self.state.update(intent, merged)
        text = self.generator.generate(intent, merged, self.state.profile)
        return {"text": text, **metadata, "entities": merged, "profile": self.state.snapshot()["profile"]}

    def _is_followup(self, message: str, entities: dict[str, list[str]]) -> bool:
        if self.state.last_intent is None:
            return False
        lowered = message.casefold()
        if self.state.last_intent == "get_nutrition_info" and not any(
            entities.get(key) for key in ("food", "nutrient", "quantity_g", "serving")
        ) and not re.search(r"\b(raw|cooked|boiled|grilled|roasted|steamed)\b", lowered):
            return False
        if self.state.last_intent != "get_nutrition_info" and entities.get("quantity_g") and not any(
            entities.get(key) for key in ("food", "nutrient")
        ):
            return False
        has_slots = any(entities.get(key) for key in (
            "body_part", "exercise", "equipment", "goal", "level", "duration", "days", "food", "nutrient", "quantity_g", "serving"
        ))
        modifier = bool(re.fullmatch(r"(?:and |what about |how about |actually |instead )?(raw|cooked|boiled|grilled|roasted|steamed)[?.!]*", lowered))
        nutrient_followup = self.state.last_intent == "get_nutrition_info" and bool(entities.get("nutrient")) and not entities.get("food")
        return modifier or nutrient_followup or (has_slots and len(lowered.split()) <= 12 and bool(
            re.match(r"^(?:what about|how about|and\b|instead\b|actually\b|make it\b|use\b|using\b|with\b|for\b|only\b)", lowered)
            or not re.search(r"\b(how|what|create|generate|design|show|explain)\b", lowered)
        ))

    @staticmethod
    def _rule_intent(message: str, entities: dict[str, list[str]]) -> str | None:
        lowered = message.casefold()
        if entities.get("exercise") and re.search(r"\b(how (?:do i|to)|perform|form|technique|demonstrate|explain)\b", lowered):
            return "find_exercise"
        if entities.get("nutrient") or re.search(r"\b(nutrition|nutrients?|macros?)\b", lowered):
            return "get_nutrition_info"
        if entities.get("food") and not entities.get("exercise"):
            return "get_nutrition_info"
        if FITNESS_PLAN_PHRASE.search(normalise_text(message)):
            return "generate_plan"
        if re.search(r"\b(plan|routine|schedule|program)\b", lowered) and re.search(
            r"\b(workout|training|fitness|exercise|full[- ]body)\b", lowered
        ):
            return "generate_plan"
        if entities.get("body_part") and re.search(r"\b(exercises?|train|work)\b", lowered):
            return "find_exercise"
        if is_social_message(message):
            return "general_chat"
        return None

    @staticmethod
    def _apply_high_signal_routing(message: str, predicted_intent: str, confidence: float,
                                   entities: dict[str, list[str]]) -> str:
        """Compatibility wrapper; confidence always belongs to the model label."""
        return FitBuddyPipeline._rule_intent(message, entities) or predicted_intent
