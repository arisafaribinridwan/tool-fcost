from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from pathlib import Path
import re

import pandas as pd

from app.services.transform_service import (
    match_symptom_rule,
    prepare_symptom_rule_table,
    resolve_master_path,
)


LogFn = Callable[[str], None]


@dataclass(frozen=True)
class RecipeExecutionResult:
    final_df: pd.DataFrame
    output_sheets: dict[str, pd.DataFrame]
    source_df_for_header: pd.DataFrame


def _normalize_text(value: object, *, case_sensitive: bool = False) -> str:
    if pd.isna(value):
        return ""
    normalized = " ".join(str(value).strip().split())
    if case_sensitive:
        return normalized
    return normalized.casefold()


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


def _normalize_exact_key(value: object, matching_cfg: dict | None) -> str:
    config = matching_cfg or {}
    normalized = _normalize_with_options(
        value,
        {
            "trim": config.get("trim", True),
            "case_sensitive": config.get("case_sensitive", True),
        },
    )
    normalizer = config.get("normalizer")
    if normalizer is None:
        return normalized
    if normalizer == "compact_text":
        return "".join(char for char in normalized if char.isalnum())
    raise ValueError(f"Normalisasi key tidak didukung: '{normalizer}'.")


def _blank_mask(series: pd.Series) -> pd.Series:
    return series.isna() | series.map(lambda value: _normalize_text(value, case_sensitive=True)).eq("")


def _coerce_numeric_series(series: pd.Series, context: str) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    invalid_mask = numeric.isna() & ~_blank_mask(series)
    if invalid_mask.any():
        raise ValueError(
            f"{context} memerlukan kolom numerik. Nilai tidak valid ditemukan pada kolom '{series.name}'."
        )
    return numeric


def _coerce_numeric_scalar(value: object, context: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{context} harus berupa angka, bukan boolean.")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{context} harus berupa angka yang valid.")
        try:
            return float(normalized)
        except ValueError as exc:
            raise ValueError(f"{context} harus berupa angka yang valid.") from exc
    raise ValueError(f"{context} harus berupa angka yang valid.")


