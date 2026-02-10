"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { DollarSign, TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight, Download, PieChart, BarChart3, Activity } from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { ErrorBanner } from "@/components/ui/error-banner";

/* ─── Animated counter ─── */
function AnimatedCounter({ value, prefix = "", suffix = "", decimals = 0, duration = 1.2 }: {
  value: number; prefix?: string; suffix?: string; decimals?: number; duration?: number;
}) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref as any, { once: true });

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const steps = Math.ceil(duration * 60);
    const increment = value / steps;
    let frame = 0;
    const timer = setInterval(() => {
      frame++;
      start += increment;
      if (frame >= steps) { setCount(value); clearInterval(timer); }
      else setCount(start);
    }, 1000 / 60);
    return () => clearInterval(timer);
  }, [inView, value, duration]);

  return <span ref={ref}>{prefix}{count.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}{suffix}</span>;
}

/* ─── Animated bar ─── */
function AnimatedBar({ percentage, color, delay = 0 }: { percentage: number; color: string; delay?: number }) {
  return (
    <div className="h-3 w-full rounded-full bg-accent/50 overflow-hidden">
      <motion.div
        className="h-full rounded-full"
        style={{ backgroundColor: color }}
        initial={{ width: 0 }}
        animate={{ width: `${percentage}%` }}
        transition={{ duration: 1, delay, ease: "easeOut" }}
      />
    </div>
  );
}

/* ─── Mini SVG line chart ─── */
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
        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <motion.polygon
        points={areaPoints}
        fill="url(#sparkGrad)"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1 }}
      />
      <motion.polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        initial={{ pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: 1.5, ease: "easeOut" }}
      />
    </svg>
  );
}

/* ─── Budget gauge ─── */
function BudgetGauge({ percentage }: { percentage: number }) {
  const clamp = Math.min(percentage, 100);
  const color = clamp > 90 ? "#ef4444" : clamp > 70 ? "#f59e0b" : "#10b981";
  const circumference = 2 * Math.PI * 45;
  const dashoffset = circumference - (clamp / 100) * circumference;

  return (
    <div className="relative flex items-center justify-center">
      <svg width="140" height="140" className="-rotate-90">
        <circle cx="70" cy="70" r="45" fill="none" stroke="currentColor" strokeWidth="8" className="text-accent/30" />
        <motion.circle
          cx="70" cy="70" r="45" fill="none" stroke={color} strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: dashoffset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute text-center">
        <motion.span
          className="text-2xl font-bold"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {clamp.toFixed(0)}%
        </motion.span>
        <p className="text-xs text-muted-foreground">of budget</p>
      </div>
    </div>
  );
}

/* ─── Provider icon ─── */
const PROVIDER_NAMES: Record<string, string> = { aws: "AWS", azure: "Azure", gcp: "GCP" };
const PROVIDER_EMOJI: Record<string, string> = { aws: "🟠", azure: "🔵", gcp: "🔴" };

