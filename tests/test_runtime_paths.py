from __future__ import annotations

from app import get_app_paths, get_runtime_root


def test_get_app_paths_uses_expected_runtime_folder_names(tmp_path):
    paths = get_app_paths(tmp_path)

    assert paths.project_root == tmp_path
    assert paths.configs_dir == tmp_path / "configs"
    assert paths.masters_dir == tmp_path / "masters"
    assert paths.uploads_dir == tmp_path / "uploads"
    assert paths.outputs_dir == tmp_path / "outputs"


def test_ensure_runtime_dirs_creates_all_runtime_directories(app_paths):
    assert app_paths.configs_dir.is_dir()
    assert app_paths.masters_dir.is_dir()
    assert app_paths.uploads_dir.is_dir()
    assert app_paths.outputs_dir.is_dir()


def test_get_runtime_root_prefers_explicit_project_root(tmp_path):
    assert get_runtime_root(tmp_path) == tmp_path
