"""
PENGGABUNG DATASET REDDIT & X (TWITTER) UNTUK ANALISIS SENTIMEN & TOPIC MODELING
"""
import os
import pandas as pd

REDDIT_CSV = "reddit_ai_clean.csv"
X_CSV = "x_ai_clean.csv"
COMBINED_CSV = "combined_social_ai.csv"

def merge_data():
    dfs = []

    if os.path.exists(REDDIT_CSV):
        df_r = pd.read_csv(REDDIT_CSV)
        df_r_norm = pd.DataFrame({
            "id": df_r["comment_id"],
            "platform": "Reddit",
            "source_community": "r/" + df_r["subreddit"].astype(str),
            "date": df_r["date_utc"],
            "engagement": df_r["score"],
            "clean_text": df_r["clean_text"],
        })
        dfs.append(df_r_norm)
        print(f"[LOAD] Reddit: {len(df_r_norm)} data")
    else:
        print("[WARN] 'reddit_ai_clean.csv' tidak ditemukan.")

    if os.path.exists(X_CSV):
        df_x = pd.read_csv(X_CSV)
        df_x_norm = pd.DataFrame({
            "id": df_x["tweet_id"],
            "platform": "X",
            "source_community": df_x["query_topic"],
            "date": df_x["created_at"],
            "engagement": df_x["likes"],
            "clean_text": df_x["clean_text"],
        })
        dfs.append(df_x_norm)
        print(f"[LOAD] X (Twitter): {len(df_x_norm)} data")
    else:
        print("[WARN] 'x_ai_clean.csv' tidak ditemukan.")

    if dfs:
        df_all = pd.concat(dfs, ignore_index=True)
        # Buang duplikat teks jika ada
        df_all = df_all.drop_duplicates(subset=["clean_text"])
        df_all.to_csv(COMBINED_CSV, index=False, encoding="utf-8")
        print("\n" + "=" * 50)
        print(f"Dataset gabungan berhasil dibuat: '{COMBINED_CSV}'")
        print(f"Total baris gabungan: {len(df_all)}")
        print("\nDistribusi platform:")
        print(df_all["platform"].value_counts())
        print("=" * 50)
    else:
        print("[ERROR] Tidak ada dataset yang bisa digabung.")

if __name__ == "__main__":
    merge_data()

