#!/usr/bin/env python3
"""Run investigation and improvement suite for strategy profit margins."""

import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from research.investigation_suite import (
    BettingConfig,
    run_investigation_suite,
    run_live_accuracy_test,
)
from research.strategies import STRATEGY_REGISTRY


def main(argv=None):
    parser = argparse.ArgumentParser(description="Momento Investigation Suite")
    parser.add_argument("csv", nargs="*", help="CSV files for historical analysis")
    parser.add_argument("--output", default="investigation-report.json")
    parser.add_argument("--live-test", action="store_true", help="Run live accuracy test")
    parser.add_argument("--live-rounds", type=int, default=20, help="Rounds for live test")
    parser.add_argument("--strategy", help="Specific strategy to test")
    parser.add_argument("--balance", type=float, default=100.0, help="Initial balance")
    parser.add_argument("--min-bet", type=float, default=0.5, help="Minimum bet size")
    parser.add_argument("--max-bet-pct", type=float, default=0.05, help="Max bet % of balance")
    parser.add_argument("--safety-margin", type=float, default=0.10, help="Stop loss %")
    parser.add_argument("--target-profit", type=float, default=0.20, help="Target profit %")
    parser.add_argument("--max-losses", type=int, default=3, help="Max consecutive losses")
    parser.add_argument("--target-multiplier", type=float, default=2.0, help="Target multiplier")
    parser.add_argument("--confidence-threshold", type=float, default=0.5, help="Entry confidence threshold")
    
    args = parser.parse_args(argv)
    
    # Create betting config
    betting_config = BettingConfig(
        initial_balance=args.balance,
        min_bet=args.min_bet,
        max_bet_pct=args.max_bet_pct,
        safety_margin=args.safety_margin,
        target_profit_pct=args.target_profit,
        max_consecutive_losses=args.max_losses,
    )
    
    if args.live_test:
        # Run live accuracy test
        strategy_name = args.strategy or "dry_streak"
        if strategy_name not in STRATEGY_REGISTRY:
            print(f"Error: Unknown strategy '{strategy_name}'")
            print(f"Available: {list(STRATEGY_REGISTRY.keys())}")
            return 1
        
        print(f"Running live accuracy test for {strategy_name}")
        print(f"Rounds: {args.live_rounds}")
        print(f"Betting config: balance={args.balance}, min_bet={args.min_bet}")
        
        result = run_live_accuracy_test(
            STRATEGY_REGISTRY[strategy_name],
            n_rounds=args.live_rounds,
            betting_config=betting_config,
            confidence_threshold=args.confidence_threshold,
        )
        
        with open(args.output, "w") as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n=== Live Test Results ===")
        inv = result["investigation_result"]
        print(f"Strategy: {inv['strategy_name']}")
        print(f"Bets placed: {inv['bets_placed']}")
        print(f"Wins: {inv['wins']}, Losses: {inv['losses']}")
        print(f"Win rate: {inv['win_rate']:.1f}%")
        print(f"Net profit: ${inv['net_profit']:.2f}")
        print(f"ROI: {inv['roi_pct']:.1f}%")
        print(f"Final balance: ${inv['final_balance']:.2f}")
        
        print(f"\nResults saved to {args.output}")
        return 0
    
    # Historical investigation
    if not args.csv:
        print("Error: CSV files required for historical investigation")
        print("Use --live-test for live accuracy testing without historical data")
        return 1
    
    print(f"Running investigation suite on {len(args.csv)} file(s)")
    print(f"Strategy: {args.strategy or 'all'}")
    print(f"Betting config: balance=${args.balance}, min_bet=${args.min_bet}")
    print(f"Target multiplier: {args.target_multiplier}x")
    print(f"Confidence threshold: {args.confidence_threshold:.1%}")
    
    result = run_investigation_suite(
        args.csv,
        betting_config,
        target_multiplier=args.target_multiplier,
        confidence_threshold=args.confidence_threshold,
        strategies=[args.strategy] if args.strategy else None,
    )
    
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n=== Investigation Results ===")
    for strat in result["strategies"]:
        print(f"\n{strat['name']}:")
        print(f"  Bets: {strat['bets_placed']}")
        print(f"  Wins: {strat['wins']}, Losses: {strat['losses']}")
        print(f"  Win rate: {strat['win_rate']:.1f}%")
        print(f"  Net profit: ${strat['net_profit']:.2f}")
        print(f"  ROI: {strat['roi_pct']:.1f}%")
        print(f"  Max drawdown: {strat['max_drawdown']:.1f}%")
        print(f"  Final balance: ${strat['final_balance']:.2f}")
        
        entry_summary = strat.get('entry_decisions_summary', {})
        print(f"  Entry decisions: {entry_summary.get('enter', 0)} enter, {entry_summary.get('dont_enter', 0)} dont_enter, {entry_summary.get('stop', 0)} stop")
    
    print(f"\nResults saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
