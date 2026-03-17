from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.storage.config import get_base_dir


def _default_dataset_path() -> Path:
    return get_base_dir() / "fine_tuning" / "lora_dataset.jsonl"


def _default_output_path() -> Path:
    return get_base_dir() / "fine_tuning" / "lora_output"


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
        except Exception:
            continue
    return rows


def _to_sft_text(row: dict) -> str | None:
    messages = row.get("messages", [])
    if not isinstance(messages, list) or len(messages) < 2:
        return None

    user_text = ""
    assistant_text = ""
    for m in messages:
        role = str(m.get("role", "")).strip().lower()
        content = str(m.get("content", "")).strip()
        if not content:
            continue
        if role == "user" and not user_text:
            user_text = content
        elif role == "assistant" and not assistant_text:
            assistant_text = content

    if not user_text or not assistant_text:
        return None

    return f"<s>[INST] {user_text} [/INST] {assistant_text}</s>"


def _build_training_texts(dataset_path: Path) -> list[str]:
    rows = _load_jsonl(dataset_path)
    texts: list[str] = []
    for row in rows:
        text = _to_sft_text(row)
        if text:
            texts.append(text)
    return texts


def train_lora(
    dataset_path: Path,
    output_dir: Path,
    base_model: str,
    max_length: int,
    epochs: float,
    batch_size: int,
    grad_accum: int,
    learning_rate: float,
    use_4bit: bool,
) -> None:
    try:
        import torch
        from datasets import Dataset
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            DataCollatorForLanguageModeling,
            Trainer,
            TrainingArguments,
        )
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    except ImportError as exc:
        raise RuntimeError(
            "Faltan dependencias de fine-tuning. Instala con: pip install -r requirements-finetune.txt"
        ) from exc

    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset no encontrado: {dataset_path}")

    texts = _build_training_texts(dataset_path)
    if len(texts) < 20:
        raise RuntimeError(
            f"Dataset demasiado pequeño ({len(texts)} ejemplos). Exporta más ejemplos antes de entrenar."
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = None
    if use_4bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.float16,
        )

    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map="auto",
        torch_dtype=torch.float16,
        quantization_config=quant_config,
    )

    if use_4bit:
        model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora_config)

    ds = Dataset.from_dict({"text": texts})

    def tokenize_fn(batch: dict) -> dict:
        out = tokenizer(
            batch["text"],
            truncation=True,
            max_length=max_length,
            padding="max_length",
        )
        out["labels"] = out["input_ids"].copy()
        return out

    tokenized = ds.map(tokenize_fn, batched=True, remove_columns=["text"])

    args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=grad_accum,
        learning_rate=learning_rate,
        logging_steps=10,
        save_strategy="epoch",
        fp16=True,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )

    trainer.train()
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    meta = {
        "base_model": base_model,
        "examples": len(texts),
        "dataset_path": str(dataset_path),
        "output_dir": str(output_dir),
        "use_4bit": use_4bit,
        "epochs": epochs,
        "batch_size": batch_size,
        "grad_accum": grad_accum,
        "learning_rate": learning_rate,
        "max_length": max_length,
    }
    (output_dir / "training_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LoRA adapters for MINDORA with exported JSONL dataset")
    parser.add_argument("--dataset-path", type=str, default=str(_default_dataset_path()))
    parser.add_argument("--output-dir", type=str, default=str(_default_output_path()))
    parser.add_argument("--base-model", type=str, default=os.getenv("IA_OFFLINE_FT_BASE_MODEL", "mistralai/Mistral-7B-v0.1"))
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit quantization")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_lora(
        dataset_path=Path(args.dataset_path),
        output_dir=Path(args.output_dir),
        base_model=args.base_model,
        max_length=args.max_length,
        epochs=args.epochs,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        learning_rate=args.learning_rate,
        use_4bit=not args.no_4bit,
    )


if __name__ == "__main__":
    main()
