"""Direct, offline Transformers inference; no model-serving or LLM API client."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import time

from src.auto_labelling.core import digest
from src.evaluation import file_hash


class PromptBudgetError(ValueError):
    """A particular prompt cannot fit without changing experimental inputs."""


@dataclass
class Generation:
    text: str
    seconds: float
    input_tokens: int
    output_tokens: int
    finish_reason: str

    def to_dict(self):
        return asdict(self)


class LocalTransformersEngine:
    def __init__(self, model_path: Path, device: str = "cpu", quantization: str = "none",
                 max_input_tokens: int = 8192, max_new_tokens: int = 512, progress=print):
        model_path = Path(model_path).resolve()
        if not model_path.is_dir() or not (model_path / "config.json").is_file():
            raise ValueError("--model-path must be a local checkpoint directory containing config.json; no automatic downloads")
        if device not in {"cpu", "cuda"} or quantization not in {"none", "4bit"}:
            raise ValueError("Device must be cpu/cuda and quantization none/4bit")
        if max_input_tokens < 1 or max_new_tokens < 1:
            raise ValueError("Token budgets must be positive")
        if quantization == "4bit" and device != "cuda":
            raise ValueError("This workflow's 4-bit mode requires CUDA; use the isolated GPU/Colab environment")
        config = json.loads((model_path / "config.json").read_text())
        import torch
        import transformers
        if device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA is not available; no silent CPU fallback for a requested GPU run")
        if config.get("model_type") == "qwen3_5":
            if not hasattr(transformers, "Qwen3_5ForConditionalGeneration"):
                raise ValueError("Qwen3.5 requires the separate requirements-llm.txt environment (Transformers >=5.3); the chatbot environment is unchanged")
            model_class = transformers.Qwen3_5ForConditionalGeneration
        else:
            model_class = transformers.AutoModelForCausalLM
        weights = sorted(model_path.glob("*.safetensors"))
        if not weights:
            raise ValueError("A local safetensors checkpoint is required")
        files = sorted({*model_path.glob("*.json"), *model_path.glob("*.model"), *model_path.glob("*.txt"),
                        *model_path.glob("*.jinja"), *(model_path / "additional_chat_templates").glob("*.jinja"), *weights})
        hashes = {}
        for path in files:
            progress(f"Fingerprinting checkpoint file: {path.name}")
            hashes[str(path.relative_to(model_path))] = {"sha256": file_hash(path), "bytes": path.stat().st_size}
        dtype = torch.float32 if device == "cpu" else (torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16)
        kwargs = {"local_files_only": True, "trust_remote_code": False, "use_safetensors": True,
                  "device_map": {"": "cpu" if device == "cpu" else 0}}
        # Transformers 5 uses dtype; retain generic-checkpoint smoke support in
        # the existing Transformers 4 chatbot environment without upgrading it.
        kwargs["dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"] = dtype
        if quantization == "4bit":
            try:
                bnb_version = version("bitsandbytes")
            except PackageNotFoundError as error:
                raise ValueError("Install requirements-llm-4bit.txt in the separate CUDA environment") from error
            kwargs["quantization_config"] = transformers.BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=dtype)
        else:
            bnb_version = None
        progress("Loading local model weights...")
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(model_path, local_files_only=True, trust_remote_code=False)
        if not self.tokenizer.chat_template:
            raise ValueError("The checkpoint must provide a chat template; no implicit prompt-format fallback")
        self.model = model_class.from_pretrained(model_path, **kwargs).eval()
        self.torch, self.set_seed = torch, transformers.set_seed
        self.device = device
        self.max_input_tokens, self.max_new_tokens = max_input_tokens, max_new_tokens
        text_config = getattr(self.model.config, "text_config", self.model.config)
        self.context_window = getattr(text_config, "max_position_embeddings", None) or getattr(text_config, "n_positions", None)
        identity = {"backend": "transformers_local", "checkpoint_files": hashes,
                    "checkpoint_model_type": config.get("model_type"), "loaded_model_class": type(self.model).__name__,
                    "transformers": transformers.__version__, "torch": torch.__version__,
                    "bitsandbytes": bnb_version, "quantization": quantization, "dtype": str(dtype),
                    "max_input_tokens": max_input_tokens, "max_new_tokens": max_new_tokens,
                    "enable_thinking": False, "trust_remote_code": False}
        self.metadata = {**identity, "signature": digest(identity), "model_path": str(model_path),
                         "platform": platform.platform(), "device": device,
                         "cuda_device": torch.cuda.get_device_name(0) if device == "cuda" else None}

    def generate(self, messages: list[dict], seed: int, sample: bool = False) -> Generation:
        self.set_seed(seed)
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                                    enable_thinking=False)
        encoded = self.tokenizer(prompt, return_tensors="pt", add_special_tokens=False)
        input_tokens = int(encoded["input_ids"].shape[-1])
        if input_tokens > self.max_input_tokens:
            raise PromptBudgetError(f"Prompt has {input_tokens} tokens, exceeding {self.max_input_tokens}; seeds/utterance were not truncated")
        if self.context_window and input_tokens + self.max_new_tokens > self.context_window:
            raise PromptBudgetError("Prompt plus output budget exceeds the model context window; no silent truncation")
        encoded = encoded.to(self.model.device)
        eos = self.model.generation_config.eos_token_id
        if eos is None:
            eos = self.tokenizer.eos_token_id
        if eos is None:
            raise ValueError("The checkpoint must define an EOS token")
        kwargs = {"max_new_tokens": self.max_new_tokens, "do_sample": sample,
                  "return_dict_in_generate": False, "use_cache": True,
                  "eos_token_id": eos,
                  "pad_token_id": self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id}
        if sample:
            kwargs.update(temperature=0.7, top_p=0.9)
        start = time.perf_counter()
        with self.torch.inference_mode():
            output = self.model.generate(**encoded, **kwargs)
        if self.device == "cuda":
            self.torch.cuda.synchronize()
        seconds = time.perf_counter() - start
        continuation = output[0, input_tokens:]
        ids = continuation.tolist()
        eos_ids = eos if isinstance(eos, list) else [eos]
        stopped = bool(ids and ids[-1] in eos_ids)
        return Generation(self.tokenizer.decode(continuation, skip_special_tokens=True), seconds,
                          input_tokens, len(ids), "eos" if stopped else "length")
