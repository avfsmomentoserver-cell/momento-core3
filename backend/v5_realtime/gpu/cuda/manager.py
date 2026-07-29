"""
CUDA Manager - GPU Device and Context Management

Handles GPU device initialization, context management, and resource allocation
for high-performance ML inference.

Performance Requirements:
- Support NVIDIA A100/H100/V100 GPUs
- Memory bandwidth: 2TB/s+
- Tensor cores: 600+ TFLOPS
- CUDA cores: 20000+
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class GPUArchitecture(Enum):
    """Supported GPU architectures."""
    AMPERE = "ampere"  # A100, RTX 30 series
    HOPPER = "hopper"  # H100
    VOLTA = "volta"    # V100
    TURING = "turing"  # RTX 20 series


@dataclass
class GPUDeviceInfo:
    """GPU device information."""
    device_id: int
    name: str
    architecture: GPUArchitecture
    total_memory: int  # bytes
    compute_capability: Tuple[int, int]
    tensor_cores: bool
    multi_processor_count: int
    max_threads_per_block: int
    max_shared_memory_per_block: int
    warp_size: int


@dataclass
class CUDAMemoryStats:
    """CUDA memory statistics."""
    total: int  # bytes
    free: int   # bytes
    used: int   # bytes
    utilization: float  # percentage


class CUDAManager:
    """
    Manages GPU devices, contexts, and memory allocation.
    
    Provides:
    - Device initialization and selection
    - Memory pool management
    - Context switching
    - Performance monitoring
    """
    
    def __init__(self, device_id: int = 0):
        """
        Initialize CUDA manager.
        
        Args:
            device_id: GPU device ID to use (default: 0)
        """
        self.device_id = device_id
        self.device_info: Optional[GPUDeviceInfo] = None
        self._cuda_available = False
        self._initialized = False
        
        # Initialize CUDA
        self._initialize_cuda()
    
    def _initialize_cuda(self) -> None:
        """Initialize CUDA and detect GPU capabilities."""
        try:
            import torch
            if not torch.cuda.is_available():
                logger.warning("CUDA is not available. Using CPU fallback.")
                self._cuda_available = False
                return
            
            self._cuda_available = True
            torch.cuda.set_device(self.device_id)
            
            # Get device properties
            props = torch.cuda.get_device_properties(self.device_id)
            self.device_info = self._parse_device_info(props)
            
            logger.info(
                f"CUDA initialized: {self.device_info.name} "
                f"({self.device_info.total_memory / 1024**3:.1f} GB)"
            )
            
            self._initialized = True
            
        except ImportError:
            logger.warning("PyTorch not available. CUDA features disabled.")
            self._cuda_available = False
        except Exception as e:
            logger.error(f"CUDA initialization failed: {e}")
            self._cuda_available = False
    
    def _parse_device_info(self, props: Any) -> GPUDeviceInfo:
        """Parse PyTorch device properties into GPUDeviceInfo."""
        # Determine architecture based on compute capability
        major, minor = props.major, props.minor
        if major >= 9:
            arch = GPUArchitecture.HOPPER
        elif major >= 8:
            arch = GPUArchitecture.AMPERE
        elif major >= 7:
            arch = GPUArchitecture.VOLTA
        else:
            arch = GPUArchitecture.TURING
        
        return GPUDeviceInfo(
            device_id=self.device_id,
            name=props.name,
            architecture=arch,
            total_memory=props.total_memory,
            compute_capability=(major, minor),
            tensor_cores=major >= 7,  # Tensor cores available on Volta+
            multi_processor_count=props.multi_processor_count,
            max_threads_per_block=props.max_threads_per_block,
            max_shared_memory_per_block=props.max_shared_memory_per_block,
            warp_size=props.warp_size,
        )
    
    @property
    def is_available(self) -> bool:
        """Check if CUDA is available."""
        return self._cuda_available
    
    @property
    def is_initialized(self) -> bool:
        """Check if CUDA manager is initialized."""
        return self._initialized
    
    def get_memory_stats(self) -> CUDAMemoryStats:
        """
        Get current GPU memory statistics.
        
        Returns:
            CUDAMemoryStats with memory information
        """
        if not self._cuda_available:
            return CUDAMemoryStats(0, 0, 0, 0.0)
        
        try:
            import torch
            total = torch.cuda.get_device_properties(self.device_id).total_memory
            allocated = torch.cuda.memory_allocated(self.device_id)
            reserved = torch.cuda.memory_reserved(self.device_id)
            free = total - reserved
            
            return CUDAMemoryStats(
                total=total,
                free=free,
                used=allocated,
                utilization=(allocated / total) * 100.0
            )
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return CUDAMemoryStats(0, 0, 0, 0.0)
    
    def set_device(self, device_id: int) -> None:
        """
        Set active GPU device.
        
        Args:
            device_id: GPU device ID
        """
        if not self._cuda_available:
            logger.warning("CUDA not available, cannot set device")
            return
        
        try:
            import torch
            self.device_id = device_id
            torch.cuda.set_device(device_id)
            logger.info(f"Switched to GPU device {device_id}")
        except Exception as e:
            logger.error(f"Failed to set device: {e}")
    
    def get_device_count(self) -> int:
        """Get number of available GPU devices."""
        if not self._cuda_available:
            return 0
        
        try:
            import torch
            return torch.cuda.device_count()
        except Exception as e:
            logger.error(f"Failed to get device count: {e}")
            return 0
    
    def synchronize(self) -> None:
        """Synchronize CUDA operations."""
        if not self._cuda_available:
            return
        
        try:
            import torch
            torch.cuda.synchronize()
        except Exception as e:
            logger.error(f"Failed to synchronize: {e}")
    
    def empty_cache(self) -> None:
        """Empty CUDA cache to free unused memory."""
        if not self._cuda_available:
            return
        
        try:
            import torch
            torch.cuda.empty_cache()
            logger.debug("CUDA cache emptied")
        except Exception as e:
            logger.error(f"Failed to empty cache: {e}")
    
    def get_device_info(self) -> Optional[GPUDeviceInfo]:
        """Get current device information."""
        return self.device_info
    
    def list_devices(self) -> List[GPUDeviceInfo]:
        """
        List all available GPU devices.
        
        Returns:
            List of GPUDeviceInfo for all devices
        """
        if not self._cuda_available:
            return []
        
        try:
            import torch
            devices = []
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                devices.append(self._parse_device_info(props))
            return devices
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []
    
    def enable_mixed_precision(self) -> bool:
        """
        Enable mixed precision (FP16) for tensor core acceleration.
        
        Returns:
            True if mixed precision enabled successfully
        """
        if not self._cuda_available or not self.device_info:
            return False
        
        # Check if device supports tensor cores
        if not self.device_info.tensor_cores:
            logger.warning("Device does not support tensor cores")
            return False
        
        logger.info("Mixed precision (FP16) enabled for tensor core acceleration")
        return True
    
    def get_compute_capability(self) -> Tuple[int, int]:
        """Get compute capability of current device."""
        if self.device_info:
            return self.device_info.compute_capability
        return (0, 0)
    
    def is_tensor_core_supported(self) -> bool:
        """Check if current device supports tensor cores."""
        if self.device_info:
            return self.device_info.tensor_cores
        return False


# Global CUDA manager instance
_cuda_manager: Optional[CUDAManager] = None


def get_cuda_manager(device_id: int = 0) -> CUDAManager:
    """
    Get or create global CUDA manager instance.
    
    Args:
        device_id: GPU device ID to use
        
    Returns:
        CUDAManager instance
    """
    global _cuda_manager
    if _cuda_manager is None:
        _cuda_manager = CUDAManager(device_id)
    return _cuda_manager
