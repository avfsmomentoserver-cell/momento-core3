"""
CPU-Based Intelligence Configuration for V5 Free-Tier
Optimized for CPU inference without GPU acceleration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class CPUMLConfig:
    """Configuration for CPU-based ML inference."""
    
    # Model optimization
    enable_onnx: bool = True
    enable_quantization: bool = True
    quantization_mode: str = "int8"  # int8, fp16
    enable_pruning: bool = True
    pruning_threshold: float = 0.3
    
    # Inference optimization
    batch_size: int = 32
    max_batch_size: int = 128
    enable_batching: bool = True
    batching_timeout_ms: int = 50
    
    # Memory optimization
    max_memory_mb: int = 1024
    enable_memory_pooling: bool = True
    cache_size_mb: int = 256
    
    # Thread optimization
    num_threads: int = 4
    enable_threading: bool = True
    thread_affinity: bool = False
    
    # Performance targets
    target_latency_ms: int = 50  # Relaxed from 1ms (GPU)
    target_throughput: int = 100  # Reduced from 1000 (GPU)
    target_accuracy: float = 0.90  # Slightly reduced from 0.95
    
    # Model selection
    preferred_framework: str = "onnx"  # onnx, sklearn, tensorflow
    fallback_framework: str = "sklearn"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enable_onnx": self.enable_onnx,
            "enable_quantization": self.enable_quantization,
            "quantization_mode": self.quantization_mode,
            "enable_pruning": self.enable_pruning,
            "pruning_threshold": self.pruning_threshold,
            "batch_size": self.batch_size,
            "max_batch_size": self.max_batch_size,
            "enable_batching": self.enable_batching,
            "batching_timeout_ms": self.batching_timeout_ms,
            "max_memory_mb": self.max_memory_mb,
            "enable_memory_pooling": self.enable_memory_pooling,
            "cache_size_mb": self.cache_size_mb,
            "num_threads": self.num_threads,
            "enable_threading": self.enable_threading,
            "thread_affinity": self.thread_affinity,
            "target_latency_ms": self.target_latency_ms,
            "target_throughput": self.target_throughput,
            "target_accuracy": self.target_accuracy,
            "preferred_framework": self.preferred_framework,
            "fallback_framework": self.fallback_framework,
        }


@dataclass
class ModelOptimizationConfig:
    """Configuration for model optimization."""
    
    # ONNX optimization
    enable_onnx_optimization: bool = True
    onnx_optimization_level: int = 2  # 0-3, higher = more optimization
    
    # Quantization
    enable_dynamic_quantization: bool = True
    enable_static_quantization: bool = False
    calibration_dataset_size: int = 100
    
    # Pruning
    pruning_method: str = "magnitude"  # magnitude, gradient
    pruning_schedule: str = "gradual"  # gradual, one_shot
    
    # Distillation
    enable_distillation: bool = False
    distillation_temperature: float = 3.0
    distillation_alpha: float = 0.5
    
    # Compression
    enable_compression: bool = True
    compression_level: int = 6  # 0-9, higher = more compression


# Default configuration
DEFAULT_CPU_CONFIG = CPUMLConfig()
DEFAULT_OPTIMIZATION_CONFIG = ModelOptimizationConfig()