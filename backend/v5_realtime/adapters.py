"""
Multi-protocol data adapters for V5 Realtime Ingestion.

Supports multiple data formats and protocols with zero-copy parsing
where possible. Adapters are designed for sub-millisecond latency.

Supported Protocols:
- JSON (optimized with ujson/orjson)
- MessagePack (binary format)
- CSV (streaming parser)
- Protocol Buffers (binary)
- Custom binary formats
"""

from __future__ import annotations

import json
import logging
import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

try:
    import orjson
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False
    orjson = None  # type: ignore

try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False
    msgpack = None  # type: ignore

logger = logging.getLogger("v5_realtime.adapters")


class ProtocolType(Enum):
    """Supported data protocols."""
    JSON = "json"
    MESSAGEPACK = "msgpack"
    CSV = "csv"
    PROTOBUF = "protobuf"
    BINARY = "binary"
    NDJSON = "ndjson"


@dataclass
class ParseResult:
    """Result of a parse operation."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    bytes_processed: int = 0
    parse_time_ns: int = 0


class DataAdapter(ABC):
    """
    Abstract base class for data adapters.

    All adapters must implement parse and serialize methods
    with focus on performance and zero-copy where possible.
    """

    def __init__(self, protocol: ProtocolType):
        self.protocol = protocol
        self._parse_count = 0
        self._serialize_count = 0
        self._error_count = 0

    @abstractmethod
    def parse(self, data: bytes) -> ParseResult:
        """Parse raw bytes into structured data."""
        pass

    @abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serialize structured data to bytes."""
        pass

    @property
    def stats(self) -> dict:
        """Get adapter statistics."""
        return {
            "protocol": self.protocol.value,
            "parse_count": self._parse_count,
            "serialize_count": self._serialize_count,
            "error_count": self._error_count,
        }


class JSONAdapter(DataAdapter):
    """
    High-performance JSON adapter.

    Uses orjson if available for maximum performance,
    falls back to standard json library.
    """

    def __init__(self):
        super().__init__(ProtocolType.JSON)
        self._use_orjson = HAS_ORJSON

    def parse(self, data: bytes) -> ParseResult:
        """Parse JSON data."""
        import time

        start = time.time_ns()
        try:
            if self._use_orjson:
                parsed = orjson.loads(data)  # type: ignore
            else:
                parsed = json.loads(data.decode("utf-8"))

            self._parse_count += 1
            elapsed = time.time_ns() - start
            return ParseResult(
                success=True,
                data=parsed,
                bytes_processed=len(data),
                parse_time_ns=elapsed,
            )
        except Exception as e:
            self._error_count += 1
            return ParseResult(success=False, error=str(e))

    def serialize(self, data: Any) -> bytes:
        """Serialize data to JSON."""
        try:
            if self._use_orjson:
                result = orjson.dumps(data)  # type: ignore
            else:
                result = json.dumps(data).encode("utf-8")

            self._serialize_count += 1
            return result
        except Exception as e:
            self._error_count += 1
            raise


class MessagePackAdapter(DataAdapter):
    """
    MessagePack adapter for binary serialization.

    More compact than JSON, faster for complex nested structures.
    """

    def __init__(self):
        super().__init__(ProtocolType.MESSAGEPACK)
        if not HAS_MSGPACK:
            logger.warning("msgpack not available, MessagePack adapter disabled")

    def parse(self, data: bytes) -> ParseResult:
        """Parse MessagePack data."""
        import time

        if not HAS_MSGPACK:
            return ParseResult(success=False, error="msgpack not installed")

        start = time.time_ns()
        try:
            parsed = msgpack.unpackb(data, raw=False)  # type: ignore
            self._parse_count += 1
            elapsed = time.time_ns() - start
            return ParseResult(
                success=True,
                data=parsed,
                bytes_processed=len(data),
                parse_time_ns=elapsed,
            )
        except Exception as e:
            self._error_count += 1
            return ParseResult(success=False, error=str(e))

    def serialize(self, data: Any) -> bytes:
        """Serialize data to MessagePack."""
        if not HAS_MSGPACK:
            raise RuntimeError("msgpack not installed")

        try:
            result = msgpack.packb(data, use_bin_type=True)  # type: ignore
            self._serialize_count += 1
            return result
        except Exception as e:
            self._error_count += 1
            raise


