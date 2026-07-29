"""GPU Intelligence Module for Momento Core V5.

This module provides GPU-accelerated AI processing capabilities including:
- CUDA device management and memory pooling
- TensorRT model optimization and inference
- GPU-accelerated batch processing
- GPU feature extraction pipelines
"""

from .config import GPUConfig
from .device_manager import DeviceManager
from .memory_pool import GPUMemoryPool
from .tensorrt_engine import TensorRTEngine
from .batch_processor import GPUBatchProcessor
from .feature_extractor import GPUFeatureExtractor
from .integration import (
    initialize_gpu_intelligence,
    is_gpu_available,
    get_device_manager,
    get_feature_extractor,
    get_batch_processor,
    get_gpu_status,
    shutdown_gpu_intelligence,
)

__all__ = [
    "GPUConfig",
    "DeviceManager",
    "GPUMemoryPool",
    "TensorRTEngine",
    "GPUBatchProcessor",
    "GPUFeatureExtractor",
    "initialize_gpu_intelligence",
    "is_gpu_available",
    "get_device_manager",
    "get_feature_extractor",
    "get_batch_processor",
    "get_gpu_status",
    "shutdown_gpu_intelligence",
]

# Version info
__version__ = "1.0.0"
