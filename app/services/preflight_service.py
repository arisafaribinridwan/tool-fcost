from __future__ import annotations

from pathlib import Path

from app import AppPaths
from app.services.config_service import load_config_payload
from app.services.pipeline_types import PreflightFinding, PreflightResult
from app.services.source_service import validate_source_file
from app.utils.path_safety import resolve_runtime_relative_path


def _extract_master_refs(payload: dict) -> tuple[str, ...]:
    refs: list[str] = []

    for master_cfg in payload.get("masters") or []:
        if not isinstance(master_cfg, dict):
            continue
        raw_file = master_cfg.get("file")
        if isinstance(raw_file, str) and raw_file not in refs:
            refs.append(raw_file)

    for step_cfg in payload.get("steps") or []:
        if not isinstance(step_cfg, dict):
            continue
        master_cfg = step_cfg.get("master")
        if not isinstance(master_cfg, dict):
            continue
        raw_file = master_cfg.get("file")
        if isinstance(raw_file, str) and raw_file not in refs:
            refs.append(raw_file)

    return tuple(refs)


def get_config_master_refs(config_path: Path) -> tuple[str, ...]:
    payload = load_config_payload(config_path)
    return _extract_master_refs(payload)


def run_settings_precheck(
    *,
    paths: AppPaths,
    config_path: Path,
) -> PreflightResult:
    findings: list[PreflightFinding] = []
    payload = None

    try:
        payload = load_config_payload(config_path)
    except ValueError as exc:
        findings.append(PreflightFinding(severity="error", summary=str(exc)))

    if payload is not None:
        for master_ref in _extract_master_refs(payload):
            try:
                master_path = resolve_runtime_relative_path(
                    paths.project_root,
                    master_ref,
                    root_name="masters",
                )
            except ValueError as exc:
                findings.append(PreflightFinding(severity="error", summary=f"Master tidak valid: {exc}"))
                continue

            if not master_path.exists():
                findings.append(
                    PreflightFinding(
                        severity="error",
                        summary=f"File master tidak ditemukan: {master_ref}",
                    )
                )
                continue

            if not master_path.is_file():
                findings.append(
                    PreflightFinding(
                        severity="error",
                        summary=f"Path master harus berupa file: {master_ref}",
                    )
                )
                continue

            if master_path.suffix.lower() not in {".csv", ".xlsx"}:
                findings.append(
                    PreflightFinding(
                        severity="error",
                        summary=f"Ekstensi master tidak didukung: {master_ref}",
                    )
                )

    status = "Blocked" if any(item.severity == "error" for item in findings) else "Ready"
    return PreflightResult(status=status, findings=tuple(findings), output_path=None)


def run_preflight(
    *,
    paths: AppPaths,
    source_path: Path,
    config_path: Path,
) -> PreflightResult:
    findings: list[PreflightFinding] = []

    for error in validate_source_file(source_path):
        findings.append(PreflightFinding(severity="error", summary=error))

    try:
        load_config_payload(config_path)
    except ValueError as exc:
        findings.append(PreflightFinding(severity="error", summary=str(exc)))

    status = "Blocked" if any(item.severity == "error" for item in findings) else "Ready"
    return PreflightResult(status=status, findings=tuple(findings), output_path=None)
