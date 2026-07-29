import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { 
  Brain, 
  Calculator, 
  TrendingUp, 
  ShieldAlert, 
  Target, 
  Zap, 
  Loader2, 
  Settings, 
  Play, 
  Pause,
  LineChart,
  BarChart3,
  Activity
} from "lucide-react";
import { useState, useEffect } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/console/EmptyState";
import { Panel } from "@/components/console/Panel";
import { StateBadge } from "@/components/console/StateBadge";
import { StatTile } from "@/components/console/StatTile";
import { AppShell } from "@/components/layout/AppShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import { POLL } from "@/lib/config";
import { currency, decimal, percent, integer, multiplier } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useAuth } from "@/state/AuthProvider";
import { usePlatform } from "@/state/PlatformProvider";
import type { MegaplanPlan, MegaplanBankrollState, MegaplanSafetyCheck, MegaplanStrategyComparison } from "@/lib/types";

const PRECISION_STYLE: Record<string, string> = {
  CONSERVATIVE: "border-info/40 bg-info/10 text-info",
  MODERATE: "border-caution/40 bg-caution/10 text-caution",
  AGGRESSIVE: "border-signal/40 bg-signal/10 text-signal",
  DYNAMIC: "border-purple-500/40 bg-purple-500/10 text-purple-500",
};

const RISK_LEVEL_STYLE: Record<string, string> = {
  normal: "border-signal/35 bg-signal/10 text-signal",
  elevated: "border-caution/35 bg-caution/10 text-caution",
  critical: "border-critical/35 bg-critical/10 text-critical",
};

