#!/usr/bin/env python3
"""Test dynamic strategies with investigation suite."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.investigation_suite import BettingConfig, investigate_strategy
from research.dynamic_strategies import (
    VolatilityAdaptiveStrategy,
    MomentumReversalStrategy,
    DynamicConfidenceStrategy,
)


def generate_realistic_data(n_rounds: int = 2000, seed: int = 42):
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


def test_dynamic_strategies():
    """Test all dynamic strategies with investigation suite."""
    print("=== Dynamic Strategies Investigation Suite ===\n")
    
    # Generate test data
    print("Generating realistic test data...")
    test_data = generate_realistic_data(n_rounds=2000, seed=42)
    
    # Test configurations optimized for dynamic strategies
    configs = [
        ("Dynamic_Aggressive", BettingConfig(
            initial_balance=100, 
            min_bet=0.5, 
            max_bet_pct=0.15,  # Higher max bet for dynamic strategies
            safety_margin=0.12, 
            max_consecutive_losses=4,
            recovery_mode=True  # Enable recovery mode
        )),
        ("Dynamic_Balanced", BettingConfig(
            initial_balance=100, 
            min_bet=0.5, 
            max_bet_pct=0.08, 
            safety_margin=0.10, 
            max_consecutive_losses=3
        )),
    ]
    
    strategies = [
        ("Volatility Adaptive", VolatilityAdaptiveStrategy),
        ("Momentum Reversal", MomentumReversalStrategy),
        ("Dynamic Confidence", DynamicConfidenceStrategy),
    ]
    
    results = []
    
    for config_name, betting_config in configs:
        print(f"\n--- Testing {config_name} Configuration ---")
        print(f"Balance: ${betting_config.initial_balance}, Max Bet: {betting_config.max_bet_pct*100:.1f}%")
        print(f"Recovery Mode: {betting_config.recovery_mode}")
        
        for strategy_name, strategy_cls in strategies:
            try:
                result = investigate_strategy(
                    strategy_cls,
                    test_data,
                    betting_config,
                    horizon=5,
                    threshold=10.0,
                    target_multiplier=1.5,  # Lower target for dynamic strategies
                    confidence_threshold=0.1,  # Even lower threshold for dynamic strategies
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
                
                # Get betting recommendation if available
                if hasattr(strategy_cls, 'get_betting_recommendation'):
                    print(f"  Dynamic Betting: Available")
                
            except Exception as e:
                print(f"  Error: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    "config": config_name,
                    "strategy": strategy_name,
                    "error": str(e),
                })
    
    # Save comprehensive results
    output = {
        "meta": {
            "suite": "momento-dynamic-strategies",
            "purpose": "Dynamic adaptive strategy testing",
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
    
    output_path = Path(__file__).parent.parent.parent / "dynamic-strategies-results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    
    print(f"\n=== Summary ===")
    print(f"Results saved to {output_path}")
    
    # Find best performing configuration
    valid_results = [r for r in results if "result" in r and r["result"].bets_placed > 0]
    if valid_results:
        best_roi = max(valid_results, key=lambda x: x["result"].roi_pct)
        best_balance = max(valid_results, key=lambda x: x["result"].final_balance)
        
        print(f"\nBest ROI: {best_roi['config']} + {best_roi['strategy']}")
        print(f"  ROI: {best_roi['result'].roi_pct:.1f}%")
        print(f"  Final Balance: ${best_roi['result'].final_balance:.2f}")
        
        print(f"\nHighest Balance: {best_balance['config']} + {best_balance['strategy']}")
        print(f"  Final Balance: ${best_balance['result'].final_balance:.2f}")
        print(f"  ROI: {best_balance['result'].roi_pct:.1f}%")
    
    return output


if __name__ == "__main__":
    test_dynamic_strategies()
