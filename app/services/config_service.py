from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from app.utils.path_safety import normalize_relative_path_string
from app.services.transform_service import (
    SUPPORTED_FORMULA_OPERATIONS,
    SUPPORTED_GROUPBY_AGGFUNCS,
    SUPPORTED_RULE_OPERATORS,
)


REQUIRED_ROOT_FIELDS = ("name", "source_sheet", "header", "outputs")
SUPPORTED_MASTER_STRATEGIES = {"lookup", "lookup_rules", "ordered_rules"}
SUPPORTED_MATCHER_MODES = {"equals", "contains"}
SUPPORTED_KEY_NORMALIZERS = {"compact_text"}
SUPPORTED_RECIPE_MATCHING_ORDERS = {"top_to_bottom"}
SUPPORTED_TRANSFORM_TYPES = {
    "conditional",
    "ensure_optional_columns",
    "filter_rows",
    "formula",
}


def _is_supported_literal(value: object) -> bool:
    return value is None or isinstance(value, str | int | float | bool)


def _validate_master_file_path(
    raw_path: object,
    *,
    path: str,
    errors: list[str],
) -> None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        errors.append(f"{path} harus berupa string path relatif.")
        return

    try:
        normalized = normalize_relative_path_string(raw_path)
    except ValueError as exc:
        errors.append(f"{path} tidak valid: {exc}")
        return

    parts = normalized.split("/")
    if parts[0].casefold() != "masters":
        errors.append(f"{path} wajib berada di bawah folder masters/.")

    if Path(parts[-1]).suffix.lower() not in {".csv", ".xlsx"}:
        errors.append(f"{path} hanya mendukung file .csv atau .xlsx.")


def _normalize_master_file_references(payload: dict) -> None:
    if is_step_recipe_payload(payload):
        for step in payload.get("steps", []):
            if not isinstance(step, dict):
                continue
            master_cfg = step.get("master")
            if isinstance(master_cfg, dict) and isinstance(master_cfg.get("file"), str):
                master_cfg["file"] = normalize_relative_path_string(master_cfg["file"])
        return

    for master_cfg in payload.get("masters", []) or []:
        if isinstance(master_cfg, dict) and isinstance(master_cfg.get("file"), str):
            master_cfg["file"] = normalize_relative_path_string(master_cfg["file"])


SUPPORTED_RECIPE_STEP_TYPES = {
    "derive_column",
    "duplicate_group_rewrite",
    "extract_sheet",
    "lookup_exact",
    "lookup_exact_replace",
    "lookup_rules",
    "map_ranges",
    "update_columns",
}


@dataclass(frozen=True)
class ConfigSummary:
    name: str
    path: Path
    is_valid: bool
    errors: tuple[str, ...]


def list_config_files(configs_dir: Path) -> list[Path]:
    if not configs_dir.exists():
        return []

    files = list(configs_dir.glob("*.yaml"))
    files.extend(configs_dir.glob("*.yml"))
    return sorted(set(files), key=lambda item: item.name.casefold())


def _validate_condition_rule(
    rule: object,
    *,
    path: str,
    errors: list[str],
) -> None:
    if not isinstance(rule, dict):
        errors.append(f"{path} harus berupa object.")
        return

    if "column" not in rule or not isinstance(rule.get("column"), str):
        errors.append(f"{path}.column wajib berupa string.")

    operators = [name for name in SUPPORTED_RULE_OPERATORS if name in rule]
    if len(operators) != 1:
        errors.append(
            f"{path} harus memiliki tepat satu operator kondisi yang didukung."
        )
        return

    operator = operators[0]
    if operator in {"in", "not_in"} and not isinstance(rule.get(operator), list):
        errors.append(f"{path}.{operator} harus berupa list.")
    if operator in {"in", "not_in"} and isinstance(rule.get(operator), list):
        invalid_items = [item for item in rule.get(operator, []) if not _is_supported_literal(item)]
        if invalid_items:
            errors.append(
                f"{path}.{operator} hanya boleh berisi nilai literal sederhana."
            )
    if operator not in {"in", "not_in", "is_blank", "is_not_blank"} and not _is_supported_literal(
        rule.get(operator)
    ):
        errors.append(
            f"{path}.{operator} hanya boleh memakai nilai literal sederhana."
        )
    if operator in {"is_blank", "is_not_blank"} and not isinstance(rule.get(operator), bool):
        errors.append(f"{path}.{operator} harus berupa boolean.")
    if "case_sensitive" in rule and not isinstance(rule.get("case_sensitive"), bool):
        errors.append(f"{path}.case_sensitive harus berupa boolean.")


