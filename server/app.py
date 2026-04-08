"""Compatibility entrypoint for OpenEnv multi-mode deployment checks."""

from __future__ import annotations

from apps.api.server.app import app as app
from apps.api.server.app import main as _main


def main() -> None:
    _main()


if __name__ == "__main__":
    main()

