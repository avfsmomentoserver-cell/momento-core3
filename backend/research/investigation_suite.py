"""Investigation and Improvement Suite for Strategy Profit Margins.

This suite extends the falsification framework to focus on practical improvement:
- Profit margin analysis for orchestrator strategies
- Safe targeted betting with configurable parameters
- Flexible target/enter/don't enter logic
- Live accuracy testing with real-time feedback
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .labels import DEFAULT_HORIZON, DEFAULT_THRESHOLD, horizon_labels
from .loader import load_exports, multipliers
from .metrics import paper_pnl, score_forecasts
from .runner import run_strategy
from .strategies import STRATEGY_REGISTRY, ResearchStrategy

logger = logging.getLogger("momento.investigation")


@dataclass
class BettingConfig:
    """Safe targeted betting configuration."""
    initial_balance: float = 100.0
    min_bet: float = 0.5
    max_bet_pct: float = 0.05  # Max 5% of balance per bet
    safety_margin: float = 0.10  # Stop if down 10%
    target_profit_pct: float = 0.20  # Stop if up 20%
    max_consecutive_losses: int = 3
    recovery_mode: bool = False
    recovery_multiplier: float = 1.5  # Increase bet size in recovery mode


@dataclass
class InvestigationResult:
    """Results from a single investigation run."""
    strategy_name: str
    total_rounds: int
    bets_placed: int
    wins: int
    losses: int
    net_profit: float
    roi_pct: float
    max_drawdown: float
    max_balance: float
    min_balance: float
    final_balance: float
    win_rate: float
    avg_bet_size: float
    consecutive_losses: int = 0
    max_consecutive_losses: int = 0
    entry_decisions: List[str] = field(default_factory=list)
    exit_decisions: List[str] = field(default_factory=list)
    profit_timeline: List[float] = field(default_factory=list)


class OrchestratorSimulator:
    """Simulate orchestrator decision-making with safe betting rules."""
    
    def __init__(self, config: BettingConfig):
        self.config = config
        self.reset()
    
    def reset(self) -> None:
        """Reset simulator state."""
        self.balance = self.config.initial_balance
        self.initial_balance = self.config.initial_balance
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        self.max_balance = self.balance
        self.min_balance = self.balance
        self.bets_placed = 0
        self.wins = 0
        self.losses = 0
        self.profit_timeline = [self.balance]
        self.entry_decisions = []
        self.exit_decisions = []
        self.stopped_reason = None
    
    def _calculate_bet_size(self, confidence: float) -> float:
        """Calculate safe bet size based on confidence and balance."""
        base_bet = self.config.min_bet
        max_bet = self.balance * self.config.max_bet_pct
        
        # Scale bet by confidence (0.0 to 1.0)
        confidence_factor = max(0.5, confidence)
        suggested_bet = base_bet * confidence_factor
        
        # Apply recovery mode if enabled
        if self.config.recovery_mode and self.consecutive_losses >= 2:
            suggested_bet *= self.config.recovery_multiplier
        
        # Respect limits
        bet_size = min(suggested_bet, max_bet)
        return max(bet_size, self.config.min_bet)
    
    def _should_enter(self, probability: float, confidence_threshold: float = 0.5) -> Tuple[bool, str]:
        """Determine if we should enter a bet."""
        # Safety checks
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            return False, "STOP: Max consecutive losses reached"
        
        if self.balance <= self.initial_balance * (1 - self.config.safety_margin):
            return False, "STOP: Safety margin breached"
        
        if self.balance >= self.initial_balance * (1 + self.config.target_profit_pct):
            return False, "STOP: Target profit reached"
        
        # Flexible entry logic
        if probability >= confidence_threshold:
            return True, f"ENTER: Probability {probability:.2%} >= threshold {confidence_threshold:.2%}"
        
        # Consider entering with lower probability if in recovery mode
        if self.config.recovery_mode and probability >= 0.35:
            return True, f"ENTER: Recovery mode, probability {probability:.2%}"
        
        return False, f"DONT_ENTER: Probability {probability:.2%} below threshold"
    
    def _should_exit(self, current_multiplier: float, target_multiplier: float, 
                    stop_multiplier: float) -> Tuple[bool, str]:
        """Determine if we should exit a position."""
        if current_multiplier >= target_multiplier:
            return True, f"EXIT: Target reached at {current_multiplier:.2f}x"
        
        if current_multiplier <= stop_multiplier:
            return True, f"EXIT: Stop loss hit at {current_multiplier:.2f}x"
        
        return False, f"HOLD: Current {current_multiplier:.2f}x, target {target_multiplier:.2f}x"
    
    def simulate_round(self, probability: float, actual_multiplier: float,
                      target_multiplier: float = 2.0, 
                      confidence_threshold: float = 0.5) -> Optional[Dict[str, Any]]:
        """Simulate a single betting round."""
        if self.stopped_reason:
            return None
        
        # Entry decision
        should_enter, entry_reason = self._should_enter(probability, confidence_threshold)
        self.entry_decisions.append(entry_reason)
        
        if not should_enter:
            self.profit_timeline.append(self.balance)
            return {
                "entered": False,
                "reason": entry_reason,
                "balance": self.balance,
            }
        
        # Calculate bet size
        bet_size = self._calculate_bet_size(probability)
        
        # Check if we can afford the bet
        if bet_size > self.balance:
            self.entry_decisions.append(f"SKIP: Insufficient balance for bet {bet_size:.2f}")
            self.profit_timeline.append(self.balance)
            return {
                "entered": False,
                "reason": f"Insufficient balance for bet {bet_size:.2f}",
                "balance": self.balance,
            }
        
        # Place bet
        self.bets_placed += 1
        self.balance -= bet_size
        
        # Exit decision
        stop_multiplier = max(1.01, target_multiplier * 0.55)
        should_exit, exit_reason = self._should_exit(actual_multiplier, target_multiplier, stop_multiplier)
        self.exit_decisions.append(exit_reason)
        
        # Calculate outcome
        if actual_multiplier >= target_multiplier:
            # Win
            payout = bet_size * target_multiplier
            self.balance += payout
            self.wins += 1
            self.consecutive_losses = 0
            outcome = "WIN"
        else:
            # Loss
            self.balance += bet_size * actual_multiplier  # Get back whatever crashed at
            self.losses += 1
            self.consecutive_losses += 1
            self.max_consecutive_losses = max(self.max_consecutive_losses, self.consecutive_losses)
            outcome = "LOSS"
        
        # Update statistics
        self.max_balance = max(self.max_balance, self.balance)
        self.min_balance = min(self.min_balance, self.balance)
        self.profit_timeline.append(self.balance)
        
        # Check if we should stop
        if self.balance <= self.initial_balance * (1 - self.config.safety_margin):
            self.stopped_reason = "Safety margin breached"
        elif self.balance >= self.initial_balance * (1 + self.config.target_profit_pct):
            self.stopped_reason = "Target profit reached"
        elif self.consecutive_losses >= self.config.max_consecutive_losses:
            self.stopped_reason = "Max consecutive losses reached"
        
        return {
            "entered": True,
            "bet_size": bet_size,
            "probability": probability,
            "actual_multiplier": actual_multiplier,
            "target_multiplier": target_multiplier,
            "outcome": outcome,
            "payout": payout if outcome == "WIN" else bet_size * actual_multiplier,
            "balance": self.balance,
            "entry_reason": entry_reason,
            "exit_reason": exit_reason,
        }
    
    def get_result(self, strategy_name: str, total_rounds: int) -> InvestigationResult:
        """Get investigation results."""
        net_profit = self.balance - self.initial_balance
        roi_pct = (net_profit / self.initial_balance) * 100 if self.initial_balance > 0 else 0
        
        # Calculate max drawdown
        peak = max(self.profit_timeline)
        trough = min(self.profit_timeline)
        max_drawdown = ((peak - trough) / peak) * 100 if peak > 0 else 0
        
        win_rate = (self.wins / self.bets_placed) * 100 if self.bets_placed > 0 else 0
        avg_bet_size = (self.initial_balance - self.balance + net_profit) / self.bets_placed if self.bets_placed > 0 else 0
        
        return InvestigationResult(
            strategy_name=strategy_name,
            total_rounds=total_rounds,
            bets_placed=self.bets_placed,
            wins=self.wins,
            losses=self.losses,
            net_profit=net_profit,
            roi_pct=roi_pct,
            max_drawdown=max_drawdown,
            max_balance=self.max_balance,
            min_balance=self.min_balance,
            final_balance=self.balance,
            win_rate=win_rate,
            avg_bet_size=avg_bet_size,
            consecutive_losses=self.consecutive_losses,
            max_consecutive_losses=self.max_consecutive_losses,
            entry_decisions=self.entry_decisions,
            exit_decisions=self.exit_decisions,
            profit_timeline=self.profit_timeline,
        )


def investigate_strategy(
    strategy_cls: type[ResearchStrategy],
    values: Sequence[float],
    betting_config: BettingConfig,
    *,
    horizon: int = DEFAULT_HORIZON,
    threshold: float = DEFAULT_THRESHOLD,
    target_multiplier: float = 2.0,
    confidence_threshold: float = 0.5,
) -> InvestigationResult:
    """Investigate a strategy with safe targeted betting."""
    logger.info(f"Investigating {strategy_cls.name} with {len(values)} rounds")
    
    # Fit strategy on first 80% of data
    split_point = int(len(values) * 0.8)
    train_values = values[:split_point]
    test_values = values[split_point:]
    
    strategy = strategy_cls(horizon=horizon, threshold=threshold)
    strategy.fit_on(train_values)
    
    # Simulate betting on test data
    simulator = OrchestratorSimulator(betting_config)
    
    for i, multiplier in enumerate(test_values):
        if simulator.stopped_reason:
            break
        
        # Get prediction for this round
        context = [{"multiplier": m} for m in test_values[:i]]
        probability = strategy.predict_proba(context)
        
        # Simulate round
        simulator.simulate_round(
            probability=probability,
            actual_multiplier=multiplier,
            target_multiplier=target_multiplier,
            confidence_threshold=confidence_threshold,
        )
    
    return simulator.get_result(strategy_cls.name, len(test_values))


def run_investigation_suite(
    paths: Sequence[str],
    betting_config: BettingConfig,
    *,
    horizon: int = DEFAULT_HORIZON,
    threshold: float = DEFAULT_THRESHOLD,
    target_multiplier: float = 2.0,
    confidence_threshold: float = 0.5,
    strategies: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Run full investigation suite across multiple strategies."""
    rounds, load_report = load_exports(paths)
    values = multipliers(rounds)
    
    names = list(strategies) if strategies else list(STRATEGY_REGISTRY)
    unknown = [n for n in names if n not in STRATEGY_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown strategies: {unknown}")
    
    results = []
    for name in names:
        try:
            result = investigate_strategy(
                STRATEGY_REGISTRY[name],
                values,
                betting_config,
                horizon=horizon,
                threshold=threshold,
                target_multiplier=target_multiplier,
                confidence_threshold=confidence_threshold,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Error investigating {name}: {e}")
            results.append(None)
    
    return {
        "meta": {
            "suite": "momento-investigation",
            "purpose": "Profit margin investigation with safe targeted betting",
            "target": f"moonshot >= {threshold}x within {horizon} rounds",
            "betting_config": {
                "initial_balance": betting_config.initial_balance,
                "min_bet": betting_config.min_bet,
                "max_bet_pct": betting_config.max_bet_pct,
                "safety_margin": betting_config.safety_margin,
                "target_profit_pct": betting_config.target_profit_pct,
                "max_consecutive_losses": betting_config.max_consecutive_losses,
            },
        },
        "load": load_report.as_dict(),
        "strategies": [
            {
                "name": r.strategy_name if r else "ERROR",
                "total_rounds": r.total_rounds if r else 0,
                "bets_placed": r.bets_placed if r else 0,
                "wins": r.wins if r else 0,
                "losses": r.losses if r else 0,
                "net_profit": r.net_profit if r else 0,
                "roi_pct": r.roi_pct if r else 0,
                "max_drawdown": r.max_drawdown if r else 0,
                "final_balance": r.final_balance if r else 0,
                "win_rate": r.win_rate if r else 0,
                "avg_bet_size": r.avg_bet_size if r else 0,
                "max_consecutive_losses": r.max_consecutive_losses if r else 0,
                "entry_decisions_summary": {
                    "enter": sum(1 for d in r.entry_decisions if d.startswith("ENTER")) if r else 0,
                    "dont_enter": sum(1 for d in r.entry_decisions if d.startswith("DONT_ENTER")) if r else 0,
                    "stop": sum(1 for d in r.entry_decisions if d.startswith("STOP")) if r else 0,
                } if r else {},
            }
            for r in results
        ],
    }


def run_live_accuracy_test(
    strategy_cls: type[ResearchStrategy],
    n_rounds: int = 20,
    *,
    horizon: int = DEFAULT_HORIZON,
    threshold: float = DEFAULT_THRESHOLD,
    betting_config: Optional[BettingConfig] = None,
    confidence_threshold: float = 0.5,
) -> Dict[str, Any]:
    """Run a live accuracy test with specified number of rounds."""
    logger.info(f"Running live accuracy test for {n_rounds} rounds")
    
    if betting_config is None:
        betting_config = BettingConfig()
    
    # Generate synthetic test data (in production, this would be live data)
    import random
    random.seed(42)
    
    # Generate realistic training data with some moonshots
    train_values = []
    for _ in range(500):
        u = random.random()
        if u >= 0.97:
            train_values.append(min(10_000.0, 0.97 / (1.0 - u)))
        else:
            train_values.append(1.0 + random.random() * 2.0)  # Some variance
    
    # Generate test data
    test_values = []
    for _ in range(n_rounds):
        u = random.random()
        if u >= 0.97:
            test_values.append(min(10_000.0, 0.97 / (1.0 - u)))
        else:
            test_values.append(1.0 + random.random() * 2.0)  # Some variance
    
    # Fit on realistic training data
    strategy = strategy_cls(horizon=horizon, threshold=threshold)
    strategy.fit_on(train_values)
    
    # Debug: Check base rate
    if hasattr(strategy, '_base_rate'):
        logger.info(f"Strategy {strategy_cls.name} base rate: {strategy._base_rate:.4f}")
    
    # Run live simulation
    simulator = OrchestratorSimulator(betting_config)
    
    live_results = []
    for i, multiplier in enumerate(test_values):
        context = [{"multiplier": m} for m in test_values[:i]]
        probability = strategy.predict_proba(context)
        
        result = simulator.simulate_round(
            probability=probability,
            actual_multiplier=multiplier,
            target_multiplier=2.0,
            confidence_threshold=confidence_threshold,
        )
        
        live_results.append({
            "round": i + 1,
            "probability": probability,
            "actual_multiplier": multiplier,
            "result": result,
        })
    
    investigation_result = simulator.get_result(strategy_cls.name, n_rounds)
    
    return {
        "meta": {
            "test_type": "live_accuracy",
            "n_rounds": n_rounds,
            "strategy": strategy_cls.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "investigation_result": {
            "strategy_name": investigation_result.strategy_name,
            "bets_placed": investigation_result.bets_placed,
            "wins": investigation_result.wins,
            "losses": investigation_result.losses,
            "net_profit": investigation_result.net_profit,
            "roi_pct": investigation_result.roi_pct,
            "win_rate": investigation_result.win_rate,
            "final_balance": investigation_result.final_balance,
        },
        "live_rounds": live_results,
    }
