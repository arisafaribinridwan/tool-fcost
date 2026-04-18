from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys

from app import get_project_root, get_runtime_root


@dataclass(frozen=True)
class BuildInfo:
    mode: str
    commit: str | None
    built_at: str | None
    dirty: bool | None
    python: str | None

    def summary(self) -> str:
        parts = [f"mode={self.mode}"]
        if self.commit:
            parts.append(f"commit={self.commit[:7]}")
        if self.built_at:
            parts.append(f"built_at={self.built_at}")
        if self.dirty is not None:
            parts.append(f"dirty={'yes' if self.dirty else 'no'}")
        return ", ".join(parts)


def _run_git(repo_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _repo_has_newer_runtime_sources(repo_root: Path, executable_path: Path) -> bool:
    executable_mtime = executable_path.stat().st_mtime
    candidates: list[Path] = []
    run_entry = repo_root / "run.py"
    if run_entry.exists():
        candidates.append(run_entry)
    for directory in ("app", "configs"):
        base = repo_root / directory
        if base.exists():
            candidates.extend(path for path in base.rglob("*") if path.is_file())

    for path in candidates:
        if path.stat().st_mtime > executable_mtime:
            return True
    return False


def _load_build_info_file(runtime_root: Path) -> BuildInfo | None:
    candidates = [
        runtime_root / "build-info.json",
        runtime_root / "_internal" / "build-info.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return BuildInfo(
            mode=str(payload.get("mode", "bundle")),
            commit=str(payload["commit"]) if payload.get("commit") else None,
            built_at=str(payload["built_at"]) if payload.get("built_at") else None,
            dirty=bool(payload["dirty"]) if payload.get("dirty") is not None else None,
            python=str(payload["python"]) if payload.get("python") else None,
        )
    return None


def get_build_info(runtime_root: Path | None = None) -> BuildInfo:
    root = runtime_root or get_runtime_root()
    if getattr(sys, "frozen", False):
        bundle_info = _load_build_info_file(root)
        if bundle_info is not None:
            return bundle_info
        return BuildInfo(mode="bundle", commit=None, built_at=None, dirty=None, python=None)

    repo_root = get_project_root()
    commit = _run_git(repo_root, "rev-parse", "HEAD")
    dirty = _run_git(repo_root, "status", "--porcelain")
    return BuildInfo(
        mode="source",
        commit=commit,
        built_at=None,
        dirty=bool(dirty) if dirty is not None else None,
        python=sys.executable,
    )


def get_stale_bundle_warning(runtime_root: Path | None = None) -> str | None:
    if not getattr(sys, "frozen", False):
        return None

    root = runtime_root or get_runtime_root()
    bundle_info = get_build_info(root)
    repo_root = root.parent.parent
    if not (repo_root / ".git").exists():
        return None

    current_commit = _run_git(repo_root, "rev-parse", "HEAD")
    if current_commit is None:
        return None

    if bundle_info.commit and bundle_info.commit != current_commit:
        return (
            "Bundle Linux yang sedang dijalankan sudah stale terhadap source repo ini. "
            f"Bundle commit={bundle_info.commit[:7]}, source commit={current_commit[:7]}. "
            "Jalankan ulang ./packaging/linux/build.sh sebelum test manual."
        )

    repo_dirty = _run_git(repo_root, "status", "--porcelain", "--untracked-files=no")
    executable_path = Path(sys.executable).resolve()
    if repo_dirty and _repo_has_newer_runtime_sources(repo_root, executable_path):
        return (
            "Bundle Linux yang sedang dijalankan lebih lama daripada perubahan source/config "
            "di repo ini. Jalankan ulang ./packaging/linux/build.sh sebelum test manual."
        )

    return None


__all__ = ["BuildInfo", "get_build_info", "get_stale_bundle_warning"]