def _validate_output_items(outputs: object, errors: list[str]) -> None:
    if not isinstance(outputs, list) or len(outputs) == 0:
        errors.append("Field 'outputs' wajib berupa list dan minimal 1 item.")
        return

    for idx, item in enumerate(outputs):
        if not isinstance(item, dict):
            errors.append(
                f"outputs[{idx}] harus berupa object dengan sheet_name dan rule output."
            )
            continue
        if "sheet_name" not in item:
            errors.append(f"outputs[{idx}] wajib memiliki field 'sheet_name'.")
        elif not isinstance(item.get("sheet_name"), str):
            errors.append(f"outputs[{idx}].sheet_name harus berupa string.")

        has_columns = "columns" in item
        has_pivot = "pivot" in item
        has_group_by = "group_by" in item
        if not has_columns and not has_pivot and not has_group_by:
            errors.append(
                f"outputs[{idx}] wajib memiliki minimal salah satu: 'columns', 'pivot', atau 'group_by'."
            )

        if has_pivot and has_columns:
            errors.append(
                f"outputs[{idx}] tidak boleh memakai 'columns' bersamaan dengan 'pivot'."
            )
        if has_pivot and has_group_by:
            errors.append(
                f"outputs[{idx}] tidak boleh memakai 'pivot' bersamaan dengan 'group_by'."
            )
        if has_columns and not isinstance(item.get("columns"), list):
            errors.append(f"outputs[{idx}].columns harus berupa list.")
        if has_pivot and not isinstance(item.get("pivot"), dict):
            errors.append(f"outputs[{idx}].pivot harus berupa object.")
        if has_group_by and not isinstance(item.get("group_by"), dict):
            errors.append(f"outputs[{idx}].group_by harus berupa object.")

        if has_group_by and isinstance(item.get("group_by"), dict):
            group_by = item["group_by"]
            by = group_by.get("by")
            if not isinstance(by, str | list):
                errors.append(f"outputs[{idx}].group_by.by harus berupa string atau list string.")
            elif isinstance(by, list) and not all(isinstance(value, str) for value in by):
                errors.append(f"outputs[{idx}].group_by.by harus berupa string atau list string.")

            aggregations = group_by.get("aggregations")
            if not isinstance(aggregations, dict) or len(aggregations) == 0:
                errors.append(
                    f"outputs[{idx}].group_by.aggregations harus berupa object dan minimal 1 item."
                )
            elif not all(
                isinstance(column, str)
                and isinstance(func, str)
                and func in SUPPORTED_GROUPBY_AGGFUNCS
                for column, func in aggregations.items()
            ):
                errors.append(
                    f"outputs[{idx}].group_by.aggregations hanya mendukung fungsi: {', '.join(sorted(SUPPORTED_GROUPBY_AGGFUNCS))}."
                )


