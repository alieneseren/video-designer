"""
pipeline_integration.py
=======================
Kök dizin köprüsü: core/pipeline_integration.py içeriğini dışa aktarır.
"""

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from core.pipeline_integration import (
        PipelineIntegration,
        pipeline_integration
    )
except ImportError:
    from src.core.pipeline_integration import (
        PipelineIntegration,
        pipeline_integration
    )

__all__ = [
    "PipelineIntegration",
    "pipeline_integration"
]
