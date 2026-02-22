"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ErrorBanner } from "@/components/ui/error-banner";
import { apiRequest } from "@/lib/auth";
import {
  Building2,
  Users,
  Cloud,
  Rocket,
  Activity,
  DollarSign,
  Trash2,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  X,
  Crown,
  Sparkles,
} from "lucide-react";

const TIER_COLORS: Record<string, string> = {
  free: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
  pro: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  enterprise: "bg-amber-500/15 text-amber-400 border-amber-500/30",
};

const TIER_OPTIONS = ["free", "pro", "enterprise"] as const;
const BONOBOT_OPTIONS = ["none", "pro", "enterprise"] as const;

interface OrgSummary {
  id: string;
  name: string;
  user_count: number;
  provider_count: number;
  deployment_count: number;
  total_requests: number;
  total_cost: number;
  subscription_tier: string;
  bonobot_plan: string;
  created_at: string | null;
}

interface OrgDetail {
  id: string;
  name: string;
  created_at: string | null;
  users: Array<{
    id: string;
    email: string;
    name: string;
    role: string;
    email_verified: boolean;
    created_at: string | null;
  }>;
  providers: Array<{
    id: string;
    provider_type: string;
    status: string;
    created_at: string | null;
  }>;
  deployments: Array<{
    id: string;
    status: string;
    config: any;
    created_at: string | null;
  }>;
}

