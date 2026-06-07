"use client";

import { Bot, BookOpen, FolderKanban, Key, Link2, HelpCircle, Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Resource } from "./useOrigamiSession";

const ICONS = {
  agent: Bot,
  kb: BookOpen,
  project: FolderKanban,
  gateway_key: Key,
  link: Link2,
  unknown: HelpCircle,
} as const;

const TYPE_LABELS: Record<Resource["type"], string> = {
  agent: "Agent",
  kb: "Knowledge Base",
  project: "Project",
  gateway_key: "Gateway Key",
  link: "Link",
  unknown: "Resource",
};

function StatusBadge({ state }: { state: Resource["state"] }) {
  if (state === "creating") {
    return (
      <Badge variant="outline" className="gap-1 text-xs">
        <Loader2 className="h-3 w-3 animate-spin" />
        Creating
      </Badge>
    );
  }
  if (state === "done") {
    return (
      <Badge variant="default" className="gap-1 text-xs">
        <CheckCircle2 className="h-3 w-3" />
        Done
      </Badge>
    );
  }
  if (state === "error") {
    return (
      <Badge variant="destructive" className="gap-1 text-xs">
        <XCircle className="h-3 w-3" />
        Error
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1 text-xs">
      <Clock className="h-3 w-3" />
      Queued
    </Badge>
  );
}

export function ResourceCard({ resource }: { resource: Resource }) {
  const Icon = ICONS[resource.type] || HelpCircle;
  const label = TYPE_LABELS[resource.type];

  return (
    <div className="rounded-lg border border-border bg-card p-3 transition-colors hover:bg-accent/30">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
          <span className="text-xs uppercase tracking-wider text-muted-foreground">
            {label}
          </span>
        </div>
        <StatusBadge state={resource.state} />
      </div>
      <div className="text-sm font-medium truncate">{resource.name}</div>
      {resource.realId && (
        <div className="text-xs text-muted-foreground mt-1 font-mono truncate">
          {resource.realId.slice(0, 8)}…
        </div>
      )}
      {resource.error && (
        <div className="text-xs text-destructive mt-2 whitespace-pre-wrap break-words">
          {resource.error}
        </div>
      )}
    </div>
  );
}
