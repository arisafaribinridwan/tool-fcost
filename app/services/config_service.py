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

    masters = payload.get("masters")
    if masters is not None and not isinstance(masters, list):
        errors.append("Field 'masters' harus berupa list jika diisi.")

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
