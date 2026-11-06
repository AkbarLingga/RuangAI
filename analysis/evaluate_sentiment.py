"""
Evaluasi model Transformer terhadap label manual.

1. `sample`   membuat file Excel untuk diberi label oleh manusia. Jawaban model
              disimpan terpisah supaya pemberi label tidak terpengaruh.
2. `evaluate` membandingkan prediksi model dengan label manual tersebut.

Model dipakai apa adanya (tidak dilatih ulang pada data ini), jadi seluruh baris
berlabel bisa dipakai sebagai data uji.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # supaya folder proyek terbaca saat file ini dijalankan langsung

from analysis.config import DATA_DIR, LABELS, PROCESSED_FILE


ANNOTATION_FILE = DATA_DIR / "annotations" / "sentiment_annotations.csv"
LABEL_FILE = DATA_DIR / "annotations" / "label_manual.xlsx"
REPORT_FILE = DATA_DIR / "evaluation" / "sentiment_evaluation.json"
SARCASM_LABELS = ("Ya", "Tidak")
RANDOM_GROUP = "acak"
SARCASM_GROUP = "tambahan_sarkasme"
SARCASM_EXTRA = 40
SAMPLE_COLUMNS = (
    "row_id", "sample_group", "platform", "source_id", "clean_text",
    "model_sentiment", "human_sentiment", "model_sarcasm", "human_sarcasm",
)


def create_annotation_sample(
    data: pd.DataFrame,
    sample_size: int = 300,
    random_state: int = 42,
    sarcasm_extra: int = 0,
) -> pd.DataFrame:
    """Ambil sampel acak berstrata, ditambah komentar bertanda sarkasme bila diminta."""
    required = {"platform", "source_id", "clean_text", "sentiment", "sarcasm"}
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
    random_size = sample_size - sarcasm_extra
    if (stratum_counts < 2).any() or random_size < len(stratum_counts):
        raise ValueError("Ukuran sampel tidak cukup untuk mewakili semua kelompok.")

    sampled = train_test_split(
        sample_data,
        train_size=random_size,
        random_state=random_state,
        stratify=sample_data["stratum"],
    )[0]
    sampled = sampled.assign(sample_group=RANDOM_GROUP)
    if sarcasm_extra:
        remaining = sample_data[
            (sample_data["sarcasm"] == "Ya") & ~sample_data["row_id"].isin(sampled["row_id"])
        ]
        if len(remaining) < sarcasm_extra:
            raise ValueError("Komentar bertanda sarkasme tidak cukup untuk sampel tambahan.")
        extra = remaining.sample(n=sarcasm_extra, random_state=random_state)
        sampled = pd.concat([sampled, extra.assign(sample_group=SARCASM_GROUP)])
    sampled = sampled.rename(columns={"sentiment": "model_sentiment", "sarcasm": "model_sarcasm"})
    sampled["human_sentiment"] = ""
    sampled["human_sarcasm"] = ""
    return sampled.loc[:, SAMPLE_COLUMNS].sort_values("row_id").reset_index(drop=True)


LABEL_GUIDE = (
    "Panduan pemberian label",
    "Baca komentarnya, lalu isi dua kolom memakai dropdown. Nilai sikap penulis, bukan topiknya.",
    "",
    "human_sentiment",
    "Positif: penulis setuju, senang, memuji, atau berharap baik.",
    "Negatif: penulis marah, takut, kecewa, mengeluh, atau mengkritik.",
    "Netral: informasi, pertanyaan, berita, atau sikap penulis tidak jelas.",
    "Komentar sarkas: nilai arti sebenarnya. Contoh: Great, AI took my job = Negatif.",
    "",
    "human_sarcasm",
    "Ya: yang dimaksud penulis berlawanan dengan yang ditulis, biasanya untuk menyindir.",
    "Tidak: penulis berkata apa adanya. Kalau ragu, pilih Tidak.",
    "",
    "Kalau dikerjakan berdua, tentukan dulu aturan yang sama dan samakan cara menilai pada 10 komentar pertama.",
)


def _classification_metrics(
    actual: pd.Series, predicted: pd.Series, labels: tuple[str, ...]
) -> dict[str, object]:
    return {
        "rows": len(actual),
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
        "labels": list(labels),
        "confusion_matrix": confusion_matrix(actual, predicted, labels=labels).tolist(),
        "per_class": classification_report(
            actual, predicted, labels=labels, output_dict=True, zero_division=0
        ),
    }


def _labeled(annotations: pd.DataFrame, human: str, labels: tuple[str, ...]) -> pd.DataFrame:
    values = annotations[human].astype(str).str.strip()
    rows = annotations[values != ""].copy()
    rows[human] = values[values != ""]
    if not set(rows[human]).issubset(labels):
        raise ValueError(f"Isi {human} harus salah satu dari: {', '.join(labels)}.")
    return rows


def evaluate_labeled_data(annotations: pd.DataFrame) -> dict[str, object]:
    required = {"model_sentiment", "human_sentiment", "model_sarcasm", "human_sarcasm"}
    missing = sorted(required - set(annotations.columns))
    if missing:
        raise ValueError(f"Kolom anotasi hilang: {', '.join(missing)}")

    # Baris tambahan dipilih karena bertanda sarkasme, jadi tidak ikut menghitung
    # akurasi umum. Baris ini hanya dipakai untuk presisi sarkasme.
    random_rows = annotations
    if "sample_group" in annotations.columns:
        random_rows = annotations[annotations["sample_group"] == RANDOM_GROUP]

    sentiment = _labeled(random_rows, "human_sentiment", LABELS)
    if sentiment.empty:
        raise ValueError("Belum ada label manual pada human_sentiment.")
    report: dict[str, object] = {
        "sentiment": _classification_metrics(
            sentiment["human_sentiment"], sentiment["model_sentiment"].astype(str).str.strip(), LABELS
        ),
    }
    sarcasm = _labeled(random_rows, "human_sarcasm", SARCASM_LABELS)
    if not sarcasm.empty:
        report["sarcasm"] = _classification_metrics(
            sarcasm["human_sarcasm"], sarcasm["model_sarcasm"].astype(str).str.strip(), SARCASM_LABELS
        )
    flagged = _labeled(annotations, "human_sarcasm", SARCASM_LABELS)
    flagged = flagged[flagged["model_sarcasm"].astype(str).str.strip() == "Ya"]
    if not flagged.empty:
        report["sarcasm_flag_precision"] = {
            "rows": len(flagged),
            "precision": float((flagged["human_sarcasm"] == "Ya").mean()),
        }
    return report


def write_label_workbook(sample: pd.DataFrame, path: Path, random_state: int) -> None:
    """Buat file Excel tanpa jawaban model, dengan pilihan label berbentuk dropdown."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation

    rows = sample.sample(frac=1, random_state=random_state)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Label"
    sheet.append(["no", "row_id", "platform", "komentar", "human_sentiment", "human_sarcasm"])
    for number, row in enumerate(rows.itertuples(), start=1):
        sheet.append([number, row.row_id, row.platform, None, None, None])
        cell = sheet.cell(row=number + 1, column=4)
        cell.value = row.clean_text
        cell.data_type = "s"  # teks yang diawali "=" tidak boleh dibaca sebagai rumus
        cell.alignment = Alignment(wrap_text=True, vertical="top")

    last = len(rows) + 1
    for column, labels in (("E", LABELS), ("F", SARCASM_LABELS)):
        choices = DataValidation(type="list", formula1='"' + ",".join(labels) + '"', allow_blank=True)
        choices.error = "Pilih dari daftar."
        sheet.add_data_validation(choices)
        choices.add(f"{column}2:{column}{last}")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4B9C00")
    for column, width in zip("ABCDEF", (6, 9, 11, 90, 18, 16)):
        sheet.column_dimensions[column].width = width
    sheet.column_dimensions["B"].hidden = True
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:F{last}"

    guide = workbook.create_sheet("Panduan")
    for line in LABEL_GUIDE:
        guide.append([line])
    guide.column_dimensions["A"].width = 110
    guide["A1"].font = Font(bold=True)
    workbook.save(path)


