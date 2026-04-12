"""Re-export from root environment module.

The hackathon validator imports ``from server.environment import ...``
following the canonical OpenEnv scaffold. Our code lives flat at the
repo root, so this module just re-exports everything.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from environment import ATCEnvironment  # noqa: F401, E402

__all__ = ["ATCEnvironment"]
