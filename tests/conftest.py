from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path):
    runtime_dirs = {
        "CONFIGS_DIR": tmp_path / "configs",
        "MASTERS_DIR": tmp_path / "masters",
        "UPLOADS_DIR": tmp_path / "uploads",
        "OUTPUTS_DIR": tmp_path / "outputs",
    }
    return create_app({"TESTING": True, **runtime_dirs})


@pytest.fixture()
def client(app):
    return app.test_client()
