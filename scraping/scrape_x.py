"""
SCRAPER TWEET X (TWITTER) - ISU PERKEMBANGAN & KEKHAWATIRAN AI (BAHASA INGGRIS)

Fitur:
1. Mode 'live'    : Scraping tweet terbaru langsung dari X menggunakan twikit
                    (Dapat menggunakan cookies auth_token & ct0 ATAU login akun dummy).
2. Mode 'archive' : Mengambil tweet asli dari arsip publik akademik X (Hugging Face
                    deberain/ChatGPT-Tweets: 300.000+ tweet publik asli bertopik AI).
                    Sangat cocok jika belum punya akun dummy X atau kuota dibatasi X.
3. Preprocessing  : Pembersihan URL, emoji, mention berlebih, bot, dan validasi bahasa Inggris (langdetect).
4. Output         : 'x_ai_raw.csv' (data mentah) dan 'x_ai_clean.csv' (data bersih siap olah).
"""

import os
from pathlib import Path
import re
import sys
import time
import json
import asyncio
import argparse
from datetime import datetime, timezone
import pandas as pd
import requests
from langdetect import DetectorFactory, detect
from tqdm import tqdm

DetectorFactory.seed = 0

# ==========================================
# FILE OUTPUT
# ==========================================
ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = str(ROOT / "data" / "raw" / "x" / "x_ai_raw.csv")
CLEAN_CSV = str(ROOT / "data" / "cleaned" / "x_ai_clean.csv")
COOKIE_FILE = "x_cookies.json"

# ==========================================
# KATA KUNCI & TOPIK KEKHAWATIRAN AI
# ==========================================
SEARCH_QUERIES = [
    # Topik 1: Pekerjaan & Disrupsi Tenaga Kerja
    '"AI" ("replace jobs" OR "layoffs" OR "unemployment" OR "job market") lang:en',
    # Topik 2: Privasi & Pengawasan Data
    '"AI" ("privacy" OR "data harvesting" OR "surveillance" OR "steal data") lang:en',
    # Topik 3: Deepfake, Penipuan & Kejahatan Siber
    '"AI" ("deepfake" OR "scam" OR "disinformation" OR "impersonation") lang:en',
    # Topik 4: Pendidikan & Kecurangan Akademik
    '("ChatGPT" OR "AI") ("cheating" OR "plagiarism" OR "school" OR "students") lang:en',
    # Topik 5: Hak Cipta, Seniman & AI Slop
    '("AI art" OR "generative AI") ("copyright" OR "stolen" OR "artists" OR "slop") lang:en',
    # Topik 6: Keamanan Eksistensial & Regulasi
    '"AI" ("existential risk" OR "danger" OR "regulation" OR "threat to humanity") lang:en',
]

# Regex filter kekhawatiran untuk mode archive
AI_CONCERN_REGEX = re.compile(
    r'\b(job|jobs|layoff|layoffs|unemploy|unemployment|replace|replacing|career|workforce|'
    r'privacy|surveillance|harvesting|leak|data|security|'
    r'deepfake|deepfakes|scam|scams|fraud|fake|impersonat|misinformation|disinformation|'
    r'cheat|cheating|plagiar|plagiarism|school|schools|student|students|teacher|teachers|education|'
    r'copyright|artist|artists|art|stolen|intellectual property|slop|'
    r'danger|threat|risk|existential|destroy|ethics|ethical|harm)\b',
    re.IGNORECASE
)


# Regex filter untuk menyingkirkan spam promosi, event, giveaway, dan iklan
SPAM_PROMO_REGEX = re.compile(
    r'\b(book now|register now|webinar|summit|conference|discount|promo|promocode|buy now|on sale|'
    r'giveaway|airdrop|sponsored|affiliate|dm me for|click here|crypto alert|hiring now|apply here)\b',
    re.IGNORECASE
)

