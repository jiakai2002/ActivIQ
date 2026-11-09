"""Shared prompt format and model loading for the LoRA labelling experiment.

The LoRA model reads one utterance and writes one JSON object:
{"intent": ..., "entities": {eight slots}}. Training and evaluation must use
the same prompt, so both scripts import it from here.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.config import INTENT_LABELS
from src.evaluation import ENTITY_SLOTS

SYSTEM_PROMPT = (
    "You label one fitness-chat utterance. Return only a JSON object with keys "
    "intent and entities. Intent is one of: " + ", ".join(INTENT_LABELS) + ". "
    "entities has these keys, each a list of strings: " + ", ".join(ENTITY_SLOTS) + "."
)


def messages(text: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]


def target_json(intent: str, entities: dict) -> str:
    """Stable, compact target text that the strict parser accepts."""
    return json.dumps({"intent": intent, "entities": {slot: entities[slot] for slot in ENTITY_SLOTS}},
                      ensure_ascii=True, separators=(",", ":"))


def render_prompt(tokenizer, text: str) -> str:
    return tokenizer.apply_chat_template(messages(text), tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False)


def pick_device(requested: str = "auto") -> str:
    import torch
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_base_model(model_path: Path, device: str, quantization: str = "none"):
    """Load a local checkpoint. Mirrors src/auto_labelling/engine.py class choice."""
    import torch
    import transformers

    config = json.loads((Path(model_path) / "config.json").read_text())
    if config.get("model_type") == "qwen3_5":
        if not hasattr(transformers, "Qwen3_5ForConditionalGeneration"):
            raise ValueError("Qwen3.5 needs Transformers >= 5.3: use the .venv-llm environment")
        model_class = transformers.Qwen3_5ForConditionalGeneration
    else:
        model_class = transformers.AutoModelForCausalLM
    dtype = torch.float32 if device == "cpu" else (
        torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float16)
    kwargs = {"local_files_only": True, "trust_remote_code": False, "use_safetensors": True}
    kwargs["dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"] = dtype
    if quantization == "4bit":
        if device != "cuda":
            raise ValueError("4-bit mode needs CUDA")
        kwargs["quantization_config"] = transformers.BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype)
        kwargs["device_map"] = {"": 0}
    tokenizer = transformers.AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
    if not tokenizer.chat_template:
        raise ValueError("The checkpoint must provide a chat template")
    model = model_class.from_pretrained(model_path, **kwargs)
    if quantization != "4bit":
        model = model.to(device)
    return model, tokenizer, dtype
