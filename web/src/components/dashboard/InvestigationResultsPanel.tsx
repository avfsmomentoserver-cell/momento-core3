import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Target, 
  Activity,
  CheckCircle,
  XCircle
} from 'lucide-react';

interface InvestigationResultsPanelProps {
  results: {
    strategy_name: string;
    bets_placed: number;
    wins: number;
    losses: number;
    net_profit: number;
    roi_pct: number;
    max_drawdown: number;
    final_balance: number;
    win_rate: number;
    max_consecutive_losses: number;
    entry_decisions: string[];
  };
  showDetails?: boolean;
}

export const InvestigationResultsPanel: React.FC<InvestigationResultsPanelProps> = ({
  results,
  showDetails = true
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

  const getDrawdownColor = (drawdown: number) => {
    if (drawdown <= 5) return 'text-green-400';
    if (drawdown <= 10) return 'text-yellow-400';
    return 'text-red-400';
  };

  const entryDecisions = results.entry_decisions || [];
  const enterCount = entryDecisions.filter(d => d.startsWith('ENTER')).length;
  const dontEnterCount = entryDecisions.filter(d => d.startsWith('DONT_ENTER')).length;
  const stopCount = entryDecisions.filter(d => d.startsWith('STOP')).length;

  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-400" />
            {results.strategy_name}
          </CardTitle>
          <Badge className={getRoiColor(results.roi_pct)}>
            {results.roi_pct >= 0 ? '+' : ''}{results.roi_pct.toFixed(1)}% ROI
          </Badge>
        </div>
        <CardDescription>
          Investigation suite results and performance metrics
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Key Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Net Profit</div>
            <div className={`text-lg font-bold ${results.net_profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              ${results.net_profit.toFixed(2)}
            </div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Win Rate</div>
            <div className={`text-lg font-bold ${getWinRateColor(results.win_rate)}`}>
              {results.win_rate.toFixed(1)}%
            </div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Max Drawdown</div>
            <div className={`text-lg font-bold ${getDrawdownColor(results.max_drawdown)}`}>
              {results.max_drawdown.toFixed(1)}%
            </div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Final Balance</div>
            <div className="text-lg font-bold text-blue-400">
              ${results.final_balance.toFixed(2)}
            </div>
          </div>
        </div>

        {/* Win/Loss Breakdown */}
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle className="w-4 h-4 text-green-400" />
              <span className="text-xs text-gray-400">Wins</span>
            </div>
            <div className="text-xl font-bold text-green-400">{results.wins}</div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-1">
              <XCircle className="w-4 h-4 text-red-400" />
              <span className="text-xs text-gray-400">Losses</span>
            </div>
            <div className="text-xl font-bold text-red-400">{results.losses}</div>
          </div>
          <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
            <div className="flex items-center gap-2 mb-1">
              <Target className="w-4 h-4 text-blue-400" />
              <span className="text-xs text-gray-400">Total Bets</span>
            </div>
            <div className="text-xl font-bold text-blue-400">{results.bets_placed}</div>
          </div>
        </div>

        {/* Win Rate Progress */}
        <div>
          <div className="flex justify-between text-sm text-gray-400 mb-2">
            <span>Win Rate</span>
            <span>{results.win_rate.toFixed(1)}%</span>
          </div>
          <div className="relative h-3 bg-gray-700 rounded-full overflow-hidden">
            <div 
              className={`absolute top-0 left-0 h-full transition-all ${
                results.win_rate >= 50 ? 'bg-green-500':
                results.win_rate >= 40 ? 'bg-yellow-500' :
                'bg-red-500'
              }`}
              style={{ width: `${results.win_rate}%` }}
            />
          </div>
        </div>

        {showDetails && (
          <>
            {/* Entry Decision Analysis */}
            <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
              <div className="text-sm text-gray-400 mb-2">Entry Decision Analysis</div>
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center">
                  <div className="text-lg font-bold text-green-400">{enterCount}</div>
                  <div className="text-xs text-gray-500">ENTER</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-yellow-400">{dontEnterCount}</div>
                  <div className="text-xs text-gray-500">DONT_ENTER</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-red-400">{stopCount}</div>
                  <div className="text-xs text-gray-500">STOP</div>
                </div>
              </div>
            </div>

            {/* Risk Metrics */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
                <div className="text-xs text-gray-400 mb-1">Max Consecutive Losses</div>
                <div className="text-lg font-bold text-orange-400">
                  {results.max_consecutive_losses}
                </div>
              </div>
              <div className="p-3 bg-gray-800 rounded-lg border border-gray-700">
                <div className="text-xs text-gray-400 mb-1">Entry Rate</div>
                <div className="text-lg font-bold text-blue-400">
                  {entryDecisions.length > 0 ? ((enterCount / entryDecisions.length) * 100).toFixed(1) : 0}%
                </div>
              </div>
            </div>
         
            {/* Performance Assessment */}
            <div className={`p-3 rounded-lg border ${
              results.roi_pct >= 10 ? 'bg-green-900/30 border-green-500/50' :
              results.roi_pct >= 0 ? 'bg-blue-900/30 border-blue-500/50' :
              'bg-red-900/30 border-red-500/50'
            }`}>
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4" />
                <span className="text-sm font-medium">
                  {results.roi_pct >= 15 ? 'Excellent Performance' :
                   results.roi_pct >= 10 ? 'Good Performance' :
                   results.roi_pct >= 5 ? 'Moderate Performance' :
                   results.roi_pct >= 0 ? 'Positive Performance' :
                   'Negative Performance'}
                </span>
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};