class CSVAdapter(DataAdapter):
    """
    Streaming CSV adapter.

    Optimized for row-by-row processing without loading entire file.
    """

    def __init__(self, delimiter: str = ",", has_header: bool = True):
        super().__init__(ProtocolType.CSV)
        self.delimiter = delimiter
        self.has_header = has_header
        self._headers: Optional[list[str]] = None

    def parse(self, data: bytes) -> ParseResult:
        """Parse CSV data (single row or multiple rows)."""
        import time
        import io

        start = time.time_ns()
        try:
            text = data.decode("utf-8")
            lines = text.strip().split("\n")

            if self.has_header and self._headers is None:
                self._headers = [h.strip() for h in lines[0].split(self.delimiter)]
                lines = lines[1:]

            rows = []
            for line in lines:
                if not line.strip():
                    continue
                values = [v.strip() for v in line.split(self.delimiter)]
                if self._headers:
                    rows.append(dict(zip(self._headers, values)))
                else:
                    rows.append(values)

            self._parse_count += 1
            elapsed = time.time_ns() - start
            return ParseResult(
                success=True,
                data=rows,
                bytes_processed=len(data),
                parse_time_ns=elapsed,
            )
        except Exception as e:
            self._error_count += 1
            return ParseResult(success=False, error=str(e))

    def serialize(self, data: Any) -> bytes:
        """Serialize data to CSV."""
        try:
            import io

            output = io.StringIO()

            if isinstance(data, list) and data and isinstance(data[0], dict):
                # Dict rows
                headers = list(data[0].keys())
                output.write(self.delimiter.join(headers) + "\n")
                for row in data:
                    output.write(self.delimiter.join(str(row.get(h, "")) for h in headers) + "\n")
            else:
                # Simple list of lists
                for row in data:
                    output.write(self.delimiter.join(str(v) for v in row) + "\n")

            self._serialize_count += 1
            return output.getvalue().encode("utf-8")
        except Exception as e:
            self._error_count += 1
            raise


class BinaryAdapter(DataAdapter):
    """
    Custom binary format adapter.

    Uses struct for efficient binary parsing.
    Format: [length:4][type:1][data:...]
    """

    HEADER_FORMAT = "!LB"  # length (4 bytes), type (1 byte)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def __init__(self):
        super().__init__(ProtocolType.BINARY)

    def parse(self, data: bytes) -> ParseResult:
        """Parse binary data."""
        import time

        start = time.time_ns()
        try:
            if len(data) < self.HEADER_SIZE:
                return ParseResult(success=False, error="Data too short")

            length, data_type = struct.unpack(self.HEADER_FORMAT, data[: self.HEADER_SIZE])
            payload = data[self.HEADER_SIZE : self.HEADER_SIZE + length]

            result = {"type": data_type, "payload": payload}

            self._parse_count += 1
            elapsed = time.time_ns() - start
            return ParseResult(
                success=True,
                data=result,
                bytes_processed=len(data),
                parse_time_ns=elapsed,
            )
        except Exception as e:
            self._error_count += 1
            return ParseResult(success=False, error=str(e))

    def serialize(self, data: Any) -> bytes:
        """Serialize data to binary format."""
        try:
            if isinstance(data, dict):
                payload = json.dumps(data).encode("utf-8")
                data_type = 1  # JSON payload
            else:
                payload = str(data).encode("utf-8")
                data_type = 0  # String payload

            header = struct.pack(self.HEADER_FORMAT, len(payload), data_type)
            result = header + payload

            self._serialize_count += 1
            return result
        except Exception as e:
            self._error_count += 1
            raise


