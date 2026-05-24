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
  Bot,
  HeartPulse,
  AlertTriangle,
  XCircle,
  CheckCircle,
  Search,
  Filter,
} from "lucide-react";

interface AgentHealth {
  id: string;
  name: string;
  org_id: string;
  org_name: string;
  project_name: string;
  model_id: string;
  model_health: "ok" | "deprecated" | "no_route" | "warning";
  health_detail: string;
  status: string;
  total_runs: number;
  total_cost: number;
  last_active_at: string | null;
  created_at: string | null;
}

interface HealthSummary {
  total_agents: number;
  healthy: number;
  deprecated: number;
  no_route: number;
}

interface AgentHealthResponse {
  agents: AgentHealth[];
  summary: HealthSummary;
}

const healthBadge = (health: string) => {
  switch (health) {
    case "ok":
      return <Badge className="bg-emerald-500/20 text-emerald-400 border-emerald-500/30"><CheckCircle className="h-3 w-3 mr-1" />Healthy</Badge>;
    case "deprecated":
      return <Badge className="bg-red-500/20 text-red-400 border-red-500/30"><XCircle className="h-3 w-3 mr-1" />Deprecated</Badge>;
    case "no_route":
      return <Badge className="bg-orange-500/20 text-orange-400 border-orange-500/30"><AlertTriangle className="h-3 w-3 mr-1" />No Route</Badge>;
    case "warning":
      return <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30"><AlertTriangle className="h-3 w-3 mr-1" />Warning</Badge>;
    default:
      return <Badge variant="outline">{health}</Badge>;
  }
};

export default function AdminAgentHealthPage() {
  const [data, setData] = useState<AgentHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [healthFilter, setHealthFilter] = useState<string>("all");

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest("/api/admin/agent-health");
      if (!res.ok) throw new Error("Failed to load agent health data");
      const json = await res.json();
      setData(json);
    } catch (e: any) {
      setError(e.message || "Failed to load agent health");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const filtered = data?.agents.filter((a) => {
    const matchesSearch =
      !search ||
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.org_name.toLowerCase().includes(search.toLowerCase()) ||
      a.model_id.toLowerCase().includes(search.toLowerCase()) ||
      a.project_name.toLowerCase().includes(search.toLowerCase());
    const matchesHealth = healthFilter === "all" || a.model_health === healthFilter;
    return matchesSearch && matchesHealth;
  }) ?? [];

  const summary = data?.summary;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Agent Health"
        description="Platform-wide agent model health and deprecation monitoring"
        icon={HeartPulse}
      />

      {error && <ErrorBanner message={error} onRetry={fetchHealth} />}

      {loading ? (
        <LoadingDots />
      ) : (
        <>
          {/* Summary Cards */}
          {summary && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4 flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-violet-500/10">
                    <Bot className="h-5 w-5 text-violet-400" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Agents</p>
                    <p className="text-2xl font-bold">{summary.total_agents}</p>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-emerald-500/10">
                    <CheckCircle className="h-5 w-5 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Healthy</p>
                    <p className="text-2xl font-bold text-emerald-400">{summary.healthy}</p>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-red-500/10">
                    <XCircle className="h-5 w-5 text-red-400" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Deprecated</p>
                    <p className="text-2xl font-bold text-red-400">{summary.deprecated}</p>
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-orange-500/10">
                    <AlertTriangle className="h-5 w-5 text-orange-400" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">No Route</p>
                    <p className="text-2xl font-bold text-orange-400">{summary.no_route}</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search agents, orgs, models..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            </div>
            <div className="flex gap-2">
              {["all", "ok", "deprecated", "no_route", "warning"].map((f) => (
                <button
                  key={f}
                  onClick={() => setHealthFilter(f)}
                  className={`px-3 py-2 text-xs font-medium rounded-lg border transition-colors ${
                    healthFilter === f
                      ? "bg-violet-600 border-violet-500 text-white"
                      : "bg-card border-border text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {f === "all" ? "All" : f === "ok" ? "Healthy" : f === "no_route" ? "No Route" : f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Agent Table */}
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground">
                      <th className="px-4 py-3 font-medium">Agent</th>
                      <th className="px-4 py-3 font-medium">Organization</th>
                      <th className="px-4 py-3 font-medium">Project</th>
                      <th className="px-4 py-3 font-medium">Model</th>
                      <th className="px-4 py-3 font-medium">Health</th>
                      <th className="px-4 py-3 font-medium">Runs</th>
                      <th className="px-4 py-3 font-medium">Cost</th>
                      <th className="px-4 py-3 font-medium">Last Active</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="px-4 py-8 text-center text-muted-foreground">
                          {search || healthFilter !== "all"
                            ? "No agents match your filters"
                            : "No agents found"}
                        </td>
                      </tr>
                    ) : (
                      filtered.map((agent, i) => (
                        <motion.tr
                          key={agent.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.02 }}
                          className="border-b border-border/50 hover:bg-accent/30 transition-colors"
                        >
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <Bot className="h-4 w-4 text-violet-400 shrink-0" />
                              <div>
                                <p className="font-medium">{agent.name}</p>
                                <p className="text-xs text-muted-foreground">{agent.status}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">{agent.org_name}</td>
                          <td className="px-4 py-3 text-muted-foreground">{agent.project_name}</td>
                          <td className="px-4 py-3">
                            <code className="text-xs bg-card px-1.5 py-0.5 rounded border border-border">
                              {agent.model_id}
                            </code>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-col gap-1">
                              {healthBadge(agent.model_health)}
                              <span className="text-xs text-muted-foreground">{agent.health_detail}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">{agent.total_runs.toLocaleString()}</td>
                          <td className="px-4 py-3 text-muted-foreground">${agent.total_cost.toFixed(2)}</td>
                          <td className="px-4 py-3 text-muted-foreground text-xs">
                            {agent.last_active_at
                              ? new Date(agent.last_active_at).toLocaleDateString()
                              : "Never"}
                          </td>
                        </motion.tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
