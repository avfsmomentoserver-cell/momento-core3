/**
 * Middleware Framework - Entry point
 * 
 * Exports all middleware components for inventions to use.
 * Provides a clean interface for data ingestion, transformation,
 * analysis, and state management without touching the main system.
 */

export { dataIngester } from './dataIngester';
export type { Round, Analysis, Forecast } from './dataIngester';

export { transformProcessor } from './transformProcessor';
export type { NormalizedRound, NormalizedAnalysis } from './transformProcessor';

export { analysisEngine } from './analysisEngine';
export type { PatternMatch, AnomalyDetection, PredictionResult } from './analysisEngine';

export { rubberbandAnalyzer } from './rubberbandAnalysis';
export type {
  RubberbandTension,
  RubberbandSnap,
  RubberbandAnalysis,
  RubberbandConfig
} from './rubberbandAnalysis';

export { anomalyDetector } from './anomalyDetection';
export type {
  AnomalyThreshold,
  PredictionAnomaly,
  AnomalyPattern,
  AnomalyReport,
  AnomalyDetectionConfig
} from './anomalyDetection';

export { strategyInsightsEngine } from './strategyInsights';
export type {
  StreakInsight,
  SafeEntrySignal,
  OverdueMoonshotSignal,
  BandExhaustionSignal,
  PressureReleaseSignal,
  StrategyInsights,
  StrategyInsightsConfig
} from './strategyInsights';

export {
  useInventionRounds,
  useInventionAnalysis,
  usePatternDetection,
  useAnomalyDetection,
  usePrediction
} from './stateManager';
