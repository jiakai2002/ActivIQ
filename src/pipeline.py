"""End-to-end ActivIQ conversation pipeline."""

from __future__ import annotations

import re

from src.dialogue_manager import DialogueState
from src.entity_extractor import FitnessEntityExtractor
from src.intent_classifier import IntentClassifier
from src.knowledge_base import KnowledgeBase
from src.response_generator import ResponseGenerator
from src.safety import MEDICAL_RESPONSE, OUT_OF_SCOPE_RESPONSE, safety_route


class FitBuddyPipeline:
    def __init__(self):
        self.classifier = IntentClassifier()
        self.extractor = FitnessEntityExtractor()
        self.state = DialogueState()
        self.knowledge_base = KnowledgeBase()
        self.generator = ResponseGenerator(self.knowledge_base)

    def respond(self, message: str) -> dict:
        message = message.strip()
        if not message:
            return {"text": "Please enter a fitness or nutrition question.", "route": "empty"}
        route = safety_route(message)
        if route == "medical":
            return {"text": MEDICAL_RESPONSE, "route": route}
        if route == "out_of_scope":
            return {"text": OUT_OF_SCOPE_RESPONSE, "route": route}
        if message.casefold().strip() in {"reset", "reset profile", "forget my preferences"}:
            self.state.reset()
            return {"text": "Your profile has been reset.", "route": "reset"}

        prediction = self.classifier.predict(message)
        predicted_intent = prediction["intent"]
        entities = self.extractor.extract(message)
        intent = self._apply_high_signal_routing(message, predicted_intent, prediction["confidence"], entities)
        was_rerouted = intent != predicted_intent
        if intent == "find_exercise" and not entities.get("exercise"):
            exercise_match = re.search(
                r"\b(push[- ]?ups?|pull[- ]?ups?|squats?|lunges?|planks?|deadlifts?|bench press)\b",
                message.casefold(),
            )
            if exercise_match:
                entities["exercise"] = [exercise_match.group(0).replace("-", " ")]
        if intent == "get_nutrition_info":
            entities["food"] = [message]
        merged = self.state.inherit(entities)
        self.state.update(intent, entities)
        obvious_general_chat = intent == "general_chat" and re.search(
            r"\b(thanks|thank you|hello|hi|hey)\b", message.casefold()
        )
        if prediction["confidence"] < 0.60 and not was_rerouted and not obvious_general_chat:
            return {
                "text": "I’m not sure I understood. Are you asking for a workout plan, exercise instructions, or nutrition information?",
                "intent": intent,
                "confidence": prediction["confidence"],
                "entities": entities,
                "profile": self.state.profile,
            }
        text = self.generator.generate(intent, merged, self.state.profile)
        return {
            "text": text,
            "intent": intent,
            "confidence": prediction["confidence"],
            "entities": entities,
            "profile": self.state.profile,
        }

    @staticmethod
    def _apply_high_signal_routing(
        message: str,
        predicted_intent: str,
        confidence: float,
        entities: dict[str, list[str]],
    ) -> str:
        """Correct low-confidence obvious requests with transparent rules."""

        lowered = message.casefold()
        # These phrases are high-signal enough to correct an occasional
        # classifier miss (especially for short exercise names).
        if re.search(r"\b(plan|routine|schedule|program|workout week|training week)\b", lowered):
            return "generate_plan"
        if re.search(r"\b(how do i|how to|perform|form|technique|demonstrate)\b", lowered) and (
            entities.get("exercise")
            or re.search(r"\b(push[- ]?ups?|pull[- ]?ups?|squats?|lunges?|planks?|deadlifts?|bench press)\b", lowered)
        ):
            return "find_exercise"
        if re.search(
            r"\b(calories?|protein|carbs?|fat|nutrition|nutrients?|vitamins?)\b", lowered
        ):
            return "get_nutrition_info"
        if re.search(r"\b(thanks|thank you|hello|hi|hey)\b", lowered):
            return "general_chat"
        if confidence >= 0.75:
            return predicted_intent
        return predicted_intent