# ==========================================
# FUNGSI PREPROCESSING & VALIDASI
# ==========================================
def clean_tweet_text(text: str) -> str:
    """Membersihkan tweet dari URL, emoji, mention, hashtag symbol, dan whitespace."""
    if not isinstance(text, str):
        return ""
    # Hapus tautan URL (http/https/t.co)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r't\.co/\S+', '', text)
    # Hapus emoji dan simbol grafis/panah tambahan
    emoji_pattern = re.compile(
        r'[\U00010000-\U0010ffff\uD800-\uDBFF\uDC00-\uDFFF\u2600-\u26FF\u2700-\u27BF\u2B00-\u2BFF\u200D\uFE0F]+'
    )
    text = emoji_pattern.sub('', text)
    # Hapus mention @username
    text = re.sub(r'@\w+', '', text)
    # Ubah #hashtag menjadi kata biasa (#ChatGPT -> ChatGPT) agar bisa dibaca model sentimen/topik
    text = re.sub(r'#(\w+)', r'\1', text)
    # Hapus karakter HTML entities seperti &amp;, &lt;, dll.
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    # Rapikan spasi dan baris baru
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_english_and_valid(text: str) -> bool:
    """Memvalidasi teks berbahasa Inggris, tidak terlalu pendek, bukan spam iklan, dan berbobot."""
    if not text:
        return False
    # Singkirkan iklan dan spam promosi
    if SPAM_PROMO_REGEX.search(text):
        return False
    # Minimal 35 karakter dan minimal 6 kata agar bermakna untuk sentimen & topik
    if len(text) < 35 or len(text.split()) < 6:
        return False
    # Cek ada karakter alfabet
    if not re.search(r'[a-zA-Z]', text):
        return False
    try:
        lang = detect(text)
        return lang == "en"
    except Exception:
        return False


def load_existing_tweet_ids():
    """Membaca tweet_id yang sudah pernah tersimpan agar tidak duplikat."""
    seen = set()
    if os.path.exists(RAW_CSV):
        try:
            df = pd.read_csv(RAW_CSV)
            if "tweet_id" in df.columns:
                seen = set(df["tweet_id"].dropna().astype(str).tolist())
        except Exception:
            pass
    return seen


