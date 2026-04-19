from __future__ import annotations

from pathlib import Path
import subprocess

from app.utils import os_utils


def test_select_source_file_linux_uses_kdialog_first(monkeypatch, tmp_path):
    initialdir = tmp_path

    monkeypatch.setattr(os_utils.platform, "system", lambda: "Linux")
    monkeypatch.setattr(os_utils, "_select_source_file_linux", lambda _: "/tmp/source.csv")

    called = {"fallback": False}

    def fake_askopenfilename(**_: object) -> str:
        called["fallback"] = True
        return ""

    monkeypatch.setattr(os_utils.filedialog, "askopenfilename", fake_askopenfilename)

    result = os_utils.select_source_file(initialdir)

    assert result == "/tmp/source.csv"
    assert called["fallback"] is False


def test_select_source_file_linux_falls_back_to_tk(monkeypatch, tmp_path):
    initialdir = tmp_path

    monkeypatch.setattr(os_utils.platform, "system", lambda: "Linux")
    monkeypatch.setattr(os_utils, "_select_source_file_linux", lambda _: "")
    monkeypatch.setattr(
        os_utils.filedialog,
        "askopenfilename",
        lambda **_: "/home/user/fallback.xlsx",
    )

    result = os_utils.select_source_file(initialdir)

    assert result == "/home/user/fallback.xlsx"


def test_select_source_file_non_linux_uses_tk_directly(monkeypatch, tmp_path):
    initialdir = tmp_path

    monkeypatch.setattr(os_utils.platform, "system", lambda: "Windows")

    called = {"linux": False}

    def fake_linux(_: Path) -> str:
        called["linux"] = True
        return ""

    monkeypatch.setattr(os_utils, "_select_source_file_linux", fake_linux)
    monkeypatch.setattr(
        os_utils.filedialog,
        "askopenfilename",
        lambda **_: "C:/temp/source.csv",
    )

    result = os_utils.select_source_file(initialdir)

    assert result == "C:/temp/source.csv"
    assert called["linux"] is False


def test_select_source_file_linux_prefers_zenity_when_kdialog_missing(monkeypatch, tmp_path):
    initialdir = tmp_path

    monkeypatch.setattr(os_utils, "_is_command_available", lambda cmd: cmd == "zenity")

    commands: list[list[str]] = []

    def fake_run(command: list[str], check: bool, capture_output: bool, text: bool):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="/tmp/selected.csv\n", stderr="")

    monkeypatch.setattr(os_utils.subprocess, "run", fake_run)

    result = os_utils._select_source_file_linux(initialdir)

    assert result == "/tmp/selected.csv"
    assert commands and commands[0][0] == "zenity"


def test_select_source_file_linux_returns_empty_when_helpers_fail(monkeypatch, tmp_path):
    initialdir = tmp_path

    monkeypatch.setattr(os_utils, "_is_command_available", lambda _: True)

    def fake_run(command: list[str], check: bool, capture_output: bool, text: bool):
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="cancel")

    monkeypatch.setattr(os_utils.subprocess, "run", fake_run)

    result = os_utils._select_source_file_linux(initialdir)

    assert result == ""


def test_run_dialog_command_handles_oserror(monkeypatch):
    def fake_run(command: list[str], check: bool, capture_output: bool, text: bool):
        raise OSError("missing binary")

    monkeypatch.setattr(os_utils.subprocess, "run", fake_run)

    result = os_utils._run_dialog_command(["kdialog", "--getopenfilename"])

    assert result == ""
