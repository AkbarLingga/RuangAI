from __future__ import annotations

import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # supaya folder proyek terbaca saat file ini dijalankan langsung

from scraping.scrape_x import is_english_and_valid as is_english_tweet
from scraping.scrape_reddit_batch1 import clean_comment_text, is_english_and_valid as is_english_comment


ROOT = Path(__file__).resolve().parents[1]
SOCIAL_COLUMNS = [
    "video_id",
    "video_title",
    "video_published_at",
    "comment_id",
    "parent_comment_id",
    "type",
    "author",
    "comment_published_at",
    "like_count",
    "text",
    "relevance_basis",
]

X_PARQUET_URL = "https://datasets-server.huggingface.co/parquet"
X_DATASET = "deberain/ChatGPT-Tweets"
X_CONCERN_PATTERN = re.compile(
    r"\b(?:job|jobs|layoff|layoffs|unemploy|unemployment|replace|replacing|career|"
    r"workforce|privacy|surveillance|harvesting|leak|data|security|deepfake|"
    r"deepfakes|scam|scams|fraud|fake|impersonat|misinformation|disinformation|"
    r"cheat|cheating|plagiar|plagiarism|school|schools|student|students|teacher|"
    r"teachers|education|copyright|artist|artists|art|stolen|intellectual property|"
    r"slop|danger|threat|risk|existential|destroy|ethics|ethical|harm)\b",
    re.IGNORECASE,
)

REDDIT_URL = "https://arctic-shift.photon-reddit.com/api/comments/search"
REDDIT_SUBREDDITS = (
    "ChatGPT",
    "aiwars",
    "singularity",
    "OpenAI",
    "technology",
    "LocalLLaMA",
)
REDDIT_RELEVANCE_PATTERN = re.compile(
    r"\b(ai|a\.i\.|artificial intelligence|chatgpt|openai|llm|llms|"
    r"machine learning|generative model|language model)\b",
    re.IGNORECASE,
)
REDDIT_START_MONTH = (2024, 1)
REDDIT_END_MONTH = (2026, 10)
REDDIT_TARGET_PER_MONTH = 48
X_MONTH_TARGETS = {"2022-12": 541, "2023-01": 541, "2023-02": 542}


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(5):
        try:
            response = requests.get(url, params=params, timeout=40)
            if response.status_code == 429 or response.status_code >= 500:
                last_error = RuntimeError(
                    f"HTTP {response.status_code} dari {response.url}: {response.text[:200]}"
                )
                time.sleep(min(2 ** attempt, 8))
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError(f"Respons dari {url} bukan objek JSON.")
            return payload
        except (requests.RequestException, ValueError) as error:
            last_error = error
            if attempt < 4:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Gagal mengambil data dari {url}: {last_error}") from last_error


def _month_range(start: tuple[int, int], end: tuple[int, int]):
    year, month = start
    while (year, month) <= end:
        yield year, month
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end


def _common_record(
    *,
    comment_id: str,
    parent_comment_id: str,
    comment_type: str,
    author: str,
    published_at: str,
    like_count: Any,
    text: str,
    relevance_basis: str,
    video_title: str = "",
) -> dict[str, Any]:
    return {
        "video_id": "",
        "video_title": video_title,
        "video_published_at": "",
        "comment_id": comment_id,
        "parent_comment_id": parent_comment_id,
        "type": comment_type,
        "author": author,
        "comment_published_at": published_at,
        "like_count": like_count,
        "text": text,
        "relevance_basis": relevance_basis,
    }


def _date_from_x(row: dict[str, Any]) -> datetime | None:
    value = pd.to_datetime(row.get("Date"), errors="coerce", utc=True)
    if pd.isna(value):
        return None
    return value.to_pydatetime()


