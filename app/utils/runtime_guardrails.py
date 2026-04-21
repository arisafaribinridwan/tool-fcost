from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import time

import yaml


DEFAULT_LIMITS_CONFIG_PATH = Path("configs/app_limits.yaml")


@dataclass(frozen=True)
class GuardrailLimits:
    max_source_size_mb: float = 75.0
    warning_source_size_mb: float = 60.0
    interactive_row_limit: int = 150000
    row_limit_mode: str = "warning"
    read_timeout_seconds: float = 45.0
    transform_timeout_seconds: float = 120.0
    write_timeout_seconds: float = 60.0


@dataclass(frozen=True)
class SourceSizeCheckResult:
    size_bytes: int
    size_mb: float
    exceeds_warning: bool
    exceeds_max: bool


@dataclass(frozen=True)
class StageTimingResult:
    value: object
    duration_seconds: float


def _coerce_positive_float(raw_value: object, field_name: str, default: float) -> float:
    if raw_value is None:
        return default
    if isinstance(raw_value, bool):
        raise ValueError(f"{field_name} harus berupa angka positif.")
    try:
        parsed = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} harus berupa angka positif.") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} harus lebih besar dari 0.")
    return parsed


def _coerce_positive_int(raw_value: object, field_name: str, default: int) -> int:
    if raw_value is None:
        return default
    if isinstance(raw_value, bool):
        raise ValueError(f"{field_name} harus berupa bilangan bulat positif.")
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} harus berupa bilangan bulat positif.") from exc
    if parsed <= 0:
        raise ValueError(f"{field_name} harus lebih besar dari 0.")
    return parsed


def _coerce_row_limit_mode(raw_value: object, default: str) -> str:
    if raw_value is None:
        return default
    if not isinstance(raw_value, str):
        raise ValueError("resource_guardrails.row_limit_mode harus berupa string.")
    normalized = raw_value.strip().casefold()
    if normalized not in {"warning", "error"}:
        raise ValueError("resource_guardrails.row_limit_mode harus bernilai 'warning' atau 'error'.")
    return normalized


def _merge_guardrail_config(payload: dict[str, object], defaults: GuardrailLimits) -> GuardrailLimits:
    guardrails_cfg = payload.get("resource_guardrails")
    if guardrails_cfg is None:
        return defaults
    if not isinstance(guardrails_cfg, dict):
        raise ValueError("resource_guardrails harus berupa object.")

    timeouts_cfg = guardrails_cfg.get("timeouts") or {}
    if not isinstance(timeouts_cfg, dict):
        raise ValueError("resource_guardrails.timeouts harus berupa object.")

    return GuardrailLimits(
        max_source_size_mb=_coerce_positive_float(
            guardrails_cfg.get("max_source_size_mb"),
            "resource_guardrails.max_source_size_mb",
            defaults.max_source_size_mb,
        ),
        warning_source_size_mb=_coerce_positive_float(
            guardrails_cfg.get("warning_source_size_mb"),
            "resource_guardrails.warning_source_size_mb",
            defaults.warning_source_size_mb,
        ),
        interactive_row_limit=_coerce_positive_int(
            guardrails_cfg.get("interactive_row_limit"),
            "resource_guardrails.interactive_row_limit",
            defaults.interactive_row_limit,
        ),
        row_limit_mode=_coerce_row_limit_mode(
            guardrails_cfg.get("row_limit_mode"),
            defaults.row_limit_mode,
        ),
        read_timeout_seconds=_coerce_positive_float(
            timeouts_cfg.get("read_seconds"),
            "resource_guardrails.timeouts.read_seconds",
            defaults.read_timeout_seconds,
        ),
        transform_timeout_seconds=_coerce_positive_float(
            timeouts_cfg.get("transform_seconds"),
            "resource_guardrails.timeouts.transform_seconds",
            defaults.transform_timeout_seconds,
        ),
        write_timeout_seconds=_coerce_positive_float(
            timeouts_cfg.get("write_seconds"),
            "resource_guardrails.timeouts.write_seconds",
            defaults.write_timeout_seconds,
        ),
    )


def get_default_guardrail_limits() -> GuardrailLimits:
    return GuardrailLimits()


def load_guardrail_limits(project_root: Path) -> tuple[GuardrailLimits, str | None]:
    defaults = get_default_guardrail_limits()
    config_path = project_root / DEFAULT_LIMITS_CONFIG_PATH
    if not config_path.exists():
        return defaults, None

    try:
        raw_payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw_payload, dict):
            raise ValueError("Isi file guardrail harus berupa object YAML.")
        limits = _merge_guardrail_config(raw_payload, defaults)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        warning = (
            "Konfigurasi guardrail internal tidak valid, menggunakan default aman. "
            f"Detail: {exc}"
        )
        return defaults, warning

    if limits.warning_source_size_mb > limits.max_source_size_mb:
        warning = (
            "Konfigurasi guardrail internal tidak valid, menggunakan default aman. "
            "Detail: warning_source_size_mb tidak boleh melebihi max_source_size_mb."
        )
        return defaults, warning

    return limits, None


def check_source_size(path: Path, limits: GuardrailLimits) -> SourceSizeCheckResult:
    size_bytes = path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    return SourceSizeCheckResult(
        size_bytes=size_bytes,
        size_mb=size_mb,
        exceeds_warning=size_mb >= limits.warning_source_size_mb,
        exceeds_max=size_mb > limits.max_source_size_mb,
    )


def run_with_timeout(label: str, seconds: float, fn: Callable[[], object]) -> StageTimingResult:
    started_at = time.monotonic()
    value = fn()
    duration_seconds = time.monotonic() - started_at
    if duration_seconds > seconds:
        raise TimeoutError(
            f"Tahap '{label}' melebihi batas waktu {seconds:.0f} detik "
            f"({duration_seconds:.1f} detik)."
        )
    return StageTimingResult(value=value, duration_seconds=duration_seconds)
