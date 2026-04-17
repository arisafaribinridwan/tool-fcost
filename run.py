from __future__ import annotations

from app import ensure_runtime_dirs



if __name__ == "__main__":
    paths = ensure_runtime_dirs()
    print("Excel Automation Tool desktop skeleton belum dibuat.")
    print(f"Project root : {paths.project_root}")
    print(f"Configs dir  : {paths.configs_dir}")
    print(f"Masters dir  : {paths.masters_dir}")
    print(f"Uploads dir  : {paths.uploads_dir}")
    print(f"Outputs dir  : {paths.outputs_dir}")
