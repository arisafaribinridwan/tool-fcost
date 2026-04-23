from __future__ import annotations

from pathlib import Path

from app import AppPaths
from app.services.config_service import load_config_payload
from app.services.pipeline_types import PreflightFinding, PreflightResult
from app.services.source_service import validate_source_file


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
        payload = load_config_payload(config_path)
    except ValueError as exc:
        findings.append(PreflightFinding(severity="error", summary=str(exc)))
        payload = None

    output_path = None
    if payload is not None:
        config_name = str(payload.get("name", config_path.stem)).strip() or config_path.stem
        output_path = paths.outputs_dir / f"{config_name}.xlsx"
        findings.append(
            PreflightFinding(
                severity="info",
                summary=f"Target output akan ditulis ke {output_path.name}.",
            )
        )

    status = "Blocked" if any(item.severity == "error" for item in findings) else "Ready"
    return PreflightResult(status=status, findings=tuple(findings), output_path=output_path)
