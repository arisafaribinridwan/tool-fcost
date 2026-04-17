from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


REQUIRED_ROOT_FIELDS = ("name", "source_sheet", "header", "outputs")


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


def validate_config_payload(payload: object) -> tuple[str, ...]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ("Isi YAML harus berupa object/dictionary di level root.",)

    missing_fields = [field for field in REQUIRED_ROOT_FIELDS if field not in payload]
    if missing_fields:
        errors.append(
            "Field wajib belum lengkap: " + ", ".join(sorted(missing_fields))
        )

    outputs = payload.get("outputs")
    if "outputs" in payload:
        if not isinstance(outputs, list) or len(outputs) == 0:
            errors.append("Field 'outputs' wajib berupa list dan minimal 1 item.")
        else:
            for idx, item in enumerate(outputs):
                if not isinstance(item, dict):
                    errors.append(
                        f"outputs[{idx}] harus berupa object dengan sheet_name dan rule output."
                    )
                    continue
                if "sheet_name" not in item:
                    errors.append(f"outputs[{idx}] wajib memiliki field 'sheet_name'.")
                has_columns = "columns" in item
                has_pivot = "pivot" in item
                if not has_columns and not has_pivot:
                    errors.append(
                        f"outputs[{idx}] wajib memiliki minimal salah satu: 'columns' atau 'pivot'."
                    )
                if has_columns and not isinstance(item.get("columns"), list):
                    errors.append(f"outputs[{idx}].columns harus berupa list.")
                if has_pivot and not isinstance(item.get("pivot"), dict):
                    errors.append(f"outputs[{idx}].pivot harus berupa object.")

    masters = payload.get("masters")
    if masters is not None:
        if not isinstance(masters, list):
            errors.append("Field 'masters' harus berupa list jika diisi.")
        else:
            for idx, item in enumerate(masters):
                if not isinstance(item, dict):
                    errors.append(
                        f"masters[{idx}] harus berupa object berisi file, key, dan columns."
                    )
                    continue
                for required in ("file", "key"):
                    if required not in item:
                        errors.append(
                            f"masters[{idx}] wajib memiliki field '{required}'."
                        )
                if "columns" in item and not isinstance(item.get("columns"), list):
                    errors.append(f"masters[{idx}].columns harus berupa list.")

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
    return payload
