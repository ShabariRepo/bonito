"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  Activity,
  DollarSign,
  Zap,
  Clock,
  TrendingUp,
  Filter,
  Calendar,
  Download,
  BarChart3,
} from "lucide-react";
import { apiRequest } from "@/lib/auth";

/* ─── Types ─── */

interface UsageStats {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number;
  by_model: { model: string; requests: number; cost: number; tokens: number }[];
  by_day: { date: string; requests: number; cost: number }[];
}

interface LogEntry {
  id: string;
  model_requested: string;
  model_used: string | null;
  provider: string | null;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  latency_ms: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

/* ─── Chart Components ─── */

function UsageChart({ data }: { data: { date: string; requests: number; cost: number }[] }) {
  if (!data || data.length === 0) return <div className="h-64 flex items-center justify-center text-muted-foreground">No data available</div>;

  const maxRequests = Math.max(...data.map(d => d.requests));
  const maxCost = Math.max(...data.map(d => d.cost));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-500">{data.reduce((acc, d) => acc + d.requests, 0).toLocaleString()}</div>
          <div className="text-sm text-muted-foreground">Total Requests</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-violet-500">${data.reduce((acc, d) => acc + d.cost, 0).toFixed(4)}</div>
          <div className="text-sm text-muted-foreground">Total Cost</div>
        </div>
      </div>
      
      <div className="space-y-3">
        {data.map((day, index) => (
          <div key={day.date} className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{new Date(day.date).toLocaleDateString()}</span>
              <span className="text-muted-foreground">{day.requests} requests • ${day.cost.toFixed(4)}</span>
            </div>
            <div className="space-y-1">
              <div className="h-2 bg-accent rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(day.requests / maxRequests) * 100}%` }}
                  transition={{ duration: 0.8, delay: index * 0.1 }}
                  className="h-full bg-blue-500"
                />
              </div>
              <div className="h-1 bg-accent rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(day.cost / maxCost) * 100}%` }}
                  transition={{ duration: 0.8, delay: index * 0.1 + 0.2 }}
                  className="h-full bg-violet-500"
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ModelBreakdown({ data }: { data: { model: string; requests: number; cost: number; tokens: number }[] }) {
  if (!data || data.length === 0) return <div className="text-center text-muted-foreground py-8">No model usage data</div>;

  const sortedData = [...data].sort((a, b) => b.cost - a.cost);
  const maxCost = Math.max(...sortedData.map(d => d.cost));

  return (
    <div className="space-y-4">
      {sortedData.map((model, index) => (
        <motion.div
          key={model.model}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
          className="p-4 bg-accent/30 rounded-lg"
        >
          <div className="flex items-center justify-between mb-2">
            <code className="text-sm font-mono font-semibold">{model.model}</code>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-xs">
                {model.requests.toLocaleString()} req
              </Badge>
              <Badge variant="outline" className="text-xs">
                {model.tokens.toLocaleString()} tok
              </Badge>
              <Badge className="bg-violet-600 text-xs">
                ${model.cost.toFixed(6)}
              </Badge>
            </div>
          </div>
          <div className="h-2 bg-accent rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(model.cost / maxCost) * 100}%` }}
              transition={{ duration: 0.8, delay: index * 0.1 }}
              className="h-full bg-gradient-to-r from-violet-600 to-violet-400"
            />
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>{((model.cost / maxCost) * 100).toFixed(1)}% of total cost</span>
            <span>{(model.cost / model.requests).toFixed(6)} per request</span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

/* ─── Latency Insights ─── */

function LatencyInsights({ logs }: { logs: LogEntry[] }) {
  if (!logs || logs.length === 0) return null;

  const latencies = logs.map(log => log.latency_ms);
  const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;
  const p50 = latencies.sort((a, b) => a - b)[Math.floor(latencies.length * 0.5)];
  const p95 = latencies.sort((a, b) => a - b)[Math.floor(latencies.length * 0.95)];
  const p99 = latencies.sort((a, b) => a - b)[Math.floor(latencies.length * 0.99)];

  const errorRate = (logs.filter(log => log.status === "error").length / logs.length) * 100;

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <div className="text-center">
        <div className="text-lg font-bold text-blue-500">{avg.toFixed(0)}ms</div>
        <div className="text-xs text-muted-foreground">Average</div>
      </div>
      <div className="text-center">
        <div className="text-lg font-bold text-green-500">{p50}ms</div>
        <div className="text-xs text-muted-foreground">P50</div>
      </div>
      <div className="text-center">
        <div className="text-lg font-bold text-yellow-500">{p95}ms</div>
        <div className="text-xs text-muted-foreground">P95</div>
      </div>
      <div className="text-center">
        <div className="text-lg font-bold text-orange-500">{p99}ms</div>
        <div className="text-xs text-muted-foreground">P99</div>
      </div>
      <div className="text-center">
        <div className={`text-lg font-bold ${errorRate > 5 ? 'text-red-500' : errorRate > 1 ? 'text-yellow-500' : 'text-green-500'}`}>
          {errorRate.toFixed(1)}%
        </div>
        <div className="text-xs text-muted-foreground">Error Rate</div>
      </div>
    </div>
  );
}

/* ─── Main Page ─── */

export default function GatewayUsagePage() {
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState("30");
  const [selectedModel, setSelectedModel] = useState<string>("");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [usageRes, logsRes] = await Promise.all([
        apiRequest(`/api/gateway/usage?days=${timeRange}`),
        apiRequest(`/api/gateway/logs?limit=1000${selectedModel ? `&model=${selectedModel}` : ''}`),
      ]);
      if (usageRes.ok) setUsage(await usageRes.json());
      if (logsRes.ok) setLogs(await logsRes.json());
    } catch (e) {
      console.error("Failed to fetch usage data:", e);
    } finally {
      setLoading(false);
    }
  }, [timeRange, selectedModel]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const exportData = async () => {
    try {
      const res = await apiRequest("/api/gateway/logs?limit=10000");
      if (res.ok) {
        const logs = await res.json();
        const csvContent = [
          ["Date", "Model", "Provider", "Input Tokens", "Output Tokens", "Cost", "Latency", "Status"].join(","),
          ...logs.map((log: LogEntry) => [
            log.created_at,
            log.model_requested,
            log.provider || "",
            log.input_tokens,
            log.output_tokens,
            log.cost,
            log.latency_ms,
            log.status
          ].join(","))
        ].join("\n");

        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `gateway-usage-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error("Export failed:", e);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingDots />
      </div>
    );
  }

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      <PageHeader
        title="Usage Analytics"
        description="Detailed analysis of API gateway usage, costs, and performance metrics."
        actions={
          <div className="flex gap-2">
            <button
              onClick={exportData}
              className="flex items-center gap-2 px-4 py-2 border border-border rounded-lg hover:bg-accent transition-colors"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
          </div>
        }
      />

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="bg-accent border border-border rounded px-3 py-1 text-sm"
              >
                <option value="7">Last 7 days</option>
                <option value="30">Last 30 days</option>
                <option value="90">Last 90 days</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="bg-accent border border-border rounded px-3 py-1 text-sm"
              >
                <option value="">All Models</option>
                {usage?.by_model?.map(model => (
                  <option key={model.model} value={model.model}>{model.model}</option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { 
            label: "Total Requests", 
            value: usage?.total_requests?.toLocaleString() ?? "0", 
            icon: Activity, 
            color: "text-blue-500",
            change: "+12%" 
          },
          { 
            label: "Input Tokens", 
            value: (usage?.total_input_tokens ?? 0).toLocaleString(), 
            icon: Zap, 
            color: "text-amber-500",
            change: "+8%" 
          },
          { 
            label: "Output Tokens", 
            value: (usage?.total_output_tokens ?? 0).toLocaleString(), 
            icon: Zap, 
            color: "text-green-500",
            change: "+15%" 
          },
          { 
            label: "Total Cost", 
            value: `$${(usage?.total_cost ?? 0).toFixed(4)}`, 
            icon: DollarSign, 
            color: "text-violet-500",
            change: "+5%" 
          },
        ].map((stat, index) => (
          <motion.div 
            key={stat.label} 
            initial={{ opacity: 0, y: 20 }} 
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    <p className="text-2xl font-bold mt-1">{stat.value}</p>
                    <div className="flex items-center gap-1 mt-1">
                      <TrendingUp className="h-3 w-3 text-green-500" />
                      <span className="text-xs text-green-500">{stat.change}</span>
                    </div>
                  </div>
                  <stat.icon className={`h-8 w-8 ${stat.color} opacity-50`} />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Performance Metrics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Clock className="h-4 w-4" />
            Performance Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          <LatencyInsights logs={logs} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Usage Over Time */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BarChart3 className="h-4 w-4" />
              Usage Over Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <UsageChart data={usage?.by_day || []} />
          </CardContent>
        </Card>

        {/* Model Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Activity className="h-4 w-4" />
              Usage by Model
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ModelBreakdown data={usage?.by_model || []} />
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Clock className="h-4 w-4" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <p className="text-center text-muted-foreground py-8">No recent activity</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 font-medium">Time</th>
                    <th className="pb-2 font-medium">Model</th>
                    <th className="pb-2 font-medium">Provider</th>
                    <th className="pb-2 font-medium">Tokens</th>
                    <th className="pb-2 font-medium">Cost</th>
                    <th className="pb-2 font-medium">Latency</th>
                    <th className="pb-2 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.slice(0, 20).map((log) => (
                    <tr key={log.id} className="border-b border-border/50 hover:bg-accent/30">
                      <td className="py-2 text-xs">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </td>
                      <td className="py-2 font-mono text-xs">{log.model_requested}</td>
                      <td className="py-2">
                        {log.provider && <Badge variant="outline" className="text-xs">{log.provider}</Badge>}
                      </td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {(log.input_tokens + log.output_tokens).toLocaleString()}
                      </td>
                      <td className="py-2 text-xs text-violet-500">${log.cost.toFixed(6)}</td>
                      <td className="py-2 text-xs text-muted-foreground">{log.latency_ms}ms</td>
                      <td className="py-2">
                        <Badge
                          variant={log.status === "success" ? "secondary" : "destructive"}
                          className="text-xs"
                        >
                          {log.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}