def _refresh_x() -> list[dict[str, Any]]:
    metadata = _request_json(X_PARQUET_URL, {"dataset": X_DATASET, "config": "default"})
    parquet_files = metadata.get("parquet_files", [])
    if not parquet_files or not parquet_files[0].get("url"):
        raise RuntimeError(f"Dataset arsip X tidak menyediakan berkas Parquet: {X_DATASET}")

    parquet_url = str(parquet_files[0]["url"])
    expected_size = int(parquet_files[0].get("size", 0) or 0)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="ruangai-x-", suffix=".parquet", delete=False) as temp:
            temp_path = Path(temp.name)
        downloaded = 0
        last_error: Exception | None = None
        for attempt in range(5):
            headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}
            try:
                with requests.get(
                    parquet_url,
                    headers=headers,
                    stream=True,
                    timeout=(30, 60),
                ) as response:
                    response.raise_for_status()
                    if downloaded and response.status_code != 206:
                        downloaded = 0
                        temp_path.write_bytes(b"")
                    with temp_path.open("ab" if downloaded else "wb") as target:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                target.write(chunk)
                                downloaded += len(chunk)
                if expected_size and downloaded != expected_size:
                    raise OSError(
                        f"Arsip X terunduh tidak lengkap ({downloaded}/{expected_size} byte)."
                    )
                break
            except (OSError, requests.RequestException) as error:
                last_error = error
                if attempt == 4:
                    raise RuntimeError(f"Gagal mengunduh arsip X: {error}") from error
                if expected_size and downloaded >= expected_size:
                    raise RuntimeError(f"Ukuran arsip X tidak valid: {error}") from error
                time.sleep(min(2 ** attempt, 8))

        if last_error and expected_size and downloaded != expected_size:
            raise RuntimeError(f"Gagal mengunduh arsip X: {last_error}") from last_error

        frame = pd.read_parquet(
            temp_path,
            columns=["Date", "Tweet", "Url", "User", "Likes"],
        )
    except (ImportError, OSError, ValueError) as error:
        raise RuntimeError(f"Gagal membaca arsip Parquet X: {error}") from error
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    frame["published"] = pd.to_datetime(frame["Date"], errors="coerce", utc=True)
    frame["month"] = frame["published"].dt.strftime("%Y-%m")
    frame["text"] = frame["Tweet"].fillna("").astype(str).str.strip()
    frame = frame[
        frame["text"].str.len().ge(35)
        & frame["text"].str.split().str.len().ge(6)
        & frame["text"].str.contains(X_CONCERN_PATTERN, na=False)
    ]

    records: list[dict[str, Any]] = []
    for month, target in X_MONTH_TARGETS.items():
        selected = frame[frame["month"] == month]
        month_records: list[dict[str, Any]] = []
        for row in selected.to_dict(orient="records"):
            text = str(row["text"])
            tweet_url = str(row.get("Url", "") or "")
            match = re.search(r"/status/(\d+)", tweet_url)
            published = row["published"]
            if not match or not is_english_tweet(text):
                continue
            month_records.append(
                _common_record(
                    comment_id=match.group(1),
                    parent_comment_id="",
                    comment_type="post",
                    author=str(row.get("User", "") or ""),
                    published_at=published.strftime("%Y-%m-%d %H:%M:%S"),
                    like_count=row.get("Likes", 0) or 0,
                    text=text,
                    relevance_basis="arsip_x_topik_ai",
                )
            )
            if len(month_records) == target:
                break
        if len(month_records) < target:
            raise RuntimeError(
                f"Arsip X hanya menyediakan {len(month_records)} dari {target} data "
                f"berbahasa Inggris yang relevan untuk {month}."
            )
        records.extend(month_records)
        print(f"X {month}: {len(month_records)} posting relevan", flush=True)

    if len({record["comment_id"] for record in records}) != len(records):
        raise RuntimeError("Arsip X mengembalikan ID posting duplikat.")
    return records


