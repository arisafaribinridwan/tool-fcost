from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, current_app, jsonify, render_template, request

web_bp = Blueprint("web", __name__)
ALLOWED_SOURCE_EXTENSIONS = frozenset({".xlsx", ".csv"})


def _list_config_names(configs_dir: Path) -> list[str]:
    config_names = [
        path.name
        for path in configs_dir.iterdir()
        if path.is_file() and path.suffix.casefold() in {".yaml", ".yml"}
    ]
    return sorted(config_names, key=str.casefold)


@web_bp.get("/")
def index():
    return render_template("index.html", app_name=current_app.config["APP_NAME"])


@web_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@web_bp.get("/api/configs")
def list_configs():
    configs_dir = Path(current_app.config["CONFIGS_DIR"])
    return jsonify({"configs": _list_config_names(configs_dir)})


@web_bp.post("/api/execute")
def execute_pipeline():
    source_file = request.files.get("source_file")
    config_name = request.form.get("config_name", "").strip()
    configs_dir = Path(current_app.config["CONFIGS_DIR"])
    available_configs = _list_config_names(configs_dir)

    if not config_name:
        return jsonify({"error": "Config YAML wajib dipilih."}), 400
    if config_name not in available_configs:
        return jsonify({"error": "Config YAML tidak ditemukan di folder configs/."}), 400
    if source_file is None or not source_file.filename:
        return jsonify({"error": "File source wajib dipilih."}), 400

    source_name = Path(source_file.filename).name
    source_extension = Path(source_name).suffix.casefold()
    if source_extension not in ALLOWED_SOURCE_EXTENSIONS:
        allowed_text = ", ".join(sorted(ALLOWED_SOURCE_EXTENSIONS))
        return jsonify({"error": f"Ekstensi file tidak didukung. Gunakan {allowed_text}."}), 400

    run_id = uuid4().hex[:8]
    now_iso = datetime.now(tz=UTC).isoformat()
    output_name = f"result-{run_id}.xlsx"

    logs = [
        {"time": now_iso, "level": "info", "message": "Validasi input selesai."},
        {"time": now_iso, "level": "info", "message": f"Config terpilih: {config_name}"},
        {"time": now_iso, "level": "info", "message": f"Source diterima: {source_name}"},
        {
            "time": now_iso,
            "level": "info",
            "message": "Fase 2 dry-run selesai. Engine transform penuh ada di fase berikutnya.",
        },
    ]

    return jsonify(
        {
            "status": "success",
            "mode": "dry-run",
            "run_id": run_id,
            "logs": logs,
            "result": {
                "file_name": output_name,
                "download_url": None,
                "download_ready": False,
            },
        }
    )
