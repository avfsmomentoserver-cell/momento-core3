"""Megaplan Orchestrator - Dynamic Decision-Making System.

Advanced orchestrator with:
- Dynamic precision decision-making based on real-time conditions
- Comprehensive bankroll tracking and analysis
- Recovery strategies (martingale, anti-martingale, fibonacci, etc.)
- Chase strategy implementation with safety guardrails
- Vigorous backtesting with conditional strategy evaluation
- Self-awareness and adaptive learning
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from enum import Enum
from dataclasses import dataclass, field

from . import analysis, db, forecast, store, backtest
from .config import AnalysisSettings

logger = logging.getLogger("momento.megaplan")


class RecoveryStrategy(Enum):
    """Recovery strategy types."""
    NONE = "none"
    MARTINGALE = "martingale"
    ANTI_MARTINGALE = "anti_martingale"
    FIBONACCI = "fibonacci"
    DALEMBERT = "dalembert"
    LABOUCHERE = "labouchere"
    FIXED_PERCENTAGE = "fixed_percentage"
    KELLY_CRITERION = "kelly_criterion"
    DYNAMIC_SIZING = "dynamic_sizing"


class ChaseStrategy(Enum):
    """Chase strategy types."""
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI_CHASE = "fibonacci_chase"
    HYBRID = "hybrid"
    CONDITIONAL = "conditional"


class DecisionPrecision(Enum):
    """Decision precision levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    DYNAMIC = "dynamic"


@dataclass
class BankrollState:
    """Current bankroll state and metrics."""
    current_bankroll: float
    initial_bankroll: float
    daily_pnl: float
    daily_loss_limit: float
    max_drawdown: float
    current_drawdown: float
    consecutive_losses: int
    consecutive_wins: int
    win_rate: float
    total_trades: int
    average_win: float
    average_loss: float
    risk_per_round: float
    risk_level: str
    last_updated: str = field(default_factory=lambda: db.utc_now())


@dataclass
class RecoveryState:
    """Recovery strategy state."""
    strategy: RecoveryStrategy
    active: bool
    trigger_threshold: float
    current_step: int
    max_steps: int
    recovery_multiplier: float
    progress: float
    estimated_recovery_rounds: int
    bankroll_before_recovery: float
    target_bankroll: float
    safety_limits: Dict[str, Any]
    started_at: Optional[str] = None


@dataclass
class ChaseState:
    """Chase strategy state."""
    strategy: ChaseStrategy
    active: bool
    target_multiplier: float
    current_multiplier: float
    chase_sequence: List[float]
    current_step: int
    max_steps: int
    bankroll_allocated: float
    expected_value: float
    risk_reward_ratio: float
    safety_conditions: Dict[str, Any]
    started_at: Optional[str] = None


@dataclass
class DecisionContext:
    """Context for dynamic decision-making."""
    confidence: float
    market_state: str
    volatility: float
    trend_strength: float
    volume_profile: float
    time_of_day_factor: float
    regime: str
    band_exhaustion: Dict[str, Any]
    streaks: Dict[str, Any]
    prediction_accuracy: float
    historical_accuracy: float
    risk_appetite: float
    opportunity_score: float


@dataclass
class MegaplanInstruction:
    """Complete megaplan instruction."""
    action: str
    headline: str
    detail: str
    position_size: float
    target_multiplier: float
    stop_multiplier: float
    confidence: float
    precision_level: DecisionPrecision
    reasoning: Dict[str, Any]
    recovery_plan: Optional[RecoveryState]
    chase_plan: Optional[ChaseState]
    risk_analysis: Dict[str, Any]
    expected_outcome: Dict[str, Any]
    execution_conditions: List[str]
    safety_checks: List[Dict[str, Any]]


# Default megaplan settings
DEFAULT_MEGAPLAN_SETTINGS: Dict[str, Any] = {
    "enabled": True,
    "initial_bankroll": 1000.0,
    "base_position_size": 10.0,
    "max_risk_per_round": 0.02,
    "daily_loss_limit": 0.15,
    "max_drawdown_limit": 0.25,
    "recovery_strategy": "none",
    "recovery_trigger_threshold": 0.10,
    "chase_strategy": "none",
    "chase_target_multiplier": 50.0,
    "chase_max_steps": 10,
    "decision_precision": "dynamic",
    "adaptive_learning": True,
    "backtest_enabled": True,
    "backtest_window": 10000,
    "min_confidence_threshold": 0.45,
    "position_sizing_method": "dynamic",
}


RECOVERY_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "none": {
        "label": "No Recovery",
        "description": "Standard trading without recovery mechanisms",
        "trigger_threshold": 0.0,
        "max_steps": 0,
    },
    "martingale": {
        "label": "Martingale",
        "description": "Double position after each loss (risky)",
        "trigger_threshold": 0.05,
        "max_steps": 5,
        "multiplier": 2.0,
    },
    "anti_martingale": {
        "label": "Anti-Martingale",
        "description": "Increase position after wins, decrease after losses",
        "trigger_threshold": 0.05,
        "max_steps": 5,
        "multiplier": 1.5,
    },
    "fibonacci": {
        "label": "Fibonacci",
        "description": "Use Fibonacci sequence for position sizing",
        "trigger_threshold": 0.08,
        "max_steps": 8,
        "sequence": [1, 1, 2, 3, 5, 8, 13, 21],
    },
    "dalembert": {
        "label": "D'Alembert",
        "description": "Increase by one unit after loss, decrease after win",
        "trigger_threshold": 0.06,
        "max_steps": 10,
        "unit_size": 5.0,
    },
    "labouchere": {
        "label": "Labouchere",
        "description": "Cross out numbers from sequence after wins",
        "trigger_threshold": 0.07,
        "max_steps": 10,
        "base_sequence": [1, 2, 3, 4, 5],
    },
    "fixed_percentage": {
        "label": "Fixed Percentage",
        "description": "Risk fixed percentage of bankroll",
        "trigger_threshold": 0.05,
        "max_steps": 0,
        "percentage": 0.02,
    },
    "kelly_criterion": {
        "label": "Kelly Criterion",
        "description": "Optimal sizing based on edge and odds",
        "trigger_threshold": 0.04,
        "max_steps": 0,
        "kelly_fraction": 0.25,
    },
    "dynamic_sizing": {
        "label": "Dynamic Sizing",
        "description": "Adaptive sizing based on market conditions",
        "trigger_threshold": 0.03,
        "max_steps": 0,
        "adaptation_rate": 0.1,
    },
}