/** Megaplan Orchestrator - Advanced Decision-Making System */
export default function MegaplanOrchestrator() {
  const { source } = usePlatform();
  const { isOperator } = useAuth();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState("overview");
  
  // Settings state
  const [enabled, setEnabled] = useState(true);
  const [initialBankroll, setInitialBankroll] = useState<string>("1000");
  const [basePositionSize, setBasePositionSize] = useState<string>("10");
  const [maxRiskPerRound, setMaxRiskPerRound] = useState<number>(0.02);
  const [dailyLossLimit, setDailyLossLimit] = useState<number>(0.15);
  const [recoveryStrategy, setRecoveryStrategy] = useState<string>("none");
  const [chaseStrategy, setChaseStrategy] = useState<string>("none");
  const [decisionPrecision, setDecisionPrecision] = useState<string>("dynamic");
  const [adaptiveLearning, setAdaptiveLearning] = useState(true);

  // Queries
  const megaplanQuery = useQuery({
    queryKey: ["megaplan", source],
    queryFn: () => api.megaplan(source),
    refetchInterval: POLL.analysis,
    enabled,
  });

  const settingsQuery = useQuery({
    queryKey: ["megaplan-settings"],
    queryFn: () => api.megaplanSettings(),
  });

  const bankrollQuery = useQuery({
    queryKey: ["megaplan-bankroll", source],
    queryFn: () => api.megaplanBankroll(source),
    refetchInterval: POLL.analysis,
  });

  const compareStrategiesQuery = useQuery({
    queryKey: ["megaplan-compare", source],
    queryFn: () => api.compareStrategies(source),
    enabled: activeTab === "backtest",
  }) as { data: MegaplanStrategyComparison | undefined; isLoading: boolean; refetch: () => void; };

  const comparisonData = compareStrategiesQuery.data;

  // Seed form from settings
  useEffect(() => {
    const settings = settingsQuery.data?.settings;
    if (!settings) return;
    setEnabled(Boolean(settings.enabled ?? true));
    setInitialBankroll(String(settings.initial_bankroll ?? 1000));
    setBasePositionSize(String(settings.base_position_size ?? 10));
    setMaxRiskPerRound(Number(settings.max_risk_per_round ?? 0.02));
    setDailyLossLimit(Number(settings.daily_loss_limit ?? 0.15));
    setRecoveryStrategy(String(settings.recovery_strategy ?? "none"));
    setChaseStrategy(String(settings.chase_strategy ?? "none"));
    setDecisionPrecision(String(settings.decision_precision ?? "dynamic"));
    setAdaptiveLearning(Boolean(settings.adaptive_learning ?? true));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settingsQuery.data?.settings]);

  // Mutations
  const saveSettings = useMutation({
    mutationFn: () =>
      api.updateMegaplanSettings({
        enabled,
        initial_bankroll: Number(initialBankroll) || 0,
        base_position_size: Number(basePositionSize) || 0,
        max_risk_per_round: maxRiskPerRound,
        daily_loss_limit: dailyLossLimit,
        recovery_strategy: recoveryStrategy,
        chase_strategy: chaseStrategy,
        decision_precision: decisionPrecision,
        adaptive_learning: adaptiveLearning,
      }),
    onSuccess: () => {
      toast.success("Megaplan settings updated");
      void queryClient.invalidateQueries({ queryKey: ["megaplan-settings"] });
    },
    onError: (error: Error) => toast.error("Update failed", { description: error.message }),
  });

  const backtestRecovery = useMutation({
    mutationFn: (strategy: string) => api.backtestRecoveryStrategy(source, strategy),
    onSuccess: () => {
      toast.success("Recovery backtest completed");
      void queryClient.invalidateQueries({ queryKey: ["megaplan-compare"] });
    },
    onError: (error: Error) => toast.error("Backtest failed", { description: error.message }),
  });

  const backtestChase = useMutation({
    mutationFn: (strategy: string) => api.backtestChaseStrategy(source, strategy),
    onSuccess: () => {
      toast.success("Chase backtest completed");
      void queryClient.invalidateQueries({ queryKey: ["megaplan-compare"] });
    },
    onError: (error: Error) => toast.error("Backtest failed", { description: error.message }),
  });

  const plan = megaplanQuery.data as MegaplanPlan | undefined;
  const instruction = plan?.instruction;
  const bankrollState = bankrollQuery.data?.bankroll_state;
  const recoveryPlan = plan?.recovery_plan;
  const chasePlan = plan?.chase_plan;

  return (
    <AppShell 
      title="Megaplan Orchestrator" 
      subtitle="Dynamic Decision-Making · Recovery Strategies · Chase Systems"
    >
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="recovery">Recovery</TabsTrigger>
          <TabsTrigger value="chase">Chase</TabsTrigger>
          <TabsTrigger value="backtest">Backtest</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          {megaplanQuery.isLoading ? (
            <div className="flex h-64 items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Building megaplan…
            </div>
          ) : !plan || !instruction ? (
            <EmptyState 
              title="No plan available" 
              description="Ingest rounds so the megaplan orchestrator has structure to reason about." 
            />
          ) : (
            <div className="space-y-4">
              {/* Main Instruction */}
              <section className={cn(
                "panel panel-lit scanline relative overflow-hidden border p-6",
                PRECISION_STYLE[instruction?.precision_level || "DYNAMIC"]
              )}>
                <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-[10px] font-bold uppercase tracking-[0.22em]">
                        {instruction?.action.replace("_", " ") || "WAIT"}
                      </span>
                      <Badge variant="outline" className={cn(
                        "text-[10px] font-bold uppercase",
                        instruction?.precision_level === "CONSERVATIVE" && "text-info border-info",
                        instruction?.precision_level === "MODERATE" && "text-caution border-caution",
                        instruction?.precision_level === "AGGRESSIVE" && "text-signal border-signal",
                        instruction?.precision_level === "DYNAMIC" && "text-purple-500 border-purple-500"
                      )}>
                        {instruction?.precision_level || "DYNAMIC"}
                      </Badge>
                    </div>
                    <h2 className="mt-2.5 text-2xl font-bold tracking-tight text-foreground">
                      {instruction?.headline || "No instruction"}
                    </h2>
                    <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-muted-foreground">
                      {instruction?.detail || "Waiting for market analysis..."}
                    </p>
                  </div>

                  <dl className="grid shrink-0 grid-cols-3 gap-4 lg:gap-6">
                    <div className="text-center">
                      <dt className="hud-label">Size</dt>
                      <dd className="mt-1 font-mono text-xl font-semibold tabular-nums text-foreground">
                        {currency(instruction?.position_size || 0)}
                      </dd>
                    </div>
                    <div className="text-center">
                      <dt className="hud-label">Target</dt>
                      <dd className="mt-1 font-mono text-xl font-semibold tabular-nums text-signal">
                        {multiplier(instruction?.target_multiplier || 0)}
                      </dd>
                    </div>
                    <div className="text-center">
                      <dt className="hud-label">Stop</dt>
                      <dd className="mt-1 font-mono text-xl font-semibold tabular-nums text-critical">
                        {multiplier(instruction?.stop_multiplier || 0)}
                      </dd>
                    </div>
                  </dl>
                </div>
              </section>

              {/* Context Metrics */}
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <StatTile
                  label="Confidence"
                  value={percent(instruction?.confidence || 0)}
                  accent={(instruction?.confidence || 0) >= 0.7 ? "signal" : (instruction?.confidence || 0) >= 0.5 ? "caution" : "critical"}
                  progress={instruction?.confidence || 0}
                  hint="Prediction confidence"
                  icon={<Brain className="h-3.5 w-3.5" />}
                />
                <StatTile
                  label="Opportunity Score"
                  value={percent(plan?.context?.opportunity_score || 0)}
                  accent={(plan?.context?.opportunity_score || 0) >= 0.7 ? "signal" : "caution"}
                  progress={plan?.context?.opportunity_score || 0}
                  hint="Market opportunity"
                  icon={<Target className="h-3.5 w-3.5" />}
                />
                <StatTile
                  label="Risk Appetite"
                  value={percent(plan?.context?.risk_appetite || 0)}
                  accent="info"
                  hint="Current risk tolerance"
                  icon={<Activity className="h-3.5 w-3.5" />}
                />
                <StatTile
                  label="Market State"
                  value={plan?.context?.market_state || "Unknown"}
                  accent="info"
                  hint={`Volatility: ${decimal(plan?.context?.volatility || 0, 2)}`}
                  icon={<LineChart className="h-3.5 w-3.5" />}
                />
              </div>

              {/* Bankroll State */}
              {bankrollState && (
                <Panel title="Bankroll State" subtitle="Current financial position" icon={<Calculator className="h-3.5 w-3.5" />}>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Current Bankroll</div>
                      <div className="text-2xl font-bold text-foreground">
                        {currency(bankrollState.current_bankroll)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Daily P&L</div>
                      <div className={cn(
                        "text-2xl font-bold",
                        bankrollState.daily_pnl >= 0 ? "text-signal" : "text-critical"
                      )}>
                        {currency(bankrollState.daily_pnl)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Drawdown</div>
                      <div className={cn(
                        "text-2xl font-bold",
                        bankrollState.current_drawdown < 0.1 ? "text-signal" : 
                        bankrollState.current_drawdown < 0.2 ? "text-caution" : "text-critical"
                      )}>
                        {percent(bankrollState.current_drawdown)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Win Rate</div>
                      <div className="text-2xl font-bold text-foreground">
                        {percent(bankrollState.win_rate)}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-3">
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Consecutive Losses</span>
                        <span className="font-mono">{bankrollState.consecutive_losses}</span>
                      </div>
                      <Progress 
                        value={Math.min((bankrollState.consecutive_losses / 5) * 100, 100)} 
                        className="h-2"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Consecutive Wins</span>
                        <span className="font-mono">{bankrollState.consecutive_wins}</span>
                      </div>
                      <Progress 
                        value={Math.min((bankrollState.consecutive_wins / 5) * 100, 100)} 
                        className="h-2"
                      />
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs">
                        <span className="text-muted-foreground">Risk Level</span>
                        <Badge className={cn(
                          RISK_LEVEL_STYLE[bankrollState.risk_level] || RISK_LEVEL_STYLE.normal
                        )}>
                          {bankrollState.risk_level.toUpperCase()}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </Panel>
              )}

              {/* Risk Analysis */}
              {plan?.risk_analysis && (
                <Panel title="Risk Analysis" subtitle="Detailed risk assessment" icon={<ShieldAlert className="h-3.5 w-3.5" />}>
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Risk Amount</div>
                      <div className="text-lg font-bold text-foreground">
                        {currency(plan.risk_analysis.risk_amount)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Potential Reward</div>
                      <div className="text-lg font-bold text-signal">
                        {currency(plan.risk_analysis.potential_reward)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Risk/Reward Ratio</div>
                      <div className="text-lg font-bold text-foreground">
                        1:{decimal(plan.risk_analysis.risk_reward_ratio, 2)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Expected Value</div>
                      <div className={cn(
                        "text-lg font-bold",
                        plan.risk_analysis.expected_value >= 0 ? "text-signal" : "text-critical"
                      )}>
                        {currency(plan.risk_analysis.expected_value)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Position Risk</div>
                      <div className="text-lg font-bold text-foreground">
                        {percent(plan.risk_analysis.position_risk_pct)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Win Probability</div>
                      <div className="text-lg font-bold text-foreground">
                        {percent(1 - plan.risk_analysis.probability_of_loss)}
                      </div>
                    </div>
                  </div>
                </Panel>
              )}

              {/* Execution Conditions */}
              {plan?.execution_conditions && plan.execution_conditions.length > 0 && (
                <Panel title="Execution Conditions" subtitle="Requirements for this decision" icon={<Zap className="h-3.5 w-3.5" />}>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {plan.execution_conditions.map((condition: string, idx: number) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <div className="h-1.5 w-1.5 rounded-full bg-signal" />
                        <span className="text-muted-foreground">{condition}</span>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}

              {/* Safety Checks */}
              {plan?.safety_checks && plan.safety_checks.length > 0 && (
                <Panel title="Safety Checks" subtitle="System safety validations" icon={<ShieldAlert className="h-3.5 w-3.5" />}>
                  <div className="space-y-2">
                    {plan.safety_checks.map((check: MegaplanSafetyCheck, idx: number) => (
                      <div key={idx} className={cn(
                        "flex items-center justify-between rounded-md border p-3",
                        check.status === "pass" ? "border-signal/25 bg-signal/8" : "border-critical/25 bg-critical/8"
                      )}>
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "h-2 w-2 rounded-full",
                            check.status === "pass" ? "bg-signal" : "bg-critical"
                          )} />
                          <div>
                            <div className="text-sm font-medium capitalize">{check.type}</div>
                            <div className="text-xs text-muted-foreground">{check.message}</div>
                          </div>
                        </div>
                        <Badge variant="outline" className={cn(
                          "text-[10px]",
                          check.status === "pass" ? "text-signal border-signal" : "text-critical border-critical"
                        )}>
                          {check.status.toUpperCase()}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </Panel>
              )}
            </div>
          )}
        </TabsContent>

        {/* Recovery Tab */}
        <TabsContent value="recovery" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recovery Strategies</CardTitle>
              <CardDescription>
                Automated recovery mechanisms to handle drawdowns and losing streaks
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {recoveryPlan?.active ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium capitalize">{recoveryPlan.strategy}</div>
                      <div className="text-xs text-muted-foreground">
                        Step {recoveryPlan.current_step + 1} of {recoveryPlan.max_steps}
                      </div>
                    </div>
                    <Badge className="bg-signal text-signal-foreground">Active</Badge>
                  </div>
                  
                  <Progress value={recoveryPlan.progress * 100} className="h-2" />
                  
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Recovery Multiplier</div>
                      <div className="text-lg font-bold text-foreground">
                        {multiplier(recoveryPlan.recovery_multiplier)}x
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Est. Recovery Rounds</div>
                      <div className="text-lg font-bold text-foreground">
                        {integer(recoveryPlan.estimated_recovery_rounds)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Progress</div>
                      <div className="text-lg font-bold text-foreground">
                        {percent(recoveryPlan.progress)}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <ShieldAlert className="h-4 w-4" />
                  No recovery strategy active
                </div>
              )}
            </CardContent>
          </Card>

          {settingsQuery.data?.recovery_strategies && (
            <Card>
              <CardHeader>
                <CardTitle>Available Strategies</CardTitle>
                <CardDescription>Select a recovery strategy for automatic drawdown handling</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {settingsQuery.data.recovery_strategies.map((strategy: any) => (
                    <div
                      key={strategy.id}
                      className={cn(
                        "cursor-pointer rounded-md border p-4 transition-colors",
                        recoveryStrategy === strategy.id
                          ? "border-signal bg-signal/10"
                          : "border-gray-700 bg-gray-800 hover:border-gray-600"
                      )}
                      onClick={() => setRecoveryStrategy(strategy.id)}
                    >
                      <div className="font-medium capitalize">{strategy.label}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{strategy.description}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Chase Tab */}
        <TabsContent value="chase" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Chase Strategies</CardTitle>
              <CardDescription>
                High-multiplier chase systems with safety guardrails
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {chasePlan?.active ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium capitalize">{chasePlan.strategy}</div>
                      <div className="text-xs text-muted-foreground">
                        Target: {multiplier(chasePlan.target_multiplier)}x
                      </div>
                    </div>
                    <Badge className="bg-signal text-signal-foreground">Active</Badge>
                  </div>
                  
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Expected Value</div>
                      <div className={cn(
                        "text-lg font-bold",
                        chasePlan.expected_value >= 0 ? "text-signal" : "text-critical"
                      )}>
                        {currency(chasePlan.expected_value)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Risk/Reward</div>
                      <div className="text-lg font-bold text-foreground">
                        1:{decimal(chasePlan.risk_reward_ratio, 2)}
                      </div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-muted-foreground">Current Step</div>
                      <div className="text-lg font-bold text-foreground">
                        {chasePlan.current_step + 1}/{chasePlan.max_steps}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Target className="h-4 w-4" />
                  No chase strategy active
                </div>
              )}
            </CardContent>
          </Card>

          {settingsQuery.data?.chase_strategies && (
            <Card>
              <CardHeader>
                <CardTitle>Available Strategies</CardTitle>
                <CardDescription>Select a chase strategy for high-multiplier targets</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {settingsQuery.data.chase_strategies.map((strategy: any) => (
                    <div
                      key={strategy.id}
                      className={cn(
                        "cursor-pointer rounded-md border p-4 transition-colors",
                        chaseStrategy === strategy.id
                          ? "border-signal bg-signal/10"
                          : "border-gray-700 bg-gray-800 hover:border-gray-600"
                      )}
                      onClick={() => setChaseStrategy(strategy.id)}
                    >
                      <div className="font-medium capitalize">{strategy.label}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{strategy.description}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Backtest Tab */}
        <TabsContent value="backtest" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Strategy Backtesting</CardTitle>
              <CardDescription>
                Test recovery and chase strategies on historical data
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {compareStrategiesQuery.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running backtests…
                </div>
              ) : comparisonData ? (
                <div className="space-y-6">
                  {/* Recovery Strategy Results */}
                  <div>
                    <h3 className="mb-3 text-sm font-medium">Recovery Strategies</h3>
                    <div className="space-y-2">
                      {Object.entries(comparisonData.recovery_strategies || {}).map(
                        ([strategy, result]: [string, any]) => (
                          <div
                            key={strategy}
                            className="flex items-center justify-between rounded-md border border-gray-700 bg-gray-800 p-3"
                          >
                            <div>
                              <div className="text-sm font-medium capitalize">{strategy}</div>
                              <div className="text-xs text-muted-foreground">
                                Success Rate: {percent(result.recovery_success_rate || 0)}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className={cn(
                                "text-sm font-bold",
                                result.pnl_percentage >= 0 ? "text-signal" : "text-critical"
                              )}>
                                {result.pnl_percentage >= 0 ? "+" : ""}{decimal(result.pnl_percentage, 2)}%
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {currency(result.total_pnl)}
                              </div>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* Chase Strategy Results */}
                  <div>
                    <h3 className="mb-3 text-sm font-medium">Chase Strategies</h3>
                    <div className="space-y-2">
                      {Object.entries(comparisonData.chase_strategies || {}).map(
                        ([strategy, result]: [string, any]) => (
                          <div
                            key={strategy}
                            className="flex items-center justify-between rounded-md border border-gray-700 bg-gray-800 p-3"
                          >
                            <div>
                              <div className="text-sm font-medium capitalize">{strategy}</div>
                              <div className="text-xs text-muted-foreground">
                                Success Rate: {percent(result.chase_success_rate || 0)}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className={cn(
                                "text-sm font-bold",
                                result.pnl_percentage >= 0 ? "text-signal" : "text-critical"
                              )}>
                                {result.pnl_percentage >= 0 ? "+" : ""}{decimal(result.pnl_percentage, 2)}%
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {currency(result.total_pnl)}
                              </div>
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* Recommendations */}
                  {comparisonData?.recommendations && (
                    <div className="rounded-md border border-signal/25 bg-signal/8 p-4">
                      <h3 className="mb-2 text-sm font-medium text-signal">Recommendations</h3>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Best Recovery:</span>
                          <span className="font-medium capitalize">
                            {comparisonData?.recommendations?.best_recovery_strategy || "N/A"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Best Chase:</span>
                          <span className="font-medium capitalize">
                            {comparisonData?.recommendations?.best_chase_strategy || "N/A"}
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <Button
                  onClick={() => compareStrategiesQuery.refetch()}
                  disabled={compareStrategiesQuery.isLoading}
                >
                  {compareStrategiesQuery.isLoading && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Run Strategy Comparison
                </Button>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Settings Panel */}
      {isOperator && (
        <Panel title="Settings" subtitle="Configure megaplan orchestrator" icon={<Settings className="h-3.5 w-3.5" />}>
          <div className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="enabled">Enabled</Label>
                <Select value={enabled ? "true" : "false"} onValueChange={(v) => setEnabled(v === "true")}>
                  <SelectTrigger id="enabled">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="true">Enabled</SelectItem>
                    <SelectItem value="false">Disabled</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="precision">Decision Precision</Label>
                <Select value={decisionPrecision} onValueChange={setDecisionPrecision}>
                  <SelectTrigger id="precision">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="conservative">Conservative</SelectItem>
                    <SelectItem value="moderate">Moderate</SelectItem>
                    <SelectItem value="aggressive">Aggressive</SelectItem>
                    <SelectItem value="dynamic">Dynamic</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="initialBankroll">Initial Bankroll</Label>
                <Input
                  id="initialBankroll"
                  type="number"
                  min={0}
                  value={initialBankroll}
                  onChange={(e) => setInitialBankroll(e.target.value)}
                  className="font-mono text-xs"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="basePositionSize">Base Position Size</Label>
                <Input
                  id="basePositionSize"
                  type="number"
                  min={0}
                  value={basePositionSize}
                  onChange={(e) => setBasePositionSize(e.target.value)}
                  className="font-mono text-xs"
                />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="maxRiskPerRound">Max Risk Per Round</Label>
                <div className="flex items-center gap-4">
                  <Slider
                    value={[maxRiskPerRound]}
                    onValueChange={([v]) => setMaxRiskPerRound(v)}
                    min={0.01}
                    max={0.1}
                    step={0.01}
                    className="flex-1"
                  />
                  <span className="w-12 text-right font-mono text-xs">{percent(maxRiskPerRound)}</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="dailyLossLimit">Daily Loss Limit</Label>
                <div className="flex items-center gap-4">
                  <Slider
                    value={[dailyLossLimit]}
                    onValueChange={([v]) => setDailyLossLimit(v)}
                    min={0.05}
                    max={0.5}
                    step={0.05}
                    className="flex-1"
                  />
                  <span className="w-12 text-right font-mono text-xs">{percent(dailyLossLimit)}</span>
                </div>
              </div>
            </div>

            <div className="flex justify-end">
              <Button
                onClick={() => saveSettings.mutate()}
                disabled={saveSettings.isPending}
              >
                {saveSettings.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Save Settings
              </Button>
            </div>
          </div>
        </Panel>
      )}
    </AppShell>
  );
}