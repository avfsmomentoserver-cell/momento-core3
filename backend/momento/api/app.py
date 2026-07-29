"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .. import __version__, auth, config, db, plugins
from ..feed import autostart_if_configured, feed
from ..fpga_ingest import get_pipeline
from ..hub import hub
from ..stream_optimizer import get_optimizer
from ..watcher import watcher
# Security imports disabled to prevent CORS issues
SECURITY_AVAILABLE = False
security_config = None
from .routes import analysis as analysis_routes
from .routes import backtest as backtest_routes
from .routes import backtest_enhanced as backtest_enhanced_routes
from .routes import backup as backup_routes
from .routes import core as core_routes
from .routes import engines as engines_routes
from .routes import fpga as fpga_routes
from .routes import features as features_routes
from .routes import forecasts as forecast_routes
try:
    from .routes import gpu as gpu_routes
    GPU_ROUTES_AVAILABLE = True
except ImportError:
    GPU_ROUTES_AVAILABLE = False
    gpu_routes = None
from .routes import ingest as ingest_routes
from .routes import market as market_routes
from .routes import mega_pressure as mega_pressure_routes
from .routes import platform as platform_routes
from .routes import rounds as rounds_routes
try:
    from .routes import scopes as scopes_routes
    SCOPES_ROUTES_AVAILABLE = True
except ImportError:
    SCOPES_ROUTES_AVAILABLE = False
    scopes_routes = None
from .routes import users as users_routes
from .routes import vocabulary as vocabulary_routes
try:
    from .routes import v5_admin as v5_admin_routes
    V5_ADMIN_ROUTES_AVAILABLE = True
except ImportError:
    V5_ADMIN_ROUTES_AVAILABLE = False
    v5_admin_routes = None
from .routes import ws as ws_routes
try:
    from .scope_gateway import ScopeGatewayMiddleware
    SCOPE_GATEWAY_AVAILABLE = True
except ImportError:
    SCOPE_GATEWAY_AVAILABLE = False
    ScopeGatewayMiddleware = None

logger = logging.getLogger("momento")

API_PREFIX = "/api/v1"


