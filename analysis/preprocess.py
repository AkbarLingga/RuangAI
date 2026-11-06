from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # supaya folder proyek terbaca saat file ini dijalankan langsung

from analysis.sentiment import (
    analyze_sentiment,
    clean_text,
    identify_topics,
    is_noise,
    normalized_polarity,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "processed"
OUTPUT_FILE = OUTPUT_DIR / "social_ai_processed.csv"

SOURCE_CONFIG = (
    {
        "filename": "data/raw/x/x_ai_refreshed_raw.csv",
        "platform": "X",
        "id_column": "comment_id",
        "text_column": "text",
        "date_column": "comment_published_at",
        "context_column": "video_title",
        "author_column": "author",
        "engagement_columns": ("like_count",),
    },
    {
        "filename": "data/raw/reddit/reddit_ai_refreshed_raw.csv",
        "platform": "Reddit",
        "id_column": "comment_id",
        "text_column": "text",
        "date_column": "comment_published_at",
        "context_column": "video_title",
        "author_column": "author",
        "engagement_columns": ("like_count",),
    },
    {
        "filename": "data/raw/archive/komentar_youtube_relevan_dampak_ai_pada_masyarakat.csv",
        "platform": "YouTube",
        "id_column": "comment_id",
        "text_column": "text",
        "date_column": "comment_published_at",
        "context_column": "video_title",
        "author_column": "author",
        "engagement_columns": ("like_count",),
    },
)


def _number(value: object) -> int:
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return 0


def _load_source(config: dict[str, object]) -> tuple[list[dict[str, object]], dict[str, int]]:
    source_path = ROOT / str(config["filename"])
    if not source_path.exists():
        return [], {"raw": 0, "noise": 0, "duplicate_id": 0, "kept": 0}

    frame = pd.read_csv(source_path, dtype=str, keep_default_na=False)
    required = (config["id_column"], config["text_column"])
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{source_path.name}: kolom wajib tidak ditemukan: {', '.join(missing)}")

    stats = {"raw": len(frame), "noise": 0, "duplicate_id": 0, "kept": 0}
    seen_ids: set[str] = set()
    records: list[dict[str, object]] = []

    for row in frame.to_dict(orient="records"):
        source_id = str(row.get(str(config["id_column"]), "")).strip()
        raw_text = str(row.get(str(config["text_column"]), ""))
        author = str(row.get(str(config["author_column"]), ""))
        text = clean_text(raw_text)

        if is_noise(text, author):
            stats["noise"] += 1
            continue
        if source_id and source_id in seen_ids:
            stats["duplicate_id"] += 1
            continue
        if source_id:
            seen_ids.add(source_id)

        engagement_columns = config["engagement_columns"]
        assert isinstance(engagement_columns, tuple)
        engagement = sum(_number(row.get(column, 0)) for column in engagement_columns)
        sentiment, score = analyze_sentiment(text)
        polarity = normalized_polarity(text, score)
        records.append(
            {
                "platform": config["platform"],
                "source_id": source_id,
                "date": str(row.get(str(config["date_column"]), "")).strip(),
                "source_context": str(row.get(str(config["context_column"]), "")).strip(),
                "engagement": engagement,
                "raw_text": raw_text,
                "clean_text": text,
                "sentiment": sentiment,
                "sentiment_score": score,
                "polarity": polarity,
                "topic": identify_topics(text),
            }
        )

    stats["kept"] = len(records)
    return records, stats


def build_dataset() -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    all_records: list[dict[str, object]] = []
    stats: dict[str, dict[str, int]] = {}
    found_sources = 0

    for config in SOURCE_CONFIG:
        if (ROOT / str(config["filename"])).exists():
            found_sources += 1
        records, source_stats = _load_source(config)
        all_records.extend(records)
        stats[str(config["platform"])] = source_stats

    if found_sources == 0:
        expected = ", ".join(str(item["filename"]) for item in SOURCE_CONFIG)
        raise FileNotFoundError(f"Tidak ada file sumber ditemukan di {ROOT}: {expected}")

    columns = [
        "platform", "source_id", "date", "source_context", "engagement",
        "raw_text", "clean_text", "sentiment", "sentiment_score", "polarity", "topic",
    ]
    dataset = pd.DataFrame(all_records, columns=columns)
    return dataset, stats


def main() -> int:
    try:
        dataset, stats = build_dataset()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        dataset.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    except (OSError, ValueError, pd.errors.ParserError) as error:
        print(f"Gagal memproses data: {error}", file=sys.stderr)
        return 1

    print(f"Dataset tersimpan: {OUTPUT_FILE}")
    print(f"Baris siap dianalisis: {len(dataset)}")
    for platform, counts in stats.items():
        if counts["raw"]:
            print(
                f"{platform}: mentah {counts['raw']}, terbuang {counts['noise']} "
                f"(noise) + {counts['duplicate_id']} (ID duplikat), "
                f"dipakai {counts['kept']}"
            )
    if dataset.empty:
        print("Peringatan: tidak ada data yang lolos pembersihan.", file=sys.stderr)
        return 1
    print("\nDistribusi sentimen:")
    print(dataset["sentiment"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
