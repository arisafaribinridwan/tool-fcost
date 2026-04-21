from __future__ import annotations

from pathlib import Path, PurePosixPath


def normalize_relative_path_string(raw_path: str) -> str:
    normalized = raw_path.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("Path tidak boleh kosong.")

    if normalized.startswith(("/", "\\")):
        raise ValueError("Path harus relatif, bukan absolute path.")

    if len(normalized) >= 2 and normalized[1] == ":" and normalized[0].isalpha():
        raise ValueError("Path harus relatif, bukan drive path Windows.")

    parts = PurePosixPath(normalized).parts
    if not parts:
        raise ValueError("Path tidak boleh kosong.")
    if any(part in {".", ".."} for part in parts):
        raise ValueError("Path tidak boleh mengandung '.' atau '..'.")

    return str(PurePosixPath(*parts))


def validate_runtime_relative_path(raw_path: str, *, root_name: str) -> str:
    normalized = normalize_relative_path_string(raw_path)
    parts = normalized.split("/")
    if parts[0].casefold() != root_name.casefold():
        raise ValueError(f"Path wajib berada di bawah folder {root_name}/.")
    return normalized


def resolve_casefold_relative_path(base_dir: Path, relative_path: str) -> Path:
    current = base_dir.resolve()
    for part in normalize_relative_path_string(relative_path).split("/"):
        candidate = current / part
        if candidate.exists():
            current = candidate
            continue

        matches = [child for child in current.iterdir() if child.name.casefold() == part.casefold()]
        if len(matches) > 1:
            raise ValueError(f"Path ambigu karena lebih dari satu nama cocok untuk '{part}'.")
        if matches:
            current = matches[0]
            continue
        current = candidate
    return current


def resolve_runtime_relative_path(base_dir: Path, relative_path: str, *, root_name: str) -> Path:
    normalized = validate_runtime_relative_path(relative_path, root_name=root_name)
    resolved = resolve_casefold_relative_path(base_dir, normalized).resolve()
    runtime_root = (base_dir.resolve() / root_name).resolve()
    if not resolved.is_relative_to(runtime_root):
        raise ValueError(f"Path tidak aman: '{relative_path}'. File wajib berada di folder {root_name}/.")
    return resolved