def read_annotations() -> pd.DataFrame:
    """Gabungkan label manual dari Excel dengan jawaban model."""
    annotations = pd.read_csv(ANNOTATION_FILE, keep_default_na=False)
    if not LABEL_FILE.exists():
        return annotations
    labels = pd.read_excel(LABEL_FILE, sheet_name="Label", keep_default_na=False)
    labels = labels[["row_id", "human_sentiment", "human_sarcasm"]]
    model = annotations.drop(columns=["human_sentiment", "human_sarcasm"])
    return model.merge(labels, on="row_id", how="left", validate="one_to_one").fillna("")


def prepare_sample(sample_size: int, random_state: int) -> None:
    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            f"Dataset olahan tidak ditemukan: {PROCESSED_FILE}. "
            "Jalankan `python analysis/merge_social_data.py` terlebih dahulu."
        )
    if ANNOTATION_FILE.exists() or LABEL_FILE.exists():
        raise FileExistsError(
            f"File anotasi sudah ada di {ANNOTATION_FILE.parent}. "
            "Pindahkan atau ganti nama file tersebut agar anotasi tidak tertimpa."
        )

    data = pd.read_csv(PROCESSED_FILE, keep_default_na=False)
    sample = create_annotation_sample(data, sample_size, random_state, SARCASM_EXTRA)
    ANNOTATION_FILE.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(ANNOTATION_FILE, index=False, encoding="utf-8-sig")
    write_label_workbook(sample, LABEL_FILE, random_state)
    print(f"File untuk diisi: {LABEL_FILE}")
    print("Isi kolom human_sentiment dan human_sarcasm, lalu simpan.")


def write_evaluation() -> None:
    if not ANNOTATION_FILE.exists():
        raise FileNotFoundError(
            f"File anotasi tidak ditemukan: {ANNOTATION_FILE}. "
            "Jalankan `python analysis/evaluate_sentiment.py sample` terlebih dahulu."
        )
    report = evaluate_labeled_data(read_annotations())
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for task in ("sentiment", "sarcasm"):
        if task in report:
            metrics = report[task]
            print(
                f"{task}: {metrics['rows']} baris, accuracy={metrics['accuracy']:.3f}, "
                f"macro-F1={metrics['macro_f1']:.3f}"
            )
    if "sarcasm_flag_precision" in report:
        flagged = report["sarcasm_flag_precision"]
        print(f"presisi tanda sarkasme: {flagged['precision']:.3f} dari {flagged['rows']} baris")
    print(f"Laporan evaluasi tersimpan: {REPORT_FILE}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Siapkan anotasi manual dan evaluasi model Transformer."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    sample_parser = commands.add_parser(
        "sample", help="Buat sampel berstrata untuk diberi label secara manual."
    )
    sample_parser.add_argument("--size", type=int, default=300)
    sample_parser.add_argument("--seed", type=int, default=42)
    commands.add_parser("evaluate", help="Bandingkan prediksi model dengan label manual.")
    args = parser.parse_args()

    try:
        if args.command == "sample":
            prepare_sample(args.size, args.seed)
        else:
            write_evaluation()
    except (OSError, ValueError, pd.errors.ParserError) as error:
        print(f"Gagal menjalankan evaluasi: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
