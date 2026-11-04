from __future__ import annotations

import json
import sys
from pathlib import Path

from flask import render_template

from app import ROOT, _get_sentiment_model, _load_data, app
from sentiment_model import export_browser_model


SITE_DIR = ROOT / "_site"
DATA_COLUMNS = [
    "platform", "source_id", "date", "source_context", "engagement",
    "clean_text", "sentiment", "sentiment_score", "polarity", "topic",
]


def build() -> None:
    data = _load_data()
    missing = [column for column in DATA_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Kolom dataset olahan tidak lengkap: {', '.join(missing)}")

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    with app.test_request_context("/"):
        page = render_template("index.html")
    page = page.replace('href="/static/style.css"', 'href="./style.css"')
    page = page.replace('src="/static/app.js"', 'src="./app.js"')
    page = page.replace('href="/"', 'href="./"')

    (SITE_DIR / "index.html").write_text(page, encoding="utf-8")
    (SITE_DIR / "data.json").write_text(
        json.dumps(
            {
                "rows": json.loads(
                    data[DATA_COLUMNS].to_json(orient="records", force_ascii=False)
                ),
                "total": len(data),
                "sentiment_model": export_browser_model(_get_sentiment_model()),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (SITE_DIR / "style.css").write_bytes((ROOT / "static" / "style.css").read_bytes())
    (SITE_DIR / "app.js").write_bytes((ROOT / "static" / "app.js").read_bytes())
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"GitHub Pages site built: {SITE_DIR} ({len(data)} records)")


if __name__ == "__main__":
    try:
        build()
    except (OSError, ValueError) as error:
        print(f"Static site build failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
