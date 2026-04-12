"""Re-export from root graders module."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from graders import (  # noqa: F401, E402
    GRADERS,
    MAX_STRICT_SCORE,
    MIN_STRICT_SCORE,
    grade_easy,
    grade_episode,
    grade_extra_hard,
    grade_hard,
    grade_medium,
    strict_score,
)

__all__ = [
    "GRADERS",
    "MAX_STRICT_SCORE",
    "MIN_STRICT_SCORE",
    "grade_easy",
    "grade_episode",
    "grade_extra_hard",
    "grade_hard",
    "grade_medium",
    "strict_score",
]
