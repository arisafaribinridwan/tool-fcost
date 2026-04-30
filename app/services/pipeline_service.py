from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import re
from time import perf_counter

from app import AppPaths
from app.services.config_service import is_step_recipe_payload, load_config_payload
from app.services.output_service import write_output_workbook
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


LogFn = Callable[[str], None]
ProgressFn = Callable[[PipelineStepStatus], None]

_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(raw_name: str) -> str:
    normalized = _UNSAFE_FILENAME_CHARS.sub("_", raw_name.strip())
    normalized = normalized.strip("._")
    return normalized or "report"


def run_pipeline(
    *,
    paths: AppPaths,
    source_path: Path,
    config_path: Path,
    log: LogFn,
    progress: ProgressFn | None = None,
    period_text_override: str | None = None,
    period_keydate_override: str | None = None,
) -> PipelineResult:
    started_at = perf_counter()

    def emit_progress(step_key: str, step_label: str, state: str, detail: str = "") -> None:
        if progress is None:
            return
        progress(
            PipelineStepStatus(
                step_key=step_key,
                step_label=step_label,
                state=state,
                detail=detail,
            )
        )

    source_errors = validate_source_file(source_path)
    if source_errors:
        raise PipelineError("; ".join(source_errors))

    emit_progress("load_config", "Load config", "running", config_path.name)
    log(f"Load config: {config_path.name}")
    try:
        config = load_config_payload(config_path)
    except ValueError as exc:
        raise PipelineError(str(exc)) from exc
    emit_progress("load_config", "Load config", "done", config_path.name)

    emit_progress("copy_source", "Copy source", "running", source_path.name)
    source_resolved = source_path.resolve()
    uploads_resolved = paths.uploads_dir.resolve()
    upload_resolved = (paths.project_root / "upload").resolve()

    in_uploads_dir = source_resolved.is_relative_to(uploads_resolved)
    in_upload_dir = source_resolved.is_relative_to(upload_resolved)

    if in_uploads_dir or in_upload_dir:
        source_copy = source_resolved
        log("Source sudah berada di folder upload(s), copy source dilewati.")
    else:
        log("Salin source ke folder uploads/")
        try:
            source_copy = copy_source_to_uploads(source_path, paths.uploads_dir)
        except OSError as exc:
            raise PipelineError(f"Gagal menyalin source ke uploads/: {exc}") from exc
    emit_progress("copy_source", "Copy source", "done", source_copy.name)

    sheet_layouts: dict[str, str] | None = None

    if is_step_recipe_payload(config):
        emit_progress("read_source", "Read source", "running", source_path.name)
        log(f"Read source workbook: {source_path.name}")
        try:
            recipe_result = execute_step_recipe(
                source_path=source_path,
                recipe_cfg=config,
                project_root=paths.project_root,
                masters_dir=paths.masters_dir,
                log=log,
                runtime_values={"period_keydate": period_keydate_override},
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        source_df = recipe_result.source_df_for_header
        output_sheets = recipe_result.output_sheets
        sheet_layouts = recipe_result.sheet_layouts
        emit_progress("read_source", "Read source", "done", f"{len(source_df)} baris")
    else:
        source_sheet = config["source_sheet"]
        emit_progress("read_source", "Read source", "running", source_path.name)
        log(f"Read source: {source_path.name}")
        try:
            source_df = load_source_dataframe(
                source_path,
                source_sheet=str(source_sheet) if source_path.suffix.lower() == ".xlsx" else None,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        emit_progress("read_source", "Read source", "done", f"{len(source_df)} baris")

        try:
            validate_required_source_columns(
                source_df,
                config.get("required_source_columns"),
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc

        if source_df.empty:
            log("Warning: source kosong, output akan tetap dibuat.")
        else:
            log(f"Source loaded: {len(source_df)} baris, {len(source_df.columns)} kolom.")

        emit_progress("load_master", "Load master", "running")
        log("Load master & apply lookup")
        try:
            transformed_df = apply_master_lookups(
                source_df=source_df,
                masters_config=config.get("masters"),
                project_root=paths.project_root,
                masters_dir=paths.masters_dir,
                log=log,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        emit_progress("load_master", "Load master", "done")

        emit_progress("transform", "Transform", "running")
        log("Apply transform rules")
        try:
            transformed_df = apply_transform_steps(
                data_df=transformed_df,
                transforms_cfg=config.get("transforms"),
                log=log,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        emit_progress("transform", "Transform", "done")

        emit_progress("build_output", "Build output", "running")
        log("Build output sheets")
        try:
            output_sheets = build_output_sheets(config["outputs"], transformed_df, log)
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        emit_progress("build_output", "Build output", "done", f"{len(output_sheets)} sheet")

    config_name = str(config.get("name", config_path.stem))
    output_file_name = (
        f"{_safe_filename(config_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    output_path = paths.outputs_dir / output_file_name

    emit_progress("write_output", "Write output", "running", output_path.name)
    log("Write workbook (.xlsx)")
    try:
        write_output_workbook(
            output_sheets=output_sheets,
            output_path=output_path,
            outputs_dir=paths.outputs_dir,
            report_title=str(config.get("header", {}).get("title", config_name)),
            header_cfg=config.get("header", {}),
            styling_cfg=config.get("styling", {}),
            source_df=source_df,
            period_text_override=period_text_override,
            sheet_layouts=sheet_layouts,
        )
    except Exception as exc:
        raise PipelineError(f"Gagal menulis file output: {exc}") from exc
    emit_progress("write_output", "Write output", "done", output_path.name)

    log(f"Selesai. Output: {output_path.name}")
    return PipelineResult(
        output_path=output_path,
        source_copy_path=source_copy,
        sheets_written=len(output_sheets),
        duration_ms=max(1, int(round((perf_counter() - started_at) * 1000))),
    )
