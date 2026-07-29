#!/usr/bin/env python3
"""
MEGA PLAN: Full System Prediction Testing
Comprehensive testing of all prediction components for 10x chase 5 rounds scenario
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
    predictions: int
    correct: int
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    details: Dict[str, Any]

class MegaPlanTester:
    """Comprehensive prediction system tester."""
    
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
    
    def phase1_baseline_random(self, target: float = 10.0, horizon: int = 5) -> StrategyResult:
        """Phase 1: Baseline random testing."""
        print("\n=== PHASE 1: BASELINE RANDOM TESTING ===")
        
        predictions = 0
        correct = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for i in range(100, len(self.rounds) - horizon, 10):
            # Random prediction
            predicted = random.random() > 0.5
            predictions += 1
            
            # Check actual outcome
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
        
        accuracy = correct / predictions if predictions > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        result = StrategyResult(
            name="random_baseline",
            predictions=predictions,
            correct=correct,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            details={"target": target, "horizon": horizon}
        )
        
        print(f"Random Baseline: {accuracy:.2%} accuracy, {precision:.2%} precision, {recall:.2%} recall")
        return result
    
    def phase2_linguistics_strategies(self, target: float = 10.0, horizon: int = 5) -> List[StrategyResult]:
        """Phase 2: Linguistics-based strategies."""
        print("\n=== PHASE 2: LINGUISTICS STRATEGIES ===")
        
        # Import momento linguistics from backend
        try:
            import sys
            sys.path.insert(0, '/home/pirates/Avfs_GIT/backend')
            from momento import linguistics as ling
        except ImportError as e:
            print(f"Momento linguistics not available: {e}, skipping")
            return []
        
        results = []
        
        # Strategy 1: Band-based prediction
        print("Testing band-based prediction...")
        predictions = 0
        correct = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for i in range(100, len(self.rounds) - horizon, 10):
            window = self.rounds[max(0, i-20):i]
            if not window:
                continue
            
            # Analyze recent bands using simple band classification
            def simple_band(mult):
                if mult < 1.5: return 'dust'
                elif mult < 2.0: return 'low'
                elif mult < 3.0: return 'base'
                elif mult < 5.0: return 'mid'
                elif mult < 10.0: return 'high'
                elif mult < 20.0: return 'ignition'
                elif mult < 50.0: return 'moonshot'
                else: return 'mega'
            
            bands = [simple_band(r['multiplier']) for r in window]
            high_band_count = sum(1 for b in bands if b in ['ignition', 'moonshot', 'mega'])
            
            # Predict if high band activity predicts target
            predicted = high_band_count >= 2
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
        
        accuracy = correct / predictions if predictions > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        result = StrategyResult(
            name="band_activity",
            predictions=predictions,
            correct=correct,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            details={"target": target, "horizon": horizon, "threshold": 2}
        )
        results.append(result)
        print(f"Band Activity: {accuracy:.2%} accuracy, {precision:.2%} precision, {recall:.2%} recall")
        
        # Strategy 2: Points momentum
        print("Testing points momentum...")
        predictions = 0
        correct = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for i in range(100, len(self.rounds) - horizon, 10):
            window = self.rounds[max(0, i-20):i]
            if len(window) < 5:
                continue
            
            # Calculate simple momentum
            multipliers = [r['multiplier'] for r in window]
            momentum = multipliers[-1] - multipliers[0]
            
            # Predict if positive momentum predicts target
            predicted = momentum > 10
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
        
        accuracy = correct / predictions if predictions > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        result = StrategyResult(
            name="points_momentum",
            predictions=predictions,
            correct=correct,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            details={"target": target, "horizon": horizon, "momentum_threshold": 10}
        )
        results.append(result)
        print(f"Points Momentum: {accuracy:.2%} accuracy, {precision:.2%} precision, {recall:.2%} recall")
        
        return results
    
    def phase3_pressure_strategies(self, target: float = 10.0, horizon: int = 5) -> List[StrategyResult]:
        """Phase 3: Forex-style pressure analysis."""
        print("\n=== PHASE 3: PRESSURE STRATEGIES ===")
        
        try:
            import sys
            sys.path.insert(0, '/home/pirates/Avfs_GIT/backend')
            from features.pressure.detector import CeilingDetector
            from features.pressure.calculator import PressureCalculator
        except ImportError as e:
            print(f"Pressure features not available: {e}, skipping")
            return []
        
        results = []
        
        # Strategy 1: High pressure prediction
        print("Testing high pressure prediction...")
        detector = CeilingDetector(min_touches=3, tolerance=0.10)
        calculator = PressureCalculator()
        
        predictions = 0
        correct = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for i in range(500, len(self.rounds) - horizon, 50):
            window = self.rounds[max(0, i-200):i]
            if len(window) < 20:
                continue
            
            try:
                ceilings = detector.detect_resistance_ceilings(window)
                pressure = calculator.compute_pressure(window, ceilings)
                
                # Predict if high pressure predicts target
                predicted = pressure.get('pressure_percent', 0) >= 50
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
            except Exception as e:
                continue
        
        accuracy = correct / predictions if predictions > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        result = StrategyResult(
            name="high_pressure",
            predictions=predictions,
            correct=correct,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            details={"target": target, "horizon": horizon, "pressure_threshold": 50}
        )
        results.append(result)
        print(f"High Pressure: {accuracy:.2%} accuracy, {precision:.2%} precision, {recall:.2%} recall")
        
        return results
    
    def phase4_shape_strategies(self, target: float = 10.0, horizon: int = 5) -> List[StrategyResult]:
        """Phase 4: Shape and pattern detection."""
        print("\n=== PHASE 4: SHAPE STRATEGIES ===")
        
        try:
            import sys
            sys.path.insert(0, '/home/pirates/Avfs_GIT/backend')
            from momento import linguistics as ling
        except ImportError as e:
            print(f"Linguistics not available: {e}, skipping")
            return []
        
        results = []
        
        # Strategy 1: Shape-based prediction
        print("Testing shape-based prediction...")
        predictions = 0
        correct = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for i in range(100, len(self.rounds) - horizon, 10):
            window = self.rounds[max(0, i-20):i]
            if len(window) < 10:
                continue
            
            # Analyze shape using simple logic
            multipliers = [r['multiplier'] for r in window]
            # Simple shape classification
            if len(multipliers) >= 5:
                first_half = multipliers[:len(multipliers)//2]
                second_half = multipliers[len(multipliers)//2:]
                first_mean = sum(first_half) / len(first_half)
                second_mean = sum(second_half) / len(second_half)
                
                if second_mean > first_mean * 1.1:
                    shape = 'ascending'
                elif second_mean < first_mean * 0.9:
                    shape = 'descending'
                else:
                    shape = 'stable'
            else:
                shape = 'unknown'
            
            # Predict certain shapes indicate target
            predicted = shape in ['ascending', 'volatile']
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
        
        accuracy = correct / predictions if predictions > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        result = StrategyResult(
            name="shape_pattern",
            predictions=predictions,
            correct=correct,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            details={"target": target, "horizon": horizon, "shapes": ['ascending', 'volatile']}
        )
        results.append(result)
        print(f"Shape Pattern: {accuracy:.2%} accuracy, {precision:.2%} precision, {recall:.2%} recall")
        
        return results
    
    def phase5_research_strategies(self, target: float = 10.0, horizon: int = 5) -> List[StrategyResult]:
        """Phase 5: Research suite strategies."""
        print("\n=== PHASE 5: RESEARCH STRATEGIES ===")
        
        try:
            import sys
            sys.path.insert(0, '/home/pirates/Avfs_GIT/backend')
            from research.strategies import TimeBasedPatternStrategy, DryStreakStrategy, BaseRateStrategy
        except ImportError as e:
            print(f"Research strategies not available: {e}, skipping")
            return []
        
        results = []
        
        # Test TimeBasedPatternStrategy
        print("Testing TimeBasedPatternStrategy...")
        try:
            strategy = TimeBasedPatternStrategy(horizon=horizon, threshold=target)
            
            predictions = 0
            correct = 0
            true_positives = 0
            false_positives = 0
            false_negatives = 0
            
            for i in range(1000, len(self.rounds) - horizon, 100):
                historical = self.rounds[:i]
                if len(historical) < 100:
                    continue
                
                try:
                    strategy.fit_on([r['multiplier'] for r in historical])
                    prob = strategy.predict_proba(historical)
                    
                    predicted = prob > 0.5
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
                except Exception as e:
                    continue
            
            accuracy = correct / predictions if predictions > 0 else 0
            precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
            recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            result = StrategyResult(
                name="time_based_pattern",
                predictions=predictions,
                correct=correct,
                accuracy=accuracy,
                precision=precision,
                recall=recall,
                f1_score=f1,
                details={"target": target, "horizon": horizon}
            )
            results.append(result)
            print(f"TimeBasedPattern: {accuracy:.2%} accuracy, {precision:.2%} precision, {recall:.2%} recall")
        except Exception as e:
            print(f"TimeBasedPattern failed: {e}")
        
        return results
    
    def phase6_combined_pipeline(self, target: float = 10.0, horizon: int = 5) -> StrategyResult:
        """Phase 6: Combined pipeline optimization."""
        print("\n=== PHASE 6: COMBINED PIPELINE ===")
        
        # Ensemble of best individual strategies
        predictions = 0
        correct = 0
        true_positives = 0
        false_positives = 0
        false_negatives = 0
        
        for i in range(500, len(self.rounds) - horizon, 50):
            window = self.rounds[max(0, i-50):i]
            if len(window) < 20:
                continue
            
            votes = 0
            
            # Strategy 1: Recent volatility
            multipliers = [r['multiplier'] for r in window[-20:]]
            if len(multipliers) > 1:
                volatility = statistics.stdev(multipliers)
                if volatility > statistics.mean(multipliers) * 0.5:
                    votes += 1
            
            # Strategy 2: Recent high multipliers
            recent_highs = sum(1 for m in multipliers if m >= target * 0.5)
            if recent_highs >= 2:
                votes += 1
            
            # Strategy 3: Momentum
            if len(multipliers) >= 5:
                momentum = multipliers[-1] - multipliers[0]
                if momentum > 0:
                    votes += 1
            
            # Ensemble decision (majority vote)
            predicted = votes >= 2
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
        
        accuracy = correct / predictions if predictions > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        result = StrategyResult(
            name="combined_ensemble",
            predictions=predictions,
            correct=correct,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            details={"target": target, "horizon": horizon, "strategies": 3}
        )
        print(f"Combined Ensemble: {accuracy:.2%} accuracy, {precision:.2%} precision, {recall:.2%} recall")
        
        return result
    
    def run_full_mega_plan(self, target: float = 10.0, horizon: int = 5) -> Dict[str, Any]:
        """Run the complete mega plan test."""
        print(f"\n{'='*60}")
        print(f"MEGA PLAN: FULL SYSTEM TESTING")
        print(f"Target: {target}x, Horizon: {horizon} rounds")
        print(f"{'='*60}")
        
        all_results = []
        
        # Phase 1: Baseline
        baseline = self.phase1_baseline_random(target, horizon)
        all_results.append(baseline)
        
        # Phase 2: Linguistics
        linguistics_results = self.phase2_linguistics_strategies(target, horizon)
        all_results.extend(linguistics_results)
        
        # Phase 3: Pressure
        pressure_results = self.phase3_pressure_strategies(target, horizon)
        all_results.extend(pressure_results)
        
        # Phase 4: Shape
        shape_results = self.phase4_shape_strategies(target, horizon)
        all_results.extend(shape_results)
        
        # Phase 5: Research
        research_results = self.phase5_research_strategies(target, horizon)
        all_results.extend(research_results)
        
        # Phase 6: Combined
        combined = self.phase6_combined_pipeline(target, horizon)
        all_results.append(combined)
        
        # Rank results
        ranked = sorted(all_results, key=lambda x: x.accuracy, reverse=True)
        
        print(f"\n{'='*60}")
        print(f"FINAL RANKING")
        print(f"{'='*60}")
        for i, result in enumerate(ranked):
            print(f"{i+1}. {result.name}: {result.accuracy:.2%} accuracy, F1: {result.f1_score:.3f}")
        
        return {
            "target": target,
            "horizon": horizon,
            "baseline_accuracy": baseline.accuracy,
            "best_strategy": ranked[0].name if ranked else None,
            "best_accuracy": ranked[0].accuracy if ranked else 0,
            "all_results": [
                {
                    "name": r.name,
                    "accuracy": r.accuracy,
                    "precision": r.precision,
                    "recall": r.recall,
                    "f1_score": r.f1_score,
                    "predictions": r.predictions,
                    "details": r.details
                }
                for r in all_results
            ]
        }

if __name__ == "__main__":
    tester = MegaPlanTester("/home/pirates/Avfs_GIT/clean_data.csv")
    results = tester.run_full_mega_plan(target=10.0, horizon=5)
    
    # Save results
    with open("/home/pirates/Avfs_GIT/research/mega_plan_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to research/mega_plan_results.json")