/**
 * Rubberband Analysis - Elastic Moonshot Prediction
 * 
 * Analyzes rounds as if they were being pulled down elastically like a rubberband
 * Predicts when the rubberband will "snap" to a mega moonshot
 * 
 * Core Concepts:
 * - Elastic tension: How much "pull" is in the system
 * - Snap prediction: When tension will release to moonshot
 * - Lower tier moonshot integration: Enhanced detection when lower tiers are present
 * 
 * Follows strict middleware pattern - read-only access to platform API
 */

import type { NormalizedRound, NormalizedAnalysis } from './transformProcessor';

export interface RubberbandTension {
  current_tension: number; // 0-1 scale
  tension_trend: 'increasing' | 'decreasing' | 'stable';
  elastic_potential: number; // Potential energy stored
  resistance_points: number; // Points of resistance
  snap_probability: number; // Probability of snap occurring
}

export interface RubberbandSnap {
  predicted_multiplier: number;
  confidence: number;
  estimated_rounds: number;
  tension_threshold: number;
  snap_type: 'mega_moonshot' | 'high_moonshot' | 'medium_moonshot';
  contributing_factors: string[];
}

export interface RubberbandAnalysis {
  tension: RubberbandTension;
  snap_prediction: RubberbandSnap | null;
  lower_tier_influence: {
    has_lower_tier: boolean;
    influence_factor: number;
    moonshot_probability: number;
  };
  historical_snaps: {
    count: number;
    avg_multiplier: number;
    avg_tension_at_snap: number;
  };
  recommendation: string;
}

export interface RubberbandConfig {
  tension_window: number; // Rounds to analyze for tension
  snap_threshold: number; // Tension level for snap prediction
  lower_tier_threshold: number; // Multiplier threshold for lower tier
  mega_moonshot_threshold: number; // Multiplier for mega moonshot
  min_confidence: number; // Minimum confidence for predictions
}

const DEFAULT_CONFIG: RubberbandConfig = {
  tension_window: 20,
  snap_threshold: 0.75,
  lower_tier_threshold: 5.0,
  mega_moonshot_threshold: 50.0,
  min_confidence: 0.6,
};

/**
 * Rubberband Analysis Engine
 */
export class RubberbandAnalyzer {
  private config: RubberbandConfig;

