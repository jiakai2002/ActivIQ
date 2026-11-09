"""Compare the LoRA model with DistilBERT + spaCy on the held-out test split.

Reports intent accuracy and macro-F1, entity F1 and per-utterance latency for
both systems on the same 120 test utterances. Entity F1 uses human labels
only: it stays pending until data/evaluation/entities_test.jsonl is reviewed,
unless --allow-draft is given (the result is then marked provisional).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_intent import macro_f1
from src.auto_labelling.core import parse_annotation
from src.config import INTENT_LABELS, PROCESSED_DATA_DIR
from src.entity_extractor import FitnessEntityExtractor
from src.evaluation import ENTITY_SLOTS, prf, read_jsonl, score_entities, timing_summary
from src.intent_classifier import IntentClassifier
from src.lora import load_base_model, pick_device, render_prompt


def intent_metrics(gold: list[str], predicted: list[str]) -> dict:
    index = {label: i for i, label in enumerate(INTENT_LABELS)}
    y = [index[g] for g in gold]
    p = [index.get(x, -1) for x in predicted]  # invalid output counts as wrong
    per_class = {}
    for label, i in index.items():
        tp = sum(a == i and b == i for a, b in zip(y, p))
        fp = sum(a != i and b == i for a, b in zip(y, p))
        fn = sum(a == i and b != i for a, b in zip(y, p))
        per_class[label] = prf(tp, fp, fn)
    confusion = {g: {q: 0 for q in [*INTENT_LABELS, "INVALID"]} for g in INTENT_LABELS}
    for g, q in zip(gold, predicted):
        confusion[g][q if q in index else "INVALID"] += 1
    return {"accuracy": sum(a == b for a, b in zip(y, p)) / len(y),
            "macro_f1": macro_f1(y, p, len(INTENT_LABELS)),
            "weighted_f1": sum(m["f1"] * m["support"] for m in per_class.values()) / len(y),
            "per_class": per_class, "confusion_gold_by_predicted": confusion}


def entity_metrics(records: list[dict], predictions: dict[str, dict], allow_draft: bool) -> dict:
    ready = [r for r in records if isinstance(r.get("entities"), dict) and (
        (r.get("label_status") == "human_reviewed" and r.get("annotator")) or allow_draft and r.get("label_status") != "unlabelled")]
    if len(ready) < len(records):
        return {"status": "pending_human_annotation", "scored": len(ready), "total": len(records)}
    empty = {slot: [] for slot in ENTITY_SLOTS}
    result = score_entities([r["entities"] for r in ready], [predictions.get(r["id"], empty) for r in ready])
    result["provisional"] = allow_draft
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True, help="Base Qwen3.5-2B checkpoint")
    parser.add_argument("--adapter", type=Path, default=None,
                        help="LoRA adapter directory. Omit to benchmark the bare base model (e.g. Qwen3.5-9B zero-shot)")
    parser.add_argument("--skip-baseline", action="store_true",
                        help="Skip DistilBERT+spaCy (needs models/intent_classifier and the spaCy model)")
    parser.add_argument("--device", choices=("auto", "cuda", "mps", "cpu"), default="auto")
    parser.add_argument("--quantization", choices=("none", "4bit"), default="none")
    parser.add_argument("--entities", type=Path, default=ROOT / "data/evaluation/entities_test.jsonl")
    parser.add_argument("--allow-draft", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    import torch
    from peft import PeftModel

    test = pd.read_csv(PROCESSED_DATA_DIR / "intents" / "test.csv")
    texts, gold_intents = list(test["text"]), list(test["label"])
    records = read_jsonl(args.entities)
    ids_by_text = {r["text"]: r["id"] for r in records}
    if len(ids_by_text) != len(records) or set(ids_by_text) != set(texts):
        raise SystemExit("entities file must hold exactly the 120 test utterances")

    # Baseline: DistilBERT + spaCy rules, same texts, same timing method.
    base_intents, base_entities, base_times = [], {}, []
    if not args.skip_baseline:
        classifier, extractor = IntentClassifier(), FitnessEntityExtractor()
        classifier.predict(texts[0]); extractor.extract(texts[0])  # warm-up
        for text in texts:
            start = time.perf_counter()
            base_intents.append(classifier.predict(text)["intent"])
            base_entities[ids_by_text[text]] = extractor.extract(text)
            base_times.append(time.perf_counter() - start)

    # LLM (bare base model, or base + LoRA adapter).
    device = pick_device(args.device)
    model, tokenizer, _ = load_base_model(args.model_path, device, args.quantization)
    model = (PeftModel.from_pretrained(model, args.adapter) if args.adapter else model).eval()
    eos = tokenizer.eos_token_id

    def generate(text: str) -> tuple[str, float]:
        encoded = tokenizer(render_prompt(tokenizer, text), return_tensors="pt", add_special_tokens=False).to(model.device)
        start = time.perf_counter()
        with torch.inference_mode():
            out = model.generate(**encoded, max_new_tokens=args.max_new_tokens, do_sample=False,
                                 eos_token_id=eos, pad_token_id=eos)
        if device == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
        return tokenizer.decode(out[0, encoded["input_ids"].shape[-1]:], skip_special_tokens=True), elapsed

    generate(texts[0])  # warm-up
    lora_intents, lora_entities, lora_times, invalid = [], {}, [], []
    for text in texts:
        raw, seconds = generate(text)
        lora_times.append(seconds)
        try:
            parsed = parse_annotation(raw)
            lora_intents.append(parsed["intent"])
            lora_entities[ids_by_text[text]] = parsed["entities"]
        except ValueError as error:  # JSONDecodeError is a ValueError
            lora_intents.append("INVALID")
            invalid.append({"text": text, "output": raw, "error": str(error)})

    report = {
        "test_utterances": len(texts),
        **({} if args.skip_baseline else {"distilbert_spacy": {
            "intent": intent_metrics(gold_intents, base_intents),
            "entities": entity_metrics(records, base_entities, args.allow_draft),
            "latency_seconds": timing_summary(base_times)}}),
        "lora": {"model_path": str(args.model_path), "adapter": str(args.adapter) if args.adapter else None,"intent": intent_metrics(gold_intents, lora_intents),
                 "entities": entity_metrics(records, lora_entities, args.allow_draft),
                 "latency_seconds": timing_summary(lora_times),
                 "invalid_outputs": len(invalid), "device": device, "quantization": args.quantization},
        "invalid_examples": invalid[:20],
        "note": "Entity scores are pending until the test entity labels are human reviewed.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "lora_comparison.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    for name in [n for n in ("distilbert_spacy", "lora") if n in report]:
        r = report[name]
        ent = r["entities"]
        f1 = ent["micro"]["f1"] if "micro" in ent else ent["status"]
        print(f"{name}: acc={r['intent']['accuracy']:.4f} macroF1={r['intent']['macro_f1']:.4f} "
              f"entityF1={f1} median={r['latency_seconds'].get('median_seconds')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