def _validate_matching_config(
    matching: object,
    *,
    path: str,
    errors: list[str],
) -> None:
    if not isinstance(matching, dict):
        errors.append(f"{path} harus berupa object.")
        return

    matchers = matching.get("matchers")
    if not isinstance(matchers, list) or len(matchers) == 0:
        errors.append(f"{path}.matchers harus berupa list dan minimal 1 item.")
    else:
        for idx, matcher in enumerate(matchers):
            matcher_path = f"{path}.matchers[{idx}]"
            if not isinstance(matcher, dict):
                errors.append(f"{matcher_path} harus berupa object.")
                continue
            for field in ("source", "master", "mode"):
                if field not in matcher or not isinstance(matcher.get(field), str):
                    errors.append(f"{matcher_path}.{field} wajib berupa string.")
            mode = matcher.get("mode")
            if isinstance(mode, str) and mode not in SUPPORTED_MATCHER_MODES:
                errors.append(
                    f"{matcher_path}.mode harus salah satu dari: {', '.join(sorted(SUPPORTED_MATCHER_MODES))}."
                )
            normalize_cfg = matcher.get("normalize")
            if normalize_cfg is not None:
                if not isinstance(normalize_cfg, dict):
                    errors.append(f"{matcher_path}.normalize harus berupa object.")
                else:
                    allowed_keys = {
                        "trim",
                        "case_sensitive",
                        "wildcard",
                        "blank_as_wildcard",
                        "alternative_separator",
                    }
                    unknown_keys = sorted(set(normalize_cfg) - allowed_keys)
                    if unknown_keys:
                        errors.append(
                            f"{matcher_path}.normalize memiliki field tidak didukung: {', '.join(unknown_keys)}."
                        )
                    for bool_key in ("trim", "case_sensitive", "blank_as_wildcard"):
                        if bool_key in normalize_cfg and not isinstance(
                            normalize_cfg.get(bool_key), bool
                        ):
                            errors.append(
                                f"{matcher_path}.normalize.{bool_key} harus berupa boolean."
                            )
                    for str_key in ("wildcard", "alternative_separator"):
                        if str_key in normalize_cfg and not isinstance(
                            normalize_cfg.get(str_key), str
                        ):
                            errors.append(
                                f"{matcher_path}.normalize.{str_key} harus berupa string."
                            )

    if "order" in matching:
        order = matching.get("order")
        if not isinstance(order, str) or order not in SUPPORTED_RECIPE_MATCHING_ORDERS:
            errors.append(
                f"{path}.order harus salah satu dari: {', '.join(sorted(SUPPORTED_RECIPE_MATCHING_ORDERS))}."
            )
    if "first_match_wins" in matching and not isinstance(
        matching.get("first_match_wins"), bool
    ):
        errors.append(f"{path}.first_match_wins harus berupa boolean.")


