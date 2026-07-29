"""
V5 Realtime Ingestion Layer

Core ingestion pipeline with FPGA acceleration and DPDK networking.
"""

from .pipeline import IngestionPipeline
from .coordinator import IngestionCoordinator

__all__ = ["IngestionPipeline", "IngestionCoordinator"]
