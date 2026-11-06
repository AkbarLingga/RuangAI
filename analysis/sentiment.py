"""
sentiment.py  (versi berkomentar)

Peta 6 tahap analisis sentimen -> posisi di file ini:

  TAHAP 1  Pengumpulan data ........ TIDAK ADA di file ini
                                     (folder scraping/ dan analysis/merge_social_data.py)
  TAHAP 2  Pelabelan data .......... kamus kata + analyze_sentiment() + normalized_polarity()
                                     (+ identify_topics() sebagai label tambahan)
  TAHAP 3  Preprocessing ........... clean_text(), is_noise(), tokenisasi, case folding
  TAHAP 4  Ekstraksi fitur ......... TIDAK ADA di file ini (TF-IDF ada di sentiment_model.py)
  TAHAP 5  Klasifikasi ............. analyze_sentiment() = pendekatan RULE-BASED (leksikon)
                                     (model Logistic Regression ada di sentiment_model.py)
  TAHAP 6  Evaluasi & visualisasi .. TIDAK ADA di file ini (evaluate_sentiment.py, app.py, static/app.js)

Logika kode TIDAK diubah dari versi asli, hanya ditambah komentar.
"""
from __future__ import annotations

import re
import unicodedata
from html import unescape


# =====================================================================
# TAHAP 3 - PREPROCESSING: pola regex untuk CLEANING
# =====================================================================
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)           # [Cleaning] hapus URL
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((?:https?://)?[^)]+\)")  # [Cleaning] [teks](link) -> teks
_MENTION_RE = re.compile(r"(?<!\w)@\w+")                                 # [Cleaning] hapus @mention
_HASHTAG_RE = re.compile(r"#(\w+)")                                      # [Cleaning] #kata -> kata

# [Tokenization] pola pemecah teks jadi token kata (hanya huruf; angka & tanda baca dibuang di sini)
_TOKEN_RE = re.compile(r"[a-zA-Z]+(?:'[a-zA-Z]+)?")

# [Filter noise] pola teks promosi/iklan yang dibuang oleh is_noise()
_PROMO_RE = re.compile(
    r"\b(book now|register now|webinar|summit|conference|discount|promo code|"
    r"buy now|giveaway|airdrop|sponsored|affiliate|dm me for|click here)\b",
    re.IGNORECASE,
)


# =====================================================================
# TAHAP 2 & 5 - PELABELAN / KLASIFIKASI RULE-BASED: KAMUS (LEKSIKON)
# Kata-kata ini yang menentukan skor di analyze_sentiment()
# =====================================================================

# Kamus kata POSITIF (Inggris + Indonesia): tiap kata cocok = +1
_POSITIVE_WORDS = set(
    """
    amazing awesome beautiful benefit beneficial best better brilliant cool easy
    effective excellent exciting fair fantastic good great helpful hope improve
    improved improvement incredible innovative like love lovely nice opportunity
    positive powerful productive progress recommend safe succeed useful valuable
    wonderful wow yes bermanfaat bagus baik keren hebat mantap membantu mudah
    memudahkan positif aman suka senang setuju menarik berguna peluang
    """.split()
)

# Kamus kata NEGATIF (Inggris + Indonesia): tiap kata cocok = -1
_NEGATIVE_WORDS = set(
    """
    abuse alarming awful bad biased broke broken harmful harm hate horrible
    inaccurate issue lie lies lying misleading misinformation mistake dangerous
    danger wrong fail failed failure fake fear fearful flawed fraud frustrating
    frustratingly glitch hate harmful harm insecure issue scam scary stolen theft
    threat threaten terrible terrible unfair unsafe useless worry worried
    worries risk risks privacy exploit exploitative replace replacing replacement
    unemployment layoff layoffs steal steals stole stolen leak leaks leaked
    bahaya berbahaya buruk takut khawatir ancaman mengancam merugikan rugi
    negatif salah bohong palsu penipuan tipu curi dicuri kebocoran ancam
    rusak merusak gagal masalah susah sulit jelek buruknya kriminal hoaks
    kekeringan krisis kecanduan ketergantungan menakutkan seram
    """.split()
)

# Kata PEMBALIK: membalik tanda skor pada 3 kata berikutnya ("not good" -> negatif)
_NEGATORS = {
    "not", "no", "never", "neither", "nor", "hardly", "isn't", "wasn't",
    "don't", "doesn't", "didn't", "can't", "cannot", "won't", "wouldn't",
    "shouldn't", "without", "tidak", "bukan", "belum", "jangan", "nggak",
    "enggak", "gak", "ga", "kurang",
}

# Kata PENGUAT: mengalikan 1,5 pada kata sentimen berikutnya
_INTENSIFIERS = {
    "very", "really", "extremely", "so", "too", "sangat", "banget", "amat",
    "benar-benar", "terlalu",
}


# =====================================================================
# TAHAP 2 - PELABELAN (label tambahan): DAFTAR TOPIK BERBASIS KATA KUNCI
# Dipakai identify_topics() untuk mengisi kolom `topic`
# =====================================================================
_TOPICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Pekerjaan",
        (
            r"\bjobs?\b", r"\bwork(?:er|ers|force)?\b", r"\bemploy(?:ment|ee|ees)?\b",
            r"\bcareer\b", r"\blayoffs?\b", r"\bunemploy\w*\b", r"\breplac\w*\b",
            r"\bpekerja(?:an)?\b", r"\bkerja\b", r"\bpengangguran\b", r"\bphk\b",
            r"\blapangan kerja\b", r"\bgaji\b",
        ),
    ),
    (
        "Privasi dan keamanan data",
        (
            r"\bprivacy\b", r"\bprivasi\b", r"\bsurveillance\b", r"\bdata breach\b",
            r"\bdata leak\b", r"\bdata theft\b", r"\bpersonal data\b",
            r"\bkeamanan data\b", r"\bprivasi data\b", r"\bpengawasan\b",
            r"\bdata pribadi\b",
        ),
    ),
    (
        "Deepfake dan misinformasi",
        (
            r"\bdeepfakes?\b", r"\bmisinformation\b", r"\bdisinformation\b",
            r"\bfake news\b", r"\bhoax\b", r"\bscams?\b", r"\bfraud\b",
            r"\bpenipuan\b", r"\bpalsu\b", r"\bberita bohong\b", r"\bnipu\b",
        ),
    ),
    (
        "Pendidikan",
        (
            r"\bschools?\b", r"\beducation(?:al)?\b", r"\bstudents?\b",
            r"\bteachers?\b", r"\bplagiar\w*\b", r"\bcheating\b", r"\blearning\b",
            r"\bpendidikan\b", r"\bsekolah\b", r"\bsiswa\b", r"\bmahasiswa\b",
            r"\bguru\b", r"\bbelajar\b", r"\bujian\b", r"\btugas\b",
        ),
    ),
    (
        "Hak cipta dan kreator",
        (
            r"\bcopyright\b", r"\bintellectual property\b", r"\bartists?\b",
            r"\billustrators?\b", r"\bcreators?\b", r"\bartwork\b", r"\bai art\b",
            r"\bhak cipta\b", r"\bseniman\b", r"\bkreator\b", r"\bpencipta\b",
        ),
    ),
    (
        "Lingkungan dan sumber daya",
        (
            r"\bdata cent(?:er|re)s?\b", r"\bdatacent(?:er|re)s?\b",
            r"\bwater\b", r"\benergy\b", r"\belectricity\b", r"\bcooling\b",
            r"\bclimate\b", r"\benvironment\w*\b", r"\bcarbon\b", r"\bpollution\b",
            r"\bair\b", r"\benergi\b", r"\blistrik\b", r"\bpusat data\b",
            r"\bair bersih\b", r"\bair tanah\b", r"\bkekeringan\b",
            r"\blingkungan\b", r"\bpendingin\b",
        ),
    ),
    (
        "Risiko sosial dan etika",
        (
            r"\bexistential\b", r"\bextinction\b", r"\bethics?\b", r"\bethical\b",
            r"\bthreat\b", r"\bdanger(?:ous)?\b", r"\baddiction\b",
            r"\bdependency\b", r"\bketergantungan\b", r"\bkecanduan\b",
            r"\bancaman\b", r"\bbahaya\b", r"\bdampak sosial\b",
            r"\bmasa depan\b", r"\bkemanusiaan\b",
        ),
    ),
    (
        "Manfaat dan produktivitas",
        (
            r"\bbenefit\w*\b", r"\bhelpful\b", r"\buseful\b", r"\bproductiv\w*\b",
            r"\befficient\w*\b", r"\bopportunit\w*\b", r"\binnovation\b",
            r"\bbermanfaat\b", r"\bmanfaat\b", r"\bmembantu\b", r"\bmemudahkan\b",
            r"\bproduktivitas\b", r"\befisien\b", r"\bpeluang\b", r"\binovasi\b",
        ),
    ),
)
# Pola topik dikompilasi sekali di awal supaya pencarian cepat
_COMPILED_TOPICS = tuple(
    (label, tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns))
    for label, patterns in _TOPICS
)


