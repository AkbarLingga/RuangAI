from __future__ import annotations

import json
import sys
from pathlib import Path

from flask import render_template

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # supaya folder proyek terbaca saat file ini dijalankan langsung

from web.app import DATA_COLUMNS, ROOT, WEB_DIR, _load_data, app


SITE_DIR = ROOT / "_site"


def build() -> None:
    data = _load_data()
    missing = [column for column in DATA_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Kolom dataset olahan tidak lengkap: {', '.join(missing)}")

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    with app.test_request_context("/"):
        page = render_template("index.html", static_site=True)
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
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (SITE_DIR / "style.css").write_bytes((WEB_DIR / "static" / "style.css").read_bytes())
    (SITE_DIR / "app.js").write_bytes((WEB_DIR / "static" / "app.js").read_bytes())
    (SITE_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print(f"GitHub Pages site built: {SITE_DIR} ({len(data)} records)")


if __name__ == "__main__":
    try:
        build()
    except (OSError, ValueError) as error:
        print(f"Static site build failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