/* ─── Main page ─── */
export default function CostsPage() {
  const [summary, setSummary] = useState<any>(null);
  const [breakdown, setBreakdown] = useState<any>(null);
  const [forecast, setForecast] = useState<any>(null);
  const [period, setPeriod] = useState("monthly");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCosts = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, b, f] = await Promise.all([
        apiRequest(`/api/costs/?period=${period}`).then(r => { if (!r.ok) throw new Error("costs"); return r.json(); }),
        apiRequest("/api/costs/breakdown").then(r => { if (!r.ok) throw new Error("breakdown"); return r.json(); }),
        apiRequest("/api/costs/forecast").then(r => { if (!r.ok) throw new Error("forecast"); return r.json(); }),
      ]);
      setSummary(s);
      setBreakdown(b);
      setForecast(f);
    } catch (e) {
      console.error("Failed to load costs", e);
      setError("Failed to load cost data. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCosts();
  }, [period]);

  const exportCSV = useCallback(() => {
    if (!summary) return;
    const rows = [["Date", "Amount"], ...summary.daily_costs.map((d: any) => [d.date, d.amount])];
    const csv = rows.map((r: any) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `bonito-costs-${period}.csv`; a.click();
    URL.revokeObjectURL(url);
  }, [summary, period]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingDots size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Cost Tracking"
        description="Unified spend visibility across all providers"
        actions={
          <div className="flex items-center gap-3">
            <div className="flex rounded-lg border border-border overflow-hidden">
              {["daily", "weekly", "monthly"].map((p) => (
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
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={exportCSV}
              className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </motion.button>
          </div>
        }
      />

      {error && <ErrorBanner message={error} onRetry={loadCosts} />}

      {/* Top stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[
          {
            title: "Total Spend",
            value: summary?.total_spend || 0,
            prefix: "$",
            icon: DollarSign,
            color: "text-violet-500",
            sub: `${period} total`,
          },
          {
            title: "Budget Used",
            value: summary?.budget_used_percentage || 0,
            suffix: "%",
            icon: PieChart,
            color: summary?.budget_used_percentage > 80 ? "text-amber-500" : "text-emerald-500",
            sub: `of $${(summary?.budget || 0).toLocaleString()} budget`,
          },
          {
            title: "Trend",
            value: Math.abs(summary?.change_percentage || 0),
            suffix: "%",
            icon: summary?.change_percentage >= 0 ? TrendingUp : TrendingDown,
            color: summary?.change_percentage >= 0 ? "text-red-400" : "text-emerald-500",
            sub: summary?.change_percentage >= 0 ? "increase vs prev." : "decrease vs prev.",
          },
          {
            title: "Projected Monthly",
            value: forecast?.projected_monthly_spend || 0,
            prefix: "$",
            icon: Activity,
            color: "text-blue-500",
            sub: forecast?.trend === "increasing" ? "↗ trending up" : forecast?.trend === "decreasing" ? "↘ trending down" : "→ stable",
          },
        ].map((stat, i) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="hover:border-violet-500/30 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{stat.title}</CardTitle>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  <AnimatedCounter value={stat.value} prefix={stat.prefix} suffix={stat.suffix} decimals={stat.prefix === "$" ? 2 : 1} />
                </div>
                <p className="text-xs text-muted-foreground mt-1">{stat.sub}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Spend trend chart + budget gauge */}
      <div className="grid gap-6 lg:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-2"
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-violet-500" />
                Spend Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-40">
                <SparkLine
                  data={summary?.daily_costs?.map((d: any) => d.amount) || []}
                  color="#8b5cf6"
                  height={140}
                />
              </div>
              <div className="flex justify-between text-xs text-muted-foreground mt-2">
                <span>{summary?.daily_costs?.[0]?.date}</span>
                <span>{summary?.daily_costs?.[summary.daily_costs.length - 1]?.date}</span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card className="flex flex-col items-center justify-center h-full">
            <CardHeader>
              <CardTitle className="text-center">Budget Utilization</CardTitle>
            </CardHeader>
            <CardContent>
              <BudgetGauge percentage={summary?.budget_used_percentage || 0} />
              <p className="text-center text-sm text-muted-foreground mt-3">
                ${summary?.total_spend?.toLocaleString(undefined, { minimumFractionDigits: 2 })} of ${summary?.budget?.toLocaleString()}
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Provider breakdown */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Provider Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            {breakdown?.by_provider?.map((p: any, i: number) => (
              <div key={p.provider} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span>{PROVIDER_EMOJI[p.provider] || "⚪"}</span>
                    <span className="font-medium">{PROVIDER_NAMES[p.provider] || p.provider}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-muted-foreground">{p.percentage}%</span>
                    <span className="font-semibold">${p.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>
                <AnimatedBar percentage={p.percentage} color={p.color} delay={i * 0.15} />
              </div>
            ))}
          </CardContent>
        </Card>
      </motion.div>

      {/* Top models + Departments */}
      <div className="grid gap-6 lg:grid-cols-2">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Top Models by Spend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {breakdown?.by_model?.slice(0, 6).map((m: any, i: number) => (
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
                        <p className="text-xs text-muted-foreground">{PROVIDER_NAMES[m.provider] || m.provider} · {m.requests.toLocaleString()} reqs</p>
                      </div>
                    </div>
                    <span className="text-sm font-semibold">${m.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  </motion.div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Spend by Department</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {breakdown?.by_department?.map((d: any, i: number) => (
                  <div key={d.department} className="space-y-1.5">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{d.department}</span>
                      <span className="text-muted-foreground">${d.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                    </div>
                    <AnimatedBar
                      percentage={d.percentage}
                      color={["#8b5cf6", "#3b82f6", "#10b981", "#f59e0b", "#6b7280"][i] || "#8b5cf6"}
                      delay={0.7 + i * 0.1}
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Forecast */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-violet-500" />
                14-Day Forecast
              </CardTitle>
              {forecast?.savings_opportunity > 0 && (
                <Badge variant="success">
                  💡 Save ~${forecast.savings_opportunity.toLocaleString()} with optimization
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-32">
              <SparkLine
                data={forecast?.forecast?.map((f: any) => f.projected) || []}
                color="#3b82f6"
                height={120}
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground mt-2">
              <span>{forecast?.forecast?.[0]?.date}</span>
              <span>{forecast?.forecast?.[forecast.forecast.length - 1]?.date}</span>
            </div>
            <div className="mt-4 flex gap-6 text-sm">
              <div>
                <span className="text-muted-foreground">Current monthly: </span>
                <span className="font-semibold">${forecast?.current_monthly_spend?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Projected: </span>
                <span className="font-semibold">${forecast?.projected_monthly_spend?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