def _refresh_reddit() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for month_index, (year, month) in enumerate(_month_range(REDDIT_START_MONTH, REDDIT_END_MONTH)):
        month = int(month)
        month_label = f"{year:04d}-{month:02d}"
        start, end = _month_bounds(year, month)
        first_subreddit = month_index % len(REDDIT_SUBREDDITS)
        subreddits = (
            REDDIT_SUBREDDITS[first_subreddit:]
            + REDDIT_SUBREDDITS[:first_subreddit]
        )
        before = int(end.timestamp())
        selected: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        used_subreddits: set[str] = set()

        for subreddit in subreddits:
            after = int(start.timestamp())
            for _ in range(8):
                params: dict[str, Any] = {
                    "subreddit": subreddit,
                    "after": after,
                    "before": before,
                    "limit": 100,
                    "sort": "asc",
                }
                payload = _request_json(REDDIT_URL, params)
                comments = payload.get("data", [])
                if not isinstance(comments, list) or not comments:
                    break

                for comment in comments:
                    comment_id = str(comment.get("id", "") or "")
                    text = str(comment.get("body", "") or "")
                    author = str(comment.get("author", "") or "")
                    if (
                        not comment_id
                        or comment_id in seen_ids
                        or not REDDIT_RELEVANCE_PATTERN.search(text)
                        or not is_english_comment(clean_comment_text(text), author=author)
                    ):
                        continue
                    created_utc = int(comment.get("created_utc", 0) or 0)
                    published = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                    if not (start <= published < end):
                        continue
                    seen_ids.add(comment_id)
                    parent_id = str(comment.get("parent_id", "") or "")
                    selected.append(
                        _common_record(
                            comment_id=comment_id,
                            parent_comment_id=parent_id,
                            comment_type=(
                                "balasan" if parent_id.startswith("t1_") else "komentar_utama"
                            ),
                            author=author,
                            published_at=published.strftime("%Y-%m-%d %H:%M:%S"),
                            like_count=comment.get("score", 0) or 0,
                            text=text,
                            relevance_basis=(
                                "kata_kunci_ai" if subreddit == "technology" else "subreddit_ai"
                            ),
                            video_title=str(comment.get("link_title", "") or ""),
                        )
                    )
                    used_subreddits.add(subreddit)
                    if len(selected) == REDDIT_TARGET_PER_MONTH:
                        break

                if len(selected) == REDDIT_TARGET_PER_MONTH or len(comments) < 100:
                    break
                last_created = int(comments[-1].get("created_utc", 0) or 0)
                if last_created <= after:
                    raise RuntimeError(
                        f"Pagination Reddit tidak bergerak untuk r/{subreddit} pada {month_label}."
                    )
                after = last_created
            if len(selected) == REDDIT_TARGET_PER_MONTH:
                break

        if len(selected) < REDDIT_TARGET_PER_MONTH:
            raise RuntimeError(
                f"Reddit hanya menyediakan {len(selected)} dari {REDDIT_TARGET_PER_MONTH} "
                f"komentar valid untuk {month_label}."
            )
        records.extend(selected)
        subreddits_used = ", ".join(sorted(used_subreddits))
        print(
            f"Reddit {month_label} (r/{subreddits_used}): "
            f"{len(selected)} komentar relevan",
            flush=True,
        )

    return records


def _save_source(filename: str, records: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(records, columns=SOCIAL_COLUMNS)
    if frame.empty:
        raise RuntimeError(f"Tidak ada data untuk disimpan ke {filename}.")
    frame.to_csv(ROOT / filename, index=False, encoding="utf-8-sig")
    print(f"Tersimpan: {filename} ({len(frame)} baris, {len(SOCIAL_COLUMNS)} kolom)", flush=True)


def main() -> int:
    try:
        x_records = _refresh_x()
        reddit_records = _refresh_reddit()
        _save_source("data/raw/x/x_ai_refreshed_raw.csv", x_records)
        _save_source("data/raw/reddit/reddit_ai_refreshed_raw.csv", reddit_records)
    except (OSError, RuntimeError, ValueError, requests.RequestException) as error:
        print(f"Gagal mengambil ulang data sosial: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
