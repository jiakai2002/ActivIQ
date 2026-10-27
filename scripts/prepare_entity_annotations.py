"""Create blank entity annotation sheets without using model predictions as gold."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import PROCESSED_DATA_DIR
from src.evaluation import ENTITY_SLOTS, file_hash


def prepare_annotations(output_dir: Path, validation_count: int = 100, seed: int = 42) -> dict:
    if validation_count < 1:
        raise ValueError("validation_count must be positive")
    outputs = [output_dir / f"entities_{split}.jsonl" for split in ("validation", "test")]
    outputs.append(output_dir / "annotation_manifest.json")
    if any(path.exists() for path in outputs):
        raise FileExistsError("Annotation outputs already exist; refusing to overwrite human labels. Use a new output directory.")
    prepared, sources = {}, {}
    for split in ("validation", "test"):
        source = PROCESSED_DATA_DIR / "intents" / f"{split}.csv"
        with source.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        indexed = list(enumerate(rows, 1))
        if split == "validation":
            if validation_count > len(indexed):
                raise ValueError("Requested validation annotations exceed available validation rows")
            indexed = sorted(random.Random(seed).sample(indexed, validation_count))
        prepared[split] = [{"id": f"entity-{split}-{index:03d}", "split": split,
                            "source_row": index, "text": row["text"], "intent": row["label"],
                            "label_status": "unlabelled", "annotator": None, "entities": None}
                           for index, row in indexed]
        sources[split] = {"path": str(source.relative_to(PROJECT_ROOT)), "sha256": file_hash(source),
                          "rows_selected": len(indexed)}
    output_dir.mkdir(parents=True, exist_ok=True)
    for split, rows in prepared.items():
        (output_dir / f"entities_{split}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=True) + "\n" for row in rows), encoding="utf-8")
    manifest = {"purpose": "Blank human annotation templates; not evaluation results or machine-generated gold labels",
                "sampling_seed": seed, "required_slots": ENTITY_SLOTS, "sources": sources,
                "policy": "Use validation labels for development. Freeze rules before scoring the test labels. Do not turn extractor predictions into reference labels."}
    (output_dir / "annotation_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data/evaluation")
    parser.add_argument("--validation-count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        manifest = prepare_annotations(args.output_dir, args.validation_count, args.seed)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
