"""
PENGGABUNGAN, PEMBERSIHAN, DAN PENYEIMBANGAN DATASET 3 PLATFORM (YOUTUBE, REDDIT, X)
Proyek: Analisis Sentimen dan Identifikasi Topik Kekhawatiran Masyarakat terhadap Perkembangan AI
Fase E: Multi-platform Harmonization, Stratified Sampling & Composition Report
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from langdetect import DetectorFactory, detect
from tqdm import tqdm

import config
from sentiment import (
    analyze_sentiment,
    clean_text,
    identify_topics,
    is_noise,
    normalized_polarity,
)

DetectorFactory.seed = config.RANDOM_STATE

ROOT = config.ROOT_DIR
RAW_DIR = config.RAW_DIR
INTERIM_DIR = config.INTERIM_DIR
PROCESSED_DIR = config.PROCESSED_DIR
REPORTS_DIR = config.REPORTS_DIR

INTERIM_FILE = INTERIM_DIR / "combined_all.csv"
PROCESSED_FILE = PROCESSED_DIR / "social_ai_processed.csv"
EXCEL_FILE = PROCESSED_DIR / "social_ai_processed.xlsx"
REPORT_MD = REPORTS_DIR / "data_composition.md"
REPORT_CSV = REPORTS_DIR / "data_composition.csv"


def _clean_str(val: Any) -> str:
    if val is None or pd.isna(val):
        return ""
    return str(val).strip()


def _parse_utc_date(val: Any) -> str:
    if not val or pd.isna(val):
        return ""
    s = str(val).strip()
    try:
        dt = pd.to_datetime(s, utc=True)
        if pd.notna(dt):
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return s[:19]


def _safe_detect_en(text: str) -> bool:
    if not text or len(text.strip()) < 15:
        return False
    try:
        return detect(text) == "en"
    except Exception:
        return False


def load_youtube_raw() -> list[dict[str, Any]]:
    yt_dir = RAW_DIR / "youtube"
    yt_files = [
        yt_dir / "komentar_youtube_relevan_ai_impact_and_effects.csv",
        yt_dir / "komentar_youtube_relevan_ai_impact_and_effect.csv",
        yt_dir / "komentar_youtube_relevan_ai_impact_and_ai_effects.csv",
    ]
    records: list[dict[str, Any]] = []
    for f in yt_files:
        if not f.exists():
            continue
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        for r in df.to_dict(orient="records"):
            cid = _clean_str(r.get("comment_id"))
            text = _clean_str(r.get("text"))
            if not cid or not text:
                continue
            parent_id = _clean_str(r.get("parent_comment_id"))
            likes = int(float(r.get("like_count", 0) or 0))
            records.append({
                "platform": "YouTube",
                "source_id": cid,
                "parent_id": parent_id,
                "is_reply": bool(parent_id),
                "date": _parse_utc_date(r.get("comment_published_at")),
                "source_context": _clean_str(r.get("video_title")),
                "source_group": _clean_str(r.get("video_id")) or _clean_str(r.get("video_title")),
                "engagement": likes,
                "raw_text": text,
                "source_file": f.name,
            })
    return records


def load_reddit_raw() -> list[dict[str, Any]]:
    reddit_dir = RAW_DIR / "reddit"
    reddit_files = [
        reddit_dir / "reddit_ai_raw.csv",
        reddit_dir / "reddit_ai_raw_batch2.csv",
    ]
    records: list[dict[str, Any]] = []
    for f in reddit_files:
        if not f.exists():
            continue
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        for r in df.to_dict(orient="records"):
            cid = _clean_str(r.get("comment_id"))
            text = _clean_str(r.get("body"))
            if not cid or not text:
                continue
            score = int(float(r.get("score", 0) or 0))
            sub = _clean_str(r.get("subreddit"))
            records.append({
                "platform": "Reddit",
                "source_id": cid,
                "parent_id": "",
                "is_reply": True,  # Komentar reddit di post
                "date": _parse_utc_date(r.get("date_utc")),
                "source_context": f"r/{sub}",
                "source_group": sub,
                "engagement": score,
                "raw_text": text,
                "source_file": f.name,
            })
    return records


def load_x_raw() -> list[dict[str, Any]]:
    x_dir = RAW_DIR / "x"
    x_files = [
        x_dir / "x_ai_raw.csv",
        x_dir / "x_ai_raw_batch2.csv",
    ]
    records: list[dict[str, Any]] = []
    for f in x_files:
        if not f.exists():
            continue
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
        for r in df.to_dict(orient="records"):
            tid = _clean_str(r.get("tweet_id"))
            text = _clean_str(r.get("raw_text"))
            if not tid or not text:
                continue
            likes = int(float(r.get("likes", 0) or 0))
            query = _clean_str(r.get("query"))
            records.append({
                "platform": "X",
                "source_id": tid,
                "parent_id": "",
                "is_reply": False,
                "date": _parse_utc_date(r.get("created_at")),
                "source_context": query,
                "source_group": query.split(" - ")[-1] if " - " in query else query,
                "engagement": likes,
                "raw_text": text,
                "source_file": f.name,
            })
    return records


def run_merge_and_balance():
    print("=" * 65)
    print(" FASE E: HARMONISASI & PENYEIMBANGAN DATA MULTI-PLATFORM")
    print(f" Target per platform: {config.TARGET_PER_PLATFORM}")
    print(f" Mode bahasa: {config.LANG_MODE}")
    print("=" * 65)

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Muat seluruh data mentah
    yt_raw = load_youtube_raw()
    reddit_raw = load_reddit_raw()
    x_raw = load_x_raw()

    raw_counts = {
        "YouTube": len(yt_raw),
        "Reddit": len(reddit_raw),
        "X": len(x_raw),
    }
    print(f"Data mentah terbaca:")
    for p, c in raw_counts.items():
        print(f" - {p}: {c:,} baris")

    all_raw = yt_raw + reddit_raw + x_raw
    df_all_raw = pd.DataFrame(all_raw)
    df_all_raw.to_csv(INTERIM_FILE, index=False, encoding="utf-8")
    print(f"\n[INTERIM] Disimpan ke {INTERIM_FILE} ({len(df_all_raw)} total baris mentah)")

    # 2. Pembersihan & Filter Noise / Bahasa
    print("\nMelakukan pembersihan teks, filter noise & validasi bahasa Inggris...")
    cleaned_records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()

    filter_stats = {
        "YouTube": {"noise": 0, "dup_id": 0, "dup_text": 0, "non_en": 0, "valid": 0},
        "Reddit": {"noise": 0, "dup_id": 0, "dup_text": 0, "non_en": 0, "valid": 0},
        "X": {"noise": 0, "dup_id": 0, "dup_text": 0, "non_en": 0, "valid": 0},
    }

    for item in tqdm(all_raw, desc="Preprocessing"):
        p = item["platform"]
        sid = item["source_id"]
        raw_text = item["raw_text"]

        # Deduplikasi ID
        if sid in seen_ids:
            filter_stats[p]["dup_id"] += 1
            continue
        seen_ids.add(sid)

        # Cleaning
        c_text = clean_text(raw_text)

        # Filter Noise
        if is_noise(c_text):
            filter_stats[p]["noise"] += 1
            continue

        # Normalisasi teks untuk dedup teks yang identik
        norm_text = re.sub(r"\s+", " ", c_text.lower()).strip()
        if norm_text in seen_texts:
            filter_stats[p]["dup_text"] += 1
            continue
        seen_texts.add(norm_text)

        # Filter bahasa bila en_only
        if config.LANG_MODE == "en_only" and not _safe_detect_en(c_text):
            filter_stats[p]["non_en"] += 1
            continue

        filter_stats[p]["valid"] += 1

        # Tambahkan label leksikon baseline
        sentiment, score = analyze_sentiment(c_text)
        polarity = normalized_polarity(c_text, score)
        topic = identify_topics(c_text)

        cleaned_records.append({
            "platform": p,
            "source_id": sid,
            "parent_id": item["parent_id"],
            "is_reply": item["is_reply"],
            "date": item["date"],
            "source_context": item["source_context"],
            "source_group": item["source_group"],
            "engagement": item["engagement"],
            "raw_text": raw_text,
            "clean_text": c_text,
            "sentiment": sentiment,
            "sentiment_score": score,
            "polarity": polarity,
            "topic": topic,
            "source_file": item["source_file"],
        })

    df_clean = pd.DataFrame(cleaned_records)
    print("\nHasil seleksi valid per platform (sebelum balancing):")
    print(df_clean["platform"].value_counts().to_string())

    # 3. Sampling Berstrata & Anti-Dominasi (Target tepat 2.000 per platform)
    target = config.TARGET_PER_PLATFORM
    sampled_dfs: list[pd.DataFrame] = []

    print(f"\nMenjalankan sampling berstrata anti-dominasi (Target: {target} per platform)...")
    for platform in ("YouTube", "Reddit", "X"):
        df_p = df_clean[df_clean["platform"] == platform].copy()
        if len(df_p) < target:
            raise RuntimeError(
                f"Data valid untuk {platform} ({len(df_p)}) kurang dari target {target}!"
            )

        # Batasi dominasi sumber/video
        if platform == "YouTube":
            max_per_group = int(target * config.MAX_SHARE_PER_VIDEO)  # 8% = 160 per video
        elif platform == "Reddit":
            max_per_group = int(target * config.MAX_SHARE_PER_SOURCE)  # 10% = 200 per sub
        else:
            max_per_group = int(target * 0.30)  # 30% max per topik X

        # Cap group size
        capped_list = []
        for group_val, grp in df_p.groupby("source_group"):
            if len(grp) > max_per_group:
                grp = grp.sample(n=max_per_group, random_state=config.RANDOM_STATE)
            capped_list.append(grp)
        df_p_capped = pd.concat(capped_list, ignore_index=True)

        if len(df_p_capped) >= target:
            df_sampled = df_p_capped.sample(n=target, random_state=config.RANDOM_STATE)
        else:
            # Fallback ambil dari sisa jika capped terlalu agresif
            remaining = df_p[~df_p["source_id"].isin(df_p_capped["source_id"])]
            needed = target - len(df_p_capped)
            df_sampled = pd.concat([
                df_p_capped,
                remaining.sample(n=needed, random_state=config.RANDOM_STATE)
            ], ignore_index=True)

        sampled_dfs.append(df_sampled)
        print(f" - {platform}: Berhasil disampel tepat {len(df_sampled):,} data.")

    df_final = pd.concat(sampled_dfs, ignore_index=True)

    # Acak urutan secara reproduktif
    df_final = df_final.sample(frac=1.0, random_state=config.RANDOM_STATE).reset_index(drop=True)

    # 4. Verifikasi Kualitas & Keseimbangan Otomatis
    total_final = len(df_final)
    p_counts = df_final["platform"].value_counts()
    for p, count in p_counts.items():
        share = count / total_final
        if not (0.31 <= share <= 0.35):
            raise AssertionError(f"Proporsi {p} tidak seimbang (33% +/- 2%): {share*100:.1f}%")

    if df_final["source_id"].duplicated().any():
        raise AssertionError("Terdapat source_id duplikat di dataset final!")

    if df_final["clean_text"].str.strip().eq("").any():
        raise AssertionError("Terdapat clean_text kosong di dataset final!")

    # 5. Simpan Dataset Final CSV & Excel
    # Kolom standar analisis
    output_columns = [
        "platform", "source_id", "date", "source_context", "engagement",
        "raw_text", "clean_text", "sentiment", "sentiment_score", "polarity", "topic"
    ]
    df_output = df_final[output_columns].copy()
    df_output.to_csv(PROCESSED_FILE, index=False, encoding="utf-8-sig")
    print(f"\n[SUKSES] Dataset seimbang tersimpan: {PROCESSED_FILE} ({len(df_output)} baris)")

    # Buat file Excel rapi dengan header di-freeze
    try:
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            df_output.head(2000).to_excel(writer, sheet_name="Sampel_Data_Seimbang", index=False)
            ws = writer.sheets["Sampel_Data_Seimbang"]
            ws.freeze_panes = "A2"
            # Lebar kolom otomatis
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col[:50])
                col_letter = col[0].column_letter
                ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)
        print(f"[EXCEL] File Excel rapi untuk dosen tersimpan: {EXCEL_FILE}")
    except Exception as e:
        print(f"[WARN] Gagal membuat file Excel: {e}")

    # 6. Buat Laporan Komposisi Data (reports/data_composition.md & .csv)
    df_final["month"] = pd.to_datetime(df_final["date"], errors="coerce", utc=True).dt.strftime("%Y-%m")
    
    comp_records = []
    for p in ("YouTube", "Reddit", "X"):
        sub = df_final[df_final["platform"] == p]
        n_parent = (df_final[df_final["platform"] == p]["parent_id"] == "").sum()
        n_reply = len(sub) - n_parent
        comp_records.append({
            "Platform": p,
            "Mentah": raw_counts[p],
            "Valid_Setelah_Clean": filter_stats[p]["valid"],
            "Dataset_Final": len(sub),
            "Persentase": f"{len(sub)/total_final*100:.1f}%",
            "Top_Level_Komentar": f"{n_parent} ({n_parent/len(sub)*100:.1f}%)" if p == "YouTube" else "N/A",
            "Balasan": f"{n_reply} ({n_reply/len(sub)*100:.1f}%)" if p == "YouTube" else "N/A",
            "Rentang_Tanggal": f"{sub['date'].min()[:10]} s/d {sub['date'].max()[:10]}",
        })

    df_comp = pd.DataFrame(comp_records)
    df_comp.to_csv(REPORT_CSV, index=False)

    md_content = f"""# Laporan Komposisi dan Keseimbangan Data Multi-Platform
