"""
V5 GPU Intelligence System

Phase 2 Implementation: GPU-accelerated ML inference with CUDA and TensorRT optimization.

Target Performance:
- <1ms ML inference latency
- 1000+ inferences/second
- <1% accuracy degradation
- Efficient GPU utilization
- Scalable batch processing

Architecture:
- CUDA-based processing modules
- TensorRT model optimization
- GPU inference pipeline
- Model quantization (FP16/INT8)
- Batch processing optimization
- Performance monitoring
"""

__version__ = "5.0.0"
__author__ = "V5 GPU Intelligence Team"

from .cuda.manager import CUDAManager
from .tensorrt.optimizer import TensorRTOptimizer
from .inference.pipeline import GPUInferencePipeline
from .quantization.quantizer import ModelQuantizer
from .batch.processor import BatchProcessor
from .monitoring.metrics import GPUMetrics

__all__ = [
    "CUDAManager",
    "TensorRTOptimizer", 
    "GPUInferencePipeline",
    "ModelQuantizer",
    "BatchProcessor",
    "GPUMetrics",
]
