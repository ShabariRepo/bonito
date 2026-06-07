"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import type { ActivityEntry } from "./useOrigamiSession";

export function ActivityPanel({ activity }: { activity: ActivityEntry[] }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  if (activity.length === 0) {
    return (
      <div className="text-sm text-muted-foreground italic">No tool calls yet.</div>
    );
  }

  return (
    <div className="space-y-2">
      {activity.map((a) => {
        const isOpen = !!expanded[a.id];
        const duration = a.completedAt ? a.completedAt - a.startedAt : null;
        const StatusIcon =
          a.status === "success" ? CheckCircle2 : a.status === "error" ? XCircle : Loader2;
        const iconClass =
          a.status === "success"
            ? "text-emerald-500"
            : a.status === "error"
              ? "text-destructive"
              : "text-amber-500 animate-spin";

        return (
          <div
            key={a.id}
            className="border border-border rounded-md bg-card overflow-hidden"
          >
            <button
              type="button"
              onClick={() => setExpanded((e) => ({ ...e, [a.id]: !isOpen }))}
              className="w-full text-left px-3 py-2 flex items-center justify-between hover:bg-accent/30 transition-colors"
            >
              <div className="flex items-center gap-2 min-w-0">
                <StatusIcon className={`h-3.5 w-3.5 shrink-0 ${iconClass}`} />
                <span className="font-mono text-xs truncate">{a.tool}</span>
              </div>
              <div className="flex items-center gap-3 text-xs text-muted-foreground shrink-0">
                {duration !== null && <span>{duration}ms</span>}
                {isOpen ? (
                  <ChevronDown className="h-3.5 w-3.5" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" />
                )}
              </div>
            </button>
            {isOpen && (
              <div className="px-3 pb-3 border-t border-border">
                {a.summary && (
                  <pre className="text-xs text-muted-foreground mt-2 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(a.summary, null, 2)}
                  </pre>
                )}
                {a.error && (
                  <div className="text-xs text-destructive mt-2 whitespace-pre-wrap">
                    {a.error}
                  </div>
                )}
                {!a.summary && !a.error && (
                  <div className="text-xs text-muted-foreground italic mt-2">
                    No additional detail.
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
