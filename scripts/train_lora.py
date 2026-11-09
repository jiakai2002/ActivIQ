"""Fine-tune a small Qwen model with LoRA on machine-generated labels.

Input: machine_labels.jsonl from `scripts/auto_label.py label`.
Output: a LoRA adapter directory plus training_report.json.

Run this in the separate research environment (.venv-llm), see
data/auto_labelling/README.md. No external API is used.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluation import file_hash
from src.lora import load_base_model, pick_device, render_prompt, target_json


def load_examples(path: Path) -> list[dict]:
    """Machine-generated training labels only. Test-split rows are never accepted."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("split") == "test":
            raise ValueError(f"{path}: test-split rows must never be used for training ({row.get('id')})")
        if row.get("label_status") != "machine_generated" or row.get("split", "train") != "train":
            raise ValueError(f"{path}: only machine-generated training labels may be used, got {row.get('id')}")
        rows.append(row)
    if not rows:
        raise ValueError(f"{path} has no rows")
    return rows


def encode(tokenizer, row: dict, max_length: int) -> dict:
    """Mask the prompt so the loss covers only the JSON answer and EOS."""
    prompt_ids = tokenizer(render_prompt(tokenizer, row["text"]), add_special_tokens=False)["input_ids"]
    answer = target_json(row["intent"], row["entities"]) + tokenizer.eos_token
    answer_ids = tokenizer(answer, add_special_tokens=False)["input_ids"]
    ids = (prompt_ids + answer_ids)[:max_length]
    labels = ([-100] * len(prompt_ids) + answer_ids)[:max_length]
    return {"input_ids": ids, "labels": labels}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True, help="Local Qwen3.5-2B checkpoint")
    parser.add_argument("--labels", type=Path, required=True, help="machine_labels.jsonl")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=("auto", "cuda", "mps", "cpu"), default="auto")
    parser.add_argument("--quantization", choices=("none", "4bit"), default="none")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--alpha", type=int, default=32)
    parser.add_argument("--dropout", type=float, default=0.05)
    parser.add_argument("--max-length", type=int, default=384)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"{args.output_dir} is not empty; choose a new directory")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = pick_device(args.device)
    rows = load_examples(args.labels)
    model, tokenizer, dtype = load_base_model(args.model_path, device, args.quantization)
    if args.quantization == "4bit":
        model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, LoraConfig(
        r=args.rank, lora_alpha=args.alpha, lora_dropout=args.dropout,
        target_modules="all-linear", task_type="CAUSAL_LM"))
    model.print_trainable_parameters()
    model.train()

    examples = [encode(tokenizer, row, args.max_length) for row in rows]
    pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    optimiser = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.learning_rate)
    steps = args.epochs * ((len(examples) + args.batch_size - 1) // args.batch_size)
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimiser, lambda s: max(0.0, 1 - s / max(1, steps)))

    log, step, start = [], 0, time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        random.shuffle(examples)
        total = 0.0
        for i in range(0, len(examples), args.batch_size):
            batch = examples[i:i + args.batch_size]
            width = max(len(item["input_ids"]) for item in batch)
            ids = torch.tensor([item["input_ids"] + [pad] * (width - len(item["input_ids"])) for item in batch])
            lab = torch.tensor([item["labels"] + [-100] * (width - len(item["labels"])) for item in batch])
            mask = torch.tensor([[1] * len(item["input_ids"]) + [0] * (width - len(item["input_ids"])) for item in batch])
            loss = model(input_ids=ids.to(model.device), attention_mask=mask.to(model.device),
                         labels=lab.to(model.device)).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimiser.step()
            scheduler.step()
            optimiser.zero_grad()
            step += 1
            total += loss.item() * len(batch)
            if step % 10 == 0:
                print(f"epoch {epoch} step {step}/{steps} loss {loss.item():.4f}", flush=True)
        log.append({"epoch": epoch, "mean_loss": total / len(examples)})
        print(f"epoch {epoch} mean loss {log[-1]['mean_loss']:.4f}", flush=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    report = {"base_model": str(args.model_path), "labels": str(args.labels), "labels_sha256": file_hash(args.labels),
              "examples": len(rows), "device": device, "quantization": args.quantization, "dtype": str(dtype),
              "epochs": args.epochs, "batch_size": args.batch_size, "learning_rate": args.learning_rate,
              "lora_rank": args.rank, "lora_alpha": args.alpha, "lora_dropout": args.dropout,
              "max_length": args.max_length, "seed": args.seed, "epoch_losses": log,
              "train_seconds": time.perf_counter() - start,
              "note": "Trained on machine-generated labels only. Evaluate with scripts/evaluate_lora.py."}
    (args.output_dir / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved adapter to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
