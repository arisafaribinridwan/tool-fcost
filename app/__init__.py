from __future__ import annotations

import os
from pathlib import Path

from flask import Flask


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="web/templates",
        static_folder="web/static",
    )

    project_root = Path(__file__).resolve().parent.parent
    runtime_dirs = {
        "CONFIGS_DIR": project_root / "configs",
        "MASTERS_DIR": project_root / "masters",
        "UPLOADS_DIR": project_root / "uploads",
        "OUTPUTS_DIR": project_root / "outputs",
    }

    app.config.from_mapping(
        APP_NAME="Excel Automation Tool",
        PROJECT_ROOT=project_root,
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        **runtime_dirs,
    )

    if test_config:
        app.config.update(test_config)

    for folder_path in runtime_dirs.values():
        folder_path.mkdir(parents=True, exist_ok=True)

    from app.web.routes import web_bp

    app.register_blueprint(web_bp)
    return app
