from __future__ import annotations

import time

import pytest

from app.utils.runtime_guardrails import (
    check_source_size,
    get_default_guardrail_limits,
    load_guardrail_limits,
    run_with_timeout,
)


def test_load_guardrail_limits_falls_back_to_default_on_invalid_config(tmp_path):
    config_dir = tmp_path / "configs"
    config_dir.mkdir(parents=True)
    (config_dir / "app_limits.yaml").write_text(
        "resource_guardrails:\n  max_source_size_mb: invalid\n",
        encoding="utf-8",
    )

    limits, warning = load_guardrail_limits(tmp_path)

    assert limits == get_default_guardrail_limits()
    assert warning is not None
    assert "menggunakan default aman" in warning


def test_check_source_size_reports_warning_and_max_flags(tmp_path):
    source_path = tmp_path / "source.csv"
    source_path.write_bytes(b"a" * 6 * 1024 * 1024)

    limits = get_default_guardrail_limits().__class__(
        max_source_size_mb=5,
        warning_source_size_mb=4,
        interactive_row_limit=150000,
        row_limit_mode="warning",
        read_timeout_seconds=45,
        transform_timeout_seconds=120,
        write_timeout_seconds=60,
    )

    result = check_source_size(source_path, limits)

    assert result.exceeds_warning is True
    assert result.exceeds_max is True
    assert result.size_mb > 5


def test_run_with_timeout_raises_after_slow_stage():
    with pytest.raises(TimeoutError, match="melebihi batas waktu"):
        run_with_timeout("Tahap Tes", 0.01, lambda: time.sleep(0.02))