CHASE_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "none": {
        "label": "No Chase",
        "description": "Do not chase high multipliers",
        "target_multiplier": 0.0,
        "max_steps": 0,
    },
    "linear": {
        "label": "Linear Chase",
        "description": "Linear increase in chase attempts",
        "target_multiplier": 50.0,
        "max_steps": 10,
        "increment": 1.0,
    },
    "exponential": {
        "label": "Exponential Chase",
        "description": "Exponential increase in position size",
        "target_multiplier": 100.0,
        "max_steps": 7,
        "base_multiplier": 1.5,
    },
    "fibonacci_chase": {
        "label": "Fibonacci Chase",
        "description": "Use Fibonacci sequence for chase attempts",
        "target_multiplier": 50.0,
        "max_steps": 8,
        "sequence": [1, 1, 2, 3, 5, 8, 13, 21],
    },
    "hybrid": {
        "label": "Hybrid Chase",
        "description": "Combine multiple chase strategies",
        "target_multiplier": 75.0,
        "max_steps": 10,
        "strategies": ["linear", "fibonacci_chase"],
    },
    "conditional": {
        "label": "Conditional Chase",
        "description": "Chase based on specific market conditions",
        "target_multiplier": 50.0,
        "max_steps": 12,
        "conditions": {
            "min_confidence": 0.6,
            "max_volatility": 1.5,
            "required_state": ["Ignition", "Moonshot"],
        },
    },
}


def megaplan_settings() -> Dict[str, Any]:
    """Get megaplan orchestrator settings."""
    stored = db.get_setting("megaplan_orchestrator") or {}
    merged = dict(DEFAULT_MEGAPLAN_SETTINGS)
    merged.update({k: v for k, v in stored.items() if k in DEFAULT_MEGAPLAN_SETTINGS and v is not None})
    return merged


def update_megaplan_settings(values: Dict[str, Any]) -> Dict[str, Any]:
    """Update megaplan orchestrator settings."""
    current = megaplan_settings()
    for key, value in values.items():
        if key not in DEFAULT_MEGAPLAN_SETTINGS or value is None:
            continue
        if key == "recovery_strategy":
            if str(value) in RECOVERY_STRATEGIES:
                current[key] = str(value)
        elif key == "chase_strategy":
            if str(value) in CHASE_STRATEGIES:
                current[key] = str(value)
        elif key == "decision_precision":
            if str(value) in [e.value for e in DecisionPrecision]:
                current[key] = str(value)
        elif key == "position_sizing_method":
            if str(value) in ("fixed", "confidence_scaled", "kelly", "dynamic"):
                current[key] = str(value)
        else:
            try:
                current[key] = float(value) if isinstance(value, (int, float, str)) else value
            except (TypeError, ValueError):
                continue
    db.set_setting("megaplan_orchestrator", current)
    return current


def get_bankroll_state(source: str) -> BankrollState:
    """Get current bankroll state."""
    settings = megaplan_settings()
    
    # Get autopilot performance data
    perf_data = get_autopilot_performance(source)
    
    # Calculate current metrics
    current_bankroll = float(settings["initial_bankroll"]) + float(perf_data.get("total_pnl", 0.0))
    daily_pnl = float(perf_data.get("daily_pnl", 0.0))
    consecutive_losses = int(perf_data.get("consecutive_losses", 0))
    consecutive_wins = int(perf_data.get("consecutive_wins", 0))
    win_rate = float(perf_data.get("win_rate", 0.0))
    total_trades = int(perf_data.get("total_trades", 0))
    
    # Calculate drawdown
    max_bankroll = float(perf_data.get("max_bankroll", settings["initial_bankroll"]))
    current_drawdown = (max_bankroll - current_bankroll) / max_bankroll if max_bankroll > 0 else 0.0
    max_drawdown = float(perf_data.get("max_drawdown", 0.0))
    
    # Calculate average win/loss
    resolved_trades = perf_data.get("resolved_trades", [])
    wins = [t.get("pnl", 0) for t in resolved_trades if t.get("pnl", 0) > 0]
    losses = [abs(t.get("pnl", 0)) for t in resolved_trades if t.get("pnl", 0) < 0]
    
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    
    # Determine risk level
    risk_level = "normal"
    if current_drawdown > 0.15 or consecutive_losses >= 3:
        risk_level = "elevated"
    if current_drawdown > 0.25 or consecutive_losses >= 5:
        risk_level = "critical"
    
    return BankrollState(
        current_bankroll=current_bankroll,
        initial_bankroll=float(settings["initial_bankroll"]),
        daily_pnl=daily_pnl,
        daily_loss_limit=float(settings["daily_loss_limit"]),
        max_drawdown=max_drawdown,
        current_drawdown=current_drawdown,
        consecutive_losses=consecutive_losses,
        consecutive_wins=consecutive_wins,
        win_rate=win_rate,
        total_trades=total_trades,
        average_win=average_win,
        average_loss=average_loss,
        risk_per_round=float(settings["max_risk_per_round"]),
        risk_level=risk_level,
    )


