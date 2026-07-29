"""CUDA device manager for GPU detection and initialization.

Handles GPU device discovery, capability checking, and device context management.
Compatible with V5 specifications for NVIDIA A100, H100, and V100.
"""

import logging
from typing import Dict, List, Optional, Tuple

from .config import GPUConfig, GPUModel, GPUSpecs

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages CUDA device discovery and context.

    This class provides a unified interface for GPU device management,
    with graceful fallback to CPU when GPU is unavailable.
    """

    def __init__(self, config: Optional[GPUConfig] = None):
        """Initialize device manager.

        Args:
            config: GPU configuration. If None, uses default config.
        """
        self.config = config or GPUConfig()
        self._cuda_available = False
        self._device_count = 0
        self._device_specs: Dict[int, GPUSpecs] = {}
        self._current_device: Optional[int] = None

        # Try to import CUDA libraries
        self._torch = None
        self._cupy = None
        self._cuda_version = None

        self._initialize()

    def _initialize(self) -> None:
        """Initialize CUDA runtime and detect devices."""
        try:
            import torch

            self._torch = torch
            self._cuda_available = torch.cuda.is_available()

            if self._cuda_available:
                self._device_count = torch.cuda.device_count()
                self._cuda_version = torch.version.cuda
                self._detect_devices()
                logger.info(
                    f"CUDA available: {self._device_count} devices, "
                    f"CUDA {self._cuda_version}, PyTorch {torch.__version__}"
                )
            else:
                logger.warning("CUDA not available, will use CPU fallback")
        except ImportError:
            logger.warning("PyTorch not available, GPU acceleration disabled")
            self._cuda_available = False

        # Update config
        self.config.device_count = self._device_count
        if self._device_count > 0:
            self.config.primary_device_id = 0
            self.config.device_specs = self._device_specs.get(0)

    def _detect_devices(self) -> None:
        """Detect and catalog all available GPU devices."""
        if not self._torch or not self._cuda_available:
            return

        for device_id in range(self._device_count):
            try:
                props = self._torch.cuda.get_device_properties(device_id)
                name = props.name
                total_memory = props.total_memory / (1024**3)  # Convert to GB
                compute_capability = (props.major, props.minor)
                multi_processor_count = props.multi_processor_count

                # Map to known GPU models
                specs = self._identify_gpu(name, total_memory, compute_capability)
                self._device_specs[device_id] = specs

                logger.info(
                    f"Device {device_id}: {name}, {total_memory:.1f}GB, "
                    f"Compute {compute_capability[0]}.{compute_capability[1]}, "
                    f"{multi_processor_count} SMs"
                )
            except Exception as e:
                logger.error(f"Error detecting device {device_id}: {e}")

    def _identify_gpu(
        self, name: str, memory_gb: float, compute_capability: Tuple[int, int]
    ) -> GPUSpecs:
        """Identify GPU model from device properties.

        Args:
            name: GPU device name
            memory_gb: Total memory in GB
            compute_capability: (major, minor) compute capability

        Returns:
            GPUSpecs for the detected device
        """
        name_upper = name.upper()

        if "H100" in name_upper or compute_capability == (9, 0):
            return GPUSpecs.h100()
        elif "A100" in name_upper or (compute_capability == (8, 0) and memory_gb > 70):
            return GPUSpecs.a100()
        elif "V100" in name_upper or compute_capability == (7, 0):
            return GPUSpecs.v100()
        elif "4090" in name_upper:
            # RTX 4090 for development
            return GPUSpecs(
                model=GPUModel.RTX_4090,
                memory_gb=24.0,
                memory_bandwidth_tbps=1.0,
                tensor_cores_tflops=330.0,
                cuda_cores=16384,
                compute_capability=(8, 9),
            )
        else:
            # Unknown GPU - create generic specs
            return GPUSpecs(
                model=GPUModel.UNKNOWN,
                memory_gb=memory_gb,
                memory_bandwidth_tbps=0.5,
                tensor_cores_tflops=100.0,
                cuda_cores=multi_processor_count * 64 if compute_capability else 1000,
                compute_capability=compute_capability,
            )

    @property
    def is_available(self) -> bool:
        """Check if CUDA is available."""
        return self._cuda_available

    @property
    def device_count(self) -> int:
        """Get number of available GPU devices."""
        return self._device_count

    def get_device_specs(self, device_id: int = 0) -> Optional[GPUSpecs]:
        """Get specifications for a specific device.

        Args:
            device_id: GPU device ID

        Returns:
            GPUSpecs if device exists, None otherwise
        """
        return self._device_specs.get(device_id)

    def get_device_memory(self, device_id: int = 0) -> Optional[Tuple[float, float]]:
        """Get device memory information (total, free) in GB.

        Args:
            device_id: GPU device ID

        Returns:
            Tuple of (total_gb, free_gb) or None if unavailable
        """
        if not self._torch or not self._cuda_available:
            return None

        try:
            total = self._torch.cuda.get_device_properties(device_id).total_memory / (
                1024**3
            )
            free = self._torch.cuda.memory_allocated(device_id) / (1024**3)
            return total, (total - free)
        except Exception as e:
            logger.error(f"Error getting memory info for device {device_id}: {e}")
            return None

    def set_device(self, device_id: int = 0) -> bool:
        """Set the current CUDA device.

        Args:
            device_id: GPU device ID

        Returns:
            True if successful, False otherwise
        """
        if not self._torch or not self._cuda_available:
            return False

        if device_id >= self._device_count:
            logger.error(f"Invalid device ID: {device_id}")
            return False

        try:
            self._torch.cuda.set_device(device_id)
            self._current_device = device_id
            logger.debug(f"Set current device to {device_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting device {device_id}: {e}")
            return False

    def get_current_device(self) -> Optional[int]:
        """Get the current CUDA device ID."""
        if not self._torch or not self._cuda_available:
            return None
        return self._current_device or self._torch.cuda.current_device()

    def synchronize(self) -> None:
        """Synchronize CUDA operations."""
        if self._torch and self._cuda_available:
            self._torch.cuda.synchronize()

    def empty_cache(self) -> None:
        """Empty CUDA cache to free memory."""
        if self._torch and self._cuda_available:
            self._torch.cuda.empty_cache()
            logger.debug("CUDA cache emptied")

    def get_memory_summary(self) -> Dict[str, any]:
        """Get detailed memory usage summary.

        Returns:
            Dictionary with memory statistics
        """
        if not self._torch or not self._cuda_available:
            return {"available": False, "devices": []}

        summary = {"available": True, "devices": []}
        for device_id in range(self._device_count):
            try:
                total = self._torch.cuda.get_device_properties(device_id).total_memory
                allocated = self._torch.cuda.memory_allocated(device_id)
                reserved = self._torch.cuda.memory_reserved(device_id)
                free = total - allocated

                summary["devices"].append(
                    {
                        "device_id": device_id,
                        "total_gb": total / (1024**3),
                        "allocated_gb": allocated / (1024**3),
                        "reserved_gb": reserved / (1024**3),
                        "free_gb": free / (1024**3),
                        "utilization_pct": (allocated / total) * 100 if total > 0 else 0,
                    }
                )
            except Exception as e:
                logger.error(f"Error getting memory summary for device {device_id}: {e}")

        return summary

    def __repr__(self) -> str:
        return (
            f"DeviceManager(available={self.is_available}, "
            f"devices={self.device_count}, "
            f"primary={self.config.primary_device_id})"
        )
