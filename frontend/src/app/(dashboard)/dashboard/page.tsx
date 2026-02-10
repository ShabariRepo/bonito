"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { Box, Cloud, Rocket, Activity, TrendingUp, Zap, Plus, ArrowRight, DollarSign } from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { ErrorBanner } from "@/components/ui/error-banner";
import Link from "next/link";
import { useRouter } from "next/navigation";

function AnimatedCounter({ value, duration = 1, prefix = "", suffix = "" }: { value: number; duration?: number; prefix?: string; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const step = Math.max(1, Math.ceil(value / (duration * 60)));
    const timer = setInterval(() => {
      start += step;
      if (start >= value) {
        setCount(value);
        clearInterval(timer);
      } else {
        setCount(start);
      }
    }, 1000 / 60);
    return () => clearInterval(timer);
  }, [inView, value, duration]);

  return <span ref={ref}>{prefix}{count.toLocaleString()}{suffix}</span>;
}

interface Provider {
  id: string;
  name: string;
  provider_type: string;
  status: string;
  model_count: number;
  region: string;
}

interface AuditEntry {
  action: string;
  target?: string;
  resource_type?: string;
  timestamp?: string;
  created_at?: string;
  details?: string;
  [key: string]: any;
}

const providerEmoji: Record<string, string> = { aws: "☁️", azure: "🔷", gcp: "🔺" };

