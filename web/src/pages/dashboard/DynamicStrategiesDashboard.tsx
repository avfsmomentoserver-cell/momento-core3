import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { DynamicStrategyCard } from '@/components/dashboard/DynamicStrategyCard';
import { ProfitCappingPanel } from '@/components/dashboard/ProfitCappingPanel';
import { OrchestratorPanel } from '@/components/dashboard/OrchestratorPanel';
import { 
  Brain, 
  TrendingUp, 
  Shield, 
  Activity, 
  BarChart3,
  RefreshCw
} from 'lucide-react';

// Mock data - in production this would come from the backend
const mockStrategies = [
  {
    name: 'Dynamic Confidence',
    roi: 17.6,
    winRate: 53.8,
    betsPlaced: 93,
    maxDrawdown: 15.0,
    finalBalance: 117.65,
    strategyType: 'ensemble_aggressive'
  },
  {
    name: 'Momentum Reversal',
    roi: 15.8,
    winRate: 51.8,
    betsPlaced: 85,
    maxDrawdown: 13.6,
    finalBalance: 115.80,
    strategyType: 'momentum_reversal'
  },
  {
    name: 'Volatility Adaptive',
    roi: 9.3,
    winRate: 51.0,
    betsPlaced: 49,
    maxDrawdown: 8.5,
    finalBalance: 104.71,
    strategyType: 'volatility_adaptive'
  }
];

const mockProfitCapping = {
  currentProfit: 17.65,
  profitCap: 23.62,
  capRatio: 0.747,
  capReached: false,
  actionRequired: 'CONTINUE_NORMAL',
  remainingCapacity: 5.97
};

const mockBalanceMapping = {
  tier: 'starter',
  scalingFactor: 0.6,
  riskLevel: 'moderate',
  positionInRange: 0.18
};

const mockOrchestratorPlan = {
  strategy: 'dynamic_confidence',
  probability: 0.68,
  positionSize: 8.50,
  targetMultiplier: 1.3,
  stopMultiplier: 0.78,
  shouldEnter: true,
  entryReason: 'CONFIDENCE_ABOVE_THRESHOLD: Multiple factors aligned with high ensemble score',
  strategyType: 'ensemble_aggressive',
  profitCapping: mockProfitCapping,
  balanceMapping: mockBalanceMapping
};

