from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app import AppPaths
from app.services.config_service import is_step_recipe_payload, load_config_payload
from app.services.output_service import write_output_workbook
from app.services.preflight_service import preview_output_path
from app.services.pipeline_types import PipelineError, PipelineResult, PipelineStepStatus
from app.services.recipe_service import execute_step_recipe
from app.services.source_service import (
    copy_source_to_uploads,
    load_source_dataframe,
    validate_required_source_columns,
    validate_source_file,
)
from app.services.transform_service import (
    apply_master_lookups,
    apply_transform_steps,
    build_output_sheets,
)
from app.utils.runtime_guardrails import (
    GuardrailLimits,
    check_source_size,
    load_guardrail_limits,
    run_with_timeout,
)


LogFn = Callable[[str], None]
ProgressFn = Callable[[PipelineStepStatus], None]

STEP_LABELS = {
    "load_config": "Load config",
    "copy_source": "Salin source",
    "read_source": "Baca source",
    "load_masters": "Load master",
    "transform": "Transform",
    "build_output": "Build output",
    "write_output": "Write output",
}


def _emit_progress(
    progress: ProgressFn | None,
    *,
    step_id: str,
    state: str,
    duration_ms: int | None = None,
) -> None:
    if progress is None:
        return
    progress(
        PipelineStepStatus(
            step_id=step_id,
            label=STEP_LABELS[step_id],
            state=state,
            duration_ms=duration_ms,
        )
    )


def _duration_ms(duration_seconds: float) -> int:
    return max(1, int(round(duration_seconds * 1000)))


def _format_size_mb(size_mb: float) -> str:
    return f"{size_mb:.1f}".rstrip("0").rstrip(".")


def _raise_size_limit_error(size_mb: float, limits: GuardrailLimits) -> None:
    raise PipelineError(
        "Ukuran source melebihi batas aplikasi. "
        f"Ukuran file {_format_size_mb(size_mb)} MB, maksimum {_format_size_mb(limits.max_source_size_mb)} MB. "
        "Gunakan file yang lebih kecil atau pecah source sebelum menjalankan proses."
    )


def _warn_large_source(log: LogFn, size_mb: float, limits: GuardrailLimits) -> None:
    if size_mb < limits.warning_source_size_mb:
        return
    log(
        "Warning: ukuran source mendekati batas aplikasi "
        f"({_format_size_mb(size_mb)} MB dari {_format_size_mb(limits.max_source_size_mb)} MB)."
    )


def _enforce_row_limit(row_count: int, limits: GuardrailLimits) -> None:
    if row_count <= limits.interactive_row_limit or limits.row_limit_mode != "error":
        return
    raise PipelineError(
        "Jumlah baris source melebihi batas mode interaktif. "
        f"Baris terbaca: {row_count}, batas: {limits.interactive_row_limit}. "
        "Kurangi data source atau gunakan batch yang lebih kecil."
    )


def _run_stage(
    *,
    step_id: str,
    timeout_seconds: float,
    progress: ProgressFn | None,
    fn: Callable[[], object],
) -> object:
    _emit_progress(progress, step_id=step_id, state="running")
    try:
        timed_result = run_with_timeout(STEP_LABELS[step_id], timeout_seconds, fn)
    except Exception:
        _emit_progress(progress, step_id=step_id, state="failed")
        raise
    _emit_progress(
        progress,
        step_id=step_id,
        state="success",
        duration_ms=_duration_ms(timed_result.duration_seconds),
    )
    return timed_result.value


