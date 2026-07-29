"""
TensorRT Builder - Engine Construction Helper

Helper class for building TensorRT engines with various configurations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BuilderConfig:
    """Configuration for TensorRT builder."""
    max_batch_size: int = 32
    max_workspace_size: int = 1 << 30  # 1GB
    fp16_mode: bool = True
    int8_mode: bool = False
    strict_type_constraints: bool = False
    allow_gpu_fallback: bool = True


class TensorRTBuilder:
    """
    Helper class for building TensorRT engines.
    
    Provides simplified interface for engine construction
    with common configurations.
    """
    
    def __init__(self, config: Optional[BuilderConfig] = None):
        """
        Initialize TensorRT builder.
        
        Args:
            config: Builder configuration
        """
        self.config = config or BuilderConfig()
        self._builder_available = False
        self._check_builder_availability()
    
    def _check_builder_availability(self) -> None:
        """Check if TensorRT builder is available."""
        try:
            import tensorrt as trt
            self._builder_available = True
            logger.info("TensorRT builder initialized")
        except ImportError:
            logger.warning("TensorRT not available, builder disabled")
            self._builder_available = False
        except Exception as e:
            logger.error(f"Builder initialization failed: {e}")
            self._builder_available = False
    
    @property
    def is_available(self) -> bool:
        """Check if builder is available."""
        return self._builder_available
    
    def create_builder_config(self) -> Optional[Any]:
        """
        Create TensorRT builder configuration.
        
        Returns:
            Builder config or None
        """
        if not self._builder_available:
            return None
        
        try:
            import tensorrt as trt
            
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            config = builder.create_builder_config()
            
            # Set workspace size
            config.max_workspace_size = self.config.max_workspace_size
            
            # Set precision modes
            if self.config.fp16_mode:
                config.set_flag(trt.BuilderFlag.FP16)
            
            if self.config.int8_mode:
                config.set_flag(trt.BuilderFlag.INT8)
            
            if self.config.strict_type_constraints:
                config.set_flag(trt.BuilderFlag.STRICT_TYPES)
            
            return config
            
        except Exception as e:
            logger.error(f"Builder config creation failed: {e}")
            return None
    
    def create_network(
        self,
        explicit_batch: bool = True
    ) -> Optional[Any]:
        """
        Create TensorRT network.
        
        Args:
            explicit_batch: Use explicit batch dimension
            
        Returns:
            Network or None
        """
        if not self._builder_available:
            return None
        
        try:
            import tensorrt as trt
            
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            
            flags = 0
            if explicit_batch:
                flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
            
            network = builder.create_network(flags)
            
            return network
            
        except Exception as e:
            logger.error(f"Network creation failed: {e}")
            return None
    
    def create_optimization_profile(
        self,
        min_shape: Tuple[int, ...],
        opt_shape: Tuple[int, ...],
        max_shape: Tuple[int, ...],
        input_name: str = "input"
    ) -> Optional[Any]:
        """
        Create optimization profile for dynamic shapes.
        
        Args:
            min_shape: Minimum input shape
            opt_shape: Optimal input shape
            max_shape: Maximum input shape
            input_name: Input tensor name
            
        Returns:
            Optimization profile or None
        """
        if not self._builder_available:
            return None
        
        try:
            import tensorrt as trt
            
            logger = trt.Logger(trt.Logger.WARNING)
            builder = trt.Builder(logger)
            
            profile = builder.create_optimization_profile()
            profile.set_shape(input_name, min_shape, opt_shape, max_shape)
            
            return profile
            
        except Exception as e:
            logger.error(f"Optimization profile creation failed: {e}")
            return None


# Global builder instance
_global_builder: Optional[TensorRTBuilder] = None


def get_tensorrt_builder(config: Optional[BuilderConfig] = None) -> TensorRTBuilder:
    """Get global TensorRT builder instance."""
    global _global_builder
    if _global_builder is None:
        _global_builder = TensorRTBuilder(config)
    return _global_builder
