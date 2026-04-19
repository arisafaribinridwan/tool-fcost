from __future__ import annotations

import os
from pathlib import Path
import platform
import shutil
import subprocess
from tkinter import filedialog


def open_in_file_manager(path: Path) -> None:
    if not path.exists():
        raise RuntimeError(f"Path tidak ditemukan: {path}")

    system_name = platform.system().lower()
    try:
        if system_name == "windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif system_name == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError as exc:
        raise RuntimeError(f"Gagal membuka path: {path}") from exc


def select_source_file(initialdir: Path) -> str:
    if platform.system().lower() == "linux":
        linux_selection = _select_source_file_linux(initialdir)
        if linux_selection:
            return linux_selection

    return filedialog.askopenfilename(
        title="Pilih file source",
        initialdir=str(initialdir),
        filetypes=[
            ("Excel/CSV", "*.xlsx *.csv"),
            ("Excel", "*.xlsx"),
            ("CSV", "*.csv"),
            ("All Files", "*.*"),
        ],
    )


def _select_source_file_linux(initialdir: Path) -> str:
    selection = _select_with_kdialog(initialdir)
    if selection:
        return selection

    selection = _select_with_zenity(initialdir)
    if selection:
        return selection

    return ""


def _select_with_kdialog(initialdir: Path) -> str:
    if not _is_command_available("kdialog"):
        return ""

    return _run_dialog_command(
        [
            "kdialog",
            "--title",
            "Pilih file source",
            "--getopenfilename",
            str(initialdir),
            "Excel/CSV files (*.xlsx *.csv)\nExcel files (*.xlsx)\nCSV files (*.csv)\nAll files (*)",
        ]
    )


def _select_with_zenity(initialdir: Path) -> str:
    if not _is_command_available("zenity"):
        return ""

    initialdir_with_sep = f"{initialdir}/"
    return _run_dialog_command(
        [
            "zenity",
            "--file-selection",
            "--title=Pilih file source",
            f"--filename={initialdir_with_sep}",
            "--file-filter=Excel/CSV files | *.xlsx *.csv",
            "--file-filter=Excel files | *.xlsx",
            "--file-filter=CSV files | *.csv",
            "--file-filter=All files | *",
        ]
    )


def _is_command_available(command: str) -> bool:
    return shutil.which(command) is not None


def _run_dialog_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError:
        return ""

    if result.returncode != 0:
        return ""

    output = result.stdout.strip()
    if not output:
        return ""

    return output.splitlines()[0].strip()
