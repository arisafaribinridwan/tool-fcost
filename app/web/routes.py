from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    return render_template("index.html", app_name=current_app.config["APP_NAME"])


@web_bp.get("/health")
def health():
    return jsonify({"status": "ok"})
