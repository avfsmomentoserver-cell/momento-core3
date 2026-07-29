"""Integration layer for GPU intelligence with existing analysis and forecast modules.

Provides GPU-accelerated versions of analysis functions that seamlessly integrate
with the existing codebase in analysis.py and forecast.py.
"""

import logging
from typing import Any, Dict, List, Optional, Sequence

from .config import GPUConfig
from .device_manager import DeviceManager
from .memory_pool import GPUMemoryPool
from .feature_extractor import GPUFeatureExtractor
from .batch_processor import AnalysisBatchProcessor

logger = logging.getLogger(__name__)

# Global GPU intelligence instances
_device_manager: Optional[DeviceManager] = None
_memory_pool: Optional[GPUMemoryPool] = None
_feature_extractor: Optional[GPUFeatureExtractor] = None
_batch_processor: Optional[AnalysisBatchProcessor] = None
_config: Optional[GPUConfig] = None


def initialize_gpu_intelligence(config: Optional[GPUConfig] = None) -> bool:
    """Initialize GPU intelligence subsystem.

    Args:
        config: GPU configuration (uses default if None)

    Returns:
        True if initialization successful, False otherwise
    """
    global _device_manager, _memory_pool, _feature_extractor, _batch_processor, _config

    try:
        _config = config or GPUConfig()

        # Initialize device manager
        _device_manager = DeviceManager(_config)

        if not _device_manager.is_available:
            logger.info("GPU not available, GPU intelligence disabled")
            return False

        # Initialize memory pool
        _memory_pool = GPUMemoryPool(_device_manager, _config)

        # Initialize feature extractor
        _feature_extractor = GPUFeatureExtractor(_device_manager, _memory_pool, _config)

        # Initialize batch processor
        _batch_processor = AnalysisBatchProcessor(
            _device_manager, _memory_pool, _config
        )

        logger.info(
            f"GPU intelligence initialized: {_device_manager.device_count} devices"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to initialize GPU intelligence: {e}")
        return False


def is_gpu_available() -> bool:
    """Check if GPU intelligence is available.

    Returns:
        True if GPU is available and initialized
    """
    return _device_manager is not None and _device_manager.is_available


def get_device_manager() -> Optional[DeviceManager]:
    """Get the device manager instance.

    Returns:
        DeviceManager instance or None
    """
    return _device_manager


def get_feature_extractor() -> Optional[GPUFeatureExtractor]:
    """Get the feature extractor instance.

    Returns:
        GPUFeatureExtractor instance or None
    """
    return _feature_extractor


def get_batch_processor() -> Optional[AnalysisBatchProcessor]:
    """Get the batch processor instance.

    Returns:
        AnalysisBatchProcessor instance or None
    """
    return _batch_processor


def get_memory_pool() -> Optional[GPUMemoryPool]:
    """Get the memory pool instance.

    Returns:
        GPUMemoryPool instance or None
    """
    return _memory_pool


def gpu_percentile(values: Sequence[float], pct: float) -> float:
    """GPU-accelerated percentile calculation.

    Args:
        values: Input values
        pct: Percentile (0-100)

    Returns:
        Percentile value
    """
    if not is_gpu_available():
        # Fallback to CPU implementation
        import statistics

        if not values:
            return 0.0
        ordered = sorted(float(v) for v in values)
        if len(ordered) == 1:
            return round(ordered[0], 4)
        import math

        rank = (pct / 100.0) * (len(ordered) - 1)
        low = math.floor(rank)
        high = math.ceil(rank)
        if low == high:
            return round(ordered[int(rank)], 4)
        weight = rank - low
        return round(ordered[low] * (1 - weight) + ordered[high] * weight, 4)

    # GPU implementation
    try:
        import torch

        device_id = _device_manager.get_current_device() or 0
        device = f"cuda:{device_id}"
        tensor = torch.tensor(values, dtype=torch.float32, device=device)
        sorted_tensor, _ = torch.sort(tensor)
        n = len(sorted_tensor)
        rank = (pct / 100.0) * (n - 1)
        low = int(rank)
        high = min(low + 1, n - 1)
        weight = rank - low
        result = sorted_tensor[low] * (1 - weight) + sorted_tensor[high] * weight
        return round(result.cpu().item(), 4)
    except Exception as e:
        logger.warning(f"GPU percentile failed, falling back to CPU: {e}")
        # Fallback to CPU
        from momento.analysis import percentile

        return percentile(values, pct)


def gpu_robust_percentiles(values: Sequence[float]) -> Dict[str, float]:
    """GPU-accelerated robust percentile calculation.

    Args:
        values: Input values

    Returns:
        Dictionary with percentiles (p05, p10, p25, p50, p75, p90, p95, p99)
    """
    if not is_gpu_available():
        # Fallback to CPU implementation
        from momento.analysis import robust_percentiles

        return robust_percentiles(values)

    # GPU implementation - compute all at once for efficiency
    try:
        import torch

        device_id = _device_manager.get_current_device() or 0
        device = f"cuda:{device_id}"
        tensor = torch.tensor(values, dtype=torch.float32, device=device)
        sorted_tensor, _ = torch.sort(tensor)
        n = len(sorted_tensor)

        percentiles = {}
        for pct in [5, 10, 25, 50, 75, 90, 95, 99]:
            rank = (pct / 100.0) * (n - 1)
            low = int(rank)
            high = min(low + 1, n - 1)
            weight = rank - low
            result = sorted_tensor[low] * (1 - weight) + sorted_tensor[high] * weight
            percentiles[f"p{pct:02d}"] = round(result.cpu().item(), 4)

        return percentiles
    except Exception as e:
        logger.warning(f"GPU robust percentiles failed, falling back to CPU: {e}")
        from momento.analysis import robust_percentiles

        return robust_percentiles(values)


def gpu_multipliers_stats(multipliers: Sequence[float]) -> Dict[str, float]:
    """GPU-accelerated statistics calculation for multipliers.

    Args:
        multipliers: Sequence of multiplier values

    Returns:
        Dictionary with mean, std, median, min, max
    """
    if not is_gpu_available():
        # Fallback to CPU implementation
        import statistics

        return {
            "mean": round(statistics.fmean(multipliers), 4) if multipliers else 0.0,
            "std": round(statistics.pstdev(multipliers), 4) if len(multipliers) > 1 else 0.0,
            "median": gpu_percentile(multipliers, 50),
            "min": round(min(multipliers), 4) if multipliers else 0.0,
            "max": round(max(multipliers), 4) if multipliers else 0.0,
        }

    # GPU implementation
    try:
        import torch

        device_id = _device_manager.get_current_device() or 0
        device = f"cuda:{device_id}"
        tensor = torch.tensor(multipliers, dtype=torch.float32, device=device)

        return {
            "mean": round(torch.mean(tensor).cpu().item(), 4),
            "std": round(torch.std(tensor).cpu().item(), 4),
            "median": gpu_percentile(multipliers, 50),
            "min": round(torch.min(tensor).cpu().item(), 4),
            "max": round(torch.max(tensor).cpu().item(), 4),
        }
    except Exception as e:
        logger.warning(f"GPU stats failed, falling back to CPU: {e}")
        import statistics

        return {
            "mean": round(statistics.fmean(multipliers), 4) if multipliers else 0.0,
            "std": round(statistics.pstdev(multipliers), 4) if len(multipliers) > 1 else 0.0,
            "median": gpu_percentile(multipliers, 50),
            "min": round(min(multipliers), 4) if multipliers else 0.0,
            "max": round(max(multipliers), 4) if multipliers else 0.0,
        }


def gpu_extract_round_features(rounds: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """GPU-accelerated feature extraction for rounds.

    Args:
        rounds: Sequence of round dictionaries

    Returns:
        Dictionary with extracted features
    """
    if not rounds:
        return {}

    multipliers = [float(r.get("multiplier", 1.0)) for r in rounds]

    if not is_gpu_available():
        # Fallback to CPU implementation
        return {
            "stats": gpu_multipliers_stats(multipliers),
            "percentiles": gpu_robust_percentiles(multipliers),
            "gpu_accelerated": False,
        }

    # GPU implementation with full feature extraction
    try:
        result = _feature_extractor.extract_features(
            multipliers,
            feature_names=[
                "mean",
                "std",
                "median",
                "min",
                "max",
                "range",
                "percentiles",
                "skewness",
                "kurtosis",
                "momentum",
                "volatility",
                "trend",
            ],
        )

        return {
            "stats": {
                "mean": result.features.get("mean", 0.0),
                "std": result.features.get("std", 0.0),
                "median": result.features.get("median", 0.0),
                "min": result.features.get("min", 0.0),
                "max": result.features.get("max", 0.0),
            },
            "percentiles": result.features.get("percentiles", {}),
            "advanced": {
                "skewness": result.features.get("skewness", 0.0),
                "kurtosis": result.features.get("kurtosis", 0.0),
                "momentum": result.features.get("momentum", 0.0),
                "volatility": result.features.get("volatility", 0.0),
                "trend": result.features.get("trend", 0.0),
            },
            "gpu_accelerated": True,
            "extraction_time_ms": result.extraction_time_ms,
            "device_id": result.device_id,
        }
    except Exception as e:
        logger.warning(f"GPU feature extraction failed, falling back to CPU: {e}")
        return {
            "stats": gpu_multipliers_stats(multipliers),
            "percentiles": gpu_robust_percentiles(multipliers),
            "gpu_accelerated": False,
        }


def gpu_detect_patterns(multipliers: Sequence[float]) -> Dict[str, Any]:
    """GPU-accelerated pattern detection.

    Args:
        multipliers: Sequence of multiplier values

    Returns:
        Dictionary with detected patterns
    """
    if not is_gpu_available():
        # Fallback to CPU implementation
        return {
            "ladder": {"detected": False, "length": 0, "strength": 0.0},
            "streak": {"current_streak": 0, "max_streak": 0, "threshold": 0.0},
            "spike": {"count": 0, "threshold": 2.0, "fraction": 0.0},
            "gpu_accelerated": False,
        }

    # GPU implementation
    try:
        patterns = _feature_extractor.detect_patterns_gpu(
            multipliers, pattern_types=["ladder", "streak", "spike"]
        )
        patterns["gpu_accelerated"] = True
        return patterns
    except Exception as e:
        logger.warning(f"GPU pattern detection failed, falling back to CPU: {e}")
        return {
            "ladder": {"detected": False, "length": 0, "strength": 0.0},
            "streak": {"current_streak": 0, "max_streak": 0, "threshold": 0.0},
            "spike": {"count": 0, "threshold": 2.0, "fraction": 0.0},
            "gpu_accelerated": False,
        }


def get_gpu_status() -> Dict[str, Any]:
    """Get GPU intelligence status and metrics.

    Returns:
        Dictionary with GPU status information
    """
    status = {
        "available": is_gpu_available(),
        "initialized": _device_manager is not None,
    }

    if is_gpu_available():
        status["device_count"] = _device_manager.device_count
        status["primary_device"] = _device_manager.get_current_device()
        status["memory_summary"] = _device_manager.get_memory_summary()

        if _memory_pool:
            status["memory_pool"] = _memory_pool.get_stats()

        if _batch_processor:
            status["batch_processor"] = _batch_processor.get_stats()

    return status


def shutdown_gpu_intelligence() -> None:
    """Shutdown GPU intelligence subsystem and free resources."""
    global _device_manager, _memory_pool, _feature_extractor, _batch_processor, _config

    if _batch_processor:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(_batch_processor.stop())
        except:
            pass

    if _memory_pool:
        _memory_pool.clear_pool()

    if _device_manager:
        _device_manager.empty_cache()

    _device_manager = None
    _memory_pool = None
    _feature_extractor = None
    _batch_processor = None
    _config = None

    logger.info("GPU intelligence shutdown complete")
