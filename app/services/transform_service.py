from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

from app.services.dataframe_io_service import read_tabular_file
from app.utils.path_safety import normalize_relative_path_string, resolve_casefold_relative_path


LogFn = Callable[[str], None]
SUPPORTED_RULE_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "in",
    "not_in",
    "gt",
    "gte",
    "lt",
    "lte",
    "is_blank",
    "is_not_blank",
}
SUPPORTED_FORMULA_OPERATIONS = {"add", "subtract", "multiply", "divide"}
SUPPORTED_GROUPBY_AGGFUNCS = {"sum", "mean", "min", "max", "count", "first", "last"}


def resolve_master_path(master_file: str, project_root: Path, masters_dir: Path) -> Path:
    try:
        normalized_ref = normalize_relative_path_string(master_file)
    except ValueError as exc:
        raise ValueError(f"Path master tidak valid: {exc}") from exc

    path_parts = normalized_ref.split("/")
    if not path_parts or path_parts[0].casefold() != "masters":
        raise ValueError("Path master harus relatif dan berada di folder masters/.")

    resolved = resolve_casefold_relative_path(project_root, normalized_ref).resolve()
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


def _normalize_text_with_case(value: object, *, case_sensitive: bool) -> str:
    if pd.isna(value):
        return ""
    normalized = " ".join(str(value).strip().split())
    if case_sensitive:
        return normalized
    return normalized.casefold()


def _normalized_series(series: pd.Series, *, case_sensitive: bool) -> pd.Series:
    return series.map(lambda value: _normalize_text_with_case(value, case_sensitive=case_sensitive))


def _blank_mask(series: pd.Series) -> pd.Series:
    return series.isna() | _normalized_series(series, case_sensitive=True).eq("")


def _normalize_with_options(value: object, normalize_cfg: dict | None) -> str:
    config = normalize_cfg or {}
    trim = bool(config.get("trim", True))
    case_sensitive = bool(config.get("case_sensitive", False))
    alternative_separator = config.get("alternative_separator")

    if pd.isna(value):
        normalized = ""
    else:
        normalized = str(value)
        if trim:
            normalized = " ".join(normalized.strip().split())
        if isinstance(alternative_separator, str) and alternative_separator:
            normalized = normalized.replace(alternative_separator, " ")
            normalized = " ".join(normalized.split())

    if not case_sensitive:
        normalized = normalized.casefold()
    return normalized


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


def _matcher_matches(source_value: object, master_value: object, matcher_cfg: dict) -> bool:
    normalize_cfg = matcher_cfg.get("normalize")
    blank_as_wildcard = bool((normalize_cfg or {}).get("blank_as_wildcard", False))
    source_normalized = _normalize_with_options(source_value, normalize_cfg)
    master_normalized = _normalize_with_options(master_value, normalize_cfg)

    if blank_as_wildcard and not master_normalized:
        return True

    mode = str(matcher_cfg["mode"])
    if mode == "equals":
        return source_normalized == master_normalized
    if mode == "contains":
        wildcard = str((normalize_cfg or {}).get("wildcard", "*"))
        token = master_normalized.replace(wildcard, "")
        if not token:
            return True
        return token in source_normalized
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


def _ensure_columns_exist(data_df: pd.DataFrame, columns: list[str], context: str) -> None:
    missing_columns = [column for column in columns if column not in data_df.columns]
    if missing_columns:
        raise ValueError(f"{context} gagal, kolom tidak ditemukan: {', '.join(missing_columns)}")


def _coerce_numeric_scalar(value: object, context: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{context} harus berupa angka, bukan boolean.")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{context} harus berupa angka, bukan string kosong.")
        try:
            return float(normalized)
        except ValueError as exc:
            raise ValueError(f"{context} harus berupa angka yang valid.") from exc
    raise ValueError(f"{context} harus berupa angka yang valid.")


def _coerce_numeric_series(series: pd.Series, context: str) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce")
    invalid_mask = numeric_series.isna() & ~_blank_mask(series)
    if invalid_mask.any():
        raise ValueError(
            f"{context} harus memakai kolom numerik. Nilai tidak valid ditemukan pada kolom '{series.name}'."
        )
    return numeric_series


def _resolve_rule_operator(rule_cfg: dict, context: str) -> str:
    operators = [name for name in SUPPORTED_RULE_OPERATORS if name in rule_cfg]
    if len(operators) != 1:
        raise ValueError(
            f"{context} harus memiliki tepat satu operator kondisi yang didukung."
        )
    return operators[0]