def _validate_master_items(masters: object, errors: list[str]) -> None:
    if not isinstance(masters, list):
        errors.append("Field 'masters' harus berupa list jika diisi.")
        return

    for idx, item in enumerate(masters):
        if not isinstance(item, dict):
            errors.append(
                f"masters[{idx}] harus berupa object berisi file, key, dan columns."
            )
            continue
        if "file" not in item:
            errors.append(f"masters[{idx}].file wajib diisi.")
        else:
            _validate_master_file_path(
                item.get("file"),
                path=f"masters[{idx}].file",
                errors=errors,
            )
        strategy = item.get("strategy", "lookup")
        if not isinstance(strategy, str) or strategy not in SUPPORTED_MASTER_STRATEGIES:
            errors.append(
                f"masters[{idx}].strategy harus salah satu dari: {', '.join(sorted(SUPPORTED_MASTER_STRATEGIES))}."
            )
            continue
        if "sheet_name" in item and not isinstance(item.get("sheet_name"), str):
            errors.append(f"masters[{idx}].sheet_name harus berupa string.")

        if strategy == "lookup":
            has_shared_key = "key" in item
            has_split_keys = "source_key" in item or "master_key" in item
            if not has_shared_key and not has_split_keys:
                errors.append(
                    f"masters[{idx}] wajib memiliki field 'key' atau pasangan 'source_key' dan 'master_key'."
                )
            if has_split_keys:
                for required in ("source_key", "master_key"):
                    if required not in item:
                        errors.append(
                            f"masters[{idx}] wajib memiliki field '{required}' saat memakai key terpisah."
                        )
            if "columns" in item and not isinstance(item.get("columns"), list):
                errors.append(f"masters[{idx}].columns harus berupa list.")
            if "rename_columns" in item:
                rename_columns = item.get("rename_columns")
                if not isinstance(rename_columns, dict) or not all(
                    isinstance(key, str) and isinstance(value, str)
                    for key, value in rename_columns.items()
                ):
                    errors.append(
                        f"masters[{idx}].rename_columns harus berupa object string-to-string."
                    )
            if "key_aliases" in item:
                key_aliases = item.get("key_aliases")
                if not isinstance(key_aliases, dict) or not all(
                    isinstance(key, str) and isinstance(value, str)
                    for key, value in key_aliases.items()
                ):
                    errors.append(
                        f"masters[{idx}].key_aliases harus berupa object string-to-string."
                    )
            if "key_normalizer" in item:
                normalizer = item.get("key_normalizer")
                if not isinstance(normalizer, str) or normalizer not in SUPPORTED_KEY_NORMALIZERS:
                    errors.append(
                        f"masters[{idx}].key_normalizer harus salah satu dari: {', '.join(sorted(SUPPORTED_KEY_NORMALIZERS))}."
                    )
            continue

        if strategy == "lookup_rules":
            for required in ("file", "sheet_name", "target_column", "value_column", "matching"):
                if required not in item:
                    errors.append(
                        f"masters[{idx}] wajib memiliki field '{required}' untuk strategy 'lookup_rules'."
                    )
            if "target_column" in item and not isinstance(item.get("target_column"), str):
                errors.append(f"masters[{idx}].target_column harus berupa string.")
            if "value_column" in item and not isinstance(item.get("value_column"), str):
                errors.append(f"masters[{idx}].value_column harus berupa string.")
            if "matching" in item:
                _validate_matching_config(
                    item.get("matching"),
                    path=f"masters[{idx}].matching",
                    errors=errors,
                )
            if "on_missing_match" in item and not _is_supported_literal(
                item.get("on_missing_match")
            ):
                errors.append(
                    f"masters[{idx}].on_missing_match hanya boleh memakai nilai literal sederhana."
                )
            continue

        for required in ("file", "sheet_name", "target_column", "value_column", "matchers"):
            if required not in item:
                errors.append(
                    f"masters[{idx}] wajib memiliki field '{required}' untuk strategy 'ordered_rules'."
                )

        matchers = item.get("matchers")
        if "matchers" in item:
            if not isinstance(matchers, list) or len(matchers) == 0:
                errors.append(
                    f"masters[{idx}].matchers harus berupa list dan minimal 1 item."
                )
            else:
                for matcher_idx, matcher in enumerate(matchers):
                    if not isinstance(matcher, dict):
                        errors.append(
                            f"masters[{idx}].matchers[{matcher_idx}] harus berupa object."
                        )
                        continue
                    for required in ("source", "master", "mode"):
                        if required not in matcher:
                            errors.append(
                                f"masters[{idx}].matchers[{matcher_idx}] wajib memiliki field '{required}'."
                            )
                    mode = matcher.get("mode")
                    if mode is not None and (
                        not isinstance(mode, str) or mode not in SUPPORTED_MATCHER_MODES
                    ):
                        errors.append(
                            f"masters[{idx}].matchers[{matcher_idx}].mode harus salah satu dari: {', '.join(sorted(SUPPORTED_MATCHER_MODES))}."
                        )


