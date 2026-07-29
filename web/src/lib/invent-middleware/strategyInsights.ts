/**
 * Strategy Insights System
 * 
 * Provides actionable trading insights based on:
 * - Streak detection (winning/losing streaks)
 * - Safe entries live signals
 * - Overdue moonshot signals
 * - 1x band exhaustion signals
 * - Overdue pressure release signals
 * 
 * Follows strict middleware pattern - read-only access to platform API
 */

import type { NormalizedRound, NormalizedAnalysis } from './transformProcessor';

export interface StreakInsight {
  streak_type: 'winning' | 'losing' | 'neutral';
  current_streak: number;
  longest_streak: number;
  avg_streak_length: number;
  confidence: number;
  recommendation: string;
  expected_reversal_rounds: number;
}

export interface SafeEntrySignal {
  is_safe: boolean;
  confidence: number;
  entry_type: 'low_risk' | 'medium_risk' | 'high_risk';
  optimal_multiplier: number;
  risk_reward_ratio: number;
  supporting_factors: string[];
  warning_factors: string[];
  expiry_rounds: number;
}

export interface OverdueMoonshotSignal {
  is_overdue: boolean;
  overdue_ratio: number;
  expected_multiplier: number;
  confidence: number;
  rounds_since_last: number;
  expected_gap: number;
  urgency: 'low' | 'medium' | 'high' | 'critical';
  recommendation: string;
}

export interface BandExhaustionSignal {
  band: string;
  is_exhausted: boolean;
  exhaustion_level: number; // 0-1 scale
  rounds_since_exhaustion: number;
  expected_release_rounds: number;
  release_direction: 'up' | 'down' | 'neutral';
  confidence: number;
}

export interface PressureReleaseSignal {
  pressure_type: 'accumulation' | 'distribution' | 'volatility';
  current_pressure: number; // 0-1 scale
  is_overdue: boolean;
  expected_release_rounds: number;
  release_magnitude: number;
  confidence: number;
  recommendation: string;
}

export interface StrategyInsights {
  streak_insight: StreakInsight;
  safe_entry_signal: SafeEntrySignal;
  overdue_moonshot: OverdueMoonshotSignal;
  band_exhaustion: BandExhaustionSignal[];
  pressure_release: PressureReleaseSignal;
  overall_recommendation: string;
  confidence: number;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  actionable_signals: string[];
}

export interface StrategyInsightsConfig {
  streak_threshold: number; // Minimum rounds for streak detection
  safe_entry_confidence: number; // Minimum confidence for safe entry
  moonshot_threshold: number; // Multiplier threshold for moonshot
  overdue_threshold: number; // Overdue ratio threshold
  exhaustion_threshold: number; // Exhaustion level threshold
  pressure_threshold: number; // Pressure level threshold
}

const DEFAULT_CONFIG: StrategyInsightsConfig = {
  streak_threshold: 3,
  safe_entry_confidence: 0.7,
  moonshot_threshold: 10.0,
  overdue_threshold: 1.5,
  exhaustion_threshold: 0.8,
  pressure_threshold: 0.75,
};

/**
 * Strategy Insights Engine
 */
export class StrategyInsightsEngine {
  private config: StrategyInsightsConfig;

