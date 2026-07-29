"""Profit capping and balance management system.

This module implements a robust profit capping mechanism with flexible balance
mapping to ensure safe and sustainable betting operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum


class ProfitCapMode(Enum):
    """Profit capping modes."""
    FIXED_RATIO = "fixed_ratio"  # Fixed profit-to-balance ratio
    DYNAMIC_RATIO = "dynamic_ratio"  # Dynamic ratio based on performance
    TIERED = "tiered"  # Tiered profit caps based on balance levels
    HYBRID = "hybrid"  # Combination of fixed and dynamic


@dataclass
class BalanceTier:
    """Balance tier configuration."""
    min_balance: float
    max_balance: float
    profit_cap_ratio: float  # Maximum profit as ratio of balance
    bet_size_ratio: float  # Maximum bet as ratio of balance
    description: str


@dataclass
class ProfitCapConfig:
    """Profit capping configuration."""
    mode: ProfitCapMode = ProfitCapMode.DYNAMIC_RATIO
    base_profit_ratio: float = 0.20  # 20% profit cap base
    max_profit_ratio: float = 0.50  # 50% maximum profit cap
    min_balance: float = 100.0
    max_balance: float = 10000.0
    balance_tiers: List[BalanceTier] = None
    dynamic_adjustment_factor: float = 0.1  # Adjustment based on performance
    enable_profit_locking: bool = True  # Lock profits when cap reached
    enable_auto_withdrawal: bool = False  # Auto-withdraw when cap reached
    
    def __post_init__(self):
        if self.balance_tiers is None:
            self.balance_tiers = self._default_tiers()
    
    def _default_tiers(self) -> List[BalanceTier]:
        """Default balance tiers."""
        return [
            BalanceTier(100, 500, 0.25, 0.05, "Starter tier - conservative limits"),
            BalanceTier(500, 2000, 0.30, 0.08, "Growth tier - moderate limits"),
            BalanceTier(2000, 5000, 0.40, 0.10, "Advanced tier - higher limits"),
            BalanceTier(5000, 10000, 0.50, 0.12, "Expert tier - maximum limits"),
            BalanceTier(10000, float('inf'), 0.50, 0.15, "Professional tier - highest limits"),
        ]


class ProfitCapper:
    """Profit capping and balance management system."""
    
    def __init__(self, config: ProfitCapConfig):
        self.config = config
        self._profit_history: List[Dict[str, Any]] = []
        self._current_balance = config.min_balance
        self._initial_balance = config.min_balance
        self._locked_profits = 0.0
        self._withdrawn_profits = 0.0
    
    def calculate_profit_cap(self, current_balance: float, performance: Dict[str, Any]) -> float:
        """Calculate maximum allowable profit based on configuration."""
        if current_balance <= 0:
            return 0.0
        
        if self.config.mode == ProfitCapMode.FIXED_RATIO:
            return current_balance * self.config.base_profit_ratio
        
        elif self.config.mode == ProfitCapMode.DYNAMIC_RATIO:
            base_cap = current_balance * self.config.base_profit_ratio
            
            # Dynamic adjustment based on performance
            win_rate = performance.get("win_rate", 0.5)
            consecutive_losses = performance.get("consecutive_losses", 0)
            
            # Increase cap for high win rate, decrease for losses
            performance_factor = 1.0 + (win_rate - 0.5) * self.config.dynamic_adjustment_factor
            loss_factor = max(0.5, 1.0 - consecutive_losses * 0.1)
            
            dynamic_cap = base_cap * performance_factor * loss_factor
            return min(dynamic_cap, current_balance * self.config.max_profit_ratio)
        
        elif self.config.mode == ProfitCapMode.TIERED:
            tier = self._get_balance_tier(current_balance)
            return current_balance * tier.profit_cap_ratio
        
        elif self.config.mode == ProfitCapMode.HYBRID:
            # Combine tier-based with dynamic adjustment
            tier = self._get_balance_tier(current_balance)
            tier_cap = current_balance * tier.profit_cap_ratio
            
            # Apply dynamic adjustment
            win_rate = performance.get("win_rate", 0.5)
            adjustment = 1.0 + (win_rate - 0.5) * 0.05
            
            hybrid_cap = tier_cap * adjustment
            return min(hybrid_cap, current_balance * self.config.max_profit_ratio)
        
        return current_balance * self.config.base_profit_ratio
    
    def _get_balance_tier(self, balance: float) -> BalanceTier:
        """Get applicable balance tier for given balance."""
        for tier in self.config.balance_tiers:
            if tier.min_balance <= balance < tier.max_balance:
                return tier
        return self.config.balance_tiers[-1]  # Return highest tier
    
    def calculate_bet_size(self, current_balance: float, confidence: float, 
                         performance: Dict[str, Any]) -> float:
        """Calculate maximum allowable bet size."""
        if current_balance <= 0:
            return 0.0
        
        tier = self._get_balance_tier(current_balance)
        base_bet_ratio = tier.bet_size_ratio
        
        # Confidence-based adjustment
        confidence_factor = max(0.5, min(1.5, confidence * 2))
        
        # Performance-based adjustment
        consecutive_losses = performance.get("consecutive_losses", 0)
        loss_factor = max(0.3, 1.0 - consecutive_losses * 0.15)
        
        # Calculate bet size
        bet_size = current_balance * base_bet_ratio * confidence_factor * loss_factor
        
        # Ensure minimum bet
        min_bet = self.config.min_balance * 0.01  # 1% of minimum balance
        return max(min_bet, bet_size)
    
    def check_profit_cap(self, current_balance: float, initial_balance: float, 
                        performance: Dict[str, Any]) -> Dict[str, Any]:
        """Check if profit cap has been reached."""
        current_profit = current_balance - initial_balance
        profit_cap = self.calculate_profit_cap(current_balance, performance)
        
        cap_reached = current_profit >= profit_cap
        cap_ratio = current_profit / profit_cap if profit_cap > 0 else 0
        
        return {
            "current_profit": current_profit,
            "profit_cap": profit_cap,
            "cap_reached": cap_reached,
            "cap_ratio": cap_ratio,
            "remaining_capacity": max(0, profit_cap - current_profit),
            "action_required": self._determine_cap_action(cap_reached, cap_ratio),
        }
    
    def _determine_cap_action(self, cap_reached: bool, cap_ratio: float) -> str:
        """Determine required action based on cap status."""
        if cap_reached:
            if self.config.enable_profit_locking:
                return "LOCK_PROFITS"
            elif self.config.enable_auto_withdrawal:
                return "AUTO_WITHDRAW"
            else:
                return "STOP_BETTING"
        elif cap_ratio >= 0.9:
            return "REDUCE_SIZE"
        elif cap_ratio >= 0.75:
            return "MONITOR_CLOSELY"
        else:
            return "CONTINUE_NORMAL"
    
    def update_balance(self, new_balance: float) -> None:
        """Update current balance."""
        self._current_balance = new_balance
    
    def lock_profits(self, amount: float) -> None:
        """Lock profits to prevent further betting with locked amount."""
        if amount > 0:
            self._locked_profits += amount
            self._current_balance -= amount
    
    def withdraw_profits(self, amount: float) -> None:
        """Record profit withdrawal."""
        if amount > 0:
            self._withdrawn_profits += amount
            self._current_balance -= amount
    
    def get_balance_summary(self) -> Dict[str, Any]:
        """Get comprehensive balance summary."""
        current_profit = self._current_balance - self._initial_balance
        
        return {
            "initial_balance": self._initial_balance,
            "current_balance": self._current_balance,
            "locked_profits": self._locked_profits,
            "withdrawn_profits": self._withdrawn_profits,
            "available_balance": self._current_balance - self._locked_profits,
            "current_profit": current_profit,
            "profit_ratio": current_profit / self._initial_balance if self._initial_balance > 0 else 0,
            "total_realized_profits": self._locked_profits + self._withdrawn_profits,
            "active_tier": self._get_balance_tier(self._current_balance).description,
        }
    
    def get_profit_mapping(self, target_profit: float) -> Dict[str, Any]:
        """Map target profit to required balance and betting parameters."""
        if self.config.mode == ProfitCapMode.TIERED:
            # Find tier that can support target profit
            for tier in self.config.balance_tiers:
                required_balance = target_profit / tier.profit_cap_ratio
                if tier.min_balance <= required_balance < tier.max_balance:
                    return {
                        "target_profit": target_profit,
                        "required_balance": required_balance,
                        "applicable_tier": tier.description,
                        "max_bet_size": required_balance * tier.bet_size_ratio,
                        "profit_cap_ratio": tier.profit_cap_ratio,
                        "feasible": True,
                    }
        
        # Default calculation
        required_balance = target_profit / self.config.base_profit_ratio
        return {
            "target_profit": target_profit,
            "required_balance": required_balance,
            "applicable_tier": "standard",
            "max_bet_size": required_balance * 0.10,
            "profit_cap_ratio": self.config.base_profit_ratio,
            "feasible": required_balance <= self.config.max_balance,
        }


class FlexibleBalanceMapper:
    """Flexible balance mapping for dynamic scaling."""
    
    def __init__(self, min_balance: float = 100.0, max_balance: float = 10000.0):
        self.min_balance = min_balance
        self.max_balance = max_balance
        self._mapping_history: List[Dict[str, Any]] = []
    
    def map_balance_to_tier(self, balance: float) -> Dict[str, Any]:
        """Map balance to appropriate tier with scaling factors."""
        if balance < self.min_balance:
            return {
                "tier": "below_minimum",
                "scaling_factor": 0.5,
                "risk_level": "high",
                "recommended_action": "increase_balance",
            }
        
        # Calculate position in balance range (0-1)
        balance_range = self.max_balance - self.min_balance
        position = (balance - self.min_balance) / balance_range if balance_range > 0 else 0
        
        # Determine tier based on position
        if position < 0.2:
            tier = "starter"
            scaling_factor = 0.6
            risk_level = "moderate"
        elif position < 0.5:
            tier = "growth"
            scaling_factor = 0.8
            risk_level = "moderate"
        elif position < 0.8:
            tier = "advanced"
            scaling_factor = 1.0
            risk_level = "normal"
        else:
            tier = "expert"
            scaling_factor = 1.2
            risk_level = "normal"
        
        return {
            "tier": tier,
            "scaling_factor": scaling_factor,
            "risk_level": risk_level,
            "position_in_range": position,
            "recommended_action": "maintain" if 0.2 <= position <= 0.8 else "adjust",
        }
    
    def calculate_optimal_bet_size(self, balance: float, base_confidence: float,
                                  risk_tolerance: str = "moderate") -> float:
        """Calculate optimal bet size based on balance mapping."""
        mapping = self.map_balance_to_tier(balance)
        scaling_factor = mapping["scaling_factor"]
        
        # Risk-based adjustments
        risk_multipliers = {
            "conservative": 0.5,
            "moderate": 0.8,
            "aggressive": 1.2,
        }
        
        risk_multiplier = risk_multipliers.get(risk_tolerance, 0.8)
        confidence_multiplier = max(0.5, min(1.5, base_confidence * 2))
        
        # Base bet size calculation
        base_bet = balance * 0.02  # 2% base
        optimal_bet = base_bet * scaling_factor * risk_multiplier * confidence_multiplier
        
        # Ensure minimum bet
        min_bet = self.min_balance * 0.01
        return max(min_bet, optimal_bet)
    
    def simulate_profit_trajectory(self, initial_balance: float, win_rate: float,
                                  avg_win_multiplier: float, n_rounds: int) -> List[Dict[str, Any]]:
        """Simulate profit trajectory with balance mapping."""
        balance = initial_balance
        trajectory = []
        
        for round_num in range(n_rounds):
            mapping = self.map_balance_to_tier(balance)
            bet_size = self.calculate_optimal_bet_size(balance, 0.7, "moderate")
            
            # Simulate outcome
            import random
            win = random.random() < win_rate
            
            if win:
                profit = bet_size * (avg_win_multiplier - 1)
                balance += profit
            else:
                loss = bet_size * 0.9  # Assume 90% loss on loss
                balance -= loss
            
            # Ensure balance doesn't go below minimum
            balance = max(balance, self.min_balance * 0.5)
            
            trajectory.append({
                "round": round_num + 1,
                "balance": balance,
                "bet_size": bet_size,
                "tier": mapping["tier"],
                "outcome": "win" if win else "loss",
                "profit": balance - initial_balance,
            })
        
        return trajectory


def create_profit_capping_config(mode: str = "dynamic_ratio") -> ProfitCapConfig:
    """Create profit capping configuration with sensible defaults."""
    mode_enum = ProfitCapMode(mode) if isinstance(mode, str) else mode
    
    return ProfitCapConfig(
        mode=mode_enum,
        base_profit_ratio=0.20,
        max_profit_ratio=0.50,
        min_balance=100.0,
        max_balance=10000.0,
        dynamic_adjustment_factor=0.1,
        enable_profit_locking=True,
        enable_auto_withdrawal=False,
    )
