"use client";

import { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ErrorBanner } from "@/components/ui/error-banner";
import { apiRequest } from "@/lib/auth";
import {
  UserPlus,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Copy,
  Check,
  Mail,
  Building2,
  FileText,
} from "lucide-react";

interface AccessRequest {
  id: string;
  email: string;
  name: string;
  company: string | null;
  use_case: string | null;
  status: string;
  invite_code: string | null;
  created_at: string | null;
  processed_at: string | null;
  processed_by: string | null;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  approved: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  denied: "bg-red-500/15 text-red-400 border-red-500/30",
  redeemed: "bg-violet-500/15 text-violet-400 border-violet-500/30",
};

const STATUS_ICONS: Record<string, typeof Clock> = {
  pending: Clock,
  approved: CheckCircle2,
  denied: XCircle,
  redeemed: UserPlus,
};

export default function AccessRequestsPage() {
  const [requests, setRequests] = useState<AccessRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [processing, setProcessing] = useState<string | null>(null);
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [expandedUseCase, setExpandedUseCase] = useState<string | null>(null);

  const fetchRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest("/api/admin/access-requests");
      if (!res.ok) throw new Error("Failed to load access requests");
      const data = await res.json();
      setRequests(data);
    } catch (e: any) {
      setError(e.message || "Failed to load access requests");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const filteredRequests = useMemo(() => {
    let filtered = requests;
    if (statusFilter !== "all") {
      filtered = filtered.filter((r) => r.status === statusFilter);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      filtered = filtered.filter(
        (r) =>
          r.email.toLowerCase().includes(q) ||
          r.name.toLowerCase().includes(q) ||
          (r.company && r.company.toLowerCase().includes(q))
      );
    }
    return filtered;
  }, [requests, search, statusFilter]);

  const counts = useMemo(() => {
    const c = { pending: 0, approved: 0, denied: 0, redeemed: 0 };
    requests.forEach((r) => {
      if (r.status in c) c[r.status as keyof typeof c]++;
    });
    return c;
  }, [requests]);

  const handleProcess = async (requestId: string, action: "approve" | "deny") => {
    setProcessing(requestId);
    try {
      const res = await apiRequest(`/api/admin/access-requests/${requestId}`, {
        method: "PATCH",
        body: JSON.stringify({ action }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Failed to ${action} request`);
      }
      await fetchRequests();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setProcessing(null);
    }
  };

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Access Requests"
        description={`${counts.pending} pending · ${counts.approved} approved · ${counts.redeemed} redeemed · ${counts.denied} denied`}
        breadcrumbs={[
          { label: "Admin", href: "/admin/system" },
          { label: "Access Requests" },
        ]}
      />

      {error && <ErrorBanner message={error} onRetry={fetchRequests} />}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by email, name, or company..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-md border border-border bg-card pl-10 pr-4 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-violet-500/40 transition-shadow"
          />
        </div>
        <div className="flex gap-1.5">
          {["all", "pending", "approved", "redeemed", "denied"].map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                statusFilter === s
                  ? "bg-violet-600 text-white"
                  : "bg-card border border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
              {s !== "all" && ` (${counts[s as keyof typeof counts] || 0})`}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <LoadingDots />
        </div>
      ) : filteredRequests.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <UserPlus className="h-12 w-12 mx-auto text-muted-foreground/40 mb-4" />
            <p className="text-muted-foreground">
              {search || statusFilter !== "all"
                ? "No requests match your filters."
                : "No access requests yet."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredRequests.map((req, i) => {
            const StatusIcon = STATUS_ICONS[req.status] || Clock;
            return (
              <motion.div
                key={req.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <Card className="overflow-hidden">
                  <CardContent className="p-4">
                    <div className="flex flex-col md:flex-row md:items-center gap-4">
                      {/* Avatar + Info */}
                      <div className="flex items-start gap-3 flex-1 min-w-0">
                        <div className="h-10 w-10 rounded-full bg-violet-600 flex items-center justify-center text-sm font-bold text-white shrink-0">
                          {req.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-medium">{req.name}</span>
                            <Badge
                              className={`text-[10px] ${STATUS_STYLES[req.status] || ""}`}
                            >
                              <StatusIcon className="h-3 w-3 mr-1" />
                              {req.status}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <Mail className="h-3 w-3 text-muted-foreground" />
                            <span className="text-sm text-muted-foreground truncate">
                              {req.email}
                            </span>
                          </div>
                          {req.company && (
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <Building2 className="h-3 w-3 text-muted-foreground" />
                              <span className="text-sm text-muted-foreground">
                                {req.company}
                              </span>
                            </div>
                          )}
                          {req.use_case && (
                            <button
                              onClick={() =>
                                setExpandedUseCase(
                                  expandedUseCase === req.id ? null : req.id
                                )
                              }
                              className="flex items-center gap-1.5 mt-1 text-xs text-violet-400 hover:text-violet-300 transition-colors"
                            >
                              <FileText className="h-3 w-3" />
                              {expandedUseCase === req.id
                                ? "Hide use case"
                                : "Show use case"}
                            </button>
                          )}
                          <AnimatePresence>
                            {expandedUseCase === req.id && req.use_case && (
                              <motion.p
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: "auto", opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="text-sm text-muted-foreground mt-2 bg-accent/30 rounded-md p-3 overflow-hidden"
                              >
                                {req.use_case}
                              </motion.p>
                            )}
                          </AnimatePresence>
                          <span className="text-xs text-muted-foreground/60 mt-1 block">
                            Submitted {formatDate(req.created_at)}
                            {req.processed_at &&
                              ` · Processed ${formatDate(req.processed_at)}`}
                          </span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 shrink-0">
                        {req.status === "pending" && (
                          <>
                            <button
                              onClick={() => handleProcess(req.id, "approve")}
                              disabled={processing === req.id}
                              className="px-3 py-1.5 text-sm font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                            >
                              {processing === req.id ? "..." : "Approve"}
                            </button>
                            <button
                              onClick={() => handleProcess(req.id, "deny")}
                              disabled={processing === req.id}
                              className="px-3 py-1.5 text-sm font-medium rounded-md border border-border text-muted-foreground hover:text-red-400 hover:border-red-500/30 disabled:opacity-50 transition-colors"
                            >
                              Deny
                            </button>
                          </>
                        )}
                        {req.status === "approved" && req.invite_code && (
                          <div className="flex items-center gap-2">
                            <code className="px-2.5 py-1 rounded-md bg-accent/50 text-sm font-mono text-emerald-400">
                              {req.invite_code}
                            </code>
                            <button
                              onClick={() => handleCopyCode(req.invite_code!)}
                              className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                              title="Copy invite code"
                            >
                              {copiedCode === req.invite_code ? (
                                <Check className="h-4 w-4 text-emerald-400" />
                              ) : (
                                <Copy className="h-4 w-4" />
                              )}
                            </button>
                          </div>
                        )}
                        {req.status === "redeemed" && (
                          <span className="text-xs text-violet-400">Registered</span>
                        )}
                        {req.status === "denied" && (
                          <span className="text-xs text-red-400">Denied</span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
