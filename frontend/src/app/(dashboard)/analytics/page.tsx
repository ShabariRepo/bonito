"use client";

import { useState, useEffect, useRef } from "react";
import { motion, useInView } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  BarChart3,
  Activity,
  DollarSign,
  Layers,
  Users,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
} from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { ErrorBanner } from "@/components/ui/error-banner";

/* ─── Animated counter ─── */
function AnimatedCounter({ value, prefix = "", suffix = "", decimals = 0 }: {
  value: number; prefix?: string; suffix?: string; decimals?: number;
}) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref as any, { once: true });

  useEffect(() => {
    if (!inView) return;
    const duration = 1.2;
    const steps = Math.ceil(duration * 60);
    const increment = value / steps;
    let frame = 0;
    let current = 0;
    const timer = setInterval(() => {
      frame++;
      current += increment;
      if (frame >= steps) { setCount(value); clearInterval(timer); }
      else setCount(current);
    }, 1000 / 60);
    return () => clearInterval(timer);
  }, [inView, value]);

  return <span ref={ref}>{prefix}{count.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}{suffix}</span>;
}

/* ─── Spark line ─── */
function SparkLine({ data, color = "#8b5cf6", height = 60 }: { data: number[]; color?: string; height?: number }) {
  if (!data.length) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 100;
  const points = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = height - ((v - min) / range) * (height - 10) - 5;
    return `${x},${y}`;
  }).join(" ");
  const areaPoints = `0,${height} ${points} ${w},${height}`;

  return (
    <svg viewBox={`0 0 ${w} ${height}`} className="w-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`grad-${color.replace("#","")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <motion.polygon points={areaPoints} fill={`url(#grad-${color.replace("#","")})`} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 1 }} />
      <motion.polyline points={points} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.5, ease: "easeOut" }} />
    </svg>
  );
}

/* ─── Animated bar ─── */
function AnimatedBar({ percentage, color, delay = 0 }: { percentage: number; color: string; delay?: number }) {
  return (
    <div className="h-3 w-full rounded-full bg-accent/50 overflow-hidden">
      <motion.div className="h-full rounded-full" style={{ backgroundColor: color }} initial={{ width: 0 }} animate={{ width: `${percentage}%` }} transition={{ duration: 1, delay, ease: "easeOut" }} />
    </div>
  );
}

/* ─── Trend arrow ─── */
function TrendIndicator({ direction, percentage }: { direction: string; percentage: number }) {
  const Icon = direction === "increasing" ? TrendingUp : direction === "decreasing" ? TrendingDown : Minus;
  const color = direction === "increasing" ? "text-red-400" : direction === "decreasing" ? "text-emerald-500" : "text-muted-foreground";
  return (
    <span className={`flex items-center gap-1 text-sm font-medium ${color}`}>
      <Icon className="h-4 w-4" />
      {Math.abs(percentage).toFixed(1)}%
    </span>
  );
}

