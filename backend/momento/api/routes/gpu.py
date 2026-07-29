"""GPU intelligence API endpoints.

Provides monitoring, control, and status endpoints for the GPU intelligence subsystem.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from ...gpu_intelligence.integration import (
    get_batch_processor,
    get_device_manager,
    get_feature_extractor,
    get_gpu_status,
    is_gpu_available,
    shutdown_gpu_intelligence,
)
from ..deps import source_param

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gpu", tags=["gpu"])


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """Get GPU intelligence status and metrics.

    Returns:
        Dictionary with GPU availability, device info, memory usage, and performance metrics
    """
    try:
        status = get_gpu_status()
        return status
    except Exception as e:
        logger.error(f"Error getting GPU status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices")
async def get_devices() -> Dict[str, Any]:
    """Get detailed information about available GPU devices.

    Returns:
        Dictionary with device specifications and capabilities
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        device_manager = get_device_manager()
        if not device_manager:
            raise HTTPException(status_code=503, detail="Device manager not initialized")

        devices = []
        for device_id in range(device_manager.device_count):
            specs = device_manager.get_device_specs(device_id)
            memory = device_manager.get_device_memory(device_id)

            device_info = {
                "device_id": device_id,
                "model": specs.model.value if specs else "Unknown",
                "memory_gb": specs.memory_gb if specs else 0,
                "memory_bandwidth_tbps": specs.memory_bandwidth_tbps if specs else 0,
                "tensor_cores_tflops": specs.tensor_cores_tflops if specs else 0,
                "cuda_cores": specs.cuda_cores if specs else 0,
                "compute_capability": specs.compute_capability if specs else (0, 0),
                "memory_total_gb": memory[0] if memory else 0,
                "memory_free_gb": memory[1] if memory else 0,
            }
            devices.append(device_info)

        return {"available": True, "devices": devices}
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory")
async def get_memory_summary(
    device_id: int = Query(default=0, ge=0, description="GPU device ID")
) -> Dict[str, Any]:
    """Get detailed memory usage summary for a device.

    Args:
        device_id: GPU device ID

    Returns:
        Dictionary with memory statistics
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        device_manager = get_device_manager()
        if not device_manager:
            raise HTTPException(status_code=503, detail="Device manager not initialized")

        summary = device_manager.get_memory_summary()
        if device_id < len(summary.get("devices", [])):
            return summary["devices"][device_id]
        else:
            raise HTTPException(status_code=404, detail="Device not found")
    except Exception as e:
        logger.error(f"Error getting memory summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pool/stats")
async def get_memory_pool_stats(
    device_id: int = Query(default=0, ge=0, description="GPU device ID")
) -> Dict[str, Any]:
    """Get memory pool statistics.

    Args:
        device_id: GPU device ID

    Returns:
        Dictionary with pool statistics
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        from ...gpu_intelligence.integration import get_memory_pool

        memory_pool = get_memory_pool()
        if not memory_pool:
            raise HTTPException(status_code=503, detail="Memory pool not initialized")

        stats = memory_pool.get_stats(device_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting pool stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pool/clear")
async def clear_memory_pool(
    device_id: int = Query(default=None, description="GPU device ID (null for all)")
) -> Dict[str, Any]:
    """Clear the memory pool.

    Args:
        device_id: GPU device ID (optional, clears all if not specified)

    Returns:
        Success message
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        from ...gpu_intelligence.integration import get_memory_pool

        memory_pool = get_memory_pool()
        if not memory_pool:
            raise HTTPException(status_code=503, detail="Memory pool not initialized")

        memory_pool.clear_pool(device_id)
        return {"success": True, "message": "Memory pool cleared"}
    except Exception as e:
        logger.error(f"Error clearing pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/batch/stats")
async def get_batch_stats() -> Dict[str, Any]:
    """Get batch processing statistics.

    Returns:
        Dictionary with batch processing metrics
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        batch_processor = get_batch_processor()
        if not batch_processor:
            raise HTTPException(status_code=503, detail="Batch processor not initialized")

        stats = batch_processor.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting batch stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/reset")
async def reset_batch_stats() -> Dict[str, Any]:
    """Reset batch processing statistics.

    Returns:
        Success message
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        batch_processor = get_batch_processor()
        if not batch_processor:
            raise HTTPException(status_code=503, detail="Batch processor not initialized")

        batch_processor.reset_stats()
        return {"success": True, "message": "Batch statistics reset"}
    except Exception as e:
        logger.error(f"Error resetting batch stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cache/clear")
async def clear_gpu_cache() -> Dict[str, Any]:
    """Clear GPU cache to free memory.

    Returns:
        Success message
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        device_manager = get_device_manager()
        if not device_manager:
            raise HTTPException(status_code=503, detail="Device manager not initialized")

        device_manager.empty_cache()
        return {"success": True, "message": "GPU cache cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synchronize")
async def synchronize_gpu() -> Dict[str, Any]:
    """Synchronize CUDA operations.

    Returns:
        Success message
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        device_manager = get_device_manager()
        if not device_manager:
            raise HTTPException(status_code=503, detail="Device manager not initialized")

        device_manager.synchronize()
        return {"success": True, "message": "GPU synchronized"}
    except Exception as e:
        logger.error(f"Error synchronizing GPU: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/extract")
async def extract_features(
    data: list[float] = Query(..., description="List of multiplier values"),
) -> Dict[str, Any]:
    """Extract features from data using GPU acceleration.

    Args:
        data: List of multiplier values

    Returns:
        Dictionary with extracted features
    """
    if not is_gpu_available():
        return {"available": False, "message": "GPU not available"}

    try:
        feature_extractor = get_feature_extractor()
        if not feature_extractor:
            raise HTTPException(status_code=503, detail="Feature extractor not initialized")

        result = feature_extractor.extract_features(data)
        return {
            "features": result.features,
            "extraction_time_ms": result.extraction_time_ms,
            "batch_size": result.batch_size,
            "device_id": result.device_id,
            "used_gpu": result.used_gpu,
        }
    except Exception as e:
        logger.error(f"Error extracting features: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for GPU intelligence subsystem.

    Returns:
        Health status
    """
    try:
        available = is_gpu_available()
        status = get_gpu_status() if available else {}

        return {
            "healthy": True,
            "gpu_available": available,
            "initialized": status.get("initialized", False),
            "device_count": status.get("device_count", 0),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
        }