def _normalize_condition_items(raw_when: object, context: str) -> list[dict]:
    if isinstance(raw_when, dict):
        return [raw_when]
    if isinstance(raw_when, list) and all(isinstance(item, dict) for item in raw_when):
        return raw_when
    raise ValueError(f"{context} harus berupa object atau list object.")


def _build_condition_mask(data_df: pd.DataFrame, condition_cfg: dict, context: str) -> pd.Series:
    if "column" not in condition_cfg:
        raise ValueError(f"{context} wajib memiliki field 'column'.")

    column = str(condition_cfg["column"])
    if column not in data_df.columns:
        raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")

    operator = _resolve_rule_operator(condition_cfg, context)
    series = data_df[column]
    case_sensitive = bool(condition_cfg.get("case_sensitive", False))

    if operator == "is_blank":
        return _blank_mask(series)
    if operator == "is_not_blank":
        return ~_blank_mask(series)

    rule_value = condition_cfg[operator]

    if operator in {"gt", "gte", "lt", "lte"}:
        numeric_series = _coerce_numeric_series(series, context)
        numeric_value = _coerce_numeric_scalar(rule_value, f"{context} operator '{operator}'")
        if operator == "gt":
            return numeric_series > numeric_value
        if operator == "gte":
            return numeric_series >= numeric_value
        if operator == "lt":
            return numeric_series < numeric_value
        return numeric_series <= numeric_value

    if operator == "contains":
        token = _normalize_text_with_case(rule_value, case_sensitive=case_sensitive)
        normalized_series = _normalized_series(series, case_sensitive=case_sensitive)
        return normalized_series.str.contains(token, regex=False)

    if operator in {"equals", "not_equals"}:
        if isinstance(rule_value, str):
            normalized_series = _normalized_series(series, case_sensitive=case_sensitive)
            normalized_value = _normalize_text_with_case(
                rule_value,
                case_sensitive=case_sensitive,
            )
            mask = normalized_series.eq(normalized_value)
        else:
            mask = series.eq(rule_value)
        return ~mask if operator == "not_equals" else mask

    if operator in {"in", "not_in"}:
        if not isinstance(rule_value, list):
            raise ValueError(f"{context} operator '{operator}' harus berupa list nilai.")
        if all(isinstance(item, str) for item in rule_value):
            normalized_series = _normalized_series(series, case_sensitive=case_sensitive)
            normalized_values = {
                _normalize_text_with_case(item, case_sensitive=case_sensitive)
                for item in rule_value
            }
            mask = normalized_series.isin(normalized_values)
        else:
            mask = series.isin(rule_value)
        return ~mask if operator == "not_in" else mask

    raise ValueError(f"{context} memakai operator yang tidak didukung: '{operator}'.")


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


