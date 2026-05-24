"use client";

import { memo } from "react";
import {
  Bot,
  Activity,
  MessageSquare,
  X,
  ChevronRight,
  User,
  Cpu,
  Clock,
  ArrowRight,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ── Types ──────────────────────────────────────────────────────────

export interface BreadcrumbNode {
  id: string;
  name: string;
  status: string;
  model_id: string;
  description?: string | null;
  total_runs: number;
  total_cost: number;
  last_active_at?: string | null;
  message_count: number;
  position?: { x: number; y: number } | null;
}

export interface AgentMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string | null;
  tool_name?: string | null;
  tool_calls?: any;
  model_used?: string | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  cost?: number | null;
  latency_ms?: number | null;
  sequence: number;
  created_at: string | null;
}

// ── Helpers ────────────────────────────────────────────────────────

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

function relativeTime(dateString: string): string {
  const now = Date.now();
  const then = new Date(dateString).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// ── Component ──────────────────────────────────────────────────────

interface Props {
  agent: BreadcrumbNode;
  messages: AgentMessage[];
  messagesLoading: boolean;
  totalMessages: number;
  open: boolean;
  onClose: () => void;
  onExpand: () => void;
}

export const BreadcrumbSummaryPanel = memo(function BreadcrumbSummaryPanel({
  agent,
  messages,
  messagesLoading,
  totalMessages,
  open,
  onClose,
  onExpand,
}: Props) {
  return (
    <div
      className={cn(
        "absolute top-0 right-0 h-full w-[340px] sm:w-[400px] max-w-[90vw] bg-[#12122a] border-l border-gray-800 shadow-2xl transition-transform duration-300 z-20 flex flex-col",
        open ? "translate-x-0" : "translate-x-full"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <Bot className="h-4 w-4 text-cyan-500 flex-shrink-0" />
          <h3 className="font-semibold text-white text-sm truncate">
            {agent.name}
          </h3>
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

      {/* Model badge */}
      <div className="px-4 pt-3 pb-2 flex-shrink-0">
        <Badge
          variant="outline"
          className="text-[10px] bg-gray-500/10 text-gray-400 border-gray-500/30"
        >
          <Cpu className="w-3 h-3 mr-1" />
          {agent.model_id}
        </Badge>
      </div>

      {/* Stats grid */}
      <div className="px-4 pb-3 border-b border-gray-800 flex-shrink-0">
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div className="rounded-md bg-[#1a1a2e] px-3 py-2">
            <div className="text-gray-500 mb-0.5">Runs</div>
            <div className="text-white font-semibold text-lg">
              {agent.total_runs}
            </div>
          </div>
          <div className="rounded-md bg-[#1a1a2e] px-3 py-2">
            <div className="text-gray-500 mb-0.5">Messages</div>
            <div className="text-white font-semibold text-lg">
              {agent.message_count}
            </div>
          </div>
          <div className="rounded-md bg-[#1a1a2e] px-3 py-2">
            <div className="text-gray-500 mb-0.5">Last active</div>
            <div className="text-white font-medium text-xs mt-1">
              {agent.last_active_at
                ? relativeTime(agent.last_active_at)
                : "—"}
            </div>
          </div>
        </div>
      </div>

      {/* Recent messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-2">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">
            Recent Activity
          </div>
          {totalMessages > 0 && (
            <span className="text-[10px] text-gray-500">
              {totalMessages} total
            </span>
          )}
        </div>

        {messagesLoading ? (
          <div className="space-y-2">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="animate-pulse">
                <div className="h-14 bg-gray-800/50 rounded-lg" />
              </div>
            ))}
          </div>
        ) : messages.length === 0 ? (
          <div className="text-center py-8">
            <MessageSquare className="mx-auto h-8 w-8 text-gray-600 mb-2" />
            <p className="text-gray-500 text-sm">No messages in this period</p>
          </div>
        ) : (
          messages.slice(0, 5).map((msg) => (
            <div
              key={msg.id}
              className="rounded-lg px-3 py-2 text-xs bg-[#1a1a2e] border border-gray-700/50 hover:border-gray-600 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
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
                </div>
                <span className="text-[10px] text-gray-500">
                  {msg.created_at ? relativeTime(msg.created_at) : ""}
                </span>
              </div>
              <p className="text-gray-300 leading-relaxed truncate">
                {msg.content
                  ? msg.content.slice(0, 120)
                  : msg.tool_name
                  ? `[${msg.tool_name}]`
                  : ""}
              </p>
            </div>
          ))
        )}
      </div>

      {/* See all button */}
      {totalMessages > 5 && (
        <div className="px-4 py-3 border-t border-gray-800 flex-shrink-0">
          <button
            onClick={onExpand}
            className="w-full flex items-center justify-center gap-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 px-4 py-2.5 text-sm text-cyan-400 hover:bg-cyan-500/20 transition-colors"
          >
            See all {totalMessages} messages
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
});
