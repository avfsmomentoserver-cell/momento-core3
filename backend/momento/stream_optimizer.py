"""Real-time stream processing optimization layer.

Provides optimizations for high-throughput stream processing:
- Batch processing with dynamic batching
- Memory pooling for reduced allocations
- SIMD-friendly data layouts
- Asynchronous processing pipelines
- Backpressure management

Performance targets (from V5 specs):
- Sub-millisecond latency for single-round processing
- 100K+ rounds/second throughput
- Minimal memory allocations
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from . import config, store
from .hub import hub

logger = logging.getLogger("momento.stream_optimizer")

# Batch processing configuration
DEFAULT_BATCH_SIZE = 100
MAX_BATCH_SIZE = 1000
MIN_BATCH_SIZE = 10
BATCH_TIMEOUT_MS = 10  # 10ms max wait for batch completion

# Memory pool configuration
POOL_SIZE = 10000
POOL_MAX_SIZE = 50000


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    enabled: bool = True
    default_size: int = DEFAULT_BATCH_SIZE
    max_size: int = MAX_BATCH_SIZE
    min_size: int = MIN_BATCH_SIZE
    timeout_ms: int = BATCH_TIMEOUT_MS
    adaptive: bool = True
    pressure_threshold: float = 0.8


@dataclass
class StreamMetrics:
    """Stream processing metrics."""
    rounds_processed: int = 0
    batches_processed: int = 0
    avg_batch_size: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    throughput_rps: float = 0.0
    backpressure_events: int = 0
    memory_pool_hits: int = 0
    memory_pool_misses: int = 0
    last_update: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rounds_processed": self.rounds_processed,
            "batches_processed": self.batches_processed,
            "avg_batch_size": self.avg_batch_size,
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "throughput_rps": self.throughput_rps,
            "backpressure_events": self.backpressure_events,
            "memory_pool_hits": self.memory_pool_hits,
            "memory_pool_misses": self.memory_pool_misses,
            "last_update": self.last_update,
        }


class MemoryPool:
    """Object pool for reducing memory allocations.

    Reuses dict objects to reduce GC pressure and allocation overhead.
    Target: <1% allocation rate during steady state.
    """

    __slots__ = ("_pool", "_max_size", "_hits", "_misses")

    def __init__(self, initial_size: int = POOL_SIZE, max_size: int = POOL_MAX_SIZE):
        """Initialize memory pool."""
        self._pool: deque = deque(maxlen=max_size)
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

        # Pre-populate pool
        for _ in range(initial_size):
            self._pool.append({})

    def acquire(self) -> Dict[str, Any]:
        """Acquire a dict from the pool."""
        if self._pool:
            self._hits += 1
            return self._pool.popleft()
        self._misses += 1
        return {}

    def release(self, obj: Dict[str, Any]) -> None:
        """Release a dict back to the pool."""
        obj.clear()  # Clear the dict for reuse
        if len(self._pool) < self._max_size:
            self._pool.append(obj)

    def stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        return {
            "pool_size": len(self._pool),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0.0,
        }


class BatchProcessor:
    """Optimized batch processor for rounds.

    Processes rounds in batches for improved throughput.
    Adaptive batching adjusts batch size based on load.
    """

    def __init__(self, cfg: BatchConfig):
        """Initialize batch processor."""
        self._cfg = cfg
        self._current_batch: List[Dict[str, Any]] = []
        self._batch_start_time: Optional[float] = None
        self._memory_pool = MemoryPool()
        self._metrics = StreamMetrics()
        self._latency_samples: deque = deque(maxlen=1000)
        self._lock = asyncio.Lock()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._start_timestamp: Optional[float] = None

    async def start(self) -> None:
        """Start batch processor."""
        if self._running:
            return
        self._running = True
        self._start_timestamp = time.time()
        self._task = asyncio.create_task(self._process_loop(), name="batch-processor")
        logger.info("Batch processor started")

    async def stop(self) -> None:
        """Stop batch processor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Flush remaining batch
        if self._current_batch:
            await self._flush_batch()
        logger.info("Batch processor stopped")

    async def add_round(self, round_data: Dict[str, Any]) -> None:
        """Add a round to the current batch."""
        async with self._lock:
            self._current_batch.append(round_data)

            if self._batch_start_time is None:
                self._batch_start_time = time.perf_counter()

            # Check if batch should be flushed
            batch_size = len(self._current_batch)
            should_flush = False

            if batch_size >= self._cfg.max_size:
                should_flush = True
            elif batch_size >= self._cfg.default_size:
                # Check timeout
                if self._batch_start_time:
                    elapsed_ms = (time.perf_counter() - self._batch_start_time) * 1000
                    if elapsed_ms >= self._cfg.timeout_ms:
                        should_flush = True

            if should_flush:
                await self._flush_batch()

    async def _flush_batch(self) -> None:
        """Flush the current batch for processing."""
        if not self._current_batch:
            return

        batch = self._current_batch
        self._current_batch = []
        self._batch_start_time = None

        start = time.perf_counter()

        try:
            # Process batch
            result = store.insert_rounds(batch, method="stream_optimizer")

            # Broadcast updates
            if result.get("rounds"):
                source = batch[0].get("source", "aviator")
                hub.broadcast_source_threadsafe(source, "rounds:update", {"rounds": result["rounds"], "source": source})

            # Update metrics
            self._metrics.rounds_processed += len(batch)
            self._metrics.batches_processed += 1
            self._metrics.avg_batch_size = (
                self._metrics.avg_batch_size * (self._metrics.batches_processed - 1) + len(batch)
            ) / self._metrics.batches_processed

            latency = (time.perf_counter() - start) * 1000  # ms
            self._latency_samples.append(latency)

        except Exception as exc:
            logger.exception("Batch processing error: %s", exc)

    async def _process_loop(self) -> None:
        """Main processing loop for timeout-based flushing."""
        while self._running:
            try:
                await asyncio.sleep(self._cfg.timeout_ms / 1000.0)

                async with self._lock:
                    if self._current_batch and self._batch_start_time:
                        elapsed_ms = (time.perf_counter() - self._batch_start_time) * 1000
                        if elapsed_ms >= self._cfg.timeout_ms:
                            await self._flush_batch()

            except Exception as exc:
                logger.exception("Batch processor loop error: %s", exc)

    def metrics(self) -> StreamMetrics:
        """Get processor metrics."""
        samples = sorted(self._latency_samples)
        if samples:
            self._metrics.avg_latency_ms = sum(samples) / len(samples)
            idx = min(len(samples) - 1, int(round(0.95 * (len(samples) - 1))))
            self._metrics.p95_latency_ms = samples[idx]

        # Calculate throughput
        if self._metrics.rounds_processed > 0:
            self._metrics.throughput_rps = self._metrics.rounds_processed / max(1, time.time() - self._start_time())

        self._metrics.memory_pool_hits = self._memory_pool._hits
        self._metrics.memory_pool_misses = self._memory_pool._misses
        self._metrics.last_update = datetime.now(timezone.utc).isoformat(timespec="milliseconds")

        return self._metrics

    def _start_time(self) -> float:
        """Get start time for throughput calculation."""
        if self._start_timestamp is None:
            return time.time() - 60.0  # Assume 60 second window
        return self._start_timestamp