def _condition_mask(data_df: pd.DataFrame, condition_cfg: dict, context: str) -> pd.Series:
    if "column" not in condition_cfg:
        raise ValueError(f"{context} wajib memiliki field 'column'.")

    column = str(condition_cfg["column"])
    if column not in data_df.columns:
        raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")

    supported_operators = {
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
    operators = [name for name in supported_operators if name in condition_cfg]
    if len(operators) != 1:
        raise ValueError(f"{context} harus memiliki tepat satu operator kondisi.")

    operator = operators[0]
    series = data_df[column]
    case_sensitive = bool(condition_cfg.get("case_sensitive", False))

    if operator == "is_blank":
        return _blank_mask(series)
    if operator == "is_not_blank":
        return ~_blank_mask(series)

    value = condition_cfg[operator]
    if operator in {"gt", "gte", "lt", "lte"}:
        numeric_series = _coerce_numeric_series(series, context)
        numeric_value = _coerce_numeric_scalar(value, context)
        if operator == "gt":
            return numeric_series > numeric_value
        if operator == "gte":
            return numeric_series >= numeric_value
        if operator == "lt":
            return numeric_series < numeric_value
        return numeric_series <= numeric_value

    if operator == "contains":
        token = _normalize_text(value, case_sensitive=case_sensitive)
        normalized = series.map(
            lambda item: _normalize_text(item, case_sensitive=case_sensitive)
        )
        return normalized.str.contains(token, regex=False)

    if operator in {"equals", "not_equals"}:
        if isinstance(value, str):
            normalized_series = series.map(
                lambda item: _normalize_text(item, case_sensitive=case_sensitive)
            )
            normalized_value = _normalize_text(value, case_sensitive=case_sensitive)
            mask = normalized_series.eq(normalized_value)
        else:
            mask = series.eq(value)
        return ~mask if operator == "not_equals" else mask

    if operator in {"in", "not_in"}:
        if not isinstance(value, list):
            raise ValueError(f"{context} operator '{operator}' harus berupa list.")
        if all(isinstance(item, str) for item in value):
            normalized_series = series.map(
                lambda item: _normalize_text(item, case_sensitive=case_sensitive)
            )
            normalized_values = {
                _normalize_text(item, case_sensitive=case_sensitive) for item in value
            }
            mask = normalized_series.isin(normalized_values)
        else:
            mask = series.isin(value)
        return ~mask if operator == "not_in" else mask

    raise ValueError(f"{context} memakai operator yang tidak didukung: '{operator}'.")


def _evaluate_case_condition(data_df: pd.DataFrame, condition_cfg: dict, context: str) -> pd.Series:
    if len(condition_cfg) != 1:
        raise ValueError(f"{context} harus memiliki tepat satu jenis kondisi.")

    condition_type, payload = next(iter(condition_cfg.items()))
    if not isinstance(payload, dict):
        raise ValueError(f"{context} harus berupa object.")

    if condition_type == "len_eq":
        column = str(payload["column"])
        if column not in data_df.columns:
            raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")
        expected_length = int(payload["value"])
        return data_df[column].map(lambda value: len(str(value)) if not pd.isna(value) else 0).eq(expected_length)

    if condition_type == "starts_with":
        column = str(payload["column"])
        if column not in data_df.columns:
            raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")
        prefix = str(payload["value"])
        case_sensitive = bool(payload.get("case_sensitive", True))
        if case_sensitive:
            return data_df[column].fillna("").astype(str).str.startswith(prefix)
        return data_df[column].fillna("").astype(str).str.casefold().str.startswith(prefix.casefold())

    raise ValueError(f"{context} memakai tipe kondisi yang tidak didukung: '{condition_type}'.")


def _literal_or_series(value: object, index: pd.Index) -> pd.Series:
    return pd.Series(value, index=index, dtype="object")


def _evaluate_expression(data_df: pd.DataFrame, expression_cfg: object, context: str) -> pd.Series:
    if not isinstance(expression_cfg, dict):
        return _literal_or_series(expression_cfg, data_df.index)

    if len(expression_cfg) != 1:
        raise ValueError(f"{context} harus memiliki tepat satu operator expression.")

    operator, payload = next(iter(expression_cfg.items()))

    if operator == "substring":
        column = str(payload["column"])
        if column not in data_df.columns:
            raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")
        start = int(payload["start"])
        length = int(payload["length"])
        values = data_df[column].fillna("").astype(str)
        result = values.str.slice(start, start + length)
        short_mask = values.str.len() < (start + length)
        result.loc[short_mask] = None
        return result

    if operator == "add":
        columns = payload["columns"]
        null_as_zero = bool(payload.get("null_as_zero", False))
        if not isinstance(columns, list) or not columns:
            raise ValueError(f"{context} add.columns harus berupa list dan minimal 1 item.")
        result = pd.Series(0.0, index=data_df.index)
        for column in columns:
            column_name = str(column)
            if column_name not in data_df.columns:
                raise ValueError(f"{context} gagal, kolom '{column_name}' tidak ditemukan.")
            numeric = _coerce_numeric_series(data_df[column_name], context)
            if null_as_zero:
                numeric = numeric.fillna(0)
            result = result + numeric
        return result

    if operator == "divide":
        left = _evaluate_expression(data_df, payload["left"], f"{context} divide.left")
        right = _evaluate_expression(data_df, payload["right"], f"{context} divide.right")
        left_numeric = pd.to_numeric(left, errors="coerce")
        right_numeric = pd.to_numeric(right, errors="coerce")
        zero_mask = right_numeric.eq(0)
        if zero_mask.any():
            raise ValueError(f"{context} gagal karena pembagi bernilai 0.")
        return left_numeric / right_numeric

    if operator == "ceil":
        value = _evaluate_expression(data_df, payload["value"], f"{context} ceil.value")
        numeric = pd.to_numeric(value, errors="coerce")
        return numeric.map(lambda item: ceil(item) if pd.notna(item) else None)

    if operator == "date_diff_days":
        start_column = str(payload["start_column"])
        end_column = str(payload["end_column"])
        if start_column not in data_df.columns or end_column not in data_df.columns:
            raise ValueError(f"{context} gagal, kolom tanggal tidak ditemukan.")
        start_series = pd.to_datetime(data_df[start_column], errors="coerce")
        end_series = pd.to_datetime(data_df[end_column], errors="coerce")
        return (end_series - start_series).dt.days

    if operator == "case":
        result = pd.Series("", index=data_df.index, dtype="object")
        remaining_mask = pd.Series(True, index=data_df.index)
        for idx, item in enumerate(payload, start=1):
            if "else" in item:
                else_series = _evaluate_expression(
                    data_df,
                    item["else"],
                    f"{context} case[{idx}].else",
                )
                result.loc[remaining_mask] = else_series.loc[remaining_mask]
                remaining_mask = pd.Series(False, index=data_df.index)
                continue
            condition_mask = _evaluate_case_condition(
                data_df,
                item["when"],
                f"{context} case[{idx}]",
            )
            then_series = _evaluate_expression(
                data_df,
                item["then"],
                f"{context} case[{idx}].then",
            )
            applied_mask = remaining_mask & condition_mask
            result.loc[applied_mask] = then_series.loc[applied_mask]
            remaining_mask = remaining_mask & ~condition_mask
        return result

    raise ValueError(f"{context} memakai expression yang tidak didukung: '{operator}'.")


def _load_excel_raw_sheet(source_path: Path, sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(source_path, sheet_name=sheet_name, header=None, keep_default_na=False)


def _resolve_sheet_names(source_path: Path, selector_cfg: dict) -> list[str]:
    if source_path.suffix.lower() != ".xlsx":
        raise ValueError("Recipe step 'extract_sheet' hanya mendukung source .xlsx.")

    workbook = pd.ExcelFile(source_path)
    contains = str(selector_cfg["contains"])
    case_sensitive = bool(selector_cfg.get("case_sensitive", False))
    candidates: list[str] = []
    for sheet_name in workbook.sheet_names:
        haystack = sheet_name if case_sensitive else sheet_name.casefold()
        needle = contains if case_sensitive else contains.casefold()
        if needle in haystack:
            candidates.append(sheet_name)

    if not candidates:
        raise ValueError(f"Sheet dengan selector '{contains}' tidak ditemukan pada source.")
    return candidates


def _normalize_header(value: object, *, case_sensitive: bool, normalize: bool) -> str:
    text = "" if pd.isna(value) else str(value)
    if normalize:
        text = " ".join(text.strip().split())
    if not case_sensitive:
        text = text.casefold()
    return text


def _detect_header_row(raw_df: pd.DataFrame, header_cfg: dict, label: str) -> int:
    scan_rows = header_cfg["scan_rows"]
    start_row = int(scan_rows[0])
    end_row = int(scan_rows[1])
    case_sensitive = bool(header_cfg.get("case_sensitive", False))
    normalize = bool(header_cfg.get("normalize", True))
    required = [str(item) for item in header_cfg["required"]]
    normalized_required = {
        _normalize_header(item, case_sensitive=case_sensitive, normalize=normalize)
        for item in required
    }

    for row_number in range(start_row, end_row + 1):
        row_index = row_number - 1
        if row_index >= len(raw_df.index):
            break
        header_values = {
            _normalize_header(value, case_sensitive=case_sensitive, normalize=normalize)
            for value in raw_df.iloc[row_index].tolist()
        }
        if normalized_required.issubset(header_values):
            return row_index

    raise ValueError(f"Header {label} tidak ditemukan dalam row scan {start_row}..{end_row}.")


def _build_sheet_dataframe(source_path: Path, step_cfg: dict, log: LogFn) -> pd.DataFrame:
    header_cfg = step_cfg["header_locator"]
    candidate_sheets = _resolve_sheet_names(source_path, step_cfg["sheet_selector"])
    last_error: ValueError | None = None

    for sheet_name in candidate_sheets:
        raw_df = _load_excel_raw_sheet(source_path, sheet_name)
        try:
            header_index = _detect_header_row(raw_df, header_cfg, sheet_name)
        except ValueError as exc:
            last_error = exc
            continue

        header_row = raw_df.iloc[header_index].tolist()
        data_rows = raw_df.iloc[header_index + 1 :].reset_index(drop=True).copy()
        data_rows.columns = header_row
        data_rows = data_rows.dropna(how="all")
        data_rows = data_rows.loc[
            :, [column for column in data_rows.columns if str(column).strip() != ""]
        ]

        log(f"Sheet '{sheet_name}' dipakai untuk step '{step_cfg['id']}'.")
        return data_rows.reset_index(drop=True)

    if last_error is not None:
        raise last_error
    raise ValueError(f"Sheet valid untuk step '{step_cfg['id']}' tidak ditemukan.")


def _apply_extract_filters(data_df: pd.DataFrame, filters_cfg: list[dict] | None) -> pd.DataFrame:
    if not filters_cfg:
        return data_df

    filtered_df = data_df.copy()
    for idx, filter_cfg in enumerate(filters_cfg, start=1):
        mask = _condition_mask(filtered_df, filter_cfg, f"Filter extract {idx}")
        filtered_df = filtered_df.loc[mask].copy()
    return filtered_df


def _select_and_rename_columns(data_df: pd.DataFrame, select_cfg: dict, step_id: str) -> pd.DataFrame:
    missing_columns = [column for column in select_cfg if column not in data_df.columns]
    if missing_columns:
        raise ValueError(
            f"Step '{step_id}' gagal, kolom source tidak ditemukan: {', '.join(missing_columns)}"
        )
    selected = data_df.loc[:, list(select_cfg.keys())].copy()
    return selected.rename(columns={str(src): str(dst) for src, dst in select_cfg.items()})


def _append_dataset(existing_df: pd.DataFrame | None, new_df: pd.DataFrame) -> pd.DataFrame:
    if existing_df is None:
        return new_df.reset_index(drop=True)
    all_columns = list(dict.fromkeys([*existing_df.columns.tolist(), *new_df.columns.tolist()]))
    left = existing_df.reindex(columns=all_columns)
    right = new_df.reindex(columns=all_columns)
    return pd.concat([left, right], ignore_index=True)


def _apply_extract_step(
    datasets: dict[str, pd.DataFrame],
    source_path: Path,
    step_cfg: dict,
    canonical_columns: list[str],
    log: LogFn,
) -> None:
    extracted_df = _build_sheet_dataframe(source_path, step_cfg, log)
    extracted_df = _apply_extract_filters(extracted_df, step_cfg.get("filters"))
    result_df = _select_and_rename_columns(extracted_df, step_cfg["select"], str(step_cfg["id"]))

    for column, value in (step_cfg.get("fill_missing") or {}).items():
        result_df[str(column)] = value

    if canonical_columns:
        for column in canonical_columns:
            if column not in result_df.columns:
                result_df[column] = None
        result_df = result_df.loc[:, canonical_columns].copy()

    target_dataset = str(step_cfg["write_to"])
    mode = str(step_cfg.get("mode", "replace"))
    if mode == "replace":
        datasets[target_dataset] = result_df.reset_index(drop=True)
    elif mode == "append":
        datasets[target_dataset] = _append_dataset(datasets.get(target_dataset), result_df)
    else:
        raise ValueError(f"Mode write dataset tidak didukung: '{mode}'.")

    log(f"Step '{step_cfg['id']}' selesai: dataset '{target_dataset}' berisi {len(datasets[target_dataset])} baris.")


class _RecipeContext:
    def __init__(self, project_root: Path, masters_dir: Path) -> None:
        self.project_root = project_root
        self.masters_dir = masters_dir
        self._master_cache: dict[tuple[str, str], pd.DataFrame] = {}

    def load_master_sheet(self, file_ref: str, sheet_name: str) -> pd.DataFrame:
        cache_key = (file_ref, sheet_name)
        if cache_key not in self._master_cache:
            master_path = resolve_master_path(file_ref, self.project_root, self.masters_dir)
            if not master_path.exists():
                raise ValueError(f"File master tidak ditemukan: {master_path}")
            self._master_cache[cache_key] = pd.read_excel(
                master_path,
                sheet_name=sheet_name,
                keep_default_na=False,
            )
        return self._master_cache[cache_key].copy()


def _apply_derive_column_step(data_df: pd.DataFrame, step_cfg: dict, log: LogFn) -> pd.DataFrame:
    target = str(step_cfg["target"])
    result_df = data_df.copy()
    result_series = _evaluate_expression(result_df, step_cfg["expression"], f"Step '{step_cfg['id']}'")
    result_df[target] = result_series
    log(f"Step '{step_cfg['id']}' selesai: kolom '{target}' ditambahkan.")
    return result_df


def _evaluate_update_operation(data_df: pd.DataFrame, op_cfg: dict, context: str) -> pd.Series:
    if "multiply" in op_cfg:
        payload = op_cfg["multiply"]
        column = str(payload["column"])
        if column not in data_df.columns:
            raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")
        numeric = _coerce_numeric_series(data_df[column], context)
        factor = _coerce_numeric_scalar(payload["value"], context)
        return numeric * factor
    if "set" in op_cfg:
        return pd.Series(op_cfg["set"], index=data_df.index)
    raise ValueError(f"{context} memakai operasi update yang tidak didukung.")


def _apply_update_columns_step(data_df: pd.DataFrame, step_cfg: dict, log: LogFn) -> pd.DataFrame:
    result_df = data_df.copy()
    mask = _condition_mask(result_df, step_cfg["when"], f"Step '{step_cfg['id']}'")
    for column, operation_cfg in step_cfg["updates"].items():
        result_series = _evaluate_update_operation(result_df, operation_cfg, f"Step '{step_cfg['id']}'")
        result_df.loc[mask, str(column)] = result_series.loc[mask]
    log(f"Step '{step_cfg['id']}' selesai: {int(mask.sum())} baris diupdate.")
    return result_df


def _replace_exact_keys_in_text(source_text: str, lookup_map: dict[str, object], matching_cfg: dict) -> str:
    if not source_text or not lookup_map:
        return source_text

    ordered_keys = [key for key in sorted(lookup_map.keys(), key=len, reverse=True) if key]
    if not ordered_keys:
        return source_text

    flags = 0 if bool(matching_cfg.get("case_sensitive", True)) else re.IGNORECASE
    alternation = "|".join(re.escape(key) for key in ordered_keys)
    pattern = re.compile(rf"(?<![0-9A-Za-z])({alternation})(?![0-9A-Za-z])", flags)

    def _replacement(match: re.Match) -> str:
        normalized_match = _normalize_exact_key(match.group(1), matching_cfg)
        canonical = lookup_map.get(normalized_match)
        if canonical is None:
            return match.group(0)
        if pd.isna(canonical):
            return ""
        return str(canonical)

    return pattern.sub(_replacement, source_text)


def _apply_lookup_exact_step(data_df: pd.DataFrame, step_cfg: dict, context: _RecipeContext, log: LogFn) -> pd.DataFrame:
    source_column = str(step_cfg["source_column"])
    target_column = str(step_cfg["target_column"])
    if source_column not in data_df.columns:
        raise ValueError(f"Step '{step_cfg['id']}' gagal, kolom '{source_column}' tidak ditemukan.")

    master_cfg = step_cfg["master"]
    matching_cfg = step_cfg.get("matching", {})
    alias_separator = matching_cfg.get("alias_separator")
    if alias_separator is not None and (not isinstance(alias_separator, str) or not alias_separator):
        raise ValueError(
            f"Step '{step_cfg['id']}' gagal, matching.alias_separator harus berupa string non-kosong."
        )

    match_mode = str(matching_cfg.get("match_mode", "exact"))
    if match_mode not in {"exact", "contains"}:
        raise ValueError(
            f"Step '{step_cfg['id']}' gagal, matching.match_mode harus salah satu dari: contains, exact."
        )

    master_df = context.load_master_sheet(str(master_cfg["file"]), str(master_cfg["sheet"]))
    key_column = str(master_cfg["key"])
    value_column = str(master_cfg["value"])
    if key_column not in master_df.columns or value_column not in master_df.columns:
        raise ValueError(f"Step '{step_cfg['id']}' gagal, kolom master tidak lengkap.")

    aliases = {
        _normalize_exact_key(source_key, matching_cfg): _normalize_exact_key(target_key, matching_cfg)
        for source_key, target_key in (matching_cfg.get("aliases") or {}).items()
    }
    lookup_map: dict[str, object] = {}
    for _, row in master_df.iterrows():
        raw_key = row[key_column]
        if isinstance(alias_separator, str):
            split_keys = str(raw_key).split(alias_separator) if not pd.isna(raw_key) else [""]
            for split_key in split_keys:
                normalized_split_key = _normalize_exact_key(split_key, matching_cfg)
                if normalized_split_key:
                    lookup_map[normalized_split_key] = row[value_column]
        else:
            normalized_key = _normalize_exact_key(raw_key, matching_cfg)
            if normalized_key:
                lookup_map[normalized_key] = row[value_column]

    result_df = data_df.copy()
    values: list[object] = []
    on_missing = step_cfg.get("on_missing_match")
    on_blank = step_cfg.get("on_blank_source")
    for source_value in result_df[source_column]:
        normalized_key = _normalize_exact_key(source_value, matching_cfg)
        if not normalized_key:
            values.append(on_blank)
            continue
        normalized_key = aliases.get(normalized_key, normalized_key)
        if normalized_key in lookup_map:
            values.append(lookup_map[normalized_key])
            continue

        if match_mode == "contains":
            source_text = "" if pd.isna(source_value) else str(source_value)
            replaced_text = _replace_exact_keys_in_text(source_text, lookup_map, matching_cfg)
            if replaced_text != source_text:
                values.append(replaced_text)
                continue

        if on_missing == "keep_original":
            values.append(source_value)
        else:
            values.append(on_missing)

    result_df[target_column] = values
    log(f"Step '{step_cfg['id']}' selesai: lookup exact ke kolom '{target_column}'.")
    return result_df


def _matcher_matches(source_value: object, master_value: object, matcher_cfg: dict) -> bool:
    normalize_cfg = matcher_cfg.get("normalize", {})
    blank_as_wildcard = bool(normalize_cfg.get("blank_as_wildcard", False))
    source_normalized = _normalize_with_options(source_value, normalize_cfg)
    master_normalized = _normalize_with_options(master_value, normalize_cfg)

    if blank_as_wildcard and not master_normalized:
        return True

    mode = str(matcher_cfg["mode"])
    if mode == "equals":
        return source_normalized == master_normalized
    if mode == "contains":
        wildcard = str(normalize_cfg.get("wildcard", "*"))
        token = master_normalized.replace(wildcard, "")
        if not token:
            return True
        return token in source_normalized
    if mode == "regex":
        try:
            return re.search(master_normalized, source_normalized) is not None
        except re.error as exc:
            raise ValueError(f"Regex matcher tidak valid: {exc}") from exc
    raise ValueError(f"Mode matcher tidak didukung: '{mode}'.")


def _validate_and_sort_lookup_rules_master(master_df: pd.DataFrame, step_cfg: dict) -> pd.DataFrame:
    priority_column = step_cfg.get("matching", {}).get("priority_column")
    if not isinstance(priority_column, str) or not priority_column.strip():
        return master_df

    column_name = priority_column.strip()
    if column_name not in master_df.columns:
        raise ValueError(
            f"Step '{step_cfg['id']}' gagal, kolom priority '{column_name}' tidak ditemukan pada master."
        )

    result_df = master_df.copy()
    result_df["_row_order"] = range(len(result_df))

    invalid_rows: list[str] = []
    parsed_priorities: list[int] = []
    for idx, value in enumerate(result_df[column_name], start=2):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            invalid_rows.append(str(idx))
            parsed_priorities.append(0)
            continue
        if parsed <= 0:
            invalid_rows.append(str(idx))
        parsed_priorities.append(parsed)

    if invalid_rows:
        raise ValueError(
            f"Step '{step_cfg['id']}' gagal, priority invalid pada baris: {', '.join(invalid_rows)}. "
            "Priority harus integer positif."
        )

    result_df[column_name] = parsed_priorities
    result_df = result_df.sort_values([column_name, "_row_order"], kind="stable")
    return result_df.drop(columns=["_row_order"]).reset_index(drop=True)


def _apply_lookup_rules_step(data_df: pd.DataFrame, step_cfg: dict, context: _RecipeContext, log: LogFn) -> pd.DataFrame:
    master_cfg = step_cfg["master"]
    master_df = context.load_master_sheet(str(master_cfg["file"]), str(master_cfg["sheet"]))
    target_column = str(step_cfg["target_column"])
    value_column = str(master_cfg["value"])
    master_df = _validate_and_sort_lookup_rules_master(master_df, step_cfg)
    if value_column not in master_df.columns:
        raise ValueError(f"Step '{step_cfg['id']}' gagal, kolom value master tidak ditemukan.")

    for matcher in step_cfg["matching"]["matchers"]:
        source_col = str(matcher["source"])
        master_col = str(matcher["master"])
        if source_col not in data_df.columns:
            raise ValueError(f"Step '{step_cfg['id']}' gagal, kolom '{source_col}' tidak ditemukan.")
        if (
            str(master_cfg.get("sheet", "")).casefold() == "symptom"
            and target_column == "symptom"
            and source_col == "symptom_comment"
        ):
            continue
        if master_col not in master_df.columns:
            raise ValueError(f"Step '{step_cfg['id']}' gagal, kolom master '{master_col}' tidak ditemukan.")

    if str(master_cfg.get("sheet", "")).casefold() == "symptom" and target_column == "symptom":
        symptom_rules = prepare_symptom_rule_table(
            master_df,
            context=f"Sheet symptom '{master_cfg['sheet']}' pada step '{step_cfg['id']}'",
        )
        if "part_name" not in data_df.columns or "symptom_comment" not in data_df.columns:
            raise ValueError(
                f"Step '{step_cfg['id']}' gagal, kolom source untuk symptom rules tidak lengkap."
            )

        results: list[object] = []
        on_missing = step_cfg.get("on_missing_match")
        for _, source_row in data_df.iterrows():
            resolved = on_missing
            source_part = _normalize_text(source_row["part_name"], case_sensitive=True)
            for _, master_row in symptom_rules.iterrows():
                rule_part = _normalize_text(master_row["part_name"], case_sensitive=True)
                if source_part != rule_part:
                    continue
                if match_symptom_rule(source_row["symptom_comment"], master_row):
                    resolved = master_row["symptom"]
                    break
            results.append(resolved)

        result_df = data_df.copy()
        result_df[target_column] = results
        log(f"Step '{step_cfg['id']}' selesai: symptom rules tervalidasi dan diterapkan.")
        return result_df

    results: list[object] = []
    on_missing = step_cfg.get("on_missing_match")
    for _, source_row in data_df.iterrows():
        resolved = on_missing
        for _, master_row in master_df.iterrows():
            if all(
                _matcher_matches(
                    source_row[str(matcher["source"])],
                    master_row[str(matcher["master"])],
                    matcher,
                )
                for matcher in step_cfg["matching"]["matchers"]
            ):
                resolved = master_row[value_column]
                break
        results.append(resolved)

    result_df = data_df.copy()
    result_df[target_column] = results
    log(f"Step '{step_cfg['id']}' selesai: lookup rules ke kolom '{target_column}'.")
    return result_df


def _apply_map_ranges_step(data_df: pd.DataFrame, step_cfg: dict, log: LogFn) -> pd.DataFrame:
    source_column = str(step_cfg["source_column"])
    target_column = str(step_cfg["target_column"])
    if source_column not in data_df.columns:
        raise ValueError(f"Step '{step_cfg['id']}' gagal, kolom '{source_column}' tidak ditemukan.")

    numeric = pd.to_numeric(data_df[source_column], errors="coerce")
    values: list[object] = []
    for raw_value, numeric_value in zip(data_df[source_column], numeric, strict=False):
        if pd.isna(raw_value) or (isinstance(raw_value, str) and not raw_value.strip()):
            values.append(step_cfg.get("on_blank_source"))
            continue
        resolved = None
        for range_cfg in step_cfg["ranges"]:
            if "lte" in range_cfg and pd.notna(numeric_value) and numeric_value <= float(range_cfg["lte"]):
                resolved = range_cfg["value"]
                break
            if "gte" in range_cfg and pd.notna(numeric_value) and numeric_value >= float(range_cfg["gte"]):
                resolved = range_cfg["value"]
                break
        values.append(resolved)

    result_df = data_df.copy()
    result_df[target_column] = values
    log(f"Step '{step_cfg['id']}' selesai: range map ke kolom '{target_column}'.")
    return result_df


def _apply_duplicate_update(group_df: pd.DataFrame, row_indexes: list[int], updates_cfg: dict, *, is_winner: bool) -> pd.DataFrame:
    result_group = group_df.copy()
    sum_cache = {
        column: pd.to_numeric(group_df[column], errors="coerce").fillna(0).sum()
        for column, cfg in updates_cfg.items()
        if isinstance(cfg, dict) and cfg.get("aggregate") == "sum_group"
    }

    winner_index = row_indexes[0] if row_indexes else None
    for row_index in group_df.index:
        current_updates = updates_cfg
        for column, cfg in current_updates.items():
            target_column = str(column)
            if "set" in cfg:
                result_group.at[row_index, target_column] = cfg["set"]
            elif cfg.get("aggregate") == "sum_group":
                if is_winner and row_index == winner_index:
                    result_group.at[row_index, target_column] = sum_cache[target_column]
            elif cfg.get("keep_original"):
                continue
    return result_group


def _normalize_signature(values: pd.Series) -> tuple[str, ...]:
    normalized = [str(value).strip().upper() for value in values if str(value).strip()]
    return tuple(sorted(set(normalized)))


def _apply_duplicate_group_rewrite_step(data_df: pd.DataFrame, step_cfg: dict, log: LogFn) -> pd.DataFrame:
    group_column = str(step_cfg["group_by"])
    section_column = str(step_cfg["section_column"])
    required = [group_column, section_column]
    missing = [column for column in required if column not in data_df.columns]
    if missing:
        raise ValueError(f"Step '{step_cfg['id']}' gagal, kolom tidak ditemukan: {', '.join(missing)}")

    result_df = data_df.copy()
    for _, group_index in result_df.groupby(group_column, sort=False).groups.items():
        row_indexes = list(group_index)
        if len(row_indexes) <= 1:
            continue

        group_df = result_df.loc[row_indexes].copy()
        section = str(group_df.iloc[0][section_column])
        dispatch_cfg = step_cfg["dispatch"].get(section)
        if dispatch_cfg is None:
            continue

        winner_index: int | None = None
        if section == "SASS":
            parts_cost = pd.to_numeric(group_df[dispatch_cfg["winner_selection"]["column"]], errors="coerce").fillna(0)
            max_parts = parts_cost.max()
            candidates = group_df.loc[parts_cost.eq(max_parts)]
            if len(candidates) > 1:
                tie_column = str(dispatch_cfg["winner_selection"]["tie_breakers"][0]["column"])
                tie_numeric = pd.to_numeric(candidates[tie_column], errors="coerce").fillna(0)
                max_tie = tie_numeric.max()
                candidates = candidates.loc[tie_numeric.eq(max_tie)]
            winner_index = int(candidates.index[0])
        elif section == "GQS":
            part_column = str(dispatch_cfg["required_columns"][0])
            signature = _normalize_signature(group_df[part_column])
            matched_rule = None
            for rule in sorted(dispatch_cfg["winner_rules"], key=lambda item: int(item["priority"])):
                expected_signature = tuple(sorted(str(item).strip().upper() for item in rule["parts_signature"]))
                if signature == expected_signature:
                    matched_rule = rule
                    break
            if matched_rule is None:
                if dispatch_cfg.get("on_unmatched_signature") == "warn_and_keep_group":
                    log(
                        f"Warning: step '{step_cfg['id']}' tidak menemukan rule GQS untuk signature {signature}."
                    )
                    continue
                raise ValueError(f"Step '{step_cfg['id']}' gagal, rule GQS tidak ditemukan untuk signature {signature}.")
            winner_part = str(matched_rule["winner_part_name"]).strip().upper()
            matched_rows = group_df[group_df[part_column].fillna("").astype(str).str.strip().str.upper().eq(winner_part)]
            if matched_rows.empty:
                raise ValueError(f"Step '{step_cfg['id']}' gagal, winner part '{winner_part}' tidak ditemukan pada group.")
            winner_index = int(matched_rows.index[0])
        else:
            continue

        winner_updates = dispatch_cfg["winner_updates"]
        loser_updates = dispatch_cfg["loser_updates"]

        sum_cache = {
            column: pd.to_numeric(group_df[column], errors="coerce").fillna(0).sum()
            for column, cfg in winner_updates.items()
            if cfg.get("aggregate") == "sum_group"
        }

        for row_index in group_df.index:
            target_updates = winner_updates if row_index == winner_index else loser_updates
            for column, cfg in target_updates.items():
                target_column = str(column)
                if "set" in cfg:
                    result_df.at[row_index, target_column] = cfg["set"]
                elif cfg.get("aggregate") == "sum_group":
                    if row_index == winner_index:
                        result_df.at[row_index, target_column] = sum_cache[target_column]
                    else:
                        result_df.at[row_index, target_column] = 0
                elif cfg.get("keep_original"):
                    continue

    log(f"Step '{step_cfg['id']}' selesai: duplicate group rewrite diterapkan.")
    return result_df


def _build_output_sheets(data_df: pd.DataFrame, outputs_cfg: list[dict], log: LogFn) -> dict[str, pd.DataFrame]:
    output_sheets: dict[str, pd.DataFrame] = {}
    for item in outputs_cfg:
        sheet_name = str(item["sheet_name"])
        columns = [str(column) for column in item.get("columns", [])]
        missing = [column for column in columns if column not in data_df.columns]
        if missing:
            raise ValueError(f"Output '{sheet_name}' gagal, kolom tidak ditemukan: {', '.join(missing)}")
        output_sheets[sheet_name] = data_df.loc[:, columns].copy()
        log(f"Output recipe '{sheet_name}' siap ({len(output_sheets[sheet_name])} baris).")
    return output_sheets


def execute_step_recipe(
    *,
    source_path: Path,
    recipe_cfg: dict,
    project_root: Path,
    masters_dir: Path,
    log: LogFn,
) -> RecipeExecutionResult:
    canonical_columns = [str(column) for column in recipe_cfg.get("datasets", {}).get("canonical_columns", [])]
    working_dataset = str(recipe_cfg.get("datasets", {}).get("working_dataset", "result"))
    datasets: dict[str, pd.DataFrame] = {}
    context = _RecipeContext(project_root=project_root, masters_dir=masters_dir)

    for step_cfg in recipe_cfg["steps"]:
        step_type = str(step_cfg["type"])
        if step_type == "extract_sheet":
            _apply_extract_step(datasets, source_path, step_cfg, canonical_columns, log)
            continue

        if working_dataset not in datasets:
            raise ValueError(f"Dataset kerja '{working_dataset}' belum tersedia saat step '{step_cfg['id']}'.")

        current_df = datasets[working_dataset]
        if step_type == "derive_column":
            datasets[working_dataset] = _apply_derive_column_step(current_df, step_cfg, log)
        elif step_type == "update_columns":
            datasets[working_dataset] = _apply_update_columns_step(current_df, step_cfg, log)
        elif step_type in {"lookup_exact", "lookup_exact_replace"}:
            datasets[working_dataset] = _apply_lookup_exact_step(current_df, step_cfg, context, log)
        elif step_type == "lookup_rules":
            datasets[working_dataset] = _apply_lookup_rules_step(current_df, step_cfg, context, log)
        elif step_type == "map_ranges":
            datasets[working_dataset] = _apply_map_ranges_step(current_df, step_cfg, log)
        elif step_type == "duplicate_group_rewrite":
            datasets[working_dataset] = _apply_duplicate_group_rewrite_step(current_df, step_cfg, log)
        else:
            raise ValueError(f"Step type tidak didukung: '{step_type}'.")

    final_df = datasets.get(working_dataset)
    if final_df is None:
        raise ValueError(f"Dataset kerja '{working_dataset}' tidak terbentuk.")

    output_sheets = _build_output_sheets(final_df, recipe_cfg["outputs"], log)
    return RecipeExecutionResult(
        final_df=final_df,
        output_sheets=output_sheets,
        source_df_for_header=final_df,
    )
