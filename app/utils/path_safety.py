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
