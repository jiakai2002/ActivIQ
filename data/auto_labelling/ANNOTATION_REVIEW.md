# AI-assisted entity annotation review

**Status: human reviewed.** These 110 labels started as AI drafts on existing utterances (not new synthetic utterances). A team member (Qixun, recorded as `annotator`) then reviewed every row and corrected 5 labels (validation 003, 047, 055, 059, 114). All 110 records have `label_status: human_reviewed`. The AI drafts are kept in `annotation_provenance`, and the report must disclose that the reviewed labels were AI-assisted. Source intents are preserved, not independently verified.

The instructions below describe the review that was done. Use them again for any new annotation file: check the utterance and all eight slots, correct the labels, put your real name in annotator, and change label_status to human_reviewed only after review. Keep annotation_provenance and the original draft snapshot for disclosure. Do not batch-approve unchecked rows. Resolve taxonomy choices consistently across seeds and validation before freezing.

The test file was not read for annotation or modified. Do not use it for prompt tuning.

Draft conventions: annotate named mentions across all intents, including feelings and out-of-scope requests. Do not infer muscles or equipment from exercise knowledge. Macros expands to Protein, Total lipid (fat), and Carbohydrate, by difference; nutritional facts alone does not expand. Named sports/activity families are tentative exercise labels. Negated body-part targets are excluded. These choices need team agreement.

Coverage below describes draft support, not measured accuracy. There are no positive session-duration examples; do not invent durations to improve coverage. The original fixed validation set alone therefore cannot verify all eight slots. Add separately documented development examples if needed; preserve the held-out test.

## data\auto_labelling\seeds.jsonl

| ID | Utterance | Draft labels | Review note |
| --- | --- | --- | --- |
| train-0056 | How to do a Cossack squat. | exercise: cossack squat | Check each stated mention and canonical value; no additional entities inferred. |
| train-0106 | Thanks for the tips on my squat form, they really make a lot of sense! | exercise: squat | Exercise mention is annotated even in thanks; do not infer equipment or muscles. |
| train-0169 | I need a plan to follow for a lean bulk. | goal: muscle gain | Lean bulk is mapped to muscle gain; no separate weight-gain slot. |
| train-0222 | Can you recommend a good TV show to binge-watch on Netflix? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| train-0352 | Tell me about the macros for a serving of cottage cheese. | food: cottage cheese; nutrient: Protein, Total lipid (fat), Carbohydrate, by difference | Macros expands to the three macronutrients; Energy is not added. Confirm this convention. |
| train-0370 | That workout completely wiped me out. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| train-0384 | I'm glad I found an app like you. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| train-0699 | My run was really tough today but I'm glad I pushed through. | exercise: run | Run is an exercise family even in a feeling log. |
| train-0761 | How do people find the time for two-a-day workouts? | (all empty) | Two-a-day is frequency, not session duration. |
| train-0765 | What are the different types of clouds, like cumulus and stratus? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |

Draft entity-value counts: exercise=3, body_part=0, equipment=0, goal=1, level=0, duration=0, food=1, nutrient=3

## data\evaluation\entities_validation.jsonl