def configure_logging() -> None:
    """Console + rotating file logging into `logs/api.log`."""
    config.ensure_directories()
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s :: %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            config.LOG_DIR / "api.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except OSError as exc:
        logger.warning("file logging unavailable: %s", exc)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Boot every subsystem, then tear it down cleanly."""
    configure_logging()
    logger.info("Momento Core %s starting", __version__)

    db.init_db()
    auth.bootstrap()
    
    # Initialize multi-scope authentication system
    try:
        from ..scope_init import initialize_multi_scope_schema
        initialize_multi_scope_schema()
    except Exception as exc:
        logger.warning("Multi-scope initialization failed: %s", exc)
    
    hub.bind_loop(asyncio.get_running_loop())

    # V5 Security: Initialize security monitoring
    if SECURITY_AVAILABLE and security_config:
        logger.info("V5 Security Level: %s", security_config.level)
        if security_config.monitoring.anomaly_detection_enabled:
            logger.info("Security anomaly detection enabled")
        if security_config.monitoring.intrusion_detection_enabled:
            logger.info("Intrusion detection enabled")
        if security_config.authentication.mfa_enabled:
            logger.info("Multi-factor authentication enabled")
    else:
        logger.info("Security modules not available, running in basic mode")

    if config.WATCHER_ENABLED:
        watcher.start()

    await autostart_if_configured()

    # Start FPGA pipeline if enabled
    if config.FPGA_ENABLED or config.DPDK_ENABLED:
        fpga_pipeline = get_pipeline()
        await fpga_pipeline.start()
        logger.info("FPGA-accelerated ingestion pipeline started")

    # Start stream optimizer if enabled
    if config.STREAM_OPTIMIZER_ENABLED:
        stream_optimizer = get_optimizer()
        await stream_optimizer.start()
        logger.info("Stream optimizer started")

    # Initialize GPU intelligence if available
    try:
        from gpu_intelligence.integration import initialize_gpu_intelligence

        gpu_initialized = initialize_gpu_intelligence()
        if gpu_initialized:
            logger.info("GPU intelligence subsystem initialized")
        else:
            logger.info("GPU not available, CPU-only mode")
    except ImportError:
        logger.debug("GPU intelligence module not available")
    except Exception as exc:
        logger.warning("GPU intelligence initialization failed: %s", exc)

    # Initialize CPU intelligence for V5 free-tier
    if config.CPU_ML_ENABLED:
        try:
            from cpu_intelligence import get_cpu_processor
            cpu_processor = get_cpu_processor()
            logger.info("V5 CPU intelligence initialized (free-tier mode)")
        except Exception as exc:
            logger.warning("CPU intelligence initialization failed: %s", exc)

    logger.info("Momento Core ready on %s:%s", config.API_HOST, config.API_PORT)

    try:
        yield
    finally:
        logger.info("Momento Core shutting down")
        try:
            await feed.stop()
        except Exception as exc:
            logger.debug("feed shutdown: %s", exc)
        watcher.stop()

        # Stop FPGA pipeline
        try:
            fpga_pipeline = get_pipeline()
            await fpga_pipeline.stop()
            logger.info("FPGA-accelerated ingestion pipeline stopped")
        except Exception as exc:
            logger.debug("FPGA pipeline shutdown: %s", exc)

        # Stop stream optimizer
        try:
            stream_optimizer = get_optimizer()
            await stream_optimizer.stop()
            logger.info("Stream optimizer stopped")
        except Exception as exc:
            logger.debug("Stream optimizer shutdown: %s", exc)

        # Shutdown GPU intelligence
        try:
            from gpu_intelligence.integration import shutdown_gpu_intelligence

            shutdown_gpu_intelligence()
            logger.info("GPU intelligence subsystem shutdown")
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("GPU intelligence shutdown: %s", exc)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Momento Core / AVFS API",
        description=(
            "Modular analytics and forecasting platform. "
            "Pipeline: Collector -> Ingest API -> Analysis -> Forecast Engine -> Database -> Dashboard."
        ),
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if config.ALLOW_ALL_CORS else config.CORS_ORIGINS,
        allow_credentials=not config.ALLOW_ALL_CORS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # V5 Security: Add security headers middleware
    # Disabled for now to prevent CORS issues
    # if SECURITY_AVAILABLE and security_config and security_config.security_headers:
    #     application.add_middleware(
    #         SecurityHeadersMiddleware,
    #         config=security_config.get_headers_config(),
    #         sensitive_paths=["/api/v1/auth/", "/api/v1/users/", "/api/v1/admin/"],
    #     )

    # V5 Security: Add zero-trust middleware
    # Disabled for now to prevent CORS issues
    # if SECURITY_AVAILABLE and security_config and security_config.zero_trust_enabled:
    #     application.add_middleware(
    #         ZeroTrustMiddleware,
    #         public_paths=security_config.public_paths,
    #         strict_mode=security_config.zero_trust_strict_mode,
    #     )

    # Add scope gateway middleware for multi-scope authentication
    # Disabled for now to prevent CORS issues
    # if SCOPE_GATEWAY_AVAILABLE and ScopeGatewayMiddleware:
    #     application.add_middleware(ScopeGatewayMiddleware)

    @application.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        """Sanitised error envelope — internals never reach the client."""
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "path": request.url.path,
                "timestamp": db.utc_now(),
            },
        )

    for module in (
        core_routes,
        rounds_routes,
        analysis_routes,
        market_routes,
        forecast_routes,
        engines_routes,
        ingest_routes,
        users_routes,
        platform_routes,
        backtest_routes,
        features_routes,
        backtest_enhanced_routes,
        vocabulary_routes,
        mega_pressure_routes,
        fpga_routes,
        backup_routes,
    ):
        application.include_router(module.router, prefix=API_PREFIX)

    if GPU_ROUTES_AVAILABLE and gpu_routes:
        application.include_router(gpu_routes.router, prefix=API_PREFIX)

    if SCOPES_ROUTES_AVAILABLE and scopes_routes:
        application.include_router(scopes_routes.router, prefix=API_PREFIX)

    if V5_ADMIN_ROUTES_AVAILABLE and v5_admin_routes:
        application.include_router(v5_admin_routes.router, prefix=API_PREFIX)

    application.include_router(ws_routes.router)

    # Convenience aliases matching the legacy documented surface.
    @application.get("/health", include_in_schema=False)
    async def legacy_health() -> Dict[str, Any]:
        return await core_routes.health()

    @application.get("/", include_in_schema=False)
    async def root() -> Dict[str, Any]:
        return {
            "platform": "Momento Core / AVFS",
            "version": __version__,
            "api": API_PREFIX,
            "docs": "/docs",
            "websocket": "/ws",
            "health": f"{API_PREFIX}/health",
        }

    return application


app = create_app()