def get_autopilot_performance(source: str) -> Dict[str, Any]:
    """Get autopilot performance data."""
    try:
        from . import autopilot
        return autopilot.performance(source)
    except Exception as e:
        logger.error(f"Error getting autopilot performance: {e}")
        return {
            "total_pnl": 0.0,
            "daily_pnl": 0.0,
            "consecutive_losses": 0,
            "consecutive_wins": 0,
            "win_rate": 0.0,
            "total_trades": 0,
            "max_bankroll": 1000.0,
            "max_drawdown": 0.0,
            "resolved_trades": [],
        }


def build_decision_context(payload: Dict[str, Any]) -> DecisionContext:
    """Build decision context from analysis payload."""
    prediction_confidence = payload.get("prediction_confidence", {})
    session = payload.get("session", {})
    regime = payload.get("regime", {})
    streaks = payload.get("streaks", {})
    band_exhaustion = payload.get("band_exhaustion", {})
    
    confidence = float(prediction_confidence.get("confidence", 0.0))
    volatility = float(regime.get("volatility", 0.0))
    trend_strength = float(regime.get("trend_strength", 0.0))
    
    # Calculate opportunity score
    opportunity_score = calculate_opportunity_score(payload)
    
    # Calculate risk appetite based on bankroll state
    bankroll_state = get_bankroll_state(payload.get("source", "unknown"))
    risk_appetite = calculate_risk_appetite(bankroll_state, confidence)
    
    return DecisionContext(
        confidence=confidence,
        market_state=payload.get("state", "Normal"),
        volatility=volatility,
        trend_strength=trend_strength,
        volume_profile=float(session.get("volume_profile", 0.5)),
        time_of_day_factor=calculate_time_factor(),
        regime=regime.get("regime", "neutral"),
        band_exhaustion=band_exhaustion,
        streaks=streaks,
        prediction_accuracy=confidence,
        historical_accuracy=float(prediction_confidence.get("historical_accuracy", 0.5)),
        risk_appetite=risk_appetite,
        opportunity_score=opportunity_score,
    )


def calculate_opportunity_score(payload: Dict[str, Any]) -> float:
    """Calculate opportunity score (0-1) based on market conditions."""
    state = payload.get("state", "Normal")
    confidence = float(payload.get("prediction_confidence", {}).get("confidence", 0.0))
    streaks = payload.get("streaks", {})
    exhaustion = payload.get("band_exhaustion", {}).get("most_overdue") or {}
    
    # Base score from confidence
    score = confidence
    
    # State bonuses
    state_bonus = {
        "Moonshot": 0.3,
        "Ignition": 0.2,
        "Normal": 0.0,
        "Exhaustion": -0.1,
        "Bait": -0.2,
        "Collapse": -0.3,
    }
    score += state_bonus.get(state, 0.0)
    
    # Streak adjustments
    low_streak = int(streaks.get("current_low_streak", 0))
    high_streak = int(streaks.get("current_high_streak", 0))
    
    if low_streak >= 6:
        score += 0.15  # Due for high
    if high_streak >= 4:
        score -= 0.1  # Due for low
    
    # Exhaustion bonus
    overdue_ratio = float(exhaustion.get("overdue_ratio", 0))
    if overdue_ratio > 1.5:
        score += 0.1
    
    return max(0.0, min(1.0, score))


def calculate_risk_appetite(bankroll_state: BankrollState, confidence: float) -> float:
    """Calculate risk appetite (0-1) based on bankroll state and confidence."""
    base_appetite = 0.5
    
    # Adjust for bankroll health
    if bankroll_state.current_drawdown < 0.05:
        base_appetite += 0.2  # Healthy, can take more risk
    elif bankroll_state.current_drawdown > 0.15:
        base_appetite -= 0.3  # Drawdown, reduce risk
    
    # Adjust for consecutive losses
    if bankroll_state.consecutive_losses >= 3:
        base_appetite -= 0.2
    elif bankroll_state.consecutive_wins >= 3:
        base_appetite += 0.1
    
    # Adjust for confidence
    base_appetite += (confidence - 0.5) * 0.3
    
    return max(0.1, min(0.9, base_appetite))


def calculate_time_factor() -> float:
    """Calculate time-of-day factor for decision making."""
    hour = datetime.now().hour
    
    # Assuming higher activity during certain hours
    if 9 <= hour <= 11 or 14 <= hour <= 16:
        return 1.0  # High activity
    elif 12 <= hour <= 13:
        return 0.7  # Lunch lull
    elif 20 <= hour <= 22:
        return 0.9  # Evening activity
    else:
        return 0.5  # Low activity


def evaluate_recovery_strategy(bankroll_state: BankrollState, context: DecisionContext) -> Optional[RecoveryState]:
    """Evaluate if recovery strategy should be activated."""
    settings = megaplan_settings()
    strategy_name = settings.get("recovery_strategy", "none")
    
    if strategy_name == "none":
        return None
    
    strategy_config = RECOVERY_STRATEGIES[strategy_name]
    trigger_threshold = float(strategy_config["trigger_threshold"])
    
    # Check if recovery should be triggered
    should_trigger = (
        bankroll_state.current_drawdown >= trigger_threshold or
        bankroll_state.consecutive_losses >= 3
    )
    
    if not should_trigger:
        return None
    
    # Calculate recovery parameters
    current_step = min(bankroll_state.consecutive_losses, strategy_config["max_steps"])
    recovery_multiplier = calculate_recovery_multiplier(strategy_name, current_step, strategy_config)
    
    # Estimate recovery rounds
    estimated_rounds = estimate_recovery_rounds(bankroll_state, strategy_name, recovery_multiplier)
    
    return RecoveryState(
        strategy=RecoveryStrategy(strategy_name),
        active=True,
        trigger_threshold=trigger_threshold,
        current_step=current_step,
        max_steps=strategy_config["max_steps"],
        recovery_multiplier=recovery_multiplier,
        progress=current_step / strategy_config["max_steps"],
        estimated_recovery_rounds=estimated_rounds,
        bankroll_before_recovery=bankroll_state.current_bankroll,
        target_bankroll=bankroll_state.initial_bankroll * (1 + 0.05),  # 5% profit target
        safety_limits={
            "max_drawdown": 0.40,
            "max_consecutive_losses": strategy_config["max_steps"] + 2,
            "emergency_stop": 0.50,
        },
        started_at=db.utc_now(),
    )


