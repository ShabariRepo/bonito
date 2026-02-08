"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "@/components/ui/status-badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { Box, Cloud, Rocket, Activity, TrendingUp, Zap, Plus, ArrowRight } from "lucide-react";
import { API_URL } from "@/lib/utils";
import Link from "next/link";
import { useRouter } from "next/navigation";

function AnimatedCounter({ value, duration = 1 }: { value: number; duration?: number }) {
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

  return <span ref={ref}>{count}</span>;
}

const staticStats = [
  { name: "Active Deployments", value: 8, display: "8", icon: Rocket, color: "text-emerald-500" },
  { name: "API Requests (24h)", value: 12400, display: "12.4K", icon: Activity, color: "text-amber-500" },
];

const recentActivity = [
  { action: "Connected", target: "AWS Bedrock", time: "2 hours ago", type: "provider" },
  { action: "Deployed", target: "GPT-4o", time: "5 hours ago", type: "deployment" },
  { action: "Connected", target: "Azure OpenAI", time: "1 day ago", type: "provider" },
  { action: "Model refresh", target: "GCP Vertex AI", time: "2 days ago", type: "provider" },
  { action: "Deployed", target: "Claude 3.5 Sonnet", time: "3 days ago", type: "deployment" },
];

export default function DashboardPage() {
  const router = useRouter();
  const [providerCount, setProviderCount] = useState<number | null>(null);
  const [modelCount, setModelCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch(`${API_URL}/api/providers/`);
        if (res.ok) {
          const providers = await res.json();
          setProviderCount(providers.length);
          const totalModels = providers.reduce((sum: number, p: any) => sum + (p.model_count || 0), 0);
          setModelCount(totalModels);
          if (providers.length === 0) {
            router.replace("/onboarding");
            return;
          }
        }
      } catch {
        setProviderCount(0);
        setModelCount(0);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, [router]);

  const stats = [
    { name: "Connected Providers", value: providerCount ?? 0, icon: Cloud, color: "text-blue-500", href: "/providers" },
    { name: "Available Models", value: modelCount ?? 0, icon: Box, color: "text-violet-500", href: "/models" },
    ...staticStats,
  ];

  return (
    <div className="space-y-8">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Overview of your AI infrastructure</p>
      </motion.div>

      {/* Stats grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card className="hover:border-violet-500/30 transition-colors">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{stat.name}</CardTitle>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {loading && i < 2 ? <LoadingDots size="sm" /> : (
                    typeof stat.value === "number" ? <AnimatedCounter value={stat.value} /> : stat.value
                  )}
                </div>
              </CardContent>
            </Card>
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

      {/* Recent activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-violet-500" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentActivity.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.08 }}
                className="flex items-center justify-between rounded-lg border border-border p-3 hover:bg-accent/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent">
                    {item.type === "provider" ? <Cloud className="h-4 w-4 text-blue-400" /> : <Rocket className="h-4 w-4 text-violet-400" />}
                  </div>
                  <div>
                    <p className="text-sm font-medium">
                      <span className="text-muted-foreground">{item.action}</span>{" "}
                      {item.target}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-muted-foreground">{item.time}</span>
              </motion.div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
