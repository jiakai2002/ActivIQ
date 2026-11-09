"""Record that a named person has reviewed the seed and validation annotations.

Run this ONLY after you have read data/auto_labelling/ANNOTATION_REVIEW.md and
checked the labels yourself. It sets label_status to human_reviewed and writes
your name as annotator. Original AI provenance is kept, and an `ai_assisted`
flag stays on every record so the report can disclose AI assistance.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (ROOT / "data/auto_labelling/seeds.jsonl", ROOT / "data/evaluation/entities_validation.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotator", required=True, help="Your full name: the person responsible for the labels")
    args = parser.parse_args()
    name = args.annotator.strip()
    if not name:
        raise SystemExit("--annotator must not be empty")
    for path in FILES:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            row["label_status"] = "human_reviewed"
            row["annotator"] = name
            row.setdefault("annotation_provenance", {})["ai_assisted"] = True
            row["annotation_provenance"]["human_reviewed"] = True
        path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
        print(f"{path.relative_to(ROOT)}: {len(rows)} records signed off by {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
