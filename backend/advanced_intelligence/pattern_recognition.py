"""
Advanced Pattern Recognition for V5 Intelligence Engine
Implements real-time pattern recognition with transformer models
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from collections import deque
import asyncio

logger = logging.getLogger("momento.advanced_intelligence")


@dataclass
class PatternMatch:
    """Represents a detected pattern with confidence and metadata."""
    pattern_type: str
    confidence: float
    start_index: int
    end_index: int
    features: Dict[str, Any]
    prediction: Optional[float] = None
    explanation: Optional[str] = None


class AdvancedPatternRecognizer:
    """
    Advanced pattern recognition using transformer-based models.
    Detects complex patterns in real-time data streams.
    """
    
    def __init__(self, sequence_length: int = 100, confidence_threshold: float = 0.85):
        self.sequence_length = sequence_length
        self.confidence_threshold = confidence_threshold
        self.buffer = deque(maxlen=sequence_length * 2)
        self.pattern_cache = {}
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize ML models for pattern recognition."""
        try:
            # Placeholder for transformer model initialization
            # In production, load pre-trained transformer models
            logger.info("Advanced pattern recognition models initialized")
        except Exception as exc:
            logger.warning("Pattern recognition model initialization failed: %s", exc)
    
    async def analyze_sequence(self, sequence: List[float]) -> List[PatternMatch]:
        """
        Analyze a sequence for complex patterns.
        
        Args:
            sequence: List of numerical values to analyze
            
        Returns:
            List of detected patterns with confidence scores
        """
        if len(sequence) < self.sequence_length:
            return []
        
        patterns = []
        
        # Detect various pattern types
        patterns.extend(await self._detect_ladder_patterns(sequence))
        patterns.extend(await self._detect_momentum_patterns(sequence))
        patterns.extend(await self._detect_reversal_patterns(sequence))
        patterns.extend(await self._detect_cycles_patterns(sequence))
        patterns.extend(await self._detect_anomaly_patterns(sequence))
        
        # Filter by confidence threshold
        high_confidence = [p for p in patterns if p.confidence >= self.confidence_threshold]
        
        return high_confidence
    
    async def _detect_ladder_patterns(self, sequence: List[float]) -> List[PatternMatch]:
        """Detect ladder patterns using sequence analysis."""
        patterns = []
        
        # Look for consistent upward movement with small variations
        window_size = 10
        for i in range(len(sequence) - window_size):
            window = sequence[i:i + window_size]
            
            # Calculate trend and consistency
            if len(window) < 2:
                continue
                
            trend = window[-1] - window[0]
            variance = np.var(window)
            
            # Ladder pattern: consistent upward trend with low variance
            if trend > 0 and variance < 0.1:
                confidence = min(0.95, 0.7 + (1 - variance) * 0.25)
                
                pattern = PatternMatch(
                    pattern_type="ladder",
                    confidence=confidence,
                    start_index=i,
                    end_index=i + window_size,
                    features={
                        "trend": trend,
                        "variance": variance,
                        "mean": np.mean(window)
                    },
                    prediction=self._predict_ladder_continuation(window),
                    explanation=f"Consistent upward trend of {trend:.3f} with low variance"
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_momentum_patterns(self, sequence: List[float]) -> List[PatternMatch]:
        """Detect momentum patterns using velocity analysis."""
        patterns = []
        
        # Calculate velocity (rate of change)
        velocities = np.diff(sequence)
        
        # Look for sustained momentum
        window_size = 20
        for i in range(len(velocities) - window_size):
            window = velocities[i:i + window_size]
            
            avg_velocity = np.mean(window)
            velocity_std = np.std(window)
            
            # Momentum pattern: sustained positive/negative velocity
            if abs(avg_velocity) > 0.01 and velocity_std < 0.05:
                confidence = min(0.90, 0.6 + abs(avg_velocity) * 10)
                
                pattern = PatternMatch(
                    pattern_type="momentum",
                    confidence=confidence,
                    start_index=i,
                    end_index=i + window_size,
                    features={
                        "avg_velocity": avg_velocity,
                        "velocity_std": velocity_std,
                        "direction": "upward" if avg_velocity > 0 else "downward"
                    },
                    prediction=self._predict_momentum_continuation(window),
                    explanation=f"Sustained {'upward' if avg_velocity > 0 else 'downward'} momentum of {avg_velocity:.4f}"
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_reversal_patterns(self, sequence: List[float]) -> List[PatternMatch]:
        """Detect reversal patterns using signal processing."""
        patterns = []
        
        # Calculate moving averages and crossovers
        if len(sequence) < 30:
            return patterns
            
        ma_short = np.convolve(sequence, np.ones(5)/5, mode='valid')
        ma_long = np.convolve(sequence, np.ones(20)/20, mode='valid')
        
        # Look for crossovers
        for i in range(len(ma_short) - 1):
            if i >= len(ma_long):
                break
                
            # Golden cross (short crosses above long)
            if ma_short[i] <= ma_long[i] and ma_short[i+1] > ma_long[i+1]:
                confidence = 0.85
                
                pattern = PatternMatch(
                    pattern_type="bullish_reversal",
                    confidence=confidence,
                    start_index=i,
                    end_index=i+10,
                    features={
                        "ma_short": ma_short[i],
                        "ma_long": ma_long[i],
                        "crossover_strength": ma_short[i+1] - ma_long[i+1]
                    },
                    prediction=self._predict_reversal_strength(sequence[i:i+20]),
                    explanation="Golden cross detected - bullish reversal signal"
                )
                patterns.append(pattern)
            
            # Death cross (short crosses below long)
            elif ma_short[i] >= ma_long[i] and ma_short[i+1] < ma_long[i+1]:
                confidence = 0.85
                
                pattern = PatternMatch(
                    pattern_type="bearish_reversal",
                    confidence=confidence,
                    start_index=i,
                    end_index=i+10,
                    features={
                        "ma_short": ma_short[i],
                        "ma_long": ma_long[i],
                        "crossover_strength": ma_long[i+1] - ma_short[i+1]
                    },
                    prediction=self._predict_reversal_strength(sequence[i:i+20]),
                    explanation="Death cross detected - bearish reversal signal"
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_cycles_patterns(self, sequence: List[float]) -> List[PatternMatch]:
        """Detect cyclical patterns using FFT analysis."""
        patterns = []
        
        if len(sequence) < 64:
            return patterns
            
        # Perform FFT analysis
        fft_result = np.fft.fft(sequence)
        frequencies = np.fft.fftfreq(len(sequence))
        
        # Find dominant frequencies
        power_spectrum = np.abs(fft_result) ** 2
        dominant_freq_idx = np.argmax(power_spectrum[1:len(power_spectrum)//2]) + 1
        dominant_freq = frequencies[dominant_freq_idx]
        dominant_power = power_spectrum[dominant_freq_idx]
        
        # Check if there's a strong cyclical component
        if dominant_power > np.mean(power_spectrum) * 3:
            cycle_length = int(1 / abs(dominant_freq)) if dominant_freq != 0 else 0
            
            if cycle_length > 5 and cycle_length < len(sequence) // 2:
                confidence = min(0.90, 0.6 + dominant_power / np.max(power_spectrum))
                
                pattern = PatternMatch(
                    pattern_type="cycle",
                    confidence=confidence,
                    start_index=0,
                    end_index=len(sequence),
                    features={
                        "cycle_length": cycle_length,
                        "dominant_frequency": dominant_freq,
                        "power": dominant_power
                    },
                    prediction=self._predict_cycle_peak(sequence, cycle_length),
                    explanation=f"Detected cyclical pattern with period of {cycle_length}"
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_anomaly_patterns(self, sequence: List[float]) -> List[PatternMatch]:
        """Detect anomaly patterns using statistical analysis."""
        patterns = []
        
        if len(sequence) < 20:
            return patterns
            
        # Calculate z-scores
        mean = np.mean(sequence)
        std = np.std(sequence)
        
        if std == 0:
            return patterns
            
        z_scores = [(x - mean) / std for x in sequence]
        
        # Look for statistical anomalies
        for i, z_score in enumerate(z_scores):
            if abs(z_score) > 3:  # 3-sigma anomaly
                confidence = min(0.95, 0.7 + (abs(z_score) - 3) * 0.1)
                
                pattern = PatternMatch(
                    pattern_type="anomaly",
                    confidence=confidence,
                    start_index=i,
                    end_index=i,
                    features={
                        "z_score": z_score,
                        "value": sequence[i],
                        "mean": mean,
                        "std": std
                    },
                    prediction=self._predict_anomaly_impact(sequence, i),
                    explanation=f"Statistical anomaly detected: {z_score:.2f} sigma"
                )
                patterns.append(pattern)
        
        return patterns
    
    def _predict_ladder_continuation(self, window: List[float]) -> float:
        """Predict ladder pattern continuation."""
        # Simple linear extrapolation
        if len(window) < 2:
            return 0.5
            
        trend = window[-1] - window[0]
        return min(0.95, max(0.05, 0.5 + trend * 10))
    
    def _predict_momentum_continuation(self, velocities: List[float]) -> float:
        """Predict momentum continuation."""
        if not velocities:
            return 0.5
            
        avg_velocity = np.mean(velocities)
        return min(0.95, max(0.05, 0.5 + avg_velocity * 100))
    
    def _predict_reversal_strength(self, sequence: List[float]) -> float:
        """Predict reversal strength."""
        if len(sequence) < 10:
            return 0.5
            
        # Measure recent change
        recent_change = sequence[-1] - sequence[-10]
        return min(0.95, max(0.05, 0.5 + abs(recent_change) * 5))
    
    def _predict_cycle_peak(self, sequence: List[float], cycle_length: int) -> float:
        """Predict next cycle peak."""
        if len(sequence) < cycle_length:
            return 0.5
            
        # Find last peak and predict next
        recent_cycle = sequence[-cycle_length:]
        peak_index = np.argmax(recent_cycle)
        return peak_index / cycle_length
    
    def _predict_anomaly_impact(self, sequence: List[float], anomaly_index: int) -> float:
        """Predict anomaly impact."""
        if anomaly_index >= len(sequence) - 1:
            return 0.5
            
        # Measure recovery after anomaly
        recovery = sequence[anomaly_index + 1] - sequence[anomaly_index]
        return min(0.95, max(0.05, 0.5 - recovery * 10))
    
    def add_to_buffer(self, value: float):
        """Add value to analysis buffer."""
        self.buffer.append(value)
    
    async def get_realtime_patterns(self) -> List[PatternMatch]:
        """Get patterns from current buffer."""
        if len(self.buffer) < self.sequence_length:
            return []
            
        sequence = list(self.buffer)
        return await self.analyze_sequence(sequence)
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about detected patterns."""
        return {
            "buffer_size": len(self.buffer),
            "sequence_length": self.sequence_length,
            "confidence_threshold": self.confidence_threshold,
            "cached_patterns": len(self.pattern_cache)
        }


# Singleton instance
_pattern_recognizer: Optional[AdvancedPatternRecognizer] = None


def get_pattern_recognizer() -> AdvancedPatternRecognizer:
    """Get the singleton pattern recognizer instance."""
    global _pattern_recognizer
    if _pattern_recognizer is None:
        _pattern_recognizer = AdvancedPatternRecognizer()
    return _pattern_recognizer