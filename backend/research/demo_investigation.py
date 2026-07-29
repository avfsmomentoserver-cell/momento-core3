#!/usr/bin/env python3
"""Demonstration investigation suite with synthetic data."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.investigation_suite import (
    BettingConfig,
    investigate_strategy,
    OrchestratorSimulator,
)
from research.strategies import BaseRateStrategy, DryStreakStrategy, TimeBasedPatternStrategy


def generate_realistic_data(n_rounds: int = 1000, seed: int = 42):
    """Generate realistic crash game data."""
    import random
    random.seed(seed)
    
    values = []
    for _ in range(n_rounds):
        u = random.random()
        if u >= 0.97:
            # Moonshot (3% chance)
            values.append(min(10_000.0, 0.97 / (1.0 - u)))
        elif u >= 0.85:
            # High multiplier (12% chance)
            values.append(2.0 + random.random() * 8.0)
        elif u >= 0.60:
            # Medium multiplier (25% chance)
            values.append(1.5 + random.random() * 1.5)
        else:
            # Low multiplier (60% chance)
            values.append(1.0 + random.random() * 0.5)
    
    return values


def run_comprehensive_investigation():
    """Run comprehensive investigation across strategies."""
    print("=== Investigation Suite: Strategy Profit Margin Analysis ===\n")
    
    # Generate test data
    print("Generating realistic test data...")
    test_data = generate_realistic_data(n_rounds=2000, seed=42)
    
    # Test configurations
    configs = [
        ("Conservative", BettingConfig(initial_balance=100, min_bet=0.5, max_bet_pct=0.02, safety_margin=0.05, max_consecutive_losses=2)),
        ("Balanced", BettingConfig(initial_balance=100, min_bet=0.5, max_bet_pct=0.05, safety_margin=0.10, max_consecutive_losses=3)),
        ("Aggressive", BettingConfig(initial_balance=100, min_bet=0.5, max_bet_pct=0.10, safety_margin=0.15, max_consecutive_losses=5)),
    ]
    
    strategies = [
        ("Base Rate", BaseRateStrategy),
        ("Dry Streak", DryStreakStrategy),
        ("Time Pattern", TimeBasedPatternStrategy),
    ]
    
    results = []
    
    for config_name, betting_config in configs:
        print(f"\n--- Testing {config_name} Configuration ---")
        print(f"Balance: ${betting_config.initial_balance}, Min Bet: ${betting_config.min_bet}")
        print(f"Max Bet: {betting_config.max_bet_pct*100:.1f}%, Safety Margin: {betting_config.safety_margin*100:.1f}%")
        
        for strategy_name, strategy_cls in strategies:
            try:
                result = investigate_strategy(
                    strategy_cls,
                    test_data,
                    betting_config,
                    horizon=5,
                    threshold=10.0,
                    target_multiplier=2.0,
                    confidence_threshold=0.05,  # Lower threshold to force some betting
                )
                
                results.append({
                    "config": config_name,
                    "strategy": strategy_name,
                    "result": result,
                })
                
                print(f"\n{strategy_name}:")
                print(f"  Bets: {result.bets_placed}, Wins: {result.wins}, Losses: {result.losses}")
                print(f"  Win Rate: {result.win_rate:.1f}%")
                print(f"  Net Profit: ${result.net_profit:.2f}")
                print(f"  ROI: {result.roi_pct:.1f}%")
                print(f"  Max Drawdown: {result.max_drawdown:.1f}%")
                print(f"  Final Balance: ${result.final_balance:.2f}")
                print(f"  Max Consecutive Losses: {result.max_consecutive_losses}")
                
                # Entry decision analysis
                enter_count = sum(1 for d in result.entry_decisions if d.startswith("ENTER"))
                dont_enter_count = sum(1 for d in result.entry_decisions if d.startswith("DONT_ENTER"))
                stop_count = sum(1 for d in result.entry_decisions if d.startswith("STOP"))
                print(f"  Decisions: {enter_count} ENTER, {dont_enter_count} DONT_ENTER, {stop_count} STOP")
                
            except Exception as e:
                print(f"  Error: {e}")
                results.append({
                    "config": config_name,
                    "strategy": strategy_name,
                    "error": str(e),
                })
    
    # Save comprehensive results
    output = {
        "meta": {
            "suite": "momento-investigation-demo",
            "purpose": "Comprehensive profit margin analysis",
            "data_points": len(test_data),
        },
        "results": [
            {
                "config": r["config"],
                "strategy": r["strategy"],
                "bets_placed": r["result"].bets_placed if "result" in r else 0,
                "wins": r["result"].wins if "result" in r else 0,
                "losses": r["result"].losses if "result" in r else 0,
                "win_rate": r["result"].win_rate if "result" in r else 0,
                "net_profit": r["result"].net_profit if "result" in r else 0,
                "roi_pct": r["result"].roi_pct if "result" in r else 0,
                "max_drawdown": r["result"].max_drawdown if "result" in r else 0,
                "final_balance": r["result"].final_balance if "result" in r else 0,
                "max_consecutive_losses": r["result"].max_consecutive_losses if "result" in r else 0,
                "error": r.get("error"),
            }
            for r in results
        ],
    }
    
    output_path = Path(__file__).parent.parent.parent / "investigation-demo-results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n=== Summary ===")
    print(f"Results saved to {output_path}")
    
    # Find best performing configuration
    valid_results = [r for r in results if "result" in r and r["result"].bets_placed > 0]
    if valid_results:
        best = max(valid_results, key=lambda x: x["result"].roi_pct)
        print(f"\nBest performing: {best['config']} + {best['strategy']}")
        print(f"  ROI: {best['result'].roi_pct:.1f}%")
        print(f"  Final Balance: ${best['result'].final_balance:.2f}")
    
    return output


if __name__ == "__main__":
    run_comprehensive_investigation()
