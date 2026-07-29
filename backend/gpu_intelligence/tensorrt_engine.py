"""TensorRT model optimizer and inference engine.

Provides optimized model inference using TensorRT for low-latency, high-throughput
AI workloads. Supports FP16/INT8 quantization, layer fusion, and dynamic batching
per V5 specifications.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .config import GPUConfig, PrecisionMode, TensorRTConfig
from .device_manager import DeviceManager
from .memory_pool import GPUMemoryPool

logger = logging.getLogger(__name__)


class ModelFormat(Enum):
    """Supported model formats."""
    PYTORCH = "pytorch"
    ONNX = "onnx"
    TENSORFLOW = "tensorflow"
    TENSORRT = "tensorrt"


@dataclass
class InferenceResult:
    """Result from model inference."""
    predictions: Any
    latency_ms: float
    batch_size: int
    device_id: int
    memory_used_mb: float
    success: bool
    error: Optional[str] = None


@dataclass
class EngineMetrics:
    """TensorRT engine performance metrics."""
    total_inferences: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    throughput_ips: float = 0.0  # inferences per second
    memory_peak_mb: float = 0.0


class TensorRTEngine:
    """TensorRT inference engine with optimization and batching.

    This class provides a unified interface for model optimization and inference
    using TensorRT, with fallback to PyTorch when TensorRT is unavailable.
    """

    def __init__(
        self,
        device_manager: DeviceManager,
        memory_pool: GPUMemoryPool,
        config: Optional[GPUConfig] = None,
    ):
        """Initialize TensorRT engine.

        Args:
            device_manager: Device manager instance
            memory_pool: Memory pool instance
            config: GPU configuration
        """
        self.device_manager = device_manager
        self.memory_pool = memory_pool
        self.config = config or GPUConfig()
        self.trt_config = self.config.tensorrt

        # Engine state
        self._engine = None
        self._context = None
        self._model_loaded = False
        self._model_path: Optional[Path] = None
        self._input_shapes: Dict[str, Tuple[int, ...]] = {}
        self._output_shapes: Dict[str, Tuple[int, ...]] = {}

        # PyTorch fallback
        self._torch_model = None
        self._use_tensorrt = False

        # Metrics
        self._metrics = EngineMetrics()
        self._start_time = time.time()

        # Try to initialize TensorRT
        self._initialize_tensorrt()

    def _initialize_tensorrt(self) -> None:
        """Initialize TensorRT runtime."""
        try:
            import tensorrt as trt

            self._trt = trt
            self._trt_logger = trt.Logger(trt.Logger.INFO)
            self._use_tensorrt = True
            logger.info(f"TensorRT initialized: {trt.__version__}")
        except ImportError:
            logger.warning("TensorRT not available, will use PyTorch fallback")
            self._use_tensorrt = False
        except Exception as e:
            logger.error(f"Error initializing TensorRT: {e}")
            self._use_tensorrt = False

    def load_model(
        self,
        model_path: Union[str, Path],
        model_format: ModelFormat = ModelFormat.PYTORCH,
        optimize: bool = True,
    ) -> bool:
        """Load and optionally optimize a model.

        Args:
            model_path: Path to model file
            model_format: Model format
            optimize: Whether to optimize with TensorRT

        Returns:
            True if successful, False otherwise
        """
        model_path = Path(model_path)
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return False

        self._model_path = model_path

        if self._use_tensorrt and optimize:
            # Try to load optimized TensorRT engine
            trt_path = model_path.with_suffix(".trt")
            if trt_path.exists():
                return self._load_tensorrt_engine(trt_path)
            else:
                # Build TensorRT engine from source model
                return self._build_tensorrt_engine(model_path, model_format)
        else:
            # Use PyTorch fallback
            return self._load_pytorch_model(model_path)

    def _load_tensorrt_engine(self, engine_path: Path) -> bool:
        """Load a pre-built TensorRT engine.

        Args:
            engine_path: Path to TensorRT engine file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(engine_path, "rb") as f:
                engine_data = f.read()

            self._engine = self._trt.Runtime(self._trt_logger).deserialize_cuda_engine(
                engine_data
            )
            self._context = self._engine.create_execution_context()
            self._model_loaded = True

            # Get I/O shapes
            for i in range(self._engine.num_io_tensors):
                name = self._engine.get_tensor_name(i)
                shape = self._engine.get_tensor_shape(name)
                mode = self._engine.get_tensor_mode(name)

                if mode == self._trt.TensorIOMode.INPUT:
                    self._input_shapes[name] = tuple(shape)
                else:
                    self._output_shapes[name] = tuple(shape)

            logger.info(f"Loaded TensorRT engine from {engine_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading TensorRT engine: {e}")
            return False

    def _build_tensorrt_engine(
        self, model_path: Path, model_format: ModelFormat
    ) -> bool:
        """Build TensorRT engine from source model.

        Args:
            model_path: Path to source model
            model_format: Source model format

        Returns:
            True if successful, False otherwise
        """
        try:
            if model_format == ModelFormat.PYTORCH:
                return self._build_from_pytorch(model_path)
            elif model_format == ModelFormat.ONNX:
                return self._build_from_onnx(model_path)
            else:
                logger.error(f"Unsupported model format: {model_format}")
                return False
        except Exception as e:
            logger.error(f"Error building TensorRT engine: {e}")
            # Fall back to PyTorch
            return self._load_pytorch_model(model_path)

    def _build_from_pytorch(self, model_path: Path) -> bool:
        """Build TensorRT engine from PyTorch model.

        Args:
            model_path: Path to PyTorch model

        Returns:
            True if successful, False otherwise
        """
        try:
            import torch
            from torch2trt import TRTModule

            # Load PyTorch model
            self._torch_model = torch.load(model_path)
            self._torch_model.eval()

            # Create dummy input for shape inference
            # This is a simplified version - in production, you'd need
            # to know the actual input shapes
            dummy_input = torch.randn(1, 32).cuda()

            # Convert to TensorRT
            self._engine = TRTModule()
            self._engine = torch2trt(self._torch_model, [dummy_input])

            self._model_loaded = True
            logger.info("Built TensorRT engine from PyTorch model")
            return True
        except ImportError:
            logger.warning("torch2trt not available, using PyTorch fallback")
            return self._load_pytorch_model(model_path)
        except Exception as e:
            logger.error(f"Error converting PyTorch to TensorRT: {e}")
            return self._load_pytorch_model(model_path)

    def _build_from_onnx(self, model_path: Path) -> bool:
        """Build TensorRT engine from ONNX model.

        Args:
            model_path: Path to ONNX model

        Returns:
            True if successful, False otherwise
        """
        try:
            import tensorrt as trt

            builder = trt.Builder(self._trt_logger)
            network = builder.create_network(
                1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
            )
            parser = trt.OnnxParser(network, self._trt_logger)

            # Parse ONNX model
            with open(model_path, "rb") as f:
                if not parser.parse(f.read()):
                    logger.error("Failed to parse ONNX model")
                    for error in range(parser.num_errors):
                        logger.error(parser.get_error(error))
                    return False

            # Build config
            config = builder.create_builder_config()
            config.max_workspace_size = self.trt_config.max_workspace_size

            # Set precision
            if self.trt_config.precision == PrecisionMode.FP16:
                config.set_flag(trt.BuilderFlag.FP16)
            elif self.trt_config.precision == PrecisionMode.INT8:
                config.set_flag(trt.BuilderFlag.INT8)
                # INT8 requires calibration - skipped in this simplified version

            # Build engine
            self._engine = builder.build_engine(network, config)
            self._context = self._engine.create_execution_context()
            self._model_loaded = True

            logger.info("Built TensorRT engine from ONNX model")
            return True
        except Exception as e:
            logger.error(f"Error building from ONNX: {e}")
            return False

    def _load_pytorch_model(self, model_path: Path) -> bool:
        """Load PyTorch model as fallback.

        Args:
            model_path: Path to PyTorch model

        Returns:
            True if successful, False otherwise
        """
        try:
            import torch

            self._torch_model = torch.load(model_path)
            self._torch_model.eval()

            if self.device_manager.is_available:
                self._torch_model = self._torch_model.cuda()

            self._model_loaded = True
            logger.info(f"Loaded PyTorch model from {model_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading PyTorch model: {e}")
            return False

    def infer(
        self,
        inputs: Dict[str, Any],
        batch_size: Optional[int] = None,
    ) -> InferenceResult:
        """Run inference on input data.

        Args:
            inputs: Input tensors (name -> tensor)
            batch_size: Override batch size (for dynamic batching)

        Returns:
            InferenceResult with predictions and metrics
        """
        if not self._model_loaded:
            return InferenceResult(
                predictions=None,
                latency_ms=0.0,
                batch_size=0,
                device_id=-1,
                memory_used_mb=0.0,
                success=False,
                error="Model not loaded",
            )

        start_time = time.time()
        device_id = self.device_manager.get_current_device() or 0

        try:
            if self._use_tensorrt and self._engine is not None:
                result = self._infer_tensorrt(inputs, batch_size)
            else:
                result = self._infer_pytorch(inputs, batch_size)

            latency_ms = (time.time() - start_time) * 1000
            self._update_metrics(latency_ms, result.batch_size)

            return InferenceResult(
                predictions=result.predictions,
                latency_ms=latency_ms,
                batch_size=result.batch_size,
                device_id=device_id,
                memory_used_mb=result.memory_used_mb,
                success=True,
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Inference error: {e}")
            return InferenceResult(
                predictions=None,
                latency_ms=latency_ms,
                batch_size=0,
                device_id=device_id,
                memory_used_mb=0.0,
                success=False,
                error=str(e),
            )

    def _infer_tensorrt(
        self, inputs: Dict[str, Any], batch_size: Optional[int]
    ) -> InferenceResult:
        """Run inference with TensorRT engine.

        Args:
            inputs: Input tensors
            batch_size: Batch size

        Returns:
            InferenceResult
        """
        import torch

        # Prepare inputs
        input_tensors = {}
        for name, value in inputs.items():
            if isinstance(value, torch.Tensor):
                tensor = value.cuda()
            else:
                tensor = torch.tensor(value).cuda()
            input_tensors[name] = tensor

        # Set dynamic batch size if specified
        if batch_size is not None:
            for name in self._input_shapes:
                self._context.set_input_shape(name, (batch_size,) + self._input_shapes[name][1:])

        # Execute
        output_tensors = {}
        for name in self._output_shapes:
            output_tensors[name] = torch.empty(
                self._context.get_tensor_shape(name), device="cuda"
            )

        # Bind buffers and execute
        for name, tensor in input_tensors.items():
            self._context.set_tensor_address(name, tensor.data_ptr())
        for name, tensor in output_tensors.items():
            self._context.set_tensor_address(name, tensor.data_ptr())

        self._context.execute_async_v3(0)
        self.device_manager.synchronize()

        # Get memory usage
        mem_info = self.device_manager.get_device_memory()
        memory_used = mem_info[1] if mem_info else 0.0  # Free memory
        memory_used_mb = (mem_info[0] - memory_used) * 1024 if mem_info else 0.0

        return InferenceResult(
            predictions={k: v.cpu() for k, v in output_tensors.items()},
            latency_ms=0.0,  # Set by caller
            batch_size=batch_size or next(iter(input_tensors.values())).shape[0],
            device_id=self.device_manager.get_current_device() or 0,
            memory_used_mb=memory_used_mb,
            success=True,
        )

    def _infer_pytorch(
        self, inputs: Dict[str, Any], batch_size: Optional[int]
    ) -> InferenceResult:
        """Run inference with PyTorch (fallback).

        Args:
            inputs: Input tensors
            batch_size: Batch size

        Returns:
            InferenceResult
        """
        import torch

        # Prepare inputs
        input_tensors = []
        for value in inputs.values():
            if isinstance(value, torch.Tensor):
                tensor = value
            else:
                tensor = torch.tensor(value)

            if self.device_manager.is_available:
                tensor = tensor.cuda()
            input_tensors.append(tensor)

        # Run inference
        with torch.no_grad():
            if self.config.cuda.enable_mixed_precision:
                with torch.cuda.amp.autocast():
                    outputs = self._torch_model(*input_tensors)
            else:
                outputs = self._torch_model(*input_tensors)

        # Get memory usage
        mem_info = self.device_manager.get_device_memory()
        memory_used = mem_info[1] if mem_info else 0.0
        memory_used_mb = (mem_info[0] - memory_used) * 1024 if mem_info else 0.0

        return InferenceResult(
            predictions=outputs.cpu() if self.device_manager.is_available else outputs,
            latency_ms=0.0,
            batch_size=batch_size or input_tensors[0].shape[0],
            device_id=self.device_manager.get_current_device() or 0,
            memory_used_mb=memory_used_mb,
            success=True,
        )

    def _update_metrics(self, latency_ms: float, batch_size: int) -> None:
        """Update engine metrics.

        Args:
            latency_ms: Inference latency
            batch_size: Batch size
        """
        self._metrics.total_inferences += batch_size
        self._metrics.total_latency_ms += latency_ms
        self._metrics.min_latency_ms = min(self._metrics.min_latency_ms, latency_ms)
        self._metrics.max_latency_ms = max(self._metrics.max_latency_ms, latency_ms)
        self._metrics.avg_latency_ms = (
            self._metrics.total_latency_ms / self._metrics.total_inferences
            if self._metrics.total_inferences > 0
            else 0.0
        )

        # Calculate throughput
        elapsed = time.time() - self._start_time
        if elapsed > 0:
            self._metrics.throughput_ips = self._metrics.total_inferences / elapsed

    def get_metrics(self) -> EngineMetrics:
        """Get current engine metrics.

        Returns:
            EngineMetrics with performance statistics
        """
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset engine metrics."""
        self._metrics = EngineMetrics()
        self._start_time = time.time()

    def save_engine(self, output_path: Union[str, Path]) -> bool:
        """Save TensorRT engine to disk.

        Args:
            output_path: Output path for engine file

        Returns:
            True if successful, False otherwise
        """
        if not self._use_tensorrt or self._engine is None:
            logger.warning("TensorRT engine not available for saving")
            return False

        try:
            output_path = Path(output_path)
            engine_data = self._engine.serialize()
            with open(output_path, "wb") as f:
                f.write(engine_data)
            logger.info(f"Saved TensorRT engine to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving engine: {e}")
            return False

    def __repr__(self) -> str:
        return (
            f"TensorRTEngine(model_loaded={self._model_loaded}, "
            f"use_tensorrt={self._use_tensorrt}, "
            f"device={self.device_manager.get_current_device()})"
        )
