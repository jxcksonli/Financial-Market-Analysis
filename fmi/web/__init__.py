"""Flask application factory."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from fmi.web.routes import register_routes

def _project_root(explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[2]


def create_app(*, root_dir: Path | None = None) -> Flask:
    root = _project_root(root_dir)
    load_dotenv(root / ".env")
    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    register_routes(app)
    return app
