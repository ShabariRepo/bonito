"use client";

import { Card } from "@/components/ui/card";
import type { ExecutionProgress } from "./useOrigamiSession";

export function ProgressHeader({ execution }: { execution: ExecutionProgress }) {
  if (!execution) return null;
  const pct = Math.min(
    100,
    Math.round((execution.currentStep / Math.max(execution.totalSteps, 1)) * 100),
  );
  return (
    <Card className="p-3">
      <div className="flex items-center justify-between text-sm mb-2">
        <span className="text-foreground">
          Deploying step {execution.currentStep} of {execution.totalSteps}
        </span>
        <span className="text-muted-foreground font-mono text-xs">{pct}%</span>
      </div>
      <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </Card>
  );
}
