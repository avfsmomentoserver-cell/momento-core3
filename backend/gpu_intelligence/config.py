"""GPU configuration and hardware specifications.

Defines GPU hardware specs, optimization settings, and runtime configuration
for CUDA and TensorRT operations as per V5 specifications.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class PrecisionMode(Enum):
    """Precision modes for GPU inference."""
    FP32 = "fp32"  # Full precision (32-bit float)
    FP16 = "fp16"  # Half precision (16-bit float) - recommended for A100/H100
    INT8 = "int8"  # 8-bit integer quantization - fastest but may impact accuracy
    MIXED = "mixed"  # Mixed precision (FP16 compute, FP32 storage)


class GPUModel(Enum):
    """Supported GPU models per V5 specifications."""
    A100_80GB = "A100-80GB"
    H100_80GB = "H100-80GB"
    V100_32GB = "V100-32GB"
    RTX_4090 = "RTX-4090"  # For development/testing
    UNKNOWN = "UNKNOWN"


@dataclass
class GPUSpecs:
    """Hardware specifications for a GPU."""
    model: GPUModel
    memory_gb: float
    memory_bandwidth_tbps: float
    tensor_cores_tflops: float
    cuda_cores: int
    compute_capability: Tuple[int, int]

    # V5 reference specs
    @classmethod
    def a100(cls) -> "GPUSpecs":
        return cls(
            model=GPUModel.A100_80GB,
            memory_gb=80.0,
            memory_bandwidth_tbps=2.0,
            tensor_cores_tflops=600.0,
            cuda_cores=6912,
            compute_capability=(8, 0),
        )

    @classmethod
    def h100(cls) -> "GPUSpecs":
        return cls(
            model=GPUModel.H100_80GB,
            memory_gb=80.0,
            memory_bandwidth_tbps=3.35,
            tensor_cores_tflops=2000.0,
            cuda_cores=16896,
            compute_capability=(9, 0),
        )

    @classmethod
    def v100(cls) -> "GPUSpecs":
        return cls(
            model=GPUModel.V100_32GB,
            memory_gb=32.0,
            memory_bandwidth_tbps=0.9,
            tensor_cores_tflops=125.0,
            cuda_cores=5120,
            compute_capability=(7, 0),
        )


@dataclass
class TensorRTConfig:
    """TensorRT optimization configuration per V5 specs."""
    version: str = "8.6+"
    precision: PrecisionMode = PrecisionMode.FP16
    enable_layer_fusion: bool = True
    enable_dynamic_batching: bool = True
    enable_kernel_autotuning: bool = True
    max_workspace_size: int = 2_147_483_648  # 2GB default
    min_batch_size: int = 1
    max_batch_size: int = 128
    opt_batch_size: int = 32

    # Performance targets per V5 specs
    target_latency_ms: float = 1.0
    target_throughput_ips: int = 1000  # inferences per second
    max_memory_gb: float = 2.0
    max_accuracy_degradation_pct: float = 1.0


@dataclass
class CUDAConfig:
    """CUDA runtime configuration per V5 specs."""
    version: str = "12.2+"
    enable_mixed_precision: bool = True
    enable_tensor_cores: bool = True
    enable_memory_coalescing: bool = True
    enable_kernel_fusion: bool = True

    # Stream and block configuration
    num_streams: int = 4
    default_block_size: int = 256
    default_grid_size: int = 0  # 0 = auto-calculate

    # Memory configuration
    memory_fraction: float = 0.9  # Use 90% of GPU memory
    enable_cached_allocator: bool = True


@dataclass
class BatchConfig:
    """Batch processing configuration."""
    enabled: bool = True
    dynamic_batching: bool = True
    min_batch_size: int = 1
    max_batch_size: int = 128
    opt_batch_size: int = 32
    batch_timeout_ms: int = 5  # Wait up to 5ms for batch accumulation
    enable_padding: bool = True
    padding_strategy: str = "constant"  # constant, edge, reflect


@dataclass
class GPUConfig:
    """Complete GPU intelligence configuration."""

    # Hardware specs (detected at runtime)
    device_specs: Optional[GPUSpecs] = None
    device_count: int = 0
    primary_device_id: int = 0

    # Subsystem configurations
    cuda: CUDAConfig = field(default_factory=CUDAConfig)
    tensorrt: TensorRTConfig = field(default_factory=TensorRTConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)

    # Feature extraction settings
    enable_feature_extraction: bool = True
    feature_extraction_batch_size: int = 64
    enable_async_feature_extraction: bool = True

    # Monitoring and profiling
    enable_profiling: bool = False
    profiling_memory_mb: int = 100
    log_level: str = "INFO"

    # Fallback to CPU if GPU unavailable
    enable_cpu_fallback: bool = True
    cpu_threads: int = 4

    def is_available(self) -> bool:
        """Check if GPU is available."""
        return self.device_count > 0

    def get_primary_device(self) -> Optional[int]:
        """Get primary GPU device ID."""
        return self.primary_device_id if self.is_available() else None

    def should_use_mixed_precision(self) -> bool:
        """Determine if mixed precision should be used."""
        return (
            self.cuda.enable_mixed_precision
            and self.tensorrt.precision in (PrecisionMode.FP16, PrecisionMode.MIXED)
        )


# Default configuration instance
default_config = GPUConfig()
