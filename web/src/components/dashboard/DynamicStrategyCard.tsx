import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { TrendingUp, TrendingDown, Target, Activity } from 'lucide-react';

interface DynamicStrategyCardProps {
  strategy: {
    name: string;
    roi: number;
    winRate: number;
    betsPlaced: number;
    maxDrawdown: number;
    finalBalance: number;
    strategyType: string;
  };
  isActive?: boolean;
}

export const DynamicStrategyCard: React.FC<DynamicStrategyCardProps> = ({ 
  strategy, 
  isActive = false 
}) => {
  const getRoiColor = (roi: number) => {
    if (roi >= 15) return 'text-green-400';
    if (roi >= 5) return 'text-green-300';
    if (roi >= 0) return 'text-gray-400';
    return 'text-red-400';
  };

  const getWinRateColor = (winRate: number) => {
    if (winRate >= 50) return 'text-green-400';
    if (winRate >= 40) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <Card className={`bg-gray-900 border-gray-800 ${isActive ? 'ring-2 ring-blue-500' : ''}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{strategy.name}</CardTitle>
          {isActive && (
            <Badge className="bg-blue-500/20 text-blue-400 border-blue-500">
              Active
            </Badge>
          )}
        </div>
        <CardDescription className="capitalize">{strategy.strategyType}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* ROI */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">ROI</span>
          </div>
          <span className={`text-lg font-bold ${getRoiColor(strategy.roi)}`}>
            {strategy.roi.toFixed(1)}%
          </span>
        </div>

        {/* Win Rate */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400">Win Rate</span>
          </div>
          <span className={`text-lg font-bold ${getWinRateColor(strategy.winRate)}`}>
            {strategy.winRate.toFixed(1)}%
          </span>
        </div>

        {/* Win Rate Progress */}
        <div>
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Win Rate</span>
            <span>{strategy.winRate.toFixed(1)}%</span>
          </div>
          <Progress value={strategy.winRate} className="h-2" />
        </div>

        {/* Additional Metrics */}
        <div className="grid grid-cols-2 gap-3 pt-3 border-t border-gray-800">
          <div>
            <div className="text-xs text-gray-400 mb-1">Bets Placed</div>
            <div className="text-sm font-medium">{strategy.betsPlaced}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Max Drawdown</div>
            <div className="text-sm font-medium text-red-400">{strategy.maxDrawdown.toFixed(1)}%</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Final Balance</div>
            <div className="text-sm font-medium">${strategy.finalBalance.toFixed(2)}</div>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Activity</div>
            <div className="text-sm font-medium flex items-center gap-1">
              <Activity className="w-3 h-3" />
              {strategy.betsPlaced > 50 ? 'High' : strategy.betsPlaced > 20 ? 'Medium' : 'Low'}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