def _validate_transform_items(transforms: object, errors: list[str]) -> None:
    if not isinstance(transforms, list):
        errors.append("Field 'transforms' harus berupa list jika diisi.")
        return

    for idx, item in enumerate(transforms):
        path = f"transforms[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{path} harus berupa object.")
            continue

        transform_type = item.get("type")
        if not isinstance(transform_type, str) or transform_type not in SUPPORTED_TRANSFORM_TYPES:
            errors.append(
                f"{path}.type harus salah satu dari: {', '.join(sorted(SUPPORTED_TRANSFORM_TYPES))}."
            )
            continue

        if transform_type == "ensure_optional_columns":
            columns = item.get("columns")
            if not isinstance(columns, list | dict):
                errors.append(f"{path}.columns harus berupa list atau object.")
            elif isinstance(columns, list) and not all(isinstance(value, str) for value in columns):
                errors.append(f"{path}.columns harus berupa list string.")
            elif isinstance(columns, dict) and not all(isinstance(key, str) for key in columns):
                errors.append(f"{path}.columns harus memakai key string.")
            continue

        if transform_type == "filter_rows":
            _validate_condition_rule(item, path=path, errors=errors)
            continue

        if transform_type == "formula":
            if "target" not in item or not isinstance(item.get("target"), str):
                errors.append(f"{path}.target wajib berupa string.")
            operation = item.get("operation")
            if not isinstance(operation, str) or operation not in SUPPORTED_FORMULA_OPERATIONS:
                errors.append(
                    f"{path}.operation harus salah satu dari: {', '.join(sorted(SUPPORTED_FORMULA_OPERATIONS))}."
                )
            operands = item.get("operands")
            if not isinstance(operands, list) or len(operands) == 0:
                errors.append(f"{path}.operands harus berupa list dan minimal 1 item.")
            else:
                for operand_idx, operand in enumerate(operands):
                    operand_path = f"{path}.operands[{operand_idx}]"
                    if not isinstance(operand, dict):
                        errors.append(f"{operand_path} harus berupa object.")
                        continue
                    has_column = "column" in operand
                    has_value = "value" in operand
                    if has_column == has_value:
                        errors.append(
                            f"{operand_path} harus memiliki tepat satu dari 'column' atau 'value'."
                        )
                    if has_column and not isinstance(operand.get("column"), str):
                        errors.append(f"{operand_path}.column harus berupa string.")
                    if has_value and not _is_supported_literal(operand.get("value")):
                        errors.append(
                            f"{operand_path}.value hanya boleh memakai nilai literal sederhana."
                        )
            if "null_as_zero" in item and not isinstance(item.get("null_as_zero"), bool):
                errors.append(f"{path}.null_as_zero harus berupa boolean.")
            continue

        if "target" not in item or not isinstance(item.get("target"), str):
            errors.append(f"{path}.target wajib berupa string.")
        cases = item.get("cases")
        if not isinstance(cases, list) or len(cases) == 0:
            errors.append(f"{path}.cases harus berupa list dan minimal 1 item.")
        else:
            for case_idx, case in enumerate(cases):
                case_path = f"{path}.cases[{case_idx}]"
                if not isinstance(case, dict):
                    errors.append(f"{case_path} harus berupa object.")
                    continue
                if "when" not in case:
                    errors.append(f"{case_path}.when wajib diisi.")
                else:
                    when = case["when"]
                    if isinstance(when, dict):
                        _validate_condition_rule(when, path=f"{case_path}.when", errors=errors)
                    elif isinstance(when, list):
                        if len(when) == 0:
                            errors.append(f"{case_path}.when harus minimal 1 kondisi.")
                        for rule_idx, rule in enumerate(when):
                            _validate_condition_rule(
                                rule,
                                path=f"{case_path}.when[{rule_idx}]",
                                errors=errors,
                            )
                    else:
                        errors.append(f"{case_path}.when harus berupa object atau list object.")
                if "value" not in case:
                    errors.append(f"{case_path}.value wajib diisi.")
                elif not _is_supported_literal(case.get("value")):
                    errors.append(
                        f"{case_path}.value hanya boleh memakai nilai literal sederhana."
                    )
        if "default" in item and not _is_supported_literal(item.get("default")):
            errors.append(f"{path}.default hanya boleh memakai nilai literal sederhana.")


def is_step_recipe_payload(payload: object) -> bool:
    return isinstance(payload, dict) and "steps" in payload and "datasets" in payload


