"""
Cleaning teks, filter noise, dan penandaan topik.

Sentimen dan sarkasme TIDAK dihitung di sini. Keduanya diklasifikasikan oleh
model Transformer di analysis/transformer_model.py.
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

# [Filter noise] pola teks promosi/iklan yang dibuang oleh is_noise()
_PROMO_RE = re.compile(
    r"\b(book now|register now|webinar|summit|conference|discount|promo code|"
    r"buy now|giveaway|airdrop|sponsored|affiliate|dm me for|click here)\b",
    re.IGNORECASE,
)


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