def calculate_recovery_multiplier(strategy_name: str, step: int, config: Dict[str, Any]) -> float:
    """Calculate position size multiplier for recovery strategy."""
    if strategy_name == "martingale":
        return 2.0 ** step
    elif strategy_name == "anti_martingale":
        return 1.5 ** step
    elif strategy_name == "fibonacci":
        sequence = config.get("sequence", [1, 1, 2, 3, 5, 8, 13, 21])
        return float(sequence[min(step, len(sequence) - 1)])
    elif strategy_name == "dalembert":
        return 1.0 + (step * config.get("unit_size", 5.0) / 10.0)
    elif strategy_name == "labouchere":
        return 1.0 + step * 0.5
    elif strategy_name == "fixed_percentage":
        return config.get("percentage", 0.02)
    elif strategy_name == "kelly_criterion":
        return config.get("kelly_fraction", 0.25)
    else:
        return 1.0


def estimate_recovery_rounds(bankroll_state: BankrollState, strategy_name: str, multiplier: float) -> int:
    """Estimate rounds needed to recover losses."""
    loss_amount = bankroll_state.initial_bankroll - bankroll_state.current_bankroll
    if loss_amount <= 0:
        return 0
    
    avg_win_per_round = bankroll_state.average_win * multiplier
    if avg_win_per_round <= 0:
        return 10  # Conservative estimate
    
    return int((loss_amount / avg_win_per_round) * 1.5)  # 1.5x safety factor


def evaluate_chase_strategy(context: DecisionContext, bankroll_state: BankrollState) -> Optional[ChaseState]:
    """Evaluate if chase strategy should be activated."""
    settings = megaplan_settings()
    strategy_name = settings.get("chase_strategy", "none")
    
    if strategy_name == "none":
        return None
    
    strategy_config = CHASE_STRATEGIES[strategy_name]
    target_multiplier = float(strategy_config["target_multiplier"])
    
    # Check conditions for chase
    should_chase = should_activate_chase(context, bankroll_state, strategy_config)
    
    if not should_chase:
        return None
    
    # Calculate chase sequence
    chase_sequence = calculate_chase_sequence(strategy_name, strategy_config)
    current_step = 0
    bankroll_allocated = bankroll_state.current_bankroll * 0.1  # Allocate 10% for chase
    
    # Calculate expected value
    expected_value = calculate_chase_ev(chase_sequence, target_multiplier, context.confidence)
    
    return ChaseState(
        strategy=ChaseStrategy(strategy_name),
        active=True,
        target_multiplier=target_multiplier,
        current_multiplier=chase_sequence[0] if chase_sequence else 1.0,
        chase_sequence=chase_sequence,
        current_step=current_step,
        max_steps=strategy_config["max_steps"],
        bankroll_allocated=bankroll_allocated,
        expected_value=expected_value,
        risk_reward_ratio=calculate_risk_reward_ratio(chase_sequence, target_multiplier),
        safety_conditions={
            "max_loss_per_chase": bankroll_allocated * 0.5,
            "max_steps_without_hit": strategy_config["max_steps"],
            "min_confidence": strategy_config.get("conditions", {}).get("min_confidence", 0.5),
        },
        started_at=db.utc_now(),
    )


def should_activate_chase(context: DecisionContext, bankroll_state: BankrollState, config: Dict[str, Any]) -> bool:
    """Determine if chase should be activated based on conditions."""
    # Check confidence threshold
    conditions = config.get("conditions", {})
    min_confidence = conditions.get("min_confidence", 0.5)
    if context.confidence < min_confidence:
        return False
    
    # Check volatility
    max_volatility = conditions.get("max_volatility", 2.0)
    if context.volatility > max_volatility:
        return False
    
    # Check market state
    required_states = conditions.get("required_state", [])
    if required_states and context.market_state not in required_states:
        return False
    
    # Check bankroll health
    if bankroll_state.current_drawdown > 0.20:
        return False  # Don't chase during drawdown
    
    # Check opportunity score
    if context.opportunity_score < 0.6:
        return False
    
    return True


def calculate_chase_sequence(strategy_name: str, config: Dict[str, Any]) -> List[float]:
    """Calculate chase sequence based on strategy."""
    if strategy_name == "linear":
        max_steps = config["max_steps"]
        increment = config.get("increment", 1.0)
        return [1.0 + (i * increment) for i in range(max_steps)]
    
    elif strategy_name == "exponential":
        max_steps = config["max_steps"]
        base = config.get("base_multiplier", 1.5)
        return [base ** i for i in range(max_steps)]
    
    elif strategy_name == "fibonacci_chase":
        sequence = config.get("sequence", [1, 1, 2, 3, 5, 8, 13, 21])
        return sequence[:config["max_steps"]]
    
    elif strategy_name == "hybrid":
        # Combine strategies
        strategies = config.get("strategies", ["linear"])
        if "linear" in strategies:
            return [1.0 + i for i in range(config["max_steps"])]
        else:
            return [1.0] * config["max_steps"]
    
    else:  # conditional
        return [1.0] * config["max_steps"]


def calculate_chase_ev(sequence: List[float], target_multiplier: float, confidence: float) -> float:
    """Calculate expected value of chase strategy."""
    if not sequence:
        return 0.0
    
    # Simplified EV calculation
    hit_probability = confidence * 0.3  # Reduced probability for high multipliers
    miss_probability = 1.0 - hit_probability
    
    total_invested = sum(sequence)
    potential_win = target_multiplier * sequence[-1]  # Last step hit
    
    ev = (hit_probability * potential_win) - (miss_probability * total_invested)
    return ev / total_invested if total_invested > 0 else 0.0


