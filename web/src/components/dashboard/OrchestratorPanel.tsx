import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Brain, Target, Shield, Zap, Play, Pause } from 'lucide-react';

interface OrchestratorPanelProps {
  orchestratorPlan: {
    strategy: string;
    probability: number;
    positionSize: number;
    targetMultiplier: number;
    stopMultiplier: number;
    shouldEnter: boolean;
    entryReason: string;
    strategyType: string;
    profitCapping: {
      currentProfit: number;
      profitCap: number;
      capRatio: number;
      capReached: boolean;
      actionRequired: string;
    };
    balanceMapping: {
      tier: string;
      scalingFactor: number;
      riskLevel: string;
    };
  };
  onExecute?: () => void;
  onPause?: () => void;
}

export const OrchestratorPanel: React.FC<OrchestratorPanelProps> = ({
  orchestratorPlan,
  onExecute,
  onPause
}) => {
  const getConfidenceColor = (probability: number) => {
    if (probability >= 0.7) return 'text-green-400';
    if (probability >= 0.4) return 'text-yellow-400';
    return 'text-red-400';
  };

  const getConfidenceLabel = (probability: number) => {
    if (probability >= 0.7) return 'HIGH';
    if (probability >= 0.4) return 'MEDIUM';
    return 'LOW';
  };

  const getActionColor = (shouldEnter: boolean) => {
    return shouldEnter ? 'bg-green-500/20 text-green-400 border-green-500' : 'bg-red-500/20 text-red-400 border-red-500';
  };

  const getStrategyTypeColor = (type: string) => {
    switch (type) {
      case 'ensemble_aggressive':
        return 'bg-purple-500/20 text-purple-400 border-purple-500';
      case 'momentum_reversal':
        return 'bg-blue-500/20 text-blue-400 border-blue-500';
      case 'volatility_adaptive':
        return 'bg-green-500/20 text-green-400 border-green-500';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500';
    }
  };

  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            Orchestrator Recommendation
          </CardTitle>
          <div className="flex gap-2">
            {orchestratorPlan.shouldEnter && onExecute && (
              <Button 
                size="sm" 
                className="bg-green-600 hover:bg-green-700"
                onClick={onExecute}
              >
                <Play className="w-4 h-4 mr-2" />
                Execute
              </Button>
            )}
            {onPause && (
              <Button 
                size="sm" 
                variant="outline"
                className="border-gray-600 hover:bg-gray-800"
                onClick={onPause}
              >
                <Pause className="w-4 h-4 mr-2" />
                Pause
              </Button>
            )}
          </div>
        </div>
        <CardDescription>
          Dynamic strategy execution plan with profit capping
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Main Decision */}
        <div className={`p-4 rounded-lg border ${getActionColor(orchestratorPlan.shouldEnter)}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              <span className="font-semibold">
                {orchestratorPlan.shouldEnter ? 'ENTER POSITION' : 'WAIT FOR SIGNAL'}
              </span>
            </div>
            <Badge className={getActionColor(orchestratorPlan.shouldEnter)}>
              {orchestratorPlan.shouldEnter ? 'ACTIVE' : 'STANDBY'}
            </Badge>
          </div>
          <p className="text-sm text-gray-300">{orchestratorPlan.entryReason}</p>
        </div>

        {/* Strategy Information */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Strategy</div>
            <div className="text-sm font-medium capitalize">{orchestratorPlan.strategy}</div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Type</div>
            <Badge className={getStrategyTypeColor(orchestratorPlan.strategyType)}>
              {orchestratorPlan.strategyType.replace('_', ' ')}
            </Badge>
          </div>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Confidence</div>
            <div className={`text-lg font-bold ${getConfidenceColor(orchestratorPlan.probability)}`}>
              {(orchestratorPlan.probability * 100).toFixed(0)}%
            </div>
            <div className="text-xs text-gray-500">{getConfidenceLabel(orchestratorPlan.probability)}</div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Position Size</div>
            <div className="text-lg font-bold text-blue-400">
              ${orchestratorPlan.positionSize.toFixed(2)}
            </div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Target</div>
            <div className="text-lg font-bold text-green-400">
              {orchestratorPlan.targetMultiplier.toFixed(2)}x
            </div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Stop Loss</div>
            <div className="text-lg font-bold text-red-400">
              {orchestratorPlan.stopMultiplier.toFixed(2)}x
            </div>
          </div>
        </div>

        {/* Profit Capping Status */}
        <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-blue-400" />
              <span className="text-sm text-gray-400">Profit Cap Status</span>
            </div>
            <Badge variant="outline" className={
              orchestratorPlan.profitCapping.capRatio >= 0.9 ? 'text-red-400 border-red-500' :
              orchestratorPlan.profitCapping.capRatio >= 0.75 ? 'text-yellow-400 border-yellow-500' :
              'text-green-400 border-green-500'
            }>
              {(orchestratorPlan.profitCapping.capRatio * 100).toFixed(0)}%
            </Badge>
          </div>
          <div className="flex justify-between text-xs text-gray-500">
            <span>${orchestratorPlan.profitCapping.currentProfit.toFixed(2)} / ${orchestratorPlan.profitCapping.profitCap.toFixed(2)}</span>
            <span className="capitalize">{orchestratorPlan.profitCapping.actionRequired.replace('_', ' ')}</span>
          </div>
        </div>

        {/* Balance Tier */}
        <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400" />
            <span className="text-sm text-gray-400">Balance Tier</span>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="text-purple-400 border-purple-500">
              {orchestratorPlan.balanceMapping.tier.toUpperCase()}
            </Badge>
            <span className="text-sm text-gray-400">
              {orchestratorPlan.balanceMapping.scalingFactor.toFixed(1)}x scaling
            </span>
          </div>
        </div>

        {/* Action Required Alert */}
        {orchestratorPlan.profitCapping.capReached && (
          <div className="p-3 bg-red-900/30 rounded-lg border border-red-500/50">
            <div className="flex items-center gap-2 text-sm">
              <Shield className="w-4 h-4 text-red-400" />
              <span className="text-red-400 font-medium">
                Profit cap reached - {orchestratorPlan.profitCapping.actionRequired.replace('_', ' ')}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
