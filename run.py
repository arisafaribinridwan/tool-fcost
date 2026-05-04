from __future__ import annotations

import sys

from app import ensure_runtime_dirs
from app.ui import run_desktop_app


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    paths = ensure_runtime_dirs()

    if "--settings" in args:
        from app.ui.settings import JobSettingsApp

        app = JobSettingsApp(paths)
        app.mainloop()
        return

    run_desktop_app(paths)


if __name__ == "__main__":
    main()
