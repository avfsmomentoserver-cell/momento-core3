#!/usr/bin/env python3
"""
COMPREHENSIVE MEGA PLAN: Multi-target, multi-horizon testing
Testing all prediction components across different scenarios
"""

import csv
import statistics
import random
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import json

@dataclass
class StrategyResult:
    """Results from a single strategy test."""
    name: str
    target: float
    horizon: int
    predictions: int
    correct: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    true_positive_rate: float
    false_positive_rate: float
    details: Dict[str, Any]

class ComprehensiveMegaPlan:
    """Comprehensive multi-scenario prediction system tester."""
    
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.rounds = []
        self.load_data()
        
    def load_data(self):
        """Load clean data from CSV."""
        with open(self.data_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    mult = float(row['multiplier'])
                    self.rounds.append({'multiplier': mult})
                except (ValueError, KeyError):
                    continue
        print(f"Loaded {len(self.rounds)} rounds")
    
    def simple_band(self, multiplier: float) -> str:
        """Simple band classification."""
        if multiplier < 1.5: return 'dust'
        elif multiplier < 2.0: return 'low'
        elif multiplier < 3.0: return 'base'
        elif multiplier < 5.0: return 'mid'
        elif multiplier < 10.0: return 'high'
        elif multiplier < 20.0: return 'ignition'
        elif multiplier < 50.0: return 'moonshot'
        else: return 'mega'
    
    def test_strategy(self, strategy_func, strategy_name: str, target: float, horizon: int) -> StrategyResult:
        """Test a single strategy."""
        predictions = 0
        correct = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        true_negatives = 0
        
        for i in range(500, len(self.rounds) - horizon, 50):
            window = self.rounds[max(0, i-100):i]
            if len(window) < 20:
                continue
            
            try:
                predicted = strategy_func(window, target, horizon)
                predictions += 1
                
                future = self.rounds[i:i+horizon]
                actual = any(r['multiplier'] >= target for r in future)
                
                if predicted and actual:
                    correct += 1
                    true_positives += 1
                elif predicted and not actual:
                    false_positives += 1
                elif not predicted and actual:
                    false_negatives += 1
                elif not predicted and not actual:
                    correct += 1
                    true_negatives += 1
            except Exception as e:
                continue
        
        if predictions == 0:
            return StrategyResult(
                name=strategy_name,
                target=target,
                horizon=horizon,
                predictions=0,
                correct=0,
                accuracy=0.0,
                precision=0.0,
                recall=0.0,
                f1_score=0.0,
                true_positive_rate=0.0,
                false_positive_rate=0.0,
                details={"error": "no predictions"}
            )
        
        accuracy = correct / predictions
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        tpr = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        fpr = false_positives / (false_positives + true_negatives) if (false_positives + true_negatives) > 0 else 0
        
        return StrategyResult(
            name=strategy_name,
            target=target,
            horizon=horizon,
            predictions=predictions,
            correct=correct,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            true_positive_rate=tpr,
            false_positive_rate=fpr,
            details={}
        )
    
    # Strategy implementations
    def random_strategy(self, window, target, horizon):
        return random.random() > 0.5
    
    def band_activity_strategy(self, window, target, horizon):
        bands = [self.simple_band(r['multiplier']) for r in window]
        high_band_count = sum(1 for b in bands if b in ['ignition', 'moonshot', 'mega'])
        return high_band_count >= 2
    
    def momentum_strategy(self, window, target, horizon):
        multipliers = [r['multiplier'] for r in window]
        if len(multipliers) < 5:
            return False
        momentum = multipliers[-1] - multipliers[0]
        return momentum > 0
    
    def volatility_strategy(self, window, target, horizon):
        multipliers = [r['multiplier'] for r in window]
        if len(multipliers) < 2:
            return False
        volatility = statistics.stdev(multipliers)
        mean = statistics.mean(multipliers)
        return volatility > mean * 0.3
    
    def recent_highs_strategy(self, window, target, horizon):
        multipliers = [r['multiplier'] for r in window]
        recent_highs = sum(1 for m in multipliers if m >= target * 0.5)
        return recent_highs >= 2
    
    def ascending_shape_strategy(self, window, target, horizon):
        multipliers = [r['multiplier'] for r in window]
        if len(multipliers) < 6:
            return False
        first_half = multipliers[:len(multipliers)//2]
        second_half = multipliers[len(multipliers)//2:]
        first_mean = sum(first_half) / len(first_half)
        second_mean = sum(second_half) / len(second_half)
        return second_mean > first_mean * 1.1
    
    def mean_reversion_strategy(self, window, target, horizon):
        multipliers = [r['multiplier'] for r in window]
        if len(multipliers) < 5:
            return False
        mean = statistics.mean(multipliers)
        current = multipliers[-1]
        return current < mean * 0.8  # Bet on bounce from low
    
    def streak_strategy(self, window, target, horizon):
        multipliers = [r['multiplier'] for r in window]
        if len(multipliers) < 3:
            return False
        # Count consecutive low rounds
        streak = 0
        for m in reversed(multipliers):
            if m < 2.0:
                streak += 1
            else:
                break
        return streak >= 5  # Bet after long low streak
    
    def ensemble_strategy(self, window, target, horizon):
        """Combined ensemble of multiple strategies."""
        votes = 0
        votes += 1 if self.momentum_strategy(window, target, horizon) else 0
        votes += 1 if self.volatility_strategy(window, target, horizon) else 0
        votes += 1 if self.recent_highs_strategy(window, target, horizon) else 0
        return votes >= 2  # Majority vote
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive test across multiple targets and horizons."""
        print(f"\n{'='*70}")
        print(f"COMPREHENSIVE MEGA PLAN: MULTI-TARGET, MULTI-HORIZON TESTING")
        print(f"{'='*70}")
        
        strategies = [
            ("random_baseline", self.random_strategy),
            ("band_activity", self.band_activity_strategy),
            ("momentum", self.momentum_strategy),
            ("volatility", self.volatility_strategy),
            ("recent_highs", self.recent_highs_strategy),
            ("ascending_shape", self.ascending_shape_strategy),
            ("mean_reversion", self.mean_reversion_strategy),
            ("streak", self.streak_strategy),
            ("ensemble", self.ensemble_strategy),
        ]
        
        targets = [5.0, 10.0, 20.0, 50.0]
        horizons = [3, 5, 10]
        
        all_results = []
        
        for target in targets:
            for horizon in horizons:
                print(f"\n--- Target: {target}x, Horizon: {horizon} rounds ---")
                
                strategy_results = []
                for strategy_name, strategy_func in strategies:
                    result = self.test_strategy(strategy_func, strategy_name, target, horizon)
                    strategy_results.append(result)
                    print(f"{strategy_name:20s}: {result.accuracy:6.2%} acc, {result.precision:6.2%} prec, {result.recall:6.2%} rec, F1: {result.f1_score:.3f}")
                
                all_results.extend(strategy_results)
        
        # Find best overall strategy
        ranked_by_accuracy = sorted(all_results, key=lambda x: x.accuracy, reverse=True)
        ranked_by_f1 = sorted(all_results, key=lambda x: x.f1_score, reverse=True)
        
        print(f"\n{'='*70}")
        print(f"TOP 10 STRATEGIES BY ACCURACY")
        print(f"{'='*70}")
        for i, result in enumerate(ranked_by_accuracy[:10]):
            print(f"{i+1:2d}. {result.name:20s} {result.target:5.1f}x/{result.horizon:2d}rnd: {result.accuracy:6.2%} acc, F1: {result.f1_score:.3f}")
        
        print(f"\n{'='*70}")
        print(f"TOP 10 STRATEGIES BY F1 SCORE")
        print(f"{'='*70}")
        for i, result in enumerate(ranked_by_f1[:10]):
            print(f"{i+1:2d}. {result.name:20s} {result.target:5.1f}x/{result.horizon:2d}rnd: {result.f1_score:.3f} F1, {result.accuracy:6.2%} acc")
        
        # Best for 10x/5 rounds (our target scenario)
        target_results = [r for r in all_results if r.target == 10.0 and r.horizon == 5]
        target_ranked = sorted(target_results, key=lambda x: x.accuracy, reverse=True)
        
        print(f"\n{'='*70}")
        print(f"BEST STRATEGIES FOR 10x/5 ROUNDS (TARGET SCENARIO)")
        print(f"{'='*70}")
        for i, result in enumerate(target_ranked):
            print(f"{i+1:2d}. {result.name:20s}: {result.accuracy:6.2%} acc, {result.precision:6.2%} prec, {result.recall:6.2%} rec, F1: {result.f1_score:.3f}")
        
        return {
            "strategies_tested": len(strategies),
            "targets_tested": targets,
            "horizons_tested": horizons,
            "total_results": len(all_results),
            "best_overall": {
                "name": ranked_by_accuracy[0].name if ranked_by_accuracy else None,
                "accuracy": ranked_by_accuracy[0].accuracy if ranked_by_accuracy else 0,
                "target": ranked_by_accuracy[0].target if ranked_by_accuracy else 0,
                "horizon": ranked_by_accuracy[0].horizon if ranked_by_accuracy else 0
            },
            "best_for_target_scenario": {
                "name": target_ranked[0].name if target_ranked else None,
                "accuracy": target_ranked[0].accuracy if target_ranked else 0,
                "precision": target_ranked[0].precision if target_ranked else 0,
                "recall": target_ranked[0].recall if target_ranked else 0,
                "f1_score": target_ranked[0].f1_score if target_ranked else 0
            },
            "all_results": [
                {
                    "name": r.name,
                    "target": r.target,
                    "horizon": r.horizon,
                    "accuracy": r.accuracy,
                    "precision": r.precision,
                    "recall": r.recall,
                    "f1_score": r.f1_score,
                    "predictions": r.predictions,
                    "true_positive_rate": r.true_positive_rate,
                    "false_positive_rate": r.false_positive_rate
                }
                for r in all_results
            ]
        }

if __name__ == "__main__":
    tester = ComprehensiveMegaPlan("/home/pirates/Avfs_GIT/clean_data.csv")
    results = tester.run_comprehensive_test()
    
    # Save results
    with open("/home/pirates/Avfs_GIT/research/comprehensive_mega_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to research/comprehensive_mega_results.json")