# =====================================================================
# TAHAP 3 - PREPROCESSING: CLEANING
# =====================================================================
def clean_text(text: object) -> str:
    """Normalize social text while keeping readable words and punctuation."""
    if not isinstance(text, str):
        return ""
    text = unescape(text)                          # [Cleaning] &amp; -> &, dst
    text = _MARKDOWN_LINK_RE.sub(r"\1", text)      # [Cleaning] [teks](link) -> teks
    text = _URL_RE.sub(" ", text)                  # [Cleaning] hapus URL
    text = _MENTION_RE.sub(" ", text)              # [Cleaning] hapus @mention
    text = _HASHTAG_RE.sub(r"\1", text)            # [Cleaning] hapus tanda #, kata dipertahankan
    text = re.sub(r"(?m)^\s*>\s?", " ", text)      # [Cleaning] hapus tanda kutipan '>' (Reddit)
    # [Cleaning] buang karakter kontrol & emoji/simbol (kategori Cc, Cs, So)
    text = "".join(
        char for char in text 
        if unicodedata.category(char) not in {"Cc", "Cs", "So"}
        or char in "\n\t\r"
    )
    # [Cleaning] rapikan spasi/enter berlebih jadi satu spasi
    # CATATAN: angka & tanda baca TIDAK dibuang di sini; baru hilang saat tokenisasi.
    return re.sub(r"\s+", " ", text).strip()


