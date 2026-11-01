"""
pipeline_orchestrator.py
========================
Kök dizin köprüsü: core/pipeline_orchestrator.py içeriğini dışa aktarır.
"""

import sys
from pathlib import Path

# PYTHONPATH koruması
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from core.pipeline_orchestrator import (
        PipelineOrchestrator,
        pipeline_orchestrator
    )
except ImportError:
    from src.core.pipeline_orchestrator import (
        PipelineOrchestrator,
        pipeline_orchestrator
    )

__all__ = [
    "PipelineOrchestrator",
    "pipeline_orchestrator"
]
