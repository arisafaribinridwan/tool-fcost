from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

from app.services.dataframe_io_service import read_tabular_file


LogFn = Callable[[str], None]


def resolve_master_path(master_file: str, project_root: Path, masters_dir: Path) -> Path:
    raw_path = Path(master_file)
    if raw_path.is_absolute():
        raise ValueError("Path master harus relatif ke folder project.")

    resolved = (project_root / raw_path).resolve()
    masters_root = masters_dir.resolve()
    if not resolved.is_relative_to(masters_root):
        raise ValueError(
            f"Path master tidak aman: '{master_file}'. File wajib berada di folder masters/."
        )
    return resolved


def apply_master_lookups(
    source_df: pd.DataFrame,
    masters_config: list[dict] | None,
    project_root: Path,
    masters_dir: Path,
    log: LogFn,
) -> pd.DataFrame:
    if not masters_config:
        log("Tidak ada master lookup. Proses lanjut dengan source asli.")
        return source_df.copy()

    merged_df = source_df.copy()
    for idx, master_cfg in enumerate(masters_config, start=1):
        file_ref = str(master_cfg["file"])
        key_col = str(master_cfg["key"])
        master_path = resolve_master_path(file_ref, project_root, masters_dir)
        if not master_path.exists():
            raise ValueError(f"File master tidak ditemukan: {master_path}")

        master_df = read_tabular_file(master_path)
        if key_col not in merged_df.columns:
            raise ValueError(
                f"Kolom key '{key_col}' dari master tidak ditemukan di source."
            )
        if key_col not in master_df.columns:
            raise ValueError(
                f"Kolom key '{key_col}' tidak ditemukan di file master '{master_path.name}'."
            )

        requested_columns = master_cfg.get("columns") or [
            col for col in master_df.columns if col != key_col
        ]
        required_columns = [key_col, *requested_columns]
        missing_master_cols = [c for c in required_columns if c not in master_df.columns]
        if missing_master_cols:
            raise ValueError(
                f"Kolom master hilang di '{master_path.name}': {', '.join(missing_master_cols)}"
            )

        selected_master = master_df.loc[:, required_columns].drop_duplicates(
            subset=[key_col],
            keep="last",
        )

        rename_map: dict[str, str] = {}
        for col_name in requested_columns:
            if col_name in merged_df.columns:
                rename_map[col_name] = f"{col_name}_master{idx}"
        if rename_map:
            selected_master = selected_master.rename(columns=rename_map)
            log(
                "Master kolom bentrok, diganti nama: "
                + ", ".join(f"{src}->{dst}" for src, dst in rename_map.items())
            )

        try:
            merged_df = merged_df.merge(
                selected_master,
                how="left",
                on=key_col,
                validate="m:1",
            )
        except pd.errors.MergeError as exc:
            raise ValueError(
                f"Lookup master gagal karena key '{key_col}' tidak unik."
            ) from exc

        log(
            f"Master {idx} loaded: {master_path.name} "
            f"({len(selected_master)} baris unik key '{key_col}')."
        )

    return merged_df


def _normalize_as_list(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("Field pivot index/values harus string atau list string.")


def build_output_sheets(outputs_cfg: list[dict], data_df: pd.DataFrame, log: LogFn) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}

    for item in outputs_cfg:
        sheet_name = str(item["sheet_name"])
        if "columns" in item:
            columns = item["columns"]
            if not isinstance(columns, list):
                raise ValueError(f"Output '{sheet_name}' memiliki columns yang tidak valid.")
            missing_columns = [col for col in columns if col not in data_df.columns]
            if missing_columns:
                raise ValueError(
                    f"Output '{sheet_name}' gagal, kolom tidak ditemukan: {', '.join(missing_columns)}"
                )
            sheet_df = data_df.loc[:, columns].copy()
        elif "pivot" in item:
            pivot_cfg = item["pivot"]
            index_cols = _normalize_as_list(pivot_cfg["index"])
            value_cols = _normalize_as_list(pivot_cfg["values"])
            aggfunc = pivot_cfg.get("aggfunc", "sum")

            missing_columns = [
                col for col in [*index_cols, *value_cols] if col not in data_df.columns
            ]
            if missing_columns:
                raise ValueError(
                    f"Pivot '{sheet_name}' gagal, kolom tidak ditemukan: {', '.join(missing_columns)}"
                )

            pivot_df = pd.pivot_table(
                data_df,
                index=index_cols,
                values=value_cols,
                aggfunc=aggfunc,
                dropna=False,
            ).reset_index()
            sheet_df = pivot_df
        else:
            sheet_df = data_df.copy()

        log(f"Output '{sheet_name}' siap ({len(sheet_df)} baris).")
        result[sheet_name] = sheet_df

    return result
