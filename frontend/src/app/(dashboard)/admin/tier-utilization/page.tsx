"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ErrorBanner } from "@/components/ui/error-banner";
import { apiRequest } from "@/lib/auth";
import {
  TrendingUp,
  AlertTriangle,
  Activity,
  DollarSign,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

type Dimension = {
  used: number;
  cap: number | null;
  pct: number;
};

type OrgRow = {
  org_id: string;
  org_name: string;
  tier: string;
  tier_band_usd: number;
  user_count: number;
  dimensions: {
    pats: Dimension;
    project_tokens: Dimension;
    origami_turns: Dimension;
    providers: Dimension;
  };
  worst_pct: number;
  status: "ok" | "near" | "at_cap" | "over";
  subscription_status?: string | null;
};

type Summary = {
  total_orgs: number;
  over_cap: number;
  at_cap: number;
  near_cap: number;
  healthy: number;
  monthly_revenue_at_risk_usd: number;
};

const STATUS_LABEL: Record<OrgRow["status"], string> = {
  ok: "Healthy",
  near: "Near cap",
  at_cap: "At cap",
  over: "Over cap",
};

const STATUS_COLOR: Record<OrgRow["status"], string> = {
  ok: "text-emerald-500 border-emerald-500/30 bg-emerald-500/10",
  near: "text-amber-500 border-amber-500/30 bg-amber-500/10",
  at_cap: "text-orange-500 border-orange-500/30 bg-orange-500/10",
  over: "text-destructive border-destructive/30 bg-destructive/10",
};

function pctBarColor(pct: number) {
  if (pct >= 100) return "bg-destructive";
  if (pct >= 85) return "bg-orange-500";
  if (pct >= 60) return "bg-amber-500";
  return "bg-emerald-500";
}

function PctBar({ used, cap, pct }: Dimension) {
  if (cap === null) {
    return (
      <div className="text-xs text-muted-foreground">
        {used.toLocaleString()} <span className="text-text-dim">/ ∞</span>
      </div>
    );
  }
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">
          {used.toLocaleString()} / {cap.toLocaleString()}
        </span>
        <span className="font-mono">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full ${pctBarColor(pct)}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function TierUtilizationPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [orgs, setOrgs] = useState<OrgRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "near" | "at_cap" | "over">(
    "all",
  );
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  useEffect(() => {
    (async () => {
      try {
        const res = await apiRequest("/api/admin/tier-utilization");
        const data = await res.json();
        setSummary(data.summary);
        setOrgs(data.orgs);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const visibleOrgs = orgs.filter((o) => filter === "all" || o.status === filter);

  return (
    <div className="container mx-auto px-4 py-8">
      <PageHeader
        title="Tier Utilization"
        description="Per-org cap utilization across PATs, project tokens, Origami turns, and providers. Sorted by worst dimension descending — upsell candidates at the top."
      />

      {error && <ErrorBanner message={error} />}

      {loading ? (
        <div className="flex justify-center py-12">
          <LoadingDots />
        </div>
      ) : (
        <>
          {summary && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-muted-foreground uppercase tracking-wider">
                    Total Orgs
                  </div>
                  <div className="text-2xl font-bold mt-1">
                    {summary.total_orgs}
                  </div>
                </CardContent>
              </Card>
              <Card className="border-emerald-500/30">
                <CardContent className="p-4">
                  <div className="text-xs text-emerald-500 uppercase tracking-wider">
                    Healthy
                  </div>
                  <div className="text-2xl font-bold mt-1">
                    {summary.healthy}
                  </div>
                </CardContent>
              </Card>
              <Card className="border-amber-500/30">
                <CardContent className="p-4">
                  <div className="text-xs text-amber-500 uppercase tracking-wider">
                    Near Cap (60-85%)
                  </div>
                  <div className="text-2xl font-bold mt-1">
                    {summary.near_cap}
                  </div>
                </CardContent>
              </Card>
              <Card className="border-orange-500/30">
                <CardContent className="p-4">
                  <div className="text-xs text-orange-500 uppercase tracking-wider">
                    At Cap (85-100%)
                  </div>
                  <div className="text-2xl font-bold mt-1">
                    {summary.at_cap}
                  </div>
                </CardContent>
              </Card>
              <Card className="border-destructive/30">
                <CardContent className="p-4">
                  <div className="text-xs text-destructive uppercase tracking-wider flex items-center gap-1">
                    <DollarSign className="h-3 w-3" />
                    Revenue at Risk
                  </div>
                  <div className="text-2xl font-bold mt-1">
                    ${summary.monthly_revenue_at_risk_usd.toLocaleString()}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    /mo MRR from at-cap orgs
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          <div className="flex gap-2 mb-4">
            {(["all", "near", "at_cap", "over"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  filter === f
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {f === "all"
                  ? "All"
                  : f === "near"
                    ? "Near cap"
                    : f === "at_cap"
                      ? "At cap"
                      : "Over"}
              </button>
            ))}
          </div>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Activity className="h-4 w-4" />
                Orgs ({visibleOrgs.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {visibleOrgs.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No orgs match the current filter.
                </div>
              ) : (
                <div>
                  {visibleOrgs.map((o, idx) => (
                    <motion.div
                      key={o.org_id}
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.02 }}
                      className="border-b border-border last:border-b-0"
                    >
                      <button
                        onClick={() =>
                          setExpanded((e) => ({
                            ...e,
                            [o.org_id]: !e[o.org_id],
                          }))
                        }
                        className="w-full px-4 py-3 hover:bg-muted/30 transition-colors text-left flex items-center justify-between gap-4"
                      >
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          {expanded[o.org_id] ? (
                            <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                          )}
                          <div className="min-w-0 flex-1">
                            <div className="font-medium truncate">
                              {o.org_name}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {o.user_count} user
                              {o.user_count === 1 ? "" : "s"} · ${o.tier_band_usd.toLocaleString()}/mo band
                            </div>
                          </div>
                        </div>
                        <Badge variant="outline" className="capitalize shrink-0">
                          {o.tier}
                        </Badge>
                        <Badge
                          variant="outline"
                          className={`shrink-0 ${STATUS_COLOR[o.status]}`}
                        >
                          {o.status === "over" || o.status === "at_cap" ? (
                            <AlertTriangle className="h-3 w-3 mr-1" />
                          ) : null}
                          {STATUS_LABEL[o.status]} · {o.worst_pct.toFixed(0)}%
                        </Badge>
                      </button>
                      {expanded[o.org_id] && (
                        <div className="px-4 pb-4 grid grid-cols-1 md:grid-cols-2 gap-4 bg-muted/10">
                          <div className="space-y-2">
                            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                              Personal Access Tokens
                            </div>
                            <PctBar {...o.dimensions.pats} />
                          </div>
                          <div className="space-y-2">
                            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                              Project Tokens (bj-)
                            </div>
                            <PctBar {...o.dimensions.project_tokens} />
                          </div>
                          <div className="space-y-2">
                            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                              Origami Turns (this month)
                            </div>
                            <PctBar {...o.dimensions.origami_turns} />
                          </div>
                          <div className="space-y-2">
                            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                              Active Providers
                            </div>
                            <PctBar {...o.dimensions.providers} />
                          </div>
                          <div className="md:col-span-2 pt-2 text-xs text-muted-foreground font-mono">
                            org_id: {o.org_id}
                          </div>
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
