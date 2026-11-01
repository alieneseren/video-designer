"""
query_builder.py
================
Kök dizin köprüsü: core/query_builder.py içeriğini dışa aktarır.
"""

import sys
from pathlib import Path

# PYTHONPATH koruması
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from core.query_builder import (
        QueryBuilder,
        ContextLockedQuery,
        query_builder,
        NBA_TEAMS,
        PLAYER_CAREER_MAP,
        STANDARD_CIVILIAN_NEGATIVES
    )
except ImportError:
    from src.core.query_builder import (
        QueryBuilder,
        ContextLockedQuery,
        query_builder,
        NBA_TEAMS,
        PLAYER_CAREER_MAP,
        STANDARD_CIVILIAN_NEGATIVES
    )

__all__ = [
    "QueryBuilder",
    "ContextLockedQuery",
    "query_builder",
    "NBA_TEAMS",
    "PLAYER_CAREER_MAP",
    "STANDARD_CIVILIAN_NEGATIVES"
]
