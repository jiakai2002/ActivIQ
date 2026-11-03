"""Prepare ten blank, stratified training-seed annotation records."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.auto_labelling.core import ExperimentData


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/processed/intents")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/auto_labelling")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        result = ExperimentData(args.source_dir).prepare_seeds(args.output_dir, args.seed)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
