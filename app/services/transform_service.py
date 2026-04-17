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


def _normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().split()).casefold()


def _normalize_lookup_key(value: object, normalizer: str | None) -> str:
    normalized = _normalize_text(value)
    if normalizer is None:
        return normalized
    if normalizer == "compact_text":
        return "".join(char for char in normalized if char.isalnum())
    raise ValueError(f"Normalisasi key tidak didukung: '{normalizer}'.")


def _build_lookup_aliases(
    aliases_cfg: dict[object, object] | None,
    normalizer: str | None,
) -> dict[str, str]:
    if not aliases_cfg:
        return {}

    aliases: dict[str, str] = {}
    for raw_source, raw_target in aliases_cfg.items():
        source_key = _normalize_lookup_key(raw_source, normalizer)
        target_key = _normalize_lookup_key(raw_target, normalizer)
        aliases[source_key] = target_key
    return aliases


def _match_rule_value(source_value: object, master_value: object, mode: str) -> bool:
    normalized_master = _normalize_text(master_value)
    if not normalized_master:
        return True

    normalized_source = _normalize_text(source_value)
    if mode == "equals":
        return normalized_source == normalized_master
    if mode == "contains":
        token = normalized_master.replace("*", "")
        if not token:
            return True
        return token in normalized_source
    raise ValueError(f"Mode matcher tidak didukung: '{mode}'.")


