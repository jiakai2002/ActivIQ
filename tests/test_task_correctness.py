"""Task regressions; no trained model, network, or Streamlit server required."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.dialogue_manager import DialogueState
from src.entity_extractor import FitnessEntityExtractor
from src.knowledge_base import KnowledgeBase
from src.pipeline import FitBuddyPipeline
from src.planner import build_plan
from src.response_generator import ResponseGenerator
from src.vocabulary import MUSCLE_GROUPS


class FixedClassifier:
    def __init__(self, intent="out_of_scope", confidence=0.4):
        self.intent, self.confidence = intent, confidence

    def predict(self, text):
        return {"intent": self.intent, "confidence": self.confidence}


def exercise(name, muscle, equipment="body only", level="beginner", category="strength"):
    return {"id": name, "name": name, "primary_muscles": [muscle], "secondary_muscles": [],
            "equipment": equipment, "level": level, "category": category,
            "instructions": ["First step.", "Second step.", "Third step.", "Fourth step.", "Fifth step."]}


class TaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        exercises = [
            exercise("Squat", "quadriceps"), exercise("Lunge", "hamstrings"),
            exercise("Calf Raise", "calves"), exercise("Push-Up", "chest"),
            exercise("Plank", "abdominals"), exercise("Chin-Up", "biceps"),
            exercise("Dumbbell Curl", "biceps", "dumbbell"),
            exercise("Kettlebell Floor Press", "chest", "kettlebells"),
            exercise("Machine Fly", "chest", "machine", "intermediate"),
            exercise("Hamstring Stretch", "hamstrings", category="stretching"),
        ]
        foods = [
            {"description": "Kale, raw", "nutrients": {"Energy": {"amount": 35, "unit": "kcal"},
                "Protein": {"amount": 3, "unit": "g"}, "Vitamin K (phylloquinone)": {"amount": 100, "unit": "UG"}}},
            {"description": "Kale, cooked", "nutrients": {"Protein": {"amount": 2, "unit": "g"}}},
            {"description": "Chicken, breast, raw", "nutrients": {"Protein": {"amount": 22, "unit": "g"}}},
            {"description": "Chicken spread", "nutrients": {"Protein": {"amount": 18, "unit": "g"}}},
            {"description": "Apple, raw", "nutrients": {"Protein": {"amount": 0, "unit": "g"}}},
        ]
        for name, records in (("exercises", exercises), ("nutrition", foods)):
            (self.root / f"{name}.json").write_text(json.dumps(records), encoding="utf-8")
        self.kb = KnowledgeBase(self.root)
        self.extractor = FitnessEntityExtractor(self.root / "exercises.json", self.root / "nutrition.json")
        self.generator = ResponseGenerator(self.kb)
        self.bot = FitBuddyPipeline(FixedClassifier(), self.kb, self.extractor)

    def test_body_groups_retrieve_actual_muscles(self):
        for group in ("legs", "arms", "core", "back", "chest"):
            with self.subTest(group=group):
                matches = self.kb.find_exercises(body_part=group)
                if group != "back":
                    self.assertTrue(matches)
                for item in matches:
                    self.assertTrue(MUSCLE_GROUPS[group] & set(item["primary_muscles"]))

    def test_specific_muscle_is_not_broadened_to_entire_body_group(self):
        self.assertEqual(self.extractor.extract("quads")["body_part"], ["quadriceps"])
        self.assertEqual([x["name"] for x in self.kb.find_exercises(body_part="quadriceps")], ["Squat"])

    def test_one_day_numeric_word_and_hyphenated(self):
        for prompt in ("Create a 1 day beginner workout plan", "Create a one-day beginner workout plan"):
            with self.subTest(prompt=prompt):
                response = self.bot.respond(prompt)["text"]
                self.assertIn("1-day", response)
                self.assertNotIn("Day 2", response)

    def test_invalid_day_count_is_not_clamped(self):
        self.assertIn("between 1 and 7", self.bot.respond("Create an 8 day workout plan")["text"])

    def test_negative_and_fractional_days_are_rejected(self):
        for value in ("-2", "1.5"):
            self.assertIn("between 1 and 7", self.bot.respond(f"Create a {value} day workout plan")["text"])

    def test_scarce_plan_keeps_all_constraints(self):
        plan = build_plan(self.kb, "beginner", "kettlebell", "chest", 5)
        for day in plan:
            self.assertEqual([item["name"] for item in day["exercises"]], ["Kettlebell Floor Press"])
        response = self.bot.respond("Create a 5-day beginner chest workout plan using kettlebells")["text"]
        self.assertIn("repeat across days", response)
        self.assertNotIn("Machine Fly", response)

    def test_unmatched_constraints_ask_for_change(self):
        response = self.bot.respond("Create a beginner legs workout plan using kettlebells")["text"]
        self.assertIn("No local exercises match", response)
        self.assertNotIn("Kettlebell Floor Press:", response)

    def test_multiple_equipment_choices_are_honoured(self):
        plan = build_plan(self.kb, equipment=["dumbbell", "kettlebell"], days=1)
        self.assertEqual({e["name"] for e in plan[0]["exercises"]}, {"Dumbbell Curl", "Kettlebell Floor Press"})

    def test_duration_changes_volume_without_exceeding_budget(self):
        short = build_plan(self.kb, equipment="bodyweight", duration="20 minutes")
        long = build_plan(self.kb, equipment="bodyweight", duration="60 minutes")
        self.assertLess(len(short[0]["exercises"]), len(long[0]["exercises"]))
        self.assertTrue(all(d["estimated_minutes"] <= 20 for d in short))

    def test_compound_duration_and_training_days_are_separate(self):
        entities = self.extractor.extract("Create a 3-day workout plan for 1 hour 30 minutes")
        self.assertEqual(entities["duration"], ["1 hour", "30 minutes"])
        self.assertEqual(self.extractor.extract("A 25-minute workout")["duration"], ["25 minutes"])
        self.assertEqual(entities["days"], ["3"])

    def test_short_duration_asks_for_longer_session(self):
        self.assertIn("too short", self.bot.respond("Create a workout plan for 2 minutes")["text"])
        self.assertIn("too short", self.bot.respond("Create a strength workout plan for 11 minutes")["text"])

    def test_negative_duration_is_rejected(self):
        self.assertIn("greater than zero", self.bot.respond("Create a workout plan for -20 minutes")["text"])

    def test_fat_loss_goal_does_not_route_to_nutrition(self):
        for phrase in ("fat loss", "lose fat", "weight loss", "lose weight"):
            self.assertEqual(self.bot.respond(f"Create a workout plan to {phrase}")["intent"], "generate_plan")

    def test_goals_change_prescription(self):
        strength = build_plan(self.kb, days=1, goal="strength")[0]["exercises"][0]
        endurance = build_plan(self.kb, days=1, goal="endurance")[0]["exercises"][0]
        self.assertNotEqual(strength["repetitions"], endurance["repetitions"])
        self.assertNotEqual(strength["rest"], endurance["rest"])

    def test_flexibility_plan_uses_timed_stretches(self):
        item = build_plan(self.kb, goal="flexibility", days=1)[0]["exercises"][0]
        self.assertEqual(item["name"], "Hamstring Stretch")
        self.assertIn("seconds", item["repetitions"])

    def test_no_duplicate_exercises_within_a_day(self):
        for day in build_plan(self.kb, days=7):
            names = [item["name"] for item in day["exercises"]]
            self.assertEqual(len(names), len(set(names)))

    def test_default_plan_covers_different_body_groups_across_days(self):
        plan = build_plan(self.kb, equipment="bodyweight", days=3)
        names = {item["name"] for day in plan for item in day["exercises"]}
        muscles = {muscle for item in self.kb.exercises if item["name"] in names for muscle in item["primary_muscles"]}
        for group in ("chest", "arms", "legs", "core"):
            self.assertTrue(MUSCLE_GROUPS[group] & muscles)

    def test_unknown_exercise_is_not_partially_matched(self):
        response = self.bot.respond("How do I do a Cossack squat?")["text"]
        self.assertIn("could not find", response)
        self.assertNotIn("First step", response)

    def test_plural_exercise_and_all_instruction_steps(self):
        response = self.bot.respond("How do I do squats?")["text"]
        self.assertIn("Squat targets", response)
        self.assertIn("5. Fifth step", response)

    def test_hyphenated_plural_exercise(self):
        self.assertIn("Push-Up targets", self.bot.respond("How do I do push-ups?")["text"])

    def test_howto_separates_equipment_and_exercise_name(self):
        result = self.bot.respond("How do I do squats with no equipment?")
        self.assertEqual(result["entities"]["exercise"], ["squat"])
        self.assertIn("Squat targets", result["text"])

    def test_explicit_harder_exercise_shows_actual_level(self):
        response = self.bot.respond("How do I do a Machine Fly?")["text"]
        self.assertIn("level as intermediate", response)
        self.assertNotIn("beginner-friendly", response)

    def test_missing_exercise_slot_asks_question(self):
        self.assertIn("Which exercise", self.generator.generate("find_exercise", {}, {}))

    def test_food_and_nutrient_are_distinct_entities(self):
        entities = self.extractor.extract("How much vitamin K is in 200 g kale raw?")
        self.assertEqual(entities["food"], ["kale raw"])
        self.assertEqual(entities["nutrient"], ["Vitamin K (phylloquinone)"])
        self.assertEqual(entities["quantity_g"], ["200"])

    def test_micronutrient_and_unit_are_scaled(self):
        response = self.bot.respond("How much vitamin K is in 200 g kale raw?")["text"]
        self.assertIn("Vitamin K (phylloquinone): 200 mcg", response)
        self.assertNotIn("Energy:", response)

    def test_missing_nutrient_is_disclosed(self):
        response = self.bot.respond("How much calcium is in kale raw?")["text"]
        self.assertIn("Calcium, Ca: not available", response)
        self.assertNotIn("Energy:", response)

    def test_ambiguous_food_asks_instead_of_picking_spread(self):
        response = self.bot.respond("How much protein is in chicken?")["text"]
        self.assertIn("Several foods match", response)
        self.assertNotIn("For 100 g", response)

    def test_unknown_food_does_not_match_on_question_words(self):
        response = self.bot.respond("How much protein is in flibbertigibbet?")["text"]
        self.assertIn("could not find", response)

    def test_explicit_preparation_is_required_in_search(self):
        self.assertEqual(self.kb.search_food("kale grilled"), [])

    def test_zero_nutrient_is_not_treated_as_missing(self):
        self.assertIn("Protein: 0 g", self.bot.respond("How much protein is in apple raw?")["text"])

    def test_unsupported_household_portion_asks_for_weight(self):
        self.assertIn("serving weight in grams", self.bot.respond("How much protein is in one cup kale raw?")["text"])

    def test_food_boundaries_keep_preparation_and_drop_serving_words(self):
        entities = self.extractor.extract("How much protein is in a standard serving of kale raw?")
        self.assertEqual(entities["food"], ["kale raw"])
        self.assertEqual(entities["serving"], ["a standard serving"])

        entities = self.extractor.extract("Is kale raw a good source of protein?")
        self.assertEqual(entities["food"], ["kale raw"])
        self.assertEqual(entities["nutrient"], ["Protein"])

        entities = self.extractor.extract("What are some foods high in protein?")
        self.assertEqual(entities["food"], [])
        self.assertEqual(entities["nutrient"], ["Protein"])

    def test_nonpositive_food_quantity_is_rejected(self):
        for grams in ("0", "-10"):
            self.assertIn("greater than zero", self.bot.respond(f"How much protein is in {grams} g kale raw?")["text"])

    def test_kg_quantity_is_converted(self):
        self.assertIn("Protein: 30 g", self.bot.respond("How much protein is in 1 kg kale raw?")["text"])

    def test_plan_followup_inherits_intent_and_preferences(self):
        self.bot.respond("Create a 1 day beginner legs workout plan using bodyweight")
        result = self.bot.respond("Make it 5 days")
        self.assertEqual(result["intent"], "generate_plan")
        self.assertIn("5-day", result["text"])
        self.assertEqual(result["entities"]["body_part"], ["legs"])

    def test_body_followup_discards_old_exercise(self):
        self.bot.respond("How do I do squats?")
        result = self.bot.respond("What about chest?")
        self.assertEqual(result["intent"], "find_exercise")
        self.assertFalse(result["entities"].get("exercise"))
        self.assertIn("targets chest", result["text"])

    def test_food_preparation_followup(self):
        self.bot.respond("How much protein is in kale?")
        response = self.bot.respond("raw")["text"]
        self.assertIn("Kale, raw", response)
        self.assertIn("Protein: 3 g", response)

    def test_ambiguous_food_keeps_quantity_when_preparation_is_clarified(self):
        self.bot.respond("How much protein is in 200 g kale?")
        self.assertIn("Protein: 6 g", self.bot.respond("raw")["text"])

    def test_bare_food_clarification_keeps_requested_nutrient(self):
        self.bot.respond("How much protein is in chicken?")
        response = self.bot.respond("chicken breast raw")["text"]
        self.assertIn("Protein: 22 g", response)

    def test_full_food_name_clarification_keeps_weight(self):
        self.bot.respond("How much protein is in 200 g chicken?")
        self.assertIn("Protein: 44 g", self.bot.respond("chicken breast raw")["text"])

    def test_body_question_after_nutrition_starts_exercise_task(self):
        self.bot.respond("How much protein is in kale raw?")
        result = self.bot.respond("What about chest?")
        self.assertEqual(result["intent"], "find_exercise")
        self.assertFalse(result["entities"].get("food"))
        self.assertIn("targets chest", result["text"])

    def test_quantity_only_followup_keeps_food_and_nutrient(self):
        self.bot.respond("How much protein is in kale raw?")
        self.assertIn("Protein: 6 g", self.bot.respond("200g")["text"])

    def test_generic_nutrient_followup_keeps_food(self):
        self.bot.respond("How much protein is in kale raw?")
        self.assertIn("Vitamin K (phylloquinone): 100 mcg", self.bot.respond("How much vitamin K?")["text"])

    def test_missing_food_slot_can_be_filled_on_next_turn(self):
        self.assertIn("Which food", self.bot.respond("How much protein?")["text"])
        self.assertIn("Protein: 22 g", self.bot.respond("chicken breast raw")["text"])

    def test_nutrient_followup_keeps_food(self):
        self.bot.respond("How much protein is in kale raw?")
        response = self.bot.respond("And vitamin K?")["text"]
        self.assertIn("Vitamin K (phylloquinone): 100 mcg", response)

    def test_food_change_does_not_inherit_old_weight(self):
        self.bot.respond("How much protein is in 200 g kale raw?")
        response = self.bot.respond("What about apple raw?")["text"]
        self.assertIn("For 100 g of Apple, raw", response)

    def test_new_task_does_not_inherit_old_food_or_exercise(self):
        self.bot.respond("How do I do squats?")
        self.bot.respond("How much protein is in kale raw?")
        result = self.bot.respond("How do I do a Machine Fly?")
        self.assertFalse(result["entities"].get("food"))
        self.assertIn("Machine Fly targets", result["text"])

    def test_low_confidence_rule_is_consistent_when_model_agrees(self):
        self.bot.classifier = FixedClassifier("generate_plan", 0.2)
        result = self.bot.respond("Create a 1 day workout plan")
        self.assertIn("1-day", result["text"])
        self.assertEqual(result["intent_source"], "rule")

    def test_rejected_message_does_not_update_state(self):
        before = self.bot.state.snapshot()
        result = self.bot.respond("I am a beginner")
        self.assertIn("not sure", result["text"])
        self.assertEqual(before, self.bot.state.snapshot())

    def test_unrelated_schedule_is_not_workout_plan(self):
        self.bot.classifier = FixedClassifier("out_of_scope", 0.99)
        self.assertEqual(self.bot.respond("Tell me about the election schedule")["intent"], "out_of_scope")

    def test_nutrition_question_with_plan_word_stays_nutrition(self):
        result = self.bot.respond("How much protein is in kale raw for my workout plan?")
        self.assertEqual(result["intent"], "get_nutrition_info")
        self.assertIn("Protein: 3 g", result["text"])

    def test_reset_clears_preferences_and_task_context(self):
        self.bot.respond("Create a beginner dumbbell workout plan")
        self.bot.respond("reset profile")
        self.assertEqual(self.bot.state.snapshot(), DialogueState().snapshot())

    def test_medical_route_precedes_task_context(self):
        self.bot.respond("Create a beginner workout plan")
        before = self.bot.state.snapshot()
        result = self.bot.respond("I have chest pain")
        self.assertEqual(result["route"], "medical")
        self.assertEqual(before, self.bot.state.snapshot())

    def test_explicit_out_of_scope_route_precedes_context(self):
        self.bot.respond("Create a beginner workout plan")
        self.assertEqual(self.bot.respond("What about the weather?")["route"], "out_of_scope")

    def test_empty_knowledge_base_is_handled(self):
        (self.root / "exercises.json").write_text("[]")
        kb = KnowledgeBase(self.root)
        self.assertIn("empty", ResponseGenerator(kb).generate("generate_plan", {}, {}))


class RepositoryDataTests(unittest.TestCase):
    def test_real_usda_data_answers_vitamin_and_calorie_requests(self):
        kb = KnowledgeBase()
        self.assertEqual(len(kb.nutrition), 7793)
        self.assertEqual(len({name for food in kb.nutrition for name in food["nutrients"]}), 149)
        bot = FitBuddyPipeline(FixedClassifier(), kb)
        self.assertIn("Vitamin K (phylloquinone): 389.6 mcg", bot.respond("How much vitamin K is in kale raw?")["text"])
        self.assertIn("Vitamin K (phylloquinone): 779.2 mcg", bot.respond("200g")["text"])
        self.assertIn("Energy: 35 kcal", bot.respond("How many calories are in kale raw?")["text"])


class PreparationTests(unittest.TestCase):
    def test_sr_legacy_retains_micronutrients_and_original_units(self):
        from scripts.prepare_data import prepare_sr_legacy
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tables = {
                "food.csv": [["fdc_id", "description", "food_category_id"], ["1", "Kale, raw", "1"]],
                "nutrient.csv": [["id", "name", "unit_name"], ["1003", "Protein", "G"],
                    ["1185", "Vitamin K (phylloquinone)", "UG"], ["1087", "Calcium, Ca", "MG"],
                    ["1008", "Energy", "KCAL"], ["1062", "Energy", "kJ"]],
                "food_nutrient.csv": [["fdc_id", "nutrient_id", "amount"], ["1", "1003", "3"],
                    ["1", "1185", "100"], ["1", "1087", "50"], ["1", "1008", "35"], ["1", "1062", "146"]],
                "food_category.csv": [["id", "description"], ["1", "Vegetables"]],
                "food_portion.csv": [["fdc_id", "amount", "measure_unit_id", "portion_description", "modifier", "gram_weight"],
                    ["1", "1", "9999", "", "cup chopped", "67"]],
            }
            for name, rows in tables.items():
                with (root / name).open("w", newline="") as stream:
                    csv.writer(stream).writerows(rows)
            output = root / "processed"
            prepare_sr_legacy(root, output, root / "food.csv")
            nutrients = json.loads((output / "nutrition.json").read_text())[0]["nutrients"]
            self.assertEqual(nutrients["Vitamin K (phylloquinone)"], {"amount": 100, "unit": "UG"})
            self.assertEqual(nutrients["Calcium, Ca"]["unit"], "MG")
            self.assertEqual(nutrients["Energy"], {"amount": 35, "unit": "KCAL"})
            self.assertEqual(nutrients["Energy (kJ)"], {"amount": 146, "unit": "kJ"})
            foods = json.loads((output / "nutrition.json").read_text(), parse_constant=lambda value: self.fail(f"Non-standard JSON {value}"))
            self.assertIsNone(foods[0]["portions"][0]["portion_description"])

    def test_fndds_retains_micronutrients(self):
        from scripts.prepare_data import prepare_fndds
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            source.write_text(json.dumps({"SurveyFoods": [{"description": "Kale", "foodNutrients": [
                {"nutrient": {"name": "Calcium, Ca", "unitName": "mg"}, "amount": 50}]}]}))
            prepare_fndds(source, root)
            nutrients = json.loads((root / "nutrition_fndds.json").read_text())[0]["nutrients"]
            self.assertEqual(nutrients["Calcium, Ca"], {"amount": 50, "unit": "mg"})


if __name__ == "__main__":
    unittest.main()
