from __future__ import annotations

import os

from app import create_app

app = create_app()


def _is_debug_enabled() -> bool:
    return os.getenv("FLASK_DEBUG", "0") == "1"


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=_is_debug_enabled(),
    )
