"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bot,
  MessageSquare,
  X,
  ArrowLeft,
  ChevronDown,
  User,
  Cpu,
  ArrowRight,
  ChevronDown as ExpandIcon,
  ChevronUp,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";
import type { BreadcrumbNode, AgentMessage } from "./BreadcrumbSummaryPanel";

// ── Filter types ──────────────────────────────────────────────────

type RoleFilter = "all" | "user" | "assistant" | "tool" | "invoke_agent" | "delegate_task";

const ROLE_FILTERS: { value: RoleFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "user", label: "User" },
  { value: "assistant", label: "Assistant" },
  { value: "tool", label: "Tool" },
  { value: "invoke_agent", label: "Delegations" },
];

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
  agents: BreadcrumbNode[];
  initialAgentId: string;
  dateFrom: string;
  dateTo: string;
  onDateChange: (from: string, to: string) => void;
  onClose: () => void;
  onBack: () => void;
}

export function BreadcrumbDetailPanel({
  projectId,
  agents,
  initialAgentId,
  dateFrom,
  dateTo,
  onDateChange,
  onClose,
  onBack,
}: Props) {
  const [selectedAgentId, setSelectedAgentId] = useState(initialAgentId);
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("all");
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const PAGE_SIZE = 20;

  const selectedAgent = agents.find((a) => a.id === selectedAgentId);

  // Fetch messages
  const fetchMessages = useCallback(
    async (append = false) => {
      if (!projectId || !selectedAgentId) return;
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
        if (roleFilter !== "all") {
          params.set("role", roleFilter);
        }

        const res = await apiRequest(
          `/api/projects/${projectId}/breadcrumbs/agents/${selectedAgentId}/messages?${params}`
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
        console.error("Failed to fetch messages:", err);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [projectId, selectedAgentId, dateFrom, dateTo, roleFilter, offset]
  );

  // Refetch when agent or filter changes
  useEffect(() => {
    fetchMessages(false);
  }, [selectedAgentId, roleFilter, dateFrom, dateTo]);

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
    <div
      className="absolute top-0 right-0 h-full w-[90vw] sm:w-[560px] lg:w-[640px] max-w-[700px] bg-[#12122a] border-l border-gray-800 shadow-2xl z-30 flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <button
            onClick={onBack}
            className="text-gray-400 hover:text-white transition-colors p-1 -ml-1"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <Bot className="h-4 w-4 text-cyan-500 flex-shrink-0" />
          <h3 className="font-semibold text-white text-sm truncate">
            {selectedAgent?.name || "Agent Messages"}
          </h3>
          <span className="text-xs text-gray-500">
            {total} messages
          </span>
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

      {/* Filters bar */}
      <div className="px-4 py-3 border-b border-gray-800 space-y-3 flex-shrink-0">
        {/* Agent selector + date inputs */}
        <div className="flex flex-wrap items-end gap-3">
          {/* Agent dropdown */}
          <div className="relative">
            <label className="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">
              Agent
            </label>
            <button
              onClick={() => setAgentDropdownOpen(!agentDropdownOpen)}
              className="flex items-center justify-between w-48 rounded-md border border-gray-700 bg-[#1a1a2e] px-3 py-1.5 text-xs text-white hover:border-gray-500 transition-colors"
            >
              <span className="truncate">{selectedAgent?.name || "Select..."}</span>
              <ChevronDown className="h-3 w-3 text-gray-400 ml-2 flex-shrink-0" />
            </button>
            {agentDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setAgentDropdownOpen(false)}
                />
                <div className="absolute top-full left-0 mt-1 w-48 z-50 rounded-md border border-gray-700 bg-[#1a1a2e] shadow-xl py-1 max-h-48 overflow-y-auto">
                  {agents.map((a) => (
                    <button
                      key={a.id}
                      onClick={() => {
                        setSelectedAgentId(a.id);
                        setAgentDropdownOpen(false);
                      }}
                      className={cn(
                        "w-full text-left px-3 py-1.5 text-xs transition-colors",
                        a.id === selectedAgentId
                          ? "bg-cyan-500/10 text-cyan-400"
                          : "text-gray-300 hover:bg-gray-800"
                      )}
                    >
                      {a.name}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Date from */}
          <div>
            <label className="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">
              From
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => onDateChange(e.target.value, dateTo)}
              className="rounded-md border border-gray-700 bg-[#1a1a2e] px-2 py-1.5 text-xs text-white [color-scheme:dark]"
            />
          </div>

          {/* Date to */}
          <div>
            <label className="block text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">
              To
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => onDateChange(dateFrom, e.target.value)}
              className="rounded-md border border-gray-700 bg-[#1a1a2e] px-2 py-1.5 text-xs text-white [color-scheme:dark]"
            />
          </div>
        </div>

        {/* Role filter pills */}
        <div className="flex flex-wrap gap-1.5">
          {ROLE_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setRoleFilter(f.value)}
              className={cn(
                "rounded-full px-3 py-1 text-[11px] font-medium border transition-colors",
                roleFilter === f.value
                  ? "bg-cyan-500/15 border-cyan-500/40 text-cyan-400"
                  : "bg-transparent border-gray-700 text-gray-400 hover:border-gray-500 hover:text-gray-300"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 text-cyan-500 animate-spin" />
            <span className="ml-2 text-gray-400 text-sm">Loading messages...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-12">
            <MessageSquare className="mx-auto h-10 w-10 text-gray-600 mb-3" />
            <p className="text-gray-500 text-sm">No messages match your filters</p>
          </div>
        ) : (
          <>
            {/* Showing X of Y */}
            <div className="text-[10px] text-gray-500 mb-2">
              Showing {messages.length} of {total}
            </div>

            {messages.map((msg) => {
              const isExpanded = expandedMessages.has(msg.id);
              const content = msg.content || "";
              const isLong = content.length > 300;
              const displayContent = isLong && !isExpanded
                ? content.slice(0, 300) + "..."
                : content;

              return (
                <div
                  key={msg.id}
                  className={cn(
                    "rounded-lg px-3 py-2.5 text-sm border transition-colors",
                    msg.role === "user"
                      ? "bg-blue-500/5 border-blue-500/15"
                      : msg.role === "assistant"
                      ? "bg-[#1a1a2e] border-gray-700/50"
                      : msg.role === "tool"
                      ? "bg-yellow-500/5 border-yellow-500/10"
                      : "bg-gray-800/30 border-gray-700/30"
                  )}
                >
                  {/* Header */}
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5">
                      {msg.role === "user" ? (
                        <User className="h-3 w-3 text-blue-400" />
                      ) : msg.role === "assistant" ? (
                        <Cpu className="h-3 w-3 text-cyan-400" />
                      ) : msg.role === "tool" ? (
                        <ArrowRight className="h-3 w-3 text-yellow-400" />
                      ) : (
                        <Bot className="h-3 w-3 text-gray-400" />
                      )}
                      <span
                        className={cn(
                          "text-[10px] font-medium uppercase tracking-wider",
                          msg.role === "user"
                            ? "text-blue-400"
                            : msg.role === "assistant"
                            ? "text-cyan-400"
                            : msg.role === "tool"
                            ? "text-yellow-400"
                            : "text-gray-400"
                        )}
                      >
                        {msg.tool_name || msg.role}
                      </span>
                      {msg.model_used && (
                        <Badge
                          variant="outline"
                          className="text-[9px] bg-transparent text-gray-500 border-gray-700 py-0 h-4"
                        >
                          {msg.model_used}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {msg.latency_ms && (
                        <span className="text-[10px] text-gray-600">
                          {msg.latency_ms}ms
                        </span>
                      )}
                      <span className="text-[10px] text-gray-500">
                        {msg.created_at ? formatTimestamp(msg.created_at) : ""}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <p className="text-gray-200 text-xs leading-relaxed whitespace-pre-wrap break-words">
                    {displayContent ||
                      (msg.tool_name ? `[Tool: ${msg.tool_name}]` : "")}
                  </p>

                  {/* Expand toggle */}
                  {isLong && (
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
                          <ExpandIcon className="h-3 w-3" /> Show more
                        </>
                      )}
                    </button>
                  )}

                  {/* Token/cost row */}
                  {(msg.input_tokens || msg.output_tokens || msg.cost) && (
                    <div className="flex items-center gap-3 mt-2 pt-1.5 border-t border-gray-700/30 text-[10px] text-gray-500">
                      {msg.input_tokens && (
                        <span>{msg.input_tokens} in</span>
                      )}
                      {msg.output_tokens && (
                        <span>{msg.output_tokens} out</span>
                      )}
                      {msg.cost && (
                        <span>${msg.cost.toFixed(4)}</span>
                      )}
                    </div>
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
