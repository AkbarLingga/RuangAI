from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # supaya folder proyek terbaca saat file ini dijalankan langsung

from analysis.sentiment_model import create_sentiment_pipeline


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_FILE = ROOT / "data" / "processed" / "social_ai_processed.csv"
ANNOTATION_FILE = ROOT / "data" / "annotations" / "sentiment_annotations.csv"
REPORT_FILE = ROOT / "data" / "evaluation" / "sentiment_evaluation.json"
LABELS = ("Positif", "Netral", "Negatif")
SAMPLE_COLUMNS = (
    "row_id", "platform", "source_id", "clean_text",
    "lexicon_sentiment", "human_sentiment",
)


def create_annotation_sample(
    data: pd.DataFrame, sample_size: int = 300, random_state: int = 42
) -> pd.DataFrame:
    required = {"platform", "source_id", "clean_text", "sentiment"}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Kolom dataset olahan hilang: {', '.join(missing)}")
    if not 0 < sample_size < len(data):
        raise ValueError(f"Ukuran sampel harus antara 1 dan {len(data) - 1}.")

    sample_data = data.reset_index(names="row_id").copy()
    sample_data["stratum"] = (
        sample_data["platform"].astype(str)
        + "|"
        + sample_data["sentiment"].astype(str)
    )
    stratum_counts = sample_data["stratum"].value_counts()
    if (stratum_counts < 2).any() or sample_size < len(stratum_counts):
        raise ValueError("Ukuran sampel tidak cukup untuk mewakili semua kelompok.")

    sampled = train_test_split(
        sample_data,
        train_size=sample_size,
        random_state=random_state,
        stratify=sample_data["stratum"],
    )[0]
    sampled = sampled.rename(columns={"sentiment": "lexicon_sentiment"})
    sampled["human_sentiment"] = ""
    return sampled.loc[:, SAMPLE_COLUMNS].sort_values("row_id").reset_index(drop=True)


def _classification_metrics(
    actual: pd.Series, predicted: pd.Series
) -> dict[str, object]:
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, labels=LABELS, average="macro")),
        "confusion_matrix": confusion_matrix(
            actual, predicted, labels=LABELS
        ).tolist(),
        "per_class": classification_report(
            actual,
            predicted,
            labels=LABELS,
            output_dict=True,
            zero_division=0,
        ),
    }


def evaluate_labeled_data(
    annotations: pd.DataFrame, test_size: float = 0.2, random_state: int = 42
) -> dict[str, object]:
    required = {"clean_text", "lexicon_sentiment", "human_sentiment"}
    missing = sorted(required - set(annotations.columns))
    if missing:
        raise ValueError(f"Kolom anotasi hilang: {', '.join(missing)}")

    labeled = annotations.copy()
    for column in required:
        labeled[column] = labeled[column].astype(str).str.strip()
    labeled = labeled[labeled["human_sentiment"] != ""]
    if not set(labeled["human_sentiment"]).issubset(LABELS):
        raise ValueError(f"Label manual harus salah satu dari: {', '.join(LABELS)}.")
    if labeled["human_sentiment"].nunique() != len(LABELS):
        raise ValueError("Anotasi harus memiliki contoh untuk ketiga kelas sentimen.")
    if labeled["human_sentiment"].value_counts().min() < 2:
        raise ValueError("Setiap kelas membutuhkan sedikitnya dua anotasi.")
    if not 0 < test_size < 1:
        raise ValueError("Proporsi data uji harus di antara 0 dan 1.")

    train, test = train_test_split(
        labeled,
        test_size=test_size,
        random_state=random_state,
        stratify=labeled["human_sentiment"],
    )
    model = create_sentiment_pipeline(random_state, class_weight="balanced")
    model.fit(train["clean_text"], train["human_sentiment"])
    model_predictions = pd.Series(
        model.predict(test["clean_text"]), index=test.index
    )
    return {
        "seed": random_state,
        "test_size": test_size,
        "labeled_rows": len(labeled),
        "train_rows": len(train),
        "test_rows": len(test),
        "class_distribution": labeled["human_sentiment"].value_counts().to_dict(),
        "lexicon_baseline": _classification_metrics(
            test["human_sentiment"], test["lexicon_sentiment"]
        ),
        "tfidf_logistic_regression": _classification_metrics(
            test["human_sentiment"], model_predictions
        ),
    }


def prepare_sample(sample_size: int, random_state: int) -> None:
    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            f"Dataset olahan tidak ditemukan: {PROCESSED_FILE}. "
            "Jalankan `python analysis/merge_social_data.py` terlebih dahulu."
        )
    if ANNOTATION_FILE.exists():
        raise FileExistsError(
            f"File anotasi sudah ada: {ANNOTATION_FILE}. "
            "Pindahkan atau ganti nama file tersebut agar anotasi tidak tertimpa."
        )

    data = pd.read_csv(PROCESSED_FILE, keep_default_na=False)
    sample = create_annotation_sample(data, sample_size, random_state)
    ANNOTATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(ANNOTATION_FILE, index=False, encoding="utf-8-sig")
    print(f"Template anotasi dibuat: {ANNOTATION_FILE}")
    print("Isi kolom human_sentiment dengan Positif, Netral, atau Negatif.")


def write_evaluation(test_size: float, random_state: int) -> None:
    if not ANNOTATION_FILE.exists():
        raise FileNotFoundError(
            f"File anotasi tidak ditemukan: {ANNOTATION_FILE}. "
            "Jalankan `python analysis/evaluate_sentiment.py sample` terlebih dahulu."
        )
    annotations = pd.read_csv(ANNOTATION_FILE, keep_default_na=False)
    report = evaluate_labeled_data(annotations, test_size, random_state)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for method in ("lexicon_baseline", "tfidf_logistic_regression"):
        metrics = report[method]
        print(
            f"{method}: accuracy={metrics['accuracy']:.3f}, "
            f"macro-F1={metrics['macro_f1']:.3f}"
        )
    print(f"Laporan evaluasi tersimpan: {REPORT_FILE}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Siapkan anotasi manual dan evaluasi metode analisis sentimen."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    sample_parser = commands.add_parser(
        "sample", help="Buat sampel berstrata untuk diberi label secara manual."
    )
    sample_parser.add_argument("--size", type=int, default=300)
    sample_parser.add_argument("--seed", type=int, default=42)
    evaluate_parser = commands.add_parser(
        "evaluate", help="Bandingkan baseline leksikon dan model TF-IDF."
    )
    evaluate_parser.add_argument("--test-size", type=float, default=0.2)
    evaluate_parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    try:
        if args.command == "sample":
            prepare_sample(args.size, args.seed)
        else:
            write_evaluation(args.test_size, args.seed)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        print(f"Gagal menjalankan evaluasi: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
