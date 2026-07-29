#!/usr/bin/env python3
"""Test profit capping system with investigation suite."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research.investigation_suite import BettingConfig, investigate_strategy
from research.profit_capping import (
    ProfitCapper,
    ProfitCapConfig,
    FlexibleBalanceMapper,
    create_profit_capping_config,
    ProfitCapMode,
)
from research.dynamic_strategies import DynamicConfidenceStrategy


def generate_realistic_data(n_rounds: int = 2000, seed: int = 42):
    """Generate realistic crash game data."""
    import random
    random.seed(seed)
    
    values = []
    for _ in range(n_rounds):
        u = random.random()
        if u >= 0.97:
            values.append(min(10_000.0, 0.97 / (1.0 - u)))
        elif u >= 0.85:
            values.append(2.0 + random.random() * 8.0)
        elif u >= 0.60:
            values.append(1.5 + random.random() * 1.5)
        else:
            values.append(1.0 + random.random() * 0.5)
    
    return values


def test_profit_capping_modes():
    """Test different profit capping modes."""
    print("=== Profit Capping System Test ===\n")
    
    # Generate test data
    print("Generating realistic test data...")
    test_data = generate_realistic_data(n_rounds=2000, seed=42)
    
    # Test different profit capping modes
    modes = [
        ("Fixed Ratio", ProfitCapMode.FIXED_RATIO),
        ("Dynamic Ratio", ProfitCapMode.DYNAMIC_RATIO),
        ("Tiered", ProfitCapMode.TIERED),
        ("Hybrid", ProfitCapMode.HYBRID),
    ]
    
    results = []
    
    for mode_name, mode in modes:
        print(f"\n--- Testing {mode_name} Mode ---")
        
        # Create profit capping configuration
        config = create_profit_capping_config(mode.value)
        profit_capper = ProfitCapper(config)
        
        # Test profit cap calculation at different balance levels
        test_balances = [100, 500, 1000, 2500, 5000]
        performance = {"win_rate": 0.52, "consecutive_losses": 0}
        
        for balance in test_balances:
            profit_cap = profit_capper.calculate_profit_cap(balance, performance)
            print(f"  Balance ${balance}: Profit Cap = ${profit_cap:.2f} ({profit_cap/balance*100:.1f}%)")
        
        # Test bet size calculation
        print(f"\n  Bet Size Calculations:")
        for balance in test_balances:
            bet_size = profit_capper.calculate_bet_size(balance, 0.7, performance)
            print(f"  Balance ${balance}: Max Bet = ${bet_size:.2f} ({bet_size/balance*100:.1f}%)")
        
        # Test profit cap checking
        print(f"\n  Profit Cap Status:")
        for balance in test_balances:
            cap_check = profit_capper.check_profit_cap(balance, 100, performance)
            print(f"  Balance ${balance}: ${cap_check['current_profit']:.2f} / ${cap_check['profit_cap']:.2f} ({cap_check['cap_ratio']*100:.1f}%) - {cap_check['action_required']}")
        
        results.append({
            "mode": mode_name,
            "config": {
                "base_profit_ratio": config.base_profit_ratio,
                "max_profit_ratio": config.max_profit_ratio,
                "min_balance": config.min_balance,
                "max_balance": config.max_balance,
            },
        })


def test_balance_mapping():
    """Test flexible balance mapping system."""
    print("\n=== Flexible Balance Mapping Test ===\n")
    
    mapper = FlexibleBalanceMapper(min_balance=100, max_balance=10000)
    
    # Test mapping at different balance levels
    test_balances = [50, 100, 250, 500, 1000, 2500, 5000, 7500, 10000, 15000]
    
    print("Balance Tier Mapping:")
    for balance in test_balances:
        mapping = mapper.map_balance_to_tier(balance)
        print(f"  ${balance:6.0f}: {mapping['tier']:12s} | Scaling: {mapping['scaling_factor']:.1f}x | Risk: {mapping['risk_level']:10s} | {mapping['recommended_action']}")
    
    # Test optimal bet size calculation
    print(f"\nOptimal Bet Size Calculation (confidence 0.7):")
    for balance in [100, 500, 1000, 2500, 5000]:
        bet_size = mapper.calculate_optimal_bet_size(balance, 0.7, "moderate")
        print(f"  ${balance:5.0f}: ${bet_size:6.2f} ({bet_size/balance*100:.1f}%)")
    
    # Test profit trajectory simulation
    print(f"\nProfit Trajectory Simulation (100 rounds, 52% win rate):")
    trajectory = mapper.simulate_profit_trajectory(100, 0.52, 1.5, 100)
    
    print(f"  Start: ${trajectory[0]['balance']:.2f}")
    print(f"  End: ${trajectory[-1]['balance']:.2f}")
    print(f"  Final Profit: ${trajectory[-1]['profit']:.2f}")
    print(f"  Final Tier: {trajectory[-1]['tier']}")


def test_profit_capping_with_strategy():
    """Test profit capping integrated with dynamic strategy."""
    print("\n=== Profit Capping + Dynamic Strategy Test ===\n")
    
    # Generate test data
    test_data = generate_realistic_data(n_rounds=2000, seed=42)
    
    # Create configuration with profit capping
    config = BettingConfig(
        initial_balance=100,
        min_bet=0.5,
        max_bet_pct=0.12,
        safety_margin=0.10,
        target_profit_pct=0.25,  # 25% profit target
        max_consecutive_losses=4,
        recovery_mode=True,
    )
    
    # Test with profit capping enabled
    print("Testing Dynamic Confidence with Profit Capping:")
    
    result = investigate_strategy(
        DynamicConfidenceStrategy,
        test_data,
        config,
        horizon=5,
        threshold=10.0,
        target_multiplier=1.5,
        confidence_threshold=0.1,
    )
    
    print(f"\nResults:")
    print(f"  Bets: {result.bets_placed}")
    print(f"  Wins: {result.wins}, Losses: {result.losses}")
    print(f"  Win Rate: {result.win_rate:.1f}%")
    print(f"  Net Profit: ${result.net_profit:.2f}")
    print(f"  ROI: {result.roi_pct:.1f}%")
    print(f"  Final Balance: ${result.final_balance:.2f}")
    print(f"  Max Drawdown: {result.max_drawdown:.1f}%")
    
    # Test profit cap at different levels
    profit_capper = ProfitCapper(create_profit_capping_config("dynamic_ratio"))
    
    print(f"\nProfit Cap Analysis:")
    for balance in [100, result.final_balance]:
        cap_check = profit_capper.check_profit_cap(balance, 100, {"win_rate": result.win_rate/100, "consecutive_losses": 0})
        print(f"  Balance ${balance:.2f}:")
        print(f"    Current Profit: ${cap_check['current_profit']:.2f}")
        print(f"    Profit Cap: ${cap_check['profit_cap']:.2f}")
        print(f"    Cap Ratio: {cap_check['cap_ratio']*100:.1f}%")
        print(f"    Action: {cap_check['action_required']}")


def test_profit_mapping():
    """Test profit to balance mapping."""
    print("\n=== Profit Mapping Test ===\n")
    
    profit_capper = ProfitCapper(create_profit_capping_config("tiered"))
    
    # Test mapping different profit targets
    target_profits = [25, 50, 100, 250, 500, 1000, 2500]
    
    print("Profit to Balance Mapping:")
    for target_profit in target_profits:
        mapping = profit_capper.get_profit_mapping(target_profit)
        print(f"  Target Profit ${target_profit:4.0f}:")
        print(f"    Required Balance: ${mapping['required_balance']:7.2f}")
        print(f"    Max Bet Size: ${mapping['max_bet_size']:6.2f}")
        print(f"    Tier: {mapping['applicable_tier']}")
        print(f"    Feasible: {mapping['feasible']}")


if __name__ == "__main__":
    test_profit_capping_modes()
    test_balance_mapping()
    test_profit_capping_with_strategy()
    test_profit_mapping()
    
    print("\n=== Profit Capping System Test Complete ===")
