/**
 * Pattern DNA Tracker - First Invention
 * 
 * A sophisticated pattern recognition and DNA analysis tool that:
 * - Detects hidden patterns in crash sequences
 * - Analyzes "DNA" of round sequences (magnitude, timing, streaks)
 * - Provides real-time anomaly detection
 * - Generates confidence-based predictions
 * - Visualizes pattern evolution over time
 * 
 * This invention operates entirely through the middleware layer,
 * reading from the main system API without modifying it.
 */

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PatternCard } from '@/components/patterns/PatternCard';
import { 
  Activity, 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  Zap, 
  Target,
  RefreshCw,
  Clock,
  BarChart3
} from 'lucide-react';

import {
  useInventionRounds,
  useInventionAnalysis,
  usePatternDetection,
  useAnomalyDetection,
  usePrediction,
  rubberbandAnalyzer,
  anomalyDetector,
  strategyInsightsEngine,
  type NormalizedRound,
  type PatternMatch,
  type AnomalyDetection,
  type PredictionResult,
  type RubberbandAnalysis,
  type AnomalyReport,
  type StrategyInsights
} from '@/lib/invent-middleware';

const PatternDnaTracker: React.FC = () => {
  const [source, setSource] = useState('aviator');
  const [activeTab, setActiveTab] = useState('patterns');

  // Fetch data through middleware
  const roundsQuery = useInventionRounds(source);
  const analysisQuery = useInventionAnalysis(source);
  const patternsQuery = usePatternDetection(source, roundsQuery.data || []);
  const anomaliesQuery = useAnomalyDetection(source, roundsQuery.data || []);
  const predictionQuery = usePrediction(source, roundsQuery.data || [], analysisQuery.data);

  const rounds = roundsQuery.data || [];
  const patterns = patternsQuery.data || [];
  const anomalies = anomaliesQuery.data || [];
  const prediction = predictionQuery.data;

  // New analysis engines
  const rubberbandAnalysis: RubberbandAnalysis = rounds.length > 0 ? 
    rubberbandAnalyzer.analyze(rounds, analysisQuery.data) : 
    {
      tension: { current_tension: 0, tension_trend: 'stable', elastic_potential: 0, resistance_points: 0, snap_probability: 0 },
      snap_prediction: null,
      lower_tier_influence: { has_lower_tier: false, influence_factor: 0, moonshot_probability: 0 },
      historical_snaps: { count: 0, avg_multiplier: 0, avg_tension_at_snap: 0 },
      recommendation: 'Insufficient data for rubberband analysis'
    };

  const anomalyReport: AnomalyReport = rounds.length > 0 ? 
    anomalyDetector.analyzePredictions(
      rounds.map(r => ({ predicted: r.multiplier, confidence: 0.8 })),
      rounds.map(r => r.multiplier)
    ) : 
    {
      recent_anomalies: [],
      anomaly_patterns: [],
      prediction_accuracy: { total_predictions: 0, accurate_predictions: 0, false_lows: 0, false_highs: 0, accuracy_rate: 0, avg_error: 0 },
      range_analysis: { avg_range_width: 0, range_volatility: 0, range_drift: 0, is_stable: true },
      chase_distance_analysis: { current_chase_distance: 10, optimal_chase_distance: 8, distance_efficiency: 0.8, recommended_adjustment: -2 },
      recommendations: ['Insufficient data for anomaly analysis'],
      alert_level: 'normal'
    };

  const strategyInsights: StrategyInsights = rounds.length > 0 ? 
    strategyInsightsEngine.generateInsights(rounds, analysisQuery.data) : 
    {
      streak_insight: { streak_type: 'neutral', current_streak: 0, longest_streak: 0, avg_streak_length: 0, confidence: 0, recommendation: 'Insufficient data', expected_reversal_rounds: 0 },
      safe_entry_signal: { is_safe: false, confidence: 0, entry_type: 'medium_risk', optimal_multiplier: 1.5, risk_reward_ratio: 1, supporting_factors: [], warning_factors: [], expiry_rounds: 0 },
      overdue_moonshot: { is_overdue: false, overdue_ratio: 0, expected_multiplier: 10, confidence: 0, rounds_since_last: 0, expected_gap: 50, urgency: 'low', recommendation: 'No data' },
      band_exhaustion: [],
      pressure_release: { pressure_type: 'volatility', current_pressure: 0, is_overdue: false, expected_release_rounds: 0, release_magnitude: 0, confidence: 0, recommendation: 'No data' },
      overall_recommendation: 'Insufficient data for strategy insights',
      confidence: 0,
      risk_level: 'low',
      actionable_signals: []
    };

  const isLoading = roundsQuery.isLoading || analysisQuery.isLoading;

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-500';
      case 'medium': return 'bg-yellow-500';
      case 'low': return 'bg-blue-500';
      default: return 'bg-gray-500';
    }
  };

  const getMagnitudeColor = (magnitude: string) => {
    switch (magnitude) {
      case 'extreme': return 'bg-purple-500';
      case 'high': return 'bg-green-500';
      case 'medium': return 'bg-blue-500';
      case 'low': return 'bg-orange-500';
      default: return 'bg-gray-500';
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-500';
    if (confidence >= 0.6) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Activity className="w-8 h-8 text-purple-500" />
            Pattern DNA Tracker
          </h1>
          <p className="text-gray-400 mt-1">
            Advanced pattern recognition and sequence analysis
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => roundsQuery.refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Badge variant="outline" className="text-purple-400 border-purple-500">
            {source}
          </Badge>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400">Total Rounds</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{rounds.length}</div>
            <p className="text-xs text-gray-500 mt-1">Analyzed sequences</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400">Patterns Found</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-400">{patterns.length}</div>
            <p className="text-xs text-gray-500 mt-1">Active patterns</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400">Anomalies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-400">{anomalies.length}</div>
            <p className="text-xs text-gray-500 mt-1">Detected anomalies</p>
          </CardContent>
        </Card>

        <Card className="bg-gray-900 border-gray-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-400">Prediction</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getConfidenceColor(prediction?.confidence || 0)}`}>
              {prediction ? `${prediction.predictedRange?.min?.toFixed(2) ?? '0.00'}-${prediction.predictedRange?.max?.toFixed(2) ?? '0.00'}x` : 'N/A'}
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {prediction ? `${((prediction.confidence || 0) * 100).toFixed(0)}% confidence` : 'No data'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-gray-900 border-gray-800">
          <TabsTrigger value="patterns" className="data-[state=active]:bg-purple-600">
            <BarChart3 className="w-4 h-4 mr-2" />
            Patterns
          </TabsTrigger>
          <TabsTrigger value="anomalies" className="data-[state=active]:bg-red-600">
            <AlertTriangle className="w-4 h-4 mr-2" />
            Anomalies
          </TabsTrigger>
          <TabsTrigger value="prediction" className="data-[state=active]:bg-green-600">
            <Target className="w-4 h-4 mr-2" />
            Prediction
          </TabsTrigger>
          <TabsTrigger value="dna" className="data-[state=active]:bg-blue-600">
            <Zap className="w-4 h-4 mr-2" />
            DNA Analysis
          </TabsTrigger>
          <TabsTrigger value="rubberband" className="data-[state=active]:bg-orange-600">
            <TrendingUp className="w-4 h-4 mr-2" />
            Rubberband
          </TabsTrigger>
          <TabsTrigger value="strategy" className="data-[state=active]:bg-cyan-600">
            <Activity className="w-4 h-4 mr-2" />
            Strategy
          </TabsTrigger>
        </TabsList>

        {/* Patterns Tab */}
        <TabsContent value="patterns" className="space-y-4">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Detected Patterns</CardTitle>
              <CardDescription>
                Real-time pattern recognition in round sequences
              </CardDescription>
            </CardHeader>
            <CardContent>
              {patterns.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No patterns detected yet</p>
                  <p className="text-sm mt-2">Waiting for more data...</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {patterns.map((pattern, index) => (
                    <PatternCard
                      key={index}
                      pattern={{
                        id: index.toString(),
                        name: pattern.pattern,
                        pattern_type: pattern.pattern,
                        description: pattern.description,
                        confidence: pattern.confidence || 0,
                        probability: pattern.occurrences ? pattern.occurrences / 100 : undefined,
                      }}
                      size="sm"
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Anomalies Tab */}
        <TabsContent value="anomalies" className="space-y-4">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Anomaly Detection</CardTitle>
              <CardDescription>
                Statistical outliers and unusual behavior
              </CardDescription>
            </CardHeader>
            <CardContent>
              {anomalies.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No anomalies detected</p>
                  <p className="text-sm mt-2">System operating normally</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {anomalies.slice(0, 10).map((anomaly, index) => (
                    <PatternCard
                      key={index}
                      pattern={{
                        id: index.toString(),
                        name: anomaly.reason,
                        description: anomaly.reason,
                        confidence: anomaly.severity === 'high' ? 0.9 : anomaly.severity === 'medium' ? 0.6 : 0.3,
                        crashPoint: anomaly.crashPoint,
                        severity: anomaly.severity,
                        timestamp: anomaly.timestamp?.toISOString(),
                      }}
                      size="sm"
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Prediction Tab */}
        <TabsContent value="prediction" className="space-y-4">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>AI Prediction</CardTitle>
              <CardDescription>
                Confidence-based prediction using pattern analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!prediction ? (
                <div className="text-center py-8 text-gray-500">
                  <Target className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Insufficient data for prediction</p>
                  <p className="text-sm mt-2">Collecting more rounds...</p>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="text-center py-6">
                    <div className="text-5xl font-bold mb-2">
                      {prediction.predictedRange?.min?.toFixed(2) ?? '0.00'}x - {prediction.predictedRange?.max?.toFixed(2) ?? '0.00'}x
                    </div>
                    <div className={`text-xl font-medium ${getConfidenceColor(prediction.confidence || 0)}`}>
                      {((prediction.confidence || 0) * 100).toFixed(0)}% confidence
                    </div>
                  </div>

                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-400">Influencing Factors</h4>
                    {(prediction.factors || []).map((factor, index) => (
                      <div key={index} className="flex items-center gap-2 text-sm">
                        <TrendingUp className="w-4 h-4 text-green-400" />
                        <span>{factor}</span>
                      </div>
                    ))}
                  </div>

                  <div className="pt-4 border-t border-gray-700">
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Clock className="w-4 h-4" />
                      <span>Last updated: {new Date(prediction.timestamp).toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* DNA Analysis Tab */}
        <TabsContent value="dna" className="space-y-4">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Round DNA Analysis</CardTitle>
              <CardDescription>
                Magnitude distribution and sequence characteristics
              </CardDescription>
            </CardHeader>
            <CardContent>
              {rounds.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Zap className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No data available</p>
                  <p className="text-sm mt-2">Waiting for rounds...</p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Magnitude Distribution */}
                  <div>
                    <h4 className="font-medium mb-3">Magnitude Distribution</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {(['low', 'medium', 'high', 'extreme'] as const).map((mag) => {
                        const count = rounds.filter(r => r.magnitude === mag).length;
                        const percentage = (count / rounds.length) * 100;
                        return (
                          <div key={mag} className="p-3 bg-gray-800 rounded-lg border border-gray-700">
                            <div className="flex items-center gap-2 mb-2">
                              <div className={`w-3 h-3 rounded-full ${getMagnitudeColor(mag)}`} />
                              <span className="text-sm capitalize">{mag}</span>
                            </div>
                            <div className="text-xl font-bold">{count}</div>
                            <div className="text-xs text-gray-500">{percentage?.toFixed(1) ?? '0.0'}%</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Recent Rounds */}
                  <div>
                    <h4 className="font-medium mb-3">Recent Round DNA</h4>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {rounds.slice(0, 20).map((round, index) => (
                        <div
                          key={round.id}
                          className="flex items-center justify-between p-2 bg-gray-800 rounded border border-gray-700 text-sm"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500 w-6">{index + 1}</span>
                            <div className={`w-2 h-2 rounded-full ${getMagnitudeColor(round.magnitude)}`} />
                            <span className="font-medium">{round.crashPoint?.toFixed(2) ?? round.multiplier?.toFixed(2) ?? '0.00'}x</span>
                          </div>
                          <div className="flex items-center gap-3 text-gray-500">
                            <span className="capitalize">{round.magnitude}</span>
                            <span>{new Date(round.timestamp).toLocaleTimeString()}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Rubberband Analysis Tab */}
        <TabsContent value="rubberband" className="space-y-4">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Rubberband Analysis</CardTitle>
              <CardDescription>
                Elastic tension analysis for moonshot predictions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Tension Metrics */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <div className="text-sm text-gray-400 mb-1">Current Tension</div>
                    <div className="text-2xl font-bold text-orange-400">
                      {(rubberbandAnalysis.tension.current_tension * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <div className="text-sm text-gray-400 mb-1">Trend</div>
                    <div className="text-2xl font-bold capitalize">
                      {rubberbandAnalysis.tension.tension_trend}
                    </div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <div className="text-sm text-gray-400 mb-1">Snap Probability</div>
                    <div className="text-2xl font-bold text-purple-400">
                      {(rubberbandAnalysis.tension.snap_probability * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <div className="text-sm text-gray-400 mb-1">Resistance Points</div>
                    <div className="text-2xl font-bold">
                      {rubberbandAnalysis.tension.resistance_points}
                    </div>
                  </div>
                </div>

                {/* Snap Prediction */}
                {rubberbandAnalysis.snap_prediction ? (
                  <div className="p-4 bg-gradient-to-r from-orange-900/50 to-purple-900/50 rounded-lg border border-orange-500/30">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp className="w-5 h-5 text-orange-400" />
                      <h4 className="font-semibold text-orange-400">Snap Prediction</h4>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-gray-400">Predicted Multiplier</div>
                        <div className="text-xl font-bold">{rubberbandAnalysis.snap_prediction.predicted_multiplier.toFixed(1)}x</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Confidence</div>
                        <div className="text-xl font-bold">{(rubberbandAnalysis.snap_prediction.confidence * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Est. Rounds</div>
                        <div className="text-xl font-bold">{rubberbandAnalysis.snap_prediction.estimated_rounds}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Type</div>
                        <div className="text-xl font-bold capitalize">{rubberbandAnalysis.snap_prediction.snap_type.replace('_', ' ')}</div>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-700">
                      <div className="text-sm text-gray-400 mb-2">Contributing Factors:</div>
                      <div className="flex flex-wrap gap-2">
                        {rubberbandAnalysis.snap_prediction.contributing_factors.map((factor, i) => (
                          <Badge key={i} variant="outline" className="text-orange-300 border-orange-500/50">
                            {factor}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-4 bg-gray-800 rounded-lg border border-gray-700 text-center text-gray-500">
                    No snap prediction - tension below threshold
                  </div>
                )}

                {/* Lower Tier Influence */}
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <h4 className="font-medium mb-3">Lower Tier Moonshot Influence</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-gray-400">Has Lower Tier</div>
                      <div className={`text-lg font-bold ${rubberbandAnalysis.lower_tier_influence.has_lower_tier ? 'text-green-400' : 'text-gray-500'}`}>
                        {rubberbandAnalysis.lower_tier_influence.has_lower_tier ? 'Yes' : 'No'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400">Influence Factor</div>
                      <div className="text-lg font-bold">{(rubberbandAnalysis.lower_tier_influence.influence_factor * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400">Moonshot Probability</div>
                      <div className="text-lg font-bold text-purple-400">{(rubberbandAnalysis.lower_tier_influence.moonshot_probability * 100).toFixed(0)}%</div>
                    </div>
                  </div>
                </div>

                {/* Recommendation */}
                <div className="p-4 bg-blue-900/20 rounded-lg border border-blue-500/30">
                  <div className="flex items-center gap-2 mb-2">
                    <Activity className="w-5 h-5 text-blue-400" />
                    <h4 className="font-semibold text-blue-400">Recommendation</h4>
                  </div>
                  <p className="text-gray-300">{rubberbandAnalysis.recommendation}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Strategy Insights Tab */}
        <TabsContent value="strategy" className="space-y-4">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Strategy Insights</CardTitle>
              <CardDescription>
                Actionable trading signals and recommendations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                {/* Overall Recommendation */}
                <div className={`p-4 rounded-lg border ${
                  strategyInsights.risk_level === 'critical' ? 'bg-red-900/30 border-red-500/50' :
                  strategyInsights.risk_level === 'high' ? 'bg-orange-900/30 border-orange-500/50' :
                  strategyInsights.risk_level === 'medium' ? 'bg-yellow-900/30 border-yellow-500/50' :
                  'bg-green-900/30 border-green-500/50'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Activity className="w-5 h-5" />
                      <h4 className="font-semibold">Overall Assessment</h4>
                    </div>
                    <Badge variant="outline" className={
                      strategyInsights.risk_level === 'critical' ? 'text-red-400 border-red-500' :
                      strategyInsights.risk_level === 'high' ? 'text-orange-400 border-orange-500' :
                      strategyInsights.risk_level === 'medium' ? 'text-yellow-400 border-yellow-500' :
                      'text-green-400 border-green-500'
                    }>
                      {strategyInsights.risk_level.toUpperCase()} RISK
                    </Badge>
                  </div>
                  <p className="text-gray-300 mb-2">{strategyInsights.overall_recommendation}</p>
                  <div className="text-sm text-gray-400">Confidence: {(strategyInsights.confidence * 100).toFixed(0)}%</div>
                </div>

                {/* Actionable Signals */}
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <h4 className="font-medium mb-3">Actionable Signals</h4>
                  <div className="space-y-2">
                    {strategyInsights.actionable_signals.length > 0 ? (
                      strategyInsights.actionable_signals.map((signal, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          <Target className="w-4 h-4 text-green-400" />
                          <span>{signal}</span>
                        </div>
                      ))
                    ) : (
                      <div className="text-gray-500 text-sm">No actionable signals at this time</div>
                    )}
                  </div>
                </div>

                {/* Streak Analysis */}
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <h4 className="font-medium mb-3">Streak Analysis</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-gray-400">Current Streak</div>
                      <div className={`text-xl font-bold capitalize ${
                        strategyInsights.streak_insight.streak_type === 'winning' ? 'text-green-400' :
                        strategyInsights.streak_insight.streak_type === 'losing' ? 'text-red-400' :
                        'text-gray-400'
                      }`}>
                        {strategyInsights.streak_insight.streak_type} ({strategyInsights.streak_insight.current_streak})
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400">Longest Streak</div>
                      <div className="text-xl font-bold">{strategyInsights.streak_insight.longest_streak}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400">Avg Streak Length</div>
                      <div className="text-xl font-bold">{strategyInsights.streak_insight.avg_streak_length.toFixed(1)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400">Est. Reversal</div>
                      <div className="text-xl font-bold">{strategyInsights.streak_insight.expected_reversal_rounds} rounds</div>
                    </div>
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-700">
                    <p className="text-sm text-gray-400">{strategyInsights.streak_insight.recommendation}</p>
                  </div>
                </div>

                {/* Safe Entry Signal */}
                <div className={`p-4 rounded-lg border ${
                  strategyInsights.safe_entry_signal.is_safe ? 'bg-green-900/20 border-green-500/30' : 'bg-red-900/20 border-red-500/30'
                }`}>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium">Safe Entry Signal</h4>
                    <Badge variant="outline" className={
                      strategyInsights.safe_entry_signal.is_safe ? 'text-green-400 border-green-500' : 'text-red-400 border-red-500'
                    }>
                      {strategyInsights.safe_entry_signal.is_safe ? 'SAFE' : 'UNSAFE'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-gray-400">Entry Type</div>
                      <div className="text-lg font-bold capitalize">{strategyInsights.safe_entry_signal.entry_type.replace('_', ' ')}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400">Optimal Multiplier</div>
                      <div className="text-lg font-bold">{strategyInsights.safe_entry_signal.optimal_multiplier.toFixed(2)}x</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400">Risk/Reward</div>
                      <div className="text-lg font-bold">{strategyInsights.safe_entry_signal.risk_reward_ratio.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-400">Expiry</div>
                      <div className="text-lg font-bold">{strategyInsights.safe_entry_signal.expiry_rounds} rounds</div>
                    </div>
                  </div>
                </div>

                {/* Overdue Moonshot */}
                {strategyInsights.overdue_moonshot.is_overdue && (
                  <div className={`p-4 rounded-lg border ${
                    strategyInsights.overdue_moonshot.urgency === 'critical' ? 'bg-red-900/30 border-red-500/50' :
                    strategyInsights.overdue_moonshot.urgency === 'high' ? 'bg-orange-900/30 border-orange-500/50' :
                    'bg-yellow-900/30 border-yellow-500/50'
                  }`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-orange-400" />
                        <h4 className="font-semibold">Overdue Moonshot</h4>
                      </div>
                      <Badge variant="outline" className="text-orange-400 border-orange-500">
                        {strategyInsights.overdue_moonshot.urgency.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-gray-400">Expected Multiplier</div>
                        <div className="text-xl font-bold">{strategyInsights.overdue_moonshot.expected_multiplier.toFixed(1)}x</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Overdue Ratio</div>
                        <div className="text-xl font-bold">{strategyInsights.overdue_moonshot.overdue_ratio.toFixed(1)}x</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Rounds Since Last</div>
                        <div className="text-xl font-bold">{strategyInsights.overdue_moonshot.rounds_since_last}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Confidence</div>
                        <div className="text-xl font-bold">{(strategyInsights.overdue_moonshot.confidence * 100).toFixed(0)}%</div>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-700">
                      <p className="text-sm text-gray-400">{strategyInsights.overdue_moonshot.recommendation}</p>
                    </div>
                  </div>
                )}

                {/* Band Exhaustion */}
                {strategyInsights.band_exhaustion.length > 0 && (
                  <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                    <h4 className="font-medium mb-3">Band Exhaustion Signals</h4>
                    <div className="space-y-3">
                      {strategyInsights.band_exhaustion.map((signal, i) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-gray-700/50 rounded border border-gray-600">
                          <div className="flex items-center gap-3">
                            <Badge variant="outline" className="text-purple-400 border-purple-500">
                              {signal.band}
                            </Badge>
                            <div>
                              <div className="text-sm font-medium">Exhaustion: {(signal.exhaustion_level * 100).toFixed(0)}%</div>
                              <div className="text-xs text-gray-400">Release in {signal.expected_release_rounds} rounds ({signal.release_direction})</div>
                            </div>
                          </div>
                          <div className="text-sm text-gray-400">{(signal.confidence * 100).toFixed(0)}% conf</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Pressure Release */}
                {strategyInsights.pressure_release.is_overdue && (
                  <div className="p-4 bg-purple-900/20 rounded-lg border border-purple-500/30">
                    <div className="flex items-center gap-2 mb-3">
                      <Activity className="w-5 h-5 text-purple-400" />
                      <h4 className="font-semibold">Pressure Release</h4>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <div className="text-sm text-gray-400">Pressure Type</div>
                        <div className="text-lg font-bold capitalize">{strategyInsights.pressure_release.pressure_type}</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Current Pressure</div>
                        <div className="text-lg font-bold">{(strategyInsights.pressure_release.current_pressure * 100).toFixed(0)}%</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Release Magnitude</div>
                        <div className="text-lg font-bold">{strategyInsights.pressure_release.release_magnitude.toFixed(1)}x</div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-400">Est. Rounds</div>
                        <div className="text-lg font-bold">{strategyInsights.pressure_release.expected_release_rounds}</div>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-700">
                      <p className="text-sm text-gray-400">{strategyInsights.pressure_release.recommendation}</p>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default PatternDnaTracker;
