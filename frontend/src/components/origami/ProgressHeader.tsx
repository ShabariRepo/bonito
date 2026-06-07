"use client";

import type { ExecutionProgress } from "./useOrigamiSession";

export function ProgressHeader({ execution }: { execution: ExecutionProgress }) {
  if (!execution) return null;
  const pct = Math.min(
    100,
    Math.round((execution.currentStep / Math.max(execution.totalSteps, 1)) * 100),
  );
  return (
    <div className="px-4 py-2 border-b border-[#1a1a1a] bg-[#0d0d0d]">
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-[#aaa]">
          Deploying step {execution.currentStep} of {execution.totalSteps}
        </span>
        <span className="text-[#666] font-mono">{pct}%</span>
      </div>
      <div className="w-full h-1 bg-[#1a1a1a] rounded overflow-hidden">
        <div
          className="h-full bg-[#7c3aed] transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
