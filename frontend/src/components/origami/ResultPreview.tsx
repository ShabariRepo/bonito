"use client";

import type { ResultPreview as ResultPreviewType } from "./useOrigamiSession";

const STATUS_LABELS: Record<NonNullable<ResultPreviewType>["status"], string> = {
  success: "Deployed",
  partial: "Partial success",
  failed: "Deployment failed",
};

const STATUS_COLORS: Record<NonNullable<ResultPreviewType>["status"], string> = {
  success: "text-green-300 border-green-500/40 bg-green-950/20",
  partial: "text-yellow-300 border-yellow-500/40 bg-yellow-950/20",
  failed: "text-red-300 border-red-500/40 bg-red-950/20",
};

export function ResultPreview({ result }: { result: ResultPreviewType }) {
  if (!result) return null;

  return (
    <div
      className={`rounded-md border p-3 text-xs ${STATUS_COLORS[result.status]}`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="font-medium">{STATUS_LABELS[result.status]}</div>
        <div className="text-[10px] opacity-70">
          {result.succeeded} ok • {result.failed} fail
        </div>
      </div>
      <ul className="space-y-1">
        {result.resources.map((r) => (
          <li key={r.id} className="flex items-center justify-between gap-2">
            <span className="font-mono truncate">{r.name}</span>
            <span className="text-[10px] opacity-70 capitalize">{r.state}</span>
          </li>
        ))}
      </ul>
      {result.status === "success" && (
        <div className="text-[10px] mt-2 opacity-70">
          Click any resource above to open it in the platform.
        </div>
      )}
    </div>
  );
}
