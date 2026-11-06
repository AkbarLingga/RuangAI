"""
Klasifikasi sentimen dan deteksi sarkasme memakai model Transformer (RoBERTa).

Semua model adalah RoBERTa pra-latih dan dipakai tanpa kamus kata:

- Sentimen : cardiffnlp/twitter-roberta-base-sentiment-latest
- Sarkasme : cardiffnlp/twitter-roberta-base-irony (dilatih dari tweet)
             jkhan447/sarcasm-detection-RoBerta-base-CR (unggul pada data Reddit)

Sarkasme memakai dua model karena satu model saja terlalu sering salah menandai
komentar tulus. Skor akhirnya adalah skor terendah dari keduanya, jadi sebuah
komentar hanya ditandai kalau kedua model sama-sama yakin.

RoBERTa adalah turunan BERT. Keduanya membaca konteks kalimat dari dua arah
(bidirectional), sehingga arti sebuah kata ikut ditentukan oleh kata di sekitarnya.

Alur per komentar:
  teks -> tokenizer -> RoBERTa -> logit -> softmax -> probabilitas tiap kelas
"""
from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # supaya folder proyek terbaca saat file ini dijalankan langsung

from analysis import config

SENTIMENT_LABELS = {"negative": "Negatif", "neutral": "Netral", "positive": "Positif"}
MAX_TOKENS = 256
BATCH_SIZE = 16


@lru_cache(maxsize=3)
def _load(model_name: str):
    """Muat tokenizer dan model satu kali, lalu pakai ulang."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return tokenizer, model.to(device), device


def _probabilities(
    model_name: str, texts: Sequence[str], batch_size: int, progress: bool
) -> list[list[float]]:
    """Hitung probabilitas kelas. Teks diurutkan menurut panjang agar batch efisien."""
    import torch

    tokenizer, model, device = _load(model_name)
    order = sorted(range(len(texts)), key=lambda index: len(texts[index]))
    results: list[list[float]] = [[] for _ in texts]
    batches: Iterable[int] = range(0, len(order), batch_size)
    if progress:
        from tqdm import tqdm

        batches = tqdm(batches, desc=model_name.split("/")[-1])

    with torch.no_grad():
        for start in batches:
            indexes = order[start:start + batch_size]
            encoded = tokenizer(
                [texts[index] for index in indexes],
                padding=True,
                truncation=True,
                max_length=MAX_TOKENS,
                return_tensors="pt",
            ).to(device)
            logits = model(**encoded).logits
            rows = torch.softmax(logits, dim=-1).cpu().tolist()
            for index, row in zip(indexes, rows):
                results[index] = row
    return results


def _class_names(model_name: str) -> list[str]:
    model = _load(model_name)[1]
    return [model.config.id2label[index].lower() for index in range(model.config.num_labels)]


def predict_sentiment(
    texts: Sequence[str], batch_size: int = BATCH_SIZE, progress: bool = False
) -> list[dict[str, object]]:
    """Kembalikan label, keyakinan, polaritas, dan probabilitas sentimen tiap teks."""
    name = config.ROBERTA_SENTIMENT_MODEL
    rows = _probabilities(name, texts, batch_size, progress)
    classes = [SENTIMENT_LABELS[label] for label in _class_names(name)]
    predictions = []
    for row in rows:
        probabilities = dict(zip(classes, row))
        label = max(probabilities, key=probabilities.get)
        predictions.append(
            {
                "sentiment": label,
                "sentiment_score": probabilities[label],
                "polarity": probabilities["Positif"] - probabilities["Negatif"],
                "probabilities": probabilities,
            }
        )
    return predictions


def predict_sarcasm(
    texts: Sequence[str], batch_size: int = BATCH_SIZE, progress: bool = False
) -> list[float]:
    """Kembalikan skor sarkasme tiap teks: skor terendah dari kedua model."""
    irony = [row[1] for row in _probabilities(config.ROBERTA_IRONY_MODEL, texts, batch_size, progress)]
    sarcasm = [row[1] for row in _probabilities(config.ROBERTA_SARCASM_MODEL, texts, batch_size, progress)]
    return [min(pair) for pair in zip(irony, sarcasm)]


def _sarcasm_label(score: float) -> str:
    return "Ya" if score >= config.SARCASM_THRESHOLD else "Tidak"


def analyze_text(text: str) -> dict[str, object]:
    """Analisis satu teks untuk fitur coba langsung di web."""
    sentiment = predict_sentiment([text])[0]
    score = predict_sarcasm([text])[0]
    return {**sentiment, "sarcasm": _sarcasm_label(score), "sarcasm_score": score}


def label_frame(frame, text_column: str = "clean_text"):
    """Tambahkan kolom sentimen dan sarkasme ke DataFrame."""
    texts = frame[text_column].astype(str).tolist()
    sentiments = predict_sentiment(texts, progress=True)
    sarcasm_scores = predict_sarcasm(texts, progress=True)
    labeled = frame.copy()
    labeled["sentiment"] = [row["sentiment"] for row in sentiments]
    labeled["sentiment_score"] = [round(row["sentiment_score"], 4) for row in sentiments]
    labeled["polarity"] = [round(row["polarity"], 4) for row in sentiments]
    labeled["sarcasm"] = [_sarcasm_label(score) for score in sarcasm_scores]
    labeled["sarcasm_score"] = [round(score, 4) for score in sarcasm_scores]
    return labeled
