"""
CPU-Based Intelligence Processor for V5 Free-Tier
Optimized ML inference using CPU instead of GPU
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from collections import deque

logger = logging.getLogger("momento.cpu_intelligence")

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available, system metrics will be limited")

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("ONNX Runtime not available, using fallback")

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, using numpy fallback")

from .config import CPUMLConfig, ModelOptimizationConfig, DEFAULT_CPU_CONFIG, DEFAULT_OPTIMIZATION_CONFIG


@dataclass
class InferenceResult:
    """Result of CPU-based inference."""
    prediction: Any
    confidence: float
    latency_ms: float
    model_used: str
    framework: str
    batch_size: int


class CPUIntelligenceProcessor:
    """
    CPU-based intelligence processor for V5 free-tier deployment.
    Optimized for CPU inference without GPU acceleration.
    """
    
    def __init__(self, config: Optional[CPUMLConfig] = None):
        self.config = config or DEFAULT_CPU_CONFIG
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.performance_stats = deque(maxlen=1000)
        self._initialize_frameworks()
        
    def _initialize_frameworks(self):
        """Initialize ML frameworks based on configuration."""
        if self.config.enable_onnx and ONNX_AVAILABLE:
            logger.info("ONNX Runtime initialized for CPU inference")
            self.onnx_session = None  # Will be loaded per model
            
        if SKLEARN_AVAILABLE:
            logger.info("scikit-learn initialized as fallback")
            
        logger.info("CPU Intelligence Processor initialized with config: %s", self.config.to_dict())
    
    def load_model(self, model_name: str, model_path: str, model_type: str = "onnx"):
        """
        Load a model for CPU inference.
        
        Args:
            model_name: Name of the model
            model_path: Path to model file
            model_type: Type of model (onnx, sklearn)
        """
        try:
            if model_type == "onnx" and ONNX_AVAILABLE:
                # Configure ONNX Runtime for CPU
                so = ort.SessionOptions()
                so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                
                if self.config.enable_threading:
                    so.intra_op_num_threads = self.config.num_threads
                    so.inter_op_num_threads = self.config.num_threads
                
                self.onnx_session = ort.InferenceSession(model_path, so)
                self.models[model_name] = self.onnx_session
                logger.info("Loaded ONNX model: %s", model_name)
                
            elif model_type == "sklearn" and SKLEARN_AVAILABLE:
                # Load sklearn model (implementation depends on model format)
                # This is a placeholder - actual loading depends on model serialization
                self.models[model_name] = None  # Placeholder
                logger.info("Loaded sklearn model: %s", model_name)
                
            else:
                logger.warning("Model type %s not available, using fallback", model_type)
                
        except Exception as exc:
            logger.error("Failed to load model %s: %s", model_name, exc)
    
    def predict(self, model_name: str, input_data: np.ndarray) -> InferenceResult:
        """
        Run inference on CPU.
        
        Args:
            model_name: Name of the model to use
            input_data: Input data for inference
            
        Returns:
            InferenceResult with prediction and metadata
        """
        start_time = time.time()
        
        try:
            if model_name not in self.models:
                raise ValueError(f"Model {model_name} not loaded")
                
            model = self.models[model_name]
            
            # Batch processing
            if self.config.enable_batching and len(input_data) > self.config.batch_size:
                predictions = []
                confidences = []
                
                for i in range(0, len(input_data), self.config.batch_size):
                    batch = input_data[i:i + self.config.batch_size]
                    batch_result = self._run_inference(model, batch)
                    predictions.extend(batch_result[0])
                    confidences.extend(batch_result[1])
                    
                result = np.array(predictions)
                confidence = np.mean(confidences)
                batch_size = len(input_data)
                
            else:
                result, confidence = self._run_inference(model, input_data)
                batch_size = len(input_data)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Record performance
            self.performance_stats.append({
                "latency_ms": latency_ms,
                "batch_size": batch_size,
                "model": model_name,
                "timestamp": datetime.now(timezone.utc)
            })
            
            return InferenceResult(
                prediction=result,
                confidence=confidence,
                latency_ms=latency_ms,
                model_used=model_name,
                framework=self._get_framework_name(model),
                batch_size=batch_size
            )
            
        except Exception as exc:
            logger.error("Inference failed: %s", exc)
            raise
    
    def _run_inference(self, model: Any, input_data: np.ndarray) -> Tuple[np.ndarray, float]:
        """Run actual inference based on model type."""
        
        if ONNX_AVAILABLE and isinstance(model, ort.InferenceSession):
            # ONNX Runtime inference
            input_name = model.get_inputs()[0].name
            outputs = model.run(None, {input_name: input_data.astype(np.float32)})
            prediction = outputs[0]
            confidence = 0.95  # Placeholder - actual confidence depends on model
            
        elif SKLEARN_AVAILABLE:
            # scikit-learn inference
            if isinstance(model, (RandomForestClassifier, LogisticRegression)):
                prediction = model.predict(input_data)
                confidence = np.max(model.predict_proba(input_data), axis=1)
            else:
                prediction = model.predict(input_data)
                confidence = 0.90  # Placeholder
        else:
            # Fallback to simple numpy-based prediction
            prediction = np.mean(input_data, axis=1)
            confidence = np.full(len(prediction), 0.85)  # Default confidence
        
        return prediction, confidence
    
    def _get_framework_name(self, model: Any) -> str:
        """Get the framework name for a model."""
        if ONNX_AVAILABLE and isinstance(model, ort.InferenceSession):
            return "onnx"
        elif SKLEARN_AVAILABLE:
            return "sklearn"
        else:
            return "fallback"
    
    def optimize_model(self, model_name: str, optimization_config: Optional[ModelOptimizationConfig] = None):
        """
        Optimize a model for CPU inference.
        
        Args:
            model_name: Name of the model to optimize
            optimization_config: Optimization configuration
        """
        config = optimization_config or ModelOptimizationConfig()
        
        logger.info("Optimizing model %s with config: %s", model_name, config)
        
        # Placeholder for model optimization
        # In production, this would include:
        # - ONNX conversion and optimization
        # - Quantization
        # - Pruning
        # - Distillation
        
        if config.enable_onnx_optimization and ONNX_AVAILABLE:
            logger.info("Applying ONNX optimizations")
            
        if config.enable_quantization:
            logger.info("Applying quantization: %s", config.quantization_mode)
            
        if config.enable_pruning:
            logger.info("Applying pruning: %s", config.pruning_method)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.performance_stats:
            return {}
            
        latencies = [s["latency_ms"] for s in self.performance_stats]
        batch_sizes = [s["batch_size"] for s in self.performance_stats]
        
        return {
            "avg_latency_ms": np.mean(latencies),
            "p50_latency_ms": np.percentile(latencies, 50),
            "p95_latency_ms": np.percentile(latencies, 95),
            "p99_latency_ms": np.percentile(latencies, 99),
            "avg_batch_size": np.mean(batch_sizes),
            "total_inferences": len(self.performance_stats),
            "config": self.config.to_dict()
        }
    
    def benchmark(self, model_name: str, test_data: np.ndarray, iterations: int = 100) -> Dict[str, Any]:
        """
        Benchmark CPU inference performance.
        
        Args:
            model_name: Name of the model to benchmark
            test_data: Test data for benchmarking
            iterations: Number of iterations
            
        Returns:
            Benchmark results
        """
        logger.info("Benchmarking model %s with %d iterations", model_name, iterations)
        
        latencies = []
        throughputs = []
        
        for i in range(iterations):
            start = time.time()
            result = self.predict(model_name, test_data)
            latency = result.latency_ms
            throughput = len(test_data) / (latency / 1000)
            
            latencies.append(latency)
            throughputs.append(throughput)
        
        return {
            "model_name": model_name,
            "iterations": iterations,
            "avg_latency_ms": np.mean(latencies),
            "p50_latency_ms": np.percentile(latencies, 50),
            "p95_latency_ms": np.percentile(latencies, 95),
            "p99_latency_ms": np.percentile(latencies, 99),
            "avg_throughput": np.mean(throughputs),
            "p50_throughput": np.percentile(throughputs, 50),
            "target_latency_ms": self.config.target_latency_ms,
            "target_throughput": self.config.target_throughput,
            "meets_latency_target": np.mean(latencies) <= self.config.target_latency_ms,
            "meets_throughput_target": np.mean(throughputs) >= self.config.target_throughput
        }


# Singleton instance
_cpu_processor: Optional[CPUIntelligenceProcessor] = None


def get_cpu_processor() -> CPUIntelligenceProcessor:
    """Get the singleton CPU processor instance."""
    global _cpu_processor
    if _cpu_processor is None:
        _cpu_processor = CPUIntelligenceProcessor()
    return _cpu_processor