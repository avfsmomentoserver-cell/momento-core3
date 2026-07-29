"""Dynamic orchestrator integration with adaptive strategies.

This module integrates the new dynamic strategies with the orchestrator's
decision-making logic, enabling adaptive bet sizing, target selection, and
entry/exit decisions based on real-time market conditions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import db
from research.dynamic_strategies import (
    DynamicConfidenceStrategy,
    MomentumReversalStrategy,
    VolatilityAdaptiveStrategy,
)
from research.profit_capping import (
    ProfitCapper,
    ProfitCapConfig,
    FlexibleBalanceMapper,
    create_profit_capping_config,
)


class DynamicOrchestrator:
    """Enhanced orchestrator with dynamic strategy integration and profit capping."""
    
    def __init__(self, strategy_name: str = "dynamic_confidence", 
                 profit_cap_mode: str = "dynamic_ratio"):
        """Initialize dynamic orchestrator with specified strategy."""
        self.strategy_name = strategy_name
        self.strategy = self._load_strategy(strategy_name)
        self.fitted = False
        self._performance_history: List[Dict[str, Any]] = []
        
        # Initialize profit capping system
        self.profit_cap_config = create_profit_capping_config(profit_cap_mode)
        self.profit_capper = ProfitCapper(self.profit_cap_config)
        self.balance_mapper = FlexibleBalanceMapper(
            min_balance=self.profit_cap_config.min_balance,
            max_balance=self.profit_cap_config.max_balance
        )
        
        # Balance tracking
        self._initial_balance = self.profit_cap_config.min_balance
        self._current_balance = self._initial_balance
        
    def _load_strategy(self, strategy_name: str):
        """Load the specified dynamic strategy."""
        strategies = {
            "volatility_adaptive": VolatilityAdaptiveStrategy,
            "momentum_reversal": MomentumReversalStrategy,
            "dynamic_confidence": DynamicConfidenceStrategy,
        }
        
        strategy_cls = strategies.get(strategy_name, DynamicConfidenceStrategy)
        return strategy_cls(horizon=5, threshold=10.0)
    
    def fit_on_history(self, multipliers: List[float]) -> None:
        """Fit the strategy on historical multiplier data."""
        if not multipliers:
            return
        
        self.strategy.fit_on(multipliers)
        self.fitted = True
    
    def get_dynamic_plan(self, payload: Dict[str, Any], performance: Dict[str, Any]) -> Dict[str, Any]:
        """Generate dynamic execution plan using adaptive strategy with profit capping."""
        if not self.fitted:
            return self._get_fallback_plan(payload, performance)
        
        # Update balance from performance
        current_balance = float(performance.get("bankroll", self._current_balance))
        self.profit_capper.update_balance(current_balance)
        self._current_balance = current_balance
        
        # Check profit cap status
        profit_cap_check = self.profit_capper.check_profit_cap(
            current_balance, self._initial_balance, performance
        )
        
        # If profit cap reached, stop betting
        if profit_cap_check["cap_reached"]:
            return self._get_profit_capped_plan(profit_cap_check)
        
        # Extract recent multipliers from payload
        rounds = payload.get("recent_rounds", [])
        multipliers = [float(r.get("multiplier", 1.0)) for r in rounds]
        
        if not multipliers:
            return self._get_fallback_plan(payload, performance)
        
        # Get probability prediction from dynamic strategy
        context = [{"multiplier": m} for m in multipliers]
        probability = self.strategy.predict_proba(context)
        
        # Get betting recommendation if available
        betting_recommendation = {}
        if hasattr(self.strategy, 'get_betting_recommendation'):
            # Get feature for recommendation
            features = self.strategy.features(multipliers)
            if features:
                last_feature = features[-1]
                betting_recommendation = self.strategy.get_betting_recommendation(
                    last_feature, probability
                )
        
        # Calculate dynamic position size using profit capper
        dynamic_size = self.profit_capper.calculate_bet_size(
            current_balance, probability, performance
        )
        
        # Apply balance mapping scaling
        balance_mapping = self.balance_mapper.map_balance_to_tier(current_balance)
        scaling_factor = balance_mapping["scaling_factor"]
        dynamic_size *= scaling_factor
        
        # Apply consecutive loss adjustment
        consecutive_losses = int(performance.get("consecutive_losses", 0))
        if consecutive_losses >= 3:
            dynamic_size *= 0.5  # Reduce size after 3 losses
        elif consecutive_losses >= 2:
            dynamic_size *= 0.7
        
        # Get dynamic target multiplier
        target_multiplier = betting_recommendation.get("target_multiplier", 2.0)
        
        # Get dynamic confidence threshold
        confidence_threshold = betting_recommendation.get("confidence_threshold", 0.5)
        
        # Adjust based on profit cap proximity
        if profit_cap_check["cap_ratio"] >= 0.9:
            confidence_threshold *= 1.3  # Higher threshold near cap
            dynamic_size *= 0.5  # Reduce size near cap
        elif profit_cap_check["cap_ratio"] >= 0.75:
            confidence_threshold *= 1.1
            dynamic_size *= 0.7
        
        # Make entry decision
        should_enter = probability >= confidence_threshold
        
        # Apply safety checks
        if consecutive_losses >= 5:
            should_enter = False
            entry_reason = "MAX_CONSECUTIVE_LOSSES"
        elif performance.get("daily_pnl", 0) <= -performance.get("daily_loss_limit", 0.15) * current_balance:
            should_enter = False
            entry_reason = "DAILY_LOSS_LIMIT"
        else:
            entry_reason = "CONFIDENCE_ABOVE_THRESHOLD" if should_enter else "CONFIDENCE_BELOW_THRESHOLD"
        
        # Build dynamic plan with profit capping
        plan = {
            "strategy": self.strategy_name,
            "probability": probability,
            "betting_recommendation": betting_recommendation,
            "position_size": round(dynamic_size, 2) if should_enter else 0.0,
            "target_multiplier": target_multiplier,
            "stop_multiplier": round(target_multiplier * 0.6, 2),
            "confidence_threshold": confidence_threshold,
            "should_enter": should_enter,
            "entry_reason": entry_reason,
            "strategy_type": betting_recommendation.get("strategy", "unknown"),
            "profit_capping": {
                "current_profit": profit_cap_check["current_profit"],
                "profit_cap": profit_cap_check["profit_cap"],
                "cap_ratio": profit_cap_check["cap_ratio"],
                "cap_reached": profit_cap_check["cap_reached"],
                "action_required": profit_cap_check["action_required"],
                "remaining_capacity": profit_cap_check["remaining_capacity"],
            },
            "balance_mapping": {
                "tier": balance_mapping["tier"],
                "scaling_factor": scaling_factor,
                "risk_level": balance_mapping["risk_level"],
                "position_in_range": balance_mapping["position_in_range"],
            },
            "dynamic_features": {
                "consecutive_losses": consecutive_losses,
                "size_adjustment": scaling_factor,
            },
        }
        
        return plan
    
    def _get_fallback_plan(self, payload: Dict[str, Any], performance: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to conservative plan when strategy not fitted."""
        return {
            "strategy": self.strategy_name,
            "probability": 0.0,
            "betting_recommendation": {},
            "position_size": 0.0,
            "target_multiplier": 2.0,
            "stop_multiplier": 1.2,
            "confidence_threshold": 0.5,
            "should_enter": False,
            "entry_reason": "STRATEGY_NOT_FITTED",
            "strategy_type": "fallback",
            "profit_capping": {},
            "balance_mapping": {},
            "dynamic_features": {},
        }
    
    def _get_profit_capped_plan(self, profit_cap_check: Dict[str, Any]) -> Dict[str, Any]:
        """Return plan when profit cap is reached."""
        return {
            "strategy": self.strategy_name,
            "probability": 0.0,
            "betting_recommendation": {},
            "position_size": 0.0,
            "target_multiplier": 2.0,
            "stop_multiplier": 1.2,
            "confidence_threshold": 1.0,  # Maximum threshold to prevent entries
            "should_enter": False,
            "entry_reason": f"PROFIT_CAP_REACHED: {profit_cap_check['action_required']}",
            "strategy_type": "profit_capped",
            "profit_capping": {
                "current_profit": profit_cap_check["current_profit"],
                "profit_cap": profit_cap_check["profit_cap"],
                "cap_ratio": profit_cap_check["cap_ratio"],
                "cap_reached": True,
                "action_required": profit_cap_check["action_required"],
                "remaining_capacity": profit_cap_check["remaining_capacity"],
            },
            "balance_mapping": self.balance_mapper.map_balance_to_tier(self._current_balance),
            "dynamic_features": {
                "consecutive_losses": 0,
                "size_adjustment": 0.0,
            },
        }
    
    def update_performance(self, result: Dict[str, Any]) -> None:
        """Update performance history with latest result."""
        self._performance_history.append({
            "timestamp": db.utc_now(),
            "result": result,
        })
        
        # Keep only last 100 results
        if len(self._performance_history) > 100:
            self._performance_history = self._performance_history[-100:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of recent performance."""
        if not self._performance_history:
            return {"status": "no_data"}
        
        recent = self._performance_history[-20:]  # Last 20 results
        wins = sum(1 for r in recent if r["result"].get("outcome") == "WIN")
        total = len(recent)
        
        return {
            "total_trades": len(self._performance_history),
            "recent_win_rate": (wins / total * 100) if total > 0 else 0,
            "recent_trades": total,
            "strategy": self.strategy_name,
            "fitted": self.fitted,
        }


def create_dynamic_orchestrator_module(strategy_name: str = "dynamic_confidence") -> Dict[str, Any]:
    """Create a dynamic orchestrator module configuration."""
    strategy_configs = {
        "volatility_adaptive": {
            "label": "Volatility Adaptive",
            "description": "Adapts bet size and targets based on market volatility",
            "min_confidence": 0.3,
            "size_multiplier": 1.5,
            "target_multiplier": 1.3,
            "max_consecutive_losses": 4,
            "patience_bias": 0.8,
        },
        "momentum_reversal": {
            "label": "Momentum Reversal",
            "description": "Hybrid momentum-reversal for optimal entry points",
            "min_confidence": 0.35,
            "size_multiplier": 1.4,
            "target_multiplier": 1.4,
            "max_consecutive_losses": 4,
            "patience_bias": 0.9,
        },
        "dynamic_confidence": {
            "label": "Dynamic Confidence",
            "description": "Ensemble strategy with multi-factor confidence calibration",
            "min_confidence": 0.25,
            "size_multiplier": 1.6,
            "target_multiplier": 1.3,
            "max_consecutive_losses": 4,
            "patience_bias": 0.7,
        },
    }
    
    return strategy_configs.get(strategy_name, strategy_configs["dynamic_confidence"])


def integrate_with_orchestrator(payload: Dict[str, Any], performance: Dict[str, Any], 
                                strategy_name: str = "dynamic_confidence") -> Dict[str, Any]:
    """Integration function for existing orchestrator."""
    dynamic_orch = DynamicOrchestrator(strategy_name)
    
    # Fit on recent history if available
    recent_rounds = payload.get("recent_rounds", [])
    if recent_rounds:
        multipliers = [float(r.get("multiplier", 1.0)) for r in recent_rounds]
        dynamic_orch.fit_on_history(multipliers)
    
    # Get dynamic plan
    dynamic_plan = dynamic_orch.get_dynamic_plan(payload, performance)
    
    # Merge with existing orchestrator structure
    module_config = create_dynamic_orchestrator_module(strategy_name)
    
    return {
        "module": {
            "id": f"dynamic_{strategy_name}",
            **module_config,
        },
        "dynamic_plan": dynamic_plan,
        "settings": {
            "strategy": strategy_name,
            "dynamic_mode": True,
            "adaptive_sizing": True,
            "adaptive_targets": True,
        },
        "instruction": {
            "action": "ENTER" if dynamic_plan["should_enter"] else "WAIT",
            "headline": f"{'Enter next round' if dynamic_plan['should_enter'] else 'Wait for signal'}, exit at {dynamic_plan['target_multiplier']:.2f}x",
            "detail": f"{dynamic_plan['strategy_type']} strategy with {dynamic_plan['probability']:.1%} confidence. {dynamic_plan['entry_reason']}",
            "target_multiplier": dynamic_plan["target_multiplier"],
            "stop_multiplier": dynamic_plan["stop_multiplier"],
            "position_size": dynamic_plan["position_size"],
            "confidence": dynamic_plan["probability"],
            "confidence_label": "HIGH" if dynamic_plan["probability"] >= 0.7 else ("MEDIUM" if dynamic_plan["probability"] >= 0.4 else "LOW"),
        },
        "generated_at": db.utc_now(),
    }
