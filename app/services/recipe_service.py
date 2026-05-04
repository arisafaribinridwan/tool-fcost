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
    sheet_layouts: dict[str, str]


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


def _evaluate_expression(
    data_df: pd.DataFrame,
    expression_cfg: object,
    context: str,
    runtime_values: dict[str, object] | None = None,
) -> pd.Series:
    if not isinstance(expression_cfg, dict):
        return _literal_or_series(expression_cfg, data_df.index)

    if len(expression_cfg) != 1:
        raise ValueError(f"{context} harus memiliki tepat satu operator expression.")

    operator, payload = next(iter(expression_cfg.items()))

    if operator == "runtime_value":
        key = str(payload)
        values = runtime_values or {}
        if key not in values:
            raise ValueError(f"{context} gagal, runtime value '{key}' tidak tersedia.")
        return _literal_or_series(values[key], data_df.index)

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

    if operator == "lot_month_date":
        column = str(payload["column"])
        if column not in data_df.columns:
            raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")

        month_by_code = {chr(ord("A") + idx): idx + 1 for idx in range(12)}

        def parse_lot_date(value: object) -> pd.Timestamp | pd.NaT:
            if pd.isna(value):
                return pd.NaT
            text = str(value).strip()
            if len(text) != 3:
                return pd.NaT
            year_text = text[:2]
            month_code = text[2].upper()
            if not year_text.isdigit() or month_code not in month_by_code:
                return pd.NaT
            return pd.Timestamp(year=2000 + int(year_text), month=month_by_code[month_code], day=1)

        return pd.to_datetime(data_df[column].map(parse_lot_date), errors="coerce")

    if operator == "short_year_month_date":
        column = str(payload["column"])
        if column not in data_df.columns:
            raise ValueError(f"{context} gagal, kolom '{column}' tidak ditemukan.")

        current_year = int(payload.get("current_year", pd.Timestamp.today().year))
        current_decade = (current_year // 10) * 10
        current_year_digit = current_year % 10

        def parse_short_year_month_date(value: object) -> pd.Timestamp | pd.NaT:
            if pd.isna(value):
                return pd.NaT
            text = str(value).strip()
            if len(text) != 3 or not text.isdigit():
                return pd.NaT
            year_digit = int(text[0])
            month = int(text[1:])
            if month < 1 or month > 12:
                return pd.NaT
            decade = current_decade if year_digit <= current_year_digit else current_decade - 10
            return pd.Timestamp(year=decade + year_digit, month=month, day=1)

        return pd.to_datetime(data_df[column].map(parse_short_year_month_date), errors="coerce")

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
        left = _evaluate_expression(
            data_df,
            payload["left"],
            f"{context} divide.left",
            runtime_values,
        )
        right = _evaluate_expression(
            data_df,
            payload["right"],
            f"{context} divide.right",
            runtime_values,
        )
        left_numeric = pd.to_numeric(left, errors="coerce")
        right_numeric = pd.to_numeric(right, errors="coerce")
        zero_mask = right_numeric.eq(0)
        if zero_mask.any():
            raise ValueError(f"{context} gagal karena pembagi bernilai 0.")
        return left_numeric / right_numeric

    if operator == "ceil":
        value = _evaluate_expression(
            data_df,
            payload["value"],
            f"{context} ceil.value",
            runtime_values,
        )
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

    if operator == "date_diff_days_with_start_fallback":
        primary_start_column = str(payload["primary_start_column"])
        fallback_start_column = str(payload["fallback_start_column"])
        end_column = str(payload["end_column"])
        required_columns = {primary_start_column, fallback_start_column, end_column}
        if not required_columns.issubset(data_df.columns):
            raise ValueError(f"{context} gagal, kolom tanggal tidak ditemukan.")

        primary_start = pd.to_datetime(data_df[primary_start_column], errors="coerce")
        fallback_start = pd.to_datetime(data_df[fallback_start_column], errors="coerce")
        end_series = pd.to_datetime(data_df[end_column], errors="coerce")
        use_primary_mask = fallback_start.isna() | primary_start.ge(fallback_start)
        start_series = primary_start.where(use_primary_mask, fallback_start)
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
                    runtime_values,
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
                runtime_values,
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
    selector_mode = selector_cfg.get("mode")
    if selector_mode is not None and str(selector_mode) == "single_sheet_workbook":
        if len(workbook.sheet_names) != 1:
            raise ValueError(
                "Mode sheet_selector.single_sheet_workbook membutuhkan tepat 1 sheet pada source workbook."
            )
        return [workbook.sheet_names[0]]

    contains = selector_cfg.get("contains")
    if not isinstance(contains, str) or not contains.strip():
        raise ValueError("sheet_selector.contains wajib berupa string non-kosong.")

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


def _extract_period_text(raw_df: pd.DataFrame, header_index: int) -> str | None:
    for row_index in range(header_index):
        row_values = raw_df.iloc[row_index].tolist()
        for col_index, value in enumerate(row_values):
            text = " ".join(str(value).strip().split()) if not pd.isna(value) else ""
            normalized = text.casefold()
            if normalized.startswith("periode:"):
                return f"Periode: {text.split(':', 1)[1].strip() or '-'}"
            if normalized == "periode":
                for next_value in row_values[col_index + 1 :]:
                    next_text = " ".join(str(next_value).strip().split()) if not pd.isna(next_value) else ""
                    if next_text:
                        return f"Periode: {next_text}"
    return None


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
        data_rows = data_rows.reset_index(drop=True)
        period_text = _extract_period_text(raw_df, header_index)
        if period_text is not None:
            data_rows.attrs["period_text"] = period_text

        log(f"Sheet '{sheet_name}' dipakai untuk step '{step_cfg['id']}'.")
        return data_rows

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
    period_text = extracted_df.attrs.get("period_text")
    extracted_df = _apply_extract_filters(extracted_df, step_cfg.get("filters"))
    result_df = _select_and_rename_columns(extracted_df, step_cfg["select"], str(step_cfg["id"]))
    if period_text is not None:
        result_df.attrs["period_text"] = period_text

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


def _apply_derive_column_step(
    data_df: pd.DataFrame,
    step_cfg: dict,
    log: LogFn,
    runtime_values: dict[str, object] | None = None,
) -> pd.DataFrame:
    target = str(step_cfg["target"])
    result_df = data_df.copy()
    result_series = _evaluate_expression(
        result_df,
        step_cfg["expression"],
        f"Step '{step_cfg['id']}'",
        runtime_values,
    )
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


def _filter_lookup_exact_master(master_df: pd.DataFrame, master_cfg: dict, step_id: str) -> pd.DataFrame:
    filter_cfg = master_cfg.get("filter")
    if filter_cfg is None:
        return master_df
    if not isinstance(filter_cfg, dict):
        raise ValueError(
            f"Step '{step_id}' gagal, master.filter harus berupa object."
        )

    scope_in = filter_cfg.get("scope_in")
    if scope_in is None:
        return master_df
    if not isinstance(scope_in, list) or len(scope_in) == 0 or not all(
        isinstance(item, str) and item.strip() for item in scope_in
    ):
        raise ValueError(
            f"Step '{step_id}' gagal, master.filter.scope_in harus berupa list string non-kosong."
        )

    scope_column = "scope"
    if scope_column not in master_df.columns:
        raise ValueError(
            f"Step '{step_id}' gagal, kolom master '{scope_column}' tidak ditemukan untuk filter scope_in."
        )

    allowed_scopes = {_normalize_text(item, case_sensitive=False) for item in scope_in}
    return master_df[
        master_df[scope_column].map(lambda value: _normalize_text(value, case_sensitive=False)).isin(allowed_scopes)
    ].reset_index(drop=True)


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
    master_df = _filter_lookup_exact_master(master_df, master_cfg, str(step_cfg["id"]))
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


def _apply_summary_column_labels(summary_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    column_labels = cfg.get("column_labels") or {}
    if not isinstance(column_labels, dict) or not column_labels:
        return summary_df

    rename_map = {k: v for k, v in column_labels.items() if k in summary_df.columns}
    if not rename_map:
        return summary_df
    return summary_df.rename(columns=rename_map)


def _add_summary_metadata(summary_df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Tambahkan kolom _row_type untuk styling dan terapkan column_labels dari config."""
    if not summary_df.empty and "section" in summary_df.columns:
        row_types = []
        for section_val in summary_df["section"].astype(str):
            if section_val == "Grand Total":
                row_types.append("grand_total")
            elif section_val.endswith(" Total"):
                row_types.append("subtotal")
            else:
                row_types.append("data")
        summary_df = summary_df.copy()
        summary_df["_row_type"] = row_types

    return _apply_summary_column_labels(summary_df, cfg)


def _build_static_part_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    section_column = str(cfg.get("section_column", "section"))
    part_column = str(cfg.get("part_column", "part_name"))

    static_parts = [str(item) for item in cfg.get("static_parts", ["PANEL", "MAIN_UNIT", "POWER_UNIT"])]

    cost_columns = {
        "Sum of labor_cost": str(cfg.get("labor_cost_column", "labor_cost")),
        "Sum of transportation_cost": str(cfg.get("transportation_cost_column", "transportation_cost")),
        "Sum of parts_cost": str(cfg.get("parts_cost_column", "parts_cost")),
        "Sum of total_cost": str(cfg.get("total_cost_column", "total_cost")),
    }

    required_columns = [section_column, part_column, *cost_columns.values()]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError(
            "Static part summary gagal, kolom tidak ditemukan: " + ", ".join(missing)
        )

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.ne("")].copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df[part_column] = part_series

    for target_col, source_col in cost_columns.items():
        working_df[target_col] = pd.to_numeric(working_df[source_col], errors="coerce").fillna(0)

    grouped_part = part_series.where(part_series.isin(static_parts), "OTHER")
    working_df["_grouped_part"] = grouped_part

    grouped = (
        working_df.groupby([section_column, "_grouped_part"], dropna=False, sort=False)
        .agg(
            {
                "Sum of labor_cost": "sum",
                "Sum of transportation_cost": "sum",
                "Sum of parts_cost": "sum",
                "Sum of total_cost": "sum",
                part_column: "count",
            }
        )
        .reset_index()
        .rename(columns={"_grouped_part": "part_name", part_column: "Count of part_name"})
    )

    output_columns = [
        "section",
        "part_name",
        "Sum of labor_cost",
        "Sum of transportation_cost",
        "Sum of parts_cost",
        "Sum of total_cost",
        "Count of part_name",
    ]

    section_order = working_df[section_column].drop_duplicates().tolist()
    part_order = [*static_parts, "OTHER"]
    rows: list[dict[str, object]] = []

    value_mode = str(cfg.get("value_mode", "numeric")).strip().casefold()
    formula_mode = value_mode == "excel_formula"

    if formula_mode:
        formula_source_sheet = str(cfg.get("formula_source_sheet", "result"))
        formula_refs = {
            "section": str(cfg.get("formula_section_ref", "$W:$W")),
            "part_name": str(cfg.get("formula_part_ref", "$AB:$AB")),
            "Sum of labor_cost": str(cfg.get("formula_labor_ref", "$S:$S")),
            "Sum of transportation_cost": str(cfg.get("formula_transportation_ref", "$T:$T")),
            "Sum of parts_cost": str(cfg.get("formula_parts_ref", "$U:$U")),
            "Sum of total_cost": str(cfg.get("formula_total_ref", "$Z:$Z")),
        }

        def _excel_literal(value: object) -> str:
            return '"' + str(value).replace('"', '""') + '"'

        def _sumifs_formula(value_ref: str, section_value: str, part_value: str) -> str:
            return (
                f"=SUMIFS('{formula_source_sheet}'!{value_ref},"
                f"'{formula_source_sheet}'!{formula_refs['section']},{_excel_literal(section_value)},"
                f"'{formula_source_sheet}'!{formula_refs['part_name']},{_excel_literal(part_value)})"
            )

        def _countifs_formula(section_value: str, part_value: str) -> str:
            return (
                f"=COUNTIFS('{formula_source_sheet}'!{formula_refs['section']},{_excel_literal(section_value)},"
                f"'{formula_source_sheet}'!{formula_refs['part_name']},{_excel_literal(part_value)})"
            )

        def _other_sum_formula(value_ref: str, section_value: str) -> str:
            base = (
                f"SUMIFS('{formula_source_sheet}'!{value_ref},"
                f"'{formula_source_sheet}'!{formula_refs['section']},{_excel_literal(section_value)},"
                f"'{formula_source_sheet}'!{formula_refs['part_name']},\"<>\")"
            )
            minus_parts = "-".join(
                [
                    (
                        f"SUMIFS('{formula_source_sheet}'!{value_ref},"
                        f"'{formula_source_sheet}'!{formula_refs['section']},{_excel_literal(section_value)},"
                        f"'{formula_source_sheet}'!{formula_refs['part_name']},{_excel_literal(part_name)})"
                    )
                    for part_name in static_parts
                ]
            )
            return f"={base}-{minus_parts}"

        def _other_count_formula(section_value: str) -> str:
            base = (
                f"COUNTIFS('{formula_source_sheet}'!{formula_refs['section']},{_excel_literal(section_value)},"
                f"'{formula_source_sheet}'!{formula_refs['part_name']},\"<>\")"
            )
            minus_parts = "-".join(
                [
                    (
                        f"COUNTIFS('{formula_source_sheet}'!{formula_refs['section']},{_excel_literal(section_value)},"
                        f"'{formula_source_sheet}'!{formula_refs['part_name']},{_excel_literal(part_name)})"
                    )
                    for part_name in static_parts
                ]
            )
            return f"={base}-{minus_parts}"

        def _section_total_sum_formula(value_ref: str, section_value: str) -> str:
            return (
                f"=SUMIFS('{formula_source_sheet}'!{value_ref},"
                f"'{formula_source_sheet}'!{formula_refs['section']},{_excel_literal(section_value)},"
                f"'{formula_source_sheet}'!{formula_refs['part_name']},\"<>\")"
            )

        def _section_total_count_formula(section_value: str) -> str:
            return (
                f"=COUNTIFS('{formula_source_sheet}'!{formula_refs['section']},{_excel_literal(section_value)},"
                f"'{formula_source_sheet}'!{formula_refs['part_name']},\"<>\")"
            )

        def _grand_total_sum_formula(value_ref: str) -> str:
            return (
                f"=SUMIFS('{formula_source_sheet}'!{value_ref},"
                f"'{formula_source_sheet}'!{formula_refs['part_name']},\"<>\")"
            )

        def _grand_total_count_formula() -> str:
            return f"=COUNTIFS('{formula_source_sheet}'!{formula_refs['part_name']},\"<>\")"

        for section_value in section_order:
            section_rows = grouped[grouped[section_column].eq(section_value)].copy()
            for part_name in part_order:
                match = section_rows[section_rows["part_name"].eq(part_name)]
                if match.empty:
                    continue

                if part_name == "OTHER":
                    rows.append(
                        {
                            "section": section_value,
                            "part_name": part_name,
                            "Sum of labor_cost": _other_sum_formula(formula_refs["Sum of labor_cost"], str(section_value)),
                            "Sum of transportation_cost": _other_sum_formula(formula_refs["Sum of transportation_cost"], str(section_value)),
                            "Sum of parts_cost": _other_sum_formula(formula_refs["Sum of parts_cost"], str(section_value)),
                            "Sum of total_cost": _other_sum_formula(formula_refs["Sum of total_cost"], str(section_value)),
                            "Count of part_name": _other_count_formula(str(section_value)),
                        }
                    )
                else:
                    rows.append(
                        {
                            "section": section_value,
                            "part_name": part_name,
                            "Sum of labor_cost": _sumifs_formula(formula_refs["Sum of labor_cost"], str(section_value), part_name),
                            "Sum of transportation_cost": _sumifs_formula(
                                formula_refs["Sum of transportation_cost"], str(section_value), part_name
                            ),
                            "Sum of parts_cost": _sumifs_formula(formula_refs["Sum of parts_cost"], str(section_value), part_name),
                            "Sum of total_cost": _sumifs_formula(formula_refs["Sum of total_cost"], str(section_value), part_name),
                            "Count of part_name": _countifs_formula(str(section_value), part_name),
                        }
                    )

            rows.append(
                {
                    "section": f"{section_value} Total",
                    "part_name": "",
                    "Sum of labor_cost": _section_total_sum_formula(formula_refs["Sum of labor_cost"], str(section_value)),
                    "Sum of transportation_cost": _section_total_sum_formula(
                        formula_refs["Sum of transportation_cost"], str(section_value)
                    ),
                    "Sum of parts_cost": _section_total_sum_formula(formula_refs["Sum of parts_cost"], str(section_value)),
                    "Sum of total_cost": _section_total_sum_formula(formula_refs["Sum of total_cost"], str(section_value)),
                    "Count of part_name": _section_total_count_formula(str(section_value)),
                }
            )

        summary_df = pd.DataFrame(rows, columns=output_columns)
        if summary_df.empty:
            summary_df = pd.DataFrame(columns=output_columns)

        if not summary_df.empty:
            summary_df = pd.concat(
                [
                    summary_df,
                    pd.DataFrame(
                        [
                            {
                                "section": "Grand Total",
                                "part_name": "",
                                "Sum of labor_cost": _grand_total_sum_formula(formula_refs["Sum of labor_cost"]),
                                "Sum of transportation_cost": _grand_total_sum_formula(
                                    formula_refs["Sum of transportation_cost"]
                                ),
                                "Sum of parts_cost": _grand_total_sum_formula(formula_refs["Sum of parts_cost"]),
                                "Sum of total_cost": _grand_total_sum_formula(formula_refs["Sum of total_cost"]),
                                "Count of part_name": _grand_total_count_formula(),
                            }
                        ]
                    ),
                ],
                ignore_index=True,
            )

        return _add_summary_metadata(summary_df, cfg)

    for section_value in section_order:
        section_rows = grouped[grouped[section_column].eq(section_value)].copy()
        section_total = {
            "Sum of labor_cost": 0.0,
            "Sum of transportation_cost": 0.0,
            "Sum of parts_cost": 0.0,
            "Sum of total_cost": 0.0,
            "Count of part_name": 0.0,
        }

        for part_name in part_order:
            match = section_rows[section_rows["part_name"].eq(part_name)]
            if match.empty:
                continue
            row = match.iloc[0]
            data_row = {
                "section": section_value,
                "part_name": part_name,
                "Sum of labor_cost": float(row["Sum of labor_cost"]),
                "Sum of transportation_cost": float(row["Sum of transportation_cost"]),
                "Sum of parts_cost": float(row["Sum of parts_cost"]),
                "Sum of total_cost": float(row["Sum of total_cost"]),
                "Count of part_name": float(row["Count of part_name"]),
            }
            rows.append(data_row)
            for key in section_total:
                section_total[key] += float(data_row[key])

        rows.append(
            {
                "section": f"{section_value} Total",
                "part_name": "",
                **section_total,
            }
        )

    summary_df = pd.DataFrame(rows, columns=output_columns)
    if summary_df.empty:
        summary_df = pd.DataFrame(columns=output_columns)

    if not summary_df.empty:
        total_row = {
            "section": "Grand Total",
            "part_name": "",
            "Sum of labor_cost": float(summary_df["Sum of labor_cost"].sum()),
            "Sum of transportation_cost": float(summary_df["Sum of transportation_cost"].sum()),
            "Sum of parts_cost": float(summary_df["Sum of parts_cost"].sum()),
            "Sum of total_cost": float(summary_df["Sum of total_cost"].sum()),
            "Count of part_name": float(summary_df["Count of part_name"].sum()),
        }
        subtotal_mask = summary_df["section"].astype(str).str.endswith(" Total")
        for col in [
            "Sum of labor_cost",
            "Sum of transportation_cost",
            "Sum of parts_cost",
            "Sum of total_cost",
            "Count of part_name",
        ]:
            total_row[col] = float(summary_df.loc[~subtotal_mask, col].sum())
        summary_df = pd.concat([summary_df, pd.DataFrame([total_row])], ignore_index=True)

    return _add_summary_metadata(summary_df, cfg)


def _build_part_pivot_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    section_column = str(cfg.get("section_column", "section"))
    part_column = str(cfg.get("part_column", "part_name"))

    cost_columns = {
        "Sum of labor_cost": str(cfg.get("labor_cost_column", "labor_cost")),
        "Sum of transportation_cost": str(cfg.get("transportation_cost_column", "transportation_cost")),
        "Sum of parts_cost": str(cfg.get("parts_cost_column", "parts_cost")),
        "Sum of total_cost": str(cfg.get("total_cost_column", "total_cost")),
    }

    required_columns = [section_column, part_column, *cost_columns.values()]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError(
            "Part pivot summary gagal, kolom tidak ditemukan: " + ", ".join(missing)
        )

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.ne("")].copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df[part_column] = part_series

    for target_col, source_col in cost_columns.items():
        working_df[target_col] = pd.to_numeric(working_df[source_col], errors="coerce").fillna(0)

    grouped = (
        working_df.groupby([section_column, part_column], dropna=False, sort=False)
        .agg(
            **{
                "Sum of labor_cost": ("Sum of labor_cost", "sum"),
                "Sum of transportation_cost": ("Sum of transportation_cost", "sum"),
                "Sum of parts_cost": ("Sum of parts_cost", "sum"),
                "Sum of total_cost": ("Sum of total_cost", "sum"),
                "Count of part_name": (part_column, "count"),
            }
        )
        .reset_index()
    )
    grouped = grouped.rename(columns={section_column: "section", part_column: "part_name"})

    output_columns = [
        "section",
        "part_name",
        "Sum of labor_cost",
        "Sum of transportation_cost",
        "Sum of parts_cost",
        "Sum of total_cost",
        "Count of part_name",
    ]

    section_order = working_df[section_column].drop_duplicates().tolist()
    rows: list[dict[str, object]] = []

    for section_value in section_order:
        section_rows = grouped[grouped["section"].eq(section_value)].copy()
        if section_rows.empty:
            continue

        section_rows = section_rows.sort_values(
            by=["Sum of total_cost", "part_name"],
            ascending=[False, True],
            kind="stable",
        )

        section_total = {
            "Sum of labor_cost": 0.0,
            "Sum of transportation_cost": 0.0,
            "Sum of parts_cost": 0.0,
            "Sum of total_cost": 0.0,
            "Count of part_name": 0.0,
        }

        for _, row in section_rows.iterrows():
            data_row = {
                "section": section_value,
                "part_name": str(row["part_name"]),
                "Sum of labor_cost": float(row["Sum of labor_cost"]),
                "Sum of transportation_cost": float(row["Sum of transportation_cost"]),
                "Sum of parts_cost": float(row["Sum of parts_cost"]),
                "Sum of total_cost": float(row["Sum of total_cost"]),
                "Count of part_name": float(row["Count of part_name"]),
            }
            rows.append(data_row)
            for key in section_total:
                section_total[key] += float(data_row[key])

        rows.append(
            {
                "section": f"{section_value} Total",
                "part_name": "",
                **section_total,
            }
        )

    summary_df = pd.DataFrame(rows, columns=output_columns)
    if summary_df.empty:
        summary_df = pd.DataFrame(columns=output_columns)

    if not summary_df.empty:
        subtotal_mask = summary_df["section"].astype(str).str.endswith(" Total")
        total_row = {
            "section": "Grand Total",
            "part_name": "",
            "Sum of labor_cost": float(summary_df.loc[~subtotal_mask, "Sum of labor_cost"].sum()),
            "Sum of transportation_cost": float(summary_df.loc[~subtotal_mask, "Sum of transportation_cost"].sum()),
            "Sum of parts_cost": float(summary_df.loc[~subtotal_mask, "Sum of parts_cost"].sum()),
            "Sum of total_cost": float(summary_df.loc[~subtotal_mask, "Sum of total_cost"].sum()),
            "Count of part_name": float(summary_df.loc[~subtotal_mask, "Count of part_name"].sum()),
        }
        summary_df = pd.concat([summary_df, pd.DataFrame([total_row])], ignore_index=True)

    return _add_summary_metadata(summary_df, cfg)


def _build_panel_model_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    part_column = str(cfg.get("part_column", "part_name"))
    inch_column = str(cfg.get("inch_column", "inch"))
    model_column = str(cfg.get("model_column", "model_name"))
    total_cost_column = str(cfg.get("total_cost_column", "total_cost"))

    required_columns = [part_column, inch_column, model_column, total_cost_column]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError("Panel model summary gagal, kolom tidak ditemukan: " + ", ".join(missing))

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.eq("PANEL")].copy()
    working_df[part_column] = "PANEL"
    working_df[inch_column] = working_df[inch_column].fillna("").astype(str).str.strip()
    working_df[model_column] = working_df[model_column].fillna("").astype(str).str.strip()
    working_df["Total"] = pd.to_numeric(working_df[total_cost_column], errors="coerce").fillna(0)

    grouped = (
        working_df.groupby([part_column, inch_column, model_column], dropna=False, sort=False)
        .agg(Total=("Total", "sum"))
        .reset_index()
        .rename(columns={part_column: "part_name", inch_column: "inch", model_column: "model_name"})
    )

    output_columns = ["part_name", "inch", "model_name", "Total"]
    rows: list[dict[str, object]] = []

    def inch_sort_key(value: object) -> tuple[int, float, str]:
        text = str(value).strip()
        numeric_value = pd.to_numeric(text, errors="coerce")
        if pd.notna(numeric_value):
            return (0, float(numeric_value), text)
        return (1, 0.0, text.casefold())

    inch_order = sorted(working_df[inch_column].drop_duplicates().tolist(), key=inch_sort_key)

    for inch_value in inch_order:
        inch_rows = grouped[grouped["inch"].eq(inch_value)].copy()
        if inch_rows.empty:
            continue

        inch_rows = inch_rows.sort_values(by=["Total", "model_name"], ascending=[False, True], kind="stable")
        inch_total = 0.0
        for _, row in inch_rows.iterrows():
            value = float(row["Total"])
            rows.append(
                {
                    "part_name": "PANEL",
                    "inch": str(inch_value),
                    "model_name": str(row["model_name"]),
                    "Total": value,
                }
            )
            inch_total += value

        rows.append({"part_name": "PANEL", "inch": f"{inch_value} Total", "model_name": "", "Total": inch_total})

    summary_df = pd.DataFrame(rows, columns=output_columns)
    if summary_df.empty:
        summary_df = pd.DataFrame(columns=output_columns)

    if not summary_df.empty:
        subtotal_mask = summary_df["inch"].astype(str).str.endswith(" Total")
        panel_total = float(summary_df.loc[~subtotal_mask, "Total"].sum())
        summary_df = pd.concat(
            [
                summary_df,
                pd.DataFrame(
                    [
                        {"part_name": "PANEL Total", "inch": "", "model_name": "", "Total": panel_total},
                        {"part_name": "Grand Total", "inch": "", "model_name": "", "Total": panel_total},
                    ]
                ),
            ],
            ignore_index=True,
        )

    if not summary_df.empty:
        row_types = []
        for _, row in summary_df.iterrows():
            part_name = str(row["part_name"]).strip()
            inch_value = str(row["inch"]).strip()
            if part_name == "Grand Total":
                row_types.append("grand_total")
            elif part_name.endswith(" Total") or inch_value.endswith(" Total"):
                row_types.append("subtotal")
            else:
                row_types.append("data")
        summary_df = summary_df.copy()
        summary_df["_row_type"] = row_types

    default_labels = {"part_name": "Part Name", "inch": "Inch", "model_name": "Model Name"}
    column_labels = cfg.get("column_labels")
    if isinstance(column_labels, dict):
        default_labels.update(column_labels)
    return summary_df.rename(columns={k: v for k, v in default_labels.items() if k in summary_df.columns})


def _build_panel_symptom_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    part_column = str(cfg.get("part_column", "part_name"))
    symptom_column = str(cfg.get("symptom_column", "symptom"))

    required_columns = [part_column, symptom_column]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError("Panel symptom summary gagal, kolom tidak ditemukan: " + ", ".join(missing))

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.eq("PANEL")].copy()
    working_df["symptom"] = working_df[symptom_column].fillna("").astype(str).str.strip()

    grouped = (
        working_df.groupby("symptom", dropna=False, sort=False)
        .size()
        .reset_index(name="Total")
        .sort_values(by=["Total", "symptom"], ascending=[False, True], kind="stable")
    )

    summary_df = grouped.rename(columns={"symptom": "symptom"})
    summary_df.insert(0, "part_name", "PANEL")
    summary_df = summary_df[["part_name", "symptom", "Total"]]

    panel_total = float(summary_df["Total"].sum()) if not summary_df.empty else 0.0
    summary_df = pd.concat(
        [
            summary_df,
            pd.DataFrame(
                [
                    {"part_name": "PANEL Total", "symptom": "", "Total": panel_total},
                    {"part_name": "Grand Total", "symptom": "", "Total": panel_total},
                ]
            ),
        ],
        ignore_index=True,
    )
    return _apply_summary_column_labels(summary_df, cfg)


def _build_panel_area_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    part_column = str(cfg.get("part_column", "part_name"))
    area_column = str(cfg.get("area_column", "branch"))

    required_columns = [part_column, area_column]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError("Panel area summary gagal, kolom tidak ditemukan: " + ", ".join(missing))

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.eq("PANEL")].copy()
    working_df["branch"] = working_df[area_column].fillna("").astype(str).str.strip()

    grouped = (
        working_df.groupby("branch", dropna=False, sort=False)
        .size()
        .reset_index(name="Total")
        .sort_values(by=["Total", "branch"], ascending=[False, True], kind="stable")
    )

    summary_df = grouped.rename(columns={"branch": "branch"})
    summary_df.insert(0, "part_name", "PANEL")
    summary_df = summary_df[["part_name", "branch", "Total"]]

    panel_total = float(summary_df["Total"].sum()) if not summary_df.empty else 0.0
    summary_df = pd.concat(
        [
            summary_df,
            pd.DataFrame(
                [
                    {"part_name": "PANEL Total", "branch": "", "Total": panel_total},
                    {"part_name": "Grand Total", "branch": "", "Total": panel_total},
                ]
            ),
        ],
        ignore_index=True,
    )
    return _apply_summary_column_labels(summary_df, cfg)


def _build_panel_usage_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    part_column = str(cfg.get("part_column", "part_name"))
    usage_column = str(cfg.get("usage_column", "panel_usage"))
    usage_order = ["< 1 Year", "1 - 2 Years", "2 - 3 Years", "> 3 Years"]
    usage_key_to_label = {item.casefold(): item for item in usage_order}

    required_columns = [part_column, usage_column]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError("Panel usage summary gagal, kolom tidak ditemukan: " + ", ".join(missing))

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.eq("PANEL")].copy()

    usage_series = working_df[usage_column].fillna("").astype(str).str.strip()
    usage_keys = usage_series.map(lambda value: value.casefold())
    valid_mask = usage_keys.isin(usage_key_to_label.keys())
    filtered_df = working_df.loc[valid_mask].copy()
    filtered_df["panel_usage"] = usage_keys.loc[valid_mask].map(usage_key_to_label)

    counts = filtered_df.groupby("panel_usage", dropna=False).size().to_dict()
    rows = [
        {"part_name": "PANEL", "panel_usage": label, "Total": float(counts.get(label, 0))}
        for label in usage_order
    ]

    summary_df = pd.DataFrame(rows, columns=["part_name", "panel_usage", "Total"])
    panel_total = float(summary_df["Total"].sum()) if not summary_df.empty else 0.0
    summary_df = pd.concat(
        [
            summary_df,
            pd.DataFrame(
                [
                    {"part_name": "PANEL Total", "panel_usage": "", "Total": panel_total},
                    {"part_name": "Grand Total", "panel_usage": "", "Total": panel_total},
                ]
            ),
        ],
        ignore_index=True,
    )
    return _apply_summary_column_labels(summary_df, cfg)


def _build_panel_fcost_inch_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    part_column = str(cfg.get("part_column", "part_name"))
    inch_column = str(cfg.get("inch_column", "inch"))

    cost_columns = {
        "Sum of labor_cost": str(cfg.get("labor_cost_column", "labor_cost")),
        "Sum of transportation_cost": str(cfg.get("transportation_cost_column", "transportation_cost")),
        "Sum of parts_cost": str(cfg.get("parts_cost_column", "parts_cost")),
        "Sum of total_cost": str(cfg.get("total_cost_column", "total_cost")),
    }

    required_columns = [part_column, inch_column, *cost_columns.values()]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError("Panel fcost inch summary gagal, kolom tidak ditemukan: " + ", ".join(missing))

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.eq("PANEL")].copy()
    working_df["inch"] = working_df[inch_column].fillna("").astype(str).str.strip()

    for target_col, source_col in cost_columns.items():
        working_df[target_col] = pd.to_numeric(working_df[source_col], errors="coerce").fillna(0)

    grouped = (
        working_df.groupby("inch", dropna=False, sort=False)
        .agg(
            **{
                "Sum of labor_cost": ("Sum of labor_cost", "sum"),
                "Sum of transportation_cost": ("Sum of transportation_cost", "sum"),
                "Sum of parts_cost": ("Sum of parts_cost", "sum"),
                "Sum of total_cost": ("Sum of total_cost", "sum"),
                "Count of part_name": ("inch", "count"),
            }
        )
        .reset_index()
    )

    grouped = grouped.sort_values(by=["Sum of total_cost", "inch"], ascending=[False, True], kind="stable")
    top_inch_values = grouped["inch"].tolist()[:5]

    rows: list[dict[str, object]] = []
    for inch_value in top_inch_values:
        row = grouped[grouped["inch"].eq(inch_value)].iloc[0]
        rows.append(
            {
                "part_name": "PANEL",
                "inch": str(inch_value),
                "Sum of labor_cost": float(row["Sum of labor_cost"]),
                "Sum of transportation_cost": float(row["Sum of transportation_cost"]),
                "Sum of parts_cost": float(row["Sum of parts_cost"]),
                "Sum of total_cost": float(row["Sum of total_cost"]),
                "Count of part_name": float(row["Count of part_name"]),
            }
        )

    other_df = grouped[~grouped["inch"].isin(top_inch_values)].copy()
    if not other_df.empty:
        rows.append(
            {
                "part_name": "PANEL",
                "inch": "other",
                "Sum of labor_cost": float(other_df["Sum of labor_cost"].sum()),
                "Sum of transportation_cost": float(other_df["Sum of transportation_cost"].sum()),
                "Sum of parts_cost": float(other_df["Sum of parts_cost"].sum()),
                "Sum of total_cost": float(other_df["Sum of total_cost"].sum()),
                "Count of part_name": float(other_df["Count of part_name"].sum()),
            }
        )

    summary_df = pd.DataFrame(
        rows,
        columns=[
            "part_name",
            "inch",
            "Sum of labor_cost",
            "Sum of transportation_cost",
            "Sum of parts_cost",
            "Sum of total_cost",
            "Count of part_name",
        ],
    )

    if summary_df.empty:
        summary_df = pd.DataFrame(
            columns=[
                "part_name",
                "inch",
                "Sum of labor_cost",
                "Sum of transportation_cost",
                "Sum of parts_cost",
                "Sum of total_cost",
                "Count of part_name",
            ]
        )

    panel_total = {
        "part_name": "PANEL Total",
        "inch": "",
        "Sum of labor_cost": float(summary_df["Sum of labor_cost"].sum()) if not summary_df.empty else 0.0,
        "Sum of transportation_cost": float(summary_df["Sum of transportation_cost"].sum()) if not summary_df.empty else 0.0,
        "Sum of parts_cost": float(summary_df["Sum of parts_cost"].sum()) if not summary_df.empty else 0.0,
        "Sum of total_cost": float(summary_df["Sum of total_cost"].sum()) if not summary_df.empty else 0.0,
        "Count of part_name": float(summary_df["Count of part_name"].sum()) if not summary_df.empty else 0.0,
    }

    grand_total = {**panel_total, "part_name": "Grand Total"}
    summary_df = pd.concat([summary_df, pd.DataFrame([panel_total, grand_total])], ignore_index=True)
    return _apply_summary_column_labels(summary_df, cfg)


def _build_panel_top1_inch_model_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    part_column = str(cfg.get("part_column", "part_name"))
    inch_column = str(cfg.get("inch_column", "inch"))
    model_column = str(cfg.get("model_column", "model_name"))

    cost_columns = {
        "Sum of labor_cost": str(cfg.get("labor_cost_column", "labor_cost")),
        "Sum of transportation_cost": str(cfg.get("transportation_cost_column", "transportation_cost")),
        "Sum of parts_cost": str(cfg.get("parts_cost_column", "parts_cost")),
        "Sum of total_cost": str(cfg.get("total_cost_column", "total_cost")),
    }

    required_columns = [part_column, inch_column, model_column, *cost_columns.values()]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError("Panel top1 inch model summary gagal, kolom tidak ditemukan: " + ", ".join(missing))

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.eq("PANEL")].copy()
    working_df["inch"] = working_df[inch_column].fillna("").astype(str).str.strip()
    working_df["model_name"] = working_df[model_column].fillna("").astype(str).str.strip()

    for target_col, source_col in cost_columns.items():
        working_df[target_col] = pd.to_numeric(working_df[source_col], errors="coerce").fillna(0)

    inch_grouped = (
        working_df.groupby("inch", dropna=False, sort=False)
        .agg(**{"Sum of total_cost": ("Sum of total_cost", "sum")})
        .reset_index()
        .sort_values(by=["Sum of total_cost", "inch"], ascending=[False, True], kind="stable")
    )

    top1_inch = str(inch_grouped.iloc[0]["inch"]) if not inch_grouped.empty else ""
    filtered_df = working_df[working_df["inch"].eq(top1_inch)].copy()

    model_grouped = (
        filtered_df.groupby("model_name", dropna=False, sort=False)
        .agg(
            **{
                "Sum of labor_cost": ("Sum of labor_cost", "sum"),
                "Sum of transportation_cost": ("Sum of transportation_cost", "sum"),
                "Sum of parts_cost": ("Sum of parts_cost", "sum"),
                "Sum of total_cost": ("Sum of total_cost", "sum"),
                "Count of part_name": ("model_name", "count"),
            }
        )
        .reset_index()
        .sort_values(by=["Sum of total_cost", "model_name"], ascending=[False, True], kind="stable")
    )

    top_models = model_grouped["model_name"].tolist()[:5]
    rows: list[dict[str, object]] = []
    for model_name in top_models:
        row = model_grouped[model_grouped["model_name"].eq(model_name)].iloc[0]
        rows.append(
            {
                "part_name": "PANEL",
                "inch": top1_inch,
                "model_name": str(model_name),
                "Sum of labor_cost": float(row["Sum of labor_cost"]),
                "Sum of transportation_cost": float(row["Sum of transportation_cost"]),
                "Sum of parts_cost": float(row["Sum of parts_cost"]),
                "Sum of total_cost": float(row["Sum of total_cost"]),
                "Count of part_name": float(row["Count of part_name"]),
            }
        )

    other_df = model_grouped[~model_grouped["model_name"].isin(top_models)].copy()
    if not other_df.empty:
        rows.append(
            {
                "part_name": "PANEL",
                "inch": top1_inch,
                "model_name": "other",
                "Sum of labor_cost": float(other_df["Sum of labor_cost"].sum()),
                "Sum of transportation_cost": float(other_df["Sum of transportation_cost"].sum()),
                "Sum of parts_cost": float(other_df["Sum of parts_cost"].sum()),
                "Sum of total_cost": float(other_df["Sum of total_cost"].sum()),
                "Count of part_name": float(other_df["Count of part_name"].sum()),
            }
        )

    summary_df = pd.DataFrame(
        rows,
        columns=[
            "part_name",
            "inch",
            "model_name",
            "Sum of labor_cost",
            "Sum of transportation_cost",
            "Sum of parts_cost",
            "Sum of total_cost",
            "Count of part_name",
        ],
    )

    if summary_df.empty:
        summary_df = pd.DataFrame(
            columns=[
                "part_name",
                "inch",
                "model_name",
                "Sum of labor_cost",
                "Sum of transportation_cost",
                "Sum of parts_cost",
                "Sum of total_cost",
                "Count of part_name",
            ]
        )

    panel_total = {
        "part_name": "PANEL Total",
        "inch": "",
        "model_name": "",
        "Sum of labor_cost": float(summary_df["Sum of labor_cost"].sum()) if not summary_df.empty else 0.0,
        "Sum of transportation_cost": float(summary_df["Sum of transportation_cost"].sum()) if not summary_df.empty else 0.0,
        "Sum of parts_cost": float(summary_df["Sum of parts_cost"].sum()) if not summary_df.empty else 0.0,
        "Sum of total_cost": float(summary_df["Sum of total_cost"].sum()) if not summary_df.empty else 0.0,
        "Count of part_name": float(summary_df["Count of part_name"].sum()) if not summary_df.empty else 0.0,
    }
    grand_total = {**panel_total, "part_name": "Grand Total"}
    summary_df = pd.concat([summary_df, pd.DataFrame([panel_total, grand_total])], ignore_index=True)
    return _apply_summary_column_labels(summary_df, cfg)


def _build_part_model_symptom_top_summary(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    part_column = str(cfg.get("part_column", "part_name"))
    model_column = str(cfg.get("model_column", "model_name"))
    symptom_column = str(cfg.get("symptom_column", "symptom"))
    top_n = int(cfg.get("top_n", 3))
    part_order_cfg = cfg.get("part_order")
    if isinstance(part_order_cfg, list):
        part_order = [str(value).strip() for value in part_order_cfg if str(value).strip()]
    else:
        part_order = []

    required_columns = [part_column, model_column, symptom_column]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError("Part model symptom summary gagal, kolom tidak ditemukan: " + ", ".join(missing))

    working_df = data_df.copy()
    working_df["part_name"] = working_df[part_column].fillna("").astype(str).str.strip()
    working_df["model_name"] = working_df[model_column].fillna("").astype(str).str.strip()
    working_df["symptom"] = working_df[symptom_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[working_df["part_name"].ne("")].copy()

    if part_order:
        working_df = working_df.loc[working_df["part_name"].isin(part_order)].copy()
    else:
        part_order = working_df["part_name"].drop_duplicates().tolist()

    grouped = (
        working_df.groupby(["part_name", "model_name", "symptom"], dropna=False, sort=False)
        .size()
        .reset_index(name="Total")
    )

    rows: list[dict[str, object]] = []
    for part_name in part_order:
        part_rows = grouped[grouped["part_name"].eq(part_name)].copy()
        if part_rows.empty:
            continue

        part_rows = part_rows.sort_values(
            by=["Total", "model_name", "symptom"],
            ascending=[False, True, True],
            kind="stable",
        )
        if top_n > 0 and len(part_rows) > top_n:
            cutoff = part_rows.iloc[top_n - 1]["Total"]
            part_rows = part_rows.loc[part_rows["Total"] >= cutoff]

        part_total = 0.0
        for _, row in part_rows.iterrows():
            total = float(row["Total"])
            rows.append(
                {
                    "part_name": part_name,
                    "model_name": str(row["model_name"]),
                    "symptom": str(row["symptom"]),
                    "Total": total,
                    "_row_type": "data",
                }
            )
            part_total += total

        rows.append(
            {
                "part_name": f"{part_name} Total",
                "model_name": "",
                "symptom": "",
                "Total": part_total,
                "_row_type": "subtotal",
            }
        )

    grand_total = float(
        sum(float(row["Total"]) for row in rows if row.get("_row_type") == "data")
    )
    rows.append(
        {
            "part_name": "Grand Total",
            "model_name": "",
            "symptom": "",
            "Total": grand_total,
            "_row_type": "grand_total",
        }
    )

    summary_df = pd.DataFrame(
        rows,
        columns=["part_name", "model_name", "symptom", "Total", "_row_type"],
    )
    return _apply_summary_column_labels(summary_df, cfg)


def _build_panel_symptom_inch_matrix(data_df: pd.DataFrame, options: dict | None) -> pd.DataFrame:
    cfg = options or {}
    part_column = str(cfg.get("part_column", "part_name"))
    symptom_column = str(cfg.get("symptom_column", "symptom"))
    inch_column = str(cfg.get("inch_column", "inch"))

    required_columns = [part_column, symptom_column, inch_column]
    missing = [column for column in required_columns if column not in data_df.columns]
    if missing:
        raise ValueError("Panel symptom inch matrix gagal, kolom tidak ditemukan: " + ", ".join(missing))

    working_df = data_df.copy()
    part_series = working_df[part_column].fillna("").astype(str).str.strip()
    working_df = working_df.loc[part_series.eq("PANEL")].copy()
    working_df["symptom"] = working_df[symptom_column].fillna("").astype(str).str.strip()
    working_df["inch"] = working_df[inch_column].fillna("").astype(str).str.strip()

    inch_keys = working_df["inch"].drop_duplicates().tolist()
    inch_keys_sorted = sorted(
        inch_keys,
        key=lambda item: (
            1 if pd.isna(pd.to_numeric(item, errors="coerce")) else 0,
            float(pd.to_numeric(item, errors="coerce")) if pd.notna(pd.to_numeric(item, errors="coerce")) else str(item),
        ),
    )

    pivot = (
        working_df.pivot_table(index="symptom", columns="inch", values="part_name", aggfunc="count", fill_value=0)
        .reindex(columns=inch_keys_sorted, fill_value=0)
        .reset_index()
    )

    if "symptom" not in pivot.columns:
        pivot = pd.DataFrame(columns=["symptom", *inch_keys_sorted])

    if not pivot.empty:
        pivot["Grand Total"] = pivot[inch_keys_sorted].sum(axis=1)
        pivot = pivot.sort_values(by=["Grand Total", "symptom"], ascending=[False, True], kind="stable")
    else:
        pivot["Grand Total"] = []

    pivot.insert(0, "part_name", "PANEL")

    total_values = {inch: float(pivot[inch].sum()) if inch in pivot.columns else 0.0 for inch in inch_keys_sorted}
    grand_total_value = float(sum(total_values.values()))

    panel_total_row: dict[str, object] = {"part_name": "PANEL Total", "symptom": ""}
    grand_total_row: dict[str, object] = {"part_name": "Grand Total", "symptom": ""}
    for inch in inch_keys_sorted:
        panel_total_row[inch] = total_values[inch]
        grand_total_row[inch] = total_values[inch]
    panel_total_row["Grand Total"] = grand_total_value
    grand_total_row["Grand Total"] = grand_total_value

    summary_df = pd.concat([pivot, pd.DataFrame([panel_total_row, grand_total_row])], ignore_index=True)
    ordered_columns = ["part_name", "symptom", *inch_keys_sorted, "Grand Total"]
    for col in ordered_columns:
        if col not in summary_df.columns:
            summary_df[col] = 0.0 if col not in {"part_name", "symptom"} else ""
    summary_df = summary_df.loc[:, ordered_columns]
    return _apply_summary_column_labels(summary_df, cfg)


def _build_summary_output_sheet(data_df: pd.DataFrame, item: dict) -> tuple[pd.DataFrame, str]:
    summary_cfg = item["summary"]
    summary_type = str(summary_cfg["type"]).strip()
    layout_mode = str(summary_cfg.get("layout_mode", "standard"))
    options = summary_cfg.get("options")

    if summary_type == "static_part_summary":
        return _build_static_part_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "static_part_pivot_summary":
        forced_options = dict(options) if isinstance(options, dict) else {}
        forced_options["value_mode"] = "excel_formula"
        return _build_static_part_summary(data_df, forced_options), layout_mode

    if summary_type == "part_pivot_summary":
        return _build_part_pivot_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "panel_model_summary":
        return _build_panel_model_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "panel_symptom_summary":
        return _build_panel_symptom_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "panel_area_summary":
        return _build_panel_area_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "panel_usage_summary":
        return _build_panel_usage_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "panel_fcost_inch_summary":
        return _build_panel_fcost_inch_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "panel_top1_inch_model_summary":
        return _build_panel_top1_inch_model_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "part_model_symptom_top_summary":
        return _build_part_model_symptom_top_summary(data_df, options if isinstance(options, dict) else None), layout_mode

    if summary_type == "panel_symptom_inch_matrix":
        return _build_panel_symptom_inch_matrix(data_df, options if isinstance(options, dict) else None), layout_mode

    summary_row: dict[str, object] = {
        "summary_type": summary_type,
        "source_rows": len(data_df),
    }
    if isinstance(options, dict) and options:
        summary_row["options"] = str(options)

    return pd.DataFrame([summary_row]), layout_mode


def _build_output_sheets(
    data_df: pd.DataFrame,
    outputs_cfg: list[dict],
    log: LogFn,
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    output_sheets: dict[str, pd.DataFrame] = {}
    sheet_layouts: dict[str, str] = {}
    for item in outputs_cfg:
        sheet_name = str(item["sheet_name"])

        if "summary" in item:
            summary_df, layout_mode = _build_summary_output_sheet(data_df, item)
            output_sheets[sheet_name] = summary_df
            sheet_layouts[sheet_name] = layout_mode
            log(f"Output recipe summary '{sheet_name}' siap ({len(summary_df)} baris).")
            continue

        columns = [str(column) for column in item.get("columns", [])]
        missing = [column for column in columns if column not in data_df.columns]
        if missing:
            raise ValueError(f"Output '{sheet_name}' gagal, kolom tidak ditemukan: {', '.join(missing)}")
        output_sheets[sheet_name] = data_df.loc[:, columns].copy()
        sheet_layouts[sheet_name] = "standard"
        log(f"Output recipe '{sheet_name}' siap ({len(output_sheets[sheet_name])} baris).")
    return output_sheets, sheet_layouts


def execute_step_recipe(
    *,
    source_path: Path,
    recipe_cfg: dict,
    project_root: Path,
    masters_dir: Path,
    log: LogFn,
    runtime_values: dict[str, object] | None = None,
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
            datasets[working_dataset] = _apply_derive_column_step(
                current_df,
                step_cfg,
                log,
                runtime_values,
            )
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

    output_sheets, sheet_layouts = _build_output_sheets(final_df, recipe_cfg["outputs"], log)
    return RecipeExecutionResult(
        final_df=final_df,
        output_sheets=output_sheets,
        source_df_for_header=final_df,
        sheet_layouts=sheet_layouts,
    )