def calculate_risk_reward_ratio(sequence: List[float], target_multiplier: float) -> float:
    """Calculate risk-reward ratio for chase strategy."""
    if not sequence:
        return 0.0
    
    total_risk = sum(sequence)
    potential_reward = target_multiplier * sequence[-1]
    
    return potential_reward / total_risk if total_risk > 0 else 0.0


def dynamic_decision_making(context: DecisionContext, bankroll_state: BankrollState) -> DecisionPrecision:
    """Make dynamic precision decision based on context."""
    settings = megaplan_settings()
    precision_mode = settings.get("decision_precision", "dynamic")
    
    if precision_mode != "dynamic":
        return DecisionPrecision(precision_mode)
    
    # Dynamic precision logic
    if context.confidence >= 0.7 and context.opportunity_score >= 0.8:
        return DecisionPrecision.AGGRESSIVE
    elif context.confidence >= 0.5 and context.opportunity_score >= 0.6:
        return DecisionPrecision.MODERATE
    else:
        return DecisionPrecision.CONSERVATIVE


def calculate_position_size(
    context: DecisionContext,
    bankroll_state: BankrollState,
    precision: DecisionPrecision,
    recovery_state: Optional[RecoveryState],
    chase_state: Optional[ChaseState],
) -> float:
    """Calculate optimal position size."""
    settings = megaplan_settings()
    base_size = float(settings["base_position_size"])
    method = settings.get("position_sizing_method", "dynamic")
    
    if recovery_state and recovery_state.active:
        # Use recovery strategy sizing
        return base_size * recovery_state.recovery_multiplier
    
    if chase_state and chase_state.active:
        # Use chase strategy sizing
        current_multiplier = chase_state.chase_sequence[chase_state.current_step]
        return base_size * current_multiplier
    
    # Standard sizing methods
    if method == "fixed":
        return base_size
    elif method == "confidence_scaled":
        return base_size * (0.5 + context.confidence) * (1.0 + context.risk_appetite)
    elif method == "kelly":
        # Kelly criterion implementation
        odds = 2.0  # Assumed odds
        edge = (context.confidence * odds) - (1.0 - context.confidence)
        kelly = max(0.0, edge / odds) if odds > 0 else 0.0
        return bankroll_state.current_bankroll * min(0.05, kelly * 0.25)
    else:  # dynamic
        # Dynamic sizing based on multiple factors
        precision_multiplier = {
            DecisionPrecision.CONSERVATIVE: 0.6,
            DecisionPrecision.MODERATE: 1.0,
            DecisionPrecision.AGGRESSIVE: 1.5,
        }
        
        size = base_size * precision_multiplier[precision]
        size *= (0.5 + context.confidence)
        size *= (0.5 + context.risk_appetite)
        size *= (0.8 + context.opportunity_score)
        
        # Apply risk limits
        max_risk = bankroll_state.current_bankroll * bankroll_state.risk_per_round
        return min(size, max_risk)


def generate_megaplan_instruction(
    payload: Dict[str, Any],
    context: DecisionContext,
    bankroll_state: BankrollState,
    precision: DecisionPrecision,
    recovery_state: Optional[RecoveryState],
    chase_state: Optional[ChaseState],
) -> MegaplanInstruction:
    """Generate complete megaplan instruction."""
    settings = megaplan_settings()
    forecast_payload = payload.get("forecast") or {}
    
    # Calculate position size
    position_size = calculate_position_size(
        context, bankroll_state, precision, recovery_state, chase_state
    )
    
    # Calculate targets
    target_multiplier = float(forecast_payload.get("range_hi", 2.0))
    stop_multiplier = max(1.01, target_multiplier * 0.55)
    
    # Determine action
    action, headline, detail = determine_action(context, bankroll_state, recovery_state, chase_state)
    
    # Generate reasoning
    reasoning = generate_reasoning(context, bankroll_state, precision, recovery_state, chase_state)
    
    # Risk analysis
    risk_analysis = analyze_risk(context, bankroll_state, position_size, target_multiplier)
    
    # Expected outcome
    expected_outcome = calculate_expected_outcome(
        context, position_size, target_multiplier, stop_multiplier
    )
    
    # Execution conditions
    execution_conditions = generate_execution_conditions(
        context, bankroll_state, recovery_state, chase_state
    )
    
    # Safety checks
    safety_checks = generate_safety_checks(bankroll_state, recovery_state, chase_state)
    
    return MegaplanInstruction(
        action=action,
        headline=headline,
        detail=detail,
        position_size=position_size,
        target_multiplier=target_multiplier,
        stop_multiplier=stop_multiplier,
        confidence=context.confidence,
        precision_level=precision,
        reasoning=reasoning,
        recovery_plan=recovery_state,
        chase_plan=chase_state,
        risk_analysis=risk_analysis,
        expected_outcome=expected_outcome,
        execution_conditions=execution_conditions,
        safety_checks=safety_checks,
    )


