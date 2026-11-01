"""
fallback_engine.py
==================
Kök dizin köprüsü: core/fallback_engine.py içeriğini dışa aktarır.
"""

import sys
from pathlib import Path

# PYTHONPATH koruması
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from core.fallback_engine import (
        FallbackEngine,
        fallback_engine,
        get_system_font
    )
except ImportError:
    from src.core.fallback_engine import (
        FallbackEngine,
        fallback_engine,
        get_system_font
    )

__all__ = [
    "FallbackEngine",
    "fallback_engine",
    "get_system_font"
]
