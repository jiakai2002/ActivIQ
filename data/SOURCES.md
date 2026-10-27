# Data sources

## Intent classification

- Source: [Fitness Intent Classification](https://huggingface.co/datasets/harshmakwana/fitness-intent)
- License stated by source: MIT
- Splits: 960 train, 120 validation, 120 test
- Fields used: `text`, `intent`
- Augmentation: disabled; original splits are preserved.

## Exercise knowledge base

- Source: [Free Exercise DB](https://github.com/yuhonas/free-exercise-db)
- License stated by source: Unlicense
- Input: combined `dist/exercises.json`
- Local preparation removes duplicate names and converts camelCase muscle fields
  to snake_case names used by ActivIQ.

## Nutrition data

- Primary source: [USDA FoodData Central SR Legacy](https://fdc.nal.usda.gov/download-datasets/)
- Release: April 2018, the final SR Legacy release
- Input: complete SR Legacy CSV archive
- Local preparation retains every food and all supplied nutrient names, amounts
  and units, plus category and portion fields, in `data/processed/nutrition.json`.
  Energy in kcal and kJ is kept separately to prevent unit collisions.
- The processed JSON was rebuilt on 27 October 2026 from the official
  [SR Legacy CSV archive](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip).
  It contains 7,793 foods, 149 distinct nutrient fields and 644,125 nutrient
  values. Original food identities and all four previously retained macro/energy
  amounts were checked against the earlier processed file and preserved.
- Archive SHA-256: `b80817294b8850530aaedf2e515c02593b1824f763a0ff356e5c2081643e6fd0`.
  The raw archive and extracted CSVs remain ignored by Git.
- Secondary source: FNDDS 2021–2023 can be prepared as `nutrition_fndds.json`
  when its raw archive is supplied, for comparison or future integration.