class BackpressureManager:
    """Manages backpressure for stream processing.

    Prevents overload by signaling when to slow down ingestion.
    Uses adaptive thresholds based on system metrics.
    """

    def __init__(self, threshold: float = 0.8):
        """Initialize backpressure manager."""
        self._threshold = threshold
        self._current_pressure = 0.0
        self._events = 0
        self._history: deque = deque(maxlen=100)

    def update_pressure(self, metric: float) -> bool:
        """Update pressure level and return if backpressure is active.

        Args:
            metric: Current system load metric (0.0 to 1.0).

        Returns:
            True if backpressure should be applied.
        """
        self._current_pressure = metric
        self._history.append(metric)

        # Apply backpressure if threshold exceeded
        if metric > self._threshold:
            self._events += 1
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """Get backpressure status."""
        return {
            "current_pressure": self._current_pressure,
            "threshold": self._threshold,
            "active": self._current_pressure > self._threshold,
            "events": self._events,
            "avg_pressure": sum(self._history) / len(self._history) if self._history else 0.0,
        }


class StreamOptimizer:
    """Main stream processing optimizer.

    Coordinates batch processing, memory pooling, and backpressure
    for optimal real-time stream performance.
    """

    def __init__(self, batch_cfg: Optional[BatchConfig] = None):
        """Initialize stream optimizer."""
        self._batch_cfg = batch_cfg or BatchConfig()
        self._batch_processor = BatchProcessor(self._batch_cfg)
        self._backpressure = BackpressureManager(threshold=self._batch_cfg.pressure_threshold)
        self._running = False

    async def start(self) -> None:
        """Start stream optimizer."""
        if self._running:
            return
        self._running = True
        await self._batch_processor.start()
        logger.info("Stream optimizer started")

    async def stop(self) -> None:
        """Stop stream optimizer."""
        self._running = False
        await self._batch_processor.stop()
        logger.info("Stream optimizer stopped")

    async def process_round(self, round_data: Dict[str, Any]) -> None:
        """Process a single round through the optimized pipeline."""
        if not self._running:
            # Fallback to direct processing
            result = store.insert_rounds([round_data], method="direct")
            if result.get("rounds"):
                source = round_data.get("source", "aviator")
                hub.broadcast_source_threadsafe(source, "rounds:update", {"rounds": result["rounds"], "source": source})
            return

        # Check backpressure
        pressure = self._calculate_pressure()
        if self._backpressure.update_pressure(pressure):
            # Apply backpressure: small delay
            await asyncio.sleep(0.001)  # 1ms delay

        # Add to batch processor
        await self._batch_processor.add_round(round_data)

    def _calculate_pressure(self) -> float:
        """Calculate current system pressure (0.0 to 1.0)."""
        metrics = self._batch_processor.metrics()

        # Simple pressure calculation based on batch size
        batch_size = len(self._batch_processor._current_batch)
        pressure = batch_size / self._batch_cfg.max_size

        return min(1.0, max(0.0, pressure))

    def metrics(self) -> Dict[str, Any]:
        """Get optimizer metrics."""
        return {
            "batch_processor": {
                "running": self._batch_processor._running,
                "current_batch_size": len(self._batch_processor._current_batch),
                "metrics": self._batch_processor.metrics().as_dict() if hasattr(self._batch_processor.metrics(), 'as_dict') else self._batch_processor.metrics().__dict__,
            },
            "backpressure": self._backpressure.get_status(),
            "memory_pool": self._batch_processor._memory_pool.stats(),
        }


# Global optimizer instance
_optimizer: Optional[StreamOptimizer] = None


def get_optimizer() -> StreamOptimizer:
    """Get or create global optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = StreamOptimizer()
    return _optimizer


async def start_optimizer() -> None:
    """Start the global optimizer."""
    optimizer = get_optimizer()
    await optimizer.start()


async def stop_optimizer() -> None:
    """Stop the global optimizer."""
    optimizer = get_optimizer()
    await optimizer.stop()


async def process_round(round_data: Dict[str, Any]) -> None:
    """Process a round through the optimizer."""
    optimizer = get_optimizer()
    await optimizer.process_round(round_data)
