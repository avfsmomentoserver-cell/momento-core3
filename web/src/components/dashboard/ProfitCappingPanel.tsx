import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Shield, TrendingUp, AlertTriangle, Wallet } from 'lucide-react';

interface ProfitCappingPanelProps {
  profitCapping: {
    currentProfit: number;
    profitCap: number;
    capRatio: number;
    capReached: boolean;
    actionRequired: string;
    remainingCapacity: number;
  };
  balanceMapping: {
    tier: string;
    scalingFactor: number;
    riskLevel: string;
    positionInRange: number;
  };
  currentBalance: number;
  initialBalance: number;
}

export const ProfitCappingPanel: React.FC<ProfitCappingPanelProps> = ({
  profitCapping,
  balanceMapping,
  currentBalance,
  initialBalance
}) => {
  const getActionColor = (action: string) => {
    switch (action) {
      case 'LOCK_PROFITS':
        return 'bg-red-500/20 text-red-400 border-red-500';
      case 'AUTO_WITHDRAW':
        return 'bg-orange-500/20 text-orange-400 border-orange-500';
      case 'REDUCE_SIZE':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500';
      case 'MONITOR_CLOSELY':
        return 'bg-blue-500/20 text-blue-400 border-blue-500';
      default:
        return 'bg-green-500/20 text-green-400 border-green-500';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high':
        return 'text-red-400';
      case 'moderate':
        return 'text-yellow-400';
      default:
        return 'text-green-400';
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'expert':
        return 'bg-purple-500/20 text-purple-400 border-purple-500';
      case 'advanced':
        return 'bg-blue-500/20 text-blue-400 border-blue-500';
      case 'growth':
        return 'bg-green-500/20 text-green-400 border-green-500';
      case 'starter':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500';
    }
  };

  return (
    <div className="space-y-4">
      {/* Profit Cap Status */}
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-blue-400" />
              Profit Cap Status
            </CardTitle>
            <Badge className={getActionColor(profitCapping.actionRequired)}>
              {profitCapping.actionRequired.replace('_', ' ')}
            </Badge>
          </div>
          <CardDescription>
            Automatic profit protection and balance management
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Current Profit */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
              <div className="text-sm text-gray-400 mb-1">Current Profit</div>
              <div className={`text-2xl font-bold ${profitCapping.currentProfit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                ${profitCapping.currentProfit.toFixed(2)}
              </div>
            </div>
            <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
              <div className="text-sm text-gray-400 mb-1">Profit Cap</div>
              <div className="text-2xl font-bold text-blue-400">
                ${profitCapping.profitCap.toFixed(2)}
              </div>
            </div>
          </div>

          {/* Cap Ratio Progress */}
          <div>
            <div className="flex justify-between text-sm text-gray-400 mb-2">
              <span>Cap Utilization</span>
              <span>{(profitCapping.capRatio * 100).toFixed(1)}%</span>
            </div>
            <div className="relative h-3 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className={`absolute top-0 left-0 h-full transition-all ${
                  profitCapping.capRatio >= 0.9 ? 'bg-red-500' :
                  profitCapping.capRatio >= 0.75 ? 'bg-yellow-500' :
                  'bg-green-500'
                }`}
                style={{ width: `${profitCapping.capRatio * 100}%` }}
              />
            </div>
          </div>

          {/* Remaining Capacity */}
          <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">Remaining Capacity</span>
            </div>
            <span className="font-bold text-green-400">${profitCapping.remainingCapacity.toFixed(2)}</span>
          </div>

          {/* Balance Overview */}
          <div className="grid grid-cols-2 gap-4 pt-3 border-t border-gray-800">
            <div>
              <div className="text-xs text-gray-400 mb-1">Initial Balance</div>
              <div className="text-sm font-medium">${initialBalance.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-xs text-gray-400 mb-1">Current Balance</div>
              <div className="text-sm font-medium">${currentBalance.toFixed(2)}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Balance Tier Mapping */}
      <Card className="bg-gray-900 border-gray-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="w-5 h-5 text-green-400" />
            Balance Tier
          </CardTitle>
          <CardDescription>
            Current balance tier and scaling factors
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Tier Badge */}
          <div className="flex items-center justify-between">
            <Badge className={getTierColor(balanceMapping.tier)}>
              {balanceMapping.tier.toUpperCase()}
            </Badge>
            <div className={`text-sm font-medium ${getRiskColor(balanceMapping.riskLevel)}`}>
              {balanceMapping.riskLevel.toUpperCase()} RISK
            </div>
          </div>

          {/* Scaling Factor */}
          <div className="p-4 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-sm text-gray-400 mb-1">Scaling Factor</div>
            <div className="text-2xl font-bold text-purple-400">
              {balanceMapping.scalingFactor.toFixed(1)}x
            </div>
          </div>

          {/* Position in Range */}
          <div>
            <div className="flex justify-between text-sm text-gray-400 mb-2">
              <span>Position in Range</span>
              <span>{(balanceMapping.positionInRange * 100).toFixed(1)}%</span>
            </div>
            <Progress value={balanceMapping.positionInRange * 100} className="h-2" />
          </div>

          {/* Tier Progression */}
          <div className="space-y-2">
            <div className="text-xs text-gray-400 mb-2">Tier Progression</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-yellow-500 via-green-500 via-blue-500 to-purple-500"
                  style={{ width: `${balanceMapping.positionInRange * 100}%` }}
                />
              </div>
            </div>
            <div className="flex justify-between text-xs text-gray-500">
              <span>Starter</span>
              <span>Growth</span>
              <span>Advanced</span>
              <span>Expert</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Alerts */}
      {profitCapping.capReached && (
        <Card className="bg-red-900/30 border-red-500/50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <div>
                <div className="font-semibold text-red-400">Profit Cap Reached</div>
                <div className="text-sm text-gray-300">
                  Trading has been automatically stopped to protect profits
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
