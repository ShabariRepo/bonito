"use client";

import { useState } from "react";
import type { ActivityEntry } from "./useOrigamiSession";

export function ActivityPanel({ activity }: { activity: ActivityEntry[] }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  return (
    <div className="space-y-1">
      {activity.length === 0 && (
        <div className="text-xs text-[#666] italic">No tool calls yet.</div>
      )}
      {activity.map((a) => {
        const isOpen = !!expanded[a.id];
        const duration = a.completedAt ? a.completedAt - a.startedAt : null;
        return (
          <div
            key={a.id}
            className="border border-[#1a1a1a] rounded bg-[#0e0e0e] overflow-hidden"
          >
            <button
              type="button"
              onClick={() => setExpanded((e) => ({ ...e, [a.id]: !isOpen }))}
              className="w-full text-left px-2 py-1.5 flex items-center justify-between hover:bg-[#141414] transition"
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={
                    a.status === "success"
                      ? "text-green-400"
                      : a.status === "error"
                        ? "text-red-400"
                        : "text-yellow-400 animate-pulse"
                  }
                >
                  {a.status === "success" ? "✓" : a.status === "error" ? "✗" : "⋯"}
                </span>
                <span className="font-mono text-[11px] text-[#ccc] truncate">{a.tool}</span>
              </div>
              <div className="flex items-center gap-2 text-[10px] text-[#888]">
                {duration !== null && <span>{duration}ms</span>}
                <span className="opacity-50">{isOpen ? "▾" : "▸"}</span>
              </div>
            </button>
            {isOpen && (
              <div className="px-2 pb-2 border-t border-[#1a1a1a]">
                {a.summary && (
                  <pre className="text-[10px] text-[#777] mt-1 overflow-x-auto">
                    {JSON.stringify(a.summary, null, 2)}
                  </pre>
                )}
                {a.error && (
                  <div className="text-[10px] text-red-300 mt-1 whitespace-pre-wrap">
                    {a.error}
                  </div>
                )}
                {!a.summary && !a.error && (
                  <div className="text-[10px] text-[#666] italic mt-1">
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
