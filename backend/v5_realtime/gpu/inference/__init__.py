"""
GPU Inference Pipeline

High-performance inference pipeline using GPU acceleration:
- TensorRT engine loading
- Batch inference
- Dynamic batching
- Async inference
- Performance monitoring

Performance Targets:
- <1ms inference latency
- 1000+ inferences/second
- Efficient GPU utilization
"""

from .pipeline import GPUInferencePipeline

__all__ = ["GPUInferencePipeline"]
