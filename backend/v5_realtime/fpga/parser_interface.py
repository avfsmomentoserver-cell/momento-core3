"""
FPGA Parser Interface for V5 Realtime Ingestion.

Defines the interface for FPGA-accelerated parsing operations.
Target latencies: FIX parsing 14ns, orderbook updates 4ns, feature extraction 50ns.

This module provides:
- Abstract interface for FPGA parsers
- Memory-mapped FPGA communication
- PCIe transaction management
- HBM (High Bandwidth Memory) data transfer
"""

from __future__ import annotations

import logging
import mmap
import os
import struct
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("v5_realtime.fpga.parser")


class FPGADeviceType(Enum):
    """Supported FPGA device types."""
    ALVEO_UL3524 = "alveo_ul3524"
    ALVEO_U50 = "alveo_u50"
    ALVEO_U200 = "alveo_u200"
    ALVEO_U250 = "alveo_u250"


@dataclass
class FPGASpecs:
    """FPGA hardware specifications."""
    device_type: FPGADeviceType
    fpga_model: str
    hbm_size_gb: int
    hbm_bandwidth_gbps: int
    clock_mhz: int
    pcie_gen: int
    pcie_lanes: int


# Default specs for Alveo UL3524
DEFAULT_SPECS = FPGASpecs(
    device_type=FPGADeviceType.ALVEO_UL3524,
    fpga_model="UltraScale+ VU9P",
    hbm_size_gb=8,
    hbm_bandwidth_gbps=460,
    clock_mhz=644,
    pcie_gen=4,
    pcie_lanes=16,
)


@dataclass
class ParserMetrics:
    """Parser performance metrics."""
    total_parsed: int = 0
    total_errors: int = 0
    avg_latency_ns: float = 0.0
    max_latency_ns: float = 0.0
    min_latency_ns: float = float("inf")
    total_bytes_processed: int = 0
    parse_rate_mbps: float = 0.0


class FPGAParserInterface(ABC):
    """
    Abstract interface for FPGA-accelerated parsers.

    All FPGA parsers must implement this interface to ensure
    consistent behavior and performance monitoring.
    """

    def __init__(
        self,
        device_path: Optional[Path] = None,
        specs: Optional[FPGASpecs] = None,
        enable_simulation: bool = True,
    ):
        """
        Initialize FPGA parser.

        Args:
            device_path: Path to FPGA device (e.g., /dev/xfpga0)
            specs: FPGA hardware specifications
            enable_simulation: Use simulation mode if hardware not available
        """
        self._device_path = device_path or Path("/dev/xfpga0")
        self._specs = specs or DEFAULT_SPECS
        self._enable_simulation = enable_simulation
        self._is_hardware_available = False
        self._mmap_region: Optional[mmap.mmap] = None
        self._metrics = ParserMetrics()
        self._last_update = time.time()

        # Try to initialize hardware
        self._initialize_hardware()

    def _initialize_hardware(self) -> None:
        """Initialize FPGA hardware connection."""
        if self._enable_simulation:
            logger.info("FPGA parser running in simulation mode")
            self._is_hardware_available = False
            return

        try:
            if self._device_path.exists():
                # Open device file for memory-mapped I/O
                fd = os.open(self._device_path, os.O_RDWR | os.O_SYNC)
                self._mmap_region = mmap.mmap(
                    fd,
                    0,  # Map entire device
                    mmap.MAP_SHARED,
                    mmap.PROT_READ | mmap.PROT_WRITE,
                )
                os.close(fd)
                self._is_hardware_available = True
                logger.info(f"FPGA hardware initialized: {self._device_path}")
            else:
                logger.warning(f"FPGA device not found: {self._device_path}, using simulation")
                self._is_hardware_available = False
        except Exception as e:
            logger.warning(f"FPGA hardware initialization failed: {e}, using simulation")
            self._is_hardware_available = False

    @property
    def is_hardware_available(self) -> bool:
        """Check if FPGA hardware is available."""
        return self._is_hardware_available

    @property
    def specs(self) -> FPGASpecs:
        """Get FPGA specifications."""
        return self._specs

    @property
    def metrics(self) -> ParserMetrics:
        """Get parser metrics."""
        self._update_metrics()
        return self._metrics

    def _update_metrics(self) -> None:
        """Update rate calculations."""
        now = time.time()
        elapsed = now - self._last_update
        if elapsed > 0:
            self._metrics.parse_rate_mbps = (
                self._metrics.total_bytes_processed / elapsed / 1_000_000
            )
            self._last_update = now

    @abstractmethod
    def parse(self, data: bytes) -> Any:
        """
        Parse data using FPGA acceleration.

        Args:
            data: Raw input data to parse

        Returns:
            Parsed data structure

        Raises:
            ParseError: If parsing fails
        """
        pass

    @abstractmethod
    def parse_batch(self, data_list: list[bytes]) -> list[Any]:
        """
        Parse multiple data items in batch (HBM-accelerated).

        Args:
            data_list: List of raw data items

        Returns:
            List of parsed data structures
        """
        pass

    @abstractmethod
    def reset_metrics(self) -> None:
        """Reset performance metrics."""
        pass

    def close(self) -> None:
        """Close FPGA connection and cleanup resources."""
        if self._mmap_region:
            try:
                self._mmap_region.close()
                logger.info("FPGA connection closed")
            except Exception as e:
                logger.warning(f"Error closing FPGA connection: {e}")


class ParseError(Exception):
    """Parse error exception."""
    pass


class FPGASimulationError(Exception):
    """FPGA simulation error exception."""
    pass
