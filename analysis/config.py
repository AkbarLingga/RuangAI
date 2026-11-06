"""
Configuration for Balanced Social Media AI Sentiment & Topic Analysis
Project: Analisis Sentimen dan Identifikasi Topik Kekhawatiran Masyarakat terhadap Perkembangan AI di Media Sosial
"""
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
ANNOTATION_DIR = DATA_DIR / "annotations"
EVALUATION_DIR = DATA_DIR / "evaluation"
REPORTS_DIR = ROOT_DIR / "reports"

# Language Configuration
LANG_MODE = "en_only"  # "en_only" (default) or "all"

# Target per platform
TARGET_PER_PLATFORM = 2000  # 33.3% per platform (Total ~6000 items)
BUFFER_PERCENT = 0.15        # Collect 15% extra to account for noise/deduplication

# Sampling and Balance Constraints
MAX_SHARE_PER_VIDEO = 0.08   # Max 8% of YouTube data from a single video (~160 comments)
MAX_SHARE_PER_SOURCE = 0.10  # Max 10% of platform data from a single subreddit or query (~200 comments)
RANDOM_STATE = 42

# Date Windows
DATE_WINDOW_START = "2024-01-01"
DATE_WINDOW_END = "2026-11-06"
X_ARCHIVE_DATE_START = "2022-12-01"
X_ARCHIVE_DATE_END = "2023-03-01"

# Reddit Subreddits Configuration
REDDIT_SUBREDDITS = [
    # Core AI communities
    "ChatGPT",
    "singularity",
    "artificial",
    "OpenAI",
    "LocalLLaMA",
    "aiwars",
    "ControlProblem",
    "ArtificialInteligence",
    "ClaudeAI",
    # General & societal concern communities
    "technology",
    "Futurology",
    "Teachers",
    "graphic_design",
    "antiwork",
    "privacy",
    "cscareerquestions",
]

# Primary Analysis Models (Verified Hugging Face models)
ROBERTA_SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
ROBERTA_IRONY_MODEL = "cardiffnlp/twitter-roberta-base-irony"

# Lexicon Baseline Labels
LABELS = ("Positif", "Netral", "Negatif")

