"""
CUDA Management Module

Handles GPU device initialization, memory management, and CUDA operations
for high-performance ML inference.

Performance Targets:
- Memory bandwidth: 2TB/s+
- Tensor cores: 600+ TFLOPS
- Mixed precision (FP16) support
- Memory coalescing optimization
"""

from .manager import CUDAManager, get_cuda_manager
from .memory import GPUMemoryManager
from .kernels import CUDAKernels, get_cuda_kernels

__all__ = [
    "CUDAManager",
    "get_cuda_manager",
    "GPUMemoryManager",
    "CUDAKernels",
    "get_cuda_kernels"
]