def _apply_lookup_rules_master(
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
    matching_cfg = master_cfg["matching"]
    matchers = matching_cfg["matchers"]
    first_match_wins = bool(matching_cfg.get("first_match_wins", True))
    on_missing_match = master_cfg.get("on_missing_match")

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
            "Kolom source untuk lookup rules tidak ditemukan: "
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
    selected_master = selected_master[selected_master[value_column].notna()].reset_index(
        drop=True
    )

    output_values: list[object] = []
    for _, source_row in merged_df.iterrows():
        resolved_value = on_missing_match
        for _, rule_row in selected_master.iterrows():
            if all(
                _matcher_matches(
                    source_value=source_row[str(matcher["source"])],
                    master_value=rule_row[str(matcher["master"])],
                    matcher_cfg=matcher,
                )
                for matcher in matchers
            ):
                resolved_value = rule_row[value_column]
                if first_match_wins:
                    break
        output_values.append("" if pd.isna(resolved_value) else resolved_value)

    merged_df = merged_df.copy()
    merged_df[target_column] = output_values
    log(
        f"Master {idx} lookup rules loaded: {master_path.name} "
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
        if strategy == "lookup_rules":
            merged_df = _apply_lookup_rules_master(
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


def _apply_optional_columns_transform(data_df: pd.DataFrame, transform_cfg: dict, log: LogFn) -> pd.DataFrame:
    columns_cfg = transform_cfg["columns"]
    if isinstance(columns_cfg, list):
        defaults = {str(column): None for column in columns_cfg}
    else:
        defaults = {str(column): value for column, value in columns_cfg.items()}

    result_df = data_df.copy()
    missing_columns: list[str] = []
    for column, default_value in defaults.items():
        if column in result_df.columns:
            continue
        result_df[column] = default_value
        missing_columns.append(column)

    if missing_columns:
        log(
            "Warning: kolom opsional tidak ditemukan, kolom kosong ditambahkan: "
            + ", ".join(missing_columns)
        )
    else:
        log("Kolom opsional lengkap, tidak ada penambahan kolom.")
    return result_df


def _apply_filter_transform(data_df: pd.DataFrame, transform_cfg: dict, log: LogFn) -> pd.DataFrame:
    mask = _build_condition_mask(data_df, transform_cfg, "Filter")
    filtered_df = data_df.loc[mask].copy()
    log(
        f"Filter '{transform_cfg['column']}' diterapkan: {len(data_df)} -> {len(filtered_df)} baris."
    )
    return filtered_df


def _resolve_formula_operand(
    data_df: pd.DataFrame,
    operand_cfg: dict,
    context: str,
    *,
    null_as_zero: bool,
) -> pd.Series:
    has_column = "column" in operand_cfg
    has_value = "value" in operand_cfg
    if has_column == has_value:
        raise ValueError(
            f"{context} harus memiliki tepat satu dari 'column' atau 'value' pada setiap operand."
        )

    if has_column:
        column = str(operand_cfg["column"])
        if column not in data_df.columns:
            raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")
        operand_series = _coerce_numeric_series(data_df[column], context)
    else:
        numeric_value = _coerce_numeric_scalar(operand_cfg["value"], context)
        operand_series = pd.Series(float(numeric_value), index=data_df.index, dtype="float64")

    if null_as_zero:
        return operand_series.fillna(0)
    return operand_series


def _apply_formula_transform(data_df: pd.DataFrame, transform_cfg: dict, log: LogFn) -> pd.DataFrame:
    target_column = str(transform_cfg["target"])
    operation = str(transform_cfg["operation"])
    operands = transform_cfg["operands"]
    null_as_zero = bool(transform_cfg.get("null_as_zero", False))
    context = f"Formula '{target_column}'"

    resolved_operands = [
        _resolve_formula_operand(data_df, operand_cfg, context, null_as_zero=null_as_zero)
        for operand_cfg in operands
    ]

    if operation == "add":
        result_series = resolved_operands[0].copy()
        for operand_series in resolved_operands[1:]:
            result_series = result_series + operand_series
    elif operation == "subtract":
        result_series = resolved_operands[0].copy()
        for operand_series in resolved_operands[1:]:
            result_series = result_series - operand_series
    elif operation == "multiply":
        result_series = resolved_operands[0].copy()
        for operand_series in resolved_operands[1:]:
            result_series = result_series * operand_series
    elif operation == "divide":
        result_series = resolved_operands[0].copy()
        for operand_series in resolved_operands[1:]:
            zero_mask = operand_series.eq(0)
            if zero_mask.any():
                raise ValueError(
                    f"{context} gagal karena pembagi bernilai 0 pada {int(zero_mask.sum())} baris."
                )
            result_series = result_series / operand_series
    else:
        raise ValueError(f"{context} memakai operasi yang tidak didukung: '{operation}'.")

    result_df = data_df.copy()
    result_df[target_column] = result_series
    log(f"Formula '{target_column}' selesai dengan operasi '{operation}'.")
    return result_df


def _apply_conditional_transform(data_df: pd.DataFrame, transform_cfg: dict, log: LogFn) -> pd.DataFrame:
    target_column = str(transform_cfg["target"])
    cases = transform_cfg["cases"]
    default_value = transform_cfg.get("default", "")
    result_series = pd.Series(default_value, index=data_df.index, dtype="object")
    remaining_mask = pd.Series(True, index=data_df.index)

    for idx, case_cfg in enumerate(cases, start=1):
        conditions = _normalize_condition_items(
            case_cfg["when"],
            f"Conditional '{target_column}' case {idx}",
        )
        case_mask = pd.Series(True, index=data_df.index)
        for condition in conditions:
            case_mask = case_mask & _build_condition_mask(
                data_df,
                condition,
                f"Conditional '{target_column}' case {idx}",
            )
        applied_mask = remaining_mask & case_mask
        result_series.loc[applied_mask] = case_cfg["value"]
        remaining_mask = remaining_mask & ~case_mask

    result_df = data_df.copy()
    result_df[target_column] = result_series
    log(
        f"Conditional '{target_column}' selesai. {int((~remaining_mask).sum())} baris cocok rule."
    )
    return result_df


def apply_transform_steps(
    data_df: pd.DataFrame,
    transforms_cfg: list[dict] | None,
    log: LogFn,
) -> pd.DataFrame:
    if not transforms_cfg:
        log("Tidak ada transform tambahan. Proses lanjut ke output.")
        return data_df.copy()

    result_df = data_df.copy()
    for idx, transform_cfg in enumerate(transforms_cfg, start=1):
        transform_type = str(transform_cfg.get("type", "")).strip()
        if transform_type == "ensure_optional_columns":
            result_df = _apply_optional_columns_transform(result_df, transform_cfg, log)
        elif transform_type == "filter_rows":
            result_df = _apply_filter_transform(result_df, transform_cfg, log)
        elif transform_type == "formula":
            result_df = _apply_formula_transform(result_df, transform_cfg, log)
        elif transform_type == "conditional":
            result_df = _apply_conditional_transform(result_df, transform_cfg, log)
        else:
            raise ValueError(f"Transform step {idx} memakai type yang tidak didukung: '{transform_type}'.")
    return result_df


def _normalize_as_list(value: str | list[str], context: str) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError(f"{context} harus string atau list string.")


def _build_grouped_output(item: dict, data_df: pd.DataFrame, sheet_name: str) -> pd.DataFrame:
    group_cfg = item["group_by"]
    group_columns = _normalize_as_list(group_cfg["by"], f"Group by '{sheet_name}'.by")
    aggregations = group_cfg["aggregations"]
    aggregation_columns = [str(column) for column in aggregations]

    _ensure_columns_exist(
        data_df,
        [*group_columns, *aggregation_columns],
        f"Group by '{sheet_name}'",
    )

    grouped_df = (
        data_df.groupby(group_columns, dropna=False)
        .agg({str(column): str(func) for column, func in aggregations.items()})
        .reset_index()
    )

    columns = item.get("columns")
    if columns is not None:
        missing_columns = [column for column in columns if column not in grouped_df.columns]
        if missing_columns:
            raise ValueError(
                f"Output '{sheet_name}' gagal, kolom tidak ditemukan: {', '.join(missing_columns)}"
            )
        grouped_df = grouped_df.loc[:, columns].copy()

    return grouped_df


def build_output_sheets(outputs_cfg: list[dict], data_df: pd.DataFrame, log: LogFn) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}

    for item in outputs_cfg:
        sheet_name = str(item["sheet_name"])
        if "pivot" in item:
            pivot_cfg = item["pivot"]
            index_cols = _normalize_as_list(pivot_cfg["index"], f"Pivot '{sheet_name}'.index")
            value_cols = _normalize_as_list(pivot_cfg["values"], f"Pivot '{sheet_name}'.values")
            aggfunc = pivot_cfg.get("aggfunc", "sum")

            missing_columns = [
                col for col in [*index_cols, *value_cols] if col not in data_df.columns
            ]
            if missing_columns:
                raise ValueError(
                    f"Pivot '{sheet_name}' gagal, kolom tidak ditemukan: {', '.join(missing_columns)}"
                )

            sheet_df = pd.pivot_table(
                data_df,
                index=index_cols,
                values=value_cols,
                aggfunc=aggfunc,
                dropna=False,
            ).reset_index()
        elif "group_by" in item:
            sheet_df = _build_grouped_output(item, data_df, sheet_name)
        elif "columns" in item:
            columns = item["columns"]
            if not isinstance(columns, list):
                raise ValueError(f"Output '{sheet_name}' memiliki columns yang tidak valid.")
            missing_columns = [col for col in columns if col not in data_df.columns]
            if missing_columns:
                raise ValueError(
                    f"Output '{sheet_name}' gagal, kolom tidak ditemukan: {', '.join(missing_columns)}"
                )
            sheet_df = data_df.loc[:, columns].copy()
        else:
            sheet_df = data_df.copy()

        log(f"Output '{sheet_name}' siap ({len(sheet_df)} baris).")
        result[sheet_name] = sheet_df

    return result
