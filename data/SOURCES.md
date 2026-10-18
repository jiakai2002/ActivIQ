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
- Local preparation retains every food and normalizes energy, protein, fat,
  carbohydrate, category, and portion fields into `data/processed/nutrition.json`.
- Secondary source: FNDDS 2021–2023 is retained in the raw data and can be
  prepared as `nutrition_fndds.json` for comparison or fallback.
