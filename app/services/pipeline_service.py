from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app import AppPaths
from app.services.config_service import is_step_recipe_payload, load_config_payload
from app.services.output_service import write_output_workbook
from app.services.preflight_service import preview_output_path
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


def run_pipeline(
    *,
    paths: AppPaths,
    source_path: Path,
    config_path: Path,
    log: LogFn,
) -> PipelineResult:
    source_errors = validate_source_file(source_path)
    if source_errors:
        raise PipelineError(
            "Source tidak valid untuk dieksekusi. "
            + "; ".join(source_errors)
            + " Periksa file source lalu coba lagi."
        )

    log(f"Load config: {config_path.name}")
    try:
        config = load_config_payload(config_path)
    except ValueError as exc:
        raise PipelineError(str(exc)) from exc

    log("Salin source ke folder uploads/")
    try:
        source_copy = copy_source_to_uploads(source_path, paths.uploads_dir)
    except OSError as exc:
        raise PipelineError(
            "Gagal menyalin source ke folder uploads/. "
            "Pastikan file source bisa diakses dan aplikasi punya izin tulis. "
            f"Detail: {exc}"
        ) from exc

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
            raise PipelineError(
                "Recipe tidak bisa dijalankan dengan input saat ini. "
                f"Periksa kecocokan source, step recipe, dan master. Detail: {exc}"
            ) from exc
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
            raise PipelineError(
                "Source tidak bisa dibaca sesuai config aktif. "
                f"Periksa sheet source atau format file. Detail: {exc}"
            ) from exc

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
            raise PipelineError(
                "Lookup master gagal diproses. "
                f"Periksa file master dan mapping config. Detail: {exc}"
            ) from exc

        log("Apply transform rules")
        try:
            transformed_df = apply_transform_steps(
                data_df=transformed_df,
                transforms_cfg=config.get("transforms"),
                log=log,
            )
        except ValueError as exc:
            raise PipelineError(
                "Transform data gagal dijalankan. "
                f"Periksa aturan transform pada config aktif. Detail: {exc}"
            ) from exc

        log("Build output sheets")
        try:
            output_sheets = build_output_sheets(config["outputs"], transformed_df, log)
        except ValueError as exc:
            raise PipelineError(
                "Output sheet tidak bisa dibentuk. "
                f"Periksa definisi outputs pada config aktif. Detail: {exc}"
            ) from exc

    config_name = str(config.get("name", config_path.stem))
    output_path = preview_output_path(paths, config, config_path)

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
        )
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
