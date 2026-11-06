"""
SCRAPER TAMBAHAN X / TWITTER (BATCH 2) - PARQUET ENGINE
Mengumpulkan data tweet X dari arsip publik akademik terverifikasi (Hugging Face deberain/ChatGPT-Tweets).
Skema keluaran sama persis dengan x_ai_raw.csv:
tweet_id, platform, user, created_at, likes, retweets, query, raw_text, url
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from langdetect import DetectorFactory, detect
from tqdm import tqdm

DetectorFactory.seed = 0

ROOT = Path(__file__).resolve().parent
RAW_BATCH1 = ROOT / "data" / "raw" / "x" / "x_ai_raw.csv"
if not RAW_BATCH1.exists():
    RAW_BATCH1 = ROOT / "x_ai_raw.csv"

OUT_BATCH2 = ROOT / "data" / "raw" / "x" / "x_ai_raw_batch2.csv"
OUT_BATCH2.parent.mkdir(parents=True, exist_ok=True)

PARQUET_URL = (
    "https://huggingface.co/datasets/deberain/ChatGPT-Tweets/resolve/"
    "refs%2Fconvert%2Fparquet/default/train/0000.parquet"
)

TOPIC_PATTERNS = {
    "Pekerjaan & Karir": re.compile(
        r"\b(job|jobs|layoff|layoffs|unemploy|unemployment|replace|replacing|workforce|career)\b",
        re.I,
    ),
    "Privasi & Keamanan": re.compile(
        r"\b(privacy|surveillance|harvesting|leak|data leak|security|personal data)\b",
        re.I,
    ),
    "Deepfake & Penipuan": re.compile(
        r"\b(deepfake|deepfakes|scam|scams|fraud|fake news|disinformation|misinformation)\b",
        re.I,
    ),
    "Pendidikan & Integritas": re.compile(
        r"\b(cheat|cheating|plagiar|plagiarism|school|students|teacher|academic integrity)\b",
        re.I,
    ),
    "Hak Cipta & Seni": re.compile(
        r"\b(copyright|artist|artists|ai art|stolen|intellectual property|slop)\b",
        re.I,
    ),
    "Risiko Etika & Bahaya": re.compile(
        r"\b(danger|threat|existential|risk|destroy|ethics|ethical|harm)\b",
        re.I,
    ),
}

SPAM_PROMO_RE = re.compile(
    r"\b(book now|register now|webinar|summit|conference|discount|promo code|"
    r"buy now|giveaway|airdrop|sponsored|affiliate|dm me for|click here|crypto alert)\b",
    re.I,
)


def load_existing_ids() -> set[str]:
    seen: set[str] = set()
    if RAW_BATCH1.exists():
        try:
            df = pd.read_csv(RAW_BATCH1, dtype=str, keep_default_na=False)
            if "tweet_id" in df.columns:
                seen.update(df["tweet_id"].dropna().tolist())
        except Exception:
            pass
    return seen


def is_valid_tweet(text: str) -> bool:
    if not text or len(text) < 35 or len(text.split()) < 6:
        return False
    if SPAM_PROMO_RE.search(text):
        return False
    clean_snippet = re.sub(r"https?://\S+|t\.co/\S+", "", text).strip()
    if len(clean_snippet) < 20 or not re.search(r"[a-zA-Z]", clean_snippet):
        return False
    try:
        return detect(clean_snippet) == "en"
    except Exception:
        return False


def run_extraction(target_new_tweets: int = 2100) -> int:
    seen_ids = load_existing_ids()
    print("=" * 65)
    print(" PENGAMBILAN DATA X (BATCH 2) - VIA ARSIP PARQUET")
    print(f" Target tweet baru: {target_new_tweets}")
    print(f" Sudah ada di batch 1: {len(seen_ids)} tweet (dilewati)")
    print(" Membaca berkas Parquet dari Hugging Face...")
    print("=" * 65)

    df_full = pd.read_parquet(
        PARQUET_URL,
        columns=["Date", "Tweet", "Url", "User", "Likes"],
        engine="pyarrow",
    )
    print(f" Total tweet dalam arsip: {len(df_full):,} baris")

    # Filter dasar
    df_full["text"] = df_full["Tweet"].fillna("").astype(str).str.strip()
    df_full = df_full[df_full["text"].str.len().ge(35) & df_full["text"].str.split().str.len().ge(6)]
    df_full = df_full[~df_full["text"].str.contains(SPAM_PROMO_RE)]

    new_records: list[dict[str, Any]] = []
    pbar = tqdm(total=target_new_tweets, desc="Tweet X Disaring & Divalidasi")

    for row in df_full.itertuples(index=False):
        tweet_text = row.text
        tweet_url = str(row.Url or "").strip()

        match_id = re.search(r"/status/(\d+)", tweet_url)
        tid = match_id.group(1) if match_id else None
        if not tid or tid in seen_ids:
            continue

        matched_topic = None
        for topic_name, pattern in TOPIC_PATTERNS.items():
            if pattern.search(tweet_text):
                matched_topic = topic_name
                break

        if not matched_topic:
            continue

        if not is_valid_tweet(tweet_text):
            continue

        seen_ids.add(tid)
        user = str(row.User or "[user]")
        created_at = str(row.Date or "")
        likes = row.Likes if pd.notna(row.Likes) else 0

        new_records.append(
            {
                "tweet_id": tid,
                "platform": "X",
                "user": user,
                "created_at": created_at,
                "likes": likes,
                "retweets": 0,
                "query": f"AI Concerns Archive - {matched_topic}",
                "raw_text": tweet_text,
                "url": tweet_url,
            }
        )
        pbar.update(1)

        if len(new_records) >= target_new_tweets:
            break

    pbar.close()

    if new_records:
        df_out = pd.DataFrame(new_records)
        df_out.to_csv(OUT_BATCH2, index=False, encoding="utf-8")
        print("\n" + "=" * 65)
        print(f" Berhasil menyimpan {len(df_out)} tweet baru ke {OUT_BATCH2}")
        print(" Distribusi topik kekhawatiran:")
        print(df_out["query"].value_counts().to_string())
        print("=" * 65)
        return len(df_out)

    return 0


if __name__ == "__main__":
    run_extraction(target_new_tweets=2100)