| ID | Utterance | Draft labels | Review note |
| --- | --- | --- | --- |
| entity-validation-001 | Design a workout routine using only a medicine ball. | equipment: medicine ball | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-002 | Tell me about the dinosaurs. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-003 | Tell me about the benefits of taking fish oil supplements. | food: fish oil supplements | Supplement phrase is drafted as food; confirm supplement inclusion in the food slot. |
| entity-validation-004 | Some days are definitely much harder than others to get going. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-005 | How to do a bent-over dumbbell row. | exercise: bent-over dumbbell row; equipment: dumbbell | Keep the exercise variant; dumbbell is explicitly named equipment. Do not infer back muscles. |
| entity-validation-006 | What is the mind-body connection in yoga? | exercise: yoga | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-007 | Can you generate a 30-day fitness challenge for me to follow? | (all empty) | 30-day is programme length, not session duration. |
| entity-validation-008 | Create a 5-day gym workout plan for building muscle. | goal: muscle gain | 5-day is schedule frequency, not session duration; gym does not specify equipment. |
| entity-validation-009 | My breathing felt really deep and controlled during yoga. | exercise: yoga | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-011 | That was a surprisingly easy workout. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-012 | What are some foods high in zinc? | nutrient: Zinc, Zn | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-013 | I feel really hydrated and good today. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-014 | How many calories are in a serving of pad thai? | food: pad thai; nutrient: Energy | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-015 | Is almond milk a good source of calcium? | food: almond milk; nutrient: Calcium, Ca | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-016 | Thanks for being my virtual coach. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-018 | Can you explain what a black hole is in a way a child could understand? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-019 | Can you elaborate on the concept of progressive overload? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-020 | Tell me the macros for a cup of edamame. | food: edamame; nutrient: Protein, Total lipid (fat), Carbohydrate, by difference | Check each stated mention and canonical value; no additional entities inferred. Macros expands to three macronutrients, excluding Energy; confirm. |
| entity-validation-021 | That protein shake made me feel sick. | food: protein shake | Protein shake is a food phrase; Protein is not separately requested as a nutrient. |
| entity-validation-022 | I feel a bit dizzy. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-023 | Show me a good medicine ball workout for core strength. | body_part: core; equipment: medicine ball; goal: strength | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-024 | It's a journey, not a destination, right? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-025 | How many calories are in a standard pint of lager beer? | food: lager beer; nutrient: Energy | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-026 | Tell me the nutritional facts for a single slice of cheese pizza. | food: cheese pizza | Nutritional facts does not enumerate specific nutrients; no automatic expansion. |
| entity-validation-027 | I'm always looking for new healthy and tasty recipes. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-028 | I want a comprehensive training plan for an Olympic distance triathlon. | exercise: triathlon | Triathlon is drafted as an exercise/activity family; confirm taxonomy. Do not infer endurance. |
| entity-validation-029 | The endorphin rush after that run is real right now. | exercise: run | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-030 | What are the original seven wonders of the ancient world? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-032 | Create a program to help me run my fastest 5k ever. | exercise: run | Running is explicit; fastest 5k is not automatically mapped to endurance. Distance is not duration. |
| entity-validation-034 | Record my mood as 'fantastic'. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-035 | I think a positive mindset is half the battle. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-036 | How to do a proper sit-up without using your hip flexors. | exercise: sit up | Hip flexors are explicitly excluded, so no positive body-part label is assigned. |
| entity-validation-037 | My whole body is stiff this morning. | (all empty) | Whole body describes a feeling, not a specific named target muscle; confirm exclusion. |
| entity-validation-038 | Can you find some exercises for improving shoulder mobility? | body_part: shoulders; goal: flexibility | Shoulder mobility is tentatively mapped to flexibility; reviewer must confirm this mapping. |
| entity-validation-039 | I’m feeling super motivated after hitting a new PR! | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-040 | Is whole milk unhealthy for adults? | food: whole milk | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-041 | How many carbs are in a slice of watermelon? | food: watermelon; nutrient: Carbohydrate, by difference | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-042 | How do I start a successful YouTube channel? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-043 | Show me a workout for improving my basketball performance. | exercise: basketball | Basketball is drafted as an activity family; confirm sports inclusion. No unstated goal. |
| entity-validation-044 | Can you tell me about the rise and fall of the Roman Empire? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-045 | Do you have any favorite fitness influencers? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-046 | How to do a bear crawl. | exercise: bear crawl | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-047 | What's the sugar content of a Gatorade? | food: Gatorade; nutrient: Sugars, total | Gatorade is a brand-level food mention; do not choose a specific drink formulation. |
| entity-validation-049 | Create a routine for improving my balance and stability. | (all empty) | Balance and stability are outside the five goal labels; no substitute is inferred. |
| entity-validation-050 | Can you generate a beginner's plan for intermittent fasting? | level: beginner | Beginner is explicit even for fasting; fasting is not an exercise or food item. |
| entity-validation-051 | Find me a video on how to perform a pull-up correctly. | exercise: pull up | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-053 | What's the best way to learn how to swim? | exercise: swim | Swim is an activity entity despite the preserved out_of_scope source intent. Review taxonomy separately. |
| entity-validation-054 | I want a diet plan that is supposed to be good for clear skin. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-055 | What is a German volume training program? | exercise: german volume training | German volume training is tentatively an exercise/training family; may be excluded under a narrower policy. |
| entity-validation-056 | How do I make a good first impression at a job interview? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-057 | Is extra virgin olive oil better than regular vegetable oil? | food: extra virgin olive oil, vegetable oil | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-058 | What are the best practices for cybersecurity? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-059 | Find a routine for relieving neck pain. | body_part: neck | Neck is explicit; pain is not a goal label. Entity labelling does not approve medical advice. |
| entity-validation-060 | Who composed the famous classical piece 'The Four Seasons'? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-061 | Can you tell me about the art of bonsai? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-062 | I'm trying to convince my friend to join the gym with me so I have a partner. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-064 | Thanks for breaking that complex topic down for me. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-065 | What are some foods that can help lower cholesterol? | nutrient: Cholesterol | Cholesterol is a nutrient mention even though the requested direction is lower intake/level. |
| entity-validation-066 | My motivation is at an all-time low this week, I can't seem to get going. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-067 | I feel a great sense of clarity. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-068 | Tell me about the macros for a can of tuna in water. | food: tuna in water; nutrient: Protein, Total lipid (fat), Carbohydrate, by difference | Check each stated mention and canonical value; no additional entities inferred. Macros expands to three macronutrients, excluding Energy; confirm. |
| entity-validation-070 | Can you help me with a name for my new cat? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-071 | My nagging back pain seems to be gone after those stretches. | body_part: back | Back is a mentioned body part in a feeling log; generic stretches is not a named exercise. |
| entity-validation-072 | I'm feeling very grateful for my body's ability to move. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-073 | I want a diet plan specifically for gaining healthy weight and muscle. | goal: muscle gain | Muscle gain is explicit; weight gain has no separate proposal goal category. |
| entity-validation-074 | What's the proper grip width for a barbell curl? | exercise: barbell curl; equipment: barbell | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-075 | What are the differences between simple carbs and complex carbs? | nutrient: Carbohydrate, by difference | Simple and complex carbs map to one USDA carbohydrate field; do not invent subtypes. |
| entity-validation-076 | What are the different types of pasta? | food: pasta | Pasta is a food mention even though the preserved source intent is out_of_scope. |
| entity-validation-077 | What are the most common symptoms of the flu? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-078 | I'm trying to focus on my 'why'. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-079 | What's the best way to organize my closet? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-081 | How to use the leg press machine properly. | exercise: leg press; equipment: machine | Leg press is an exercise; machine is explicit equipment; do not infer requested leg muscles from the name. |
| entity-validation-082 | Thanks, I needed to hear that today. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-084 | Is it possible to eat too much protein? | nutrient: Protein | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-086 | Tell me the macros for a skinless chicken thigh. | food: skinless chicken thigh; nutrient: Protein, Total lipid (fat), Carbohydrate, by difference | Check each stated mention and canonical value; no additional entities inferred. Macros expands to three macronutrients, excluding Energy; confirm. |
| entity-validation-087 | I need a workout routine that I can do outdoors. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-090 | I feel a bit nauseous after that very intense circuit. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-091 | What is the official currency of Japan? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-092 | My appetite has been huge lately since I started lifting more. | (all empty) | Lifting is too generic to name a particular exercise; confirm family boundary. |
| entity-validation-095 | Can you recommend a good pair of noise-cancelling headphones? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-099 | Design a workout program for an endomorph who wants to lose weight. | goal: fat loss | Lose weight maps to fat loss; endomorph has no proposal slot. |
| entity-validation-100 | I want a workout schedule that realistically fits a busy 9-to-5 job. | (all empty) | 9-to-5 describes work hours, not workout duration. |
| entity-validation-101 | Are lentils a good source of dietary fiber? | food: lentils; nutrient: Fiber, total dietary | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-102 | Thanks a lot, I'll definitely give that a try next time. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-103 | Log that my stress level is high today. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-104 | What is the capital of Canada? | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-105 | Create a workout plan for someone with scoliosis. | (all empty) | Scoliosis is outside the eight entity slots; preserve source intent without endorsing medical planning. |
| entity-validation-106 | I feel so accomplished after finishing my weekly step goal. | (all empty) | Weekly step goal does not specify one of the five goal categories. |
| entity-validation-107 | How do I properly engage my abs during leg raises? | exercise: leg raise; body_part: core | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-108 | Find exercises for improving my deadlift lockout. | exercise: deadlift | Keep deadlift as the named exercise; lockout is a technique phase, not a new exercise label. |
| entity-validation-109 | I'm trying to find workouts that I genuinely enjoy. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-111 | Tell me about the benefits of eating ginger for digestion. | food: ginger | Check each stated mention and canonical value; no additional entities inferred. |
| entity-validation-112 | Awesome, thanks for setting that new plan up for me. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-113 | Can you make a meal plan that helps with bloating? | (all empty) | Bloating has no proposal entity slot; no foods are named. |
| entity-validation-114 | I think I'm starting to understand the importance of macros. | nutrient: Protein, Total lipid (fat), Carbohydrate, by difference | Macros is mentioned in general chat; use the same three-nutrient expansion as nutrition requests. |
| entity-validation-116 | I need a workout plan that's low-impact and easy on the joints. | (all empty) | Low impact and easy on joints do not imply beginner level or a named body-part target. |
| entity-validation-117 | I think my form is more important than the weight I'm lifting. | (all empty) | No explicit entity from the eight-slot schema identified; reviewer must confirm all empty slots. |
| entity-validation-118 | I want a plan to help me get back into fitness after a long break. | (all empty) | Returning after a break does not explicitly state beginner level. |
| entity-validation-119 | Find some exercises for improving my reaction time. | (all empty) | Reaction time is outside the five goal categories. |
| entity-validation-120 | Design a program for someone coming back from a shoulder injury. | body_part: shoulders | Shoulders normalises shoulder; injury has no slot and is not a fitness goal. |

