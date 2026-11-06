from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # supaya folder proyek terbaca saat file ini dijalankan langsung

from analysis.config import PROCESSED_FILE
from analysis.sentiment import clean_text, identify_topics


WEB_DIR = Path(__file__).resolve().parent
ROOT = WEB_DIR.parent
app = Flask(__name__, template_folder=str(WEB_DIR / "templates"), static_folder=str(WEB_DIR / "static"))

DATA_COLUMNS = [
    "platform", "source_id", "date", "source_context", "engagement",
    "clean_text", "sentiment", "sentiment_score", "polarity",
    "sarcasm", "sarcasm_score", "topic",
]


def _load_data() -> pd.DataFrame:
    if not PROCESSED_FILE.exists():
        raise FileNotFoundError(
            "Dataset olahan belum ditemukan. Jalankan `python analysis/merge_social_data.py` terlebih dahulu."
        )
    return pd.read_csv(PROCESSED_FILE, keep_default_na=False)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/data")
@app.get("/data.json")
def api_data():
    try:
        data = _load_data()
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 503
    except (OSError, pd.errors.ParserError, UnicodeError) as error:
        app.logger.exception("Tidak dapat membaca dataset olahan")
        return jsonify({"error": f"Gagal membaca dataset: {error}"}), 500

    missing = [column for column in DATA_COLUMNS if column not in data.columns]
    if missing:
        app.logger.error("Kolom dataset olahan hilang: %s", ", ".join(missing))
        return jsonify({"error": f"Kolom dataset tidak lengkap: {', '.join(missing)}"}), 500

    rows = data[DATA_COLUMNS].to_dict(orient="records")
    return jsonify({"rows": rows, "total": len(rows)})


@app.post("/api/analyze")
def api_analyze():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
        return jsonify({"error": "Kirim teks pada properti `text`."}), 400
    if len(payload["text"]) > 4000:
        return jsonify({"error": "Teks maksimal 4.000 karakter."}), 400

    text = clean_text(payload["text"])
    if not text:
        return jsonify({"error": "Masukkan teks yang ingin dianalisis."}), 400

    try:
        from analysis.transformer_model import analyze_text

        result = analyze_text(text)
    except ImportError:
        app.logger.exception("Paket model belum terpasang")
        return jsonify({"error": "Paket model belum terpasang. Jalankan `pip install -r requirements-ml.txt`."}), 503
    except OSError as error:
        app.logger.exception("Model Transformer gagal dimuat")
        return jsonify({"error": f"Model Transformer gagal dimuat: {error}"}), 503

    return jsonify({"clean_text": text, "topics": identify_topics(text).split("; "), **result})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
