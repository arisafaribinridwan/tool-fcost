from __future__ import annotations

import json

from app.services.session_state_service import (
    get_session_state_path,
    load_session_state,
    save_session_state,
)


def test_load_session_state_returns_none_when_missing(tmp_path):
    assert load_session_state(tmp_path) is None


def test_load_session_state_returns_none_for_invalid_json(tmp_path):
    state_path = get_session_state_path(tmp_path)
    state_path.parent.mkdir(parents=True)
    state_path.write_text("{invalid", encoding="utf-8")

    assert load_session_state(tmp_path) is None


def test_save_and_load_session_state_roundtrip(tmp_path):
    saved = save_session_state(
        tmp_path,
        last_job_id="report-bulanan",
        last_source_path=tmp_path / "source.xlsx",
        window_geometry="1120x720+100+80",
    )

    loaded = load_session_state(tmp_path)

    assert loaded == saved
    payload = json.loads(get_session_state_path(tmp_path).read_text(encoding="utf-8"))
    assert payload["last_job_id"] == "report-bulanan"
    assert payload["last_source_path"].endswith("source.xlsx")


def test_load_session_state_ignores_invalid_geometry(tmp_path):
    state_path = get_session_state_path(tmp_path)
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "version": 1,
                "last_job_id": "report-bulanan",
                "last_source_path": str(tmp_path / "source.xlsx"),
                "window_geometry": "invalid",
                "updated_at": "2026-04-22T09:10:11",
            }
        ),
        encoding="utf-8",
    )

    loaded = load_session_state(tmp_path)

    assert loaded is not None
    assert loaded.window_geometry is None