**Proyek Data Mining**: Analisis Sentimen dan Identifikasi Topik Kekhawatiran Masyarakat terhadap Perkembangan AI di Media Sosial  
**Tanggal Eksekusi**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC  
**Konfigurasi**: `LANG_MODE = {config.LANG_MODE}`, `TARGET_PER_PLATFORM = {config.TARGET_PER_PLATFORM}`

---

## 1. Ringkasan Keseimbangan 3 Platform (Target 33.3% per Platform)

| Platform | Data Mentah | Lolos Seleksi | Dataset Final | Proporsi Final | Rentang Waktu |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **YouTube** | {raw_counts['YouTube']:,} | {filter_stats['YouTube']['valid']:,} | **2,000** | **33.3%** | {df_final[df_final['platform']=='YouTube']['date'].min()[:10]} s/d {df_final[df_final['platform']=='YouTube']['date'].max()[:10]} |
| **Reddit** | {raw_counts['Reddit']:,} | {filter_stats['Reddit']['valid']:,} | **2,000** | **33.3%** | {df_final[df_final['platform']=='Reddit']['date'].min()[:10]} s/d {df_final[df_final['platform']=='Reddit']['date'].max()[:10]} |
| **X (Twitter)** | {raw_counts['X']:,} | {filter_stats['X']['valid']:,} | **2,000** | **33.3%** | {df_final[df_final['platform']=='X']['date'].min()[:10]} s/d {df_final[df_final['platform']=='X']['date'].max()[:10]} |
| **TOTAL** | **{sum(raw_counts.values()):,}** | **{sum(s['valid'] for s in filter_stats.values()):,}** | **{total_final:,}** | **100.0%** | **Seimbang Sempurna** |

