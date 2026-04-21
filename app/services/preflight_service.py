from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from app import AppPaths
from app.services.config_service import is_step_recipe_payload, load_config_payload
from app.services.output_service import sanitize_sheet_name
from app.services.pipeline_types import PreflightFinding, PreflightResult
from app.services.source_service import (
    load_source_dataframe,
    validate_required_source_columns,
    validate_source_file,
)
from app.services.transform_service import resolve_master_path


_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(raw_name: str) -> str:
    normalized = _UNSAFE_FILENAME_CHARS.sub("_", raw_name.strip())
    normalized = normalized.strip("._")
    return normalized or "report"


def _make_finding(
    severity: str,
    code: str,
    summary: str,
    suggestion: str,
) -> PreflightFinding:
    return PreflightFinding(
        severity=severity,
        code=code,
        summary=summary,
        suggestion=suggestion,
    )


def _resolve_status(findings: list[PreflightFinding]) -> str:
    if any(item.severity == "ERROR" for item in findings):
        return "Blocked"
    if any(item.severity == "WARNING" for item in findings):
        return "Warning"
    return "Ready"


def _collect_master_refs(config: dict) -> list[str]:
    master_refs: list[str] = []
    if is_step_recipe_payload(config):
        for step_cfg in config.get("steps") or []:
            if not isinstance(step_cfg, dict):
                continue
            master_cfg = step_cfg.get("master")
            if not isinstance(master_cfg, dict):
                continue
            file_ref = master_cfg.get("file")
            if isinstance(file_ref, str) and file_ref not in master_refs:
                master_refs.append(file_ref)
        return master_refs

    for master_cfg in config.get("masters") or []:
        if not isinstance(master_cfg, dict):
            continue
        file_ref = master_cfg.get("file")
        if isinstance(file_ref, str) and file_ref not in master_refs:
            master_refs.append(file_ref)
    return master_refs


def _check_master_files(
    *,
    config: dict,
    paths: AppPaths,
    findings: list[PreflightFinding],
) -> None:
    for file_ref in _collect_master_refs(config):
        try:
            master_path = resolve_master_path(file_ref, paths.project_root, paths.masters_dir)
        except ValueError as exc:
            findings.append(
                _make_finding(
                    "ERROR",
                    "MASTER_PATH_INVALID",
                    f"Referensi master tidak valid: {file_ref}.",
                    f"Perbaiki path master pada config aktif. Detail: {exc}",
                )
            )
            continue

        if not master_path.exists() or not master_path.is_file():
            findings.append(
                _make_finding(
                    "ERROR",
                    "MASTER_FILE_MISSING",
                    f"File master tidak ditemukan: {file_ref}.",
                    "Pastikan file master tersedia di folder masters/ sesuai config aktif.",
                )
            )


def _check_output_sheet_names(config: dict, findings: list[PreflightFinding]) -> None:
    outputs = config.get("outputs") or []
    if not isinstance(outputs, list):
        return

    raw_names = [str(item.get("sheet_name", "")) for item in outputs if isinstance(item, dict)]
    used_names: set[str] = set()
    changes: list[str] = []
    for raw_name in raw_names:
        sanitized = sanitize_sheet_name(raw_name, used_names)
        if sanitized != raw_name:
            changes.append(f"'{raw_name}' -> '{sanitized}'")

    if changes:
        findings.append(
            _make_finding(
                "WARNING",
                "OUTPUT_SHEET_NAME_SANITIZED",
                "Sebagian nama sheet output akan disesuaikan agar valid dan unik.",
                "Periksa nama output pada config jika ingin hasil sheet lebih konsisten: "
                + "; ".join(changes[:3]),
            )
        )


