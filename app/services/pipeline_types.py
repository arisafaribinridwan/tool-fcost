from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PipelineError(RuntimeError):
    """Domain error for user-facing pipeline failures."""


@dataclass(frozen=True)
class PipelineStepStatus:
    step_key: str
    step_label: str
    state: str
    detail: str = ""
    progress_ratio: float | None = None


@dataclass(frozen=True)
class PipelineResult:
    output_path: Path
    source_copy_path: Path
    sheets_written: int
    duration_ms: int | None = None


@dataclass(frozen=True)
class PreflightFinding:
    severity: str
    summary: str


@dataclass(frozen=True)
class PreflightResult:
    status: str
    findings: tuple[PreflightFinding, ...]
    output_path: Path | None

    @property
    def error_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "info")

    @property
    def can_execute(self) -> bool:
        return self.status == "Ready" and self.error_count == 0
