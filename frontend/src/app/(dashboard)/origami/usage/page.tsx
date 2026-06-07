"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Wand2, MessageSquare, DollarSign, BarChart3, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { apiRequest } from "@/lib/auth";

type DailyEntry = { day: string; turns: number; cost_usd: number };

type UsagePayload = {
  period: string;
  tier: string;
  turns_used: number;
  turns_cap: number | null;
  turns_remaining: number | null;
  percent_used: number | null;
  cost_usd_this_period: number;
  overage_rate_usd: number;
  input_tokens: number;
  output_tokens: number;
  tool_calls: number;
  daily: DailyEntry[];
};

function fmtUsd(v: number): string {
  if (v < 0.01) return `$${v.toFixed(4)}`;
  if (v < 1) return `$${v.toFixed(3)}`;
  return `$${v.toFixed(2)}`;
}

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return `${n}`;
}

export default function OrigamiUsagePage() {
  const [data, setData] = useState<UsagePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiRequest("/api/origami/usage")
      .then((r) => {
        setData(r as unknown as UsagePayload);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const overUsed = data && data.percent_used !== null && data.percent_used > 100;
  const nearCap = data && data.percent_used !== null && data.percent_used > 80 && data.percent_used <= 100;
  const overageTurns = data && data.turns_cap !== null
    ? Math.max(0, data.turns_used - data.turns_cap)
    : 0;
  const overageCost = data ? overageTurns * data.overage_rate_usd : 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Origami usage"
        description="Track your Origami turns this billing period and see what your team has been building."
        breadcrumbs={[
          { label: "Origami", href: "/origami" },
          { label: "Usage" },
        ]}
      />

      {loading && (
        <Card className="p-8 flex items-center justify-center text-sm text-muted-foreground">
          Loading usage…
        </Card>
      )}

      {error && (
        <Card className="p-4 border-destructive/30 bg-destructive/5 text-sm text-destructive">
          Could not load usage: {error}
        </Card>
      )}

      {data && (
        <>
          {/* Top stats row */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard
              icon={<MessageSquare className="h-4 w-4" />}
              label="Turns used"
              value={data.turns_used.toLocaleString()}
              hint={
                data.turns_cap !== null
                  ? `of ${data.turns_cap.toLocaleString()} on ${data.tier}`
                  : "Unlimited on this plan"
              }
            />
            <StatCard
              icon={<Sparkles className="h-4 w-4" />}
              label="Remaining"
              value={data.turns_remaining !== null ? data.turns_remaining.toLocaleString() : "∞"}
              hint={data.percent_used !== null ? `${data.percent_used}% used` : "no limit"}
              valueClassName={
                overUsed
                  ? "text-destructive"
                  : nearCap
                    ? "text-amber-500"
                    : undefined
              }
            />
            <StatCard
              icon={<DollarSign className="h-4 w-4" />}
              label="Period spend"
              value={fmtUsd(data.cost_usd_this_period)}
              hint={
                overageTurns > 0
                  ? `incl. ${overageTurns} overage @ ${fmtUsd(data.overage_rate_usd)}/turn`
                  : "no overage charges"
              }
            />
            <StatCard
              icon={<BarChart3 className="h-4 w-4" />}
              label="Tool calls"
              value={data.tool_calls.toLocaleString()}
              hint={`${fmtTokens(data.input_tokens)} in / ${fmtTokens(data.output_tokens)} out`}
            />
          </div>

          {/* Quota meter */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Wand2 className="h-4 w-4 text-primary" />
                Quota for {data.period}
                <Badge variant="outline" className="text-[10px] capitalize">{data.tier}</Badge>
              </CardTitle>
              <CardDescription>
                Origami turns are calls to the conversational planner. Each
                user prompt + Origami response counts as one turn. Tools
                Origami runs on your behalf aren&apos;t metered against
                this quota — they hit your gateway request quota instead.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {data.turns_cap === null ? (
                <div className="text-sm text-muted-foreground italic">
                  Unlimited turns on this plan.
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {data.turns_used.toLocaleString()} / {data.turns_cap.toLocaleString()} turns
                    </span>
                    <span className={
                      overUsed ? "text-destructive font-medium" :
                      nearCap ? "text-amber-500 font-medium" :
                      "text-muted-foreground"
                    }>
                      {data.percent_used}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(100, data.percent_used ?? 0)}%` }}
                      transition={{ duration: 0.6, ease: "easeOut" }}
                      className={
                        overUsed ? "h-full bg-destructive" :
                        nearCap ? "h-full bg-amber-500" :
                        "h-full bg-primary"
                      }
                    />
                  </div>
                  {overUsed && (
                    <div className="text-sm text-destructive mt-2">
                      You&apos;ve gone {overageTurns} turn{overageTurns === 1 ? "" : "s"} past your base quota.
                      Overage so far: {fmtUsd(overageCost)} ({fmtUsd(data.overage_rate_usd)}/turn on {data.tier}).
                    </div>
                  )}
                  {nearCap && !overUsed && (
                    <div className="text-sm text-amber-500 mt-2">
                      You&apos;re close to your monthly cap. Overage kicks in at {fmtUsd(data.overage_rate_usd)}/turn.
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Daily breakdown */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Daily breakdown</CardTitle>
              <CardDescription>Turns and spend per day in {data.period}.</CardDescription>
            </CardHeader>
            <CardContent>
              {data.daily.length === 0 ? (
                <div className="text-sm text-muted-foreground italic">
                  No turns yet this period.
                </div>
              ) : (
                <DailyChart daily={data.daily} />
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  hint,
  valueClassName = "",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  hint?: string;
  valueClassName?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
          {icon}
          {label}
        </div>
        <div className={`text-2xl font-semibold tracking-tight ${valueClassName}`}>
          {value}
        </div>
        {hint && <div className="text-xs text-muted-foreground mt-1">{hint}</div>}
      </CardContent>
    </Card>
  );
}

function DailyChart({ daily }: { daily: DailyEntry[] }) {
  const maxTurns = Math.max(...daily.map((d) => d.turns), 1);
  return (
    <div className="space-y-2">
      {daily.map((entry) => {
        const widthPct = (entry.turns / maxTurns) * 100;
        return (
          <div key={entry.day} className="flex items-center gap-3 text-sm">
            <div className="w-24 text-xs font-mono text-muted-foreground shrink-0">
              {entry.day}
            </div>
            <div className="flex-1 relative h-6 bg-muted rounded overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${widthPct}%` }}
                transition={{ duration: 0.5, ease: "easeOut" }}
                className="h-full bg-primary/40 border-r-2 border-primary"
              />
              <div className="absolute inset-0 flex items-center px-2 text-xs text-foreground/80">
                {entry.turns} turn{entry.turns === 1 ? "" : "s"}
              </div>
            </div>
            <div className="w-20 text-xs text-right font-mono text-muted-foreground shrink-0">
              {fmtUsd(entry.cost_usd)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
