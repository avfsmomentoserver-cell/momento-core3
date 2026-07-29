"""
TensorRT Calibrator - INT8 Quantization Calibration

Handles calibration for INT8 quantization to maintain accuracy
while achieving performance improvements.

Performance Targets:
- <1% accuracy degradation
- Efficient calibration process
- Representative calibration data
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CalibrationConfig:
    """Configuration for INT8 calibration."""
    calibration_data_size: int = 1000
    calibration_batch_size: int = 32
    cache_file: str = "calibration.cache"
    entropy_calibrator: bool = True
    percentile: float = 99.99  # For percentile calibration


class TensorRTCalibrator:
    """
    Calibrates models for INT8 quantization.
    
    Features:
    - Entropy calibration
    - Percentile calibration
    - Calibration caching
    - Representative data sampling
    """
    
    def __init__(self, config: Optional[CalibrationConfig] = None):
        """
        Initialize TensorRT calibrator.
        
        Args:
            config: Calibration configuration
        """
        self.config = config or CalibrationConfig()
        self._calibrator_available = False
        self._initialized = False
        self._check_calibrator_availability()
    
    def _check_calibrator_availability(self) -> None:
        """Check if TensorRT calibrator is available."""
        try:
            import tensorrt as trt
            self._calibrator_available = True
            self._initialized = True
            logger.info("TensorRT calibrator initialized")
        except ImportError:
            logger.warning("TensorRT not available, calibrator disabled")
            self._calibrator_available = False
        except Exception as e:
            logger.error(f"Calibrator initialization failed: {e}")
            self._calibrator_available = False
    
    @property
    def is_available(self) -> bool:
        """Check if calibrator is available."""
        return self._calibrator_available
    
    def create_calibrator(
        self,
        calibration_data: np.ndarray,
        input_shape: tuple
    ) -> Optional[Any]:
        """
        Create TensorRT INT8 calibrator.
        
        Args:
            calibration_data: Calibration dataset
            input_shape: Input tensor shape
            
        Returns:
            TensorRT calibrator or None
        """
        if not self._calibrator_available:
            logger.warning("Calibrator not available")
            return None
        
        try:
            import tensorrt as trt
            
            # Sample calibration data
            sampled_data = self._sample_calibration_data(calibration_data)
            
            # Create calibrator based on configuration
            if self.config.entropy_calibrator:
                calibrator = self._create_entropy_calibrator(sampled_data, input_shape)
            else:
                calibrator = self._create_percentile_calibrator(sampled_data, input_shape)
            
            logger.info(f"Calibrator created with {len(sampled_data)} samples")
            return calibrator
            
        except Exception as e:
            logger.error(f"Calibrator creation failed: {e}")
            return None
    
    def _sample_calibration_data(self, data: np.ndarray) -> np.ndarray:
        """
        Sample calibration data representative of inference workload.
        
        Args:
            data: Full calibration dataset
            
        Returns:
            Sampled calibration data
        """
        if len(data) <= self.config.calibration_data_size:
            return data
        
        # Random sampling
        indices = np.random.choice(
            len(data),
            self.config.calibration_data_size,
            replace=False
        )
        return data[indices]
    
    def _create_entropy_calibrator(
        self,
        data: np.ndarray,
        input_shape: tuple
    ) -> Any:
        """Create entropy calibrator for INT8 quantization."""
        try:
            import tensorrt as trt
            
            class EntropyCalibrator(trt.IInt8EntropyCalibrator2):
                """Entropy calibrator implementation."""
                
                def __init__(self, data, input_shape, cache_file):
                    super().__init__()
                    self.data = data
                    self.input_shape = input_shape
                    self.cache_file = cache_file
                    self.current_index = 0
                
                def get_batch_size(self):
                    return len(self.data)
                
                def get_batch(self, names):
                    if self.current_index >= len(self.data):
                        return None
                    
                    batch = self.data[self.current_index]
                    self.current_index += 1
                    
                    # Convert to contiguous array
                    batch = np.ascontiguousarray(batch, dtype=np.float32)
                    return [batch]
                
                def read_calibration_cache(self):
                    try:
                        with open(self.cache_file, 'rb') as f:
                            return f.read()
                    except:
                        return None
                
                def write_calibration_cache(self, cache):
                    try:
                        with open(self.cache_file, 'wb') as f:
                            f.write(cache)
                    except:
                        pass
            
            return EntropyCalibrator(
                data,
                input_shape,
                self.config.cache_file
            )
            
        except Exception as e:
            logger.error(f"Entropy calibrator creation failed: {e}")
            return None
    
    def _create_percentile_calibrator(
        self,
        data: np.ndarray,
        input_shape: tuple
    ) -> Any:
        """Create percentile calibrator for INT8 quantization."""
        try:
            import tensorrt as trt
            
            class PercentileCalibrator(trt.IInt8MinMaxCalibrator):
                """Percentile calibrator implementation."""
                
                def __init__(self, data, input_shape, percentile, cache_file):
                    super().__init__()
                    self.data = data
                    self.input_shape = input_shape
                    self.percentile = percentile
                    self.cache_file = cache_file
                    self.current_index = 0
                
                def get_batch_size(self):
                    return len(self.data)
                
                def get_batch(self, names):
                    if self.current_index >= len(self.data):
                        return None
                    
                    batch = self.data[self.current_index]
                    self.current_index += 1
                    
                    batch = np.ascontiguousarray(batch, dtype=np.float32)
                    return [batch]
                
                def read_calibration_cache(self):
                    try:
                        with open(self.cache_file, 'rb') as f:
                            return f.read()
                    except:
                        return None
                
                def write_calibration_cache(self, cache):
                    try:
                        with open(self.cache_file, 'wb') as f:
                            f.write(cache)
                    except:
                        pass
            
            return PercentileCalibrator(
                data,
                input_shape,
                self.config.percentile,
                self.config.cache_file
            )
            
        except Exception as e:
            logger.error(f"Percentile calibrator creation failed: {e}")
            return None
    
    def validate_calibration(
        self,
        original_model: Any,
        quantized_model: Any,
        validation_data: np.ndarray
    ) -> Dict[str, Any]:
        """
        Validate INT8 calibration accuracy.
        
        Args:
            original_model: Original FP32 model
            quantized_model: INT8 quantized model
            validation_data: Validation dataset
            
        Returns:
            Validation metrics
        """
        try:
            import numpy as np
            
            # Run inference on both models
            original_outputs = []
            quantized_outputs = []
            
            for batch in validation_data:
                original_out = original_model(batch)
                quantized_out = quantized_model(batch)
                
                original_outputs.append(original_out)
                quantized_outputs.append(quantized_out)
            
            original_outputs = np.array(original_outputs)
            quantized_outputs = np.array(quantized_outputs)
            
            # Calculate metrics
            mae = np.mean(np.abs(original_outputs - quantized_outputs))
            mse = np.mean((original_outputs - quantized_outputs) ** 2)
            rmse = np.sqrt(mse)
            
            # Relative error
            relative_error = mae / (np.mean(np.abs(original_outputs)) + 1e-8)
            accuracy_retention = 1.0 - relative_error
            
            # Check if within acceptable threshold
            acceptable = accuracy_retention >= 0.99  # 99% retention
            
            return {
                "accuracy_retention": accuracy_retention,
                "mean_absolute_error": mae,
                "root_mean_squared_error": rmse,
                "relative_error": relative_error,
                "acceptable": acceptable,
                "validation_samples": len(validation_data)
            }
            
        except Exception as e:
            logger.error(f"Calibration validation failed: {e}")
            return {
                "error": str(e)
            }


# Global calibrator instance
_global_calibrator: Optional[TensorRTCalibrator] = None


def get_tensorrt_calibrator(config: Optional[CalibrationConfig] = None) -> TensorRTCalibrator:
    """Get global TensorRT calibrator instance."""
    global _global_calibrator
    if _global_calibrator is None:
        _global_calibrator = TensorRTCalibrator(config)
    return _global_calibrator
