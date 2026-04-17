from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PipelineError(RuntimeError):
    """Domain error for user-facing pipeline failures."""


@dataclass(frozen=True)
class PipelineResult:
    output_path: Path
    source_copy_path: Path
    sheets_written: int
