from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import yaml

from app.services.config_service import discover_configs, load_config_payload


JOB_PROFILES_FILE_NAME = "job_profiles.yaml"
_JOB_ID_SLUG_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class JobProfileSummary:
    id: str
    label: str
    config_file: str
    enabled: bool
    is_valid: bool
    errors: tuple[str, ...]
    config_path: Path | None
    master_files: tuple[str, ...]


@dataclass(frozen=True)
class JobProfileRecord:
    id: str
    label: str
    config_file: str
    enabled: bool


def get_job_profiles_path(configs_dir: Path) -> Path:
    return configs_dir / JOB_PROFILES_FILE_NAME


def _make_job_id(label: str) -> str:
    slug = _JOB_ID_SLUG_RE.sub("-", label.strip().casefold()).strip("-")
    return slug or "job"


def _extract_master_files(payload: dict) -> tuple[str, ...]:
    master_files: list[str] = []

    for master_cfg in payload.get("masters") or []:
        if isinstance(master_cfg, dict):
            file_ref = master_cfg.get("file")
            if isinstance(file_ref, str) and file_ref not in master_files:
                master_files.append(file_ref)

    for step_cfg in payload.get("steps") or []:
        if not isinstance(step_cfg, dict):
            continue
        master_cfg = step_cfg.get("master")
        if not isinstance(master_cfg, dict):
            continue
        file_ref = master_cfg.get("file")
        if isinstance(file_ref, str) and file_ref not in master_files:
            master_files.append(file_ref)

    return tuple(master_files)


def _validate_job_record(raw_item: object, *, index: int) -> tuple[JobProfileRecord | None, tuple[str, ...]]:
    path = f"jobs[{index}]"
    errors: list[str] = []
    if not isinstance(raw_item, dict):
        return None, (f"{path} harus berupa object.",)

    raw_id = raw_item.get("id")
    raw_label = raw_item.get("label")
    raw_config_file = raw_item.get("config_file")
    raw_enabled = raw_item.get("enabled")

    if not isinstance(raw_id, str) or not raw_id.strip():
        errors.append(f"{path}.id wajib berupa string non-kosong.")
    if not isinstance(raw_label, str) or not raw_label.strip():
        errors.append(f"{path}.label wajib berupa string non-kosong.")
    if not isinstance(raw_config_file, str) or not raw_config_file.strip():
        errors.append(f"{path}.config_file wajib berupa string non-kosong.")
    if not isinstance(raw_enabled, bool):
        errors.append(f"{path}.enabled wajib berupa boolean.")

    if errors:
        return None, tuple(errors)

    return (
        JobProfileRecord(
            id=raw_id.strip(),
            label=raw_label.strip(),
            config_file=raw_config_file.strip(),
            enabled=raw_enabled,
        ),
        (),
    )


def load_job_profile_records(configs_dir: Path) -> list[JobProfileRecord]:
    path = get_job_profiles_path(configs_dir)
    if not path.exists():
        return []

    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Gagal membaca registry job profile: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Format job profile YAML tidak valid: {exc}") from exc

    if payload is None:
        return []

    if not isinstance(payload, dict):
        raise ValueError("Registry job profile harus berupa object dengan field 'jobs'.")

    raw_jobs = payload.get("jobs")
    if raw_jobs is None:
        return []
    if not isinstance(raw_jobs, list):
        raise ValueError("Field 'jobs' pada registry job profile harus berupa list.")

    records: list[JobProfileRecord] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_labels: set[str] = set()

    for index, raw_item in enumerate(raw_jobs):
        record, item_errors = _validate_job_record(raw_item, index=index)
        if item_errors:
            errors.extend(item_errors)
            continue
        assert record is not None
        normalized_id = record.id.casefold()
        normalized_label = record.label.casefold()
        if normalized_id in seen_ids:
            errors.append(f"jobs[{index}].id duplikat: '{record.id}'.")
        else:
            seen_ids.add(normalized_id)
        if normalized_label in seen_labels:
            errors.append(f"jobs[{index}].label duplikat: '{record.label}'.")
        else:
            seen_labels.add(normalized_label)
        records.append(record)

    if errors:
        raise ValueError("Registry job profile tidak valid: " + "; ".join(errors))

    return records