def _read_master_dataframe(master_cfg: dict, project_root: Path, masters_dir: Path) -> tuple[Path, pd.DataFrame]:
    file_ref = str(master_cfg["file"])
    sheet_name = master_cfg.get("sheet_name")
    master_path = resolve_master_path(file_ref, project_root, masters_dir)
    if not master_path.exists():
        raise ValueError(f"File master tidak ditemukan: {master_path}")

    try:
        master_df = read_tabular_file(
            master_path,
            sheet_name=str(sheet_name) if sheet_name is not None else None,
            keep_default_na=False,
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    return master_path, master_df


def _apply_lookup_master(
    merged_df: pd.DataFrame,
    master_cfg: dict,
    project_root: Path,
    masters_dir: Path,
    log: LogFn,
    idx: int,
) -> pd.DataFrame:
    source_key = str(master_cfg.get("source_key") or master_cfg.get("key"))
    master_key = str(master_cfg.get("master_key") or master_cfg.get("key"))
    key_normalizer = master_cfg.get("key_normalizer")
    lookup_aliases = _build_lookup_aliases(master_cfg.get("key_aliases"), key_normalizer)
    master_path, master_df = _read_master_dataframe(master_cfg, project_root, masters_dir)

    if source_key not in merged_df.columns:
        raise ValueError(f"Kolom key '{source_key}' dari master tidak ditemukan di source.")
    if master_key not in master_df.columns:
        raise ValueError(
            f"Kolom key '{master_key}' tidak ditemukan di file master '{master_path.name}'."
        )

    requested_columns = master_cfg.get("columns") or [
        col for col in master_df.columns if col != master_key
    ]
    configured_rename_map = {
        str(src): str(dst) for src, dst in (master_cfg.get("rename_columns") or {}).items()
    }
    required_columns = [master_key, *requested_columns]
    missing_master_cols = [c for c in required_columns if c not in master_df.columns]
    if missing_master_cols:
        raise ValueError(
            f"Kolom master hilang di '{master_path.name}': {', '.join(missing_master_cols)}"
        )

    selected_master = master_df.loc[:, required_columns].drop_duplicates(
        subset=[master_key],
        keep="last",
    )
    if configured_rename_map:
        selected_master = selected_master.rename(columns=configured_rename_map)

    rename_map: dict[str, str] = {}
    effective_columns = [
        configured_rename_map.get(col_name, col_name) for col_name in requested_columns
    ]
    for col_name in effective_columns:
        if col_name in merged_df.columns:
            rename_map[col_name] = f"{col_name}_master{idx}"
    if rename_map:
        selected_master = selected_master.rename(columns=rename_map)
        log(
            "Master kolom bentrok, diganti nama: "
            + ", ".join(f"{src}->{dst}" for src, dst in rename_map.items())
        )

    try:
        if key_normalizer is None:
            merged_df = merged_df.merge(
                selected_master,
                how="left",
                left_on=source_key,
                right_on=master_key,
                validate="m:1",
            )
        else:
            source_merge_key = "__lookup_source_key__"
            master_merge_key = "__lookup_master_key__"
            prepared_source = merged_df.copy()
            prepared_source[source_merge_key] = prepared_source[source_key].map(
                lambda value: _normalize_lookup_key(value, str(key_normalizer))
            )
            if lookup_aliases:
                prepared_source[source_merge_key] = prepared_source[source_merge_key].map(
                    lambda value: lookup_aliases.get(value, value)
                )
            prepared_master = selected_master.copy()
            prepared_master[master_merge_key] = prepared_master[master_key].map(
                lambda value: _normalize_lookup_key(value, str(key_normalizer))
            )
            merged_df = prepared_source.merge(
                prepared_master,
                how="left",
                left_on=source_merge_key,
                right_on=master_merge_key,
                validate="m:1",
            )
            merged_df = merged_df.drop(columns=[source_merge_key, master_merge_key])
    except pd.errors.MergeError as exc:
        raise ValueError(
            f"Lookup master gagal karena key '{master_key}' tidak unik."
        ) from exc

    if master_key != source_key and master_key in merged_df.columns:
        merged_df = merged_df.drop(columns=[master_key])

    log(
        f"Master {idx} loaded: {master_path.name} "
        f"({len(selected_master)} baris unik key '{master_key}')."
    )
    return merged_df


def _apply_ordered_rules_master(
    merged_df: pd.DataFrame,
    master_cfg: dict,
    project_root: Path,
    masters_dir: Path,
    log: LogFn,
    idx: int,
) -> pd.DataFrame:
    master_path, master_df = _read_master_dataframe(master_cfg, project_root, masters_dir)
    target_column = str(master_cfg["target_column"])
    value_column = str(master_cfg["value_column"])
    matchers = master_cfg["matchers"]

    required_master_cols = [value_column]
    missing_source_cols: list[str] = []
    for matcher in matchers:
        source_col = str(matcher["source"])
        master_col = str(matcher["master"])
        if source_col not in merged_df.columns:
            missing_source_cols.append(source_col)
        required_master_cols.append(master_col)

    if missing_source_cols:
        unique_missing = sorted(set(missing_source_cols))
        raise ValueError(
            "Kolom source untuk ordered rules tidak ditemukan: "
            + ", ".join(unique_missing)
        )

    missing_master_cols = [
        col for col in required_master_cols if col not in master_df.columns
    ]
    if missing_master_cols:
        raise ValueError(
            f"Kolom master hilang di '{master_path.name}': {', '.join(sorted(set(missing_master_cols)))}"
        )

    selected_master = master_df.loc[:, list(dict.fromkeys(required_master_cols))].copy()
    selected_master = selected_master[selected_master[value_column].notna()].reset_index(drop=True)

    output_values: list[object] = []
    for _, source_row in merged_df.iterrows():
        resolved_value = ""
        for _, rule_row in selected_master.iterrows():
            if all(
                _match_rule_value(
                    source_value=source_row[str(matcher["source"])],
                    master_value=rule_row[str(matcher["master"])],
                    mode=str(matcher["mode"]),
                )
                for matcher in matchers
            ):
                resolved_value = rule_row[value_column]
                break
        output_values.append("" if pd.isna(resolved_value) else resolved_value)

    merged_df = merged_df.copy()
    merged_df[target_column] = output_values
    log(
        f"Master {idx} ordered rules loaded: {master_path.name} "
        f"({len(selected_master)} rules -> kolom '{target_column}')."
    )
    return merged_df


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
        strategy = str(master_cfg.get("strategy", "lookup"))
        if strategy == "lookup":
            merged_df = _apply_lookup_master(
                merged_df=merged_df,
                master_cfg=master_cfg,
                project_root=project_root,
                masters_dir=masters_dir,
                log=log,
                idx=idx,
            )
            continue
        if strategy == "ordered_rules":
            merged_df = _apply_ordered_rules_master(
                merged_df=merged_df,
                master_cfg=master_cfg,
                project_root=project_root,
                masters_dir=masters_dir,
                log=log,
                idx=idx,
            )
            continue
        raise ValueError(f"Strategy master tidak didukung: '{strategy}'.")

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
