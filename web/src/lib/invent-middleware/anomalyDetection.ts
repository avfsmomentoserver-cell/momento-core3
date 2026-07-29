/**
 * Anomaly Detection for Moonshot Predictions
 * 
 * Detects when moonshot predictions are falsely detected:
 * - Several times too low (underestimation)
 * - Falsely high (overestimation)
 * - Larger uncalculated or forecasted ranges
 * 
 * Applies range logic and anomaly detection to:
 * - Dashboards
 * - Chase distance calculations
 * - Control panel predictions
 * 
 * Follows strict middleware pattern - read-only access to platform API
 */

import type { NormalizedRound, NormalizedAnalysis } from './transformProcessor';

export interface AnomalyThreshold {
  low_warning: number;
  low_critical: number;
  high_warning: number;
  high_critical: number;
  range_multiplier: number;
}

export interface PredictionAnomaly {
  is_anomaly: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
  type: 'underestimation' | 'overestimation' | 'range_anomaly' | 'volatility_anomaly';
  predicted_value: number;
  actual_value: number;
  deviation: number;
  deviation_pct: number;
  confidence: number;
  timestamp: string;
}

export interface AnomalyPattern {
  pattern_type: 'consistent_underestimation' | 'consistent_overestimation' | 'volatile_predictions' | 'range_drift';
  frequency: number;
  severity: 'low' | 'medium' | 'high';
  samples: number;
  avg_deviation: number;
  max_deviation: number;
}

export interface AnomalyReport {
  recent_anomalies: PredictionAnomaly[];
  anomaly_patterns: AnomalyPattern[];
  prediction_accuracy: {
    total_predictions: number;
    accurate_predictions: number;
    false_lows: number;
    false_highs: number;
    accuracy_rate: number;
    avg_error: number;
  };
  range_analysis: {
    avg_range_width: number;
    range_volatility: number;
    range_drift: number;
    is_stable: boolean;
  };
  chase_distance_analysis: {
    current_chase_distance: number;
    optimal_chase_distance: number;
    distance_efficiency: number;
    recommended_adjustment: number;
  };
  recommendations: string[];
  alert_level: 'normal' | 'warning' | 'critical';
}

export interface AnomalyDetectionConfig {
  anomaly_window: number; // Number of predictions to analyze
  deviation_threshold: number; // Percentage deviation for anomaly detection
  pattern_threshold: number; // Minimum samples for pattern detection
  range_stability_threshold: number; // Threshold for range stability
  chase_distance_optimization: boolean; // Enable chase distance optimization
}

const DEFAULT_CONFIG: AnomalyDetectionConfig = {
  anomaly_window: 20,
  deviation_threshold: 0.3, // 30% deviation
  pattern_threshold: 5,
  range_stability_threshold: 0.5,
  chase_distance_optimization: true,
};

/**
 * Anomaly Detection Engine for Moonshot Predictions
 */
export class AnomalyDetector {
  private config: AnomalyDetectionConfig;
  private predictionHistory: Array<{
    predicted: number;
    actual: number;
    timestamp: string;
    confidence: number;
  }> = [];