def run_pipeline(
    *,
    paths: AppPaths,
    source_path: Path,
    config_path: Path,
    log: LogFn,
    progress: ProgressFn | None = None,
) -> PipelineResult:
    source_errors = validate_source_file(source_path)
    if source_errors:
        raise PipelineError(
            "Source tidak valid untuk dieksekusi. "
            + "; ".join(source_errors)
            + " Periksa file source lalu coba lagi."
        )

    limits, guardrail_warning = load_guardrail_limits(paths.project_root)
    if guardrail_warning:
        log(f"Warning: {guardrail_warning}")

    try:
        source_size = check_source_size(source_path, limits)
    except OSError as exc:
        raise PipelineError(
            "Ukuran source tidak bisa diperiksa. Pastikan file source bisa diakses lalu coba lagi. "
            f"Detail: {exc}"
        ) from exc

    if source_size.exceeds_max:
        _raise_size_limit_error(source_size.size_mb, limits)
    _warn_large_source(log, source_size.size_mb, limits)

    log(f"Load config: {config_path.name}")
    try:
        config = _run_stage(
            step_id="load_config",
            timeout_seconds=limits.read_timeout_seconds,
            progress=progress,
            fn=lambda: load_config_payload(config_path),
        )
    except ValueError as exc:
        raise PipelineError(str(exc)) from exc
    except TimeoutError as exc:
        raise PipelineError(str(exc)) from exc

    log("Salin source ke folder uploads/")
    try:
        source_copy = _run_stage(
            step_id="copy_source",
            timeout_seconds=limits.read_timeout_seconds,
            progress=progress,
            fn=lambda: copy_source_to_uploads(source_path, paths.uploads_dir),
        )
    except OSError as exc:
        raise PipelineError(
            "Gagal menyalin source ke folder uploads/. "
            "Pastikan file source bisa diakses dan aplikasi punya izin tulis. "
            f"Detail: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise PipelineError(str(exc)) from exc

    if is_step_recipe_payload(config):
        log(f"Read source workbook: {source_path.name}")
        try:
            recipe_result = _run_stage(
                step_id="read_source",
                timeout_seconds=limits.read_timeout_seconds,
                progress=progress,
                fn=lambda: execute_step_recipe(
                    source_path=source_path,
                    recipe_cfg=config,
                    project_root=paths.project_root,
                    masters_dir=paths.masters_dir,
                    log=log,
                ),
            )
        except ValueError as exc:
            raise PipelineError(
                "Recipe tidak bisa dijalankan dengan input saat ini. "
                f"Periksa kecocokan source, step recipe, dan master. Detail: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise PipelineError(str(exc)) from exc
        source_df = recipe_result.source_df_for_header
        output_sheets = recipe_result.output_sheets
        _enforce_row_limit(len(source_df), limits)
        _emit_progress(progress, step_id="load_masters", state="success", duration_ms=1)
        _emit_progress(progress, step_id="transform", state="success", duration_ms=1)
        _emit_progress(progress, step_id="build_output", state="success", duration_ms=1)
    else:
        source_sheet = config["source_sheet"]
        log(f"Read source: {source_path.name}")
        try:
            source_df = _run_stage(
                step_id="read_source",
                timeout_seconds=limits.read_timeout_seconds,
                progress=progress,
                fn=lambda: load_source_dataframe(
                    source_path,
                    source_sheet=(
                        str(source_sheet) if source_path.suffix.lower() == ".xlsx" else None
                    ),
                ),
            )
        except ValueError as exc:
            raise PipelineError(
                "Source tidak bisa dibaca sesuai config aktif. "
                f"Periksa sheet source atau format file. Detail: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise PipelineError(str(exc)) from exc

        try:
            validate_required_source_columns(
                source_df,
                config.get("required_source_columns"),
            )
        except ValueError as exc:
            raise PipelineError(
                f"{exc}. Lengkapi kolom source atau sesuaikan config pekerjaan aktif."
            ) from exc

        if source_df.empty:
            log("Warning: source kosong, output akan tetap dibuat.")
        else:
            log(f"Source loaded: {len(source_df)} baris, {len(source_df.columns)} kolom.")
        _enforce_row_limit(len(source_df), limits)

        log("Load master & apply lookup")
        try:
            transformed_df = _run_stage(
                step_id="load_masters",
                timeout_seconds=limits.transform_timeout_seconds,
                progress=progress,
                fn=lambda: apply_master_lookups(
                    source_df=source_df,
                    masters_config=config.get("masters"),
                    project_root=paths.project_root,
                    masters_dir=paths.masters_dir,
                    log=log,
                ),
            )
        except ValueError as exc:
            raise PipelineError(
                "Lookup master gagal diproses. "
                f"Periksa file master dan mapping config. Detail: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise PipelineError(str(exc)) from exc

        log("Apply transform rules")
        try:
            transformed_df = _run_stage(
                step_id="transform",
                timeout_seconds=limits.transform_timeout_seconds,
                progress=progress,
                fn=lambda: apply_transform_steps(
                    data_df=transformed_df,
                    transforms_cfg=config.get("transforms"),
                    log=log,
                ),
            )
        except ValueError as exc:
            raise PipelineError(
                "Transform data gagal dijalankan. "
                f"Periksa aturan transform pada config aktif. Detail: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise PipelineError(str(exc)) from exc

        log("Build output sheets")
        try:
            output_sheets = _run_stage(
                step_id="build_output",
                timeout_seconds=limits.transform_timeout_seconds,
                progress=progress,
                fn=lambda: build_output_sheets(config["outputs"], transformed_df, log),
            )
        except ValueError as exc:
            raise PipelineError(
                "Output sheet tidak bisa dibentuk. "
                f"Periksa definisi outputs pada config aktif. Detail: {exc}"
            ) from exc
        except TimeoutError as exc:
            raise PipelineError(str(exc)) from exc

    config_name = str(config.get("name", config_path.stem))
    output_path = preview_output_path(paths, config, config_path)

    log("Write workbook (.xlsx)")
    try:
        _run_stage(
            step_id="write_output",
            timeout_seconds=limits.write_timeout_seconds,
            progress=progress,
            fn=lambda: write_output_workbook(
                output_sheets=output_sheets,
                output_path=output_path,
                outputs_dir=paths.outputs_dir,
                report_title=str(config.get("header", {}).get("title", config_name)),
                header_cfg=config.get("header", {}),
                styling_cfg=config.get("styling", {}),
                source_df=source_df,
            ),
        )
    except TimeoutError as exc:
        raise PipelineError(str(exc)) from exc
    except Exception as exc:
        raise PipelineError(
            "Gagal menulis file output. "
            "Periksa izin folder outputs/, nama file hasil, atau workbook target yang sedang terbuka. "
            f"Detail: {exc}"
        ) from exc

    log(f"Selesai. Output: {output_path.name}")
    return PipelineResult(
        output_path=output_path,
        source_copy_path=source_copy,
        sheets_written=len(output_sheets),
    )