# ==========================================
# MODE 1: LIVE SCRAPING DENGAN TWIKIT
# ==========================================
async def scrape_live_twikit(target_per_query=100):
    try:
        from twikit import Client
    except ImportError:
        print("[ERROR] Pustaka 'twikit' belum terinstall. Jalankan: pip install twikit")
        return

    client = Client('en-US')
    seen_ids = load_existing_tweet_ids()

    # Cek ketersediaan cookies
    if os.path.exists(COOKIE_FILE):
        print(f"[AUTH] Memuat cookie dari '{COOKIE_FILE}'...")
        client.load_cookies(COOKIE_FILE)
    else:
        print("\n" + "=" * 60)
        print(" OTIENTIKASI X (TWITTER)")
        print("=" * 60)
        print("Untuk scraping langsung dari X tanpa bayar API resmi ($100/bln),")
        print("Anda dapat memilih salah satu cara:")
        print("1. Masukkan cookies ('auth_token' dan 'ct0') dari browser [PALING AMAN]")
        print("2. Login dengan akun X (gunakan akun dummy/cadangan)")
        print("=" * 60)
        
        auth_choice = input("Pilih metode autentikasi (1 = Cookie, 2 = Login Akun): ").strip()

        if auth_choice == "1":
            auth_token = input("Masukkan auth_token cookie: ").strip()
            ct0 = input("Masukkan ct0 cookie: ").strip()
            client.set_cookies({"auth_token": auth_token, "ct0": ct0})
            client.save_cookies(COOKIE_FILE)
            print(f"[INFO] Cookie tersimpan di '{COOKIE_FILE}'.")
        else:
            username = input("Username X: ").strip()
            email = input("Email X: ").strip()
            password = input("Password X: ").strip()
            print("[AUTH] Mencoba login...")
            await client.login(auth_info_1=username, auth_info_2=email, password=password)
            client.save_cookies(COOKIE_FILE)
            print(f"[AUTH] Login berhasil! Cookie tersimpan di '{COOKIE_FILE}'.")

    print(f"\n[START] Memulai pencarian live di X (Target: {target_per_query} tweet per query)...")
    total_added = 0

    for query in SEARCH_QUERIES:
        print(f"\n[QUERY] Mencari: {query[:60]}...")
        pbar = tqdm(total=target_per_query, desc="Tweets")
        got_for_query = 0

        try:
            tweets = await client.search_tweet(query, product='Top', count=20)
        except Exception as e:
            print(f"[WARN] Gagal mengambil query ({e}). Lanjut ke query berikutnya.")
            pbar.close()
            continue

        while tweets and got_for_query < target_per_query:
            raw_batch = []
            clean_batch = []

            for t in tweets:
                tid = str(t.id)
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)

                text_raw = t.text or ""
                created_at = str(t.created_at) if hasattr(t, "created_at") else ""
                likes = getattr(t, "favorite_count", 0) or 0
                retweets = getattr(t, "retweet_count", 0) or 0
                user = t.user.screen_name if hasattr(t, "user") and t.user else "[user]"
                tweet_url = f"https://x.com/{user}/status/{tid}"

                raw_record = {
                    "tweet_id": tid,
                    "platform": "X",
                    "user": user,
                    "created_at": created_at,
                    "likes": likes,
                    "retweets": retweets,
                    "query": query,
                    "raw_text": text_raw,
                    "url": tweet_url,
                }
                raw_batch.append(raw_record)

                cleaned = clean_tweet_text(text_raw)
                if is_english_and_valid(cleaned):
                    clean_record = {
                        "tweet_id": tid,
                        "platform": "X",
                        "created_at": created_at,
                        "likes": likes,
                        "retweets": retweets,
                        "query_topic": query.split('"')[1] if '"' in query else "AI",
                        "clean_text": cleaned,
                        "url": tweet_url,
                    }
                    clean_batch.append(clean_record)

            if raw_batch:
                df_raw = pd.DataFrame(raw_batch)
                df_raw.to_csv(RAW_CSV, mode="a", index=False, header=not os.path.exists(RAW_CSV), encoding="utf-8")

            if clean_batch:
                df_clean = pd.DataFrame(clean_batch)
                df_clean.to_csv(CLEAN_CSV, mode="a", index=False, header=not os.path.exists(CLEAN_CSV), encoding="utf-8")
                added = len(clean_batch)
                got_for_query += added
                total_added += added
                pbar.update(added)

            # Pagination
            try:
                time.sleep(2.0)
                tweets = await tweets.next()
            except Exception:
                break

        pbar.close()

    print(f"\n[SELESAI] Berhasil mengambil {total_added} tweet live baru.")