def determine_action(
    context: DecisionContext,
    bankroll_state: BankrollState,
    recovery_state: Optional[RecoveryState],
    chase_state: Optional[ChaseState],
) -> Tuple[str, str, str]:
    """Determine action based on all factors."""
    # Check safety conditions first
    if bankroll_state.current_drawdown > bankroll_state.daily_loss_limit:
        return "STAND_DOWN", "Daily loss limit reached", "Stop trading for the day to preserve capital"
    
    if bankroll_state.current_drawdown > 0.40:
        return "STAND_DOWN", "Maximum drawdown exceeded", "Emergency stop - reset required"
    
    # Check recovery strategy
    if recovery_state and recovery_state.active:
        if recovery_state.current_step >= recovery_state.max_steps:
            return "STAND_DOWN", "Recovery strategy limit reached", "Abort recovery - reassess strategy"
        return "ENTER", f"Recovery step {recovery_state.current_step + 1}", f"Executing {recovery_state.strategy.value} recovery strategy"
    
    # Check chase strategy
    if chase_state and chase_state.active:
        if chase_state.current_step >= chase_state.max_steps:
            return "STAND_DOWN", "Chase strategy limit reached", "Abort chase - reassess conditions"
        return "ENTER", f"Chase step {chase_state.current_step + 1}", f"Chasing {chase_state.target_multiplier}x via {chase_state.strategy.value}"
    
    # Standard decision making
    if context.confidence < 0.35:
        return "WAIT", "Low confidence", "Wait for better setup"
    
    if context.opportunity_score < 0.5:
        return "WAIT", "Low opportunity score", "Market conditions not favorable"
    
    if context.market_state in ("Bait", "Collapse"):
        return "STAND_DOWN", f"Unsafe market state: {context.market_state}", "Wait for structure to form"
    
    return "ENTER", f"Enter at {context.market_state}", f"Confidence: {context.confidence:.0%}, Opportunity: {context.opportunity_score:.0%}"


def generate_reasoning(
    context: DecisionContext,
    bankroll_state: BankrollState,
    precision: DecisionPrecision,
    recovery_state: Optional[RecoveryState],
    chase_state: Optional[ChaseState],
) -> Dict[str, Any]:
    """Generate detailed reasoning for the decision."""
    reasoning = {
        "confidence": context.confidence,
        "market_state": context.market_state,
        "opportunity_score": context.opportunity_score,
        "risk_appetite": context.risk_appetite,
        "precision_level": precision.value,
        "bankroll_health": {
            "current_drawdown": bankroll_state.current_drawdown,
            "consecutive_losses": bankroll_state.consecutive_losses,
            "win_rate": bankroll_state.win_rate,
        },
        "market_conditions": {
            "volatility": context.volatility,
            "trend_strength": context.trend_strength,
            "regime": context.regime,
        },
    }
    
    if recovery_state:
        reasoning["recovery"] = {
            "strategy": recovery_state.strategy.value,
            "step": recovery_state.current_step,
            "multiplier": recovery_state.recovery_multiplier,
            "progress": recovery_state.progress,
        }
    
    if chase_state:
        reasoning["chase"] = {
            "strategy": chase_state.strategy.value,
            "target": chase_state.target_multiplier,
            "expected_value": chase_state.expected_value,
            "risk_reward": chase_state.risk_reward_ratio,
        }
    
    return reasoning


def analyze_risk(
    context: DecisionContext,
    bankroll_state: BankrollState,
    position_size: float,
    target_multiplier: float,
) -> Dict[str, Any]:
    """Analyze risk for the decision."""
    risk_amount = position_size
    potential_reward = position_size * (target_multiplier - 1)
    risk_reward_ratio = potential_reward / risk_amount if risk_amount > 0 else 0
    
    probability_of_loss = 1.0 - context.confidence
    expected_loss = risk_amount * probability_of_loss
    expected_gain = potential_reward * context.confidence
    
    return {
        "risk_amount": risk_amount,
        "potential_reward": potential_reward,
        "risk_reward_ratio": risk_reward_ratio,
        "probability_of_loss": probability_of_loss,
        "expected_loss": expected_loss,
        "expected_gain": expected_gain,
        "expected_value": expected_gain - expected_loss,
        "risk_level": bankroll_state.risk_level,
        "position_risk_pct": risk_amount / bankroll_state.current_bankroll if bankroll_state.current_bankroll > 0 else 0,
    }


def calculate_expected_outcome(
    context: DecisionContext,
    position_size: float,
    target_multiplier: float,
    stop_multiplier: float,
) -> Dict[str, Any]:
    """Calculate expected outcome distribution."""
    scenarios = [
        {"probability": context.confidence * 0.7, "multiplier": target_multiplier, "outcome": "win"},
        {"probability": context.confidence * 0.3, "multiplier": 1.5, "outcome": "partial"},
        {"probability": 1.0 - context.confidence, "multiplier": stop_multiplier, "outcome": "loss"},
    ]
    
    expected_multiplier = sum(s["probability"] * s["multiplier"] for s in scenarios)
    expected_pnl = position_size * (expected_multiplier - 1)
    
    return {
        "scenarios": scenarios,
        "expected_multiplier": expected_multiplier,
        "expected_pnl": expected_pnl,
        "upside_potential": position_size * (target_multiplier - 1),
        "downside_risk": position_size * (1 - stop_multiplier),
    }


def generate_execution_conditions(
    context: DecisionContext,
    bankroll_state: BankrollState,
    recovery_state: Optional[RecoveryState],
    chase_state: Optional[ChaseState],
) -> List[str]:
    """Generate list of execution conditions."""
    conditions = [
        f"Confidence >= {context.confidence:.0%}",
        f"Market state: {context.market_state}",
        f"Volatility: {context.volatility:.2f}",
        f"Bankroll drawdown: {bankroll_state.current_drawdown:.0%}",
    ]
    
    if recovery_state:
        conditions.append(f"Recovery active: {recovery_state.strategy.value}")
        conditions.append(f"Recovery step: {recovery_state.current_step + 1}/{recovery_state.max_steps}")
    
    if chase_state:
        conditions.append(f"Chase active: {chase_state.strategy.value}")
        conditions.append(f"Chase target: {chase_state.target_multiplier}x")
    
    return conditions


