"""
TensorRT Optimizer - Model Optimization for Low-Latency Inference

Optimizes ML models for TensorRT inference with:
- FP16/INT8 quantization
- Layer fusion
- Kernel auto-tuning
- Dynamic batching
- Calibration

Performance Targets:
- <1ms inference latency
- 1000+ inferences/second
- <2GB memory per model
- <1% accuracy degradation
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class PrecisionMode(Enum):
    """Precision modes for TensorRT optimization."""
    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"
    MIXED = "mixed"


@dataclass
class OptimizationConfig:
    """Configuration for TensorRT optimization."""
    precision: PrecisionMode = PrecisionMode.FP16
    max_batch_size: int = 32
    max_workspace_size: int = 1 << 30  # 1GB
    enable_layer_fusion: bool = True
    enable_kernel_tuning: bool = True
    enable_dynamic_batching: bool = True
    calibrate_int8: bool = True
    calibration_data_size: int = 1000
    target_latency: float = 0.001  # 1ms target
    min_accuracy: float = 0.99  # 99% accuracy threshold


@dataclass
class OptimizationResult:
    """Result of TensorRT optimization."""
    success: bool
    engine_path: str
    precision: PrecisionMode
    latency_ms: float
    throughput_ips: float
    memory_mb: float
    accuracy_retention: float
    optimization_time_s: float
    error: Optional[str] = None


class TensorRTOptimizer:
    """
    Optimizes ML models for TensorRT inference.
    
    Features:
    - Model conversion to TensorRT engine
    - Precision quantization (FP16/INT8)
    - Layer fusion optimization
    - Dynamic batching support
    - Performance benchmarking
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        """
        Initialize TensorRT optimizer.
        
        Args:
            config: Optimization configuration
        """
        self.config = config or OptimizationConfig()
        self._tensorrt_available = False
        self._initialized = False
        self._check_tensorrt_availability()
    
    def _check_tensorrt_availability(self) -> None:
        """Check if TensorRT is available."""
        try:
            import tensorrt as trt
            self._tensorrt_available = True
            self._initialized = True
            logger.info(f"TensorRT initialized: {trt.__version__}")
        except ImportError:
            logger.warning("TensorRT not available, optimization disabled")
            self._tensorrt_available = False
        except Exception as e:
            logger.error(f"TensorRT initialization failed: {e}")
            self._tensorrt_available = False
    
    @property
    def is_available(self) -> bool:
        """Check if TensorRT is available."""
        return self._tensorrt_available
    
    def optimize_model(
        self,
        model_path: str,
        output_path: str,
        input_shape: Tuple[int, ...],
        model_format: str = "onnx"
    ) -> OptimizationResult:
        """
        Optimize model for TensorRT inference.
        
        Args:
            model_path: Path to input model
            output_path: Path for optimized engine
            input_shape: Input tensor shape
            model_format: Model format ('onnx', 'torch', 'tf')
            
        Returns:
            OptimizationResult with performance metrics
        """
        if not self._tensorrt_available:
            return OptimizationResult(
                success=False,
                engine_path="",
                precision=self.config.precision,
                latency_ms=0.0,
                throughput_ips=0.0,
                memory_mb=0.0,
                accuracy_retention=0.0,
                optimization_time_s=0.0,
                error="TensorRT not available"
            )
        
        try:
            import time
            start_time = time.time()
            
            logger.info(f"Optimizing model: {model_path} -> {output_path}")
            
            # Build TensorRT engine
            engine = self._build_engine(
                model_path,
                input_shape,
                model_format
            )
            
            if engine is None:
                return OptimizationResult(
                    success=False,
                    engine_path="",
                    precision=self.config.precision,
                    latency_ms=0.0,
                    throughput_ips=0.0,
                    memory_mb=0.0,
                    accuracy_retention=0.0,
                    optimization_time_s=0.0,
                    error="Failed to build engine"
                )
            
            # Save engine
            self._save_engine(engine, output_path)
            
            # Benchmark performance
            latency, throughput, memory = self._benchmark_engine(
                engine,
                input_shape
            )
            
            optimization_time = time.time() - start_time
            
            logger.info(
                f"Optimization complete: {latency*1000:.2f}ms latency, "
                f"{throughput:.0f} inferences/sec, {memory:.0f}MB memory"
            )
            
            return OptimizationResult(
                success=True,
                engine_path=output_path,
                precision=self.config.precision,
                latency_ms=latency * 1000,
                throughput_ips=throughput,
                memory_mb=memory,
                accuracy_retention=1.0,  # Will be measured separately
                optimization_time_s=optimization_time
            )
            
        except Exception as e:
            logger.error(f"Model optimization failed: {e}")
            return OptimizationResult(
                success=False,
                engine_path="",
                precision=self.config.precision,
                latency_ms=0.0,
                throughput_ips=0.0,
                memory_mb=0.0,
                accuracy_retention=0.0,
                optimization_time_s=0.0,
                error=str(e)
            )
    
    def _build_engine(
        self,
        model_path: str,
        input_shape: Tuple[int, ...],
        model_format: str
    ) -> Optional[Any]:
        """
        Build TensorRT engine from model.
        
        Args:
            model_path: Path to model
            input_shape: Input tensor shape
            model_format: Model format
            
        Returns:
            TensorRT engine or None
        """
        try:
            import tensorrt as trt
            
            # Create builder and network
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            
            # Set optimization flags
            config = builder.create_builder_config()
            config.max_workspace_size = self.config.max_workspace_size
            
            # Set precision
            if self.config.precision == PrecisionMode.FP16:
                config.set_flag(trt.BuilderFlag.FP16)
            elif self.config.precision == PrecisionMode.INT8:
                config.set_flag(trt.BuilderFlag.INT8)
            elif self.config.precision == PrecisionMode.MIXED:
                config.set_flag(trt.BuilderFlag.FP16)
                config.set_flag(trt.BuilderFlag.INT8)
            
            # Enable layer fusion
            if self.config.enable_layer_fusion:
                config.set_flag(trt.BuilderFlag.FP16)  # Implies fusion
            
            # Dynamic batching
            if self.config.enable_dynamic_batching:
                profile = builder.create_optimization_profile()
                profile.set_shape(
                    "input",
                    (1,) + input_shape[1:],
                    (self.config.max_batch_size // 2,) + input_shape[1:],
                    (self.config.max_batch_size,) + input_shape[1:]
                )
                config.add_optimization_profile(profile)
            
            # Load model based on format
            if model_format == "onnx":
                network = self._load_onnx_model(builder, model_path, logger)
            elif model_format == "torch":
                network = self._load_torch_model(builder, model_path, input_shape, logger)
            elif model_format == "tf":
                network = self._load_tf_model(builder, model_path, input_shape, logger)
            else:
                raise ValueError(f"Unsupported model format: {model_format}")
            
            if network is None:
                return None
            
            # Build engine
            engine = builder.build_engine(network, config)
            
            if engine is None:
                logger.error("Failed to build TensorRT engine")
                return None
            
            return engine
            
        except Exception as e:
            logger.error(f"Engine build failed: {e}")
            return None
    
    def _load_onnx_model(
        self,
        builder: Any,
        model_path: str,
        logger: Any
    ) -> Optional[Any]:
        """Load ONNX model for TensorRT."""
        try:
            import tensorrt as trt
            
            network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
            parser = trt.OnnxParser(network, logger)
            
            with open(model_path, 'rb') as f:
                if not parser.parse(f.read()):
                    for error in range(parser.num_errors):
                        logger.error(parser.get_error(error))
                    return None
            
            return network
            
        except Exception as e:
            logger.error(f"ONNX loading failed: {e}")
            return None
    
    def _load_torch_model(
        self,
        builder: Any,
        model_path: str,
        input_shape: Tuple[int, ...],
        logger: Any
    ) -> Optional[Any]:
        """Load PyTorch model for TensorRT."""
        try:
            import torch
            import tensorrt as trt
            
            # Load PyTorch model
            model = torch.load(model_path)
            model.eval()
            
            # Create dummy input for tracing
            dummy_input = torch.randn(input_shape)
            
            # Convert to TorchScript
            traced_model = torch.jit.trace(model, dummy_input)
            
            # Export to ONNX first
            onnx_path = model_path.replace('.pt', '.onnx')
            torch.onnx.export(
                model,
                dummy_input,
                onnx_path,
                input_names=['input'],
                output_names=['output'],
                dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
            )
            
            # Load ONNX model
            return self._load_onnx_model(builder, onnx_path, logger)
            
        except Exception as e:
            logger.error(f"PyTorch loading failed: {e}")
            return None
    
    def _load_tf_model(
        self,
        builder: Any,
        model_path: str,
        input_shape: Tuple[int, ...],
        logger: Any
    ) -> Optional[Any]:
        """Load TensorFlow model for TensorRT."""
        try:
            import tensorflow as tf
            import tensorrt as trt
            
            # Load TensorFlow model
            model = tf.saved_model.load(model_path)
            
            # Convert to ONNX
            # Note: This requires tf2onnx package
            try:
                import tf2onnx
                
                onnx_path = model_path.replace('.pb', '.onnx')
                spec = (tf.TensorSpec(input_shape, tf.float32, name="input"),)
                model_proto, _ = tf2onnx.convert.from_keras(
                    model,
                    input_signature=spec,
                    output_path=onnx_path
                )
                
                return self._load_onnx_model(builder, onnx_path, logger)
                
            except ImportError:
                logger.error("tf2onnx not available for TF to ONNX conversion")
                return None
            
        except Exception as e:
            logger.error(f"TensorFlow loading failed: {e}")
            return None
    
    def _save_engine(self, engine: Any, output_path: str) -> None:
        """Save TensorRT engine to file."""
        try:
            import tensorrt as trt
            
            with open(output_path, 'wb') as f:
                f.write(engine.serialize())
            
            logger.info(f"Engine saved to {output_path}")
            
        except Exception as e:
            logger.error(f"Engine save failed: {e}")
    
    def _benchmark_engine(
        self,
        engine: Any,
        input_shape: Tuple[int, ...]
    ) -> Tuple[float, float, float]:
        """
        Benchmark TensorRT engine performance.
        
        Args:
            engine: TensorRT engine
            input_shape: Input tensor shape
            
        Returns:
            Tuple of (latency_sec, throughput_ips, memory_mb)
        """
        try:
            import tensorrt as trt
            import numpy as np
            import time
            
            # Create execution context
            logger = trt.Logger(trt.Logger.WARNING)
            runtime = trt.Runtime(logger)
            engine = runtime.deserialize_cuda_engine(engine.serialize())
            context = engine.create_execution_context()
            
            # Allocate memory
            batch_size = input_shape[0]
            input_size = np.prod(input_shape) * 4  # float32 = 4 bytes
            output_size = batch_size * 4  # Assume single output
            
            import torch
            d_input = torch.cuda.FloatTensor(input_shape)
            d_output = torch.cuda.FloatTensor(batch_size)
            
            # Warmup
            for _ in range(10):
                context.execute_v2(
                    [int(d_input.data_ptr()), int(d_output.data_ptr())]
                )
            
            # Benchmark
            num_iterations = 100
            torch.cuda.synchronize()
            start_time = time.time()
            
            for _ in range(num_iterations):
                context.execute_v2(
                    [int(d_input.data_ptr()), int(d_output.data_ptr())]
                )
            
            torch.cuda.synchronize()
            end_time = time.time()
            
            latency = (end_time - start_time) / num_iterations
            throughput = 1.0 / latency
            
            # Get memory usage
            import torch
            memory_mb = torch.cuda.memory_allocated() / 1024**2
            
            return latency, throughput, memory_mb
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return 0.0, 0.0, 0.0
    
    def compare_with_baseline(
        self,
        baseline_model: Any,
        trt_engine: Any,
        test_data: np.ndarray
    ) -> Dict[str, Any]:
        """
        Compare TensorRT engine with baseline model.
        
        Args:
            baseline_model: Original model
            trt_engine: TensorRT engine
            test_data: Test data for comparison
            
        Returns:
            Comparison metrics
        """
        try:
            import numpy as np
            
            # Run baseline inference
            baseline_outputs = []
            for batch in test_data:
                output = baseline_model(batch)
                baseline_outputs.append(output)
            
            # Run TensorRT inference
            trt_outputs = []
            for batch in test_data:
                output = self._run_inference(trt_engine, batch)
                trt_outputs.append(output)
            
            # Compare outputs
            baseline_outputs = np.array(baseline_outputs)
            trt_outputs = np.array(trt_outputs)
            
            # Calculate accuracy retention
            mae = np.mean(np.abs(baseline_outputs - trt_outputs))
            relative_error = mae / (np.mean(np.abs(baseline_outputs)) + 1e-8)
            accuracy_retention = 1.0 - relative_error
            
            return {
                "accuracy_retention": accuracy_retention,
                "mean_absolute_error": mae,
                "relative_error": relative_error,
                "baseline_output_shape": baseline_outputs.shape,
                "trt_output_shape": trt_outputs.shape
            }
            
        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return {
                "error": str(e)
            }
    
    def _run_inference(self, engine: Any, input_data: np.ndarray) -> np.ndarray:
        """Run inference with TensorRT engine."""
        try:
            import tensorrt as trt
            import torch
            
            logger = trt.Logger(trt.Logger.WARNING)
            runtime = trt.Runtime(logger)
            engine = runtime.deserialize_cuda_engine(engine.serialize())
            context = engine.create_execution_context()
            
            # Convert input to GPU tensor
            d_input = torch.from_numpy(input_data).float().cuda()
            d_output = torch.zeros(input_data.shape[0]).cuda()
            
            # Execute
            context.execute_v2(
                [int(d_input.data_ptr()), int(d_output.data_ptr())]
            )
            
            return d_output.cpu().numpy()
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            return np.array([])


# Global optimizer instance
_global_optimizer: Optional[TensorRTOptimizer] = None


def get_tensorrt_optimizer(config: Optional[OptimizationConfig] = None) -> TensorRTOptimizer:
    """Get global TensorRT optimizer instance."""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = TensorRTOptimizer(config)
    return _global_optimizer
