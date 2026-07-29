/**
 * MomentoFX2 - Professional Trading Platform UI
 * 
 * MT5/Deriv TradingView style interface with:
 * - Professional dark theme
 * - Advanced charting capabilities
 * - Real-time order book
 * - Multi-timeframe analysis
 * - Professional trading controls
 * - Advanced indicators panel
 * - Risk management tools
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Settings, 
  Bell, 
  Maximize2, 
  LayoutGrid,
  BarChart3,
  Brain,
  DollarSign,
  Clock,
  Zap,
  Shield,
  Target,
  LineChart,
  MoreHorizontal,
  Play,
  Pause,
  RotateCcw
} from 'lucide-react';

// Import existing components
import { AnalyticsCard } from '../shared/AnalyticsCard';
import { KPITile } from '../shared/KPITile';
import { PatternBadge } from '../shared/PatternBadge';
import { PressureGauge } from '../shared/PressureGauge';
import { SurvivalChart } from '../shared/SurvivalChart';

// Import hooks and services
import { useAnalytics, usePressureScore } from '../../hooks/useAnalytics';
import { usePatterns, useSurvivalEstimate } from '../../hooks/useML';
import { notificationService } from '../../services/NotificationService';

// Import types
import type { AnalyticsMetrics, PatternPrediction, SurvivalEstimate, PressureScore } from '../../types';
import type { Timeframe } from '../../types';
import { DEFAULT_TIMEFRAME, AVAILABLE_TIMEFRAMES } from '../../constants';

// Import new analysis engines
import { rubberbandAnalyzer, anomalyDetector, strategyInsightsEngine } from '@/lib/invent-middleware';
import type { RubberbandAnalysis, AnomalyReport, StrategyInsights } from '@/lib/invent-middleware';

// Add type for normalized rounds
interface SimulatedRound {
  id: number;
  multiplier: number;
  timestamp: string;
  magnitude: string;
}

interface OrderBookEntry {
  price: number;
  size: number;
  total: number;
}

interface Position {
  id: string;
  entry: number;
  current: number;
  size: number;
  pnl: number;
  pnlPercent: number;
  type: 'long' | 'short';
}

interface TradeSignal {
  type: 'buy' | 'sell' | 'hold';
  strength: number;
  confidence: number;
  reason: string;
  target: number;
  stopLoss: number;
}

/**
 * MomentoFX2 Professional Trading Dashboard
 */
