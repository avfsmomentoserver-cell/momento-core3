"""
DPDK Configuration for V5 Realtime Ingestion.

Kernel-bypass networking configuration for ultra-low latency packet processing.
Target: <2μs packet processing, 100M+ packets/second.

This module provides:
- DPDK EAL (Environment Abstraction Layer) configuration
- Memory pool configuration
- Queue configuration
- CPU pinning settings
- NUMA awareness
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("v5_realtime.dpdk.config")


class DPDKDriverType(Enum):
    """Supported DPDK network drivers."""
    IXGBE = "ixgbe"  # Intel 10GbE
    I40E = "i40e"  # Intel 40GbE
    MLX5 = "mlx5"  # Mellanox ConnectX
    ENIC = "enic"  # Cisco VIC
    AF_XDP = "af_xdp"  # Linux AF_XDP


class HugePagePolicy(Enum):
    """Huge page configuration policy."""
    SIZE_2MB = "2MB"
    SIZE_1GB = "1GB"
    AUTO = "auto"


@dataclass
class DPDKConfig:
    """
    DPDK configuration for kernel-bypass networking.

    Based on V5 specifications:
    - Memory channels: 4
    - RX queues: 16
    - TX queues: 16
    - Descriptor rings: 4096
    - Latency: <2μs packet processing
    - Throughput: 100M+ packets/second
    """

    # EAL Configuration
    eal_args: list[str] = field(default_factory=lambda: [
        "-c", "0xFF",  # Core mask (use cores 0-7)
        "-n", "4",  # Number of memory channels
    ])

    # Memory Configuration
    memory_channels: int = 4
    memory_size_mb: int = 4096
    hugepage_policy: HugePagePolicy = HugePagePolicy.SIZE_1GB
    hugepage_mount: Optional[Path] = None

    # Queue Configuration
    rx_queues: int = 16
    tx_queues: int = 16
    rx_desc_ring_size: int = 4096
    tx_desc_ring_size: int = 4096

    # Memory Pool Configuration
    mbuf_size: int = 2048  # Size of each mbuf
    mbuf_pool_size: int = 8192  # Number of mbufs in pool
    cache_size: int = 512  # Per-core cache size

    # CPU Configuration
    cpu_pinning: bool = True
    isolated_cores: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7])
    main_core: int = 0

    # NUMA Configuration
    numa_aware: bool = True
    preferred_numa_node: int = 0

    # Network Configuration
    pci_addresses: list[str] = field(default_factory=list)
    driver_type: DPDKDriverType = DPDKDriverType.IXGBE
    promiscuous_mode: bool = False

    # Performance Configuration
    burst_size: int = 32  # Packets per burst
    poll_mode: bool = True  # Poll mode driver (interrupt-free)
    zero_copy: bool = True  # Enable zero-copy where possible

    # Monitoring
    enable_stats: bool = True
    stats_interval_ms: int = 1000

    # Simulation Mode
    enable_simulation: bool = True  # Use simulation if DPDK not available

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.rx_queues < 1 or self.rx_queues > 1024:
            raise ValueError("rx_queues must be between 1 and 1024")

        if self.tx_queues < 1 or self.tx_queues > 1024:
            raise ValueError("tx_queues must be between 1 and 1024")

        if not (self.rx_desc_ring_size & (self.rx_desc_ring_size - 1) == 0):
            raise ValueError("rx_desc_ring_size must be power of 2")

        if not (self.tx_desc_ring_size & (self.tx_desc_ring_size - 1) == 0):
            raise ValueError("tx_desc_ring_size must be power of 2")

        # Set default hugepage mount
        if self.hugepage_mount is None:
            if self.hugepage_policy == HugePagePolicy.SIZE_1GB:
                self.hugepage_mount = Path("/mnt/huge-1GB")
            else:
                self.hugepage_mount = Path("/mnt/huge")

    def get_eal_command(self) -> str:
        """Generate DPDK EAL command line."""
        args = self.eal_args.copy()

        # Add memory configuration
        args.extend(["-m", str(self.memory_size_mb)])

        # Add hugepage directory
        if self.hugepage_mount and self.hugepage_mount.exists():
            args.extend(["--huge-dir", str(self.hugepage_mount)])

        # Add file prefix for multiple instances
        args.extend(["--file-prefix", "v5_realtime"])

        # Add PCI devices
        for pci in self.pci_addresses:
            args.extend(["-a", pci])

        return " ".join(args)

    def get_hugepage_command(self) -> str:
        """Generate command to reserve huge pages."""
        if self.hugepage_policy == HugePagePolicy.SIZE_1GB:
            # Reserve 1GB huge pages
            num_pages = 4  # 4GB total
            return f"echo {num_pages} > /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages"
        else:
            # Reserve 2MB huge pages
            num_pages = 2048  # 4GB total
            return f"echo {num_pages} > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages"

    def get_isolcpus_command(self) -> str:
        """Generate command to isolate CPUs."""
        if not self.isolated_cores:
            return ""

        core_list = ",".join(map(str, self.isolated_cores))
        return f"isolcpus={core_list}"

    def validate_system(self) -> dict[str, bool]:
        """
        Validate system configuration for DPDK.

        Returns:
            Dictionary of validation results
        """
        results = {
            "hugepages_available": self._check_hugepages(),
            "pci_devices_available": self._check_pci_devices(),
            "numa_available": self._check_numa(),
            "cpu_isolation": self._check_cpu_isolation(),
            "hugepage_mounted": self._check_hugepage_mount(),
        }

        return results

    def _check_hugepages(self) -> bool:
        """Check if huge pages are available."""
        try:
            if self.hugepage_policy == HugePagePolicy.SIZE_1GB:
                path = Path("/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages")
            else:
                path = Path("/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages")

            if path.exists():
                nr_hugepages = int(path.read_text().strip())
                return nr_hugepages > 0
            return False
        except Exception as e:
            logger.warning(f"Huge page check failed: {e}")
            return False

    def _check_pci_devices(self) -> bool:
        """Check if PCI devices are available."""
        if not self.pci_addresses:
            return True  # Optional if using simulation

        for pci in self.pci_addresses:
            path = Path(f"/sys/bus/pci/devices/{pci}")
            if not path.exists():
                logger.warning(f"PCI device not found: {pci}")
                return False
        return True

    def _check_numa(self) -> bool:
        """Check if NUMA is available."""
        try:
            return Path("/sys/devices/system/node").exists()
        except Exception:
            return False

    def _check_cpu_isolation(self) -> bool:
        """Check if CPUs are isolated."""
        if not self.isolated_cores:
            return True

        try:
            cmdline = Path("/proc/cmdline").read_text()
            return "isolcpus" in cmdline
        except Exception:
            return False

    def _check_hugepage_mount(self) -> bool:
        """Check if huge page directory is mounted."""
        if not self.hugepage_mount:
            return True

        try:
            return self.hugepage_mount.is_mount()
        except Exception:
            return False

    def get_system_info(self) -> dict[str, Any]:
        """Get system information relevant to DPDK."""
        info = {
            "numa_nodes": self._get_numa_nodes(),
            "cpu_count": os.cpu_count(),
            "hugepage_info": self._get_hugepage_info(),
            "pci_devices": self._get_pci_devices(),
        }
        return info

    def _get_numa_nodes(self) -> int:
        """Get number of NUMA nodes."""
        try:
            node_dirs = list(Path("/sys/devices/system/node").glob("node*"))
            return len(node_dirs)
        except Exception:
            return 1

    def _get_hugepage_info(self) -> dict[str, int]:
        """Get huge page information."""
        info = {}
        try:
            for size_dir in Path("/sys/kernel/mm/hugepages").glob("hugepages-*"):
                size = size_dir.name
                nr_path = size_dir / "nr_hugepages"
                free_path = size_dir / "free_hugepages"
                info[size] = {
                    "total": int(nr_path.read_text().strip()) if nr_path.exists() else 0,
                    "free": int(free_path.read_text().strip()) if free_path.exists() else 0,
                }
        except Exception as e:
            logger.warning(f"Failed to get huge page info: {e}")
        return info

    def _get_pci_devices(self) -> list[dict[str, str]]:
        """Get available PCI network devices."""
        devices = []
        try:
            net_dir = Path("/sys/bus/pci/devices")
            for device in net_dir.iterdir():
                if device.is_dir():
                    vendor = (device / "vendor").read_text().strip() if (device / "vendor").exists() else ""
                    device_id = (device / "device").read_text().strip() if (device / "device").exists() else ""
                    devices.append({
                        "address": device.name,
                        "vendor": vendor,
                        "device": device_id,
                    })
        except Exception as e:
            logger.warning(f"Failed to get PCI devices: {e}")
        return devices


# Default configuration for production
DEFAULT_CONFIG = DPDKConfig(
    memory_channels=4,
    rx_queues=16,
    tx_queues=16,
    rx_desc_ring_size=4096,
    tx_desc_ring_size=4096,
    hugepage_policy=HugePagePolicy.SIZE_1GB,
    cpu_pinning=True,
    isolated_cores=[1, 2, 3, 4, 5, 6, 7],
    poll_mode=True,
    zero_copy=True,
)

# Configuration for testing/simulation
SIMULATION_CONFIG = DPDKConfig(
    memory_channels=2,
    rx_queues=4,
    tx_queues=4,
    rx_desc_ring_size=512,
    tx_desc_ring_size=512,
    hugepage_policy=HugePagePolicy.SIZE_2MB,
    cpu_pinning=False,
    isolated_cores=[],
    poll_mode=True,
    zero_copy=False,
    enable_simulation=True,
)