def generate_safety_checks(
    bankroll_state: BankrollState,
    recovery_state: Optional[RecoveryState],
    chase_state: Optional[ChaseState],
) -> List[Dict[str, Any]]:
    """Generate safety checks."""
    checks = []
    
    # Bankroll safety
    checks.append({
        "type": "bankroll",
        "status": "pass" if bankroll_state.current_drawdown < 0.30 else "fail",
        "message": f"Drawdown: {bankroll_state.current_drawdown:.0%}",
        "limit": "30%",
    })
    
    # Consecutive losses
    checks.append({
        "type": "streak",
        "status": "pass" if bankroll_state.consecutive_losses < 5 else "fail",
        "message": f"Consecutive losses: {bankroll_state.consecutive_losses}",
        "limit": "5",
    })
    
    if recovery_state:
        checks.append({
            "type": "recovery",
            "status": "pass" if recovery_state.current_step < recovery_state.max_steps else "fail",
            "message": f"Recovery step: {recovery_state.current_step}/{recovery_state.max_steps}",
            "limit": str(recovery_state.max_steps),
        })
    
    if chase_state:
        checks.append({
            "type": "chase",
            "status": "pass" if chase_state.current_step < chase_state.max_steps else "fail",
            "message": f"Chase step: {chase_state.current_step}/{chase_state.max_steps}",
            "limit": str(chase_state.max_steps),
        })
    
    return checks


def megaplan_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate complete megaplan orchestrator plan."""
    source = payload.get("source", "unknown")
    
    # Build decision context
    context = build_decision_context(payload)
    
    # Get bankroll state
    bankroll_state = get_bankroll_state(source)
    
    # Determine precision level
    precision = dynamic_decision_making(context, bankroll_state)
    
    # Evaluate recovery strategy
    recovery_state = evaluate_recovery_strategy(bankroll_state, context)
    
    # Evaluate chase strategy
    chase_state = evaluate_chase_strategy(context, bankroll_state)
    
    # Generate instruction
    instruction = generate_megaplan_instruction(
        payload, context, bankroll_state, precision, recovery_state, chase_state
    )
    
    return {
        "source": source,
        "settings": megaplan_settings(),
        "context": {
            "confidence": context.confidence,
            "market_state": context.market_state,
            "opportunity_score": context.opportunity_score,
            "risk_appetite": context.risk_appetite,
            "volatility": context.volatility,
        },
        "bankroll_state": {
            "current_bankroll": bankroll_state.current_bankroll,
            "daily_pnl": bankroll_state.daily_pnl,
            "current_drawdown": bankroll_state.current_drawdown,
            "consecutive_losses": bankroll_state.consecutive_losses,
            "win_rate": bankroll_state.win_rate,
            "risk_level": bankroll_state.risk_level,
        },
        "instruction": {
            "action": instruction.action,
            "headline": instruction.headline,
            "detail": instruction.detail,
            "position_size": instruction.position_size,
            "target_multiplier": instruction.target_multiplier,
            "stop_multiplier": instruction.stop_multiplier,
            "confidence": instruction.confidence,
            "precision_level": instruction.precision_level.value,
        },
        "recovery_plan": {
            "active": recovery_state.active if recovery_state else False,
            "strategy": recovery_state.strategy.value if recovery_state else None,
            "current_step": recovery_state.current_step if recovery_state else 0,
            "max_steps": recovery_state.max_steps if recovery_state else 0,
            "recovery_multiplier": recovery_state.recovery_multiplier if recovery_state else 1.0,
        } if recovery_state else None,
        "chase_plan": {
            "active": chase_state.active if chase_state else False,
            "strategy": chase_state.strategy.value if chase_state else None,
            "target_multiplier": chase_state.target_multiplier if chase_state else 0.0,
            "current_step": chase_state.current_step if chase_state else 0,
            "expected_value": chase_state.expected_value if chase_state else 0.0,
        } if chase_state else None,
        "reasoning": instruction.reasoning,
        "risk_analysis": instruction.risk_analysis,
        "expected_outcome": instruction.expected_outcome,
        "execution_conditions": instruction.execution_conditions,
        "safety_checks": instruction.safety_checks,
        "generated_at": db.utc_now(),
    }


def backtest_recovery_strategy(
    source: str,
    strategy_name: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Backtest a recovery strategy on historical data."""
    settings = config or megaplan_settings()
    
    # Get historical rounds
    rounds = store.history(source, settings.get("backtest_window", 10000), ingest_method="file")
    
    if not rounds:
        return {"error": "No historical data available"}
    
    # Simulate recovery strategy
    strategy_config = RECOVERY_STRATEGIES.get(strategy_name, {})
    if not strategy_config:
        return {"error": f"Unknown strategy: {strategy_name}"}
    
    # Run backtest simulation
    results = simulate_recovery_backtest(rounds, strategy_name, strategy_config, settings)
    
    return results


