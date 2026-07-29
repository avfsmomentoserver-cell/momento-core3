import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Target, AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PatternData {
  id: string;
  name: string;
  pattern_type?: string;
  description?: string;
  confidence: number;
  probability?: number;
  target_price?: number;
  stop_loss?: number;
  risk_reward_ratio?: number;
  bullish?: boolean;
  severity?: 'high' | 'medium' | 'low';
  crashPoint?: number;
  multiplier?: number;
  detected_at?: string;
  timestamp?: string;
  type?: string;
  timeframe?: string;
}

interface PatternCardProps {
  pattern: PatternData;
  size?: 'sm' | 'md' | 'lg';
  showDetails?: boolean;
}

export function PatternCard({ pattern, size = 'md', showDetails = true }: PatternCardProps) {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-signal/20 text-signal border-signal';
    if (confidence >= 0.6) return 'bg-info/20 text-info border-info';
    if (confidence >= 0.4) return 'bg-caution/20 text-caution border-caution';
    return 'bg-critical/20 text-critical border-critical';
  };

  const getTrendIcon = () => {
    if (pattern.bullish !== undefined) {
      return pattern.bullish ? (
        <TrendingUp className="w-4 h-4 text-signal" />
      ) : (
        <TrendingDown className="w-4 h-4 text-critical" />
      );
    }
    if (pattern.severity) {
      return <AlertTriangle className="w-4 h-4" />;
    }
    return <Target className="w-4 h-4" />;
  };

  const getTrendColor = () => {
    if (pattern.bullish !== undefined) {
      return pattern.bullish ? 'bg-signal/20' : 'bg-critical/20';
    }
    if (pattern.severity === 'high') return 'bg-critical/20';
    if (pattern.severity === 'medium') return 'bg-caution/20';
    return 'bg-info/20';
  };

  const getTrendTextColor = () => {
    if (pattern.bullish !== undefined) {
      return pattern.bullish ? 'text-signal' : 'text-critical';
    }
    if (pattern.severity === 'high') return 'text-critical';
    if (pattern.severity === 'medium') return 'text-caution';
    return 'text-info';
  };

  const multiplier = pattern.crashPoint ?? pattern.multiplier ?? pattern.target_price;

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  return (
    <Card className="bg-gray-900 border-gray-800">
      <CardHeader className={cn('pb-3', size === 'sm' && 'pb-2')}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className={cn('p-2 rounded-lg', getTrendColor())}>
              {getTrendIcon()}
            </div>
            <CardTitle className={cn('font-medium', sizeClasses[size])}>
              {pattern.name || pattern.pattern_type || 'Unknown Pattern'}
            </CardTitle>
          </div>
          <Badge className={getConfidenceColor(pattern.confidence)}>
            {(pattern.confidence * 100).toFixed(0)}%
          </Badge>
        </div>
      </CardHeader>
      {showDetails && (
        <CardContent className="space-y-2">
          {pattern.description && (
            <p className={cn('text-muted-foreground', sizeClasses[size])}>
              {pattern.description}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            {pattern.type && (
              <Badge variant="outline" className="text-xs">
                {pattern.type}
              </Badge>
            )}
            {pattern.timeframe && (
              <Badge variant="outline" className="text-xs">
                {pattern.timeframe}
              </Badge>
            )}
            {pattern.severity && (
              <Badge variant="outline" className={cn('text-xs', getTrendTextColor())}>
                {pattern.severity}
              </Badge>
            )}
          </div>
          {multiplier && (
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Target</span>
              <span className="font-medium">{multiplier.toFixed(2)}x</span>
            </div>
          )}
          {pattern.stop_loss && (
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Stop Loss</span>
              <span className="font-medium">{pattern.stop_loss.toFixed(2)}x</span>
            </div>
          )}
          {pattern.risk_reward_ratio && (
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">R:R Ratio</span>
              <span className="font-medium">{pattern.risk_reward_ratio.toFixed(2)}</span>
            </div>
          )}
          {pattern.probability !== undefined && (
            <div className="flex justify-between text-xs">
              <span className="text-muted-foreground">Probability</span>
              <span className="font-medium">{(pattern.probability * 100).toFixed(0)}%</span>
            </div>
          )}
          {(pattern.detected_at || pattern.timestamp) && (
            <div className="text-xs text-muted-foreground mt-2">
              {new Date(pattern.detected_at || pattern.timestamp || '').toLocaleTimeString()}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
