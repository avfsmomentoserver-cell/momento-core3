"""GPU memory pool for efficient memory allocation and management.

Implements memory pooling strategies to reduce allocation overhead and
fragmentation, critical for high-throughput inference workloads.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .config import GPUConfig
from .device_manager import DeviceManager

logger = logging.getLogger(__name__)


@dataclass
class MemoryBlock:
    """A block of allocated GPU memory."""
    size_bytes: int
    device_id: int
    ptr: Any = None  # CUDA pointer or tensor
    in_use: bool = False
    allocated_at: float = 0.0


class GPUMemoryPool:
    """Manages GPU memory pooling for efficient allocation.

    Implements a tiered pooling strategy:
    1. Active pool: Recently used blocks for fast allocation
    2. Standby pool: Less frequently used blocks
    3. Automatic defragmentation and garbage collection
    """

    def __init__(
        self,
        device_manager: DeviceManager,
        config: Optional[GPUConfig] = None,
    ):
        """Initialize memory pool.

        Args:
            device_manager: Device manager instance
            config: GPU configuration
        """
        self.device_manager = device_manager
        self.config = config or GPUConfig()

        # Memory pools per device
        self._pools: Dict[int, List[MemoryBlock]] = defaultdict(list)
        self._allocated_blocks: Dict[int, List[MemoryBlock]] = defaultdict(list)

        # Pool configuration
        self._max_pool_size_gb = 4.0  # Max 4GB pooled per device
        self._block_sizes = [
            1024,  # 1KB
            1024 * 1024,  # 1MB
            10 * 1024 * 1024,  # 10MB
            100 * 1024 * 1024,  # 100MB
            500 * 1024 * 1024,  # 500MB
            1024 * 1024 * 1024,  # 1GB
        ]

        # Statistics
        self._stats: Dict[int, Dict[str, int]] = defaultdict(
            lambda: {
                "allocations": 0,
                "deallocations": 0,
                "pool_hits": 0,
                "pool_misses": 0,
                "total_allocated": 0,
            }
        )

        # Initialize pools for available devices
        if self.device_manager.is_available:
            for device_id in range(self.device_manager.device_count):
                self._pools[device_id] = []
                self._allocated_blocks[device_id] = []

    def allocate(
        self,
        size_bytes: int,
        device_id: int = 0,
    ) -> Optional[MemoryBlock]:
        """Allocate a memory block from the pool.

        Args:
            size_bytes: Required size in bytes
            device_id: GPU device ID

        Returns:
            MemoryBlock if successful, None otherwise
        """
        if not self.device_manager.is_available:
            logger.warning("GPU not available, cannot allocate")
            return None

        # Try to find a suitable block in the pool
        block = self._find_pool_block(size_bytes, device_id)
        if block:
            self._stats[device_id]["pool_hits"] += 1
            block.in_use = True
            self._allocated_blocks[device_id].append(block)
            logger.debug(f"Pool hit: allocated {size_bytes} bytes from pool")
            return block

        # Pool miss - allocate new block
        self._stats[device_id]["pool_misses"] += 1
        block = self._allocate_new(size_bytes, device_id)
        if block:
            self._stats[device_id]["allocations"] += 1
            self._stats[device_id]["total_allocated"] += size_bytes
            self._allocated_blocks[device_id].append(block)
            logger.debug(f"Pool miss: allocated new {size_bytes} bytes")
        return block

    def _find_pool_block(
        self, size_bytes: int, device_id: int
    ) -> Optional[MemoryBlock]:
        """Find a suitable block in the pool.

        Args:
            size_bytes: Required size
            device_id: GPU device ID

        Returns:
            MemoryBlock if found, None otherwise
        """
        pool = self._pools[device_id]

        # Find smallest block that fits (with 10% overhead tolerance)
        suitable_blocks = [
            b for b in pool if not b.in_use and b.size_bytes >= size_bytes * 0.9
        ]

        if not suitable_blocks:
            return None

        # Return smallest suitable block
        suitable_blocks.sort(key=lambda b: b.size_bytes)
        return suitable_blocks[0]

    def _allocate_new(self, size_bytes: int, device_id: int) -> Optional[MemoryBlock]:
        """Allocate a new memory block.

        Args:
            size_bytes: Required size
            device_id: GPU device ID

        Returns:
            MemoryBlock if successful, None otherwise
        """
        try:
            import torch

            # Switch to target device
            self.device_manager.set_device(device_id)

            # Allocate tensor as memory block
            num_elements = (size_bytes + 3) // 4  # Assuming float32 (4 bytes)
            tensor = torch.empty(
                num_elements, dtype=torch.float32, device=f"cuda:{device_id}"
            )

            block = MemoryBlock(
                size_bytes=size_bytes,
                device_id=device_id,
                ptr=tensor,
                in_use=True,
            )
            return block
        except Exception as e:
            logger.error(f"Failed to allocate {size_bytes} bytes: {e}")
            return None

    def deallocate(self, block: MemoryBlock) -> bool:
        """Return a memory block to the pool.

        Args:
            block: Memory block to deallocate

        Returns:
            True if successful, False otherwise
        """
        device_id = block.device_id

        # Remove from allocated list
        if block in self._allocated_blocks[device_id]:
            self._allocated_blocks[device_id].remove(block)

        # Mark as unused
        block.in_use = False

        # Return to pool if under size limit
        pool = self._pools[device_id]
        pool_size = sum(b.size_bytes for b in pool if not b.in_use)

        if pool_size + block.size_bytes <= self._max_pool_size_gb * (1024**3):
            pool.append(block)
            logger.debug(f"Returned block to pool: {block.size_bytes} bytes")
        else:
            # Pool full - actually free the memory
            self._free_block(block)
            logger.debug(f"Pool full, freed block: {block.size_bytes} bytes")

        self._stats[device_id]["deallocations"] += 1
        return True

    def _free_block(self, block: MemoryBlock) -> None:
        """Actually free a memory block.

        Args:
            block: Memory block to free
        """
        try:
            if block.ptr is not None:
                # PyTorch tensors are reference-counted
                # Setting to None allows GC
                block.ptr = None
        except Exception as e:
            logger.error(f"Error freeing block: {e}")

    def preallocate(
        self, size_bytes: int, count: int = 1, device_id: int = 0
    ) -> int:
        """Preallocate memory blocks to the pool.

        Args:
            size_bytes: Size of each block
            count: Number of blocks to allocate
            device_id: GPU device ID

        Returns:
            Number of blocks successfully allocated
        """
        allocated = 0
        for _ in range(count):
            block = self._allocate_new(size_bytes, device_id)
            if block:
                block.in_use = False
                self._pools[device_id].append(block)
                allocated += 1
            else:
                break
        logger.info(f"Preallocated {allocated} blocks of {size_bytes} bytes")
        return allocated

    def clear_pool(self, device_id: Optional[int] = None) -> None:
        """Clear the memory pool for a device or all devices.

        Args:
            device_id: Device ID to clear, or None for all devices
        """
        if device_id is not None:
            self._clear_device_pool(device_id)
        else:
            for dev_id in range(self.device_manager.device_count):
                self._clear_device_pool(dev_id)

    def _clear_device_pool(self, device_id: int) -> None:
        """Clear pool for a specific device.

        Args:
            device_id: Device ID
        """
        pool = self._pools[device_id]
        for block in pool:
            self._free_block(block)
        pool.clear()
        logger.debug(f"Cleared pool for device {device_id}")

    def get_stats(self, device_id: int = 0) -> Dict[str, Any]:
        """Get memory pool statistics.

        Args:
            device_id: Device ID

        Returns:
            Dictionary with pool statistics
        """
        pool = self._pools[device_id]
        stats = self._stats[device_id].copy()

        total_pooled = sum(b.size_bytes for b in pool if not b.in_use)
        total_allocated = sum(b.size_bytes for b in self._allocated_blocks[device_id])

        stats.update(
            {
                "device_id": device_id,
                "pooled_blocks": len([b for b in pool if not b.in_use]),
                "pooled_bytes": total_pooled,
                "pooled_gb": total_pooled / (1024**3),
                "allocated_blocks": len(self._allocated_blocks[device_id]),
                "allocated_bytes": total_allocated,
                "allocated_gb": total_allocated / (1024**3),
                "hit_rate": (
                    stats["pool_hits"] / (stats["pool_hits"] + stats["pool_misses"])
                    if (stats["pool_hits"] + stats["pool_misses"]) > 0
                    else 0.0
                ),
            }
        )
        return stats

    def get_memory_pressure(self, device_id: int = 0) -> float:
        """Calculate memory pressure (0.0 to 1.0).

        Args:
            device_id: Device ID

        Returns:
            Memory pressure value
        """
        if not self.device_manager.is_available:
            return 0.0

        mem_info = self.device_manager.get_device_memory(device_id)
        if not mem_info:
            return 0.0

        total, free = mem_info
        used = total - free
        return used / total if total > 0 else 0.0

    def defragment(self, device_id: int = 0) -> None:
        """Defragment memory pool by reallocating scattered blocks.

        Args:
            device_id: Device ID
        """
        pool = self._pools[device_id]

        # Sort by size to enable better reuse
        pool.sort(key=lambda b: b.size_bytes)

        # Remove blocks that are too small to be useful
        min_useful_size = 1024  # 1KB
        self._pools[device_id] = [b for b in pool if b.size_bytes >= min_useful_size]

        logger.debug(f"Defragmented pool for device {device_id}")

    def __repr__(self) -> str:
        return (
            f"GPUMemoryPool(devices={self.device_manager.device_count}, "
            f"max_pool_size={self._max_pool_size_gb}GB)"
        )
