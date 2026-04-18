from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.runtime_info import get_build_info, get_stale_bundle_warning


def _git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def test_get_build_info_reads_bundle_metadata(monkeypatch, tmp_path):
    runtime_root = tmp_path / "dist" / "ExcelAutoTool"
    runtime_root.mkdir(parents=True)
    (runtime_root / "build-info.json").write_text(
        (
            '{'
            '"mode":"bundle",'
            '"commit":"abc123456789",'
            '"built_at":"2026-04-18T06:00:00Z",'
            '"dirty":false,'
            '"python":"/usr/bin/python3.12"'
            '}'
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    info = get_build_info(runtime_root)

    assert info.mode == "bundle"
    assert info.commit == "abc123456789"
    assert info.built_at == "2026-04-18T06:00:00Z"
    assert info.dirty is False


def test_get_stale_bundle_warning_detects_commit_mismatch(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    runtime_root = repo_root / "dist" / "ExcelAutoTool"
    runtime_root.mkdir(parents=True)
    (repo_root / ".git").mkdir()
    (runtime_root / "build-info.json").write_text(
        (
            '{'
            '"mode":"bundle",'
            '"commit":"oldcommit",'
            '"built_at":"2026-04-18T06:00:00Z",'
            '"dirty":false,'
            '"python":"/usr/bin/python3.12"'
            '}'
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    def fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool):
        class Result:
            stdout = "newcommit\n"

        assert cmd[:3] == ["git", "-C", str(repo_root)]
        assert cmd[3:] == ["rev-parse", "HEAD"]
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)

    warning = get_stale_bundle_warning(runtime_root)

    assert warning is not None
    assert "stale" in warning
    assert "oldcomm" in warning
    assert "newcomm" in warning


def test_get_stale_bundle_warning_detects_newer_dirty_sources(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    runtime_root = repo_root / "dist" / "ExcelAutoTool"
    app_dir = repo_root / "app"
    app_dir.mkdir(parents=True)
    runtime_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".git").mkdir()

    executable = runtime_root / "ExcelAutoTool"
    executable.write_text("binary", encoding="utf-8")
    build_info = runtime_root / "build-info.json"
    build_info.write_text(
        (
            '{'
            '"mode":"bundle",'
            '"commit":"samecommit",'
            '"built_at":"2026-04-18T06:00:00Z",'
            '"dirty":false,'
            '"python":"/usr/bin/python3.12"'
            '}'
        ),
        encoding="utf-8",
    )
    source_file = app_dir / "services.py"
    source_file.write_text("print('new')\n", encoding="utf-8")
    executable.touch()
    exec_mtime = executable.stat().st_mtime
    os.utime(source_file, (exec_mtime + 5, exec_mtime + 5))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable), raising=False)

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool, capture_output: bool, text: bool):
        calls.append(cmd)

        class Result:
            stdout = ""

        if cmd[3:] == ["rev-parse", "HEAD"]:
            Result.stdout = "samecommit\n"
        elif cmd[3:] == ["status", "--porcelain", "--untracked-files=no"]:
            Result.stdout = " M app/services.py\n"
        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)

    warning = get_stale_bundle_warning(runtime_root)

    assert warning is not None
    assert "lebih lama" in warning
