"""FPGA-accelerated ingestion API routes.

Provides endpoints for monitoring and controlling the FPGA/DPDK ingestion pipeline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from ... import config
from ...fpga_ingest import get_pipeline, start_pipeline, stop_pipeline
from ...stream_optimizer import get_optimizer, start_optimizer, stop_optimizer
from ..deps import source_param

logger = logging.getLogger("momento.api.fpga")

router = APIRouter(prefix="/fpga", tags=["fpga"])


@router.get("/status")
async def get_fpga_status() -> Dict[str, Any]:
    """Get FPGA/DPDK ingestion pipeline status and metrics.

    Returns:
        Dictionary containing:
        - Pipeline running state
        - FPGA parser metrics (latency, utilization)
        - DPDK network metrics (throughput, buffer utilization)
        - Ingestion statistics (packets received/parsed/dropped)
    """
    pipeline = get_pipeline()
    metrics = pipeline.metrics()

    return {
        "config": {
            "fpga": {
                "enabled": config.FPGA_ENABLED,
                "device_path": config.FPGA_DEVICE_PATH,
                "parse_fix": config.FPGA_PARSE_FIX,
                "parse_orderbook": config.FPGA_PARSE_ORDERBOOK,
                "feature_extraction": config.FPGA_FEATURE_EXTRACTION,
                "risk_checks": config.FPGA_RISK_CHECKS,
            },
            "dpdk": {
                "enabled": config.DPDK_ENABLED,
                "memory_channels": config.DPDK_MEMORY_CHANNELS,
                "rx_queues": config.DPDK_RX_QUEUES,
                "tx_queues": config.DPDK_TX_QUEUES,
                "descriptor_rings": config.DPDK_DESCRIPTOR_RINGS,
                "hugepages": config.DPDK_HUGEPAGES,
                "mtu": config.DPDK_MTU,
            },
        },
        "metrics": metrics,
    }


@router.post("/start")
async def start_fpga_pipeline() -> Dict[str, Any]:
    """Start the FPGA-accelerated ingestion pipeline.

    Returns:
        Pipeline status after start attempt.
    """
    try:
        await start_pipeline()
        pipeline = get_pipeline()
        return {
            "status": "started",
            "metrics": pipeline.metrics(),
        }
    except Exception as exc:
        logger.exception("Failed to start FPGA pipeline")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/stop")
async def stop_fpga_pipeline() -> Dict[str, Any]:
    """Stop the FPGA-accelerated ingestion pipeline.

    Returns:
        Pipeline status after stop attempt.
    """
    try:
        await stop_pipeline()
        pipeline = get_pipeline()
        return {
            "status": "stopped",
            "metrics": pipeline.metrics(),
        }
    except Exception as exc:
        logger.exception("Failed to stop FPGA pipeline")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ingest")
async def ingest_packet(packet_data: bytes) -> Dict[str, Any]:
    """Ingest a raw packet into the FPGA pipeline.

    Useful for testing and for non-DPDK packet sources.

    Args:
        packet_data: Raw packet bytes to ingest.

    Returns:
        Ingestion result with metrics.
    """
    try:
        from ...fpga_ingest import ingest_packet as do_ingest
        do_ingest(packet_data)
        pipeline = get_pipeline()
        return {
            "status": "ingested",
            "packet_size": len(packet_data),
            "metrics": pipeline.metrics(),
        }
    except Exception as exc:
        logger.exception("Failed to ingest packet")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/config")
async def get_fpga_config() -> Dict[str, Any]:
    """Get current FPGA/DPDK configuration.

    Returns:
        Current configuration settings.
    """
    return {
        "fpga": {
            "enabled": config.FPGA_ENABLED,
            "device_path": config.FPGA_DEVICE_PATH,
            "pcie_bar_offset": config.FPGA_PCIE_BAR_OFFSET,
            "hbm_base_offset": config.FPGA_HBM_BASE_OFFSET,
            "parse_fix": config.FPGA_PARSE_FIX,
            "parse_orderbook": config.FPGA_PARSE_ORDERBOOK,
            "feature_extraction": config.FPGA_FEATURE_EXTRACTION,
            "risk_checks": config.FPGA_RISK_CHECKS,
            "poll_mode": config.FPGA_POLL_MODE,
            "cpu_pinning": config.FPGA_CPU_PINNING,
            "numa_aware": config.FPGA_NUMA_AWARE,
        },
        "dpdk": {
            "enabled": config.DPDK_ENABLED,
            "memory_channels": config.DPDK_MEMORY_CHANNELS,
            "rx_queues": config.DPDK_RX_QUEUES,
            "tx_queues": config.DPDK_TX_QUEUES,
            "descriptor_rings": config.DPDK_DESCRIPTOR_RINGS,
            "hugepages": config.DPDK_HUGEPAGES,
            "hugepage_size": config.DPDK_HUGEPAGE_SIZE,
            "mtu": config.DPDK_MTU,
            "pci_devices": config.DPDK_PCI_DEVICES,
            "cpu_pinning": config.DPDK_CPU_PINNING,
        },
    }


@router.get("/health")
async def get_fpga_health() -> Dict[str, Any]:
    """Get FPGA/DPDK health check.

    Returns:
        Health status including device availability and performance metrics.
    """
    pipeline = get_pipeline()
    metrics = pipeline.metrics()

    # Determine overall health
    health_status = "healthy"
    issues = []

    if metrics["metrics"]["packets_dropped"] > 1000:
        health_status = "degraded"
        issues.append("high_packet_drop_rate")

    if metrics["pipeline"]["buffer_utilization"] > 0.9:
        health_status = "degraded"
        issues.append("high_buffer_utilization")

    if metrics["parser"]["parse_latency_ns"] > 1000000:  # >1ms
        health_status = "degraded"
        issues.append("high_parse_latency")

    return {
        "status": health_status,
        "issues": issues,
        "metrics": metrics,
    }


@router.get("/stream/status")
async def get_stream_status() -> Dict[str, Any]:
    """Get stream optimizer status and metrics.

    Returns:
        Stream optimizer metrics including batch processing and backpressure.
    """
    optimizer = get_optimizer()
    return {
        "config": {
            "enabled": config.STREAM_OPTIMIZER_ENABLED,
            "batch_size": config.STREAM_BATCH_SIZE,
            "batch_timeout_ms": config.STREAM_BATCH_TIMEOUT_MS,
            "adaptive_batching": config.STREAM_ADAPTIVE_BATCHING,
            "backpressure_threshold": config.STREAM_BACKPRESSURE_THRESHOLD,
        },
        "metrics": optimizer.metrics(),
    }


@router.post("/stream/start")
async def start_stream_optimizer() -> Dict[str, Any]:
    """Start the stream optimizer.

    Returns:
        Optimizer status after start attempt.
    """
    try:
        await start_optimizer()
        optimizer = get_optimizer()
        return {
            "status": "started",
            "metrics": optimizer.metrics(),
        }
    except Exception as exc:
        logger.exception("Failed to start stream optimizer")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/stream/stop")
async def stop_stream_optimizer() -> Dict[str, Any]:
    """Stop the stream optimizer.

    Returns:
        Optimizer status after stop attempt.
    """
    try:
        await stop_optimizer()
        optimizer = get_optimizer()
        return {
            "status": "stopped",
            "metrics": optimizer.metrics(),
        }
    except Exception as exc:
        logger.exception("Failed to stop stream optimizer")
        raise HTTPException(status_code=500, detail=str(exc))
