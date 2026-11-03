import os
import re
import time
from datetime import datetime, timezone
import pandas as pd
import requests
from langdetect import DetectorFactory, detect
from tqdm import tqdm

# Pastikan hasil langdetect konsisten
DetectorFactory.seed = 0

BASE_URL = "https://arctic-shift.photon-reddit.com/api/comments/search"

# ==========================================
# KONFIGURASI PENGAMBILAN DATA
# ==========================================
# 1. Subreddit khusus AI & Isu AI (semua postingan sudah pasti topik AI)
CORE_AI_SUBS = [
    "ChatGPT",
    "singularity",
    "artificial",
    "OpenAI",
    "LocalLLaMA",
    "aiwars",           # Debat & kekhawatiran dampak AI vs manusia/seniman/pekerja
    "ControlProblem",   # Isu keamanan AI, AGI risk, & etika masa depan
]

# 2. Subreddit umum / terdampak (wajib filter 'body': 'AI' agar komentarnya relevan tentang AI & dampak sosial)
CONCERN_SUBS = [
    "technology",       # Opini publik teknologi, regulasi, & kekhawatiran masyarakat
    "antiwork",         # Kekhawatiran penggantian lapangan kerja / PHK oleh AI
    "teachers",         # Kekhawatiran plagiarisme / kecurangan siswa di pendidikan
    "graphic_design",   # Kekhawatiran seniman terkait AI art & hak cipta
    "privacy",          # Kekhawatiran privasi, pengawasan, & data scraping AI
    "Futurology",       # Prediksi masa depan & dampak sosial otomatisasi AI
]

ALL_SUBS = CORE_AI_SUBS + CONCERN_SUBS

# Periode data (Masa pesat adopsi GenAI: 2024 - 2026)
START_DATE = "2024-01-01"
END_DATE   = "2026-10-01"

# Target per subreddit (misal 1000 per sub -> total ~11.000 komentar)
TARGET_PER_SUB = 1000
BATCH_SIZE = 100  # Maksimal per request di Arctic Shift

RAW_CSV = "reddit_ai_raw.csv"
CLEAN_CSV = "reddit_ai_clean.csv"


# ==========================================
# FUNGSI PREPROCESSING & VALIDASI
# ==========================================
def clean_comment_text(text: str) -> str:
    """Membersihkan teks dari URL, emoji, markdown berlebih, dan whitespace."""
    if not isinstance(text, str):
        return ""
    # Buang tautan markdown [teks](url) -> teks
    text = re.sub(r'\[(.*?)\]\(https?://[^\s)]+\)', r'\1', text)
    # Buang URL biasa
    text = re.sub(r'https?://\S+', '', text)
    # Buang emoji (sesuai arahan proposal cleaning)
    emoji_pattern = re.compile(
        r'[\U00010000-\U0010ffff\uD800-\uDBFF\uDC00-\uDFFF\u2600-\u26FF\u2700-\u27BF\u2B50\u200D\uFE0F]+'
    )
    text = emoji_pattern.sub('', text)
    # Buang karakter reddit markdown quote '>' di awal baris
    text = re.sub(r'(^|\n)>\s*', ' ', text)
    # Rapikan spasi dan newline berlebih
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_english_and_valid(text: str, author: str = "") -> bool:
    """Memvalidasi bahwa komentar berbahasa Inggris, bukan bot/AutoMod, dan tidak terlalu pendek."""
    if not text or text in ["[deleted]", "[removed]"]:
        return False
    # Filter bot umum dan AutoModerator
    if author.lower() in ["automoderator", "bot", "remindmebot"]:
        return False
    lower_text = text.lower()
    if "i am a bot, and this action was performed automatically" in lower_text:
        return False
    if "this action was performed automatically" in lower_text:
        return False
    # Minimal 30 karakter dan minimal 5 kata agar bermakna untuk sentimen & topik
    if len(text) < 30 or len(text.split()) < 5:
        return False
    # Cek apakah ada huruf alfabet
    if not re.search(r'[a-zA-Z]', text):
        return False
    try:
        lang = detect(text)
        return lang == "en"
    except Exception:
        return False


def load_existing_data():
    """Membaca data yang sudah pernah di-scrape agar bisa resume tanpa duplikat."""
    seen_ids = set()
    sub_counts = {sub: 0 for sub in ALL_SUBS}
    sub_latest_utc = {sub: START_DATE for sub in ALL_SUBS}

    if os.path.exists(RAW_CSV):
        try:
            df_existing = pd.read_csv(RAW_CSV)
            if "comment_id" in df_existing.columns:
                seen_ids = set(df_existing["comment_id"].dropna().astype(str).tolist())
            if "subreddit" in df_existing.columns:
                counts = df_existing["subreddit"].astype(str).str.lower().value_counts().to_dict()
                for sub in ALL_SUBS:
                    sub_counts[sub] = counts.get(sub.lower(), 0)
            if "created_utc" in df_existing.columns and "subreddit" in df_existing.columns:
                for sub in ALL_SUBS:
                    sub_df = df_existing[df_existing["subreddit"].astype(str).str.lower() == sub.lower()]
                    if not sub_df.empty and "created_utc" in sub_df.columns:
                        max_utc = sub_df["created_utc"].max()
                        if pd.notna(max_utc):
                            sub_latest_utc[sub] = int(max_utc)
            print(f"[RESUME] Ditemukan {len(seen_ids)} komentar yang sudah tersimpan sebelumnya.")
        except Exception as e:
            print(f"[WARN] Gagal membaca CSV lama ({e}), memulai dari awal.")

    return seen_ids, sub_counts, sub_latest_utc


