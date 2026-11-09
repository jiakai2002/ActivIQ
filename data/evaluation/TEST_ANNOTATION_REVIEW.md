# Test-set entity annotation review

**Status: human reviewed by Hsien Ray (2026-11-09).** Drafted following `data/evaluation/README.md` and the decisions already made in the reviewed validation set. All 120 rows are now `label_status: human_reviewed` with `annotator: Hsien Ray`.

The extractor's and models' predictions were not viewed. The test utterances were not used for prompt tuning.

## Priority review: 32 rows with a judgement call

| Row | Utterance | Draft labels | Why check |
|---|---|---|---|
| 1 | Cardio always feels like such a repetitive grind to me. | exercise: cardio | Cardio treated as an exercise family (like yoga/run). |
| 2 | Make me a 20-minute workout plan that I can do during my lunch break. | duration: 20 minutes | '20-minute' normalised to '20 minutes'; confirm normalisation. |
| 10 | What are the main ingredients of a good curry? | food: curry | Food in an out_of_scope utterance; confirm whether to label. |
| 16 | What are some good exercises for tennis elbow? | (all empty) | 'Tennis elbow' is an injury name; I left it empty (not exercise/body part). Compare row 47. |
| 18 | Can you design a push/pull/legs workout split? | body_part: legs | 'push/pull/legs' is a split name; I labelled only 'legs'. Could be empty. |
| 24 | I want a yoga routine plan for stress relief over a month. | exercise: yoga | 'over a month' is programme length, not duration; 'stress relief' is not a goal slot. |
| 33 | What are your thoughts on the trend of barefoot running? | exercise: barefoot running | Named variant kept (vs. plain 'run'); confirm. |
| 34 | Show me how to use a TRX for inverted rows. | exercise: inverted row; equipment: trx | Canonical name for TRX equipment: 'trx' or 'suspension trainer'? Same in row 84. |
| 36 | Design a simple 2-day-a-week lifting program for maintenance. | (all empty) | '2-day-a-week' is frequency; 'lifting' not labelled (consistent with validation); 'maintenance' is not a goal slot value. |
| 47 | My elbow is bothering me again. | body_part: elbow | Body part from a pain mention (like validation 'back pain' -> back). Compare row 16. |
| 49 | How to do a Russian twist with a weight. | exercise: russian twist | 'with a weight' is too vague for equipment; left empty. |
| 51 | My stamina was great on my bike ride this weekend. | exercise: cycling | 'bike ride' normalised to 'cycling'; confirm. |
| 56 | I'm feeling a little impatient with my weight loss results. | goal: fat loss | 'weight loss' mapped to 'fat loss' in a feeling log; confirm. |
| 65 | What are some common signs of being vitamin D deficient? | nutrient: Vitamin D (D2 + D3) | Nutrient mentioned as deficiency; USDA name chosen. |
| 66 | How do you make a perfect cup of English breakfast tea? | food: english breakfast tea | Food in an out_of_scope utterance; confirm whether to label. |
| 67 | What are the benefits of taking zinc supplements? | nutrient: Zinc, Zn | 'Supplements' not labelled as food (validation fish-oil row was emptied). |
| 72 | Design a nutrition plan for someone with an iron deficiency. | nutrient: Iron, Fe | Nutrient mentioned as deficiency in a meal-plan request; confirm. |
| 73 | Show me some advanced push-up variations like the archer push-up. | exercise: push up, archer push up; level: expert | Both the generic family and the named variant labelled; 'advanced' -> expert. Confirm. |
| 74 | Is it better to do my cardio session before or after lifting weights? | exercise: cardio | 'lifting weights' not labelled. |
| 75 | Can you make a 7-day vegan meal plan for weight loss? | goal: fat loss | 'weight loss' -> fat loss; '7-day' is schedule, not duration. |
| 78 | I’m not sure if I should focus on building strength or improving my endurance first. | goal: strength, endurance | Goals mentioned as options being weighed; confirm both. |
| 83 | Design a workout routine using only a pull-up bar and the floor. | equipment: pull up bar | 'the floor' not labelled as equipment. |
| 84 | Generate a workout plan using a TRX suspension trainer. | equipment: trx | See row 34 on naming. |
| 88 | I'm trying to cut down on added sugar in my diet. | nutrient: Sugars, Total | 'added sugar' mapped to 'Sugars, Total' (closest name in KB); confirm. |
| 89 | Show me a quick 5-minute warm-up before a run. | exercise: run; duration: 5 minutes | 'warm-up' not labelled as an exercise; confirm. |
| 95 | I want a plan to increase my daily water intake. | food: water | Could be nutrient 'Water' instead of food; confirm. |
| 99 | What’s the protein content in 200g of salmon? | food: salmon; nutrient: Protein | '200g' is a quantity, excluded. |
| 103 | What is EMOM in CrossFit? | exercise: crossfit | EMOM is a format, not labelled; CrossFit as exercise family. |
| 106 | What's the difference between high-bar and low-bar squats in powerlifting? | exercise: high bar squat, low bar squat | Named variants kept; 'powerlifting' not labelled. |
| 110 | What are some good vegan protein sources besides tofu? | nutrient: Protein | 'tofu' excluded (user asks for sources besides it); confirm. |
| 118 | My endurance on the treadmill is definitely improving week by week. | equipment: treadmill | Treadmill as equipment; may belong to 'machine'; confirm. |
| 120 | Show me a 20-minute HIIT workout for beginners. | exercise: hiit; level: beginner; duration: 20 minutes | '20-minute' normalised. |

