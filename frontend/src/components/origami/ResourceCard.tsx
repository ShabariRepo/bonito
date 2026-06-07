"use client";

import type { Resource } from "./useOrigamiSession";

const ICONS: Record<Resource["type"], string> = {
  agent: "🤖",
  kb: "📚",
  project: "📁",
  gateway_key: "🔑",
  link: "🔗",
  unknown: "•",
};

const STATE_COLORS: Record<Resource["state"], string> = {
  queued: "text-[#888] border-[#222] bg-[#0f0f0f]",
  creating: "text-yellow-300 border-yellow-500/40 bg-yellow-950/20",
  done: "text-green-300 border-green-500/40 bg-green-950/20",
  error: "text-red-300 border-red-500/40 bg-red-950/20",
};

const STATE_LABELS: Record<Resource["state"], string> = {
  queued: "queued",
  creating: "creating…",
  done: "done",
  error: "error",
};

export function ResourceCard({ resource }: { resource: Resource }) {
  return (
    <div
      className={`rounded-md border p-2.5 text-xs transition-all ${
        STATE_COLORS[resource.state]
      }`}
    >
      <div className="flex items-start gap-2">
        <span className="text-base leading-none">{ICONS[resource.type]}</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium truncate">{resource.name}</div>
          <div className="flex items-center justify-between mt-0.5">
            <span className="text-[10px] uppercase tracking-wider opacity-70">
              {resource.type === "gateway_key" ? "gateway key" : resource.type}
            </span>
            <span className="text-[10px] flex items-center gap-1">
              {resource.state === "creating" && (
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse" />
              )}
              {STATE_LABELS[resource.state]}
            </span>
          </div>
          {resource.realId && (
            <div className="text-[10px] text-[#666] mt-1 font-mono truncate">
              {resource.realId.slice(0, 8)}…
            </div>
          )}
          {resource.error && (
            <div className="text-[10px] text-red-300 mt-1 whitespace-pre-wrap">
              {resource.error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
