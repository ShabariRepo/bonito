"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bot,
  MessageSquare,
  X,
  ArrowRight,
  User,
  Cpu,
  ChevronDown,
  ChevronUp,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";
import type { BreadcrumbNode, AgentMessage } from "./BreadcrumbSummaryPanel";

// ── Color map ─────────────────────────────────────────────────────

const CONNECTION_COLORS: Record<string, string> = {
  handoff: "#06b6d4",
  escalation: "#ef4444",
  data_feed: "#10b981",
  trigger: "#f59e0b",
};

const CONNECTION_LABELS: Record<string, string> = {
  handoff: "Handoff",
  escalation: "Escalation",
  data_feed: "Data Feed",
  trigger: "Trigger",
};

// ── Helpers ───────────────────────────────────────────────────────

function formatTimestamp(dateString: string): string {
  const d = new Date(dateString);
  return d.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

// ── Component ─────────────────────────────────────────────────────

interface Props {
  projectId: string;
  sourceAgent: BreadcrumbNode;
  targetAgent: BreadcrumbNode;
  connectionType: string;
  dateFrom: string;
  dateTo: string;
  onClose: () => void;
}

export function BreadcrumbEdgePanel({
  projectId,
  sourceAgent,
  targetAgent,
  connectionType,
  dateFrom,
  dateTo,
  onClose,
}: Props) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(
    new Set()
  );
  const PAGE_SIZE = 20;

  const color = CONNECTION_COLORS[connectionType] || "#06b6d4";
  const label = CONNECTION_LABELS[connectionType] || connectionType;

  const fetchMessages = useCallback(
    async (append = false) => {
      if (!projectId) return;
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setMessages([]);
        setOffset(0);
      }

      try {
        const params = new URLSearchParams({
          date_from: dateFrom,
          date_to: dateTo,
          limit: String(PAGE_SIZE),
          offset: String(append ? offset : 0),
        });

        const res = await apiRequest(
          `/api/projects/${projectId}/breadcrumbs/edges/${sourceAgent.id}/${targetAgent.id}/messages?${params}`
        );
        if (res.ok) {
          const data = await res.json();
          if (append) {
            setMessages((prev) => [...prev, ...data.messages]);
          } else {
            setMessages(data.messages);
          }
          setTotal(data.total);
          setOffset((append ? offset : 0) + data.messages.length);
        }
      } catch (err) {
        console.error("Failed to fetch edge messages:", err);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [projectId, sourceAgent.id, targetAgent.id, dateFrom, dateTo, offset]
  );

  useEffect(() => {
    fetchMessages(false);
  }, [sourceAgent.id, targetAgent.id, dateFrom, dateTo]);

  const toggleExpand = (id: string) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const hasMore = messages.length < total;

  return (
    <div className="absolute top-0 right-0 h-full w-[90vw] sm:w-[500px] max-w-[600px] bg-[#12122a] border-l border-gray-800 shadow-2xl z-30 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: color }}
            />
            <h3 className="font-semibold text-white text-sm truncate">
              Edge Messages
            </h3>
            <Badge
              variant="outline"
              className="text-[10px] border-gray-600 text-gray-400"
            >
              {label}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-gray-400 hover:text-white h-7 w-7 p-0"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Source → Target */}
        <div className="flex items-center gap-2 text-xs">
          <div className="flex items-center gap-1.5 rounded-md bg-[#1a1a2e] border border-gray-700 px-2.5 py-1.5">
            <Bot className="h-3 w-3 text-cyan-500" />
            <span className="text-white font-medium">{sourceAgent.name}</span>
          </div>
          <ArrowRight className="h-4 w-4 text-gray-500 flex-shrink-0" />
          <div className="flex items-center gap-1.5 rounded-md bg-[#1a1a2e] border border-gray-700 px-2.5 py-1.5">
            <Bot className="h-3 w-3 text-cyan-500" />
            <span className="text-white font-medium">{targetAgent.name}</span>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="px-4 py-2 border-b border-gray-800 flex-shrink-0 flex items-center justify-between text-xs text-gray-500">
        <span>{total} delegation{total !== 1 ? "s" : ""} in range</span>
        <span>
          {dateFrom} to {dateTo}
        </span>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 text-cyan-500 animate-spin" />
            <span className="ml-2 text-gray-400 text-sm">
              Loading edge messages...
            </span>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-12">
            <MessageSquare className="mx-auto h-10 w-10 text-gray-600 mb-3" />
            <p className="text-gray-500 text-sm">
              No delegations between these agents in this period
            </p>
          </div>
        ) : (
          <>
            <div className="text-[10px] text-gray-500 mb-2">
              Showing {messages.length} of {total}
            </div>

            {messages.map((msg) => {
              const isExpanded = expandedMessages.has(msg.id);
              const content = msg.content || "";
              const isLong = content.length > 300;
              const displayContent =
                isLong && !isExpanded ? content.slice(0, 300) + "..." : content;

              // Try to extract delegation info from tool_calls
              let delegationTarget = "";
              let delegationPreview = "";
              if (msg.tool_calls && Array.isArray(msg.tool_calls)) {
                for (const call of msg.tool_calls) {
                  const fn = call?.function;
                  if (fn?.name === "invoke_agent" || fn?.name === "delegate_task") {
                    try {
                      const args =
                        typeof fn.arguments === "string"
                          ? JSON.parse(fn.arguments)
                          : fn.arguments;
                      delegationTarget = args?.agent_name || "";
                      delegationPreview = args?.message_preview || args?.message || "";
                    } catch {}
                  }
                }
              }

              return (
                <div
                  key={msg.id}
                  className="rounded-lg px-3 py-2.5 text-sm bg-[#1a1a2e] border border-gray-700/50 hover:border-gray-600 transition-colors"
                >
                  {/* Header row */}
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5">
                      <ArrowRight
                        className="h-3 w-3 flex-shrink-0"
                        style={{ color }}
                      />
                      <span
                        className="text-[10px] font-medium uppercase tracking-wider"
                        style={{ color }}
                      >
                        {msg.tool_name || "invoke_agent"}
                      </span>
                      {delegationTarget && (
                        <span className="text-[10px] text-gray-500">
                          → {delegationTarget}
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-gray-500">
                      {msg.created_at ? formatTimestamp(msg.created_at) : ""}
                    </span>
                  </div>

                  {/* Delegation preview or content */}
                  <p className="text-gray-300 text-xs leading-relaxed whitespace-pre-wrap break-words">
                    {delegationPreview || displayContent || `[${msg.tool_name || msg.role}]`}
                  </p>

                  {/* Expand toggle for long content */}
                  {isLong && !delegationPreview && (
                    <button
                      onClick={() => toggleExpand(msg.id)}
                      className="flex items-center gap-1 mt-1.5 text-[10px] text-cyan-500 hover:text-cyan-400 transition-colors"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="h-3 w-3" /> Show less
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-3 w-3" /> Show more
                        </>
                      )}
                    </button>
                  )}
                </div>
              );
            })}

            {/* Load more */}
            {hasMore && (
              <button
                onClick={() => fetchMessages(true)}
                disabled={loadingMore}
                className="w-full flex items-center justify-center gap-2 rounded-lg border border-gray-700 bg-[#1a1a2e] px-4 py-2.5 text-xs text-gray-300 hover:border-gray-500 hover:text-white transition-colors disabled:opacity-50"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>Load more ({total - messages.length} remaining)</>
                )}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