# ==========================================
# MODE 2: ARSIP PUBLIK AKADEMIK X (HUGGING FACE)
# ==========================================
def scrape_archive_hf(target_count=1500):
    """
    Mengambil tweet publik asli bertopik AI & ChatGPT dari repositori riset
    'deberain/ChatGPT-Tweets' (300.000+ tweet publik asli X).
    Tanpa butuh login, tanpa risiko akun terblokir, 100% data riil X.
    """
    seen_ids = load_existing_tweet_ids()
    print("=" * 65)
    print(" PENGAMBILAN DATA TWEET X DARI ARSIP RISET AKADEMIK")
    print(f" Target: {target_count} tweet bersih berbahasa Inggris bertopik kekhawatiran AI")
    print(f" Output: '{RAW_CSV}' & '{CLEAN_CSV}'")
    print("=" * 65)

    base_url = "https://datasets-server.huggingface.co/rows"
    dataset_name = "deberain/ChatGPT-Tweets"

    offset = 0
    batch_size = 100
    added_count = 0

    pbar = tqdm(total=target_count, desc="Tweets Berhasil Dikumpulkan")

    while added_count < target_count:
        params = {
            "dataset": dataset_name,
            "config": "default",
            "split": "train",
            "offset": offset,
            "limit": batch_size,
        }

        data_rows = None
        for attempt in range(3):
            try:
                resp = requests.get(base_url, params=params, timeout=20)
                if resp.status_code == 200:
                    data_rows = resp.json().get("rows", [])
                    break
                elif resp.status_code == 429:
                    time.sleep(5)
            except Exception:
                time.sleep(2)

        if not data_rows:
            print("\n[INFO] Data arsip habis atau limit tercapai.")
            break

        offset += len(data_rows)
        raw_batch = []
        clean_batch = []

        for item in data_rows:
            row = item.get("row", {})
            tweet_text = str(row.get("Tweet", ""))
            tweet_url = str(row.get("Url", ""))

            # Ekstrak tweet_id dari URL
            match_id = re.search(r'/status/(\d+)', tweet_url)
            tid = match_id.group(1) if match_id else f"x_{offset}_{len(raw_batch)}"

            if tid in seen_ids:
                continue
            seen_ids.add(tid)

            # Cek apakah relevan dengan isu/kekhawatiran masyarakat terhadap AI
            if not AI_CONCERN_REGEX.search(tweet_text):
                continue

            user = str(row.get("User", "[user]"))
            created_at = str(row.get("Date", ""))
            likes = row.get("Likes", 0)
            retweets = row.get("Retweets", 0)

            raw_record = {
                "tweet_id": tid,
                "platform": "X",
                "user": user,
                "created_at": created_at,
                "likes": likes,
                "retweets": retweets,
                "query": "AI Concerns Archive",
                "raw_text": tweet_text,
                "url": tweet_url,
            }
            raw_batch.append(raw_record)

            # Cleaning & Validasi Bahasa Inggris
            cleaned = clean_tweet_text(tweet_text)
            if is_english_and_valid(cleaned):
                clean_record = {
                    "tweet_id": tid,
                    "platform": "X",
                    "created_at": created_at,
                    "likes": likes,
                    "retweets": retweets,
                    "query_topic": "AI Concerns",
                    "clean_text": cleaned,
                    "url": tweet_url,
                }
                clean_batch.append(clean_record)

        if raw_batch:
            df_raw = pd.DataFrame(raw_batch)
            df_raw.to_csv(RAW_CSV, mode="a", index=False, header=not os.path.exists(RAW_CSV), encoding="utf-8")

        if clean_batch:
            df_clean = pd.DataFrame(clean_batch)
            df_clean.to_csv(CLEAN_CSV, mode="a", index=False, header=not os.path.exists(CLEAN_CSV), encoding="utf-8")
            added = len(clean_batch)
            added_count += added
            pbar.update(added)

        time.sleep(0.3)

    pbar.close()

    print("\n" + "=" * 65)
    print(" PENGUMPULAN DATA SELESAI!")
    print(f" Tweet bersih baru yang ditambahkan: {added_count}")
    if os.path.exists(CLEAN_CSV):
        df_clean_all = pd.read_csv(CLEAN_CSV)
        print(f" Total seluruh dataset tweet bersih ({CLEAN_CSV}): {len(df_clean_all)} baris")
    print("=" * 65)


# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper Tweet X (Twitter) Isu & Kekhawatiran AI")
    parser.add_argument(
        "--mode",
        choices=["archive", "live"],
        default="archive",
        help="Pilih mode: 'archive' (publik tanpa login) atau 'live' (langsung dari X dengan twikit)"
    )
    parser.add_argument(
        "--target",
        type=int,
        default=500,
        help="Jumlah target tweet yang ingin dikumpulkan"
    )

    args = parser.parse_args()

    if args.mode == "live":
        asyncio.run(scrape_live_twikit(target_per_query=args.target))
    else:
        scrape_archive_hf(target_count=args.target)
