"use client";

import { useState } from "react";
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
  /** Emit each SSE event from execute_plan so the parent can update activity log */
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
        /* non-fatal — TTL will evict anyway */
      }
    }
    onCancelled?.();
  }

  const requiresUpgrade = plan.tier_impact?.requires_upgrade;
  const isWriteCount = plan.changes.filter((c) => c.is_write !== false).length;

  return (
    <div className="my-2 max-w-[90%] mr-auto bg-[#111] border border-[#7c3aed]/30 rounded-lg p-3 text-sm">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs uppercase tracking-wider text-[#7c3aed] font-semibold">
          Plan
        </span>
        <span className="text-[10px] text-[#888]">
          {isWriteCount} change{isWriteCount === 1 ? "" : "s"}
        </span>
      </div>

      <p className="text-[#ddd] mb-2">{plan.intent}</p>

      <ul className="space-y-1 mb-3">
        {plan.changes.map((change, i) => (
          <li key={i} className="flex gap-2 text-[#ccc]">
            <span className="text-[#7c3aed] mt-0.5">→</span>
            <div className="flex-1">
              <div className="font-mono text-xs text-[#aaa]">{change.action}</div>
              {Object.keys(change.params).length > 0 && (
                <pre className="text-[10px] text-[#777] overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(change.params, null, 2)}
                </pre>
              )}
            </div>
          </li>
        ))}
      </ul>

      {plan.tier_impact && (
        <div
          className={`text-xs mb-2 px-2 py-1 rounded ${
            requiresUpgrade
              ? "bg-amber-950/40 text-amber-300 border border-amber-500/30"
              : "bg-[#1a1a1a] text-[#999]"
          }`}
        >
          {plan.tier_impact.summary}
          {requiresUpgrade && plan.tier_impact.upgrade_to_tier && (
            <span className="ml-2 font-semibold">
              → upgrade to {plan.tier_impact.upgrade_to_tier}
            </span>
          )}
        </div>
      )}

      {plan.estimated_cost_usd_monthly != null && (
        <div className="text-[10px] text-[#666] mb-2">
          ~${plan.estimated_cost_usd_monthly.toFixed(2)}/mo estimated
        </div>
      )}

      {!cancelled && !finalStatus && (
        <div className="flex gap-2">
          <button
            onClick={deploy}
            disabled={deploying}
            className="px-3 py-1.5 bg-[#7c3aed] text-white rounded text-xs font-medium hover:bg-[#6d28d9] disabled:opacity-50"
          >
            {deploying ? "Deploying…" : "Deploy"}
          </button>
          <button
            onClick={cancel}
            disabled={deploying}
            className="px-3 py-1.5 bg-transparent border border-[#333] text-[#999] rounded text-xs hover:border-[#555] hover:text-[#ccc] disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      )}

      {cancelled && (
        <div className="text-xs text-[#666] italic">Plan cancelled.</div>
      )}
      {finalStatus && (
        <div
          className={`text-xs ${
            finalStatus === "success"
              ? "text-green-400"
              : finalStatus === "partial"
                ? "text-yellow-400"
                : "text-red-400"
          }`}
        >
          {finalStatus === "success" && "✓ Deployed."}
          {finalStatus === "partial" && "⚠ Partial — some tools failed."}
          {finalStatus === "failed" && "✗ Deployment failed."}
        </div>
      )}
    </div>
  );
}
