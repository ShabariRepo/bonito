"use client";

import { useState } from "react";
import { Rocket, X, CheckCircle2, AlertTriangle, ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getAccessToken } from "@/lib/auth";
import { API_URL } from "@/lib/utils";

export type PlanChange = {
  action: string;
  params: Record<string, unknown>;
  summary?: string | null;
  is_write?: boolean;
};

export type PlanCardData = {
  id: string;
  session_id: string;
  intent: string;
  changes: PlanChange[];
  tier_impact?: {
    summary: string;
    requires_upgrade: boolean;
    blocking_features?: string[];
    upgrade_to_tier?: string | null;
  } | null;
  estimated_cost_usd_monthly?: number | null;
  status: string;
};

type Props = {
  plan: PlanCardData;
  onExecuted?: (result: unknown) => void;
  onCancelled?: () => void;
  onEvent?: (event: { type: string; payload: Record<string, unknown> }) => void;
};

export function PlanCard({ plan, onExecuted, onCancelled, onEvent }: Props) {
  const [deploying, setDeploying] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [finalStatus, setFinalStatus] = useState<string | null>(null);

  async function deploy() {
    if (deploying || cancelled || finalStatus) return;
    setDeploying(true);

    const token = getAccessToken();
    if (!token) {
      onEvent?.({ type: "error", payload: { code: "no_auth", message: "Sign in first." } });
      setDeploying(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/origami/execute_plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ plan_card_id: plan.id }),
      });
      if (!res.ok || !res.body) {
        const txt = await res.text();
        onEvent?.({
          type: "error",
          payload: { code: `http_${res.status}`, message: txt.slice(0, 200) },
        });
        setDeploying(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data: ")) continue;
          try {
            const ev = JSON.parse(line.slice(6));
            onEvent?.(ev);
            if (ev.type === "execution_done") {
              setFinalStatus(ev.status || "done");
              onExecuted?.(ev);
            }
          } catch {
            /* skip */
          }
        }
      }
    } catch (e) {
      onEvent?.({
        type: "error",
        payload: { code: "network", message: e instanceof Error ? e.message : String(e) },
      });
    } finally {
      setDeploying(false);
    }
  }

  async function cancel() {
    if (deploying || cancelled || finalStatus) return;
    setCancelled(true);
    const token = getAccessToken();
    if (token) {
      try {
        await fetch(`${API_URL}/api/origami/plan`, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ plan_card_id: plan.id }),
        });
      } catch {
        /* TTL will evict anyway */
      }
    }
    onCancelled?.();
  }

  const requiresUpgrade = plan.tier_impact?.requires_upgrade;
  const isWriteCount = plan.changes.filter((c) => c.is_write !== false).length;

  return (
    <div className="my-2 mr-auto w-full max-w-[95%] rounded-lg border border-primary/30 bg-muted/40 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Rocket className="h-3.5 w-3.5 text-primary" />
          <span className="text-xs uppercase tracking-wider text-primary font-semibold">
            Plan
          </span>
        </div>
        <Badge variant="outline" className="text-xs">
          {isWriteCount} change{isWriteCount === 1 ? "" : "s"}
        </Badge>
      </div>

      <p className="text-sm text-foreground mb-3">{plan.intent}</p>

      <ul className="space-y-1.5 mb-3">
        {plan.changes.map((change, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <ArrowRight className="h-3.5 w-3.5 text-primary mt-1 shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="font-mono text-xs text-muted-foreground">
                {change.action}
              </div>
              {Object.keys(change.params).length > 0 && (
                <pre className="text-xs text-muted-foreground overflow-x-auto whitespace-pre-wrap mt-0.5">
                  {JSON.stringify(change.params, null, 2)}
                </pre>
              )}
            </div>
          </li>
        ))}
      </ul>

      {plan.tier_impact && (
        <div
          className={`text-xs mb-3 px-2 py-1.5 rounded flex items-start gap-1.5 ${
            requiresUpgrade
              ? "bg-amber-500/10 text-amber-300 border border-amber-500/30"
              : "bg-muted text-muted-foreground border border-border"
          }`}
        >
          {requiresUpgrade && <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />}
          <div>
            {plan.tier_impact.summary}
            {requiresUpgrade && plan.tier_impact.upgrade_to_tier && (
              <span className="ml-1 font-semibold">
                → upgrade to {plan.tier_impact.upgrade_to_tier}
              </span>
            )}
          </div>
        </div>
      )}

      {plan.estimated_cost_usd_monthly != null && (
        <div className="text-xs text-muted-foreground mb-3">
          ~${plan.estimated_cost_usd_monthly.toFixed(2)}/mo estimated
        </div>
      )}

      {!cancelled && !finalStatus && (
        <div className="flex gap-2">
          <Button onClick={deploy} disabled={deploying} size="sm" className="gap-1.5">
            <Rocket className="h-3.5 w-3.5" />
            {deploying ? "Deploying…" : "Deploy"}
          </Button>
          <Button
            onClick={cancel}
            disabled={deploying}
            size="sm"
            variant="ghost"
            className="gap-1.5"
          >
            <X className="h-3.5 w-3.5" />
            Cancel
          </Button>
        </div>
      )}

      {cancelled && (
        <div className="text-xs text-muted-foreground italic">Plan cancelled.</div>
      )}
      {finalStatus && (
        <div
          className={`text-xs flex items-center gap-1.5 ${
            finalStatus === "success"
              ? "text-emerald-500"
              : finalStatus === "partial"
                ? "text-amber-500"
                : "text-destructive"
          }`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          {finalStatus === "success" && "Deployed."}
          {finalStatus === "partial" && "Partial — some tools failed."}
          {finalStatus === "failed" && "Deployment failed."}
        </div>
      )}
    </div>
  );
}
