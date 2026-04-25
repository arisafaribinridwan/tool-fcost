from __future__ import annotations

from pathlib import Path
import shutil


_CONFIG_SUFFIXES = {".yaml", ".yml"}
_MASTER_SUFFIXES = {".csv", ".xlsx"}
_RESERVED_CONFIG_NAMES = {"job_profiles.yaml"}


def _ensure_existing_file(path: Path, *, kind: str) -> None:
    if not path.exists():
        raise ValueError(f"File {kind} tidak ditemukan.")
    if not path.is_file():
        raise ValueError(f"Path {kind} harus berupa file.")


def _copy_with_suffix_on_collision(source_path: Path, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    stem = source_path.stem
    suffix = source_path.suffix.lower()

    candidate = target_dir / f"{stem}{suffix}"
    index = 2
    while candidate.exists():
        candidate = target_dir / f"{stem}-{index}{suffix}"
        index += 1

    shutil.copy2(source_path, candidate)
    return candidate


def import_config_to_configs(source_path: Path, configs_dir: Path) -> Path:
    _ensure_existing_file(source_path, kind="config")

    suffix = source_path.suffix.lower()
    if suffix not in _CONFIG_SUFFIXES:
        raise ValueError("Ekstensi config hanya mendukung .yaml atau .yml.")

    if source_path.name.casefold() in _RESERVED_CONFIG_NAMES:
        raise ValueError("Nama file config tidak valid: job_profiles.yaml adalah file registry internal.")

    return _copy_with_suffix_on_collision(source_path, configs_dir)


def import_master_to_masters(source_path: Path, masters_dir: Path) -> Path:
    _ensure_existing_file(source_path, kind="master")

    suffix = source_path.suffix.lower()
    if suffix not in _MASTER_SUFFIXES:
        raise ValueError("Ekstensi master hanya mendukung .csv atau .xlsx.")

    return _copy_with_suffix_on_collision(source_path, masters_dir)


__all__ = [
    "import_config_to_configs",
    "import_master_to_masters",
]
