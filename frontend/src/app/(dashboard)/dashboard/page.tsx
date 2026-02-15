"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { Box, Cloud, Rocket, Activity, TrendingUp, Zap, Plus, ArrowRight, DollarSign, MessageSquare, Clock, Cpu } from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { useAPI } from "@/lib/swr";
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
  
  // SWR hooks — data cached across navigations, revalidates in background
  const { data: providers = [], isLoading: provLoading, error: provError, mutate: mutateProviders } = useAPI<Provider[]>("/api/providers/");
  const { data: usage } = useAPI<any>("/api/gateway/usage?days=30");
  const { data: rawDeployments = [] } = useAPI<any[]>("/api/deployments/");
  const { data: rawAudit } = useAPI<any>("/api/audit/");
  const { data: costSummary } = useAPI<any>("/api/costs/?period=monthly");
  
  const deployments = rawDeployments || [];
  const auditLog: AuditEntry[] = rawAudit ? (Array.isArray(rawAudit) ? rawAudit.slice(0, 8) : (rawAudit.items || []).slice(0, 8)) : [];
  const modelCount = providers.reduce((sum: number, p: any) => sum + (p.model_count || 0), 0);
  const loading = provLoading;
  const error = provError ? "Failed to load dashboard data." : null;
  
  const fetchAll = () => { mutateProviders(); };

  useEffect(() => {
    if (!provLoading && providers.length === 0 && !provError) {
      router.replace("/onboarding");
    }
  }, [provLoading, providers, provError, router]);

  const providerCount = providers.length;

  const totalTokens = (usage?.total_input_tokens || 0) + (usage?.total_output_tokens || 0);
  const formatTokens = (t: number) => t >= 1_000_000 ? `${(t / 1_000_000).toFixed(1)}M` : t >= 1_000 ? `${(t / 1_000).toFixed(1)}K` : `${t}`;
  const gatewayCost = usage?.total_cost || 0;
  const displayCost = gatewayCost > 0 ? gatewayCost : (costSummary?.total_spend || 0);

  const activeDeployments = deployments.filter(d => d.status === "active" || d.status === "deploying");

  const stats = [
    { name: "Connected Providers", value: providerCount, icon: Cloud, color: "text-blue-500", href: "/providers" },
    { name: "Available Models", value: modelCount ?? 0, icon: Box, color: "text-violet-500", href: "/models" },
    { name: "Active Deployments", value: activeDeployments.length, icon: Rocket, color: "text-orange-500", href: "/deployments" },
    { name: "API Requests", value: usage?.total_requests || 0, icon: MessageSquare, color: "text-cyan-500", href: "/gateway" },
    { name: "Gateway Spend", value: `$${displayCost.toFixed(4)}`, icon: DollarSign, color: "text-emerald-500", href: "/costs", isString: true },
    { name: "Tokens Used", value: formatTokens(totalTokens), icon: Cpu, color: "text-amber-500", href: "/analytics", isString: true },
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
      <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
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
          className="rounded-lg border border-dashed border-violet-500/30 bg-violet-500/5 p-4 md:p-6"
        >
          <div className="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left">
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
            <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
              {providers.map((p, i) => (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.08 }}
                  className="flex items-center gap-3 rounded-lg border border-border p-3 hover:bg-accent/30 transition-colors min-h-[60px] touch-manipulation"
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

      {/* Active Deployments */}
      {!loading && providers.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Rocket className="h-5 w-5 text-orange-500" />
                Deployments
              </CardTitle>
              <Link href="/deployments" className="text-sm text-violet-400 hover:text-violet-300 flex items-center gap-1">
                Manage <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {activeDeployments.length > 0 ? (
              <div className="space-y-3">
                {activeDeployments.slice(0, 6).map((d: any, i: number) => {
                  const config = d.config || {};
                  const providerType = config.provider_type || "unknown";
                  const emoji = providerType === "aws" ? "☁️" : providerType === "azure" ? "🔷" : providerType === "gcp" ? "🔺" : "☁️";
                  const estimate = config.cost_estimate;
                  const statusColor = d.status === "active" ? "bg-green-400" : d.status === "deploying" ? "bg-yellow-400" : "bg-gray-400";
                  return (
                    <motion.div
                      key={d.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.2 + i * 0.08 }}
                      className="flex items-center gap-3 rounded-lg border border-border p-3 hover:bg-accent/30 transition-colors"
                    >
                      <span className="text-2xl">{emoji}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium truncate">{config.name || config.model_display_name || "Deployment"}</p>
                          <div className={`h-2 w-2 rounded-full ${statusColor}`} />
                          <span className="text-xs capitalize text-muted-foreground">{d.status}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          {config.model_display_name || ""} · {providerType.toUpperCase()}
                          {estimate && estimate.monthly > 0 ? ` · ~$${estimate.monthly.toFixed(0)}/mo` : estimate ? " · Pay-per-use" : ""}
                        </p>
                      </div>
                      {config.endpoint_url && (
                        <a
                          href={config.endpoint_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-violet-400 hover:text-violet-300"
                        >
                          Endpoint →
                        </a>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            ) : (
              <div className="flex flex-col sm:flex-row items-center gap-4 py-4 text-center sm:text-left">
                <motion.div
                  animate={{ y: [0, -6, 0] }}
                  transition={{ duration: 2.5, repeat: Infinity }}
                  className="text-4xl"
                >
                  🚀
                </motion.div>
                <div className="flex-1">
                  <h3 className="font-semibold text-sm">No active deployments</h3>
                  <p className="text-xs text-muted-foreground mt-1">
                    Provision AI model infrastructure on your cloud — AWS Bedrock throughput, Azure OpenAI endpoints, or Vertex AI access.
                  </p>
                </div>
                <Link href="/deployments">
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-3 py-2 text-xs font-medium text-white hover:bg-violet-700"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Deploy Model
                  </motion.button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Usage by Model + Usage Over Time */}
      {!loading && usage && (usage.total_requests > 0 || usage.by_model?.length > 0) && (
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
          {/* Top Models by Usage */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5 text-violet-500" />
                  Top Models (30d)
                </CardTitle>
                <Link href="/analytics" className="text-sm text-violet-400 hover:text-violet-300 flex items-center gap-1">
                  Details <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {usage.by_model?.length > 0 ? (
                <div className="space-y-3">
                  {usage.by_model
                    .sort((a: any, b: any) => b.requests - a.requests)
                    .slice(0, 8)
                    .map((m: any, i: number) => {
                      const maxReqs = Math.max(...usage.by_model.map((x: any) => x.requests));
                      const pct = maxReqs > 0 ? (m.requests / maxReqs) * 100 : 0;
                      return (
                        <motion.div
                          key={m.model}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: 0.2 + i * 0.05 }}
                        >
                          <div className="flex items-center justify-between text-sm mb-1">
                            <span className="font-medium truncate max-w-[60%]" title={m.model}>{m.model}</span>
                            <span className="text-muted-foreground">{m.requests} req · {formatTokens(m.tokens)} tok · ${m.cost.toFixed(4)}</span>
                          </div>
                          <div className="h-2 rounded-full bg-accent overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${pct}%` }}
                              transition={{ delay: 0.3 + i * 0.05, duration: 0.5 }}
                              className="h-full rounded-full bg-violet-500"
                            />
                          </div>
                        </motion.div>
                      );
                    })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-8">No model usage yet. Try the Playground!</p>
              )}
            </CardContent>
          </Card>

          {/* Daily Usage Chart */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-emerald-500" />
                Daily Requests (30d)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {usage.by_day?.length > 0 ? (
                <div className="flex items-end gap-1 h-40">
                  {usage.by_day.slice(-30).map((d: any, i: number) => {
                    const maxReqs = Math.max(...usage.by_day.map((x: any) => x.requests));
                    const pct = maxReqs > 0 ? (d.requests / maxReqs) * 100 : 0;
                    return (
                      <motion.div
                        key={d.date}
                        initial={{ height: 0 }}
                        animate={{ height: `${Math.max(pct, 2)}%` }}
                        transition={{ delay: 0.2 + i * 0.03, duration: 0.4 }}
                        className="flex-1 bg-violet-500/80 rounded-t hover:bg-violet-400 transition-colors cursor-default min-w-[4px]"
                        title={`${d.date}: ${d.requests} requests, $${d.cost.toFixed(4)}`}
                      />
                    );
                  })}
                </div>
              ) : (
                <div className="flex items-center justify-center h-40">
                  <p className="text-sm text-muted-foreground">No daily data yet</p>
                </div>
              )}
              {usage.by_day?.length > 0 && (
                <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                  <span>{usage.by_day[0]?.date}</span>
                  <span>{usage.by_day[usage.by_day.length - 1]?.date}</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* No usage yet — CTA */}
      {!loading && usage && usage.total_requests === 0 && providers.length > 0 && (
        <Card className="border-dashed border-violet-500/30 bg-violet-500/5">
          <CardContent className="py-6">
            <div className="flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left">
              <div className="text-4xl">🧪</div>
              <div className="flex-1">
                <h3 className="font-semibold">No API usage yet</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Test your models in the Playground, or integrate the Gateway API into your apps.
                </p>
              </div>
              <div className="flex gap-2">
                <Link href="/playground">
                  <button className="px-4 py-2 text-sm font-medium rounded-lg bg-violet-600 text-white hover:bg-violet-700">
                    Open Playground
                  </button>
                </Link>
                <Link href="/gateway">
                  <button className="px-4 py-2 text-sm font-medium rounded-lg border border-border hover:bg-accent">
                    Gateway Docs
                  </button>
                </Link>
              </div>
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
                  className="flex items-center justify-between rounded-lg border border-border p-3 hover:bg-accent/30 transition-colors min-h-[60px] touch-manipulation"
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