def save_job_profile_records(configs_dir: Path, records: list[JobProfileRecord]) -> Path:
    path = get_job_profiles_path(configs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "jobs": [
            {
                "id": record.id,
                "label": record.label,
                "config_file": record.config_file,
                "enabled": record.enabled,
            }
            for record in records
        ]
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    return path


def upsert_job_profile_record(
    configs_dir: Path,
    *,
    label: str,
    config_file: str,
    enabled: bool,
    record_id: str | None = None,
) -> JobProfileRecord:
    normalized_label = label.strip()
    normalized_config_file = config_file.strip()
    if not normalized_label:
        raise ValueError("Nama job wajib diisi.")
    if not normalized_config_file:
        raise ValueError("Config job wajib dipilih.")

    records = load_job_profile_records(configs_dir)
    target_id = record_id.strip() if isinstance(record_id, str) and record_id.strip() else _make_job_id(normalized_label)
    normalized_target_id = target_id.casefold()
    normalized_target_label = normalized_label.casefold()

    if record_id is None and any(record.label.casefold() == normalized_target_label for record in records):
        raise ValueError(f"Nama job sudah dipakai: '{normalized_label}'.")

    updated = False
    result_record = JobProfileRecord(
        id=target_id,
        label=normalized_label,
        config_file=normalized_config_file,
        enabled=enabled,
    )

    next_records: list[JobProfileRecord] = []
    for record in records:
        if record.id.casefold() == normalized_target_id:
            next_records.append(result_record)
            updated = True
            continue
        if record.label.casefold() == normalized_target_label:
            raise ValueError(f"Nama job sudah dipakai: '{normalized_label}'.")
        next_records.append(record)

    if not updated:
        existing_ids = {record.id.casefold() for record in records}
        suffix = 2
        unique_id = target_id
        while unique_id.casefold() in existing_ids:
            unique_id = f"{target_id}-{suffix}"
            suffix += 1
        result_record = JobProfileRecord(
            id=unique_id,
            label=normalized_label,
            config_file=normalized_config_file,
            enabled=enabled,
        )
        next_records.append(result_record)

    next_records.sort(key=lambda item: item.label.casefold())
    save_job_profile_records(configs_dir, next_records)
    return result_record


def discover_job_profiles(configs_dir: Path) -> list[JobProfileSummary]:
    config_summaries = discover_configs(configs_dir)
    config_by_name = {item.path.name.casefold(): item for item in config_summaries}

    try:
        records = load_job_profile_records(configs_dir)
    except ValueError as exc:
        return [
            JobProfileSummary(
                id="registry-error",
                label="Registry job profile invalid",
                config_file=JOB_PROFILES_FILE_NAME,
                enabled=False,
                is_valid=False,
                errors=(str(exc),),
                config_path=None,
                master_files=(),
            )
        ]

    results: list[JobProfileSummary] = []
    for record in records:
        config_summary = config_by_name.get(record.config_file.casefold())
        errors: list[str] = []
        config_path: Path | None = None
        master_files: tuple[str, ...] = ()

        if config_summary is None:
            errors.append(f"Config job tidak ditemukan: {record.config_file}")
        elif not config_summary.is_valid:
            errors.append(
                f"Config job tidak valid: {'; '.join(config_summary.errors[:2])}"
            )
        else:
            config_path = config_summary.path
            try:
                payload = load_config_payload(config_summary.path)
            except ValueError as exc:
                errors.append(str(exc))
            else:
                master_files = _extract_master_files(payload)

        results.append(
            JobProfileSummary(
                id=record.id,
                label=record.label,
                config_file=record.config_file,
                enabled=record.enabled,
                is_valid=record.enabled and len(errors) == 0,
                errors=tuple(errors),
                config_path=config_path,
                master_files=master_files,
            )
        )

    return sorted(results, key=lambda item: item.label.casefold())


__all__ = [
    "JOB_PROFILES_FILE_NAME",
    "JobProfileRecord",
    "JobProfileSummary",
    "discover_job_profiles",
    "get_job_profiles_path",
    "load_job_profile_records",
    "save_job_profile_records",
    "upsert_job_profile_record",
]