def _validate_step_recipe_payload(payload: dict, errors: list[str]) -> None:
    for field in ("name", "datasets", "steps", "outputs"):
        if field not in payload:
            errors.append(f"Field recipe wajib belum lengkap: {field}")

    datasets = payload.get("datasets")
    if not isinstance(datasets, dict):
        errors.append("Field 'datasets' pada recipe harus berupa object.")
    else:
        if "working_dataset" not in datasets or not isinstance(
            datasets.get("working_dataset"), str
        ):
            errors.append("datasets.working_dataset wajib berupa string.")
        canonical_columns = datasets.get("canonical_columns")
        if not isinstance(canonical_columns, list) or not all(
            isinstance(item, str) for item in canonical_columns
        ):
            errors.append("datasets.canonical_columns wajib berupa list string.")

    if "outputs" in payload:
        _validate_output_items(payload.get("outputs"), errors)

    steps = payload.get("steps")
    if not isinstance(steps, list) or len(steps) == 0:
        errors.append("Field 'steps' pada recipe harus berupa list dan minimal 1 item.")
    else:
        for idx, step in enumerate(steps):
            path = f"steps[{idx}]"
            if not isinstance(step, dict):
                errors.append(f"{path} harus berupa object.")
                continue
            step_type = step.get("type")
            if not isinstance(step_type, str) or step_type not in SUPPORTED_RECIPE_STEP_TYPES:
                errors.append(
                    f"{path}.type harus salah satu dari: {', '.join(sorted(SUPPORTED_RECIPE_STEP_TYPES))}."
                )
                continue
            if "id" not in step or not isinstance(step.get("id"), str):
                errors.append(f"{path}.id wajib berupa string.")

            if step_type == "extract_sheet":
                for field in ("sheet_selector", "header_locator", "select", "write_to"):
                    if field not in step:
                        errors.append(f"{path}.{field} wajib diisi.")
                continue

            if step_type == "derive_column":
                for field in ("target", "expression"):
                    if field not in step:
                        errors.append(f"{path}.{field} wajib diisi.")
                continue

            if step_type == "update_columns":
                for field in ("when", "updates"):
                    if field not in step:
                        errors.append(f"{path}.{field} wajib diisi.")
                continue

            if step_type in {"lookup_exact", "lookup_exact_replace"}:
                for field in ("source_column", "target_column", "master"):
                    if field not in step:
                        errors.append(f"{path}.{field} wajib diisi.")
                master_cfg = step.get("master")
                if isinstance(master_cfg, dict):
                    for field in ("file", "sheet", "key", "value"):
                        if field not in master_cfg or not isinstance(master_cfg.get(field), str):
                            errors.append(f"{path}.master.{field} wajib berupa string.")
                    if "file" in master_cfg:
                        _validate_master_file_path(
                            master_cfg.get("file"),
                            path=f"{path}.master.file",
                            errors=errors,
                        )
                else:
                    errors.append(f"{path}.master harus berupa object.")
                matching = step.get("matching")
                if matching is not None and not isinstance(matching, dict):
                    errors.append(f"{path}.matching harus berupa object jika diisi.")
                continue

            if step_type == "lookup_rules":
                for field in ("inputs", "target_column", "master", "matching"):
                    if field not in step:
                        errors.append(f"{path}.{field} wajib diisi.")
                inputs = step.get("inputs")
                if not isinstance(inputs, list) or len(inputs) == 0 or not all(
                    isinstance(item, str) for item in inputs
                ):
                    errors.append(f"{path}.inputs harus berupa list string dan minimal 1 item.")
                master_cfg = step.get("master")
                if isinstance(master_cfg, dict):
                    for field in ("file", "sheet", "value"):
                        if field not in master_cfg or not isinstance(master_cfg.get(field), str):
                            errors.append(f"{path}.master.{field} wajib berupa string.")
                    if "file" in master_cfg:
                        _validate_master_file_path(
                            master_cfg.get("file"),
                            path=f"{path}.master.file",
                            errors=errors,
                        )
                else:
                    errors.append(f"{path}.master harus berupa object.")
                _validate_matching_config(
                    step.get("matching"),
                    path=f"{path}.matching",
                    errors=errors,
                )
                if "on_missing_match" in step and not _is_supported_literal(step.get("on_missing_match")):
                    errors.append(
                        f"{path}.on_missing_match hanya boleh memakai nilai literal sederhana."
                    )
                continue

            if step_type == "map_ranges":
                for field in ("source_column", "target_column", "ranges"):
                    if field not in step:
                        errors.append(f"{path}.{field} wajib diisi.")
                continue

            for field in ("group_by", "section_column", "dispatch"):
                if field not in step:
                    errors.append(f"{path}.{field} wajib diisi.")