const PROVIDER_COLORS: Record<string, string> = {
  Anthropic: "#8b5cf6",
  OpenAI: "#10b981",
  "AWS Bedrock": "#f59e0b",
  "Google AI": "#3b82f6",
};

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [costs, setCosts] = useState<any>(null);
  const [trends, setTrends] = useState<any>(null);
  const [period, setPeriod] = useState("day");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [o, u, c, t] = await Promise.all([
          apiRequest("/api/analytics/overview").then(r => r.json()),
          apiRequest(`/api/analytics/usage?period=${period}`).then(r => r.json()),
          apiRequest("/api/analytics/costs").then(r => r.json()),
          apiRequest("/api/analytics/trends").then(r => r.json()),
        ]);
        setOverview(o);
        setUsage(u);
        setCosts(c);
        setTrends(t);
      } catch (e) {
        console.error("Failed to load analytics", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [period]);

  if (loading) {
    return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Analytics"
        description="Usage insights, cost trends, and team performance"
        actions={
          <div className="flex rounded-lg border border-border overflow-hidden">
            {["day", "week", "month"].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                  period === p ? "bg-violet-600 text-white" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        }
      />

      {/* Overview cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[
          { title: "Total Requests", value: overview?.total_requests || 0, icon: Activity, color: "text-blue-500", prefix: "", decimals: 0 },
          { title: "Total Cost", value: overview?.total_cost || 0, icon: DollarSign, color: "text-violet-500", prefix: "$", decimals: 2 },
          { title: "Active Models", value: overview?.active_models || 0, icon: Layers, color: "text-emerald-500", prefix: "", decimals: 0 },
          { title: "Top Model", value: 0, icon: Zap, color: "text-amber-500", label: overview?.top_model || "—" },
        ].map((stat, i) => (
          <motion.div key={stat.title} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
            <Card className="hover:border-violet-500/30 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{stat.title}</CardTitle>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stat.label ? stat.label : <AnimatedCounter value={stat.value} prefix={stat.prefix} decimals={stat.decimals} />}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Trends row */}
      {trends && (
        <div className="grid gap-4 md:grid-cols-3">
          {[
            { title: "Cost Trend", data: trends.cost_trend, prefix: "$" },
            { title: "Request Trend", data: trends.request_trend },
            { title: "Efficiency", data: trends.efficiency_trend },
          ].map((t, i) => (
            <motion.div key={t.title} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 + i * 0.1 }}>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">{t.title}</CardTitle>
                </CardHeader>
                <CardContent className="flex items-center justify-between">
                  <TrendIndicator direction={t.data.direction} percentage={t.data.percentage} />
                  {t.data.current_period && (
                    <span className="text-sm text-muted-foreground">
                      {t.prefix || ""}{typeof t.data.current_period === "number" ? t.data.current_period.toLocaleString() : t.data.current_period}
                    </span>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Usage chart */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-violet-500" />
              Requests Over Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-40">
              <SparkLine data={usage?.data?.map((d: any) => d.requests) || []} color="#8b5cf6" height={140} />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground mt-2">
              <span>{usage?.data?.[0]?.label}</span>
              <span>{usage?.data?.[usage.data.length - 1]?.label}</span>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Cost breakdown by provider + by model */}
      <div className="grid gap-6 lg:grid-cols-2">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          <Card>
            <CardHeader>
              <CardTitle>Cost by Provider</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {costs?.by_provider?.map((p: any, i: number) => (
                <div key={p.provider} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{p.provider}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-muted-foreground">{p.percentage}%</span>
                      <span className="font-semibold">${p.cost.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    </div>
                  </div>
                  <AnimatedBar percentage={p.percentage} color={PROVIDER_COLORS[p.provider] || "#6b7280"} delay={i * 0.15} />
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
          <Card>
            <CardHeader>
              <CardTitle>Top Models by Cost</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {costs?.by_model?.map((m: any, i: number) => (
                  <motion.div
                    key={m.model}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 + i * 0.08 }}
                    className="flex items-center justify-between py-2 border-b border-border last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground font-mono w-5">#{i + 1}</span>
                      <div>
                        <p className="text-sm font-medium">{m.model}</p>
                        <p className="text-xs text-muted-foreground">{m.provider} · {m.requests.toLocaleString()} reqs</p>
                      </div>
                    </div>
                    <span className="text-sm font-semibold">${m.cost.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Team usage table */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5 text-violet-500" />
              Team Usage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-3 px-2 font-medium text-muted-foreground">Team</th>
                    <th className="text-right py-3 px-2 font-medium text-muted-foreground">Requests</th>
                    <th className="text-right py-3 px-2 font-medium text-muted-foreground">Cost</th>
                    <th className="text-right py-3 px-2 font-medium text-muted-foreground">Share</th>
                    <th className="text-left py-3 px-2 font-medium text-muted-foreground w-1/3"></th>
                  </tr>
                </thead>
                <tbody>
                  {costs?.by_team?.map((t: any, i: number) => (
                    <motion.tr
                      key={t.team}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.8 + i * 0.05 }}
                      className="border-b border-border last:border-0"
                    >
                      <td className="py-3 px-2 font-medium">{t.team}</td>
                      <td className="py-3 px-2 text-right text-muted-foreground">{t.requests.toLocaleString()}</td>
                      <td className="py-3 px-2 text-right font-semibold">${t.cost.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                      <td className="py-3 px-2 text-right text-muted-foreground">{t.percentage}%</td>
                      <td className="py-3 px-2">
                        <AnimatedBar
                          percentage={t.percentage}
                          color={["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#ef4444"][i] || "#6b7280"}
                          delay={0.8 + i * 0.1}
                        />
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Model shifts */}
      {trends?.model_shifts && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.9 }}>
          <Card>
            <CardHeader>
              <CardTitle>Model Adoption Trends</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-3">
                {trends.model_shifts.map((m: any, i: number) => (
                  <div key={m.model} className="flex items-center justify-between p-3 rounded-lg bg-accent/30">
                    <span className="text-sm font-medium">{m.model}</span>
                    <TrendIndicator direction={m.direction} percentage={m.change} />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
