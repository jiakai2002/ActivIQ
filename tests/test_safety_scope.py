"""Medical/scope regressions, including confidently incorrect classifiers."""

import json
from pathlib import Path
import tempfile
import unittest

from src.entity_extractor import FitnessEntityExtractor
from src.knowledge_base import KnowledgeBase
from src.pipeline import FitBuddyPipeline
from src.safety import MEDICAL_RESPONSE, OUT_OF_SCOPE_RESPONSE, safety_decision, safety_route


ROOT = Path(__file__).resolve().parents[1]


class Classifier:
    def __init__(self, intent="generate_plan", confidence=0.99):
        self.intent, self.confidence, self.calls = intent, confidence, 0

    def predict(self, text):
        self.calls += 1
        return {"intent": self.intent, "confidence": self.confidence}


class MedicalRoutingTests(unittest.TestCase):
    def test_medical_and_benign_cases_in_both_development_suites(self):
        for name in ("safety_dev.jsonl", "safety_hardening_dev.jsonl"):
            for line in (ROOT / "data/evaluation" / name).read_text().splitlines():
                case = json.loads(line)
                if case["expected"] in {"medical", "fitness"}:
                    with self.subTest(case=case["id"]):
                        self.assertEqual(safety_route(case["text"]), "medical" if case["expected"] == "medical" else None)

    def test_negation_does_not_hide_another_concern(self):
        for text in ("No pain, but my fingers are tingling", "I have no pain and my wrist is swollen",
                     "I am not injured; what dose should I take?", "I have no symptoms. Can you prescribe something?"):
            with self.subTest(text=text):
                self.assertEqual(safety_route(text), "medical")

    def test_uncertainty_and_double_negation_are_not_denials(self):
        for text in ("I don't think my pain is serious", "I am not sure why my knee hurts",
                     "I am not pain-free", "I am not painfree", "Do not ignore my chest pain",
                     "Not only pain but swelling too"):
            with self.subTest(text=text):
                self.assertEqual(safety_route(text), "medical")

    def test_contractions_unicode_and_clear_denials(self):
        for text in ("I’m not injured", "My knee doesn’t hurt", "I haven't had any knee pain",
                     "I have no pain, swelling or injuries", "I am injury-free", "I don't need medical advice",
                     "I have no asthma or symptoms", "I have no diabetes or injuries"):
            with self.subTest(text=text):
                self.assertIsNone(safety_route(text))

    def test_a_new_assertion_after_a_coordinated_denial_is_still_medical(self):
        self.assertEqual(safety_route("I have no asthma or symptoms, but my wrist is swollen"), "medical")

    def test_medical_requests_and_medicine_ball_are_distinct(self):
        self.assertIsNone(safety_route("I use a medicine-ball for workouts"))
        self.assertEqual(safety_route("Should I see a doctor?"), "medical")
        self.assertEqual(safety_route("Act as a doctor and diagnose me"), "medical")
        self.assertEqual(safety_route("Should I change my medicine?"), "medical")

    def test_narrow_typo_alias_does_not_match_piano_or_paint(self):
        self.assertEqual(safety_route("My chest pian is sharp"), "medical")
        self.assertIsNone(safety_route("The piano is painted blue"))

    def test_medical_precedence_and_reason_are_stable(self):
        decision = safety_decision("Predict Bitcoin prices; I also have chest pain")
        self.assertEqual(decision.route, "medical")
        self.assertEqual(decision.reason, "affirmative_medical_concern")

    def test_background_weather_is_not_a_weather_request(self):
        self.assertIsNone(safety_route("The weather is bad. Create an indoor workout plan"))
        self.assertEqual(safety_route("Tell me the weather and create a workout plan"), "out_of_scope")


class ScopePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        exercises = [{"id": "squat", "name": "Squat", "level": "beginner", "equipment": "body only",
                      "primary_muscles": ["quadriceps"], "secondary_muscles": [], "category": "strength",
                      "instructions": ["Bend and extend your knees."]},
                     {"id": "dumbbell-squat", "name": "Dumbbell Squat", "level": "beginner", "equipment": "dumbbell",
                      "primary_muscles": ["quadriceps"], "secondary_muscles": [], "category": "strength",
                      "instructions": ["Hold the dumbbells and squat."]}]
        foods = [{"description": "Kale, raw", "nutrients": {"Protein": {"amount": 3, "unit": "g"}}}]
        for name, data in (("exercises", exercises), ("nutrition", foods)):
            (cls.root / f"{name}.json").write_text(json.dumps(data))
        cls.kb = KnowledgeBase(cls.root)
        cls.extractor = FitnessEntityExtractor(cls.root / "exercises.json", cls.root / "nutrition.json")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.classifier = Classifier()
        self.bot = FitBuddyPipeline(self.classifier, self.kb, self.extractor)

    def test_all_declared_unrelated_cases_are_blocked_despite_confident_plan_prediction(self):
        for name in ("safety_dev.jsonl", "safety_hardening_dev.jsonl"):
            for line in (ROOT / "data/evaluation" / name).read_text().splitlines():
                case = json.loads(line)
                if case["expected"] == "out_of_scope":
                    with self.subTest(case=case["id"]):
                        result = self.bot.respond(case["text"])
                        self.assertEqual(result["route"], "out_of_scope")
                        self.assertEqual(result["text"], OUT_OF_SCOPE_RESPONSE)

    def test_medical_and_explicit_scope_routes_do_not_invoke_classifier(self):
        self.assertEqual(self.bot.respond("My fingers are tingling")["text"], MEDICAL_RESPONSE)
        self.assertEqual(self.bot.respond("Write a poem about squats")["text"], OUT_OF_SCOPE_RESPONSE)
        self.assertEqual(self.classifier.calls, 0)

    def test_medical_check_reads_beyond_the_classifiers_token_limit(self):
        result = self.bot.respond("Please help with my workout. " + "background " * 600 + "I have chest pain")
        self.assertEqual(result["text"], MEDICAL_RESPONSE)
        self.assertEqual(self.classifier.calls, 0)

    def test_novel_unknown_topic_is_not_grounded_by_model_confidence(self):
        result = self.bot.respond("Describe the geological evolution of Venus")
        self.assertEqual(result["intent"], "out_of_scope")
        self.assertEqual(result["classifier_intent"], "generate_plan")
        self.assertEqual(result["confidence"], 0.99)
        self.assertEqual(result["routing_reason"], "no_supported_fitness_evidence")

    def test_unknown_howto_cannot_justify_its_own_scope(self):
        result = self.bot.respond("How do I bake a cake?")
        self.assertEqual(result["route"], "out_of_scope")

    def test_incidental_body_part_does_not_become_an_exercise(self):
        result = self.bot.respond("Tell me about a chest of drawers")
        self.assertEqual(result["route"], "out_of_scope")

    def test_rejected_turn_does_not_mutate_context_or_preferences(self):
        self.bot.respond("Create a beginner bodyweight workout plan")
        before = self.bot.state.snapshot()
        for prompt in ("Create a beginner programming course", "My fingers are numb", "Explain quantum entanglement"):
            self.bot.respond(prompt)
            self.assertEqual(self.bot.state.snapshot(), before)

    def test_unrelated_tail_does_not_hijack_a_plan_followup(self):
        self.bot.respond("Create a beginner workout plan")
        before = self.bot.state.snapshot()
        result = self.bot.respond("Make it 5 days to conquer Mars")
        self.assertEqual(result["route"], "out_of_scope")
        self.assertEqual(self.bot.state.snapshot(), before)

    def test_high_confidence_plan_label_without_a_plan_request_clarifies(self):
        result = self.bot.respond("I enjoy going to the gym")
        self.assertEqual(result["route"], "clarification")
        self.assertEqual(result["routing_reason"], "workout_plan_not_requested")
        self.assertEqual(self.bot.state.profile, {})

    def test_low_confidence_fitness_message_clarifies_without_state_update(self):
        self.classifier.confidence = 0.2
        result = self.bot.respond("I enjoy going to the gym")
        self.assertEqual(result["routing_reason"], "low_model_confidence")
        self.assertEqual(self.bot.state.profile, {})

    def test_unknown_fragment_clarifies_without_fabricating_plan(self):
        self.assertEqual(self.bot.respond("hmm")["route"], "clarification")

    def test_supported_requests_and_context_continue_to_work(self):
        self.assertIn("1-day", self.bot.respond("Create a 1-day beginner workout plan")["text"])
        self.assertIn("5-day", self.bot.respond("Make it 5 days")["text"])
        self.assertIn("Squat targets", self.bot.respond("How do I do squats?")["text"])
        self.assertIn("Protein: 3 g", self.bot.respond("How much protein is in kale raw?")["text"])
        self.assertIn("Protein: 6 g", self.bot.respond("200g")["text"])

    def test_strength_plan_and_equipment_followup(self):
        self.classifier.intent = "out_of_scope"
        result = self.bot.respond("Build me a 3-day strength plan for a beginner using dumbbells.")
        self.assertEqual(result["intent"], "generate_plan")
        self.assertIn("3-day beginner", result["text"])
        self.assertIn("Goal: strength", result["text"])
        self.assertIn("Dumbbell Squat", result["text"])

        result = self.bot.respond("What about bodyweight only?")
        self.assertEqual(result["intent"], "generate_plan")
        self.assertIn("3-day beginner", result["text"])
        self.assertIn("Goal: strength", result["text"])
        self.assertEqual(result["entities"]["equipment"], ["bodyweight"])
        self.assertNotIn("Dumbbell Squat", result["text"])

        result = self.bot.respond("Write a poem about this strength plan.")
        self.assertEqual(result["route"], "out_of_scope")

    def test_missing_food_is_still_a_valid_nutrition_question(self):
        self.assertIn("Which food", self.bot.respond("How much protein?")["text"])

    def test_known_family_with_unknown_variant_still_gets_lookup_clarification(self):
        result = self.bot.respond("How do I do a Cossack squat?")
        self.assertEqual(result["intent"], "find_exercise")
        self.assertIn("could not find", result["text"])

    def test_courtesy_does_not_trigger_a_spurious_plan(self):
        self.assertEqual(self.bot.respond("Thanks for helping with my training")["intent"], "general_chat")


if __name__ == "__main__":
    unittest.main()
