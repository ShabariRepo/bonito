"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ScrollText, Download, ChevronDown, ChevronRight, Filter, Search, X } from "lucide-react";
import { API_URL } from "@/lib/utils";

const ACTION_STYLES: Record<string, { color: string; bg: string; label: string }> = {
  create: { color: "text-emerald-400", bg: "bg-emerald-500/15", label: "Created" },
  update: { color: "text-blue-400", bg: "bg-blue-500/15", label: "Updated" },
  delete: { color: "text-red-400", bg: "bg-red-500/15", label: "Deleted" },
  access: { color: "text-gray-400", bg: "bg-gray-500/15", label: "Accessed" },
};

function ActionBadge({ action }: { action: string }) {
  const style = ACTION_STYLES[action] || ACTION_STYLES.access;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${style.color} ${style.bg}`}>
      {style.label}
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
  return d.toLocaleDateString();
}

export default function AuditPage() {
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [filterAction, setFilterAction] = useState("");
  const [filterUser, setFilterUser] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const fetchLogs = useCallback(async (p: number, append: boolean = false) => {
    if (p === 1) setLoading(true); else setLoadingMore(true);
    try {
      const params = new URLSearchParams({ page: String(p), page_size: "20" });
      if (filterAction) params.set("action", filterAction);
      if (filterUser) params.set("user_name", filterUser);
      const res = await fetch(`${API_URL}/api/audit/?${params}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(prev => append ? [...prev, ...data.items] : data.items);
        setTotal(data.total);
      }
    } catch {} finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [filterAction, filterUser]);

  useEffect(() => { setPage(1); fetchLogs(1); }, [fetchLogs]);

  const loadMore = () => {
    const next = page + 1;
    setPage(next);
    fetchLogs(next, true);
  };

  const exportCSV = () => {
    const rows = [["Time", "User", "Action", "Resource", "Details"],
      ...logs.map(l => [l.created_at, l.user_name, l.action, l.resource_type, JSON.stringify(l.details_json)])
    ];
    const csv = rows.map(r => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "bonito-audit.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Log"
        description="Complete activity history across your platform"
        actions={
          <div className="flex gap-2">
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
              onClick={exportCSV}
              className="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <Download className="h-4 w-4" />
              Export
            </motion.button>
          </div>
        }
      />

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
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">Action:</span>
                  <div className="flex gap-1">
                    {["", "create", "update", "delete", "access"].map((a) => (
                      <button
                        key={a}
                        onClick={() => setFilterAction(a)}
                        className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                          filterAction === a ? "bg-violet-600 text-white" : "text-muted-foreground hover:text-foreground bg-accent"
                        }`}
                      >
                        {a || "All"}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">User:</span>
                  <div className="relative">
                    <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                    <input
                      type="text"
                      value={filterUser}
                      onChange={(e) => setFilterUser(e.target.value)}
                      placeholder="Search by name..."
                      className="rounded-md border border-border bg-background pl-7 pr-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 w-40"
                    />
                    {filterUser && (
                      <button onClick={() => setFilterUser("")} className="absolute right-1.5 top-1/2 -translate-y-1/2">
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
        {logs.map((log, i) => (
          <motion.div
            key={log.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.03, 0.5) }}
          >
            <Card
              className="hover:border-violet-500/15 transition-colors cursor-pointer"
              onClick={() => setExpanded(expanded === log.id ? null : log.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <motion.div animate={{ rotate: expanded === log.id ? 90 : 0 }} className="text-muted-foreground">
                      <ChevronRight className="h-4 w-4" />
                    </motion.div>
                    <ActionBadge action={log.action} />
                    <span className="text-sm">
                      <span className="font-medium">{log.user_name}</span>
                      <span className="text-muted-foreground"> {log.action}d </span>
                      <span className="font-medium">{log.resource_type}</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="font-mono">{log.ip_address}</span>
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
                      <div className="mt-3 ml-7 rounded-md bg-accent/50 p-3">
                        <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono">
                          {JSON.stringify(log.details_json, null, 2)}
                        </pre>
                        <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
                          <span>Resource ID: {log.resource_id}</span>
                          <span>User: {log.user_id}</span>
                        </div>
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
            {loadingMore ? <LoadingDots size="sm" /> : <>Load More<ChevronDown className="h-4 w-4" /></>}
          </motion.button>
        </div>
      )}
    </div>
  );
}
