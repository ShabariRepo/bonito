"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ErrorBanner } from "@/components/ui/error-banner";
import { apiRequest } from "@/lib/auth";
import {
  Server,
  Building2,
  UsersRound,
  Activity,
  DollarSign,
  TrendingUp,
  Zap,
} from "lucide-react";

interface PlatformStats {
  total_orgs: number;
  total_users: number;
  total_requests: number;
  total_cost: number;
  requests_by_day: Array<{ date: string; requests: number; cost: number }>;
  active_orgs: Array<{ id: string; name: string; recent_requests: number }>;
}

export default function AdminSystemPage() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest("/api/admin/stats");
      if (!res.ok) throw new Error("Failed to load platform stats");
      const data = await res.json();
      setStats(data);
    } catch (e: any) {
      setError(e.message || "Failed to load stats");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  const statCards = stats
    ? [
        {
          label: "Total Organizations",
          value: stats.total_orgs.toLocaleString(),
          icon: Building2,
          color: "text-violet-500",
          bg: "bg-violet-500/15",
        },
        {
          label: "Total Users",
          value: stats.total_users.toLocaleString(),
          icon: UsersRound,
          color: "text-blue-500",
          bg: "bg-blue-500/15",
        },
        {
          label: "Total Gateway Requests",
          value: stats.total_requests.toLocaleString(),
          icon: Activity,
          color: "text-cyan-500",
          bg: "bg-cyan-500/15",
        },
        {
          label: "Total Cost",
          value: `$${stats.total_cost.toFixed(4)}`,
          icon: DollarSign,
          color: "text-emerald-500",
          bg: "bg-emerald-500/15",
        },
      ]
    : [];

  const maxDailyRequests =
    stats?.requests_by_day
      ? Math.max(...stats.requests_by_day.map((d) => d.requests), 1)
      : 1;

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Overview"
        description="Platform-wide statistics and health"
        breadcrumbs={[
          { label: "Admin", href: "/admin/system" },
          { label: "System" },
        ]}
      />

      {error && <ErrorBanner message={error} onRetry={fetchStats} />}

      {loading ? (
        <div className="flex justify-center py-20">
          <LoadingDots />
        </div>
      ) : stats ? (
        <>
          {/* Stats cards */}
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            {statCards.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {stat.label}
                    </CardTitle>
                    <div className={`h-8 w-8 rounded-lg ${stat.bg} flex items-center justify-center`}>
                      <stat.icon className={`h-4 w-4 ${stat.color}`} />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stat.value}</div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          {/* Charts row */}
          <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
            {/* Requests per day chart */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-violet-500" />
                    Requests Per Day (Last 30 Days)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {stats.requests_by_day.length > 0 ? (
                    <>
                      <div className="flex items-end gap-1 h-48">
                        {stats.requests_by_day.map((day, i) => {
                          const pct = (day.requests / maxDailyRequests) * 100;
                          return (
                            <motion.div
                              key={day.date}
                              initial={{ height: 0 }}
                              animate={{ height: `${Math.max(pct, 2)}%` }}
                              transition={{ delay: 0.5 + i * 0.02, duration: 0.4 }}
                              className="flex-1 bg-violet-500/80 rounded-t hover:bg-violet-400 transition-colors cursor-default min-w-[3px]"
                              title={`${day.date}: ${day.requests} requests, $${day.cost.toFixed(4)}`}
                            />
                          );
                        })}
                      </div>
                      <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                        <span>{stats.requests_by_day[0]?.date}</span>
                        <span>{stats.requests_by_day[stats.requests_by_day.length - 1]?.date}</span>
                      </div>
                    </>
                  ) : (
                    <div className="flex items-center justify-center h-48">
                      <p className="text-sm text-muted-foreground">No request data yet</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Active orgs */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-amber-500" />
                    Active Organizations (Last 7 Days)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {stats.active_orgs.length > 0 ? (
                    <div className="space-y-3">
                      {stats.active_orgs.map((org, i) => {
                        const maxReqs = Math.max(
                          ...stats.active_orgs.map((o) => o.recent_requests),
                          1
                        );
                        const pct = (org.recent_requests / maxReqs) * 100;
                        return (
                          <motion.div
                            key={org.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.6 + i * 0.05 }}
                          >
                            <div className="flex items-center justify-between text-sm mb-1">
                              <div className="flex items-center gap-2">
                                <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
                                <span className="font-medium truncate max-w-[200px]">{org.name}</span>
                              </div>
                              <span className="text-muted-foreground">
                                {org.recent_requests.toLocaleString()} requests
                              </span>
                            </div>
                            <div className="h-2 rounded-full bg-accent overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${pct}%` }}
                                transition={{ delay: 0.7 + i * 0.05, duration: 0.5 }}
                                className="h-full rounded-full bg-amber-500"
                              />
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <Server className="h-10 w-10 text-muted-foreground/30 mb-3" />
                      <p className="text-sm text-muted-foreground">No active organizations in the last 7 days</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </>
      ) : null}
    </div>
  );
}