export default function AdminOrganizationsPage() {
  const [orgs, setOrgs] = useState<OrgSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedOrg, setExpandedOrg] = useState<string | null>(null);
  const [orgDetail, setOrgDetail] = useState<OrgDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchOrgs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest("/api/admin/organizations");
      if (!res.ok) throw new Error("Failed to load organizations");
      const data = await res.json();
      setOrgs(data);
    } catch (e: any) {
      setError(e.message || "Failed to load organizations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrgs();
  }, []);

  const toggleExpand = async (orgId: string) => {
    if (expandedOrg === orgId) {
      setExpandedOrg(null);
      setOrgDetail(null);
      return;
    }
    setExpandedOrg(orgId);
    setDetailLoading(true);
    try {
      const res = await apiRequest(`/api/admin/organizations/${orgId}`);
      if (!res.ok) throw new Error("Failed to load org details");
      const data = await res.json();
      setOrgDetail(data);
    } catch {
      setOrgDetail(null);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleDelete = async (orgId: string) => {
    setDeleting(true);
    try {
      const res = await apiRequest(`/api/admin/organizations/${orgId}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete organization");
      setOrgs((prev) => prev.filter((o) => o.id !== orgId));
      setDeleteConfirm(null);
      setExpandedOrg(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (iso: string | null) => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Organizations"
        description="Manage all organizations on the platform"
        breadcrumbs={[
          { label: "Admin", href: "/admin/system" },
          { label: "Organizations" },
        ]}
      />

      {error && <ErrorBanner message={error} onRetry={fetchOrgs} />}

      {loading ? (
        <div className="flex justify-center py-20">
          <LoadingDots />
        </div>
      ) : orgs.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Building2 className="h-12 w-12 mx-auto text-muted-foreground/40 mb-4" />
            <p className="text-muted-foreground">No organizations found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {/* Table header */}
          <div className="hidden md:grid grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr_1fr_auto] gap-4 px-4 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            <span>Organization</span>
            <span>Tier</span>
            <span>Users</span>
            <span>Providers</span>
            <span>Deployments</span>
            <span>Requests</span>
            <span>Cost</span>
            <span>Created</span>
            <span></span>
          </div>

          {orgs.map((org, i) => (
            <motion.div
              key={org.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className="overflow-hidden">
                <div
                  className="grid grid-cols-1 md:grid-cols-[2fr_1fr_1fr_1fr_1fr_1fr_1fr_1fr_auto] gap-4 px-4 py-3 items-center cursor-pointer hover:bg-accent/30 transition-colors"
                  onClick={() => toggleExpand(org.id)}
                >
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-lg bg-violet-500/15 flex items-center justify-center shrink-0">
                      <Building2 className="h-4 w-4 text-violet-500" />
                    </div>
                    <span className="font-medium truncate">{org.name}</span>
                  </div>
                  <div>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${TIER_COLORS[org.subscription_tier] || TIER_COLORS.free}`}>
                      {org.subscription_tier === "enterprise" && <Crown className="h-3 w-3" />}
                      {org.subscription_tier === "pro" && <Sparkles className="h-3 w-3" />}
                      {org.subscription_tier?.toUpperCase() || "FREE"}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm">{org.user_count}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Cloud className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm">{org.provider_count}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Rocket className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm">{org.deployment_count}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Activity className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm">{org.total_requests.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <DollarSign className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm">${org.total_cost.toFixed(4)}</span>
                  </div>
                  <span className="text-sm text-muted-foreground">{formatDate(org.created_at)}</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteConfirm(org.id);
                      }}
                      className="p-1.5 rounded-md text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Delete organization"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                    {expandedOrg === org.id ? (
                      <ChevronUp className="h-4 w-4 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground" />
                    )}
                  </div>
                </div>

                {/* Expanded detail */}
                <AnimatePresence>
                  {expandedOrg === org.id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-border px-4 py-4 space-y-4">
                        {detailLoading ? (
                          <div className="flex justify-center py-6">
                            <LoadingDots size="sm" />
                          </div>
                        ) : orgDetail ? (
                          <div className="space-y-4">
                            {/* Tier Management */}
                            <div className="flex flex-wrap items-center gap-4 p-3 rounded-lg bg-accent/20 border border-border">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">Subscription Tier:</span>
                                <select
                                  value={org.subscription_tier || "free"}
                                  onChange={async (e) => {
                                    const newTier = e.target.value;
                                    try {
                                      const res = await apiRequest(`/api/admin/organizations/${org.id}/tier`, {
                                        method: "POST",
                                        headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({ tier: newTier }),
                                      });
                                      if (res.ok) {
                                        setOrgs((prev) => prev.map((o) => o.id === org.id ? { ...o, subscription_tier: newTier } : o));
                                      }
                                    } catch {}
                                  }}
                                  className="bg-[#111] border border-[#1a1a1a] rounded-md px-3 py-1.5 text-sm focus:border-violet-500 outline-none"
                                >
                                  {TIER_OPTIONS.map((t) => (
                                    <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                                  ))}
                                </select>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium">Bonobot Plan:</span>
                                <select
                                  value={org.bonobot_plan || "none"}
                                  onChange={async (e) => {
                                    const newPlan = e.target.value;
                                    try {
                                      const res = await apiRequest(`/api/admin/organizations/${org.id}/tier`, {
                                        method: "POST",
                                        headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({ bonobot_plan: newPlan }),
                                      });
                                      if (res.ok) {
                                        setOrgs((prev) => prev.map((o) => o.id === org.id ? { ...o, bonobot_plan: newPlan } : o));
                                      }
                                    } catch {}
                                  }}
                                  className="bg-[#111] border border-[#1a1a1a] rounded-md px-3 py-1.5 text-sm focus:border-violet-500 outline-none"
                                >
                                  {BONOBOT_OPTIONS.map((t) => (
                                    <option key={t} value={t}>{t === "none" ? "None" : t.charAt(0).toUpperCase() + t.slice(1)}</option>
                                  ))}
                                </select>
                              </div>
                            </div>

                          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                            {/* Users */}
                            <div>
                              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <Users className="h-4 w-4 text-violet-500" />
                                Users ({orgDetail.users.length})
                              </h4>
                              <div className="space-y-2">
                                {orgDetail.users.map((u) => (
                                  <div key={u.id} className="rounded-md border border-border p-2 text-sm">
                                    <div className="flex items-center justify-between">
                                      <span className="font-medium truncate">{u.name}</span>
                                      <Badge variant={u.role === "admin" ? "default" : "secondary"} className="text-[10px]">
                                        {u.role}
                                      </Badge>
                                    </div>
                                    <p className="text-xs text-muted-foreground truncate">{u.email}</p>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Providers */}
                            <div>
                              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <Cloud className="h-4 w-4 text-blue-500" />
                                Providers ({orgDetail.providers.length})
                              </h4>
                              <div className="space-y-2">
                                {orgDetail.providers.length === 0 ? (
                                  <p className="text-xs text-muted-foreground">No providers connected</p>
                                ) : (
                                  orgDetail.providers.map((p) => (
                                    <div key={p.id} className="rounded-md border border-border p-2 text-sm flex items-center justify-between">
                                      <span className="font-medium uppercase">{p.provider_type}</span>
                                      <Badge variant={p.status === "active" ? "success" : "warning"} className="text-[10px]">
                                        {p.status}
                                      </Badge>
                                    </div>
                                  ))
                                )}
                              </div>
                            </div>

                            {/* Deployments */}
                            <div>
                              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <Rocket className="h-4 w-4 text-orange-500" />
                                Deployments ({orgDetail.deployments.length})
                              </h4>
                              <div className="space-y-2">
                                {orgDetail.deployments.length === 0 ? (
                                  <p className="text-xs text-muted-foreground">No deployments</p>
                                ) : (
                                  orgDetail.deployments.map((d) => (
                                    <div key={d.id} className="rounded-md border border-border p-2 text-sm flex items-center justify-between">
                                      <span className="font-medium truncate">
                                        {d.config?.name || d.config?.model_display_name || "Deployment"}
                                      </span>
                                      <Badge
                                        variant={d.status === "active" ? "success" : d.status === "error" ? "destructive" : "warning"}
                                        className="text-[10px]"
                                      >
                                        {d.status}
                                      </Badge>
                                    </div>
                                  ))
                                )}
                              </div>
                            </div>
                          </div>
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">Failed to load details.</p>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Delete confirmation modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => setDeleteConfirm(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-card border border-border rounded-lg p-6 max-w-md w-full mx-4 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start gap-4">
                <div className="h-10 w-10 rounded-full bg-red-500/15 flex items-center justify-center shrink-0">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">Delete Organization</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    This will permanently delete the organization, all its users, providers, deployments, and gateway data. This cannot be undone.
                  </p>
                  <div className="flex gap-3 mt-4">
                    <button
                      onClick={() => handleDelete(deleteConfirm)}
                      disabled={deleting}
                      className="px-4 py-2 text-sm font-medium rounded-md bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                    >
                      {deleting ? "Deleting..." : "Delete"}
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="px-4 py-2 text-sm font-medium rounded-md border border-border hover:bg-accent transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
                <button onClick={() => setDeleteConfirm(null)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
