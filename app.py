from __future__ import annotations

from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

from preprocess import OUTPUT_FILE
from sentiment import analyze_sentiment, clean_text, identify_topics


ROOT = Path(__file__).resolve().parent
app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))


def _load_data() -> pd.DataFrame:
    if not OUTPUT_FILE.exists():
        raise FileNotFoundError(
            "Dataset olahan belum ditemukan. Jalankan `python preprocess.py` terlebih dahulu."
        )
    return pd.read_csv(OUTPUT_FILE, keep_default_na=False)


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
        "clean_text", "sentiment", "sentiment_score", "topic",
    ]
    missing = [column for column in columns if column not in data.columns]
    if missing:
        app.logger.error("Kolom dataset olahan hilang: %s", ", ".join(missing))
        return jsonify({"error": f"Kolom dataset tidak lengkap: {', '.join(missing)}"}), 500

    rows = data[columns].to_dict(orient="records")
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

    sentiment, score = analyze_sentiment(text)
    return jsonify(
        {
            "clean_text": text,
            "sentiment": sentiment,
            "sentiment_score": score,
            "topics": identify_topics(text).split("; "),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
