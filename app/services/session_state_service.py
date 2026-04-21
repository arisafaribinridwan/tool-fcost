from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re


SESSION_STATE_VERSION = 1
_GEOMETRY_PATTERN = re.compile(r"^\d+x\d+(?:[+-]\d+[+-]\d+)?$")


@dataclass(frozen=True)
class SessionState:
    version: int
    last_job_id: str | None
    last_source_path: Path | None
    window_geometry: str | None
    updated_at: str


def get_session_state_path(runtime_root: Path) -> Path:
    return runtime_root / ".app_state" / "session_state.json"


def load_session_state(runtime_root: Path) -> SessionState | None:
    state_path = get_session_state_path(runtime_root)
    if not state_path.exists():
        return None

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    version = payload.get("version")
    if not isinstance(version, int) or version < 1:
        return None

    updated_at = payload.get("updated_at")
    if not isinstance(updated_at, str) or not updated_at.strip():
        return None

    last_job_id = payload.get("last_job_id")
    if not isinstance(last_job_id, str) or not last_job_id.strip():
        last_job_id = None

    last_source_path_raw = payload.get("last_source_path")
    last_source_path = None
    if isinstance(last_source_path_raw, str) and last_source_path_raw.strip():
        last_source_path = Path(last_source_path_raw)

    window_geometry = payload.get("window_geometry")
    if not isinstance(window_geometry, str) or not is_valid_window_geometry(window_geometry):
        window_geometry = None

    return SessionState(
        version=version,
        last_job_id=last_job_id,
        last_source_path=last_source_path,
        window_geometry=window_geometry,
        updated_at=updated_at,
    )


def save_session_state(
    runtime_root: Path,
    *,
    last_job_id: str | None,
    last_source_path: Path | None,
    window_geometry: str | None,
) -> SessionState:
    state = SessionState(
        version=SESSION_STATE_VERSION,
        last_job_id=last_job_id.strip() if isinstance(last_job_id, str) and last_job_id.strip() else None,
        last_source_path=last_source_path,
        window_geometry=window_geometry if is_valid_window_geometry(window_geometry) else None,
        updated_at=datetime.now().isoformat(timespec="seconds"),
    )

    state_path = get_session_state_path(runtime_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": state.version,
        "last_job_id": state.last_job_id,
        "last_source_path": str(state.last_source_path) if state.last_source_path is not None else None,
        "window_geometry": state.window_geometry,
        "updated_at": state.updated_at,
    }
    state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return state


def clear_session_state(runtime_root: Path) -> None:
    state_path = get_session_state_path(runtime_root)
    try:
        state_path.unlink()
    except FileNotFoundError:
        return


def is_valid_window_geometry(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    return bool(_GEOMETRY_PATTERN.fullmatch(value.strip()))
