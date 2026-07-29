"""
Advanced Self-Awareness System for V5
Implements automated learning, optimization, and failover management
"""

from __future__ import annotations

import logging
import asyncio
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from collections import deque
import numpy as np

logger = logging.getLogger("momento.self_awareness")


@dataclass
class SystemHealth:
    """Represents current system health status."""
    overall_health: str  # healthy, degraded, critical
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    network_latency: float
    error_rate: float
    throughput: float
    gpu_utilization: float
    prediction_accuracy: float
    ingestion_latency: float
    timestamp: datetime


@dataclass
class OptimizationAction:
    """Represents an optimization action taken by the system."""
    action_type: str
    parameters: Dict[str, Any]
    reason: str
    expected_impact: str
    executed_at: datetime
    result: Optional[str] = None


@dataclass
class LearningInsight:
    """Represents a learning insight from system behavior."""
    insight_type: str
    pattern: str
    confidence: float
    recommendation: str
    discovered_at: datetime
    validated: bool = False


class AdvancedSelfAwarenessSystem:
    """
    Advanced self-awareness system with automated learning and optimization.
    Monitors system health, learns from patterns, and automatically optimizes.
    """
    
    def __init__(self, learning_window_hours: int = 24):
        self.learning_window_hours = learning_window_hours
        self.health_history = deque(maxlen=1000)
        self.optimization_history = deque(maxlen=100)
        self.learning_insights = deque(maxlen=500)
        self.baseline_health: Optional[SystemHealth] = None
        self._running = False
        self._optimization_enabled = True
        
    async def start(self):
        """Start the self-awareness system."""
        if self._running:
            return
            
        self._running = True
        logger.info("Advanced self-awareness system started")
        
        # Start background tasks
        asyncio.create_task(self._health_monitoring_loop())
        asyncio.create_task(self._learning_loop())
        asyncio.create_task(self._optimization_loop())
        
    async def stop(self):
        """Stop the self-awareness system."""
        self._running = False
        logger.info("Advanced self-awareness system stopped")
        
    async def _health_monitoring_loop(self):
        """Continuous health monitoring loop."""
        while self._running:
            try:
                health = await self._collect_system_health()
                self.health_history.append(health)
                
                # Set baseline if not set
                if self.baseline_health is None:
                    self.baseline_health = health
                    
                # Check for health anomalies
                await self._detect_health_anomalies(health)
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as exc:
                logger.error("Health monitoring error: %s", exc)
                await asyncio.sleep(60)
    
    async def _learning_loop(self):
        """Continuous learning loop."""
        while self._running:
            try:
                # Analyze patterns every 5 minutes
                await self._analyze_performance_patterns()
                await self._detect_learning_opportunities()
                
                await asyncio.sleep(300)  # Learn every 5 minutes
                
            except Exception as exc:
                logger.error("Learning loop error: %s", exc)
                await asyncio.sleep(600)
    
    async def _optimization_loop(self):
        """Continuous optimization loop."""
        while self._running:
            try:
                if self._optimization_enabled:
                    await self._evaluate_optimization_opportunities()
                    
                await asyncio.sleep(600)  # Optimize every 10 minutes
                
            except Exception as exc:
                logger.error("Optimization loop error: %s", exc)
                await asyncio.sleep(1200)
    
    async def _collect_system_health(self) -> SystemHealth:
        """Collect current system health metrics."""
        # Placeholder for actual health collection
        # In production, this would collect real metrics
        
        health = SystemHealth(
            overall_health="healthy",
            cpu_usage=0.45,  # Placeholder
            memory_usage=0.60,  # Placeholder
            disk_usage=0.70,  # Placeholder
            network_latency=0.025,  # Placeholder
            error_rate=0.001,  # Placeholder
            throughput=1000.0,  # Placeholder
            gpu_utilization=0.75,  # Placeholder
            prediction_accuracy=0.92,  # Placeholder
            ingestion_latency=0.0005,  # Placeholder
            timestamp=datetime.now(timezone.utc)
        )
        
        return health
    
    async def _detect_health_anomalies(self, current_health: SystemHealth):
        """Detect anomalies in current health compared to baseline."""
        if self.baseline_health is None:
            return
            
        anomalies = []
        
        # Check CPU usage
        if current_health.cpu_usage > self.baseline_health.cpu_usage * 1.5:
            anomalies.append("high_cpu_usage")
            
        # Check memory usage
        if current_health.memory_usage > self.baseline_health.memory_usage * 1.3:
            anomalies.append("high_memory_usage")
            
        # Check error rate
        if current_health.error_rate > self.baseline_health.error_rate * 2:
            anomalies.append("high_error_rate")
            
        # Check latency
        if current_health.network_latency > self.baseline_health.network_latency * 2:
            anomalies.append("high_latency")
            
        # Check prediction accuracy
        if current_health.prediction_accuracy < self.baseline_health.prediction_accuracy * 0.9:
            anomalies.append("low_accuracy")
            
        if anomalies:
            logger.warning("Health anomalies detected: %s", anomalies)
            await self._handle_health_anomalies(anomalies, current_health)
    
    async def _handle_health_anomalies(self, anomalies: List[str], health: SystemHealth):
        """Handle detected health anomalies."""
        for anomaly in anomalies:
            if anomaly == "high_cpu_usage":
                await self._optimize_cpu_usage()
            elif anomaly == "high_memory_usage":
                await self._optimize_memory_usage()
            elif anomaly == "high_error_rate":
                await self._investigate_errors()
            elif anomaly == "high_latency":
                await self._optimize_latency()
            elif anomaly == "low_accuracy":
                await self._improve_accuracy()
    
    async def _optimize_cpu_usage(self):
        """Optimize CPU usage."""
        action = OptimizationAction(
            action_type="cpu_optimization",
            parameters={"strategy": "reduce_batch_size"},
            reason="High CPU usage detected",
            expected_impact="Reduce CPU usage by 15-20%",
            executed_at=datetime.now(timezone.utc)
        )
        
        logger.info("Executing CPU optimization: %s", action.reason)
        # Placeholder for actual optimization logic
        action.result = "success"
        self.optimization_history.append(action)
    
    async def _optimize_memory_usage(self):
        """Optimize memory usage."""
        action = OptimizationAction(
            action_type="memory_optimization",
            parameters={"strategy": "clear_cache"},
            reason="High memory usage detected",
            expected_impact="Reduce memory usage by 10-15%",
            executed_at=datetime.now(timezone.utc)
        )
        
        logger.info("Executing memory optimization: %s", action.reason)
        # Placeholder for actual optimization logic
        action.result = "success"
        self.optimization_history.append(action)
    
    async def _investigate_errors(self):
        """Investigate high error rate."""
        action = OptimizationAction(
            action_type="error_investigation",
            parameters={"investigate_recent_errors": True},
            reason="High error rate detected",
            expected_impact="Identify and resolve error sources",
            executed_at=datetime.now(timezone.utc)
        )
        
        logger.info("Investigating errors: %s", action.reason)
        # Placeholder for actual investigation logic
        action.result = "identified_network_timeout"
        self.optimization_history.append(action)
    
    async def _optimize_latency(self):
        """Optimize network latency."""
        action = OptimizationAction(
            action_type="latency_optimization",
            parameters={"strategy": "optimize_routing"},
            reason="High latency detected",
            expected_impact="Reduce latency by 20-30%",
            executed_at=datetime.now(timezone.utc)
        )
        
        logger.info("Executing latency optimization: %s", action.reason)
        # Placeholder for actual optimization logic
        action.result = "success"
        self.optimization_history.append(action)
    
    async def _improve_accuracy(self):
        """Improve prediction accuracy."""
        action = OptimizationAction(
            action_type="accuracy_improvement",
            parameters={"strategy": "retrain_model"},
            reason="Low prediction accuracy detected",
            expected_impact="Improve accuracy by 2-5%",
            executed_at=datetime.now(timezone.utc)
        )
        
        logger.info("Improving accuracy: %s", action.reason)
        # Placeholder for actual improvement logic
        action.result = "success"
        self.optimization_history.append(action)
    
    async def _analyze_performance_patterns(self):
        """Analyze performance patterns over time."""
        if len(self.health_history) < 10:
            return
            
        recent_health = list(self.health_history)[-10:]
        
        # Analyze trends
        cpu_trend = self._calculate_trend([h.cpu_usage for h in recent_health])
        memory_trend = self._calculate_trend([h.memory_usage for h in recent_health])
        accuracy_trend = self._calculate_trend([h.prediction_accuracy for h in recent_health])
        
        # Generate insights
        if cpu_trend > 0.1:
            insight = LearningInsight(
                insight_type="performance_trend",
                pattern="increasing_cpu_usage",
                confidence=0.8,
                recommendation="Consider scaling or optimizing CPU-intensive operations",
                discovered_at=datetime.now(timezone.utc)
            )
            self.learning_insights.append(insight)
            
        if accuracy_trend < -0.05:
            insight = LearningInsight(
                insight_type="performance_trend",
                pattern="decreasing_accuracy",
                confidence=0.85,
                recommendation="Investigate model drift and consider retraining",
                discovered_at=datetime.now(timezone.utc)
            )
            self.learning_insights.append(insight)
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (positive = increasing, negative = decreasing)."""
        if len(values) < 2:
            return 0.0
            
        return (values[-1] - values[0]) / len(values)
    
    async def _detect_learning_opportunities(self):
        """Detect opportunities for system learning."""
        if len(self.health_history) < 20:
            return
            
        # Look for correlations between metrics
        recent_health = list(self.health_history)[-20:]
        
        cpu_values = [h.cpu_usage for h in recent_health]
        accuracy_values = [h.prediction_accuracy for h in recent_health]
        
        correlation = np.corrcoef(cpu_values, accuracy_values)[0, 1]
        
        if not np.isnan(correlation) and abs(correlation) > 0.7:
            insight = LearningInsight(
                insight_type="correlation_discovery",
                pattern=f"cpu_accuracy_correlation_{correlation:.2f}",
                confidence=abs(correlation),
                recommendation=f"Strong correlation ({correlation:.2f}) between CPU and accuracy - optimize resource allocation",
                discovered_at=datetime.now(timezone.utc)
            )
            self.learning_insights.append(insight)
    
    async def _evaluate_optimization_opportunities(self):
        """Evaluate and execute optimization opportunities."""
        # Get recent insights
        recent_insights = [i for i in self.learning_insights 
                          if i.discovered_at > datetime.now(timezone.utc) - timedelta(hours=1)]
        
        for insight in recent_insights:
            if insight.confidence > 0.8 and not insight.validated:
                await self._execute_optimization_from_insight(insight)
                insight.validated = True
    
    async def _execute_optimization_from_insight(self, insight: LearningInsight):
        """Execute optimization based on learning insight."""
        action = OptimizationAction(
            action_type="insight_based_optimization",
            parameters={"insight_id": insight.insight_type},
            reason=insight.recommendation,
            expected_impact="Apply learned optimization",
            executed_at=datetime.now(timezone.utc)
        )
        
        logger.info("Executing insight-based optimization: %s", insight.recommendation)
        # Placeholder for actual optimization logic
        action.result = "success"
        self.optimization_history.append(action)
    
    async def trigger_failover(self, reason: str):
        """Trigger failover to secondary region."""
        logger.critical("Triggering failover: %s", reason)
        
        action = OptimizationAction(
            action_type="emergency_failover",
            parameters={"reason": reason},
            reason=reason,
            expected_impact="Switch to secondary region",
            executed_at=datetime.now(timezone.utc)
        )
        
        # Placeholder for actual failover logic
        action.result = "failover_initiated"
        self.optimization_history.append(action)
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get current system health."""
        return self.health_history[-1] if self.health_history else None
    
    def get_optimization_history(self, limit: int = 10) -> List[OptimizationAction]:
        """Get recent optimization history."""
        return list(self.optimization_history)[-limit:]
    
    def get_learning_insights(self, limit: int = 10) -> List[LearningInsight]:
        """Get recent learning insights."""
        return list(self.learning_insights)[-limit:]
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get comprehensive system summary."""
        current_health = self.get_current_health()
        
        return {
            "current_health": asdict(current_health) if current_health else None,
            "baseline_health": asdict(self.baseline_health) if self.baseline_health else None,
            "health_history_size": len(self.health_history),
            "optimization_count": len(self.optimization_history),
            "learning_insights_count": len(self.learning_insights),
            "optimization_enabled": self._optimization_enabled,
            "learning_window_hours": self.learning_window_hours
        }


# Singleton instance
_self_awareness_system: Optional[AdvancedSelfAwarenessSystem] = None


def get_self_awareness_system() -> AdvancedSelfAwarenessSystem:
    """Get the singleton self-awareness system instance."""
    global _self_awareness_system
    if _self_awareness_system is None:
        _self_awareness_system = AdvancedSelfAwarenessSystem()
    return _self_awareness_system