def validate_config_payload(payload: object) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ("Isi YAML harus berupa object/dictionary di level root.",)

    if is_step_recipe_payload(payload):
        _validate_step_recipe_payload(payload, errors)
        styling = payload.get("styling")
        if styling is not None and not isinstance(styling, dict):
            errors.append("Field 'styling' harus berupa object jika diisi.")
        return tuple(errors)

    missing_fields = [field for field in REQUIRED_ROOT_FIELDS if field not in payload]
    if missing_fields:
        errors.append(
            "Field wajib belum lengkap: " + ", ".join(sorted(missing_fields))
        )
    elif not isinstance(payload.get("name"), str):
        errors.append("Field 'name' harus berupa string.")
    elif not isinstance(payload.get("source_sheet"), str):
        errors.append("Field 'source_sheet' harus berupa string.")
    elif not isinstance(payload.get("header"), dict):
        errors.append("Field 'header' harus berupa object.")

    required_source_columns = payload.get("required_source_columns")
    if required_source_columns is not None and (
        not isinstance(required_source_columns, list)
        or len(required_source_columns) == 0
        or not all(isinstance(item, str) for item in required_source_columns)
    ):
        errors.append(
            "Field 'required_source_columns' harus berupa list string dan minimal 1 item jika diisi."
        )

    if "outputs" in payload:
        _validate_output_items(payload.get("outputs"), errors)

    masters = payload.get("masters")
    if masters is not None:
        _validate_master_items(masters, errors)

    transforms = payload.get("transforms")
    if transforms is not None:
        _validate_transform_items(transforms, errors)

    styling = payload.get("styling")
    if styling is not None and not isinstance(styling, dict):
        errors.append("Field 'styling' harus berupa object jika diisi.")

    return tuple(errors)


def load_config_summary(path: Path) -> ConfigSummary:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return ConfigSummary(
            name=path.stem,
            path=path,
            is_valid=False,
            errors=(f"Gagal membaca file: {exc}",),
        )
    except yaml.YAMLError as exc:
        return ConfigSummary(
            name=path.stem,
            path=path,
            is_valid=False,
            errors=(f"Format YAML tidak valid: {exc}",),
        )

    if payload is None:
        payload = {}

    errors = validate_config_payload(payload)
    config_name = path.stem
    if isinstance(payload, dict):
        raw_name = payload.get("name")
        if isinstance(raw_name, str) and raw_name.strip():
            config_name = raw_name.strip()

    return ConfigSummary(
        name=config_name,
        path=path,
        is_valid=len(errors) == 0,
        errors=errors,
    )


def discover_configs(configs_dir: Path) -> list[ConfigSummary]:
    return [load_config_summary(path) for path in list_config_files(configs_dir)]


def load_config_payload(path: Path) -> dict:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Gagal membaca config: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Format YAML tidak valid: {exc}") from exc

    if payload is None:
        payload = {}

    errors = validate_config_payload(payload)
    if errors:
        raise ValueError("Config tidak valid: " + "; ".join(errors))
    _normalize_master_file_references(payload)
    return payload
