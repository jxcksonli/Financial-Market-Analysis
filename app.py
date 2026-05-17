"""
Financial Market Insights — run with: python app.py
Open http://127.0.0.1:5000/ (do not open templates/index.html in the browser).
"""

from __future__ import annotations

import os
from pathlib import Path

from fmi.web import create_app

ROOT_DIR = Path(__file__).resolve().parent
app = create_app(root_dir=ROOT_DIR)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://127.0.0.1:{port}/"
    print()
    print("  Financial Market Insights")
    print(f"  Open this URL in your browser: {url}")
    print()
    print("  Do NOT use Live Server on templates/index.html")
    print("  (that file is a Jinja template — only Flask can render it).")
    print("  Optional: Live Server on open-app.html in the project root.")
    print()
    app.run(host="127.0.0.1", port=port, debug=True)
