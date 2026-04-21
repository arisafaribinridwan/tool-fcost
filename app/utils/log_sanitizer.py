from __future__ import annotations

from pathlib import Path
import re


MAX_LOG_LENGTH = 400
_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]{1,64})@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_LONG_NUMBER_RE = re.compile(r"\b\d{8,}\b")
_ABSOLUTE_PATH_RE = re.compile(
    r"(?P<path>(?:[A-Za-z]:[\\/]|/[A-Za-z0-9._-]+/)[^\s\r\n\t'\"<>|]*)"
)


def _mask_email(match: re.Match[str]) -> str:
    local_part = match.group(1)
    domain = match.group(2)
    if len(local_part) <= 2:
        masked_local = local_part[0] + "*" * max(0, len(local_part) - 1)
    else:
        masked_local = local_part[:2] + "***"
    return f"{masked_local}@{domain}"


def _mask_long_number(match: re.Match[str]) -> str:
    value = match.group(0)
    visible = value[-4:]
    return "*" * (len(value) - 4) + visible


def _sanitize_path_token(raw_path: str, project_root: Path | None) -> str:
    cleaned = raw_path.rstrip(".,:;)")
    suffix = raw_path[len(cleaned) :]
    try:
        candidate = Path(cleaned)
    except ValueError:
        return raw_path

    if project_root is not None:
        try:
            relative = candidate.resolve().relative_to(project_root.resolve())
            return f"<{relative.as_posix()}>" + suffix
        except (OSError, ValueError):
            pass

    parts = candidate.parts
    if len(parts) >= 2:
        tail = "/".join(str(part).replace("\\", "/") for part in parts[-2:])
        return f"<.../{tail}>" + suffix
    return "<path>" + suffix


def _sanitize_paths(message: str, project_root: Path | None) -> str:
    def replacer(match: re.Match[str]) -> str:
        raw_path = match.group("path")
        return _sanitize_path_token(raw_path, project_root)

    return _ABSOLUTE_PATH_RE.sub(replacer, message)


def _truncate_message(message: str) -> str:
    compact = re.sub(r"\s+", " ", message).strip()
    if len(compact) <= MAX_LOG_LENGTH:
        return compact
    return compact[: MAX_LOG_LENGTH - 19].rstrip() + "... [dipotong]"


def sanitize_log_message(message: str, *, project_root: Path | None = None) -> str:
    sanitized = _sanitize_paths(str(message), project_root)
    sanitized = _EMAIL_RE.sub(_mask_email, sanitized)
    sanitized = _LONG_NUMBER_RE.sub(_mask_long_number, sanitized)
    return _truncate_message(sanitized)


def sanitize_exception_message(message: str, *, project_root: Path | None = None) -> str:
    return sanitize_log_message(message, project_root=project_root)