  constructor(config: Partial<StrategyInsightsConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Generate comprehensive strategy insights
   */
  generateInsights(
    rounds: NormalizedRound[],
    analysis?: NormalizedAnalysis
  ): StrategyInsights {
    // Analyze streaks
    const streakInsight = this.analyzeStreaks(rounds);

    // Generate safe entry signal
    const safeEntrySignal = this.generateSafeEntrySignal(rounds, analysis);

    // Check overdue moonshot
    const overdueMoonshot = this.checkOverdueMoonshot(rounds, analysis);

    // Analyze band exhaustion
    const bandExhaustion = this.analyzeBandExhaustion(rounds, analysis);

    // Analyze pressure release
    const pressureRelease = this.analyzePressureRelease(rounds, analysis);

    // Generate overall recommendation
    const overallRecommendation = this.generateOverallRecommendation(
      streakInsight,
      safeEntrySignal,
      overdueMoonshot,
      bandExhaustion,
      pressureRelease
    );

    // Calculate overall confidence
    const confidence = this.calculateOverallConfidence(
      streakInsight,
      safeEntrySignal,
      overdueMoonshot,
      bandExhaustion,
      pressureRelease
    );

    // Determine risk level
    const riskLevel = this.determineRiskLevel(
      streakInsight,
      safeEntrySignal,
      overdueMoonshot,
      pressureRelease
    );

    // Generate actionable signals
    const actionableSignals = this.generateActionableSignals(
      streakInsight,
      safeEntrySignal,
      overdueMoonshot,
      bandExhaustion,
      pressureRelease
    );

    return {
      streak_insight: streakInsight,
      safe_entry_signal: safeEntrySignal,
      overdue_moonshot: overdueMoonshot,
      band_exhaustion: bandExhaustion,
      pressure_release: pressureRelease,
      overall_recommendation: overallRecommendation,
      confidence,
      risk_level: riskLevel,
      actionable_signals: actionableSignals,
    };
  }

  /**
   * Analyze winning/losing streaks
   */
  private analyzeStreaks(rounds: NormalizedRound[]): StreakInsight {
    if (rounds.length < this.config.streak_threshold) {
      return this.createDefaultStreakInsight();
    }

    const recentRounds = rounds.slice(-20);
    const baseline = 1.5; // Threshold for "winning" round

    // Calculate current streak
    let currentStreak = 0;
    let streakType: 'winning' | 'losing' | 'neutral' = 'neutral';
    
    for (let i = recentRounds.length - 1; i >= 0; i--) {
      if (recentRounds[i].multiplier >= baseline) {
        if (streakType === 'losing' || streakType === 'neutral') {
          break;
        }
        streakType = 'winning';
        currentStreak++;
      } else {
        if (streakType === 'winning' || streakType === 'neutral') {
          break;
        }
        streakType = 'losing';
        currentStreak++;
      }
    }

    // Calculate longest streak
    const longestStreak = this.calculateLongestStreak(recentRounds, baseline);

    // Calculate average streak length
    const avgStreakLength = this.calculateAvgStreakLength(recentRounds, baseline);

    // Calculate confidence
    const confidence = Math.min(1, currentStreak / (this.config.streak_threshold * 2));

    // Generate recommendation
    const recommendation = this.generateStreakRecommendation(streakType, currentStreak, longestStreak);

    // Estimate expected reversal rounds
    const expectedReversalRounds = this.estimateReversalRounds(currentStreak, avgStreakLength);

    return {
      streak_type: streakType,
      current_streak: currentStreak,
      longest_streak: longestStreak,
      avg_streak_length: avgStreakLength,
      confidence,
      recommendation,
      expected_reversal_rounds: expectedReversalRounds,
    };
  }

  /**
   * Generate safe entry signal
   */
  private generateSafeEntrySignal(
    rounds: NormalizedRound[],
    analysis?: NormalizedAnalysis
  ): SafeEntrySignal {
    const recentRounds = rounds.slice(-10);
    const avgMultiplier = recentRounds.reduce((sum, r) => sum + r.multiplier, 0) / recentRounds.length;
    const volatility = this.calculateVolatility(recentRounds);

    // Determine if safe entry
    let isSafe = true;
    let entryType: 'low_risk' | 'medium_risk' | 'high_risk' = 'medium_risk';
    
    if (volatility < 0.3 && avgMultiplier < 2.0) {
      entryType = 'low_risk';
    } else if (volatility > 0.6 || avgMultiplier > 4.0) {
      entryType = 'high_risk';
      isSafe = false;
    }

    // Calculate confidence
    let confidence = 0.7;
    if (entryType === 'low_risk') confidence = 0.9;
    if (entryType === 'high_risk') confidence = 0.5;

    // Calculate optimal multiplier
    const optimalMultiplier = this.calculateOptimalMultiplier(recentRounds, analysis);

    // Calculate risk/reward ratio
    const riskRewardRatio = this.calculateRiskRewardRatio(optimalMultiplier, recentRounds);

    // Generate supporting and warning factors
    const supportingFactors = this.generateSupportingFactors(recentRounds, analysis);
    const warningFactors = this.generateWarningFactors(recentRounds, analysis);

    // Calculate expiry rounds
    const expiryRounds = this.calculateEntryExpiryRounds(volatility, confidence);

    return {
      is_safe: isSafe && confidence >= this.config.safe_entry_confidence,
      confidence,
      entry_type: entryType,
      optimal_multiplier: optimalMultiplier,
      risk_reward_ratio: riskRewardRatio,
      supporting_factors: supportingFactors,
      warning_factors: warningFactors,
      expiry_rounds: expiryRounds,
    };
  }

  /**
   * Check overdue moonshot
   */
  private checkOverdueMoonshot(
    rounds: NormalizedRound[],
    analysis?: NormalizedAnalysis
  ): OverdueMoonshotSignal {
    const moonshots = rounds.filter(r => r.multiplier >= this.config.moonshot_threshold);
    
    if (moonshots.length === 0) {
      return this.createDefaultOverdueMoonshot();
    }

    const lastMoonshot = moonshots[moonshots.length - 1];
    const roundsSinceLast = rounds.length - rounds.indexOf(lastMoonshot);
    
    // Calculate expected gap (historical average)
    const gaps: number[] = [];
    for (let i = 1; i < moonshots.length; i++) {
      const gap = rounds.indexOf(moonshots[i]) - rounds.indexOf(moonshots[i - 1]);
      gaps.push(gap);
    }
    const expectedGap = gaps.length > 0 ? gaps.reduce((a, b) => a + b, 0) / gaps.length : 50;

    // Calculate overdue ratio
    const overdueRatio = roundsSinceLast / expectedGap;
    const isOverdue = overdueRatio > this.config.overdue_threshold;

    // Expected multiplier based on overdue
    const expectedMultiplier = this.config.moonshot_threshold * (1 + (overdueRatio - 1) * 0.5);

    // Calculate confidence
    const confidence = Math.min(1, overdueRatio / 2);

    // Determine urgency
    const urgency = this.determineUrgency(overdueRatio);

    // Generate recommendation
    const recommendation = this.generateMoonshotRecommendation(isOverdue, urgency, expectedMultiplier);

    return {
      is_overdue: isOverdue,
      overdue_ratio: overdueRatio,
      expected_multiplier: expectedMultiplier,
      confidence,
      rounds_since_last: roundsSinceLast,
      expected_gap: expectedGap,
      urgency,
      recommendation,
    };
  }

  /**
   * Analyze band exhaustion
   */
  private analyzeBandExhaustion(
    rounds: NormalizedRound[],
    analysis?: NormalizedAnalysis
  ): BandExhaustionSignal[] {
    const bands = ['1x', '2x', '5x', '10x'];
    const signals: BandExhaustionSignal[] = [];

    for (const band of bands) {
      const bandRounds = rounds.filter(r => this.getBandFromMultiplier(r.multiplier) === band);
      
      if (bandRounds.length < 5) continue;

      const recentInBand = bandRounds.slice(-10);
      const exhaustionLevel = this.calculateExhaustionLevel(recentInBand, band);
      
      if (exhaustionLevel < this.config.exhaustion_threshold) continue;

      const roundsSinceExhaustion = this.calculateRoundsSinceExhaustion(rounds, band);
      const expectedReleaseRounds = this.estimateReleaseRounds(exhaustionLevel);
      const releaseDirection = this.predictReleaseDirection(recentInBand, analysis);
      const confidence = Math.min(1, exhaustionLevel + 0.2);

      signals.push({
        band,
        is_exhausted: true,
        exhaustion_level: exhaustionLevel,
        rounds_since_exhaustion: roundsSinceExhaustion,
        expected_release_rounds: expectedReleaseRounds,
        release_direction: releaseDirection,
        confidence,
      });
    }

    return signals;
  }

  /**
   * Analyze pressure release
   */
  private analyzePressureRelease(
    rounds: NormalizedRound[],
    analysis?: NormalizedAnalysis
  ): PressureReleaseSignal {
    const recentRounds = rounds.slice(-20);
    
    // Calculate pressure metrics
    const volatility = this.calculateVolatility(recentRounds);
    const trend = this.calculateTrend(recentRounds);
    const momentum = this.calculateMomentum(recentRounds);

    // Determine pressure type
    let pressureType: 'accumulation' | 'distribution' | 'volatility' = 'volatility';
    if (trend > 0.1 && momentum > 0.5) {
      pressureType = 'accumulation';
    } else if (trend < -0.1 && momentum < -0.5) {
      pressureType = 'distribution';
    }

    // Calculate current pressure
    const currentPressure = Math.min(1, (volatility + Math.abs(trend) + Math.abs(momentum)) / 3);

    // Check if overdue
    const isOverdue = currentPressure > this.config.pressure_threshold;

    // Expected release rounds
    const expectedReleaseRounds = this.estimatePressureReleaseRounds(currentPressure);

    // Release magnitude
    const releaseMagnitude = currentPressure * 15; // Estimated multiplier release

    // Confidence
    const confidence = Math.min(1, currentPressure + 0.2);

    // Generate recommendation
    const recommendation = this.generatePressureRecommendation(
      pressureType,
      isOverdue,
      releaseMagnitude
    );

    return {
      pressure_type: pressureType,
      current_pressure: currentPressure,
      is_overdue: isOverdue,
      expected_release_rounds: expectedReleaseRounds,
      release_magnitude: releaseMagnitude,
      confidence,
      recommendation,
    };
  }

  /**
   * Helper methods
   */
  private createDefaultStreakInsight(): StreakInsight {
    return {
      streak_type: 'neutral',
      current_streak: 0,
      longest_streak: 0,
      avg_streak_length: 0,
      confidence: 0,
      recommendation: 'Insufficient data for streak analysis',
      expected_reversal_rounds: 0,
    };
  }

  private createDefaultOverdueMoonshot(): OverdueMoonshotSignal {
    return {
      is_overdue: false,
      overdue_ratio: 0,
      expected_multiplier: this.config.moonshot_threshold,
      confidence: 0,
      rounds_since_last: 0,
      expected_gap: 50,
      urgency: 'low',
      recommendation: 'No moonshot history available',
    };
  }

  private calculateLongestStreak(rounds: NormalizedRound[], baseline: number): number {
    let longestStreak = 0;
    let currentStreak = 0;
    let currentType: 'winning' | 'losing' | null = null;

    for (const round of rounds) {
      const isWinning = round.multiplier >= baseline;
      
      if (currentType === null) {
        currentType = isWinning ? 'winning' : 'losing';
        currentStreak = 1;
      } else if ((currentType === 'winning' && isWinning) || (currentType === 'losing' && !isWinning)) {
        currentStreak++;
      } else {
        longestStreak = Math.max(longestStreak, currentStreak);
        currentType = isWinning ? 'winning' : 'losing';
        currentStreak = 1;
      }
    }

    return Math.max(longestStreak, currentStreak);
  }

  private calculateAvgStreakLength(rounds: NormalizedRound[], baseline: number): number {
    const streaks: number[] = [];
    let currentStreak = 0;
    let currentType: 'winning' | 'losing' | null = null;

    for (const round of rounds) {
      const isWinning = round.multiplier >= baseline;
      
      if (currentType === null) {
        currentType = isWinning ? 'winning' : 'losing';
        currentStreak = 1;
      } else if ((currentType === 'winning' && isWinning) || (currentType === 'losing' && !isWinning)) {
        currentStreak++;
      } else {
        streaks.push(currentStreak);
        currentType = isWinning ? 'winning' : 'losing';
        currentStreak = 1;
      }
    }

    if (currentStreak > 0) streaks.push(currentStreak);

    return streaks.length > 0 ? streaks.reduce((a, b) => a + b, 0) / streaks.length : 0;
  }

  private generateStreakRecommendation(
    streakType: 'winning' | 'losing' | 'neutral',
    currentStreak: number,
    longestStreak: number
  ): string {
    if (streakType === 'neutral') {
      return 'No active streak. Monitor for pattern formation.';
    }

    if (streakType === 'winning') {
      if (currentStreak >= longestStreak * 0.8) {
        return 'WARNING: Winning streak near historical maximum. Expect reversal soon.';
      }
      return `Winning streak active (${currentStreak}). Consider reducing position size.`;
    }

    if (streakType === 'losing') {
      if (currentStreak >= longestStreak * 0.8) {
        return 'OPPORTUNITY: Losing streak near maximum. Recovery may be imminent.';
      }
      return `Losing streak active (${currentStreak}). Consider recovery strategy activation.`;
    }

    return 'Monitor streak patterns for trading opportunities.';
  }

  private estimateReversalRounds(currentStreak: number, avgStreakLength: number): number {
    return Math.max(1, Math.floor(avgStreakLength - currentStreak));
  }

  private calculateVolatility(rounds: NormalizedRound[]): number {
    const multipliers = rounds.map(r => r.multiplier);
    const mean = multipliers.reduce((a, b) => a + b, 0) / multipliers.length;
    const variance = multipliers.reduce((sum, m) => sum + Math.pow(m - mean, 2), 0) / multipliers.length;
    return Math.sqrt(variance) / mean;
  }

  private calculateOptimalMultiplier(rounds: NormalizedRound[], analysis?: NormalizedAnalysis): number {
    const percentiles = this.calculatePercentiles(rounds.map(r => r.multiplier));
    return percentiles.p75 || 2.0;
  }

  private calculateRiskRewardRatio(optimalMultiplier: number, rounds: NormalizedRound[]): number {
    const avgLoss = rounds.filter(r => r.multiplier < 1.5).reduce((sum, r) => sum + r.multiplier, 0) / 
                   rounds.filter(r => r.multiplier < 1.5).length || 1;
    return optimalMultiplier / avgLoss;
  }

  private generateSupportingFactors(rounds: NormalizedRound[], analysis?: NormalizedAnalysis[]): string[] {
    const factors: string[] = [];
    const volatility = this.calculateVolatility(rounds);
    
    if (volatility < 0.3) factors.push('Low volatility environment');
    if (analysis?.marketState === 'Normal') factors.push('Normal market state');
    if (analysis?.confidence > 0.7) factors.push('High analysis confidence');
    
    return factors;
  }

  private generateWarningFactors(rounds: NormalizedRound[], analysis?: NormalizedAnalysis[]): string[] {
    const factors: string[] = [];
    const volatility = this.calculateVolatility(rounds);
    
    if (volatility > 0.6) factors.push('High volatility detected');
    if (analysis?.marketState === 'Collapse') factors.push('Market collapse state');
    if (analysis?.warnings && analysis.warnings.length > 0) factors.push('System warnings active');
    
    return factors;
  }

  private calculateEntryExpiryRounds(volatility: number, confidence: number): number {
    return Math.max(3, Math.floor(10 / (confidence * (1 + volatility))));
  }

  private determineUrgency(overdueRatio: number): 'low' | 'medium' | 'high' | 'critical' {
    if (overdueRatio > 3.0) return 'critical';
    if (overdueRatio > 2.0) return 'high';
    if (overdueRatio > 1.5) return 'medium';
    return 'low';
  }

  private generateMoonshotRecommendation(
    isOverdue: boolean,
    urgency: 'low' | 'medium' | 'high' | 'critical',
    expectedMultiplier: number
  ): string {
    if (!isOverdue) {
      return 'Moonshot not overdue. Normal monitoring.';
    }

    if (urgency === 'critical') {
      return `CRITICAL: Mega moonshot imminent (${expectedMultiplier.toFixed(1)}x). Prepare for entry.`;
    }

    if (urgency === 'high') {
      return `HIGH: Moonshot overdue (${expectedMultiplier.toFixed(1)}x). Increase position size gradually.`;
    }

    return `Moderate moonshot signal (${expectedMultiplier.toFixed(1)}x). Monitor for confirmation.`;
  }

  private getBandFromMultiplier(multiplier: number): string {
    if (multiplier < 1.5) return '1x';
    if (multiplier < 3) return '2x';
    if (multiplier < 7) return '5x';
    return '10x';
  }

  private calculateExhaustionLevel(rounds: NormalizedRound[], band: string): number {
    // Simple exhaustion calculation based on frequency
    const totalRounds = 100; // Assume total rounds window
    const bandCount = rounds.length;
    const expectedFrequency = this.getExpectedFrequency(band);
    const actualFrequency = bandCount / totalRounds;
    return Math.max(0, 1 - (actualFrequency / expectedFrequency));
  }

  private getExpectedFrequency(band: string): number {
    const frequencies: Record<string, number> = {
      '1x': 0.5,
      '2x': 0.3,
      '5x': 0.15,
      '10x': 0.05,
    };
    return frequencies[band] || 0.1;
  }

  private calculateRoundsSinceExhaustion(rounds: NormalizedRound[], band: string): number {
    const bandRounds = rounds.filter(r => this.getBandFromMultiplier(r.multiplier) === band);
    if (bandRounds.length === 0) return rounds.length;
    return rounds.length - rounds.indexOf(bandRounds[bandRounds.length - 1]);
  }

  private estimateReleaseRounds(exhaustionLevel: number): number {
    return Math.max(1, Math.floor((1 - exhaustionLevel) * 20));
  }

  private predictReleaseDirection(rounds: NormalizedRound[], analysis?: NormalizedAnalysis): 'up' | 'down' | 'neutral' {
    const trend = this.calculateTrend(rounds);
    if (trend > 0.05) return 'up';
    if (trend < -0.05) return 'down';
    return 'neutral';
  }

  private calculateTrend(rounds: NormalizedRound[]): number {
    if (rounds.length < 2) return 0;
    const first = rounds[0].multiplier;
    const last = rounds[rounds.length - 1].multiplier;
    return (last - first) / first;
  }

  private calculateMomentum(rounds: NormalizedRound[]): number {
    if (rounds.length < 5) return 0;
    const recent = rounds.slice(-5);
    const first = recent[0].multiplier;
    const last = recent[recent.length - 1].multiplier;
    return (last - first) / first;
  }

  private estimatePressureReleaseRounds(pressure: number): number {
    return Math.max(1, Math.floor((1 - pressure) * 15));
  }

  private generatePressureRecommendation(
    pressureType: 'accumulation' | 'distribution' | 'volatility',
    isOverdue: boolean,
    releaseMagnitude: number
  ): string {
    if (!isOverdue) {
      return `Pressure building (${pressureType}). Monitor for release.`;
    }

    return `PRESSURE RELEASE: ${pressureType} type releasing. Expected ${releaseMagnitude.toFixed(1)}x move.`;
  }

  private generateOverallRecommendation(
    streakInsight: StreakInsight,
    safeEntrySignal: SafeEntrySignal,
    overdueMoonshot: OverdueMoonshotSignal,
    bandExhaustion: BandExhaustionSignal[],
    pressureRelease: PressureReleaseSignal
  ): string {
    const signals: string[] = [];

    if (overdueMoonshot.is_overdue && overdueMoonshot.urgency === 'critical') {
      return "CRITICAL: Mega moonshot imminent. Maximum position size recommended.";
    }

    if (safeEntrySignal.is_safe) {
      signals.push("Safe entry available");
    }

    if (streakInsight.streak_type === 'losing' && streakInsight.current_streak > 5) {
      signals.push("Recovery opportunity");
    }

    if (bandExhaustion.length > 0) {
      signals.push("Band exhaustion signals");
    }

    if (pressureRelease.is_overdue) {
      signals.push("Pressure release imminent");
    }

    if (signals.length === 0) {
      return "No strong signals. Maintain conservative approach.";
    }

    return signals.join('. ') + '. Monitor closely.';
  }

  private calculateOverallConfidence(
    streakInsight: StreakInsight,
    safeEntrySignal: SafeEntrySignal,
    overdueMoonshot: OverdueMoonshotSignal,
    bandExhaustion: BandExhaustionSignal[],
    pressureRelease: PressureReleaseSignal
  ): number {
    const confidences = [
      streakInsight.confidence,
      safeEntrySignal.confidence,
      overdueMoonshot.confidence,
      pressureRelease.confidence,
      ...bandExhaustion.map(b => b.confidence),
    ];

    return confidences.reduce((a, b) => a + b, 0) / confidences.length;
  }

  private determineRiskLevel(
    streakInsight: StreakInsight,
    safeEntrySignal: SafeEntrySignal,
    overdueMoonshot: OverdueMoonshotSignal,
    pressureRelease: PressureReleaseSignal
  ): 'low' | 'medium' | 'high' | 'critical' {
    if (overdueMoonshot.urgency === 'critical') return 'critical';
    if (overdueMoonshot.urgency === 'high') return 'high';
    if (!safeEntrySignal.is_safe) return 'high';
    if (pressureRelease.current_pressure > 0.8) return 'high';
    if (streakInsight.streak_type === 'losing' && streakInsight.current_streak > 5) return 'medium';
    return 'low';
  }

  private generateActionableSignals(
    streakInsight: StreakInsight,
    safeEntrySignal: SafeEntrySignal,
    overdueMoonshot: OverdueMoonshotSignal,
    bandExhaustion: BandExhaustionSignal[],
    pressureRelease: PressureReleaseSignal
  ): string[] {
    const signals: string[] = [];

    if (safeEntrySignal.is_safe) {
      signals.push(`Enter at ${safeEntrySignal.optimal_multiplier.toFixed(2)}x (Safe Entry)`);
    }

    if (overdueMoonshot.is_overdue) {
      signals.push(`Prepare for moonshot (${overdueMoonshot.expected_multiplier.toFixed(1)}x)`);
    }

    if (streakInsight.streak_type === 'losing' && streakInsight.current_streak > 3) {
      signals.push('Activate recovery strategy');
    }

    if (bandExhaustion.length > 0) {
      signals.push(`Watch ${bandExhaustion.map(b => b.band).join(', ')} band release`);
    }

    if (pressureRelease.is_overdue) {
      signals.push('Prepare for pressure release entry');
    }

    return signals;
  }

  private calculatePercentiles(values: number[]): { p25?: number; p50?: number; p75?: number } {
    const sorted = [...values].sort((a, b) => a - b);
    const p25 = sorted[Math.floor(sorted.length * 0.25)];
    const p50 = sorted[Math.floor(sorted.length * 0.5)];
    const p75 = sorted[Math.floor(sorted.length * 0.75)];
    return { p25, p50, p75 };
  }
}

// Export singleton instance
export const strategyInsightsEngine = new StrategyInsightsEngine();