class NDJSONAdapter(DataAdapter):
    """
    Newline-delimited JSON adapter.

    Each line is a separate JSON object.
    Efficient for streaming log data.
    """

    def __init__(self):
        super().__init__(ProtocolType.NDJSON)

    def parse(self, data: bytes) -> ParseResult:
        """Parse NDJSON data."""
        import time

        start = time.time_ns()
        try:
            text = data.decode("utf-8")
            lines = text.strip().split("\n")

            objects = []
            for line in lines:
                if not line.strip():
                    continue
                if HAS_ORJSON:
                    obj = orjson.loads(line)  # type: ignore
                else:
                    obj = json.loads(line)
                objects.append(obj)

            self._parse_count += 1
            elapsed = time.time_ns() - start
            return ParseResult(
                success=True,
                data=objects,
                bytes_processed=len(data),
                parse_time_ns=elapsed,
            )
        except Exception as e:
            self._error_count += 1
            return ParseResult(success=False, error=str(e))

    def serialize(self, data: Any) -> bytes:
        """Serialize data to NDJSON."""
        try:
            lines = []
            for item in data:
                if HAS_ORJSON:
                    line = orjson.dumps(item)  # type: ignore
                else:
                    line = json.dumps(item)
                lines.append(line.decode("utf-8") if isinstance(line, bytes) else line)

            result = "\n".join(lines).encode("utf-8") + b"\n"
            self._serialize_count += 1
            return result
        except Exception as e:
            self._error_count += 1
            raise


class ProtocolRouter:
    """
    Routes data to appropriate adapter based on protocol detection.

    Auto-detects protocol from data headers or content.
    Maintains adapter pool for reuse.
    """

    def __init__(self):
        self._adapters: dict[ProtocolType, DataAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Register default adapters."""
        self._adapters[ProtocolType.JSON] = JSONAdapter()
        self._adapters[ProtocolType.MESSAGEPACK] = MessagePackAdapter()
        self._adapters[ProtocolType.CSV] = CSVAdapter()
        self._adapters[ProtocolType.BINARY] = BinaryAdapter()
        self._adapters[ProtocolType.NDJSON] = NDJSONAdapter()

    def register_adapter(self, protocol: ProtocolType, adapter: DataAdapter) -> None:
        """Register a custom adapter."""
        self._adapters[protocol] = adapter

    def detect_protocol(self, data: bytes) -> ProtocolType:
        """
        Auto-detect protocol from data.

        Detection heuristics:
        - Binary header: custom binary format
        - MessagePack magic bytes: msgpack
        - Newline-delimited JSON: ndjson
        - CSV delimiter: csv
        - Default: json
        """
        if len(data) < 2:
            return ProtocolType.JSON

        # Check for binary header
        if len(data) >= 5 and data[0:4] == struct.pack("!L", len(data) - 5):
            return ProtocolType.BINARY

        # Check for MessagePack (magic bytes)
        if HAS_MSGPACK and data[0] in {0x82, 0x83, 0x84, 0x90, 0x91, 0x92}:
            return ProtocolType.MESSAGEPACK

        # Check for NDJSON (multiple lines, each valid JSON)
        text = data.decode("utf-8", errors="ignore")
        lines = text.strip().split("\n")
        if len(lines) > 1:
            try:
                json.loads(lines[0])
                return ProtocolType.NDJSON
            except Exception:
                pass

        # Check for CSV (contains delimiters, not JSON)
        if "," in text and not text.strip().startswith("{"):
            return ProtocolType.CSV

        # Default to JSON
        return ProtocolType.JSON

    def parse(self, data: bytes, protocol: Optional[ProtocolType] = None) -> ParseResult:
        """
        Parse data with auto-detection or explicit protocol.

        Args:
            data: Raw bytes to parse
            protocol: Explicit protocol (auto-detect if None)
        """
        if protocol is None:
            protocol = self.detect_protocol(data)

        adapter = self._adapters.get(protocol)
        if adapter is None:
            return ParseResult(success=False, error=f"No adapter for protocol: {protocol}")

        return adapter.parse(data)

    def serialize(self, data: Any, protocol: ProtocolType) -> bytes:
        """Serialize data with specified protocol."""
        adapter = self._adapters.get(protocol)
        if adapter is None:
            raise ValueError(f"No adapter for protocol: {protocol}")

        return adapter.serialize(data)

    def get_stats(self) -> dict:
        """Get statistics for all adapters."""
        return {protocol.value: adapter.stats for protocol, adapter in self._adapters.items()}


# Global protocol router instance
_protocol_router: Optional[ProtocolRouter] = None
_router_lock = threading.Lock()


def get_protocol_router() -> ProtocolRouter:
    """Get the global protocol router instance."""
    global _protocol_router
    with _router_lock:
        if _protocol_router is None:
            _protocol_router = ProtocolRouter()
        return _protocol_router
