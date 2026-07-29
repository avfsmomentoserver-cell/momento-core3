"""Runtime configuration for Momento Core.

All values are overridable through environment variables so that local,
staging and production deployments never require code edits.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict


def _root() -> Path:
    """Resolve the backend root directory (the folder containing `momento/`)."""
    return Path(__file__).resolve().parent.parent


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw).expanduser().resolve() if raw else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


ROOT = _root()

DATA_DIR = _env_path("MOMENTO_DATA_DIR", ROOT / "data")
DATABASE_PATH = _env_path("MOMENTO_DATABASE_PATH", DATA_DIR / "momento.db")
INBOX_DIR = _env_path("MOMENTO_INBOX_DIR", DATA_DIR / "inbox")
PROCESSED_DIR = _env_path("MOMENTO_PROCESSED_DIR", DATA_DIR / "processed")
FAILED_DIR = _env_path("MOMENTO_FAILED_DIR", DATA_DIR / "failed")
DOWNLOADS_DIR = _env_path("MOMENTO_DOWNLOADS_DIR", Path.home() / "Downloads")
LOG_DIR = _env_path("MOMENTO_LOG_DIR", ROOT / "logs")

# Static artefacts served to the dashboards (step docs + source bundles).
DIST_DIR = _env_path("MOMENTO_DIST_DIR", ROOT.parent / "downloads")
DOCS_DIR = _env_path("MOMENTO_DOCS_DIR", ROOT.parent / "docs")

API_HOST = os.environ.get("MOMENTO_API_HOST", "0.0.0.0")
API_PORT = _env_int("MOMENTO_API_PORT", 8000)

SECRET_KEY = os.environ.get("MOMENTO_SECRET_KEY", "momento-core-local-development-key")
TOKEN_TTL_SECONDS = _env_int("MOMENTO_TOKEN_TTL", 60 * 60 * 12)

# Operator bootstrap account, created on first boot if the table is empty.
BOOTSTRAP_OPERATOR_EMAIL = os.environ.get("MOMENTO_OPERATOR_EMAIL", "operator@momento.local")
BOOTSTRAP_OPERATOR_PASSWORD = os.environ.get("MOMENTO_OPERATOR_PASSWORD", "momento")

WATCHER_ENABLED = _env_bool("MOMENTO_WATCHER_ENABLED", True)
WATCHER_INTERVAL = _env_float("MOMENTO_WATCHER_INTERVAL", 2.0)
WATCH_DOWNLOADS = _env_bool("MOMENTO_WATCH_DOWNLOADS", True)

FEED_ENABLED_ON_BOOT = _env_bool("MOMENTO_FEED_AUTOSTART", True)

# FPGA/DPDK Real-time Ingestion Configuration (V5)
FPGA_ENABLED = _env_bool("MOMENTO_FPGA_ENABLED", False)
FPGA_DEVICE_PATH = os.environ.get("MOMENTO_FPGA_DEVICE", "/dev/xfpga0")
FPGA_PCIE_BAR_OFFSET = _env_int("MOMENTO_FPGA_PCIE_OFFSET", 0)
FPGA_HBM_BASE_OFFSET = _env_int("MOMENTO_FPGA_HBM_OFFSET", 0)
FPGA_PARSE_FIX = _env_bool("MOMENTO_FPGA_PARSE_FIX", True)
FPGA_PARSE_ORDERBOOK = _env_bool("MOMENTO_FPGA_PARSE_ORDERBOOK", True)
FPGA_FEATURE_EXTRACTION = _env_bool("MOMENTO_FPGA_FEATURES", True)
FPGA_RISK_CHECKS = _env_bool("MOMENTO_FPGA_RISK_CHECKS", True)
FPGA_POLL_MODE = _env_bool("MOMENTO_FPGA_POLL_MODE", True)
FPGA_CPU_PINNING = _env_bool("MOMENTO_FPGA_CPU_PINNING", True)
FPGA_NUMA_AWARE = _env_bool("MOMENTO_FPGA_NUMA_AWARE", True)

DPDK_ENABLED = _env_bool("MOMENTO_DPDK_ENABLED", False)
DPDK_MEMORY_CHANNELS = _env_int("MOMENTO_DPDK_MEM_CHANNELS", 4)
DPDK_RX_QUEUES = _env_int("MOMENTO_DPDK_RX_QUEUES", 16)
DPDK_TX_QUEUES = _env_int("MOMENTO_DPDK_TX_QUEUES", 16)
DPDK_DESCRIPTOR_RINGS = _env_int("MOMENTO_DPDK_DESCRIPTORS", 4096)
DPDK_HUGEPAGES = _env_bool("MOMENTO_DPDK_HUGEPAGES", True)
DPDK_HUGEPAGE_SIZE = _env_int("MOMENTO_DPDK_HUGEPAGE_SIZE", 1024)  # 1GB
DPDK_MTU = _env_int("MOMENTO_DPDK_MTU", 9000)
DPDK_PCI_DEVICES = os.environ.get("MOMENTO_DPDK_PCI_DEVICES", "").split(",") if os.environ.get("MOMENTO_DPDK_PCI_DEVICES") else []
DPDK_CPU_PINNING = _env_bool("MOMENTO_DPDK_CPU_PINNING", True)

# V5 Free-Tier Configuration
DEPLOYMENT_MODE = os.environ.get("MOMENTO_DEPLOYMENT_MODE", "local")  # local, cloud
CPU_ONLY_MODE = _env_bool("MOMENTO_CPU_ONLY_MODE", True)  # Force CPU-only for free tier
USE_LOCAL_DATABASE = _env_bool("MOMENTO_USE_LOCAL_DATABASE", True)  # Use local Docker databases
USE_LOCAL_REDIS = _env_bool("MOMENTO_USE_LOCAL_REDIS", True)  # Use local Docker Redis

# Local Database Configuration (Free-Tier)
LOCAL_POSTGRES_HOST = os.environ.get("MOMENTO_POSTGRES_HOST", "localhost")
LOCAL_POSTGRES_PORT = _env_int("MOMENTO_POSTGRES_PORT", 5432)
LOCAL_POSTGRES_USER = os.environ.get("MOMENTO_POSTGRES_USER", "momento")
LOCAL_POSTGRES_PASSWORD = os.environ.get("MOMENTO_POSTGRES_PASSWORD", "momento_password")
LOCAL_POSTGRES_DATABASE = os.environ.get("MOMENTO_POSTGRES_DATABASE", "momento")

# Local Redis Configuration (Free-Tier)
LOCAL_REDIS_HOST = os.environ.get("MOMENTO_REDIS_HOST", "localhost")
LOCAL_REDIS_PORT = _env_int("MOMENTO_REDIS_PORT", 6379)
LOCAL_REDIS_PASSWORD = os.environ.get("MOMENTO_REDIS_PASSWORD", "redis_password")
LOCAL_REDIS_DB = _env_int("MOMENTO_REDIS_DB", 0)

# CPU Intelligence Configuration (Free-Tier)
CPU_ML_ENABLED = _env_bool("MOMENTO_CPU_ML_ENABLED", True)
CPU_ML_FRAMEWORK = os.environ.get("MOMENTO_CPU_ML_FRAMEWORK", "onnx")  # onnx, sklearn
CPU_ML_QUANTIZATION = _env_bool("MOMENTO_CPU_ML_QUANTIZATION", True)
CPU_ML_THREADS = _env_int("MOMENTO_CPU_ML_THREADS", 4)
CPU_ML_BATCH_SIZE = _env_int("MOMENTO_CPU_ML_BATCH_SIZE", 32)

# Stream Optimizer Configuration (V5)
STREAM_OPTIMIZER_ENABLED = _env_bool("MOMENTO_STREAM_OPTIMIZER_ENABLED", True)
STREAM_BATCH_SIZE = _env_int("MOMENTO_STREAM_BATCH_SIZE", 100)
STREAM_BATCH_TIMEOUT_MS = _env_int("MOMENTO_STREAM_BATCH_TIMEOUT", 10)
STREAM_ADAPTIVE_BATCHING = _env_bool("MOMENTO_STREAM_ADAPTIVE_BATCHING", True)
STREAM_BACKPRESSURE_THRESHOLD = _env_float("MOMENTO_STREAM_BACKPRESSURE_THRESHOLD", 0.8)

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "MOMENTO_CORS_ORIGINS",
        "http://localhost:5173,http://localhost:4173,http://localhost:3000,http://127.0.0.1:5173,"
        "http://localhost:8080,http://127.0.0.1:8080",
    ).split(",")
    if o.strip()
]
ALLOW_ALL_CORS = _env_bool("MOMENTO_CORS_ALLOW_ALL", True)


@dataclass
class AnalysisSettings:
    """Tunable analysis parameters, persisted in the settings table."""

    session_gap_seconds: int = 300  # 5 minutes - continuous rounds with <5min gap stay in same session
    mega_session_gap_seconds: int = 172800  # 48 hours for mega pressure tracker
    ladder_min_length: int = 3
    ladder_tolerance: float = 0.06
    collapse_min_length: int = 3
    low_band_threshold: float = 2.0
    ignition_threshold: float = 5.0
    moonshot_threshold: float = 10.0
    mega_moonshot_threshold: float = 50.0
    shelf_window: int = 12
    shelf_variance: float = 0.35
    bait_spike_ratio: float = 2.2
    resistance_bins: int = 24
    forecast_horizon: int = 5
    volatility_window: int = 30
    dna_window: int = 8
    dna_tolerance: float = 0.85
    house_edge_prior: float = 0.03
    confidence_floor: float = 0.05
    max_rounds_buffer: int = 5000

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def merge(self, values: Dict[str, Any]) -> "AnalysisSettings":
        """Return a copy with validated overrides applied."""
        data = self.as_dict()
        for key, value in values.items():
            if key not in data or value is None:
                continue
            current = data[key]
            try:
                data[key] = int(value) if isinstance(current, int) else float(value)
            except (TypeError, ValueError):
                continue
        return AnalysisSettings(**data)


@dataclass
class RuntimeToggles:
    """Feature switches the operator can flip live from Master Settings."""

    engines_enabled: bool = True
    signal_engine: bool = True
    market_engine: bool = True
    forecast_engine: bool = True
    linguistics_engine: bool = True
    ceiling_analyzer: bool = True
    gap_swing_analyzer: bool = True
    ml_predictions: bool = True
    autopilot_engine: bool = True
    broadcast_enabled: bool = True
    
    # Advanced moonshot signals
    moonshot_eta: bool = True
    exhaustion_calculator: bool = True
    sweet_spot_signal: bool = True
    chase_readiness: bool = True
    pressure_exhaustion: bool = True
    compression_exhaustion: bool = True
    ceiling_exhaustion: bool = True

    def as_dict(self) -> Dict[str, bool]:
        return asdict(self)

    def merge(self, values: Dict[str, Any]) -> "RuntimeToggles":
        data = self.as_dict()
        for key, value in values.items():
            if key in data and value is not None:
                data[key] = bool(value)
        return RuntimeToggles(**data)


@dataclass
class BacktestingSettings:
    """Backtesting configuration parameters for the Investigation Suite."""

    default_session_gap: int = 300
    default_window_size: int = 600
    min_session_rounds: int = 10
    accuracy_threshold: float = 0.5
    confidence_threshold: float = 0.7
    max_backtest_rounds: int = 10000
    enable_parallel: bool = True
    parallel_workers: int = 4

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def merge(self, values: Dict[str, Any]) -> "BacktestingSettings":
        data = self.as_dict()
        for key, value in values.items():
            if key not in data or value is None:
                continue
            current = data[key]
            try:
                if isinstance(current, bool):
                    data[key] = bool(value)
                else:
                    data[key] = int(value) if isinstance(current, int) else float(value)
            except (TypeError, ValueError):
                continue
        return BacktestingSettings(**data)


@dataclass
class DashboardSettings:
    """Dashboard UI/UX configuration."""

    default_rounds_limit: int = 400
    refresh_interval_rounds: int = 2000
    refresh_interval_analysis: int = 5000
    refresh_interval_slow: int = 30000
    enable_animations: bool = True
    compact_mode: bool = False
    show_timestamps: bool = True
    show_bands: bool = True
    show_points: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def merge(self, values: Dict[str, Any]) -> "DashboardSettings":
        data = self.as_dict()
        for key, value in values.items():
            if key not in data or value is None:
                continue
            current = data[key]
            try:
                if isinstance(current, bool):
                    data[key] = bool(value)
                else:
                    data[key] = int(value) if isinstance(current, int) else float(value)
            except (TypeError, ValueError):
                continue
        return DashboardSettings(**data)


@dataclass
class FPGAParseSettings:
    """FPGA-accelerated parsing configuration (V5)."""

    enabled: bool = False
    device_path: str = "/dev/xfpga0"
    pcie_bar_offset: int = 0
    hbm_base_offset: int = 0
    parse_fix: bool = True
    parse_orderbook: bool = True
    feature_extraction: bool = True
    risk_checks: bool = True
    poll_mode: bool = True
    cpu_pinning: bool = True
    numa_aware: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def merge(self, values: Dict[str, Any]) -> "FPGAParseSettings":
        data = self.as_dict()
        for key, value in values.items():
            if key not in data or value is None:
                continue
            current = data[key]
            try:
                if isinstance(current, bool):
                    data[key] = bool(value)
                elif isinstance(current, str):
                    data[key] = str(value)
                else:
                    data[key] = int(value) if isinstance(current, int) else float(value)
            except (TypeError, ValueError):
                continue
        return FPGAParseSettings(**data)


@dataclass
class DPDKSettings:
    """DPDK networking configuration (V5)."""

    enabled: bool = False
    memory_channels: int = 4
    rx_queues: int = 16
    tx_queues: int = 16
    descriptor_rings: int = 4096
    hugepages: bool = True
    hugepage_size: int = 1024  # 1GB
    mtu: int = 9000
    pci_devices: list[str] = None
    cpu_pinning: bool = True

    def __post_init__(self):
        if self.pci_devices is None:
            self.pci_devices = []

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    def merge(self, values: Dict[str, Any]) -> "DPDKSettings":
        data = self.as_dict()
        for key, value in values.items():
            if key not in data or value is None:
                continue
            current = data[key]
            try:
                if isinstance(current, bool):
                    data[key] = bool(value)
                elif isinstance(current, str):
                    data[key] = str(value)
                elif isinstance(current, list):
                    if isinstance(value, str):
                        data[key] = [v.strip() for v in value.split(",") if v.strip()]
                    else:
                        data[key] = list(value)
                else:
                    data[key] = int(value) if isinstance(current, int) else float(value)
            except (TypeError, ValueError):
                continue
        return DPDKSettings(**data)


@dataclass
class StreamOptimizerSettings:
    """Stream processing optimization configuration (V5)."""

    enabled: bool = True
    batch_size: int = 100
    max_batch_size: int = 1000
    min_batch_size: int = 10
    batch_timeout_ms: int = 10
    adaptive: bool = True
    pressure_threshold: float = 0.8

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def merge(self, values: Dict[str, Any]) -> "StreamOptimizerSettings":
        data = self.as_dict()
        for key, value in values.items():
            if key not in data or value is None:
                continue
            current = data[key]
            try:
                if isinstance(current, bool):
                    data[key] = bool(value)
                elif isinstance(current, str):
                    data[key] = str(value)
                else:
                    data[key] = int(value) if isinstance(current, int) else float(value)
            except (TypeError, ValueError):
                continue
        return StreamOptimizerSettings(**data)


DEFAULT_SOURCES: list[dict[str, Any]] = [
    {"id": "aviator", "name": "Aviator", "icon": "plane", "active": True},
    {"id": "jetx", "name": "JetX", "icon": "rocket", "active": True},
    {"id": "crash", "name": "Crash", "icon": "zap", "active": True},
    {"id": "spaceman", "name": "Spaceman", "icon": "orbit", "active": False},
]


def ensure_directories() -> None:
    """Create every directory the platform writes to."""
    for directory in (
        DATA_DIR,
        DATABASE_PATH.parent,
        INBOX_DIR,
        PROCESSED_DIR,
        FAILED_DIR,
        LOG_DIR,
        DIST_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)


def describe() -> Dict[str, Any]:
    """Human readable configuration snapshot for the /health endpoint."""
    return {
        "database_path": str(DATABASE_PATH),
        "inbox_dir": str(INBOX_DIR),
        "processed_dir": str(PROCESSED_DIR),
        "failed_dir": str(FAILED_DIR),
        "downloads_dir": str(DOWNLOADS_DIR),
        "log_dir": str(LOG_DIR),
        "dist_dir": str(DIST_DIR),
        "api_host": API_HOST,
        "api_port": API_PORT,
        "watcher_enabled": WATCHER_ENABLED,
        "watch_downloads": WATCH_DOWNLOADS,
        "cors_origins": "*" if ALLOW_ALL_CORS else CORS_ORIGINS,
    }


def dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), default=str)
