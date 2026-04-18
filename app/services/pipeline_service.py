from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import re

from app import AppPaths
from app.services.config_service import is_step_recipe_payload, load_config_payload
from app.services.output_service import write_output_workbook
from app.services.pipeline_types import PipelineError, PipelineResult
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
) -> PipelineResult:
    source_errors = validate_source_file(source_path)
    if source_errors:
        raise PipelineError("; ".join(source_errors))

    log(f"Load config: {config_path.name}")
    try:
        config = load_config_payload(config_path)
    except ValueError as exc:
        raise PipelineError(str(exc)) from exc

    log("Salin source ke folder uploads/")
    try:
        source_copy = copy_source_to_uploads(source_path, paths.uploads_dir)
    except OSError as exc:
        raise PipelineError(f"Gagal menyalin source ke uploads/: {exc}") from exc

    if is_step_recipe_payload(config):
        log(f"Read source workbook: {source_path.name}")
        try:
            recipe_result = execute_step_recipe(
                source_path=source_path,
                recipe_cfg=config,
                project_root=paths.project_root,
                masters_dir=paths.masters_dir,
                log=log,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc
        source_df = recipe_result.source_df_for_header
        output_sheets = recipe_result.output_sheets
    else:
        source_sheet = config["source_sheet"]
        log(f"Read source: {source_path.name}")
        try:
            source_df = load_source_dataframe(
                source_path,
                source_sheet=str(source_sheet) if source_path.suffix.lower() == ".xlsx" else None,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc

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

        log("Apply transform rules")
        try:
            transformed_df = apply_transform_steps(
                data_df=transformed_df,
                transforms_cfg=config.get("transforms"),
                log=log,
            )
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc

        log("Build output sheets")
        try:
            output_sheets = build_output_sheets(config["outputs"], transformed_df, log)
        except ValueError as exc:
            raise PipelineError(str(exc)) from exc

    config_name = str(config.get("name", config_path.stem))
    output_file_name = (
        f"{_safe_filename(config_name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )
    output_path = paths.outputs_dir / output_file_name

    log("Write workbook (.xlsx)")
    try:
        write_output_workbook(
            output_sheets=output_sheets,
            output_path=output_path,
            report_title=str(config.get("header", {}).get("title", config_name)),
            header_cfg=config.get("header", {}),
            styling_cfg=config.get("styling", {}),
            source_df=source_df,
        )
    except Exception as exc:
        raise PipelineError(f"Gagal menulis file output: {exc}") from exc

    log(f"Selesai. Output: {output_path.name}")
    return PipelineResult(
        output_path=output_path,
        source_copy_path=source_copy,
        sheets_written=len(output_sheets),
    )
