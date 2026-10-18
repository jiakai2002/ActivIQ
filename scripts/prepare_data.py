"""Validate and prepare ActivIQ's Phase 1 data.

The script intentionally does not download data. Raw source files must be
placed under data/raw so that dataset provenance remains explicit and runs are
reproducible.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Support both `python scripts/prepare_data.py` and
# `python -m scripts.prepare_data` from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (
    INTENT_LABELS,
    LABEL_COLUMNS,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
    TEXT_COLUMNS,
)


def find_column(columns: list[str], candidates: tuple[str, ...]) -> str | None:
    """Return the first matching column, case-insensitively."""

    by_lower = {column.lower(): column for column in columns}
    return next((by_lower[name] for name in candidates if name in by_lower), None)


def read_table(path: Path) -> pd.DataFrame:
    """Read a supported tabular dataset."""

    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def prepare_intent_split(path: Path, output_path: Path) -> dict[str, Any]:
    """Normalize one intent split and report data-quality problems."""

    frame = read_table(path)
    text_column = find_column(list(frame.columns), TEXT_COLUMNS)
    label_column = find_column(list(frame.columns), LABEL_COLUMNS)
    problems: list[str] = []

    if text_column is None or label_column is None:
        missing = []
        if text_column is None:
            missing.append("text/utterance column")
        if label_column is None:
            missing.append("label/intent column")
        return {"path": str(path), "rows": 0, "problems": ["Missing " + " and ".join(missing)]}

    cleaned = frame[[text_column, label_column]].rename(
        columns={text_column: "text", label_column: "label"}
    )
    cleaned["text"] = cleaned["text"].astype("string").str.strip()
    cleaned["label"] = cleaned["label"].astype("string").str.strip().str.lower()

    empty_rows = cleaned[cleaned["text"].isna() | cleaned["text"].eq("")]
    if not empty_rows.empty:
        problems.append(f"{len(empty_rows)} empty text rows")
        cleaned = cleaned.drop(empty_rows.index)

    unknown_labels = sorted(set(cleaned["label"].dropna()) - set(INTENT_LABELS))
    if unknown_labels:
        problems.append("Unknown labels: " + ", ".join(unknown_labels))

    duplicate_count = int(cleaned["text"].duplicated().sum())
    if duplicate_count:
        problems.append(f"{duplicate_count} duplicate utterances")
        cleaned = cleaned.drop_duplicates(subset="text", keep="first")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(output_path, index=False)
    return {
        "path": str(path),
        "output": str(output_path),
        "rows": len(cleaned),
        "labels": cleaned["label"].value_counts().to_dict(),
        "problems": problems,
    }


def locate_split(raw_intent_dir: Path, split: str) -> Path | None:
    """Find a split file using common CSV and Parquet names."""

    for suffix in (".csv", ".parquet"):
        candidate = raw_intent_dir / f"{split}{suffix}"
        if candidate.exists():
            return candidate
    return None


def prepare_intents(raw_dir: Path, processed_dir: Path) -> dict[str, Any]:
    raw_intent_dir = raw_dir / "intent_dataset"
    report: dict[str, Any] = {"splits": {}, "problems": []}

    for split in ("train", "validation", "val", "test"):
        source = locate_split(raw_intent_dir, split)
        if source is None:
            continue
        output_name = "validation.csv" if split == "val" else f"{split}.csv"
        result = prepare_intent_split(source, processed_dir / "intents" / output_name)
        report["splits"][split] = result
        report["problems"].extend(result.get("problems", []))

    expected = {"train", "test"}
    found = set(report["splits"])
    if not expected.issubset(found):
        report["problems"].append("Missing required train or test split")
    if not any(name in found for name in ("validation", "val")):
        report["problems"].append("Missing validation split")

    split_texts: dict[str, set[str]] = {}
    for split, details in report["splits"].items():
        output = details.get("output")
        if output:
            prepared = pd.read_csv(output)
            split_texts[split] = set(prepared["text"].astype(str).str.casefold())
    split_names = list(split_texts)
    for index, left_name in enumerate(split_names):
        for right_name in split_names[index + 1 :]:
            overlap = split_texts[left_name] & split_texts[right_name]
            if overlap:
                report["problems"].append(
                    f"{len(overlap)} utterances overlap between {left_name} and {right_name}"
                )
    return report


def prepare_exercises(raw_dir: Path, processed_dir: Path) -> dict[str, Any]:
    """Validate and normalize the combined Free Exercise DB JSON file."""

    source = raw_dir / "exercise_db" / "exercises.json"
    result: dict[str, Any] = {"problems": []}
    if not source.exists():
        result["problems"].append("Missing exercise database JSON")
        return result

    try:
        records = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["problems"].append(f"Could not read exercise database: {exc}")
        return result

    if not isinstance(records, list):
        result["problems"].append("Exercise database must contain a JSON list")
        return result

    normalized: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    required = ("id", "name", "level", "equipment", "primaryMuscles", "instructions")
    for record in records:
        if not isinstance(record, dict):
            result["problems"].append("Skipped a non-object exercise record")
            continue
        missing = [field for field in required if field not in record]
        if missing:
            result["problems"].append(
                f"Skipped {record.get('id', '<unknown>')}: missing {', '.join(missing)}"
            )
            continue
        name = str(record["name"]).strip()
        key = name.casefold()
        if not name or key in seen_names:
            continue
        seen_names.add(key)
        normalized.append(
            {
                "id": str(record["id"]),
                "name": name,
                "level": record.get("level"),
                "equipment": record.get("equipment"),
                "primary_muscles": record.get("primaryMuscles", []),
                "secondary_muscles": record.get("secondaryMuscles", []),
                "instructions": record.get("instructions", []),
                "category": record.get("category"),
            }
        )

    output_path = processed_dir / "exercises.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    result.update({"path": str(source), "output": str(output_path), "records": len(normalized)})
    return result


def prepare_nutrition(raw_dir: Path, processed_dir: Path) -> dict[str, Any]:
    """Normalize SR Legacy as the primary source and FNDDS as a secondary source."""

    sr_root = raw_dir / "nutrition" / "sr-legacy"
    sr_food = next(sr_root.rglob("food.csv"), None) if sr_root.exists() else None
    if sr_food is not None:
        return prepare_sr_legacy(sr_root, processed_dir, sr_food)

    fndds_source = raw_dir / "nutrition" / "fndds" / "surveyDownload.json"
    if not fndds_source.exists():
        return {"problems": ["SR Legacy food.csv not provided yet"]}
    return prepare_fndds(fndds_source, processed_dir)


def prepare_sr_legacy(sr_root: Path, processed_dir: Path, food_path: Path) -> dict[str, Any]:
    """Normalize the SR Legacy relational CSV files into searchable JSON."""

    nutrient_path = next(sr_root.rglob("food_nutrient.csv"), None)
    nutrient_lookup_path = next(sr_root.rglob("nutrient.csv"), None)
    category_path = next(sr_root.rglob("food_category.csv"), None)
    portion_path = next(sr_root.rglob("food_portion.csv"), None)
    required = (nutrient_path, nutrient_lookup_path, category_path)
    if any(path is None for path in required):
        return {"problems": ["SR Legacy is missing one or more required CSV tables"]}

    foods = pd.read_csv(food_path, dtype={"fdc_id": "string", "food_category_id": "string"})
    nutrients = pd.read_csv(
        nutrient_path,
        usecols=["fdc_id", "nutrient_id", "amount"],
        dtype={"fdc_id": "string", "nutrient_id": "string"},
    )
    nutrient_lookup = pd.read_csv(nutrient_lookup_path, dtype={"id": "string"})
    nutrient_ids = {
        str(row.id): str(row.name)
        for row in nutrient_lookup.itertuples()
        if row.id in {"1003", "1004", "1005", "1008"}
    }
    nutrients = nutrients[nutrients["nutrient_id"].isin(nutrient_ids)]
    nutrients["nutrient_name"] = nutrients["nutrient_id"].map(nutrient_ids)
    nutrient_groups = nutrients.groupby("fdc_id", sort=False)

    categories = pd.read_csv(category_path, dtype={"id": "string"})
    category_lookup = dict(zip(categories["id"], categories["description"]))

    portions_by_food: dict[str, list[dict[str, Any]]] = {}
    if portion_path is not None:
        portions = pd.read_csv(portion_path, dtype={"fdc_id": "string"})
        for fdc_id, group in portions.groupby("fdc_id", sort=False):
            portions_by_food[fdc_id] = group[
                ["amount", "measure_unit_id", "portion_description", "modifier", "gram_weight"]
            ].where(pd.notna(group), None).to_dict("records")

    normalized: list[dict[str, Any]] = []
    for food in foods.itertuples(index=False):
        food_id = str(food.fdc_id)
        food_nutrients: dict[str, dict[str, Any]] = {}
        if food_id in nutrient_groups.groups:
            for nutrient in nutrient_groups.get_group(food_id).itertuples(index=False):
                food_nutrients[nutrient.nutrient_name] = {
                    "amount": None if pd.isna(nutrient.amount) else float(nutrient.amount),
                    "unit": "g" if nutrient.nutrient_name != "Energy" else "kcal",
                }
        normalized.append(
            {
                "fdc_id": food_id,
                "description": food.description,
                "category": category_lookup.get(str(food.food_category_id)),
                "nutrients": food_nutrients,
                "portions": portions_by_food.get(food_id, []),
            }
        )

    output_path = processed_dir / "nutrition.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    return {
        "source": "SR Legacy",
        "path": str(sr_root),
        "output": str(output_path),
        "records": len(normalized),
        "problems": [],
    }


def prepare_fndds(source: Path, processed_dir: Path) -> dict[str, Any]:
    """Normalize FNDDS as a secondary source when SR Legacy is unavailable."""

    try:
        raw_data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"problems": [f"Could not read nutrition data: {exc}"]}

    foods = raw_data.get("SurveyFoods") if isinstance(raw_data, dict) else raw_data
    if not isinstance(foods, list):
        return {"problems": ["FNDDS data must contain a SurveyFoods list"]}

    normalized: list[dict[str, Any]] = []
    for food in foods:
        nutrients: dict[str, Any] = {}
        for item in food.get("foodNutrients", []):
            nutrient = item.get("nutrient", {})
            name = nutrient.get("name")
            if name in {
                "Energy",
                "Protein",
                "Total lipid (fat)",
                "Carbohydrate, by difference",
            }:
                nutrients[name] = {
                    "amount": item.get("amount"),
                    "unit": nutrient.get("unitName"),
                }
        normalized.append(
            {
                "fdc_id": food.get("fdcId"),
                "food_code": food.get("foodCode"),
                "description": food.get("description"),
                "category": food.get("wweiaFoodCategory"),
                "nutrients": nutrients,
                "portions": food.get("foodPortions", []),
            }
        )

    output_path = processed_dir / "nutrition_fndds.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    return {
        "path": str(source),
        "source": "FNDDS",
        "output": str(output_path),
        "records": len(normalized),
        "problems": [],
    }


def write_report(report: dict[str, Any], processed_dir: Path) -> Path:
    processed_dir.mkdir(parents=True, exist_ok=True)
    report_path = processed_dir / "preparation_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED_DATA_DIR)
    args = parser.parse_args()

    intent_report = prepare_intents(args.raw_dir, args.processed_dir)
    exercise_report = prepare_exercises(args.raw_dir, args.processed_dir)
    nutrition_report = prepare_nutrition(args.raw_dir, args.processed_dir)
    report = {
        "augmentation": "disabled",
        "intent_dataset": intent_report,
        "exercise_database": exercise_report,
        "nutrition": nutrition_report,
    }
    report_path = write_report(report, args.processed_dir)

    print(f"Preparation report: {report_path}")
    if intent_report["splits"]:
        for split, details in intent_report["splits"].items():
            print(f"{split}: {details['rows']} rows")
    else:
        print("No intent splits found under data/raw/intent_dataset/")

    if "records" in exercise_report:
        print(f"exercises: {exercise_report['records']} records")
    if "records" in nutrition_report:
        print(f"nutrition: {nutrition_report['records']} records")

    problems = intent_report["problems"] + exercise_report["problems"] + nutrition_report["problems"]
    for problem in problems:
        print(f"WARNING: {problem}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
