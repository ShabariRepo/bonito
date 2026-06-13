"use client";

import { useState, useEffect } from "react";
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
import { DollarSign, Building2, AlertTriangle, TrendingUp } from "lucide-react";

type OrgRow = {
  org_id: string;
  org_name: string;
  tier: string;
  turns_used: number;
  turn_cap: number | null;
  over_cap: boolean;
  overage_turns: number;
  overage_rate_usd: number;
  overage_revenue_usd: number;
  cost_tracked_usd: number;
  cost_real_usd: number;
  margin_usd: number;
};

type Billing = {
  period: string;
  orgs: OrgRow[];
  totals: {
    orgs_using: number;
    orgs_over_cap: number;
    total_turns: number;
    total_overage_revenue_usd: number;
    total_real_cost_usd: number;
    total_tracked_cost_usd: number;
    total_margin_usd: number;
  };
};

const usd = (n: number) =>
  `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function Stat({ label, value, icon: Icon, accent }: {
  label: string; value: string; icon: any; accent?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`text-2xl font-bold ${accent ?? ""}`}>{value}</p>
          </div>
          <Icon className="h-8 w-8 text-muted-foreground/40" />
        </div>
      </CardContent>
    </Card>
  );
}

export default function StudioBillingPage() {
  const [data, setData] = useState<Billing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const res = await apiRequest("/api/admin/origami/billing");
        const body = await res.json();
        setData(body);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div className="p-8"><LoadingDots /></div>;
  if (error) return <div className="p-8"><ErrorBanner message={error} /></div>;
  if (!data) return null;

  const t = data.totals;
  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Studio / Origami Billing"
        description={`Per-org usage, overage, real (cache-aware) cost & margin — ${data.period}`}
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Orgs using" value={String(t.orgs_using)} icon={Building2} />
        <Stat label="Over cap" value={String(t.orgs_over_cap)} icon={AlertTriangle}
              accent={t.orgs_over_cap ? "text-amber-500" : undefined} />
        <Stat label="Overage revenue" value={usd(t.total_overage_revenue_usd)} icon={TrendingUp}
              accent="text-emerald-500" />
        <Stat label="Margin (real)" value={usd(t.total_margin_usd)} icon={DollarSign}
              accent={t.total_margin_usd >= 0 ? "text-emerald-500" : "text-red-500"} />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Per-org breakdown</CardTitle>
          <p className="text-sm text-muted-foreground">
            Real cost applies the prompt-cache discount (the actual bill). Tracked cost is
            full-price and feeds the conservative spend cap.
          </p>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-4">Org</th>
                  <th className="py-2 pr-4">Tier</th>
                  <th className="py-2 pr-4 text-right">Turns / cap</th>
                  <th className="py-2 pr-4 text-right">Overage</th>
                  <th className="py-2 pr-4 text-right">Revenue</th>
                  <th className="py-2 pr-4 text-right">Real cost</th>
                  <th className="py-2 pr-4 text-right">Tracked</th>
                  <th className="py-2 pr-4 text-right">Margin</th>
                </tr>
              </thead>
              <tbody>
                {data.orgs.map((o) => (
                  <tr key={o.org_id} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{o.org_name}</td>
                    <td className="py-2 pr-4">
                      <Badge variant="secondary" className="capitalize">{o.tier}</Badge>
                    </td>
                    <td className="py-2 pr-4 text-right">
                      <span className={o.over_cap ? "font-semibold text-amber-500" : ""}>
                        {o.turns_used.toLocaleString()}
                      </span>
                      <span className="text-muted-foreground"> / {o.turn_cap ?? "∞"}</span>
                    </td>
                    <td className="py-2 pr-4 text-right">
                      {o.overage_turns > 0
                        ? <span>{o.overage_turns} @ ${o.overage_rate_usd}</span>
                        : <span className="text-muted-foreground">—</span>}
                    </td>
                    <td className="py-2 pr-4 text-right text-emerald-500">
                      {o.overage_revenue_usd > 0 ? usd(o.overage_revenue_usd) : "—"}
                    </td>
                    <td className="py-2 pr-4 text-right">{usd(o.cost_real_usd)}</td>
                    <td className="py-2 pr-4 text-right text-muted-foreground">
                      {usd(o.cost_tracked_usd)}
                    </td>
                    <td className={`py-2 pr-4 text-right font-medium ${
                      o.margin_usd >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                      {usd(o.margin_usd)}
                    </td>
                  </tr>
                ))}
                {data.orgs.length === 0 && (
                  <tr><td colSpan={8} className="py-6 text-center text-muted-foreground">
                    No Studio/Origami usage this period.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