Draft entity-value counts: exercise=16, body_part=6, equipment=5, goal=5, level=1, duration=0, food=17, nutrient=22


## AI review pass (2026-11-09)

An AI assistant (Claude) re-checked all 10 seed and 100 validation drafts against
the conventions in `data/evaluation/README.md`. This is a second AI check, not
human review. A person (Qixun) later reviewed all rows; see the status at the top of this file.

**Changed (1 label)**
- `entity-validation-114` ("...importance of macros."): the AI pass changed nutrient to `[]`. The human reviewer restored the three macro nutrients, so the human label is final.

**Left unchanged, but judgment calls the reviewer should confirm**
- Macros expand to `Protein`, `Total lipid (fat)`, `Carbohydrate, by difference`
  (seed `train-0352`, validation 020, 068, 086). This is consistent across all four.
- Out-of-scope rows keep stated entities: validation 053 (`swim`), 076 (`pasta`).
- Sports and programmes are labelled as exercises: validation 028 (`triathlon`),
  043 (`basketball`), 055 (`german volume training`).
- Validation 023: "core strength" gives body part `core` and goal `strength`.
- Validation 005, 074, 081: a named exercise with equipment inside its name also gets
  an equipment label.
- Validation 047: `Sugars, total` matches the dataset's `Sugars, Total` because scoring
  ignores case.
- Day counts (validation 007, 008) are not durations, so `duration` stays `[]`.

All other rows were checked and agree with the conventions.