export default function DashboardPage() {
  const router = useRouter();
  const [providers, setProviders] = useState<Provider[]>([]);
  const [modelCount, setModelCount] = useState<number | null>(null);
  const [costSummary, setCostSummary] = useState<any>(null);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [topModels, setTopModels] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = async () => {
    setError(null);
    setLoading(true);
    try {
      // Fetch providers
      const provRes = await apiRequest("/api/providers/");
      let provs: Provider[] = [];
      if (provRes.ok) {
        provs = await provRes.json();
        setProviders(provs);
        const totalModels = provs.reduce((sum: number, p: any) => sum + (p.model_count || 0), 0);
        setModelCount(totalModels);
        if (provs.length === 0) {
          router.replace("/onboarding");
          return;
        }
      } else {
        throw new Error("Failed to load providers");
      }

      // Fetch in parallel: costs, audit, models
      const [costRes, auditRes, modelsRes] = await Promise.allSettled([
        apiRequest("/api/costs/?period=monthly"),
        apiRequest("/api/audit/"),
        apiRequest("/api/models/"),
      ]);

      if (costRes.status === "fulfilled" && costRes.value.ok) {
        setCostSummary(await costRes.value.json());
      }

      if (auditRes.status === "fulfilled" && auditRes.value.ok) {
        const auditData = await auditRes.value.json();
        // Handle both array and {items: []} response shapes
        setAuditLog(Array.isArray(auditData) ? auditData.slice(0, 8) : (auditData.items || []).slice(0, 8));
      }

      if (modelsRes.status === "fulfilled" && modelsRes.value.ok) {
        const allModels = await modelsRes.value.json();
        // Show a sample of models grouped by provider
        setTopModels(allModels.slice(0, 6));
      }
    } catch (e) {
      console.error("Dashboard fetch error:", e);
      setError("Failed to load dashboard data. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, [router]);

  const providerCount = providers.length;

  const stats = [
    { name: "Connected Providers", value: providerCount, icon: Cloud, color: "text-blue-500", href: "/providers" },
    { name: "Available Models", value: modelCount ?? 0, icon: Box, color: "text-violet-500", href: "/models" },
    { name: "Monthly Spend", value: costSummary?.total_spend ? `$${costSummary.total_spend.toFixed(2)}` : "$0.00", icon: DollarSign, color: "text-emerald-500", href: "/costs", isString: true },
    { name: "Budget Used", value: costSummary?.budget_used_percentage ? `${costSummary.budget_used_percentage.toFixed(0)}%` : "0%", icon: TrendingUp, color: "text-amber-500", href: "/costs", isString: true },
  ];

  function formatTime(ts?: string) {
    if (!ts) return "";
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHrs = Math.floor(diffMin / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    const diffDays = Math.floor(diffHrs / 24);
    return `${diffDays}d ago`;
  }

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Overview of your AI infrastructure</p>
      </motion.div>

      {/* Error banner */}
      {error && <ErrorBanner message={error} onRetry={fetchAll} />}

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Link href={stat.href || "#"}>
              <Card className="hover:border-violet-500/30 transition-colors cursor-pointer">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">{stat.name}</CardTitle>
                  <stat.icon className={`h-4 w-4 ${stat.color}`} />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {loading ? <LoadingDots size="sm" /> : (
                      stat.isString ? stat.value : <AnimatedCounter value={stat.value as number} />
                    )}
                  </div>
                </CardContent>
              </Card>
            </Link>
          </motion.div>
        ))}
      </div>

      {/* Quick connect CTA */}
      {!loading && providerCount === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="rounded-lg border border-dashed border-violet-500/30 bg-violet-500/5 p-6"
        >
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <motion.div
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 2.5, repeat: Infinity }}
              className="text-4xl"
            >
              ☁️
            </motion.div>
            <div className="flex-1 text-center sm:text-left">
              <h3 className="font-semibold">Welcome to Bonito! Let&apos;s connect your first cloud provider.</h3>
              <p className="text-sm text-muted-foreground mt-1">Our setup wizard will guide you through connecting AWS, Azure, or GCP</p>
            </div>
            <Link href="/onboarding">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
              >
                <Rocket className="h-4 w-4" />
                Start Setup Wizard
              </motion.button>
            </Link>
          </div>
        </motion.div>
      )}

      {/* Connected Providers */}
      {!loading && providers.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Cloud className="h-5 w-5 text-blue-500" />
                Connected Providers
              </CardTitle>
              <Link href="/providers" className="text-sm text-violet-400 hover:text-violet-300 flex items-center gap-1">
                View all <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              {providers.map((p, i) => (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.08 }}
                  className="flex items-center gap-3 rounded-lg border border-border p-3 hover:bg-accent/30 transition-colors"
                >
                  <span className="text-2xl">{providerEmoji[p.provider_type] || "☁️"}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{p.name}</p>
                    <p className="text-xs text-muted-foreground">{p.region} · {p.model_count} models</p>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className={`h-2 w-2 rounded-full ${p.status === "active" || p.status === "healthy" ? "bg-green-400" : "bg-yellow-400"}`} />
                    <span className="text-xs capitalize text-muted-foreground">{p.status}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Top Models */}
      {!loading && topModels.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Box className="h-5 w-5 text-violet-500" />
                Sample Models
              </CardTitle>
              <Link href="/models" className="text-sm text-violet-400 hover:text-violet-300 flex items-center gap-1">
                View all {modelCount} <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-3">
              {topModels.map((m, i) => (
                <motion.div
                  key={m.model_id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.06 }}
                  className="flex items-center gap-3 rounded-lg border border-border p-3 hover:bg-accent/30 transition-colors"
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
                    <Box className="h-4 w-4 text-violet-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{m.model_name || m.model_id}</p>
                    <p className="text-xs text-muted-foreground capitalize">{m.provider || m.provider_type}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Activity (from audit log) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-violet-500" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8"><LoadingDots size="sm" /></div>
          ) : auditLog.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No recent activity recorded yet</p>
          ) : (
            <div className="space-y-3">
              {auditLog.map((item, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.08 }}
                  className="flex items-center justify-between rounded-lg border border-border p-3 hover:bg-accent/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
                      {item.resource_type === "provider" || item.action?.includes("provider") ? (
                        <Cloud className="h-4 w-4 text-blue-400" />
                      ) : (
                        <Activity className="h-4 w-4 text-violet-400" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        <span className="text-muted-foreground">{item.action}</span>{" "}
                        {item.target || item.details || ""}
                      </p>
                    </div>
                  </div>
                  <span className="text-xs text-muted-foreground">{formatTime(item.timestamp || item.created_at)}</span>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
