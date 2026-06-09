"use client";

import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ResultPreview as ResultPreviewType } from "./useOrigamiSession";

const STATUS_LABEL: Record<NonNullable<ResultPreviewType>["status"], string> = {
  success: "Deployed",
  partial: "Partial success",
  failed: "Deployment failed",
};

export function ResultPreview({ result }: { result: ResultPreviewType }) {
  if (!result) return null;

  const Icon =
    result.status === "success"
      ? CheckCircle2
      : result.status === "partial"
        ? AlertTriangle
        : XCircle;

  const iconClass =
    result.status === "success"
      ? "text-emerald-500"
      : result.status === "partial"
        ? "text-amber-500"
        : "text-destructive";

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className={`h-4 w-4 ${iconClass}`} />
          <span className="text-sm font-medium">{STATUS_LABEL[result.status]}</span>
        </div>
        <div className="text-xs text-muted-foreground">
          {result.succeeded} ok • {result.failed} failed
        </div>
      </div>
      <ul className="space-y-1.5">
        {result.resources.map((r) => (
          <li
            key={r.id}
            className="flex items-center justify-between text-sm gap-2"
          >
            <span className="font-mono truncate text-foreground">{r.name}</span>
            <Badge
              variant={
                r.state === "done"
                  ? "default"
                  : r.state === "error"
                    ? "destructive"
                    : "secondary"
              }
              className="text-xs capitalize shrink-0"
            >
              {r.state}
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  );
}
