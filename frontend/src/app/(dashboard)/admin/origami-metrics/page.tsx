"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ErrorBanner } from "@/components/ui/error-banner";
import { apiRequest } from "@/lib/auth";
import {
  Activity,
  Sparkles,
  TrendingUp,
  TrendingDown,
  Users,
  Building2,
  CheckCircle2,
  Wrench,
} from "lucide-react";

type PeriodStats = {
  total_turns: number;
  success_count: number;
  success_rate: number;
  tool_calls_total: number;
  avg_tool_calls_per_turn: number;
  total_cost_usd: number;
  unique_orgs: number;
  unique_users: number;
};

type DailyPoint = {
  day: string;
  turns: number;
};

type TopTool = {
  tool_name: string;
  calls: number;
  success_count: number;
  success_rate: number;
};

type LaunchMetrics = {
  this_period_start: string;
  now: string;
  this_period: PeriodStats;
  prior_period: PeriodStats;
  growth: {
    turns_pct: number | null;
    cost_pct: number | null;
    users_pct: number | null;
    orgs_pct: number | null;
  };
  daily_turns: DailyPoint[];
  top_tools: TopTool[];
};

function GrowthBadge({ pct }: { pct: number | null }) {
  if (pct === null) {
    return <span className="text-xs text-muted-foreground">no prior data</span>;
  }
  const positive = pct >= 0;
  const Icon = positive ? TrendingUp : TrendingDown;
  const color = positive ? "text-emerald-500" : "text-destructive";
  return (
    <span className={`text-xs flex items-center gap-1 ${color}`}>
      <Icon className="h-3 w-3" />
      {positive ? "+" : ""}
      {(pct * 100).toFixed(0)}% vs last month
    </span>
  );
}

function Sparkline({ data }: { data: DailyPoint[] }) {
  if (data.length === 0) {
    return (
      <div className="h-24 flex items-center justify-center text-xs text-muted-foreground italic">
        No activity yet this period.
      </div>
    );
  }
  const max = Math.max(...data.map((d) => d.turns), 1);
  return (
    <div className="h-24 flex items-end gap-1">
      {data.map((d) => (
        <div
          key={d.day}
          className="flex-1 group relative"
          style={{ height: `${(d.turns / max) * 100}%` }}
        >
          <div className="absolute inset-0 bg-primary/60 rounded-t-sm group-hover:bg-primary transition-colors" />
          <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-popover text-popover-foreground text-xs px-2 py-1 rounded border border-border opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
            {d.day}: {d.turns}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function OrigamiMetricsPage() {
  const [data, setData] = useState<LaunchMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await apiRequest("/api/admin/origami/launch-metrics");
        const body = await res.json();
        setData(body);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="container mx-auto px-4 py-8">
      <PageHeader
        title="Origami Launch Metrics"
        description="Phase 4 launch monitoring: turns this month vs last, success rate, growth deltas, daily activity, top tools by usage. Refresh the page for current data (no auto-poll)."
      />

      {error && <ErrorBanner message={error} />}

      {loading ? (
        <div className="flex justify-center py-12">
          <LoadingDots />
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            <Card>
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <Activity className="h-3 w-3" /> Turns this month
                </div>
                <div className="text-3xl font-bold mt-1 tabular-nums">
                  {data.this_period.total_turns.toLocaleString()}
                </div>
                <div className="mt-1">
                  <GrowthBadge pct={data.growth.turns_pct} />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> Success rate
                </div>
                <div className="text-3xl font-bold mt-1 tabular-nums">
                  {(data.this_period.success_rate * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-muted-foreground mt-1">
                  {data.this_period.success_count.toLocaleString()} of {data.this_period.total_turns.toLocaleString()}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <Users className="h-3 w-3" /> Active users
                </div>
                <div className="text-3xl font-bold mt-1 tabular-nums">
                  {data.this_period.unique_users.toLocaleString()}
                </div>
                <div className="mt-1">
                  <GrowthBadge pct={data.growth.users_pct} />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                  <Building2 className="h-3 w-3" /> Active orgs
                </div>
                <div className="text-3xl font-bold mt-1 tabular-nums">
                  {data.this_period.unique_orgs.toLocaleString()}
                </div>
                <div className="mt-1">
                  <GrowthBadge pct={data.growth.orgs_pct} />
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
            <Card className="lg:col-span-2">
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Activity className="h-4 w-4" /> Daily turns (this period)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Sparkline data={data.daily_turns} />
                {data.daily_turns.length > 0 && (
                  <div className="mt-3 text-xs text-muted-foreground flex justify-between">
                    <span>{data.daily_turns[0]?.day}</span>
                    <span>{data.daily_turns[data.daily_turns.length - 1]?.day}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Sparkles className="h-4 w-4" /> Spend + signal
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wider">
                    Cost this month
                  </div>
                  <div className="text-xl font-bold tabular-nums">
                    ${data.this_period.total_cost_usd.toFixed(2)}
                  </div>
                  <GrowthBadge pct={data.growth.cost_pct} />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground uppercase tracking-wider">
                    Tool calls / turn
                  </div>
                  <div className="text-xl font-bold tabular-nums">
                    {data.this_period.avg_tool_calls_per_turn.toFixed(2)}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {data.this_period.tool_calls_total.toLocaleString()} total
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Wrench className="h-4 w-4" /> Top tools (this period)
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {data.top_tools.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground italic">
                  No tool calls recorded this period.
                </div>
              ) : (
                <div>
                  {data.top_tools.map((t, idx) => (
                    <motion.div
                      key={t.tool_name}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.02 }}
                      className="flex items-center justify-between gap-4 px-4 py-3 border-b border-border last:border-b-0"
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <span className="text-xs text-muted-foreground font-mono w-6">
                          {idx + 1}
                        </span>
                        <span className="font-mono text-sm truncate">
                          {t.tool_name}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 shrink-0 text-sm">
                        <span className="text-muted-foreground tabular-nums">
                          {t.calls.toLocaleString()} call
                          {t.calls === 1 ? "" : "s"}
                        </span>
                        <Badge
                          variant="outline"
                          className={
                            t.success_rate >= 0.95
                              ? "text-emerald-500 border-emerald-500/30 bg-emerald-500/10"
                              : t.success_rate >= 0.8
                                ? "text-amber-500 border-amber-500/30 bg-amber-500/10"
                                : "text-destructive border-destructive/30 bg-destructive/10"
                          }
                        >
                          {(t.success_rate * 100).toFixed(0)}% success
                        </Badge>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="mt-6 text-xs text-muted-foreground font-mono">
            Period start: {new Date(data.this_period_start).toISOString()} · Snapshot: {new Date(data.now).toISOString()}
          </div>
        </>
      ) : null}
    </div>
  );
}
