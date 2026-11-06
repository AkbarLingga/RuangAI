"""
SCRAPER TAMBAHAN REDDIT (BATCH 2)
Mengumpulkan data komentar Reddit untuk menyeimbangkan dataset menjadi ~2.000 data per platform.
Skema keluaran sama persis dengan reddit_ai_raw.csv:
comment_id, subreddit, author, created_utc, date_utc, score, post_title, body, permalink
"""
from __future__ import annotations

import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent
RAW_BATCH1 = ROOT / "data" / "raw" / "reddit" / "reddit_ai_raw.csv"
if not RAW_BATCH1.exists():
    RAW_BATCH1 = ROOT / "reddit_ai_raw.csv"

OUT_BATCH2 = ROOT / "data" / "raw" / "reddit" / "reddit_ai_raw_batch2.csv"
OUT_BATCH2.parent.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://arctic-shift.photon-reddit.com/api/comments/search"

# Subreddits bervariasi: Core AI dan subreddits terdampak/kekhawatiran
SUBREDDITS = [
    # Core AI
    "ChatGPT",
    "singularity",
    "artificial",
    "OpenAI",
    "LocalLLaMA",
    "aiwars",
    "ControlProblem",
    "ArtificialInteligence",
    "ClaudeAI",
    # Isu Kekhawatiran Publik
    "technology",
    "Futurology",
    "Teachers",
    "graphic_design",
    "antiwork",
    "privacy",
    "cscareerquestions",
]

# Kata kunci relevansi AI & kekhawatiran untuk subreddit non-khusus AI
CONCERN_SUBS = {
    "technology", "Futurology", "Teachers", "graphic_design",
    "antiwork", "privacy", "cscareerquestions"
}

AI_KEYWORD_RE = re.compile(
    r"\b(ai|artificial intelligence|chatgpt|openai|claude|llm|llms|"
    r"deepfake|deepfakes|generative ai|copilot|automation|replace jobs|"
    r"layoff|layoffs|surveillance|copyright|plagiarism)\b",
    re.IGNORECASE,
)

START_DATE = "2024-01-01"
END_DATE = "2026-10-15"
BATCH_LIMIT = 100


def load_existing_ids() -> set[str]:
    seen: set[str] = set()
    for file_path in (RAW_BATCH1, OUT_BATCH2):
        if file_path.exists():
            try:
                df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
                if "comment_id" in df.columns:
                    seen.update(df["comment_id"].dropna().tolist())
            except Exception:
                pass
    return seen


def fetch_comments(params: dict[str, Any], max_retries: int = 5) -> list[dict[str, Any]]:
    for attempt in range(max_retries):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=35)
            if resp.status_code == 200:
                payload = resp.json()
                data = payload.get("data")
                if isinstance(data, list):
                    return data
            elif resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
            else:
                time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(3 * (attempt + 1))
    return []


def scrape_reddit(target_new_comments: int = 1400) -> int:
    seen_ids = load_existing_ids()
    print("=" * 65)
    print(" SCRAPER TAMBAHAN REDDIT (BATCH 2)")
    print(f" Target komentar baru: {target_new_comments}")
    print(f" Sudah ada sebelumnya: {len(seen_ids)} komentar (dilewati)")
    print(f" Simpan ke: {OUT_BATCH2}")
    print("=" * 65)

    quota_per_sub = max(60, target_new_comments // len(SUBREDDITS) + 15)
    total_added = 0
    pbar = tqdm(total=target_new_comments, desc="Komentar Reddit Dikumpulkan")

    # Ambil data dari berbagai titik waktu agar rentang waktu tersebar (2024 - 2026)
    time_slices = [
        ("2024-06-01", "2024-12-31"),
        ("2025-01-01", "2025-06-30"),
        ("2025-07-01", "2025-12-31"),
        ("2026-01-01", "2026-10-15"),
    ]

    for sub in SUBREDDITS:
        if total_added >= target_new_comments:
            break

        sub_added = 0
        is_concern = sub in CONCERN_SUBS

        for slice_start, slice_end in time_slices:
            if sub_added >= quota_per_sub or total_added >= target_new_comments:
                break

            params = {
                "subreddit": sub,
                "after": slice_start,
                "before": slice_end,
                "limit": BATCH_LIMIT,
                "sort": "asc",
            }
            if is_concern:
                params["body"] = "AI"

            comments = fetch_comments(params)
            if not comments:
                continue

            new_rows: list[dict[str, Any]] = []
            for c in comments:
                cid = str(c.get("id", "") or "")
                if not cid or cid in seen_ids:
                    continue

                body = str(c.get("body", "") or "")
                # Simpan mentah, tetapi buang hanya string kosong
                if not body.strip():
                    continue

                # Untuk sub concern, pastikan cocok kata kunci AI
                if is_concern and not AI_KEYWORD_RE.search(body):
                    continue

                seen_ids.add(cid)
                created_utc = int(c.get("created_utc", 0) or 0)
                try:
                    date_utc = datetime.fromtimestamp(created_utc, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    date_utc = ""

                permalink = f"https://reddit.com{c.get('permalink', '')}" if c.get("permalink") else ""
                post_title = str(c.get("link_title", "") or "")
                author = str(c.get("author", "") or "")
                score = c.get("score", 0) or 0

                row = {
                    "comment_id": cid,
                    "subreddit": c.get("subreddit", sub),
                    "author": author,
                    "created_utc": created_utc,
                    "date_utc": date_utc,
                    "score": score,
                    "post_title": post_title,
                    "body": body,
                    "permalink": permalink,
                }
                new_rows.append(row)
                sub_added += 1
                total_added += 1
                pbar.update(1)

                if sub_added >= quota_per_sub or total_added >= target_new_comments:
                    break

            if new_rows:
                df_batch = pd.DataFrame(new_rows)
                header = not OUT_BATCH2.exists()
                df_batch.to_csv(OUT_BATCH2, mode="a", index=False, header=header, encoding="utf-8")

            time.sleep(0.8)  # Rate limiting sopan

    pbar.close()
    print("\n" + "=" * 65)
    print(f" Scraping Reddit Batch 2 Selesai!")
    print(f" Total komentar baru tersimpan: {total_added}")
    if OUT_BATCH2.exists():
        df_out = pd.read_csv(OUT_BATCH2, dtype=str)
        print(f" File: {OUT_BATCH2} ({len(df_out)} baris)")
    print("=" * 65)
    return total_added


if __name__ == "__main__":
    scrape_reddit(target_new_comments=1400)