---

## 2. Rincian Pembersihan & Filter (Data Pipeline Hygiene)

| Platform | Terbuang: Noise/Pendek | Terbuang: Duplikat ID | Terbuang: Duplikat Teks | Terbuang: Non-Inggris |
| :--- | :---: | :---: | :---: | :---: |
| **YouTube** | {filter_stats['YouTube']['noise']} | {filter_stats['YouTube']['dup_id']} | {filter_stats['YouTube']['dup_text']} | {filter_stats['YouTube']['non_en']} |
| **Reddit** | {filter_stats['Reddit']['noise']} | {filter_stats['Reddit']['dup_id']} | {filter_stats['Reddit']['dup_text']} | {filter_stats['Reddit']['non_en']} |
| **X** | {filter_stats['X']['noise']} | {filter_stats['X']['dup_id']} | {filter_stats['X']['dup_text']} | {filter_stats['X']['non_en']} |

---

## 3. Distribusi Sentimen Baseline (Leksikon)

{df_final.groupby(['platform', 'sentiment']).size().unstack(fill_value=0).to_markdown()}

---

## 4. Distribusi Topik Terbanyak per Platform

{df_final.groupby('platform')['topic'].value_counts().groupby(level=0).head(4).to_markdown()}
"""
    REPORT_MD.write_text(md_content, encoding="utf-8")
    print(f"[LAPORAN] Laporan komposisi tersimpan di {REPORT_MD} dan {REPORT_CSV}")
    print("=" * 65)


if __name__ == "__main__":
    run_merge_and_balance()
