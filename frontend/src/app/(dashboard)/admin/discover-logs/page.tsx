"use client";

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ErrorBanner } from "@/components/ui/error-banner";
import { apiRequest } from "@/lib/auth";
import {
  Sparkles,
  Search,
  Globe,
  Building2,
  ThumbsUp,
  ExternalLink,
} from "lucide-react";

interface DiscoverLog {
  id: string;
  result_id: string;
  company_name: string;
  website_url: string | null;
  industry: string | null;
  company_size: string | null;
  recommended_plan: string | null;
  thumbs_up: boolean;
  client_ip: string;
  created_at: string | null;
}

const PLAN_STYLES: Record<string, string> = {
  free: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  pro: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  enterprise: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  scale: "bg-rose-500/15 text-rose-400 border-rose-500/30",
};

export default function DiscoverLogsPage() {
  const [logs, setLogs] = useState<DiscoverLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchLogs();
  }, []);

  async function fetchLogs() {
    try {
      setLoading(true);
      const res = await apiRequest("/api/admin/discover-logs?limit=100");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setLogs(data.logs || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err.message || "Failed to load discover logs");
    } finally {
      setLoading(false);
    }
  }

  const filtered = logs.filter((log) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      log.company_name.toLowerCase().includes(q) ||
      (log.website_url && log.website_url.toLowerCase().includes(q)) ||
      (log.industry && log.industry.toLowerCase().includes(q))
    );
  });

  if (loading) return <LoadingDots />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Discover Logs"
        description={`${total} total searches`}
      />

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#555]" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter by company, URL, or industry..."
          className="w-full pl-10 pr-4 py-2.5 bg-[#111] border border-[#222] rounded-lg text-sm text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:border-[#7c3aed]/50"
        />
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-[#111] border-[#1a1a1a]">
          <CardContent className="p-4">
            <p className="text-xs text-[#666] uppercase tracking-wider">Total</p>
            <p className="text-2xl font-bold text-[#f5f0e8] mt-1">{total}</p>
          </CardContent>
        </Card>
        <Card className="bg-[#111] border-[#1a1a1a]">
          <CardContent className="p-4">
            <p className="text-xs text-[#666] uppercase tracking-wider">Thumbs Up</p>
            <p className="text-2xl font-bold text-emerald-400 mt-1">
              {logs.filter((l) => l.thumbs_up).length}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-[#111] border-[#1a1a1a]">
          <CardContent className="p-4">
            <p className="text-xs text-[#666] uppercase tracking-wider">Enterprise+</p>
            <p className="text-2xl font-bold text-amber-400 mt-1">
              {logs.filter((l) => l.recommended_plan === "enterprise" || l.recommended_plan === "scale").length}
            </p>
          </CardContent>
        </Card>
        <Card className="bg-[#111] border-[#1a1a1a]">
          <CardContent className="p-4">
            <p className="text-xs text-[#666] uppercase tracking-wider">Unique IPs</p>
            <p className="text-2xl font-bold text-[#a78bfa] mt-1">
              {new Set(logs.map((l) => l.client_ip)).size}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-[#1a1a1a]">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[#1a1a1a] bg-[#0a0a0a]">
              <th className="text-left p-3 text-[#666] font-medium">Company</th>
              <th className="text-left p-3 text-[#666] font-medium">Industry</th>
              <th className="text-left p-3 text-[#666] font-medium">Size</th>
              <th className="text-left p-3 text-[#666] font-medium">Plan</th>
              <th className="text-left p-3 text-[#666] font-medium">Feedback</th>
              <th className="text-left p-3 text-[#666] font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((log) => (
              <tr
                key={log.id}
                className="border-b border-[#111] hover:bg-[#111]/50 transition"
              >
                <td className="p-3">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-[#f5f0e8] font-medium">{log.company_name}</span>
                    {log.website_url && (
                      <a
                        href={log.website_url.startsWith("http") ? log.website_url : `https://${log.website_url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-[#555] hover:text-[#7c3aed] flex items-center gap-1"
                      >
                        <Globe className="w-3 h-3" />
                        {log.website_url.replace(/^https?:\/\/(www\.)?/, "").slice(0, 30)}
                        <ExternalLink className="w-2.5 h-2.5" />
                      </a>
                    )}
                  </div>
                </td>
                <td className="p-3 text-[#888]">{log.industry || "—"}</td>
                <td className="p-3 text-[#888] capitalize">{log.company_size || "—"}</td>
                <td className="p-3">
                  {log.recommended_plan && (
                    <Badge
                      variant="outline"
                      className={`text-xs capitalize ${PLAN_STYLES[log.recommended_plan] || ""}`}
                    >
                      {log.recommended_plan}
                    </Badge>
                  )}
                </td>
                <td className="p-3">
                  {log.thumbs_up && (
                    <ThumbsUp className="w-4 h-4 text-emerald-400" />
                  )}
                </td>
                <td className="p-3 text-[#555] text-xs">
                  {log.created_at
                    ? new Date(log.created_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "—"}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="p-8 text-center text-[#555]">
                  {search ? "No results match your search" : "No discover searches yet"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