# =====================================================================
# TAHAP 3 - PREPROCESSING: FILTER DATA TIDAK RELEVAN (NOISE)
# =====================================================================
def is_noise(text: str, author: str = "") -> bool:
    normalized = text.casefold().strip()           # [Case folding] huruf kecil semua untuk dibandingkan
    # [Filter] teks kosong atau komentar yang sudah dihapus
    if not normalized or normalized in {"[deleted]", "[removed]", "deleted", "removed"}:
        return True
    # [Filter] komentar dari bot
    if author.casefold().strip() in {"automoderator", "aut moderator", "remindmebot"}:
        return True
    if "i am a bot, and this action was performed automatically" in normalized:
        return True
    if "this action was performed automatically" in normalized:
        return True
    # [Filter] teks promosi/iklan
    if _PROMO_RE.search(text):
        return True
    # [Filter] teks terlalu pendek (< 3 karakter huruf/angka)
    return len(re.sub(r"\W", "", text)) < 3


# =====================================================================
# TAHAP 2 (PELABELAN) + TAHAP 5 (KLASIFIKASI RULE-BASED)
# Output: kolom `sentiment` (Positif/Netral/Negatif) dan `sentiment_score`
# =====================================================================
def analyze_sentiment(text: str) -> tuple[str, float]:
    """Return a transparent bilingual lexicon score and its polarity label."""
    # [Case folding + Tokenization] huruf kecil, lalu pecah teks jadi token kata
    tokens = [token.casefold() for token in _TOKEN_RE.findall(text)]
    score = 0.0
    negation_window = 0     # sisa jangkauan kata pembalik (3 kata)
    intensity = 1.0         # pengali penguat (1.0 normal, 1.5 jika ada kata penguat)

    for token in tokens:
        # Kata pembalik: aktifkan jendela 3 kata ke depan
        if token in _NEGATORS:
            negation_window = 3
            continue
        # Kata penguat: kata sentimen berikutnya dikali 1,5
        if token in _INTENSIFIERS:
            intensity = 1.5
            continue

        # Cocokkan dengan kamus: positif +1, negatif -1, lainnya 0
        value = 1.0 if token in _POSITIVE_WORDS else -1.0 if token in _NEGATIVE_WORDS else 0.0
        if value:
            # Akumulasi skor; dibalik tandanya jika masih dalam jendela negasi
            score += value * intensity * (-1 if negation_window else 1)
            intensity = 1.0
        if negation_window:
            negation_window -= 1

    # [Penentuan label] skor > 0 Positif, < 0 Negatif, = 0 Netral
    if score > 0:
        return "Positif", score
    if score < 0:
        return "Negatif", score
    return "Netral", score


# =====================================================================
# TAHAP 2 - PELABELAN: kolom `polarity` (skor dinormalisasi -1 s.d. 1)
# =====================================================================
def normalized_polarity(text: str, sentiment_score: float | None = None) -> float:
    """Return a bounded per-comment polarity normalized by sentiment-bearing words."""
    tokens = [token.casefold() for token in _TOKEN_RE.findall(text)]   # [Tokenization]
    # hitung berapa kata yang ada di kamus (positif ATAU negatif)
    matched_tokens = sum(
        token in _POSITIVE_WORDS or token in _NEGATIVE_WORDS for token in tokens
    )
    if not matched_tokens:
        return 0.0
    score = analyze_sentiment(text)[1] if sentiment_score is None else sentiment_score
    # skor dibagi jumlah kata sentimen, lalu dibatasi ke rentang [-1, 1]
    return max(-1.0, min(1.0, score / matched_tokens))


# =====================================================================
# TAHAP 2 - PELABELAN (label tambahan): kolom `topic`
# =====================================================================
def identify_topics(text: str) -> str:
    """Return all matching research topics, or 'Lainnya' when none match."""
    # satu komentar bisa punya beberapa topik (dipisah "; ")
    matches = [
        label
        for label, patterns in _COMPILED_TOPICS
        if any(pattern.search(text) for pattern in patterns)
    ]
    return "; ".join(matches) if matches else "Lainnya"