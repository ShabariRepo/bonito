"use client";

import { useEffect, useRef, useState } from "react";
import {
  Rocket,
  X,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Clock,
  Loader2,
  XCircle,
} from "lucide-react";
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
  // True when the backend already executed every step inline (the
  // resources exist). The card renders as DONE and must NOT auto-deploy
  // or call execute_plan — the work is already done.
  pre_executed?: boolean;
  // Per-step result summaries when pre_executed (gateway key value, ids, …).
  step_results?: Record<string, unknown>[];
};

type Props = {
  plan: PlanCardData;
  onExecuted?: (result: unknown) => void;
  onCancelled?: () => void;
  onEvent?: (event: { type: string; payload: Record<string, unknown> }) => void;
  /**
   * When true, the card fires its deploy flow automatically on mount —
   * no Deploy click required. Used by Bonito Studio where the chat
   * surface is intentionally friction-free; the card is shown for
   * visibility / details, not as a gating action. Origami's workspace
   * leaves this false so users keep their Deploy / Edit / Cancel choice.
   */
  autoDeploy?: boolean;
};

type StepState = "queued" | "running" | "done" | "failed";

function StepIcon({ state }: { state: StepState }) {
  if (state === "running") {
    return <Loader2 className="h-3.5 w-3.5 text-primary animate-spin mt-1 shrink-0" />;
  }
  if (state === "done") {
    return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-1 shrink-0" />;
  }
  if (state === "failed") {
    return <XCircle className="h-3.5 w-3.5 text-destructive mt-1 shrink-0" />;
  }
  return <Clock className="h-3.5 w-3.5 text-muted-foreground mt-1 shrink-0" />;
}

