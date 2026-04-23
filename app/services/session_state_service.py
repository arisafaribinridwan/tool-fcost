from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


SESSION_STATE_DIR_NAME = ".app_state"
SESSION_STATE_FILE_NAME = "session_state.json"


@dataclass(frozen=True)
class SessionState:
    version: int
    last_job_id: str | None
    last_source_path: Path | None
    window_geometry: str | None
    updated_at: str


def _get_session_state_path(runtime_root: Path) -> Path:
    return runtime_root / SESSION_STATE_DIR_NAME / SESSION_STATE_FILE_NAME


def load_session_state(runtime_root: Path) -> SessionState | None:
    path = _get_session_state_path(runtime_root)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    last_source_path = payload.get("last_source_path")
    return SessionState(
        version=int(payload.get("version", 1)),
        last_job_id=payload.get("last_job_id") if isinstance(payload.get("last_job_id"), str) else None,
        last_source_path=Path(last_source_path) if isinstance(last_source_path, str) and last_source_path else None,
        window_geometry=payload.get("window_geometry") if isinstance(payload.get("window_geometry"), str) else None,
        updated_at=str(payload.get("updated_at", "")),
    )


def save_session_state(
    runtime_root: Path,
    *,
    last_job_id: str | None,
    last_source_path: Path | None,
    window_geometry: str | None,
) -> Path:
    path = _get_session_state_path(runtime_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "last_job_id": last_job_id,
        "last_source_path": str(last_source_path) if last_source_path is not None else None,
        "window_geometry": window_geometry,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def clear_session_state(runtime_root: Path) -> None:
    path = _get_session_state_path(runtime_root)
    try:
        path.unlink()
    except FileNotFoundError:
        return