const DynamicStrategiesDashboard: React.FC = () => {
  const [activeStrategy, setActiveStrategy] = useState('Dynamic Confidence');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [orchestratorPlan, setOrchestratorPlan] = useState(mockOrchestratorPlan);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsRefreshing(false);
  };

  const handleExecute = () => {
    console.log('Executing orchestrator plan:', orchestratorPlan);
    // In production, this would execute the trade
  };

  const handlePause = () => {
    console.log('Pausing orchestrator');
    // In production, this would pause the system
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dynamic Strategies Dashboard</h1>
          <p className="text-gray-400">Real-time strategy performance and orchestrator recommendations</p>
        </div>
        <Button 
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="bg-blue-600 hover:bg-blue-700"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="strategies" className="space-y-4">
        <TabsList className="bg-gray-800 border-gray-700">
          <TabsTrigger value="strategies" className="data-[state=active]:bg-blue-600">
            <BarChart3 className="w-4 h-4 mr-2" />
            Strategies
          </TabsTrigger>
          <TabsTrigger value="orchestrator" className="data-[state=active]:bg-purple-600">
            <Brain className="w-4 h-4 mr-2" />
            Orchestrator
          </TabsTrigger>
          <TabsTrigger value="profit-capping" className="data-[state=active]:bg-green-600">
            <Shield className="w-4 h-4 mr-2" />
            Profit Capping
          </TabsTrigger>
          <TabsTrigger value="performance" className="data-[state=active]:bg-orange-600">
            <TrendingUp className="w-4 h-4 mr-2" />
            Performance
          </TabsTrigger>
        </TabsList>

        {/* Strategies Tab */}
        <TabsContent value="strategies" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {mockStrategies.map((strategy) => (
              <DynamicStrategyCard
                key={strategy.name}
                strategy={strategy}
                isActive={strategy.name === activeStrategy}
              />
            ))}
          </div>

          {/* Strategy Comparison */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Strategy Comparison</CardTitle>
              <CardDescription>Performance metrics across all dynamic strategies</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockStrategies.map((strategy) => (
                  <div key={strategy.name} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
                    <div className="flex items-center gap-3">
                      <Activity className="w-4 h-4 text-gray-400" />
                      <span className="font-medium">{strategy.name}</span>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <div className="text-xs text-gray-400">ROI</div>
                        <div className={`font-bold ${strategy.roi >= 15 ? 'text-green-400' : strategy.roi >= 5 ? 'text-green-300' : 'text-gray-400'}`}>
                          {strategy.roi.toFixed(1)}%
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-gray-400">Win Rate</div>
                        <div className={`font-bold ${strategy.winRate >= 50 ? 'text-green-400' : strategy.winRate >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {strategy.winRate.toFixed(1)}%
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-gray-400">Drawdown</div>
                        <div className="font-bold text-red-400">{strategy.maxDrawdown.toFixed(1)}%</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Orchestrator Tab */}
        <TabsContent value="orchestrator" className="space-y-4">
          <OrchestratorPanel
            orchestratorPlan={orchestratorPlan}
            onExecute={handleExecute}
            onPause={handlePause}
          />

          {/* Strategy Selection */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Active Strategy Selection</CardTitle>
              <CardDescription>Choose which dynamic strategy to use for orchestrator decisions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {mockStrategies.map((strategy) => (
                  <Button
                    key={strategy.name}
                    variant={activeStrategy === strategy.name ? "default" : "outline"}
                    className={
                      activeStrategy === strategy.name
                        ? "bg-blue-600 hover:bg-blue-700"
                        : "border-gray-600 hover:bg-gray-800"
                    }
                    onClick={() => setActiveStrategy(strategy.name)}
                  >
                    {strategy.name}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Profit Capping Tab */}
        <TabsContent value="profit-capping" className="space-y-4">
          <ProfitCappingPanel
            profitCapping={mockProfitCapping}
            balanceMapping={mockBalanceMapping}
            currentBalance={117.65}
            initialBalance={100}
          />

          {/* Profit Capping Configuration */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Profit Capping Configuration</CardTitle>
              <CardDescription>Current profit capping mode and settings</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <div className="text-sm text-gray-400 mb-1">Capping Mode</div>
                  <div className="text-lg font-bold text-purple-400">Hybrid</div>
                  <div className="text-xs text-gray-500 mt-1">Tier-based + Dynamic adjustment</div>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <div className="text-sm text-gray-400 mb-1">Base Profit Ratio</div>
                  <div className="text-lg font-bold text-blue-400">25%</div>
                  <div className="text-xs text-gray-500 mt-1">Maximum 50% with tier progression</div>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <div className="text-sm text-gray-400 mb-1">Profit Locking</div>
                  <div className="text-lg font-bold text-green-400">Enabled</div>
                  <div className="text-xs text-gray-500 mt-1">Automatic profit protection</div>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <div className="text-sm text-gray-400 mb-1">Auto-Withdrawal</div>
                  <div className="text-lg font-bold text-gray-400">Disabled</div>
                  <div className="text-xs text-gray-500 mt-1">Manual withdrawal required</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          {/* Overall Performance */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Overall Performance</CardTitle>
              <CardDescription>Combined performance metrics across all strategies</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <div className="text-sm text-gray-400 mb-1">Total ROI</div>
                  <div className="text-2xl font-bold text-green-400">14.2%</div>
                  <div className="text-xs text-gray-500 mt-1">Average across strategies</div>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <div className="text-sm text-gray-400 mb-1">Total Bets</div>
                  <div className="text-2xl font-bold text-blue-400">227</div>
                  <div className="text-xs text-gray-500 mt-1">Across all strategies</div>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <div className="text-sm text-gray-400 mb-1">Avg Win Rate</div>
                  <div className="text-2xl font-bold text-yellow-400">52.2%</div>
                  <div className="text-xs text-gray-500 mt-1">Combined performance</div>
                </div>
                <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
                  <div className="text-sm text-gray-400 mb-1">Max Drawdown</div>
                  <div className="text-2xl font-bold text-red-400">12.4%</div>
                  <div className="text-xs text-gray-500 mt-1">Worst performing strategy</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Performance Timeline */}
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader>
              <CardTitle>Performance Timeline</CardTitle>
              <CardDescription>Balance evolution over time</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 flex items-center justify-center bg-gray-800 rounded-lg border border-gray-700">
                <div className="text-center text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-2 opacity-50" />
                  <p>Performance chart visualization</p>
                  <p className="text-xs mt-1">Integration with charting library required</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default DynamicStrategiesDashboard;