  constructor(config: Partial<AnomalyDetectionConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Analyze predictions for anomalies
   */
  analyzePredictions(
    predictions: Array<{ predicted: number; confidence: number }>,
    actuals: number[]
  ): AnomalyReport {
    // Update prediction history
    this.updateHistory(predictions, actuals);

    // Detect recent anomalies
    const recentAnomalies = this.detectRecentAnomalies();

    // Analyze patterns
    const anomalyPatterns = this.detectPatterns();

    // Calculate prediction accuracy
    const predictionAccuracy = this.calculateAccuracy();

    // Analyze range stability
    const rangeAnalysis = this.analyzeRanges();

    // Analyze chase distance
    const chaseDistanceAnalysis = this.analyzeChaseDistance();

    // Generate recommendations
    const recommendations = this.generateRecommendations(
      recentAnomalies,
      anomalyPatterns,
      predictionAccuracy,
      rangeAnalysis
    );

    // Determine alert level
    const alertLevel = this.determineAlertLevel(recentAnomalies, anomalyPatterns);

    return {
      recent_anomalies: recentAnomalies,
      anomaly_patterns: anomalyPatterns,
      prediction_accuracy: predictionAccuracy,
      range_analysis: rangeAnalysis,
      chase_distance_analysis: chaseDistanceAnalysis,
      recommendations: recommendations,
      alert_level: alertLevel,
    };
  }

  /**
   * Detect anomalies in control panel predictions
   */
  detectControlPanelAnomalies(
    controlPanelPredictions: Array<{ value: number; source: string }>,
    actualMultiplier: number
  ): PredictionAnomaly[] {
    const anomalies: PredictionAnomaly[] = [];

    for (const prediction of controlPanelPredictions) {
      const deviation = Math.abs(prediction.value - actualMultiplier);
      const deviationPct = deviation / actualMultiplier;

      if (deviationPct > this.config.deviation_threshold) {
        const type = prediction.value < actualMultiplier ? 'underestimation' : 'overestimation';
        const severity = this.calculateSeverity(deviationPct);

        anomalies.push({
          is_anomaly: true,
          severity,
          type,
          predicted_value: prediction.value,
          actual_value: actualMultiplier,
          deviation,
          deviation_pct: deviationPct,
          confidence: 0.8,
          timestamp: new Date().toISOString(),
        });
      }
    }

    return anomalies;
  }

  /**
   * Apply range logic to predictions
   */
  applyRangeLogic(
    predictions: Array<{ min: number; max: number; confidence: number }>,
    currentMultiplier: number
  ): Array<{ min: number; max: number; confidence: number; is_valid: boolean; anomaly_type?: string }> {
    return predictions.map(pred => {
      const rangeWidth = pred.max - pred.min;
      const midPoint = (pred.min + pred.max) / 2;
      const deviationFromMid = Math.abs(currentMultiplier - midPoint) / midPoint;

      // Check for range anomalies
      let isValid = true;
      let anomalyType: string | undefined;

      if (rangeWidth > midPoint * this.config.range_stability_threshold) {
        isValid = false;
        anomalyType = 'excessive_range_width';
      }

      if (deviationFromMid > this.config.deviation_threshold) {
        isValid = false;
        anomalyType = 'value_outside_range';
      }

      if (pred.min > currentMultiplier) {
        isValid = false;
        anomalyType = 'underestimation';
      }

      if (pred.max < currentMultiplier) {
        isValid = false;
        anomalyType = 'overestimation';
      }

      return {
        ...pred,
        is_valid: isValid,
        anomaly_type: anomalyType,
      };
    });
  }

  /**
   * Calculate optimal chase distance with anomaly detection
   */
  calculateOptimalChaseDistance(
    currentDistance: number,
    historicalSuccess: Array<{ distance: number; success: boolean }>
  ): number {
    if (!this.config.chase_distance_optimization) {
      return currentDistance;
    }

    // Analyze historical success rates by distance
    const distanceAnalysis = this.analyzeDistanceSuccess(historicalSuccess);

    // Find optimal distance
    const optimalDistance = this.findOptimalDistance(distanceAnalysis);

    // Calculate efficiency
    const efficiency = this.calculateDistanceEfficiency(currentDistance, optimalDistance);

    // Apply adjustment if efficiency is low
    if (efficiency < 0.7) {
      const adjustment = (optimalDistance - currentDistance) * 0.3; // Gradual adjustment
      return Math.max(1, currentDistance + adjustment);
    }

    return currentDistance;
  }

  /**
   * Private helper methods
   */
  private updateHistory(
    predictions: Array<{ predicted: number; confidence: number }>,
    actuals: number[]
  ): void {
    const newEntries = predictions.map((pred, i) => ({
      predicted: pred.predicted,
      actual: actuals[i] || 0,
      timestamp: new Date().toISOString(),
      confidence: pred.confidence,
    }));

    this.predictionHistory = [...this.predictionHistory, ...newEntries];
    
    // Keep only recent history
    if (this.predictionHistory.length > this.config.anomaly_window * 2) {
      this.predictionHistory = this.predictionHistory.slice(-this.config.anomaly_window * 2);
    }
  }

  private detectRecentAnomalies(): PredictionAnomaly[] {
    const recent = this.predictionHistory.slice(-this.config.anomaly_window);
    const anomalies: PredictionAnomaly[] = [];

    for (const entry of recent) {
      const deviation = Math.abs(entry.predicted - entry.actual);
      const deviationPct = entry.actual > 0 ? deviation / entry.actual : 0;

      if (deviationPct > this.config.deviation_threshold) {
        const type = entry.predicted < entry.actual ? 'underestimation' : 'overestimation';
        const severity = this.calculateSeverity(deviationPct);

        anomalies.push({
          is_anomaly: true,
          severity,
          type,
          predicted_value: entry.predicted,
          actual_value: entry.actual,
          deviation,
          deviation_pct: deviationPct,
          confidence: entry.confidence,
          timestamp: entry.timestamp,
        });
      }
    }

    return anomalies;
  }

  private detectPatterns(): AnomalyPattern[] {
    const patterns: AnomalyPattern[] = [];
    const recent = this.predictionHistory.slice(-this.config.anomaly_window);

    if (recent.length < this.config.pattern_threshold) {
      return patterns;
    }

    // Check for consistent underestimation
    const underestimations = recent.filter(e => e.predicted < e.actual * 0.7);
    if (underestimations.length >= this.config.pattern_threshold) {
      patterns.push({
        pattern_type: 'consistent_underestimation',
        frequency: underestimations.length / recent.length,
        severity: this.calculatePatternSeverity(underestimations.length / recent.length),
        samples: underestimations.length,
        avg_deviation: this.calculateAvgDeviation(underestimations),
        max_deviation: this.calculateMaxDeviation(underestimations),
      });
    }

    // Check for consistent overestimation
    const overestimations = recent.filter(e => e.predicted > e.actual * 1.3);
    if (overestimations.length >= this.config.pattern_threshold) {
      patterns.push({
        pattern_type: 'consistent_overestimation',
        frequency: overestimations.length / recent.length,
        severity: this.calculatePatternSeverity(overestimations.length / recent.length),
        samples: overestimations.length,
        avg_deviation: this.calculateAvgDeviation(overestimations),
        max_deviation: this.calculateMaxDeviation(overestimations),
      });
    }

    // Check for volatile predictions
    const deviations = recent.map(e => Math.abs(e.predicted - e.actual) / e.actual);
    const volatility = this.calculateStandardDeviation(deviations);
    if (volatility > 0.5) {
      patterns.push({
        pattern_type: 'volatile_predictions',
        frequency: 1,
        severity: volatility > 0.8 ? 'high' : 'medium',
        samples: recent.length,
        avg_deviation: deviations.reduce((a, b) => a + b, 0) / deviations.length,
        max_deviation: Math.max(...deviations),
      });
    }

    return patterns;
  }

  private calculateAccuracy() {
    const recent = this.predictionHistory.slice(-this.config.anomaly_window);
    
    if (recent.length === 0) {
      return {
        total_predictions: 0,
        accurate_predictions: 0,
        false_lows: 0,
        false_highs: 0,
        accuracy_rate: 0,
        avg_error: 0,
      };
    }

    const accurate = recent.filter(e => Math.abs(e.predicted - e.actual) / e.actual < 0.2);
    const falseLows = recent.filter(e => e.predicted < e.actual * 0.7);
    const falseHighs = recent.filter(e => e.predicted > e.actual * 1.3);
    const errors = recent.map(e => Math.abs(e.predicted - e.actual) / e.actual);

    return {
      total_predictions: recent.length,
      accurate_predictions: accurate.length,
      false_lows: falseLows.length,
      false_highs: falseHighs.length,
      accuracy_rate: accurate.length / recent.length,
      avg_error: errors.reduce((a, b) => a + b, 0) / errors.length,
    };
  }

  private analyzeRanges() {
    const recent = this.predictionHistory.slice(-this.config.anomaly_window);
    
    if (recent.length < 2) {
      return {
        avg_range_width: 0,
        range_volatility: 0,
        range_drift: 0,
        is_stable: true,
      };
    }

    // Calculate range widths (using prediction as range center)
    const rangeWidths = recent.map(e => e.predicted * 0.2); // Assume 20% range width
    const avgRangeWidth = rangeWidths.reduce((a, b) => a + b, 0) / rangeWidths.length;
    const rangeVolatility = this.calculateStandardDeviation(rangeWidths) / avgRangeWidth;
    
    // Calculate range drift
    const firstHalf = rangeWidths.slice(0, Math.floor(rangeWidths.length / 2));
    const secondHalf = rangeWidths.slice(Math.floor(rangeWidths.length / 2));
    const firstAvg = firstHalf.reduce((a, b) => a + b, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((a, b) => a + b, 0) / secondHalf.length;
    const rangeDrift = Math.abs(secondAvg - firstAvg) / firstAvg;

    return {
      avg_range_width: avgRangeWidth,
      range_volatility: rangeVolatility,
      range_drift: rangeDrift,
      is_stable: rangeVolatility < this.config.range_stability_threshold && rangeDrift < 0.3,
    };
  }

  private analyzeChaseDistance() {
    // Placeholder for chase distance analysis
    // In production, this would analyze historical chase distances and success rates
    return {
      current_chase_distance: 10,
      optimal_chase_distance: 8,
      distance_efficiency: 0.8,
      recommended_adjustment: -2,
    };
  }

  private analyzeDistanceSuccess(historical: Array<{ distance: number; success: boolean }>) {
    // Group by distance ranges
    const distanceGroups: Record<number, { total: number; success: number }> = {};

    for (const entry of historical) {
      const distanceRange = Math.round(entry.distance / 5) * 5; // Group by 5s
      if (!distanceGroups[distanceRange]) {
        distanceGroups[distanceRange] = { total: 0, success: 0 };
      }
      distanceGroups[distanceRange].total++;
      if (entry.success) {
        distanceGroups[distanceRange].success++;
      }
    }

    return distanceGroups;
  }

  private findOptimalDistance(distanceGroups: Record<number, { total: number; success: number }>): number {
    let bestDistance = 10;
    let bestSuccessRate = 0;

    for (const [distance, data] of Object.entries(distanceGroups)) {
      const successRate = data.success / data.total;
      if (successRate > bestSuccessRate && data.total >= 3) {
        bestSuccessRate = successRate;
        bestDistance = Number(distance);
      }
    }

    return bestDistance;
  }

  private calculateDistanceEfficiency(current: number, optimal: number): number {
    const diff = Math.abs(current - optimal);
    return Math.max(0, 1 - (diff / optimal));
  }

  private generateRecommendations(
    anomalies: PredictionAnomaly[],
    patterns: AnomalyPattern[],
    accuracy: { accuracy_rate: number; false_lows: number; false_highs: number },
    rangeAnalysis: { is_stable: boolean; range_volatility: number }
  ): string[] {
    const recommendations: string[] = [];

    if (accuracy.accuracy_rate < 0.6) {
      recommendations.push('Prediction accuracy is below 60%. Review prediction model parameters.');
    }

    if (accuracy.false_lows > accuracy.false_highs * 2) {
      recommendations.push('System consistently underestimates. Increase prediction bias by 15-20%.');
    }

    if (accuracy.false_highs > accuracy.false_lows * 2) {
      recommendations.push('System consistently overestimates. Decrease prediction bias by 15-20%.');
    }

    if (!rangeAnalysis.is_stable) {
      recommendations.push('Prediction ranges are unstable. Implement range smoothing algorithm.');
    }

    if (patterns.some(p => p.pattern_type === 'volatile_predictions')) {
      recommendations.push('High prediction volatility detected. Increase smoothing factor in forecast engine.');
    }

    if (anomalies.filter(a => a.severity === 'critical').length > 2) {
      recommendations.push('CRITICAL: Multiple critical anomalies detected. Immediate system review required.');
    }

    if (recommendations.length === 0) {
      recommendations.push('System operating within normal parameters. Continue monitoring.');
    }

    return recommendations;
  }

  private determineAlertLevel(
    anomalies: PredictionAnomaly[],
    patterns: AnomalyPattern[]
  ): 'normal' | 'warning' | 'critical' {
    const criticalAnomalies = anomalies.filter(a => a.severity === 'critical').length;
    const highSeverityPatterns = patterns.filter(p => p.severity === 'high').length;

    if (criticalAnomalies > 2 || highSeverityPatterns > 1) {
      return 'critical';
    }

    if (anomalies.filter(a => a.severity === 'high').length > 3 || patterns.length > 2) {
      return 'warning';
    }

    return 'normal';
  }

  private calculateSeverity(deviationPct: number): 'low' | 'medium' | 'high' | 'critical' {
    if (deviationPct > 0.8) return 'critical';
    if (deviationPct > 0.5) return 'high';
    if (deviationPct > 0.3) return 'medium';
    return 'low';
  }

  private calculatePatternSeverity(frequency: number): 'low' | 'medium' | 'high' {
    if (frequency > 0.7) return 'high';
    if (frequency > 0.4) return 'medium';
    return 'low';
  }

  private calculateAvgDeviation(entries: Array<{ predicted: number; actual: number }>): number {
    const deviations = entries.map(e => Math.abs(e.predicted - e.actual) / e.actual);
    return deviations.reduce((a, b) => a + b, 0) / deviations.length;
  }

  private calculateMaxDeviation(entries: Array<{ predicted: number; actual: number }>): number {
    const deviations = entries.map(e => Math.abs(e.predicted - e.actual) / e.actual);
    return Math.max(...deviations);
  }

  private calculateStandardDeviation(values: number[]): number {
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const squaredDiffs = values.map(v => Math.pow(v - mean, 2));
    return Math.sqrt(squaredDiffs.reduce((a, b) => a + b, 0) / values.length);
  }
}

// Export singleton instance
export const anomalyDetector = new AnomalyDetector();