from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # supaya folder proyek terbaca saat file ini dijalankan langsung

from analysis.preprocess import OUTPUT_FILE
from analysis.sentiment import analyze_sentiment, clean_text, identify_topics, normalized_polarity
from analysis.sentiment_model import export_browser_model, fit_sentiment_model, predict_probabilities


WEB_DIR = Path(__file__).resolve().parent
ROOT = WEB_DIR.parent
app = Flask(__name__, template_folder=str(WEB_DIR / "templates"), static_folder=str(WEB_DIR / "static"))


def _load_data() -> pd.DataFrame:
    if not OUTPUT_FILE.exists():
        raise FileNotFoundError(
            "Dataset olahan belum ditemukan. Jalankan `python preprocess.py` terlebih dahulu."
        )
    return pd.read_csv(OUTPUT_FILE, keep_default_na=False)


@lru_cache(maxsize=1)
def _get_sentiment_model():
    data = _load_data()
    required = {"clean_text", "sentiment"}
    missing = sorted(required - set(data.columns))
    if missing:
        raise ValueError(f"Kolom dataset untuk model hilang: {', '.join(missing)}")
    return fit_sentiment_model(data["clean_text"].astype(str), data["sentiment"].astype(str))


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

    columns = [
        "platform", "source_id", "date", "source_context", "engagement",
        "clean_text", "sentiment", "sentiment_score", "polarity", "topic",
    ]
    missing = [column for column in columns if column not in data.columns]
    if missing:
        app.logger.error("Kolom dataset olahan hilang: %s", ", ".join(missing))
        return jsonify({"error": f"Kolom dataset tidak lengkap: {', '.join(missing)}"}), 500

    try:
        model = export_browser_model(_get_sentiment_model())
    except (OSError, ValueError, KeyError) as error:
        app.logger.exception("Tidak dapat melatih model sentimen")
        return jsonify({"error": f"Gagal menyiapkan model sentimen: {error}"}), 500

    rows = data[columns].to_dict(orient="records")
    return jsonify({"rows": rows, "total": len(rows), "sentiment_model": model})


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

    sentiment, score = analyze_sentiment(text)
    try:
        model = _get_sentiment_model()
    except (OSError, ValueError, KeyError) as error:
        app.logger.exception("Tidak dapat melatih model sentimen")
        return jsonify({"error": f"Gagal menyiapkan model sentimen: {error}"}), 500
    probabilities = predict_probabilities(model, text)
    predicted_sentiment = max(probabilities, key=probabilities.get)
    return jsonify(
        {
            "clean_text": text,
            "sentiment": sentiment,
            "sentiment_score": score,
            "polarity": normalized_polarity(text, score),
            "topics": identify_topics(text).split("; "),
            "model_sentiment": predicted_sentiment,
            "model_probabilities": probabilities,
            "model_training_labels": "Label leksikon; belum divalidasi manual",
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
