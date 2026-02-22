"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  ScrollText,
  Download,
  ChevronDown,
  ChevronRight,
  Filter,
  Search,
  X,
  BarChart3,
  AlertTriangle,
  Info,
  Bug,
  AlertCircle,
  Flame,
  RefreshCw,
} from "lucide-react";
import { apiRequest } from "@/lib/auth";

// ── Severity Config ──

const SEVERITY_STYLES: Record<string, { color: string; bg: string; icon: any }> = {
  debug: { color: "text-gray-400", bg: "bg-gray-500/15", icon: Bug },
  info: { color: "text-blue-400", bg: "bg-blue-500/15", icon: Info },
  warn: { color: "text-amber-400", bg: "bg-amber-500/15", icon: AlertTriangle },
  error: { color: "text-red-400", bg: "bg-red-500/15", icon: AlertCircle },
  critical: { color: "text-purple-400", bg: "bg-purple-500/15", icon: Flame },
};

const LOG_TYPE_LABELS: Record<string, string> = {
  gateway: "Gateway",
  auth: "Auth",
  agent: "Agents",
  kb: "Knowledge Base",
  admin: "Admin",
  deployment: "Deployments",
  billing: "Billing",
  compliance: "Compliance",
};

function SeverityBadge({ severity }: { severity: string }) {
  const style = SEVERITY_STYLES[severity] || SEVERITY_STYLES.info;
  const Icon = style.icon;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${style.color} ${style.bg}`}>
      <Icon className="h-3 w-3" />
      {severity}
    </span>
  );
}

function LogTypeBadge({ logType }: { logType: string }) {
  return (
    <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium text-violet-400 bg-violet-500/15">
      {LOG_TYPE_LABELS[logType] || logType}
    </span>
  );
}

function formatTime(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diff = (now.getTime() - d.getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString() + " " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Stats Bar ──

function StatsBar({ stats }: { stats: any }) {
  if (!stats) return null;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">Total Logs</p>
          <p className="text-2xl font-bold">{stats.total_logs?.toLocaleString() || 0}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">Errors</p>
          <p className="text-2xl font-bold text-red-400">{stats.total_errors?.toLocaleString() || 0}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">By Type</p>
          <div className="flex flex-wrap gap-1 mt-1">
            {stats.by_type && Object.entries(stats.by_type).slice(0, 3).map(([k, v]) => (
              <span key={k} className="text-xs text-muted-foreground">
                {LOG_TYPE_LABELS[k] || k}: <span className="font-medium text-foreground">{(v as number).toLocaleString()}</span>
              </span>
            ))}
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">By Severity</p>
          <div className="flex flex-wrap gap-1 mt-1">
            {stats.by_severity && Object.entries(stats.by_severity).map(([k, v]) => (
              <span key={k} className={`text-xs ${SEVERITY_STYLES[k]?.color || "text-muted-foreground"}`}>
                {k}: {(v as number).toLocaleString()}
              </span>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ── Main Component ──

export default function LogsPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [stats, setStats] = useState<any>(null);

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [filterLogType, setFilterLogType] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");
  const [filterSearch, setFilterSearch] = useState("");
  const [filterEventType, setFilterEventType] = useState("");

  const fetchLogs = useCallback(async (p: number, append: boolean = false) => {
    if (p === 1) setLoading(true); else setLoadingMore(true);
    try {
      const params = new URLSearchParams({ page: String(p), page_size: "50" });
      if (filterLogType) params.set("log_type", filterLogType);
      if (filterSeverity) params.set("severity", filterSeverity);
      if (filterSearch) params.set("search", filterSearch);
      if (filterEventType) params.set("event_type", filterEventType);
      const res = await apiRequest(`/api/logs?${params}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(prev => append ? [...prev, ...data.items] : data.items);
        setTotal(data.total);
      }
    } catch {} finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [filterLogType, filterSeverity, filterSearch, filterEventType]);

  const fetchStats = useCallback(async () => {
    try {
      const res = await apiRequest("/api/logs/stats?range=7");
      if (res.ok) {
        setStats(await res.json());
      }
    } catch {}
  }, []);

  useEffect(() => { setPage(1); fetchLogs(1); }, [fetchLogs]);
  useEffect(() => { fetchStats(); }, [fetchStats]);

  const loadMore = () => {
    const next = page + 1;
    setPage(next);
    fetchLogs(next, true);
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams({ format: "csv" });
      if (filterLogType) params.set("log_type", filterLogType);
      if (filterSeverity) params.set("severity", filterSeverity);
      const res = await apiRequest(`/api/logs/export?${params}`);
      if (res.ok) {
        const job = await res.json();
        alert(`Export started (job ${job.id}). Status: ${job.status}`);
      }
    } catch {}
  };

  if (loading) return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Platform Logs"
        description="Unified logging across all platform features"
        actions={
          <div className="flex gap-2">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => { setPage(1); fetchLogs(1); fetchStats(); }}
              className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm transition-colors ${
                showFilters ? "border-violet-500 text-violet-400" : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              <Filter className="h-4 w-4" />
              Filters
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleExport}
              className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Download className="h-4 w-4" />
              Export
            </motion.button>
          </div>
        }
      />

      {/* Stats */}
      <StatsBar stats={stats} />

      {/* Filters */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <Card>
              <CardContent className="flex flex-wrap items-center gap-4 p-4">
                {/* Log Type Filter */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Type:</span>
                  <div className="flex gap-1 flex-wrap">
                    {["", "gateway", "auth", "agent", "kb", "admin", "deployment"].map((t) => (
                      <button
                        key={t}
                        onClick={() => setFilterLogType(t)}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                          filterLogType === t ? "bg-violet-600 text-white" : "text-muted-foreground hover:text-foreground bg-accent"
                        }`}
                      >
                        {t ? (LOG_TYPE_LABELS[t] || t) : "All"}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Severity Filter */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Severity:</span>
                  <div className="flex gap-1">
                    {["", "debug", "info", "warn", "error", "critical"].map((s) => (
                      <button
                        key={s}
                        onClick={() => setFilterSeverity(s)}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                          filterSeverity === s ? "bg-violet-600 text-white" : "text-muted-foreground hover:text-foreground bg-accent"
                        }`}
                      >
                        {s || "All"}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Search */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Search:</span>
                  <div className="relative">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <input
                      type="text"
                      value={filterSearch}
                      onChange={(e) => setFilterSearch(e.target.value)}
                      placeholder="Search messages..."
                      className="rounded-md border border-border bg-background pl-7 pr-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 w-48"
                    />
                    {filterSearch && (
                      <button onClick={() => setFilterSearch("")} className="absolute right-1.5 top-1/2 -translate-y-1/2">
                        <X className="h-3.5 w-3.5 text-muted-foreground" />
                      </button>
                    )}
                  </div>
                </div>

                <span className="text-xs text-muted-foreground">{total} entries</span>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Log entries */}
      <div className="space-y-2">
        {logs.length === 0 && (
          <Card>
            <CardContent className="p-12 text-center">
              <ScrollText className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-lg font-medium">No logs found</p>
              <p className="text-sm text-muted-foreground mt-1">
                Logs will appear here as platform events occur.
              </p>
            </CardContent>
          </Card>
        )}

        {logs.map((log, i) => (
          <motion.div
            key={log.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.02, 0.4) }}
          >
            <Card
              className="hover:border-violet-500/15 transition-colors cursor-pointer"
              onClick={() => setExpanded(expanded === log.id ? null : log.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <motion.div animate={{ rotate: expanded === log.id ? 90 : 0 }} className="text-muted-foreground shrink-0">
                      <ChevronRight className="h-4 w-4" />
                    </motion.div>
                    <SeverityBadge severity={log.severity} />
                    <LogTypeBadge logType={log.log_type} />
                    <span className="text-xs font-mono text-muted-foreground">{log.event_type}</span>
                    <span className="text-sm truncate text-muted-foreground">{log.message || "—"}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                    {log.duration_ms != null && (
                      <span className="font-mono">{log.duration_ms}ms</span>
                    )}
                    {log.cost != null && log.cost > 0 && (
                      <span className="font-mono">${log.cost.toFixed(4)}</span>
                    )}
                    <span>{formatTime(log.created_at)}</span>
                  </div>
                </div>

                <AnimatePresence>
                  {expanded === log.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-3 ml-7 rounded-md bg-accent/50 p-3 space-y-2">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                          {log.user_id && <div><span className="text-muted-foreground">User:</span> <span className="font-mono">{log.user_id.substring(0, 8)}...</span></div>}
                          {log.resource_type && <div><span className="text-muted-foreground">Resource:</span> {log.resource_type}</div>}
                          {log.resource_id && <div><span className="text-muted-foreground">Resource ID:</span> <span className="font-mono">{log.resource_id.substring(0, 8)}...</span></div>}
                          {log.action && <div><span className="text-muted-foreground">Action:</span> {log.action}</div>}
                          {log.trace_id && <div><span className="text-muted-foreground">Trace:</span> <span className="font-mono">{log.trace_id.substring(0, 8)}...</span></div>}
                        </div>
                        {log.metadata && Object.keys(log.metadata).length > 0 && (
                          <div>
                            <p className="text-xs font-medium text-muted-foreground mb-1">Metadata</p>
                            <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono bg-background/50 rounded p-2">
                              {JSON.stringify(log.metadata, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Load more */}
      {logs.length < total && (
        <div className="flex justify-center pt-4">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={loadMore}
            disabled={loadingMore}
            className="flex items-center gap-2 rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {loadingMore ? <LoadingDots size="sm" /> : <>Load More <ChevronDown className="h-4 w-4" /></>}
          </motion.button>
        </div>
      )}
    </div>
  );
}