## Remaining rows (no flagged decision; still verify)

| Row | Utterance | Draft labels |
|---|---|---|
| 3 | What are the main nutritional benefits of eating spinach? | food: spinach |
| 4 | That healthy and clean meal made me feel great and not sluggish. | (all empty) |
| 5 | What are some of the best foods rich in iron? | nutrient: Iron, Fe |
| 6 | Create a meal plan for a pescatarian diet. | (all empty) |
| 7 | I'm feeling the after-effects of a poor night's sleep. | (all empty) |
| 8 | I'm trying to listen to my body's signals more often. | (all empty) |
| 9 | That was a perfect workout to end the week. | (all empty) |
| 11 | What are some foods that are said to boost metabolism? | (all empty) |
| 12 | Tell me about the Cold War. | (all empty) |
| 13 | I think progress isn't always linear. | (all empty) |
| 14 | That deep tissue massage left me feeling amazing. | (all empty) |
| 15 | What is the nutritional value of maca powder? | food: maca powder |
| 17 | My workout today was a fantastic stress reliever. | (all empty) |
| 19 | I honestly think consistency is the most important thing. | (all empty) |
| 20 | Find a video on foam rolling techniques for legs. | exercise: foam rolling; body_part: legs |
| 21 | What is proprioception and how do I train it? | (all empty) |
| 22 | I'm feeling really balanced, both mentally and physically. | (all empty) |
| 23 | I feel a great sense of personal accomplishment today. | (all empty) |
| 25 | Tell me about the benefits of eating beets. | food: beets |
| 26 | What's the best way to learn photography? | (all empty) |
| 27 | Generate a nutrition plan for someone who works night shifts. | (all empty) |
| 28 | That's good to know. | (all empty) |
| 29 | How to properly execute a lat pulldown to target the lats. | exercise: lat pulldown; body_part: lats |
| 30 | What are some common nutrient deficiencies in a vegan diet? | (all empty) |
| 31 | Create a meal plan for someone who hates cooking. | (all empty) |
| 32 | What is the process of photosynthesis? | (all empty) |
| 35 | Tell me about the benefits of eating garlic. | food: garlic |
| 37 | What is the tallest building in the entire world? | (all empty) |
| 38 | I need a sample meal plan for someone with PCOS. | (all empty) |
| 39 | I'm feeling very lethargic. | (all empty) |
| 40 | Can you tell me a funny joke? | (all empty) |
| 41 | Nutritional facts for an Impossible Burger. | food: impossible burger |
| 42 | What's a good finisher for a chest workout? | body_part: chest |
| 43 | It's amazing how much my diet really affects my overall mood. | (all empty) |
| 44 | I want a dedicated plan to build powerful core strength. | body_part: core; goal: strength |
| 45 | How many calories are in a samosa? | food: samosa; nutrient: Energy |
| 46 | What's your opinion on wearing weightlifting shoes? | (all empty) |
| 48 | Create a training plan to improve my 1-mile run time. | exercise: run |
| 50 | Is it better to eat a meal before or after a workout? | (all empty) |
| 52 | Generate a workout schedule for a rotating shift worker. | (all empty) |
| 53 | Can you recommend a good history podcast to listen to? | (all empty) |
| 54 | What's a burpee and how do I do it with correct form? | exercise: burpee |
| 55 | Tell me about the nutritional profile of asparagus. | food: asparagus |
| 57 | Who was the famous Renaissance artist Leonardo da Vinci? | (all empty) |
| 58 | Who directed the movie 'Inception' starring Leonardo DiCaprio? | (all empty) |
| 59 | Design a technical routine for improving my deadlift form. | exercise: deadlift |
| 60 | I want a plan to transition to a fully vegetarian diet. | (all empty) |
| 61 | I feel accomplished for waking up early to exercise before work. | (all empty) |
| 62 | I want a diet plan that's easy on my stomach. | (all empty) |
| 63 | What is the Pythagorean theorem used for? | (all empty) |
| 64 | How do I take care of a new puppy? | (all empty) |
| 68 | How many calories are in a shot of vodka? | food: vodka; nutrient: Energy |
| 69 | I'm grateful for your help on this journey. | (all empty) |
| 70 | How important is getting enough sleep for muscle recovery? | (all empty) |
| 71 | Find a guide on how to build an athletic stance for sports. | (all empty) |
| 76 | What are isometric exercises and what are they good for? | (all empty) |
| 77 | I feel like I'm hitting a plateau. | (all empty) |
| 79 | My body feels completely and utterly exhausted. | (all empty) |
| 80 | I had no idea there were so many different types of protein powder. | food: protein powder |
| 81 | How to change my car's oil. | (all empty) |
| 82 | Feeling mentally clear and calm after my morning meditation. | (all empty) |
| 85 | What do you think about body positivity in the fitness world? | (all empty) |
| 86 | What is the difference between aerobic and anaerobic exercise? | (all empty) |
| 87 | How to do a Jefferson curl for hamstring flexibility. | exercise: jefferson curl; body_part: hamstrings; goal: flexibility |
| 90 | What is the significance of the Great Wall of China? | (all empty) |
| 91 | I'm so stressed out from work, I really need a good workout. | (all empty) |
| 92 | Who wrote the US Constitution? | (all empty) |
| 93 | How to do a wall sit correctly for quad endurance. | exercise: wall sit; body_part: quadriceps; goal: endurance |
| 94 | How many calories are in a large Caesar salad with dressing? | food: caesar salad with dressing; nutrient: Energy |
| 96 | How to do a landmine press. | exercise: landmine press |
| 97 | My focus was amazing during my lifting session this afternoon. | (all empty) |
| 98 | What's your opinion on using smelling salts before a heavy lift? | (all empty) |
| 100 | How to do a concentration curl correctly. | exercise: concentration curl |
| 101 | How many calories are in a tablespoon of honey? | food: honey; nutrient: Energy |
| 102 | Are chia seeds a superfood? | food: chia seeds |
| 104 | I'm feeling really on top of my game in every aspect. | (all empty) |
| 105 | Okay, that makes a whole lot more sense now. | (all empty) |
| 107 | What's the best way to clean a cast iron skillet? | (all empty) |
| 108 | I felt really energized during my run this morning. | exercise: run |
| 109 | Who was Albert Einstein? | (all empty) |
| 111 | Got it, thanks for all the useful info. | (all empty) |
| 112 | Is kombucha really good for you? | food: kombucha |
| 113 | That's a really interesting way to think about my weekly nutrition. | (all empty) |
| 114 | What do you think about those '30-day shred' programs? | (all empty) |
| 115 | What's the difference between a republic and a democracy? | (all empty) |
| 116 | Who wrote the classic American novel 'To Kill a Mockingbird'? | (all empty) |
| 117 | What's the best laptop for a college student? | (all empty) |
| 119 | Design a High-Intensity Interval Training (HIIT) program for fat loss. | exercise: hiit; goal: fat loss |
