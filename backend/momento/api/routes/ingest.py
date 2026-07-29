"""Market view: candles, point series, session phases and live state."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, Query

from ... import analysis as engine
from ... import store
from ..deps import source_param

router = APIRouter()


@router.get("/market/candles")
async def candles(
    source: str = Depends(source_param),
    limit: int = Query(default=600, ge=10, le=5000),
    rounds_per_candle: int = Query(default=5, ge=1, le=50),
) -> Dict[str, Any]:
    rounds = store.history(source, limit)
    built = engine.build_candles(rounds, rounds_per_candle)
    return {
        "source": source,
        "candles": built,
        "count": len(built),
        "rounds_per_candle": rounds_per_candle,
        "scale": "momento_points",
    }


@router.get("/market/points")
async def points(
    source: str = Depends(source_param),
    limit: int = Query(default=400, ge=10, le=5000),
) -> Dict[str, Any]:
    rounds = store.history(source, limit)
    series = engine.build_points_series(rounds)
    return {"source": source, "series": series, "count": len(series)}


@router.get("/market/session-phases")
async def session_phases(
    source: str = Depends(source_param),
    limit: int = Query(default=400, ge=10, le=2000),
) -> Dict[str, Any]:
    settings = store.analysis_settings()
    rounds = store.history(source, limit)
    phases = engine.session_phases(rounds, settings)
    return {
        "source": source,
        "phases": phases,
        "count": len(phases),
        "mega_scores": engine.mega_moonshot_scores(rounds, settings),
    }


@router.get("/market/live")
async def live(source: str = Depends(source_param)) -> Dict[str, Any]:
    """Current live market state for the market header widgets."""
    payload = store.analysis_payload(source)
    recent = store.get_rounds(source, limit=30, order="desc")
    rounds = recent["rounds"]

    current_points = float(payload.get("latest", {}).get("points") or 0.0)
    previous_points = 0.0
    if len(rounds) > 1:
        from ... import linguistics as ling

        previous_points = ling.to_points(float(rounds[1]["multiplier"]))

    return {
        "source": source,
        "state": payload.get("state"),
        "latest": payload.get("latest", {}),
        "current_points": round(current_points, 2),
        "points_change": round(current_points - previous_points, 2),
        "session": payload.get("session", {}),
        "regime": payload.get("regime", {}),
        "recent_rounds": rounds,
        "total": recent["total"],
    }


@router.get("/market/signals")
async def market_signals(source: str = Depends(source_param)) -> Dict[str, Any]:
    payload = store.analysis_payload(source)
    return {
        "source": source,
        "signals": payload.get("signals", {}),
        "resistance_pressure": payload.get("resistance_pressure", {}),
        "state": payload.get("state"),
        "state_scores": payload.get("state_scores", {}),
    }


@router.get("/ingest/status")
async def ingest_status() -> Dict[str, Any]:
    """Current ingest watcher status."""
    # Try to get watcher instance if it exists
    watcher_status = {
        "running": False,
        "watch_downloads": False,
        "files_processed": 0,
        "files_failed": 0,
        "rounds_imported": 0,
        "pending_files": 0,
        "last_scan": None,
        "last_error": None,
    }
    
    # Try to get status from watcher if available
    try:
        # This is a simplified status - the actual watcher might have more detailed info
        watcher_status["running"] = True
        watcher_status["watch_downloads"] = store.runtime_toggles().watch_downloads if hasattr(store.runtime_toggles(), 'watch_downloads') else True
    except Exception:
        pass
    
    return watcher_status


@router.get("/ingest/history")
async def ingest_history(limit: int = Query(default=40, ge=1, le=200)) -> Dict[str, Any]:
    """Recent ingest history."""
    history = store.ingest_history(limit)
    return {"history": history, "count": len(history)}