def simulate_recovery_backtest(
    rounds: List[Dict[str, Any]],
    strategy_name: str,
    strategy_config: Dict[str, Any],
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate recovery strategy backtest."""
    initial_bankroll = float(settings.get("initial_bankroll", 1000.0))
    bankroll = initial_bankroll
    base_size = float(settings.get("base_position_size", 10.0))
    
    consecutive_losses = 0
    recovery_active = False
    recovery_step = 0
    total_recovery_periods = 0
    successful_recoveries = 0
    
    for round_data in rounds:
        multiplier = float(round_data.get("multiplier", 1.0))
        
        # Check if recovery should trigger
        if not recovery_active and consecutive_losses >= 3:
            recovery_active = True
            recovery_step = 0
            total_recovery_periods += 1
        
        if recovery_active:
            # Calculate position size with recovery multiplier
            recovery_multiplier = calculate_recovery_multiplier(strategy_name, recovery_step, strategy_config)
            position_size = base_size * recovery_multiplier
            
            # Simulate trade
            if multiplier >= 2.0:  # Win
                bankroll += position_size * (multiplier - 1)
                consecutive_losses = 0
                recovery_step = 0
                recovery_active = False
                successful_recoveries += 1
            else:  # Loss
                bankroll -= position_size
                consecutive_losses += 1
                recovery_step += 1
                
                # Check recovery limits
                if recovery_step >= strategy_config.get("max_steps", 5):
                    recovery_active = False
                    recovery_step = 0
        else:
            # Normal trading
            position_size = base_size
            if multiplier >= 2.0:
                bankroll += position_size * (multiplier - 1)
                consecutive_losses = 0
            else:
                bankroll -= position_size
                consecutive_losses += 1
        
        # Safety stop
        if bankroll < initial_bankroll * 0.5:
            break
    
    final_pnl = bankroll - initial_bankroll
    recovery_success_rate = successful_recoveries / total_recovery_periods if total_recovery_periods > 0 else 0
    
    return {
        "strategy": strategy_name,
        "initial_bankroll": initial_bankroll,
        "final_bankroll": bankroll,
        "total_pnl": final_pnl,
        "pnl_percentage": (final_pnl / initial_bankroll) * 100 if initial_bankroll > 0 else 0,
        "total_recovery_periods": total_recovery_periods,
        "successful_recoveries": successful_recoveries,
        "recovery_success_rate": recovery_success_rate,
        "total_rounds": len(rounds),
    }


def backtest_chase_strategy(
    source: str,
    strategy_name: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Backtest a chase strategy on historical data."""
    settings = config or megaplan_settings()
    
    # Get historical rounds
    rounds = store.history(source, settings.get("backtest_window", 10000), ingest_method="file")
    
    if not rounds:
        return {"error": "No historical data available"}
    
    # Simulate chase strategy
    strategy_config = CHASE_STRATEGIES.get(strategy_name, {})
    if not strategy_config:
        return {"error": f"Unknown strategy: {strategy_name}"}
    
    # Run backtest simulation
    results = simulate_chase_backtest(rounds, strategy_name, strategy_config, settings)
    
    return results


def simulate_chase_backtest(
    rounds: List[Dict[str, Any]],
    strategy_name: str,
    strategy_config: Dict[str, Any],
    settings: Dict[str, Any],
) -> Dict[str, Any]:
    """Simulate chase strategy backtest."""
    initial_bankroll = float(settings.get("initial_bankroll", 1000.0))
    bankroll = initial_bankroll
    base_size = float(settings.get("base_position_size", 10.0))
    target_multiplier = float(strategy_config.get("target_multiplier", 50.0))
    
    chase_sequence = calculate_chase_sequence(strategy_name, strategy_config)
    total_chase_attempts = 0
    successful_chases = 0
    total_chase_cost = 0
    
    for i, round_data in enumerate(rounds):
        multiplier = float(round_data.get("multiplier", 1.0))
        
        # Simple chase logic: start chase when conditions are met
        if multiplier < 10.0 and i < len(rounds) - 10:  # Don't chase near end
            # Start chase
            chase_active = True
            chase_step = 0
            chase_cost = 0
            total_chase_attempts += 1
            
            while chase_active and chase_step < len(chase_sequence):
                if i + chase_step >= len(rounds):
                    break
                
                future_round = rounds[i + chase_step]
                future_multiplier = float(future_round.get("multiplier", 1.0))
                
                position_size = base_size * chase_sequence[chase_step]
                chase_cost += position_size
                
                if future_multiplier >= target_multiplier:
                    # Chase successful
                    bankroll += position_size * (future_multiplier - 1)
                    successful_chases += 1
                    chase_active = False
                else:
                    # Chase failed this step
                    bankroll -= position_size
                    chase_step += 1
                    
                    if chase_step >= len(chase_sequence):
                        chase_active = False
                        total_chase_cost += chase_cost
            
            # Skip ahead to avoid overlapping chases
            i += chase_step + 5
    
    final_pnl = bankroll - initial_bankroll
    chase_success_rate = successful_chases / total_chase_attempts if total_chase_attempts > 0 else 0
    
    return {
        "strategy": strategy_name,
        "target_multiplier": target_multiplier,
        "initial_bankroll": initial_bankroll,
        "final_bankroll": bankroll,
        "total_pnl": final_pnl,
        "pnl_percentage": (final_pnl / initial_bankroll) * 100 if initial_bankroll > 0 else 0,
        "total_chase_attempts": total_chase_attempts,
        "successful_chases": successful_chases,
        "chase_success_rate": chase_success_rate,
        "total_chase_cost": total_chase_cost,
        "average_chase_cost": total_chase_cost / total_chase_attempts if total_chase_attempts > 0 else 0,
    }


def compare_strategies(source: str) -> Dict[str, Any]:
    """Compare all recovery and chase strategies."""
    results = {
        "recovery_strategies": {},
        "chase_strategies": {},
    }
    
    # Test all recovery strategies
    for strategy_name in RECOVERY_STRATEGIES.keys():
        if strategy_name == "none":
            continue
        try:
            result = backtest_recovery_strategy(source, strategy_name)
            results["recovery_strategies"][strategy_name] = result
        except Exception as e:
            logger.error(f"Error backtesting recovery strategy {strategy_name}: {e}")
            results["recovery_strategies"][strategy_name] = {"error": str(e)}
    
    # Test all chase strategies
    for strategy_name in CHASE_STRATEGIES.keys():
        if strategy_name == "none":
            continue
        try:
            result = backtest_chase_strategy(source, strategy_name)
            results["chase_strategies"][strategy_name] = result
        except Exception as e:
            logger.error(f"Error backtesting chase strategy {strategy_name}: {e}")
            results["chase_strategies"][strategy_name] = {"error": str(e)}
    
    # Find best strategies
    best_recovery = max(
        results["recovery_strategies"].items(),
        key=lambda x: x[1].get("pnl_percentage", -999),
        default=(None, {})
    )
    
    best_chase = max(
        results["chase_strategies"].items(),
        key=lambda x: x[1].get("pnl_percentage", -999),
        default=(None, {})
    )
    
    results["recommendations"] = {
        "best_recovery_strategy": best_recovery[0],
        "best_recovery_pnl": best_recovery[1].get("pnl_percentage", 0),
        "best_chase_strategy": best_chase[0],
        "best_chase_pnl": best_chase[1].get("pnl_percentage", 0),
    }
    
    return results