def preview_output_path(paths: AppPaths, config: dict, config_path: Path) -> Path:
    config_name = str(config.get("name", config_path.stem))
    output_file_name = (
        f"{_safe_filename(config_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    return paths.outputs_dir / output_file_name


def _check_classic_compatibility(
    *,
    source_path: Path,
    config: dict,
    findings: list[PreflightFinding],
) -> None:
    source_sheet = config.get("source_sheet")
    try:
        source_df = load_source_dataframe(
            source_path,
            source_sheet=str(source_sheet) if source_path.suffix.lower() == ".xlsx" else None,
        )
    except ValueError as exc:
        findings.append(
            _make_finding(
                "ERROR",
                "SOURCE_READ_FAILED",
                "Source tidak cocok dengan config pekerjaan aktif.",
                f"Periksa sheet source dan format file, lalu coba lagi. Detail: {exc}",
            )
        )
        return

    try:
        validate_required_source_columns(source_df, config.get("required_source_columns"))
    except ValueError as exc:
        findings.append(
            _make_finding(
                "ERROR",
                "SOURCE_COLUMNS_MISSING",
                str(exc),
                "Lengkapi kolom wajib pada source atau sesuaikan required_source_columns di config.",
            )
        )
        return

    findings.append(
        _make_finding(
            "INFO",
            "CLASSIC_SOURCE_READY",
            "Source kompatibel dengan mode klasik untuk pemeriksaan minimum.",
            "Lanjutkan eksekusi bila hasil preflight lain juga aman.",
        )
    )


def _check_recipe_compatibility(
    *,
    source_path: Path,
    config: dict,
    findings: list[PreflightFinding],
) -> None:
    steps = config.get("steps") or []
    extract_steps = [
        step_cfg
        for step_cfg in steps
        if isinstance(step_cfg, dict) and str(step_cfg.get("type")) == "extract_sheet"
    ]

    if not extract_steps:
        findings.append(
            _make_finding(
                "WARNING",
                "RECIPE_NO_EXTRACT_STEP",
                "Recipe tidak memiliki step extract_sheet untuk diperiksa kompatibilitasnya.",
                "Pastikan struktur recipe memang sesuai dengan alur source yang digunakan.",
            )
        )
        return

    if source_path.suffix.lower() != ".xlsx":
        findings.append(
            _make_finding(
                "ERROR",
                "RECIPE_SOURCE_TYPE_UNSUPPORTED",
                "Recipe aktif memerlukan source workbook Excel (.xlsx).",
                "Gunakan source .xlsx yang sesuai atau pilih pekerjaan non-recipe.",
            )
        )
        return

    try:
        workbook = pd.ExcelFile(source_path)
    except Exception as exc:
        findings.append(
            _make_finding(
                "ERROR",
                "RECIPE_SOURCE_READ_FAILED",
                "Source workbook untuk recipe tidak bisa dibaca.",
                f"Pastikan file Excel tidak rusak dan tidak sedang bermasalah. Detail: {exc}",
            )
        )
        return

    for step_cfg in extract_steps:
        step_id = str(step_cfg.get("id", "extract_sheet"))
        selector_cfg = step_cfg.get("sheet_selector")
        if not isinstance(selector_cfg, dict) or not isinstance(selector_cfg.get("contains"), str):
            findings.append(
                _make_finding(
                    "WARNING",
                    "RECIPE_SELECTOR_UNCHECKED",
                    f"Selector sheet pada step '{step_id}' belum bisa diperiksa otomatis.",
                    "Pastikan sheet_selector.contains pada recipe terisi dengan benar.",
                )
            )
            continue

        contains = str(selector_cfg["contains"])
        case_sensitive = bool(selector_cfg.get("case_sensitive", False))
        candidates = [
            sheet_name
            for sheet_name in workbook.sheet_names
            if (
                contains in sheet_name
                if case_sensitive
                else contains.casefold() in sheet_name.casefold()
            )
        ]
        if not candidates:
            findings.append(
                _make_finding(
                    "ERROR",
                    "RECIPE_SHEET_NOT_FOUND",
                    f"Sheet kandidat untuk step '{step_id}' tidak ditemukan.",
                    f"Pastikan source memiliki sheet yang mengandung '{contains}'.",
                )
            )
            continue

        findings.append(
            _make_finding(
                "INFO",
                "RECIPE_SHEET_CANDIDATE_FOUND",
                f"Step '{step_id}' menemukan {len(candidates)} kandidat sheet.",
                "Pemeriksaan ini minimum; validasi header penuh tetap dilakukan saat execute.",
            )
        )


def run_preflight(
    *,
    paths: AppPaths,
    source_path: Path,
    config_path: Path,
) -> PreflightResult:
    findings: list[PreflightFinding] = []

    source_errors = validate_source_file(source_path)
    if source_errors:
        for error_message in source_errors:
            findings.append(
                _make_finding(
                    "ERROR",
                    "SOURCE_INVALID",
                    error_message,
                    "Pilih file source .xlsx/.csv yang valid lalu jalankan pemeriksaan lagi.",
                )
            )
        return PreflightResult(status="Blocked", findings=tuple(findings), output_path=None)

    try:
        config = load_config_payload(config_path)
    except ValueError as exc:
        findings.append(
            _make_finding(
                "ERROR",
                "CONFIG_INVALID",
                "Config pekerjaan aktif tidak valid atau tidak bisa dibaca.",
                f"Periksa config/job aktif lalu coba lagi. Detail: {exc}",
            )
        )
        return PreflightResult(status="Blocked", findings=tuple(findings), output_path=None)

    output_path = preview_output_path(paths, config, config_path)
    findings.append(
        _make_finding(
            "INFO",
            "OUTPUT_TARGET_READY",
            f"Target output dapat dihitung: {output_path.name}.",
            "Pastikan file hasil nanti disimpan dari folder outputs/ bila diperlukan.",
        )
    )

    _check_master_files(config=config, paths=paths, findings=findings)
    _check_output_sheet_names(config, findings)

    if is_step_recipe_payload(config):
        _check_recipe_compatibility(source_path=source_path, config=config, findings=findings)
    else:
        _check_classic_compatibility(source_path=source_path, config=config, findings=findings)

    return PreflightResult(
        status=_resolve_status(findings),
        findings=tuple(findings),
        output_path=output_path,
    )
