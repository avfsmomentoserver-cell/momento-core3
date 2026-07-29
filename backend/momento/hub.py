"""WebSocket broadcast hub.

A single async connection manager shared by every route. Messages follow the
`{"type": "...", "payload": {...}, "timestamp": "..."}` envelope the dashboards
already understand.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger("momento.hub")

# Number of recent broadcast latency samples (seconds) to retain for the
# self-awareness snapshot. Bounded so memory stays flat under load.
_LATENCY_WINDOW = 256


class Hub:
    """Tracks live sockets and fans messages out to them.

    v5 additions (backward compatible): per-type counters, bounded broadcast
    latency samples, dropped-socket accounting and a ``health()`` snapshot that
    feeds the self-awareness layer. The message envelope is unchanged.
    """

    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        # Optional per-socket source subscription. A socket absent from this
        # map (or mapped to None) is treated as a global listener and receives
        # every source-routed message, preserving pre-v5 behaviour.
        self._subscriptions: Dict[WebSocket, Optional[str]] = {}
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._sent = 0
        self._dropped = 0
        self._by_type: Dict[str, int] = {}
        self._latencies: Deque[float] = deque(maxlen=_LATENCY_WINDOW)
        self._last_broadcast_at: Optional[str] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the API event loop so sync code can schedule broadcasts."""
        self._loop = loop

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def messages_sent(self) -> int:
        return self._sent

    async def connect(self, socket: WebSocket) -> None:
        await socket.accept()
        async with self._lock:
            self._clients.add(socket)
        logger.info("websocket connected (clients=%d)", len(self._clients))

    async def disconnect(self, socket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(socket)
            self._subscriptions.pop(socket, None)
        logger.info("websocket disconnected (clients=%d)", len(self._clients))

    async def subscribe(self, socket: WebSocket, source: Optional[str]) -> None:
        """Bind a socket to a single source channel.

        Passing ``None`` restores the socket to a global listener that receives
        every source-routed message.
        """
        async with self._lock:
            self._subscriptions[socket] = source

    async def broadcast(self, message_type: str, payload: Any) -> None:
        """Send one envelope to every connected client, dropping dead sockets.

        Records fan-out latency and per-type counts for the self-awareness
        snapshot. Returns early (still cheap) when there are no clients.
        """
        self._by_type[message_type] = self._by_type.get(message_type, 0) + 1
        if not self._clients:
            return
        started = time.perf_counter()
        envelope = {
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }
        async with self._lock:
            targets: List[WebSocket] = list(self._clients)

        dead: List[WebSocket] = []
        for socket in targets:
            try:
                await socket.send_json(envelope)
                self._sent += 1
            except Exception:
                dead.append(socket)

        if dead:
            self._dropped += len(dead)
            async with self._lock:
                for socket in dead:
                    self._clients.discard(socket)

        self._latencies.append(time.perf_counter() - started)
        self._last_broadcast_at = envelope["timestamp"]

    async def broadcast_source(self, source: str, message_type: str, payload: Any) -> None:
        """Fan a message out only to sockets subscribed to ``source``.

        Global listeners (sockets with no source subscription) also receive it,
        so nothing that previously relied on a full broadcast is starved. This
        is the v5 hot-path optimisation: a client watching ``aviator`` no longer
        wakes up for ``skyward`` traffic.
        """
        self._by_type[message_type] = self._by_type.get(message_type, 0) + 1
        if not self._clients:
            return
        started = time.perf_counter()
        envelope = {
            "type": message_type,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        }
        async with self._lock:
            targets: List[WebSocket] = [
                sock
                for sock in self._clients
                if self._subscriptions.get(sock) in (None, source)
            ]

        dead: List[WebSocket] = []
        for socket in targets:
            try:
                await socket.send_json(envelope)
                self._sent += 1
            except Exception:
                dead.append(socket)

        if dead:
            self._dropped += len(dead)
            async with self._lock:
                for socket in dead:
                    self._clients.discard(socket)
                    self._subscriptions.pop(socket, None)

        self._latencies.append(time.perf_counter() - started)
        self._last_broadcast_at = envelope["timestamp"]

    def broadcast_source_threadsafe(self, source: str, message_type: str, payload: Any) -> None:
        """Schedule a source-routed broadcast from a non-async thread."""
        if self._loop is None or self._loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self.broadcast_source(source, message_type, payload), self._loop
            )
        except RuntimeError:
            logger.debug("event loop unavailable, dropping %s broadcast", message_type)

    def broadcast_threadsafe(self, message_type: str, payload: Any) -> None:
        """Schedule a broadcast from a non-async thread (the file watcher)."""
        if self._loop is None or self._loop.is_closed():
            return
        try:
            asyncio.run_coroutine_threadsafe(self.broadcast(message_type, payload), self._loop)
        except RuntimeError:
            logger.debug("event loop unavailable, dropping %s broadcast", message_type)

    def stats(self) -> Dict[str, Any]:
        return {"clients": self.client_count, "messages_sent": self._sent}

    def health(self) -> Dict[str, Any]:
        """Self-awareness snapshot of the realtime fan-out layer.

        Exposes latency (avg/p95 in milliseconds), throughput, dropped sockets
        and per-type counts so the platform can monitor and reason about its own
        realtime behaviour (v5 self-awareness foundation).
        """
        samples = sorted(self._latencies)
        avg_ms = (sum(samples) / len(samples) * 1000.0) if samples else 0.0
        if samples:
            idx = min(len(samples) - 1, int(round(0.95 * (len(samples) - 1))))
            p95_ms = samples[idx] * 1000.0
        else:
            p95_ms = 0.0
        return {
            "clients": self.client_count,
            "messages_sent": self._sent,
            "messages_dropped": self._dropped,
            "subscribed_clients": sum(1 for v in self._subscriptions.values() if v is not None),
            "broadcast_latency_ms": {
                "avg": round(avg_ms, 3),
                "p95": round(p95_ms, 3),
                "samples": len(samples),
            },
            "by_type": dict(self._by_type),
            "last_broadcast_at": self._last_broadcast_at,
        }


hub = Hub()
