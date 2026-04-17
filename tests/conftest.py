from __future__ import annotations

import pytest

from app import AppPaths, ensure_runtime_dirs


@pytest.fixture()
def app_paths(tmp_path):
    paths = AppPaths(
        project_root=tmp_path,
        configs_dir=tmp_path / "configs",
        masters_dir=tmp_path / "masters",
        uploads_dir=tmp_path / "uploads",
        outputs_dir=tmp_path / "outputs",
    )
    return ensure_runtime_dirs(paths)
