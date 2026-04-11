"""OpenEnv-validator entry point for SUPERCELL.

This module exists so `openenv validate` can find a `server/app.py`
with a `main()` function. The actual environment code lives flat at
the repo root (`app.py`, `environment.py`, `models.py`, ...); this
wrapper just makes sure the repo root is on `sys.path` and then
delegates to the root `app.main`.

Supported entry points:
    - `uv run server`           (via [project.scripts] server = "server.app:main")
    - `python -m server.app`
    - `python server/app.py`
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is importable when run as `python server/app.py`
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app import create_app  # noqa: E402  (import after sys.path edit)
from app import main as _root_main  # noqa: E402

# Re-export the ASGI application so `uvicorn server.app:app` also works
app = create_app()


def main() -> None:
    """Entry point for `uv run server` — delegates to the root app.main()."""
    _root_main()


if __name__ == "__main__":
    main()
