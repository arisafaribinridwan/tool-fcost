from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    configs_dir: Path
    masters_dir: Path
    uploads_dir: Path
    outputs_dir: Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_runtime_root(project_root: Path | None = None) -> Path:
    if project_root is not None:
        return project_root
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return get_project_root()


def get_app_paths(project_root: Path | None = None) -> AppPaths:
    root = get_runtime_root(project_root)
    return AppPaths(
        project_root=root,
        configs_dir=root / "configs",
        masters_dir=root / "masters",
        uploads_dir=root / "uploads",
        outputs_dir=root / "outputs",
    )


def ensure_runtime_dirs(paths: AppPaths | None = None) -> AppPaths:
    app_paths = paths or get_app_paths()
    for directory in (
        app_paths.configs_dir,
        app_paths.masters_dir,
        app_paths.uploads_dir,
        app_paths.outputs_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    return app_paths


__all__ = [
    "AppPaths",
    "ensure_runtime_dirs",
    "get_app_paths",
    "get_project_root",
    "get_runtime_root",
]