# ==========================================
# FUNGSI UTAMA SCRAPING
# ==========================================
def scrape_reddit():
    seen_ids, sub_counts, sub_latest_utc = load_existing_data()

    print("=" * 65)
    print(" SCRAPER KOMENTAR REDDIT - ISU PERKEMBANGAN & KEKHAWATIRAN AI")
    print(f" Target: {TARGET_PER_SUB} komentar bahasa Inggris per subreddit")
    print(f" Rentang Waktu: {START_DATE} s/d {END_DATE}")
    print(f" File Output: '{RAW_CSV}' & '{CLEAN_CSV}'")
    print("=" * 65)

    total_added_this_run = 0

    for sub in ALL_SUBS:
        current_count = sub_counts.get(sub, 0)
        if current_count >= TARGET_PER_SUB:
            print(f"\n[SKIP] r/{sub} sudah mencapai target ({current_count}/{TARGET_PER_SUB})")
            continue

        is_concern_sub = (sub in CONCERN_SUBS)
        after_val = sub_latest_utc.get(sub, START_DATE)

        print(f"\n[START] Mengambil data dari r/{sub}...")
        if is_concern_sub:
            print(f"  -> Menerapkan filter kata kunci 'AI' untuk menangkap diskusi kekhawatiran masyarakat.")
        
        pbar = tqdm(total=TARGET_PER_SUB, initial=current_count, desc=f"r/{sub}")

        while current_count < TARGET_PER_SUB:
            params = {
                "subreddit": sub,
                "after": after_val,
                "before": END_DATE,
                "limit": BATCH_SIZE,
                "sort": "asc",
            }
            if is_concern_sub:
                params["body"] = "AI"

            # Request dengan mekanisme retry
            data = None
            for attempt in range(4):
                try:
                    resp = requests.get(BASE_URL, params=params, timeout=45)
                    if resp.status_code == 200:
                        raw_data = resp.json().get("data")
                        if isinstance(raw_data, list):
                            data = raw_data
                            break
                        else:
                            time.sleep(2 * (attempt + 1))
                    elif resp.status_code == 429:
                        print("\n[RATE LIMIT] Server sibuk, menunggu 10 detik...")
                        time.sleep(10)
                    else:
                        time.sleep(3 * (attempt + 1))
                except Exception as e:
                    time.sleep(3 * (attempt + 1))

            if not data:
                print(f"\n[INFO] Tidak ada data baru lagi di r/{sub}.")
                break

            new_raw_rows = []
            new_clean_rows = []

            for c in data:
                cid = str(c.get("id", ""))
                if not cid or cid in seen_ids:
                    continue

                seen_ids.add(cid)
                body_raw = c.get("body", "")
                created_utc = c.get("created_utc", 0)

                # Format tanggal UTC yang rapi
                try:
                    date_str = datetime.fromtimestamp(created_utc, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    date_str = ""

                post_title = c.get("link_title", "")
                permalink = f"https://reddit.com{c.get('permalink', '')}" if c.get("permalink") else ""

                raw_record = {
                    "comment_id": cid,
                    "subreddit": c.get("subreddit", sub),
                    "author": c.get("author", "[anonymous]"),
                    "created_utc": created_utc,
                    "date_utc": date_str,
                    "score": c.get("score", 0),
                    "post_title": post_title,
                    "body": body_raw,
                    "permalink": permalink,
                }
                new_raw_rows.append(raw_record)

                # Validasi & Preprocessing (Harus Bahasa Inggris & Berbobot)
                cleaned = clean_comment_text(body_raw)
                author_name = str(c.get("author", ""))
                if is_english_and_valid(cleaned, author=author_name):
                    clean_record = {
                        "comment_id": cid,
                        "subreddit": c.get("subreddit", sub),
                        "created_utc": created_utc,
                        "date_utc": date_str,
                        "score": c.get("score", 0),
                        "post_title": post_title,
                        "clean_text": cleaned,
                    }
                    new_clean_rows.append(clean_record)

            # Simpan langsung ke CSV secara bertahap (Checkpointing)
            if new_raw_rows:
                df_raw_batch = pd.DataFrame(new_raw_rows)
                header = not os.path.exists(RAW_CSV)
                df_raw_batch.to_csv(RAW_CSV, mode="a", index=False, header=header, encoding="utf-8")

            if new_clean_rows:
                df_clean_batch = pd.DataFrame(new_clean_rows)
                header = not os.path.exists(CLEAN_CSV)
                df_clean_batch.to_csv(CLEAN_CSV, mode="a", index=False, header=header, encoding="utf-8")
                
                added_clean = len(new_clean_rows)
                current_count += added_clean
                total_added_this_run += added_clean
                pbar.update(added_clean)

            # Majukan 'after' ke timestamp komentar terakhir
            last_comment_utc = data[-1].get("created_utc")
            if last_comment_utc:
                if isinstance(after_val, int) and last_comment_utc <= after_val:
                    after_val = after_val + 1
                else:
                    after_val = last_comment_utc

            # Jika data yang dikembalikan kurang dari batch size, berarti sudah habis
            if len(data) < BATCH_SIZE:
                print(f"\n[INFO] Data pada r/{sub} sudah mencapai batas waktu/akhir arsip.")
                break

            time.sleep(1.0)  # Hormati server sukarelawan Arctic Shift

        pbar.close()

    print("\n" + "=" * 65)
    print(f" SCRAPING SELESAI!")
    print(f" Total komentar bersih baru yang ditambahkan: {total_added_this_run}")
    if os.path.exists(CLEAN_CSV):
        df_total = pd.read_csv(CLEAN_CSV)
        print(f" Total seluruh dataset bersih siap olah ({CLEAN_CSV}): {len(df_total)} baris")
        print("\nDistribusi komentar per subreddit:")
        print(df_total["subreddit"].value_counts())
    print("=" * 65)


if __name__ == "__main__":
    scrape_reddit()