export function MomentoFX2Dashboard() {
  const [source, setSource] = useState('aviator');
  const [timeframe, setTimeframe] = useState<Timeframe>(DEFAULT_TIMEFRAME);
  const [notifications, setNotifications] = useState(0);
  const [chartType, setChartType] = useState<'candles' | 'line' | 'area'>('candles');
  const [isTrading, setIsTrading] = useState(false);
  const [positionSize, setPositionSize] = useState(10);
  const [leverage, setLeverage] = useState(1);
  const [riskPercent, setRiskPercent] = useState(2);

  // Use custom hooks for data fetching
  const { data: metrics, isLoading: metricsLoading } = useAnalytics(source, timeframe);
  const { data: pressure } = usePressureScore(source);
  const { data: patterns } = usePatterns(source, timeframe);
  const { data: survival } = useSurvivalEstimate(source);

  // New analysis engines
  const [rubberbandAnalysis, setRubberbandAnalysis] = useState<RubberbandAnalysis | null>(null);
  const [anomalyReport, setAnomalyReport] = useState<AnomalyReport | null>(null);
  const [strategyInsights, setStrategyInsights] = useState<StrategyInsights | null>(null);

  // Simulated order book
  const [orderBook, setOrderBook] = useState<{ bids: OrderBookEntry[]; asks: OrderBookEntry[] }>({
    bids: [],
    asks: []
  });

  // Simulated positions
  const [positions, setPositions] = useState<Position[]>([]);

  // Simulated trade signals
  const [tradeSignal, setTradeSignal] = useState<TradeSignal | null>(null);

  // Subscribe to notifications
  useEffect(() => {
    const unsubscribe = notificationService.subscribe(() => {
      setNotifications(notificationService.getUnreadNotifications().length);
    });
    return unsubscribe;
  }, []);

  // Simulate order book updates
  useEffect(() => {
    const interval = setInterval(() => {
      const basePrice = 1.5 + Math.random() * 0.5;
      const bids: OrderBookEntry[] = [];
      const asks: OrderBookEntry[] = [];
      
      for (let i = 0; i < 8; i++) {
        const bidPrice = basePrice - (i * 0.01) - Math.random() * 0.005;
        const askPrice = basePrice + (i * 0.01) + Math.random() * 0.005;
        const size = Math.random() * 1000;
        
        bids.push({ price: bidPrice, size, total: size * bidPrice });
        asks.push({ price: askPrice, size, total: size * askPrice });
      }
      
      setOrderBook({ bids, asks });
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // Simulate trade signals
  useEffect(() => {
    const interval = setInterval(() => {
      if (Math.random() > 0.7) {
        const signal: TradeSignal = {
          type: Math.random() > 0.5 ? 'buy' : 'sell',
          strength: Math.random(),
          confidence: Math.random(),
          reason: 'Technical analysis signal',
          target: 1.5 + Math.random() * 2,
          stopLoss: 1.0 + Math.random() * 0.3
        };
        setTradeSignal(signal);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Run new analysis engines
  useEffect(() => {
    // This would normally use real data from the API
    // For now, we'll simulate the analysis
    const simulatedRounds: SimulatedRound[] = Array.from({ length: 50 }, (_, i) => ({
      id: i,
      multiplier: 1 + Math.random() * 10,
      timestamp: new Date(Date.now() - i * 60000).toISOString(),
      magnitude: Math.random() > 0.7 ? 'high' : 'low'
    }));

    try {
      // Cast to satisfy the analyzer's expected type
      const roundsForAnalysis = simulatedRounds as any;
      setRubberbandAnalysis(rubberbandAnalyzer.analyze(roundsForAnalysis));
      setAnomalyReport(anomalyDetector.analyzePredictions(
        simulatedRounds.map(r => ({ predicted: r.multiplier, confidence: 0.8 })),
        simulatedRounds.map(r => r.multiplier)
      ));
      setStrategyInsights(strategyInsightsEngine.generateInsights(roundsForAnalysis));
    } catch (error) {
      console.error('Error running analysis engines:', error);
    }
  }, [source, timeframe]);

  const handleTimeframeChange = (newTimeframe: Timeframe) => {
    setTimeframe(newTimeframe);
  };

  const handleExecuteTrade = (type: 'buy' | 'sell') => {
    const newPosition: Position = {
      id: Date.now().toString(),
      entry: orderBook.asks[0]?.price || 1.5,
      current: orderBook.asks[0]?.price || 1.5,
      size: positionSize,
      pnl: 0,
      pnlPercent: 0,
      type: type === 'buy' ? 'long' : 'short'
    };
    setPositions([...positions, newPosition]);
    setIsTrading(true);
  };

  const handleClosePosition = (id: string) => {
    setPositions(positions.filter(p => p.id !== id));
  };

  return (
    <div className="min-h-screen bg-[#0a0e17] text-gray-100">
      {/* Top Navigation Bar */}
      <div className="bg-[#131722] border-b border-gray-800 px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Activity className="h-6 w-6 text-blue-500" />
              <span className="text-xl font-bold">MomentoFX2</span>
              <Badge variant="outline" className="text-xs text-blue-400 border-blue-500">
                PRO
              </Badge>
            </div>
            
            {/* Symbol Selector */}
            <Select value={source} onValueChange={setSource}>
              <SelectTrigger className="w-32 bg-[#1e222d] border-gray-700 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-[#1e222d] border-gray-700">
                <SelectItem value="aviator">Aviator</SelectItem>
                <SelectItem value="crash">Crash</SelectItem>
                <SelectItem value="jetx">JetX</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="text-gray-400 hover:text-white">
              <LayoutGrid className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="text-gray-400 hover:text-white">
              <Maximize2 className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="relative text-gray-400 hover:text-white">
              <Bell className="h-4 w-4" />
              {notifications > 0 && (
                <Badge className="absolute -top-1 -right-1 h-4 w-4 flex items-center justify-center p-0 text-xs bg-red-500">
                  {notifications}
                </Badge>
              )}
            </Button>
            <Button variant="ghost" size="icon" className="text-gray-400 hover:text-white">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-48px)]">
        {/* Left Sidebar - Order Book */}
        <div className="w-64 bg-[#131722] border-r border-gray-800 p-3 hidden lg:block">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium">Order Book</span>
            <MoreHorizontal className="h-4 w-4 text-gray-500" />
          </div>
          
          <div className="space-y-1">
            {/* Asks */}
            <div className="space-y-0.5">
              {orderBook.asks.slice().reverse().map((ask, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-red-400">{ask.price.toFixed(2)}</span>
                  <span className="text-gray-400">{ask.size.toFixed(0)}</span>
                </div>
              ))}
            </div>
            
            {/* Spread */}
            <div className="py-2 text-center text-sm font-medium text-yellow-400">
              Spread: {((orderBook.asks[0]?.price || 0) - (orderBook.bids[0]?.price || 0)).toFixed(3)}
            </div>
            
            {/* Bids */}
            <div className="space-y-0.5">
              {orderBook.bids.map((bid, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-green-400">{bid.price.toFixed(2)}</span>
                  <span className="text-gray-400">{bid.size.toFixed(0)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Trades */}
          <div className="mt-4 pt-4 border-t border-gray-800">
            <div className="text-sm font-medium mb-2">Recent Trades</div>
            <div className="space-y-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className={i % 2 === 0 ? 'text-green-400' : 'text-red-400'}>
                    {(1.5 + Math.random() * 0.5).toFixed(2)}
                  </span>
                  <span className="text-gray-400">{Math.floor(Math.random() * 1000)}</span>
                  <span className="text-gray-500">{i}s ago</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Main Chart Area */}
        <div className="flex-1 flex flex-col">
          {/* Chart Header */}
          <div className="bg-[#131722] border-b border-gray-800 px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div>
                <div className="text-2xl font-bold">{(orderBook.asks[0]?.price || 1.5).toFixed(2)}</div>
                <div className="flex items-center gap-2 text-sm">
                  <span className={Math.random() > 0.5 ? 'text-green-400' : 'text-red-400'}>
                    {Math.random() > 0.5 ? '+' : '-'}{(Math.random() * 2).toFixed(2)}%
                  </span>
                  <span className="text-gray-500">24h</span>
                </div>
              </div>
              
              <div className="h-8 w-px bg-gray-700" />
              
              {/* Timeframe Selector */}
              <div className="flex items-center gap-1">
                {AVAILABLE_TIMEFRAMES.map((tf) => (
                  <Button
                    key={tf}
                    variant={timeframe === tf ? 'default' : 'ghost'}
                    size="sm"
                    className={`text-xs ${timeframe === tf ? 'bg-blue-600 hover:bg-blue-700' : 'text-gray-400 hover:text-white'}`}
                    onClick={() => handleTimeframeChange(tf)}
                  >
                    {tf}
                  </Button>
                ))}
              </div>

              <div className="h-8 w-px bg-gray-700" />

              {/* Chart Type */}
              <div className="flex items-center gap-1">
                <Button
                  variant={chartType === 'candles' ? 'default' : 'ghost'}
                  size="sm"
                  className={`text-xs ${chartType === 'candles' ? 'bg-blue-600 hover:bg-blue-700' : 'text-gray-400 hover:text-white'}`}
                  onClick={() => setChartType('candles')}
                >
                  Candles
                </Button>
                <Button
                  variant={chartType === 'line' ? 'default' : 'ghost'}
                  size="sm"
                  className={`text-xs ${chartType === 'line' ? 'bg-blue-600 hover:bg-blue-700' : 'text-gray-400 hover:text-white'}`}
                  onClick={() => setChartType('line')}
                >
                  Line
                </Button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" className="text-gray-400 hover:text-white">
                <LineChart className="h-4 w-4" />
              </Button>
              <Button variant="ghost" size="icon" className="text-gray-400 hover:text-white">
                <Activity className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Chart Content */}
          <div className="flex-1 bg-[#0a0e17] p-4">
            <Tabs defaultValue="chart" className="h-full">
              <TabsList className="bg-[#131722] border border-gray-800">
                <TabsTrigger value="chart" className="data-[state=active]:bg-blue-600">Chart</TabsTrigger>
                <TabsTrigger value="analysis" className="data-[state=active]:bg-blue-600">Analysis</TabsTrigger>
                <TabsTrigger value="signals" className="data-[state=active]:bg-blue-600">Signals</TabsTrigger>
                <TabsTrigger value="risk" className="data-[state=active]:bg-blue-600">Risk</TabsTrigger>
              </TabsList>

              <TabsContent value="chart" className="h-full mt-4">
                <div className="h-full bg-[#131722] rounded-lg border border-gray-800 flex items-center justify-center">
                  <div className="text-center">
                    <LineChart className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-500">Professional Chart Display</p>
                    <p className="text-sm text-gray-600 mt-2">Advanced charting with indicators</p>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="analysis" className="h-full mt-4 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Rubberband Analysis */}
                  {rubberbandAnalysis && (
                    <Card className="bg-[#131722] border-gray-800">
                      <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <Activity className="h-4 w-4 text-orange-400" />
                          Rubberband Analysis
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <div className="text-xs text-gray-400">Tension</div>
                            <div className="text-lg font-bold text-orange-400">
                              {(rubberbandAnalysis.tension.current_tension * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-400">Snap Prob</div>
                            <div className="text-lg font-bold text-purple-400">
                              {(rubberbandAnalysis.tension.snap_probability * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>
                        {rubberbandAnalysis.snap_prediction && (
                          <div className="p-2 bg-orange-900/20 rounded border border-orange-500/30">
                            <div className="text-xs text-orange-400">Snap Prediction</div>
                            <div className="text-sm font-bold">
                              {rubberbandAnalysis.snap_prediction.predicted_multiplier.toFixed(1)}x
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* Strategy Insights */}
                  {strategyInsights && (
                    <Card className="bg-[#131722] border-gray-800">
                      <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <Brain className="h-4 w-4 text-blue-400" />
                          Strategy Insights
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-400">Risk Level</span>
                          <Badge variant="outline" className={
                            strategyInsights.risk_level === 'critical' ? 'text-red-400 border-red-500' :
                            strategyInsights.risk_level === 'high' ? 'text-orange-400 border-orange-500' :
                            'text-green-400 border-green-500'
                          }>
                            {strategyInsights.risk_level.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-400">Safe Entry</span>
                          <Badge variant="outline" className={
                            strategyInsights.safe_entry_signal.is_safe ? 'text-green-400 border-green-500' : 'text-red-400 border-red-500'
                          }>
                            {strategyInsights.safe_entry_signal.is_safe ? 'YES' : 'NO'}
                          </Badge>
                        </div>
                        {strategyInsights.overdue_moonshot.is_overdue && (
                          <div className="p-2 bg-red-900/20 rounded border border-red-500/30">
                            <div className="text-xs text-red-400">Moonshot Overdue</div>
                            <div className="text-sm font-bold">
                              {strategyInsights.overdue_moonshot.expected_multiplier.toFixed(1)}x
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )}

                  {/* Anomaly Detection */}
                  {anomalyReport && (
                    <Card className="bg-[#131722] border-gray-800">
                      <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <Shield className="h-4 w-4 text-red-400" />
                          Anomaly Detection
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-400">Alert Level</span>
                          <Badge variant="outline" className={
                            anomalyReport.alert_level === 'critical' ? 'text-red-400 border-red-500' :
                            anomalyReport.alert_level === 'warning' ? 'text-yellow-400 border-yellow-500' :
                            'text-green-400 border-green-500'
                          }>
                            {anomalyReport.alert_level.toUpperCase()}
                          </Badge>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Accuracy</div>
                          <div className="text-lg font-bold">
                            {(anomalyReport.prediction_accuracy.accuracy_rate * 100).toFixed(0)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Recent Anomalies</div>
                          <div className="text-lg font-bold text-red-400">
                            {anomalyReport.recent_anomalies.length}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  {/* Pressure Analysis */}
                  {pressure && (
                    <Card className="bg-[#131722] border-gray-800">
                      <CardHeader>
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <Activity className="h-4 w-4 text-purple-400" />
                          Pressure Analysis
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div>
                          <div className="text-xs text-gray-400">Overall Pressure</div>
                          <div className="text-lg font-bold text-purple-400">
                            {pressure.overall.toFixed(2)}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Signal</div>
                          <div className="text-sm font-bold capitalize">{pressure.signal}</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Strength</div>
                          <Progress value={pressure.strength * 100} className="h-2" />
                        </div>
                      </CardContent>
                    </Card>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="signals" className="h-full mt-4">
                <Card className="bg-[#131722] border-gray-800 h-full">
                  <CardHeader>
                    <CardTitle className="text-sm font-medium">Trade Signals</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {tradeSignal ? (
                      <div className={`p-4 rounded-lg border ${
                        tradeSignal.type === 'buy' ? 'bg-green-900/20 border-green-500/30' : 'bg-red-900/20 border-red-500/30'
                      }`}>
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            {tradeSignal.type === 'buy' ? (
                              <TrendingUp className="h-5 w-5 text-green-400" />
                            ) : (
                              <TrendingDown className="h-5 w-5 text-red-400" />
                            )}
                            <span className="font-semibold capitalize">{tradeSignal.type} Signal</span>
                          </div>
                          <Badge variant="outline" className={
                            tradeSignal.type === 'buy' ? 'text-green-400 border-green-500' : 'text-red-400 border-red-500'
                          }>
                            {(tradeSignal.confidence * 100).toFixed(0)}% conf
                          </Badge>
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <div className="text-xs text-gray-400">Target</div>
                            <div className="text-lg font-bold">{tradeSignal.target.toFixed(2)}x</div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-400">Stop Loss</div>
                            <div className="text-lg font-bold">{tradeSignal.stopLoss.toFixed(2)}x</div>
                          </div>
                          <div>
                            <div className="text-xs text-gray-400">Strength</div>
                            <div className="text-lg font-bold">{(tradeSignal.strength * 100).toFixed(0)}%</div>
                          </div>
                        </div>
                        <div className="mt-3 pt-3 border-t border-gray-700">
                          <div className="text-xs text-gray-400">Reason: {tradeSignal.reason}</div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>Waiting for signals...</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="risk" className="h-full mt-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card className="bg-[#131722] border-gray-800">
                    <CardHeader>
                      <CardTitle className="text-sm font-medium">Position Sizing</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <Label>Position Size</Label>
                        <div className="flex items-center gap-2 mt-2">
                          <Slider
                            value={[positionSize]}
                            onValueChange={(v) => setPositionSize(v[0])}
                            max={100}
                            step={1}
                            className="flex-1"
                          />
                          <span className="text-sm w-12 text-right">{positionSize}</span>
                        </div>
                      </div>
                      <div>
                        <Label>Leverage: {leverage}x</Label>
                        <div className="flex items-center gap-2 mt-2">
                          <Slider
                            value={[leverage]}
                            onValueChange={(v) => setLeverage(v[0])}
                            max={10}
                            step={0.5}
                            className="flex-1"
                          />
                        </div>
                      </div>
                      <div>
                        <Label>Risk per Trade: {riskPercent}%</Label>
                        <div className="flex items-center gap-2 mt-2">
                          <Slider
                            value={[riskPercent]}
                            onValueChange={(v) => setRiskPercent(v[0])}
                            max={10}
                            step={0.5}
                            className="flex-1"
                          />
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="bg-[#131722] border-gray-800">
                    <CardHeader>
                      <CardTitle className="text-sm font-medium">Risk Metrics</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-400">Daily P&L</span>
                        <span className="text-sm font-medium text-green-400">+$125.50</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-400">Win Rate</span>
                        <span className="text-sm font-medium">68.5%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-400">Max Drawdown</span>
                        <span className="text-sm font-medium text-red-400">-8.2%</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-400">Risk/Reward</span>
                        <span className="text-sm font-medium">1:2.5</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Right Sidebar - Trading Panel */}
        <div className="w-80 bg-[#131722] border-l border-gray-800 p-4">
          {/* Trading Controls */}
          <Card className="bg-[#1e222d] border-gray-700 mb-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Quick Trade</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <Button
                  className="bg-green-600 hover:bg-green-700 h-12"
                  onClick={() => handleExecuteTrade('buy')}
                >
                  <TrendingUp className="h-4 w-4 mr-2" />
                  BUY
                </Button>
                <Button
                  className="bg-red-600 hover:bg-red-700 h-12"
                  onClick={() => handleExecuteTrade('sell')}
                >
                  <TrendingDown className="h-4 w-4 mr-2" />
                  SELL
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="icon" className="flex-1">
                  <RotateCcw className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" className="flex-1">
                  {isTrading ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Active Positions */}
          <Card className="bg-[#1e222d] border-gray-700 mb-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Active Positions</CardTitle>
            </CardHeader>
            <CardContent>
              {positions.length === 0 ? (
                <div className="text-center py-4 text-gray-500 text-sm">
                  No active positions
                </div>
              ) : (
                <div className="space-y-2">
                  {positions.map((position) => (
                    <div key={position.id} className="p-2 bg-[#131722] rounded border border-gray-700">
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="outline" className={
                          position.type === 'long' ? 'text-green-400 border-green-500' : 'text-red-400 border-red-500'
                        }>
                          {position.type.toUpperCase()}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-xs text-gray-400 hover:text-white"
                          onClick={() => handleClosePosition(position.id)}
                        >
                          Close
                        </Button>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-gray-400">Entry:</span>
                          <span className="ml-1">{position.entry.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">Current:</span>
                          <span className="ml-1">{position.current.toFixed(2)}</span>
                        </div>
                        <div>
                          <span className="text-gray-400">Size:</span>
                          <span className="ml-1">{position.size}</span>
                        </div>
                        <div className={position.pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                          <span className="text-gray-400">P&L:</span>
                          <span className="ml-1">${position.pnl.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Account Info */}
          <Card className="bg-[#1e222d] border-gray-700">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Account</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Balance</span>
                <span className="text-sm font-medium">$10,450.00</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Equity</span>
                <span className="text-sm font-medium text-green-400">$10,575.50</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Margin</span>
                <span className="text-sm font-medium">$1,250.00</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-400">Free Margin</span>
                <span className="text-sm font-medium">$9,325.50</span>
              </div>
              <div className="pt-2 border-t border-gray-700">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Margin Level</span>
                  <span className="text-sm font-medium">845%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}