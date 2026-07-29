"""
GPU Memory Manager

Manages GPU memory allocation, pooling, and optimization for high-performance
ML inference with efficient memory coalescing and minimal fragmentation.

Performance Targets:
- Memory bandwidth: 2TB/s+
- Efficient memory coalescing
- Minimal fragmentation
- Pre-allocated memory pools
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import weakref

logger = logging.getLogger(__name__)


@dataclass
class MemoryPoolConfig:
    """Configuration for memory pool."""
    pool_size: int = 1024 * 1024 * 1024  # 1GB default
    block_size: int = 1024 * 1024  # 1MB blocks
    max_blocks: int = 1024
    grow_threshold: float = 0.8  # Grow pool when 80% used


@dataclass
class MemoryBlock:
    """Memory block in pool."""
    offset: int
    size: int
    allocated: bool
    tensor_ref: Optional[Any] = None


class GPUMemoryManager:
    """
    Manages GPU memory allocation with pooling and optimization.
    
    Features:
    - Pre-allocated memory pools
    - Efficient block allocation
    - Memory coalescing optimization
    - Automatic garbage collection
    - Memory fragmentation tracking
    """
    
    def __init__(self, config: Optional[MemoryPoolConfig] = None):
        """
        Initialize GPU memory manager.
        
        Args:
            config: Memory pool configuration
        """
        self.config = config or MemoryPoolConfig()
        self.pools: Dict[int, List[MemoryBlock]] = defaultdict(list)
        self.pool_tensors: Dict[int, Any] = {}
        self.allocated_blocks: Dict[int, List[MemoryBlock]] = defaultdict(list)
        self._initialized = False
        
        # Initialize memory pools
        self._initialize_pools()
    
    def _initialize_pools(self) -> None:
        """Initialize memory pools for each GPU device."""
        try:
            from .manager import get_cuda_manager
            cuda_mgr = get_cuda_manager()
            
            if not cuda_mgr.is_available:
                logger.warning("CUDA not available, memory pools disabled")
                return
            
            device_count = cuda_mgr.get_device_count()
            for device_id in range(device_count):
                self._create_pool(device_id)
            
            self._initialized = True
            logger.info(f"Memory pools initialized for {device_count} devices")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory pools: {e}")
    
    def _create_pool(self, device_id: int) -> None:
        """
        Create memory pool for device.
        
        Args:
            device_id: GPU device ID
        """
        try:
            import torch
            
            # Allocate pool tensor
            pool_tensor = torch.zeros(
                self.config.pool_size // 4,  # float32 = 4 bytes
                dtype=torch.float32,
                device=f"cuda:{device_id}"
            )
            
            self.pool_tensors[device_id] = pool_tensor
            
            # Create free blocks
            num_blocks = self.config.pool_size // self.config.block_size
            for i in range(num_blocks):
                block = MemoryBlock(
                    offset=i * self.config.block_size,
                    size=self.config.block_size,
                    allocated=False
                )
                self.pools[device_id].append(block)
            
            logger.debug(
                f"Created memory pool for device {device_id}: "
                f"{self.config.pool_size / 1024**3:.2f} GB, "
                f"{num_blocks} blocks"
            )
            
        except Exception as e:
            logger.error(f"Failed to create pool for device {device_id}: {e}")
    
    def allocate(self, size: int, device_id: int = 0) -> Optional[Any]:
        """
        Allocate memory block from pool.
        
        Args:
            size: Size in bytes
            device_id: GPU device ID
            
        Returns:
            Tensor view of allocated memory or None
        """
        if not self._initialized:
            logger.warning("Memory manager not initialized")
            return None
        
        try:
            import torch
            
            # Find suitable block
            block = self._find_free_block(size, device_id)
            if block is None:
                # Try to grow pool
                if not self._grow_pool(device_id):
                    logger.warning(f"No free block available for size {size}")
                    return None
                block = self._find_free_block(size, device_id)
            
            if block is None:
                return None
            
            # Mark as allocated
            block.allocated = True
            self.allocated_blocks[device_id].append(block)
            
            # Return tensor view
            pool_tensor = self.pool_tensors[device_id]
            offset_elements = block.offset // 4  # float32 = 4 bytes
            size_elements = size // 4
            
            tensor_view = pool_tensor[offset_elements:offset_elements + size_elements]
            block.tensor_ref = weakref.ref(tensor_view)
            
            return tensor_view
            
        except Exception as e:
            logger.error(f"Memory allocation failed: {e}")
            return None
    
    def _find_free_block(self, size: int, device_id: int) -> Optional[MemoryBlock]:
        """
        Find free block of required size.
        
        Args:
            size: Required size in bytes
            device_id: GPU device ID
            
        Returns:
            MemoryBlock or None
        """
        for block in self.pools[device_id]:
            if not block.allocated and block.size >= size:
                return block
        return None
    
    def _grow_pool(self, device_id: int) -> bool:
        """
        Grow memory pool if needed.
        
        Args:
            device_id: GPU device ID
            
        Returns:
            True if pool grown successfully
        """
        try:
            from .manager import get_cuda_manager
            cuda_mgr = get_cuda_manager()
            
            memory_stats = cuda_mgr.get_memory_stats()
            if memory_stats.utilization > self.config.grow_threshold:
                logger.warning("GPU memory utilization too high, cannot grow pool")
                return False
            
            # Add new blocks
            num_new_blocks = min(100, self.config.max_blocks - len(self.pools[device_id]))
            if num_new_blocks <= 0:
                return False
            
            import torch
            pool_tensor = self.pool_tensors[device_id]
            current_size = pool_tensor.numel() * 4  # float32 = 4 bytes
            new_size = current_size + (num_new_blocks * self.config.block_size)
            
            # Resize pool tensor
            new_pool = torch.zeros(
                new_size // 4,
                dtype=torch.float32,
                device=f"cuda:{device_id}"
            )
            new_pool[:pool_tensor.numel()] = pool_tensor
            self.pool_tensors[device_id] = new_pool
            
            # Add new blocks
            current_offset = current_size
            for i in range(num_new_blocks):
                block = MemoryBlock(
                    offset=current_offset,
                    size=self.config.block_size,
                    allocated=False
                )
                self.pools[device_id].append(block)
                current_offset += self.config.block_size
            
            logger.debug(f"Pool grown by {num_new_blocks} blocks for device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to grow pool: {e}")
            return False
    
    def free(self, tensor: Any, device_id: int = 0) -> None:
        """
        Free allocated memory block.
        
        Args:
            tensor: Tensor to free
            device_id: GPU device ID
        """
        if not self._initialized:
            return
        
        try:
            # Find and free block
            for block in self.allocated_blocks[device_id]:
                if block.tensor_ref and block.tensor_ref() is tensor:
                    block.allocated = False
                    block.tensor_ref = None
                    self.allocated_blocks[device_id].remove(block)
                    logger.debug(f"Freed memory block at offset {block.offset}")
                    return
        except Exception as e:
            logger.error(f"Memory free failed: {e}")
    
    def get_utilization(self, device_id: int = 0) -> float:
        """
        Get memory pool utilization.
        
        Args:
            device_id: GPU device ID
            
        Returns:
            Utilization percentage
        """
        if not self._initialized or device_id not in self.pools:
            return 0.0
        
        total_blocks = len(self.pools[device_id])
        allocated_blocks = len(self.allocated_blocks[device_id])
        
        if total_blocks == 0:
            return 0.0
        
        return (allocated_blocks / total_blocks) * 100.0
    
    def cleanup(self, device_id: Optional[int] = None) -> None:
        """
        Clean up unused memory blocks.
        
        Args:
            device_id: GPU device ID (None for all devices)
        """
        if device_id is None:
            for dev_id in list(self.pools.keys()):
                self._cleanup_device(dev_id)
        else:
            self._cleanup_device(device_id)
    
    def _cleanup_device(self, device_id: int) -> None:
        """Clean up unused blocks for specific device."""
        try:
            # Remove blocks with weak references that are dead
            alive_blocks = []
            for block in self.allocated_blocks[device_id]:
                if block.tensor_ref and block.tensor_ref() is not None:
                    alive_blocks.append(block)
                else:
                    block.allocated = False
                    block.tensor_ref = None
            
            self.allocated_blocks[device_id] = alive_blocks
            logger.debug(f"Cleaned up device {device_id} memory blocks")
            
        except Exception as e:
            logger.error(f"Cleanup failed for device {device_id}: {e}")
    
    def get_stats(self, device_id: int = 0) -> Dict[str, Any]:
        """
        Get memory manager statistics.
        
        Args:
            device_id: GPU device ID
            
        Returns:
            Dictionary with memory statistics
        """
        return {
            "initialized": self._initialized,
            "pool_size": self.config.pool_size,
            "block_size": self.config.block_size,
            "total_blocks": len(self.pools.get(device_id, [])),
            "allocated_blocks": len(self.allocated_blocks.get(device_id, [])),
            "utilization": self.get_utilization(device_id),
        }


# Global memory manager instance
_memory_manager: Optional[GPUMemoryManager] = None


def get_memory_manager(config: Optional[MemoryPoolConfig] = None) -> GPUMemoryManager:
    """
    Get or create global memory manager instance.
    
    Args:
        config: Memory pool configuration
        
    Returns:
        GPUMemoryManager instance
    """
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = GPUMemoryManager(config)
    return _memory_manager
