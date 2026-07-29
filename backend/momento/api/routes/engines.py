"""Plugin inventory, orchestrator and autopilot endpoints."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query

from ... import autopilot as autopilot_engine
from ... import db, megaplan_orchestrator, orchestrator, plugins, store
from ...hub import hub
from ..deps import current_user, operator_user, source_param
from ..schemas import (
    AutopilotConfigRequest,
    OrchestratorSettingsRequest,
    PluginConfigRequest,
    PluginCreateRequest,
    PluginToggleRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# plugin inventory
# ---------------------------------------------------------------------------

@router.get("/inventory")
async def inventory() -> Dict[str, Any]:
    return {"plugins": plugins.list_plugins(), "statistics": plugins.statistics_summary()}


@router.get("/inventory/{plugin_id}")
async def plugin_detail(plugin_id: str) -> Dict[str, Any]:
    plugin = plugins.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")
    runs = db.query(
        "SELECT signal, score, processing_ms, created_at FROM plugin_runs WHERE plugin_id = ? ORDER BY created_at DESC LIMIT 100",
        (plugin_id,),
    )
    return {"plugin": plugin, "recent_runs": db.rows_to_dicts(runs)}


@router.put("/inventory/{plugin_id}/enabled")
async def toggle_plugin(
    plugin_id: str,
    body: PluginToggleRequest,
    user: Dict[str, Any] = Depends(operator_user),
) -> Dict[str, Any]:
    if not plugins.set_enabled(plugin_id, body.enabled):
        raise HTTPException(status_code=404, detail="Plugin not found")
    db.log_audit(user["email"], "plugin_toggle", {"plugin": plugin_id, "enabled": body.enabled})
    return {"plugin": plugins.get_plugin(plugin_id)}


@router.put("/inventory/{plugin_id}/config")
async def configure_plugin(
    plugin_id: str,
    body: PluginConfigRequest,
    user: Dict[str, Any] = Depends(operator_user),
) -> Dict[str, Any]:
    if not plugins.update_config(plugin_id, body.config):
        raise HTTPException(status_code=404, detail="Plugin not found")
    db.log_audit(user["email"], "plugin_config", {"plugin": plugin_id, "config": body.config})
    return {"plugin": plugins.get_plugin(plugin_id)}


@router.post("/inventory")
async def create_plugin(
    body: PluginCreateRequest,
    user: Dict[str, Any] = Depends(operator_user),
) -> Dict[str, Any]:
    try:
        plugin = plugins.create_plugin(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.log_audit(user["email"], "plugin_create", {"plugin": plugin.get("id")})
    return {"plugin": plugin, "statistics": plugins.statistics_summary()}


@router.delete("/inventory/{plugin_id}")
async def delete_plugin(plugin_id: str, user: Dict[str, Any] = Depends(operator_user)) -> Dict[str, Any]:
    if not plugins.delete_plugin(plugin_id):
        raise HTTPException(status_code=400, detail="Plugin not found or is a built-in plugin")
    db.log_audit(user["email"], "plugin_delete", {"plugin": plugin_id})
    return {"deleted": plugin_id, "statistics": plugins.statistics_summary()}


# ---------------------------------------------------------------------------
# orchestrator
# ---------------------------------------------------------------------------

@router.get("/orchestrator")
async def orchestrator_plan(source: str = Depends(source_param)) -> Dict[str, Any]:
    payload = store.analysis_payload(source)
    performance = autopilot_engine.performance(source)
    return {"source": source, **orchestrator.plan(payload, performance)}


@router.get("/orchestrator/settings")
async def orchestrator_settings() -> Dict[str, Any]:
    return {
        "settings": orchestrator.settings(),
        "modules": [{"id": key, **value} for key, value in orchestrator.MODULES.items()],
    }


@router.put("/orchestrator/settings")
async def update_orchestrator_settings(
    body: OrchestratorSettingsRequest,
    user: Dict[str, Any] = Depends(operator_user),
) -> Dict[str, Any]:
    updated = orchestrator.update_settings(body.model_dump(exclude_none=True))
    db.log_audit(user["email"], "orchestrator_settings", updated)
    return {"settings": updated, "modules": [{"id": key, **value} for key, value in orchestrator.MODULES.items()]}


# ---------------------------------------------------------------------------
# autopilot
# ---------------------------------------------------------------------------

@router.get("/autopilot/status")
async def autopilot_status(source: str = Depends(source_param)) -> Dict[str, Any]:
    return autopilot_engine.status(source)


@router.get("/autopilot/decisions")
async def autopilot_decisions(
    source: str = Depends(source_param),
    limit: int = Query(default=100, ge=1, le=500),
) -> Dict[str, Any]:
    return {
        "source": source,
        "decisions": autopilot_engine.decisions(source, limit),
        "equity_curve": autopilot_engine.equity_curve(source),
    }


@router.get("/autopilot/config")
async def autopilot_config() -> Dict[str, Any]:
    return {"config": autopilot_engine.config()}


@router.put("/autopilot/config")
async def update_autopilot_config(
    body: AutopilotConfigRequest,
    user: Dict[str, Any] = Depends(operator_user),
) -> Dict[str, Any]:
    updated = autopilot_engine.update_config(body.model_dump(exclude_none=True))
    db.log_audit(user["email"], "autopilot_config", updated)
    await hub.broadcast("autopilot:config", updated)
    return {"config": updated}


@router.post("/autopilot/start")
async def autopilot_start(user: Dict[str, Any] = Depends(operator_user)) -> Dict[str, Any]:
    cfg = autopilot_engine.set_enabled(True)
    db.log_audit(user["email"], "autopilot_start", {"source": cfg["source"]})
    status = autopilot_engine.status(str(cfg["source"]))
    await hub.broadcast("autopilot:status", status)
    return status


@router.post("/autopilot/stop")
async def autopilot_stop(user: Dict[str, Any] = Depends(operator_user)) -> Dict[str, Any]:
    cfg = autopilot_engine.set_enabled(False)
    db.log_audit(user["email"], "autopilot_stop", {"source": cfg["source"]})
    status = autopilot_engine.status(str(cfg["source"]))
    await hub.broadcast("autopilot:status", status)
    return status


@router.post("/autopilot/evaluate")
async def autopilot_evaluate(
    source: str = Depends(source_param),
    user: Dict[str, Any] = Depends(current_user),
) -> Dict[str, Any]:
    """Run one decision cycle now."""
    decision = autopilot_engine.evaluate(source, record=user.get("is_operator", False))
    if decision.get("recorded"):
        await hub.broadcast("autopilot:decision", decision)
    return {"source": source, "decision": decision, "status": autopilot_engine.status(source)}


@router.post("/autopilot/reset")
async def autopilot_reset(
    source: str = Depends(source_param),
    user: Dict[str, Any] = Depends(operator_user),
) -> Dict[str, Any]:
    deleted = autopilot_engine.reset(source)
    db.log_audit(user["email"], "autopilot_reset", {"source": source, "deleted": deleted})
    return {"deleted": deleted, "status": autopilot_engine.status(source)}


@router.get("/health")
async def engines_health() -> Dict[str, Any]:
    """Health status of all analysis engines."""
    toggles = store.runtime_toggles()
    
    return {
        "status": "healthy",
        "engines": {
            "signal_engine": toggles.signal_engine if hasattr(toggles, 'signal_engine') else True,
            "forecast_engine": toggles.forecast_engine if hasattr(toggles, 'forecast_engine') else True,
            "ml_predictions": toggles.ml_predictions if hasattr(toggles, 'ml_predictions') else False,
        },
        "timestamp": db.utc_now(),
    }


# ---------------------------------------------------------------------------
# megaplan orchestrator
# ---------------------------------------------------------------------------

@router.get("/megaplan")
async def megaplan_plan(source: str = Depends(source_param)) -> Dict[str, Any]:
    """Generate comprehensive megaplan with dynamic decision-making."""
    payload = store.analysis_payload(source)
    return {"source": source, **megaplan_orchestrator.megaplan_plan(payload)}


@router.get("/megaplan/settings")
async def megaplan_settings() -> Dict[str, Any]:
    """Get megaplan orchestrator settings."""
    return {
        "settings": megaplan_orchestrator.megaplan_settings(),
        "recovery_strategies": [
            {"id": key, **value} for key, value in megaplan_orchestrator.RECOVERY_STRATEGIES.items()
        ],
        "chase_strategies": [
            {"id": key, **value} for key, value in megaplan_orchestrator.CHASE_STRATEGIES.items()
        ],
    }


@router.put("/megaplan/settings")
async def update_megaplan_settings(
    body: OrchestratorSettingsRequest,
    user: Dict[str, Any] = Depends(operator_user),
) -> Dict[str, Any]:
    """Update megaplan orchestrator settings."""
    updated = megaplan_orchestrator.update_megaplan_settings(body.model_dump(exclude_none=True))
    db.log_audit(user["email"], "megaplan_settings", updated)
    return {
        "settings": updated,
        "recovery_strategies": [
            {"id": key, **value} for key, value in megaplan_orchestrator.RECOVERY_STRATEGIES.items()
        ],
        "chase_strategies": [
            {"id": key, **value} for key, value in megaplan_orchestrator.CHASE_STRATEGIES.items()
        ],
    }


@router.get("/megaplan/bankroll")
async def megaplan_bankroll(source: str = Depends(source_param)) -> Dict[str, Any]:
    """Get current bankroll state."""
    bankroll_state = megaplan_orchestrator.get_bankroll_state(source)
    return {
        "source": source,
        "bankroll_state": {
            "current_bankroll": bankroll_state.current_bankroll,
            "initial_bankroll": bankroll_state.initial_bankroll,
            "daily_pnl": bankroll_state.daily_pnl,
            "daily_loss_limit": bankroll_state.daily_loss_limit,
            "max_drawdown": bankroll_state.max_drawdown,
            "current_drawdown": bankroll_state.current_drawdown,
            "consecutive_losses": bankroll_state.consecutive_losses,
            "consecutive_wins": bankroll_state.consecutive_wins,
            "win_rate": bankroll_state.win_rate,
            "total_trades": bankroll_state.total_trades,
            "average_win": bankroll_state.average_win,
            "average_loss": bankroll_state.average_loss,
            "risk_per_round": bankroll_state.risk_per_round,
            "risk_level": bankroll_state.risk_level,
            "last_updated": bankroll_state.last_updated,
        },
    }


@router.post("/megaplan/backtest/recovery")
async def backtest_recovery_strategy(
    source: str = Depends(source_param),
    strategy: str = Query(..., description="Recovery strategy to backtest"),
    user: Dict[str, Any] = Depends(current_user),
) -> Dict[str, Any]:
    """Backtest a recovery strategy on historical data."""
    result = megaplan_orchestrator.backtest_recovery_strategy(source, strategy)
    db.log_audit(user["email"], "megaplan_backtest_recovery", {"source": source, "strategy": strategy})
    return result


@router.post("/megaplan/backtest/chase")
async def backtest_chase_strategy(
    source: str = Depends(source_param),
    strategy: str = Query(..., description="Chase strategy to backtest"),
    user: Dict[str, Any] = Depends(current_user),
) -> Dict[str, Any]:
    """Backtest a chase strategy on historical data."""
    result = megaplan_orchestrator.backtest_chase_strategy(source, strategy)
    db.log_audit(user["email"], "megaplan_backtest_chase", {"source": source, "strategy": strategy})
    return result


@router.get("/megaplan/backtest/compare")
async def compare_strategies(
    source: str = Depends(source_param),
    user: Dict[str, Any] = Depends(current_user),
) -> Dict[str, Any]:
    """Compare all recovery and chase strategies."""
    result = megaplan_orchestrator.compare_strategies(source)
    db.log_audit(user["email"], "megaplan_compare_strategies", {"source": source})
    return result
