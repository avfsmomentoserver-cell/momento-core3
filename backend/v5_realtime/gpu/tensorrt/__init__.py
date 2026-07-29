"""
TensorRT Optimization Module

Handles model optimization for low-latency inference using TensorRT:
- Model conversion and optimization
- FP16/INT8 quantization
- Layer fusion
- Dynamic batching
- Calibration

Performance Targets:
- <1ms inference latency
- 1000+ inferences/second
- <2GB memory per model
- <1% accuracy degradation
"""

from .optimizer import TensorRTOptimizer
from .calibrator import TensorRTCalibrator
from .builder import TensorRTBuilder

__all__ = [
    "TensorRTOptimizer",
    "TensorRTCalibrator",
    "TensorRTBuilder"
]
