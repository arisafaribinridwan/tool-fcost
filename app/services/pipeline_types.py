from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PipelineError(RuntimeError):
    """Domain error for user-facing pipeline failures."""


@dataclass(frozen=True)
class PreflightFinding:
    severity: str
    code: str
    summary: str
    suggestion: str


@dataclass(frozen=True)
class PreflightResult:
    status: str
    findings: tuple[PreflightFinding, ...]
    output_path: Path | None

    @property
    def error_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "WARNING")

    @property
    def info_count(self) -> int:
        return sum(1 for item in self.findings if item.severity == "INFO")

    @property
    def can_execute(self) -> bool:
        return self.status in {"Ready", "Warning"}


@dataclass(frozen=True)
class PipelineResult:
    output_path: Path
    source_copy_path: Path
    sheets_written: int
