"""
V5 Multi-Protocol Adapters

Protocol adapters for FIX, WebSocket, HTTP, gRPC, and custom protocols.
Support for 5+ protocols with schema validation and lossless conversion.
"""

from .adapter_base import ProtocolAdapter
from .fix_adapter import FIXAdapter
from .websocket_adapter import WebSocketAdapter
from .http_adapter import HTTPAdapter
from .grpc_adapter import GRPCAdapter
from .custom_adapter import CustomAdapter

__all__ = [
    "ProtocolAdapter",
    "FIXAdapter",
    "WebSocketAdapter",
    "HTTPAdapter",
    "GRPCAdapter",
    "CustomAdapter",
]
