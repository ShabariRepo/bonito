"use client";

/**
 * OrigamiWorkspace — the Replit-style split-pane Origami surface.
 *
 *  ┌─────────────────────────┬─────────────────────────────┐
 *  │  Chat (40%)             │  Workspace (60%)            │
 *  │                         │                             │
 *  │  • user/assistant turns │  Progress header (during    │
 *  │  • inline plan card     │   execution)                │
 *  │                         │                             │
 *  │                         │  📦 Resources grid          │
 *  │                         │                             │
 *  │                         │  📋 Activity log            │
 *  │                         │                             │
 *  │                         │  ✓ Result preview (after    │
 *  │                         │   execution_done)           │
 *  └─────────────────────────┴─────────────────────────────┘
 */

import { useEffect, useRef } from "react";
import { useOrigamiSession } from "./useOrigamiSession";
import { OrigamiChat } from "./OrigamiChat";
import { ResourcesGrid } from "./ResourcesGrid";
import { ActivityPanel } from "./ActivityPanel";
import { ProgressHeader } from "./ProgressHeader";
import { ResultPreview } from "./ResultPreview";

export function OrigamiWorkspace() {
  const session = useOrigamiSession();

  return (
    <div className="flex h-full w-full bg-[#0a0a0a] text-[#eee]">
      {/* Left: chat panel (40%) */}
      <div className="flex flex-col w-2/5 min-w-[340px] border-r border-[#1a1a1a]">
        <OrigamiChat session={session} />
      </div>

      {/* Right: workspace (60%) */}
      <div className="flex-1 flex flex-col">
        <ProgressHeader execution={session.execution} />

        {/* Header strip */}
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1a1a1a]">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold">Workspace</span>
            {session.tier && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888] uppercase tracking-wider">
                {session.tier}
              </span>
            )}
          </div>
          <div className="text-[10px] text-[#666] font-mono">
            session: {session.conversationId}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Resources grid */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs uppercase tracking-wider text-[#888]">
                📦 Resources
              </h3>
              <span className="text-[10px] text-[#666]">
                {session.resources.length}{" "}
                {session.resources.length === 1 ? "item" : "items"}
              </span>
            </div>
            <ResourcesGrid resources={session.resources} />
          </section>

          {/* Result preview, only after a deploy */}
          {session.result && (
            <section>
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-xs uppercase tracking-wider text-[#888]">
                  ✓ Result
                </h3>
              </div>
              <ResultPreview result={session.result} />
            </section>
          )}

          {/* Activity log */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs uppercase tracking-wider text-[#888]">
                📋 Activity log
              </h3>
              <span className="text-[10px] text-[#666]">
                {session.activity.length} call
                {session.activity.length === 1 ? "" : "s"}
              </span>
            </div>
            <ActivityPanel activity={session.activity} />
          </section>
        </div>
      </div>
    </div>
  );
}