  constructor(config: Partial<RubberbandConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Perform comprehensive rubberband analysis
   */
  analyze(rounds: NormalizedRound[], analysis?: NormalizedAnalysis): RubberbandAnalysis {
    if (rounds.length < this.config.tension_window) {
      return this.createEmptyAnalysis();
    }

    const recentRounds = rounds.slice(-this.config.tension_window);
    
    // Calculate tension
    const tension = this.calculateTension(recentRounds);
    
    // Predict snap
    const snapPrediction = this.predictSnap(recentRounds, tension, analysis);
    
    // Analyze lower tier influence
    const lowerTierInfluence = this.analyzeLowerTierInfluence(recentRounds);
    
    // Analyze historical snaps
    const historicalSnaps = this.analyzeHistoricalSnaps(rounds);
    
    // Generate recommendation
    const recommendation = this.generateRecommendation(tension, snapPrediction, lowerTierInfluence);

    return {
      tension,
      snap_prediction: snapPrediction,
      lower_tier_influence: lowerTierInfluence,
      historical_snaps: historicalSnaps,
      recommendation,
    };
  }

  /**
   * Calculate elastic tension from recent rounds
   */
  private calculateTension(rounds: NormalizedRound[]): RubberbandTension {
    const multipliers = rounds.map(r => r.multiplier);
    
    // Calculate elastic potential (deviation from baseline)
    const baseline = 1.0;
    const deviations = multipliers.map(m => Math.abs(m - baseline));
    const avgDeviation = deviations.reduce((a, b) => a + b, 0) / deviations.length;
    const elasticPotential = Math.min(1, avgDeviation / 10); // Normalize to 0-1
    
    // Calculate tension trend
    const recentTrend = this.calculateTrend(deviations.slice(-5));
    const tensionTrend = recentTrend > 0.1 ? 'increasing' : 
                        recentTrend < -0.1 ? 'decreasing' : 'stable';
    
    // Calculate resistance points (local maxima in tension)
    const resistancePoints = this.countResistancePoints(deviations);
    
    // Calculate snap probability based on tension
    const snapProbability = this.calculateSnapProbability(elasticPotential, resistancePoints);
    
    // Current tension (0-1 scale)
    const currentTension = Math.min(1, (elasticPotential * 0.6) + (snapProbability * 0.4));

    return {
      current_tension: currentTension,
      tension_trend: tensionTrend,
      elastic_potential: elasticPotential,
      resistance_points: resistancePoints,
      snap_probability: snapProbability,
    };
  }

  /**
   * Predict when rubberband will snap
   */
  private predictSnap(
    rounds: NormalizedRound[],
    tension: RubberbandTension,
    analysis?: NormalizedAnalysis
  ): RubberbandSnap | null {
    // Only predict if tension is above threshold
    if (tension.current_tension < this.config.snap_threshold) {
      return null;
    }

    // Calculate confidence based on tension and trend
    let confidence = tension.current_tension;
    if (tension.tension_trend === 'increasing') {
      confidence += 0.1;
    }
    confidence = Math.min(1, confidence);

    // Only provide prediction if confidence meets minimum
    if (confidence < this.config.min_confidence) {
      return null;
    }

    // Determine snap type and predicted multiplier
    const snapType = this.determineSnapType(tension, analysis);
    const predictedMultiplier = this.calculatePredictedMultiplier(snapType, tension);
    
    // Estimate rounds until snap
    const estimatedRounds = this.estimateRoundsUntilSnap(tension);

    // Identify contributing factors
    const contributingFactors = this.identifyContributingFactors(tension, analysis);

    return {
      predicted_multiplier: predictedMultiplier,
      confidence,
      estimated_rounds: estimatedRounds,
      tension_threshold: this.config.snap_threshold,
      snap_type: snapType,
      contributing_factors: contributingFactors,
    };
  }

  /**
   * Analyze lower tier moonshot influence
   */
  private analyzeLowerTierInfluence(rounds: NormalizedRound[]) {
    const lowerTierRounds = rounds.filter(
      r => r.multiplier >= this.config.lower_tier_threshold && 
           r.multiplier < this.config.mega_moonshot_threshold
    );

    const hasLowerTier = lowerTierRounds.length > 0;
    
    // Calculate influence factor based on frequency and recency
    let influenceFactor = 0;
    if (hasLowerTier) {
      const frequency = lowerTierRounds.length / rounds.length;
      const recencyBonus = lowerTierRounds.slice(-3).length / 3;
      influenceFactor = Math.min(1, (frequency * 0.7) + (recencyBonus * 0.3));
    }

    // Calculate moonshot probability based on lower tier presence
    const moonshotProbability = hasLowerTier ? 
      0.3 + (influenceFactor * 0.4) : 0.1;

    return {
      has_lower_tier: hasLowerTier,
      influence_factor: influenceFactor,
      moonshot_probability: moonshotProbability,
    };
  }

  /**
   * Analyze historical snap patterns
   */
  private analyzeHistoricalSnaps(rounds: NormalizedRound[]) {
    const moonshots = rounds.filter(r => r.multiplier >= this.config.mega_moonshot_threshold);
    
    if (moonshots.length === 0) {
      return {
        count: 0,
        avg_multiplier: 0,
        avg_tension_at_snap: 0,
      };
    }

    const avgMultiplier = moonshots.reduce((sum, r) => sum + r.multiplier, 0) / moonshots.length;
    
    // Calculate average tension before these moonshots
    const avgTensionAtSnap = 0.8; // Placeholder - would need historical tension data

    return {
      count: moonshots.length,
      avg_multiplier: avgMultiplier,
      avg_tension_at_snap: avgTensionAtSnap,
    };
  }

  /**
   * Generate trading recommendation
   */
  private generateRecommendation(
    tension: RubberbandTension,
    snapPrediction: RubberbandSnap | null,
    lowerTierInfluence: { has_lower_tier: boolean; influence_factor: number }
  ): string {
    if (!snapPrediction) {
      if (tension.current_tension > 0.6) {
        return "Tension building. Monitor for snap signals.";
      }
      return "Low tension. No immediate snap expected.";
    }

    if (snapPrediction.snap_type === 'mega_moonshot') {
      if (lowerTierInfluence.has_lower_tier) {
        return "STRONG SNAP SIGNAL: Lower tier moonshots detected with high tension. Mega moonshot imminent.";
      }
      return "MEGA MOONSHOT ALERT: High tension with snap prediction imminent.";
    }

    if (snapPrediction.confidence > 0.8) {
      return `HIGH CONFIDENCE SNAP: ${snapPrediction.snap_type} predicted in ${snapPrediction.estimated_rounds} rounds.`;
    }

    return `MODERATE SNAP: ${snapPrediction.snap_type} possible. Monitor tension buildup.`;
  }

  /**
   * Helper methods
   */
  private calculateTrend(values: number[]): number {
    if (values.length < 2) return 0;
    const first = values[0];
    const last = values[values.length - 1];
    return (last - first) / first;
  }

  private countResistancePoints(deviations: number[]): number {
    let count = 0;
    for (let i = 1; i < deviations.length - 1; i++) {
      if (deviations[i] > deviations[i - 1] && deviations[i] > deviations[i + 1]) {
        count++;
      }
    }
    return count;
  }

  private calculateSnapProbability(elasticPotential: number, resistancePoints: number): number {
    const baseProbability = elasticPotential;
    const resistanceBonus = Math.min(0.3, resistancePoints * 0.1);
    return Math.min(1, baseProbability + resistanceBonus);
  }

  private determineSnapType(
    tension: RubberbandTension,
    analysis?: NormalizedAnalysis
  ): 'mega_moonshot' | 'high_moonshot' | 'medium_moonshot' {
    if (tension.current_tension > 0.9) {
      return 'mega_moonshot';
    }
    if (tension.current_tension > 0.75) {
      return 'high_moonshot';
    }
    return 'medium_moonshot';
  }

  private calculatePredictedMultiplier(
    snapType: 'mega_moonshot' | 'high_moonshot' | 'medium_moonshot',
    tension: RubberbandTension
  ): number {
    const baseMultipliers = {
      mega_moonshot: this.config.mega_moonshot_threshold,
      high_moonshot: 25.0,
      medium_moonshot: 10.0,
    };

    const base = baseMultipliers[snapType];
    const tensionBonus = tension.elastic_potential * 20;
    return base + tensionBonus;
  }

  private estimateRoundsUntilSnap(tension: RubberbandTension): number {
    if (tension.tension_trend === 'increasing') {
      return Math.max(1, Math.floor((1 - tension.current_tension) * 10));
    }
    return Math.max(1, Math.floor((1 - tension.current_tension) * 15));
  }

  private identifyContributingFactors(
    tension: RubberbandTension,
    analysis?: NormalizedAnalysis
  ): string[] {
    const factors: string[] = [];

    if (tension.elastic_potential > 0.7) {
      factors.push('High elastic potential');
    }
    if (tension.resistance_points > 2) {
      factors.push('Multiple resistance points');
    }
    if (tension.tension_trend === 'increasing') {
      factors.push('Increasing tension trend');
    }
    if (analysis?.marketState === 'Collapse') {
      factors.push('Market collapse state');
    }
    if (analysis?.volatility && analysis.volatility > 0.5) {
      factors.push('High volatility');
    }

    return factors;
  }

  private createEmptyAnalysis(): RubberbandAnalysis {
    return {
      tension: {
        current_tension: 0,
        tension_trend: 'stable',
        elastic_potential: 0,
        resistance_points: 0,
        snap_probability: 0,
      },
      snap_prediction: null,
      lower_tier_influence: {
        has_lower_tier: false,
        influence_factor: 0,
        moonshot_probability: 0,
      },
      historical_snaps: {
        count: 0,
        avg_multiplier: 0,
        avg_tension_at_snap: 0,
      },
      recommendation: 'Insufficient data for rubberband analysis',
    };
  }
}

// Export singleton instance
export const rubberbandAnalyzer = new RubberbandAnalyzer();