# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development commands

### Environment setup

The project currently targets Python 3.14.x.

Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

On Linux desktop/build machines, the Python used to run or package the app must include Tk/Tcl support, typically via `python3-tk`. Optional native file dialogs use `zenity` or `kdialog` when available.

### Run, lint, and test

```bash
python run.py
python -m ruff check .
python -m pytest -q
python -m pytest tests/test_pipeline_service.py -q
python -m pytest tests/test_pipeline_service.py::test_name_here -q
```

The settings window can also be launched directly:

```bash
python -m app.ui.settings
```

CI runs `python -m ruff check .` and `python -m pytest -q` on Python 3.14, then builds and smoke-tests the Linux bundle.

### Packaging

Builds must be performed on the target OS; do not rely on PyInstaller cross-builds.

Windows:

```powershell
.\packaging\windows\build.ps1
.\packaging\windows\build.ps1 -PythonExe "C:\Path\To\python.exe"
```

Linux:

```bash
sudo apt-get update
sudo apt-get install -y python3-tk python3.12-venv zenity kdialog
./packaging/linux/bootstrap-build-env.sh
./packaging/linux/build.sh
./packaging/linux/smoke-test.sh
```

The Linux build emits `dist/ExcelAutoTool/` and `dist/ExcelAutoTool-linux-x86_64.tar.gz`; the Windows build emits `dist\ExcelAutoTool\`.

## Architecture overview

This is a desktop Excel automation app built with CustomTkinter, pandas, openpyxl, and PyYAML. `run.py` creates runtime directories and starts the desktop UI via `app.ui.run_desktop_app()`.

Runtime paths are centralized in `app/__init__.py` with `AppPaths`. Source mode uses the repository root; PyInstaller bundle mode uses the executable directory. The important runtime folders are `configs/`, `masters/`, `uploads/`, and `outputs/`.

The UI layer lives in `app/ui/`:

- `main_window.py` is the primary workflow: select source, choose job profile, run preflight, execute pipeline on a worker thread, and stream logs back to the UI queue.
- `settings.py` manages job profiles and imports configs/masters. It persists job registry data through service-layer functions rather than directly mutating UI state only.

The service layer in `app/services/` owns business logic and file processing:

- `job_profile_service.py` reads and writes `configs/job_profiles.yaml`; enabled valid jobs populate the main UI dropdown.
- `config_service.py` loads and validates YAML configs. It supports both legacy configs with `source_sheet`, `header`, and `outputs`, and step recipes identified by root `steps` plus `datasets`.
- `preflight_service.py` validates source/config readiness and referenced master files before execution.
- `pipeline_service.py` orchestrates validation, source copy, source loading, transforms/recipe execution, output workbook generation, and progress events.
- `recipe_service.py` executes step-based recipes such as `configs/monthly-report-recipe.yaml`, including sheet extraction, derived columns, lookups, duplicate group rewrites, and range mapping.
- `transform_service.py` implements the legacy config transform engine: master lookups, conditional/filter/formula transforms, grouped/pivot/summary outputs, and symptom rule matching.
- `output_service.py` writes styled `.xlsx` workbooks, sanitizes sheet names, applies headers/period text, supports standard/plain sheet layouts, and enforces that outputs stay under `outputs/`.
- `source_service.py` accepts `.xlsx` and `.csv` sources, validates them, reads tabular data, and copies external sources into `uploads/` with a timestamped filename.

The canonical FCOST-style jobs are registered in `configs/job_profiles.yaml` and currently point at YAML configs in `configs/`. Step recipe YAMLs reference `masters/master_table.xlsx` sheets for lookups. The documentation copy of the monthly recipe is in `docs/monthly-report-recipe.yaml`; runtime configs live under `configs/`.

Path handling is deliberately constrained for runtime files. Config files must be inside `configs/`, master files inside `masters/`, and generated workbooks inside `outputs/`; use the existing path-safety helpers rather than string-concatenating paths. Keep paths cross-platform with `pathlib`/`os.path` and preserve filename case for Linux compatibility.

Tests are pytest-based and generally create isolated `AppPaths` from `tmp_path` via `tests/conftest.py`, so service tests should avoid relying on repository runtime folders unless the test is explicitly about bundled/configured assets.