export function PlanCard({ plan, onExecuted, onCancelled, onEvent, autoDeploy = false }: Props) {
  const [deploying, setDeploying] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  // When the backend already executed every step inline, the card opens
  // in its DONE state — no deploy, no execute_plan call.
  const [finalStatus, setFinalStatus] = useState<string | null>(
    plan.pre_executed ? (plan.status === "failed" ? "failed" : "done") : null,
  );
  // Track whether the auto-deploy mount effect has already fired so React's
  // strict-mode double-invoke (and any future state churn) can't re-trigger
  // the deploy POST.
  const autoDeployedRef = useRef(false);
  const [stepStates, setStepStates] = useState<StepState[]>(() =>
    plan.changes.map(() =>
      // Pre-executed plans render every step as done immediately.
      plan.pre_executed
        ? (plan.status === "failed" ? "failed" : "done")
        : ("queued" as StepState),
    ),
  );
  const [stepErrors, setStepErrors] = useState<(string | null)[]>(() =>
    plan.changes.map(() => null),
  );
  const [counts, setCounts] = useState<{ done: number; failed: number }>({
    done: 0,
    failed: 0,
  });

  function updateStep(idx: number, state: StepState, error?: string | null) {
    if (idx < 0 || idx >= plan.changes.length) return;
    setStepStates((prev) => {
      const next = prev.slice();
      // Don't move done/failed back to running (events can arrive in odd order)
      if (next[idx] === "done" || next[idx] === "failed") return prev;
      next[idx] = state;
      return next;
    });
    if (error !== undefined) {
      setStepErrors((prev) => {
        const next = prev.slice();
        next[idx] = error;
        return next;
      });
    }
    if (state === "done") {
      setCounts((c) => ({ ...c, done: c.done + 1 }));
    } else if (state === "failed") {
      setCounts((c) => ({ ...c, failed: c.failed + 1 }));
    }
  }

  async function deploy() {
    if (deploying || cancelled || finalStatus) return;
    setDeploying(true);
    // Reset per-step trackers in case the user re-deploys (not currently
    // exposed but keeps the state consistent)
    setStepStates(plan.changes.map(() => "queued"));
    setStepErrors(plan.changes.map(() => null));
    setCounts({ done: 0, failed: 0 });

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

            // Per-step status tracking
            if (ev.type === "tool_started" && typeof ev.step === "number") {
              updateStep(ev.step, "running");
            } else if (ev.type === "tool_completed" && typeof ev.step === "number") {
              updateStep(ev.step, "done");
            } else if (ev.type === "tool_failed" && typeof ev.step === "number") {
              updateStep(
                ev.step,
                "failed",
                typeof ev.error === "string" ? ev.error : ev.code || "failed",
              );
            } else if (ev.type === "tool_retried" && typeof ev.step === "number") {
              // Auto-repair retry — flip the row back to running. Allow
              // regression from "failed" specifically (our updateStep
              // normally refuses to regress done/failed back to running).
              setStepStates((prev) => {
                const next = prev.slice();
                next[ev.step] = "running";
                return next;
              });
              setStepErrors((prev) => {
                const next = prev.slice();
                next[ev.step] = `auto-retry: ${ev.repair}`;
                return next;
              });
            } else if (ev.type === "execution_done") {
              setFinalStatus(ev.status || "done");
              // Sweep any still-queued steps to a final state so the UI
              // doesn't leave a stuck clock icon after the deploy ends.
              setStepStates((prev) =>
                prev.map((s) =>
                  s === "queued" || s === "running"
                    ? ev.status === "failed"
                      ? "failed"
                      : "done"
                    : s,
                ),
              );
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

  // Studio's friction-free mode — fire deploy immediately on mount when
  // autoDeploy is true. Ref-guarded against React strict-mode double-mount
  // and against re-renders that might otherwise re-trigger the POST.
  useEffect(() => {
    if (!autoDeploy) return;
    // Pre-executed plans are already done — never call execute_plan.
    if (plan.pre_executed) return;
    if (autoDeployedRef.current) return;
    if (deploying || cancelled || finalStatus) return;
    autoDeployedRef.current = true;
    void deploy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoDeploy]);

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
  const runningStep = stepStates.findIndex((s) => s === "running");
  const total = plan.changes.length;
  const showProgress = deploying || finalStatus;

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
        {plan.changes.map((change, i) => {
          const state = stepStates[i] || "queued";
          return (
            <li key={i} className="flex items-start gap-2 text-sm">
              {showProgress ? (
                <StepIcon state={state} />
              ) : (
                <ArrowRight className="h-3.5 w-3.5 text-primary mt-1 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-mono text-xs text-muted-foreground">
                    {change.action}
                  </span>
                  {showProgress && state === "running" && (
                    <span className="text-xs text-primary">running…</span>
                  )}
                  {showProgress && state === "done" && (
                    <span className="text-xs text-emerald-500">done</span>
                  )}
                  {showProgress && state === "failed" && (
                    <span className="text-xs text-destructive">failed</span>
                  )}
                </div>
                {Object.keys(change.params).length > 0 && (
                  <pre className="text-xs text-muted-foreground overflow-x-auto whitespace-pre-wrap mt-0.5">
                    {JSON.stringify(change.params, null, 2)}
                  </pre>
                )}
                {state === "failed" && stepErrors[i] && (
                  <div className="text-xs text-destructive mt-1 whitespace-pre-wrap break-words">
                    {stepErrors[i]}
                  </div>
                )}
              </div>
            </li>
          );
        })}
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

      {!cancelled && !finalStatus && !deploying && (
        <div className="flex gap-2">
          <Button onClick={deploy} disabled={deploying} size="sm" className="gap-1.5">
            <Rocket className="h-3.5 w-3.5" />
            Deploy
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

      {deploying && !finalStatus && (
        <div className="flex items-center justify-between gap-3 text-xs text-muted-foreground pt-1">
          <div className="flex items-center gap-2">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
            <span>
              {runningStep >= 0
                ? `Step ${runningStep + 1} of ${total} — ${plan.changes[runningStep]?.action}`
                : `Deploying ${total} change${total === 1 ? "" : "s"}…`}
            </span>
          </div>
          <span className="font-mono">
            {counts.done + counts.failed}/{total}
          </span>
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
          {finalStatus === "success" && <CheckCircle2 className="h-3.5 w-3.5" />}
          {finalStatus === "partial" && <AlertTriangle className="h-3.5 w-3.5" />}
          {finalStatus === "failed" && <XCircle className="h-3.5 w-3.5" />}
          <span>
            {finalStatus === "success" && `Deployed all ${total} change${total === 1 ? "" : "s"}.`}
            {finalStatus === "partial" &&
              `Partial — ${counts.done} succeeded, ${counts.failed} failed.`}
            {finalStatus === "failed" && `Deployment failed (${counts.failed}/${total}).`}
          </span>
        </div>
      )}
    </div>
  );
}
