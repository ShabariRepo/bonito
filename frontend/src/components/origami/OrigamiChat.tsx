"use client";

/**
 * OrigamiChat — Phase 1 skeleton.
 *
 * Minimal chat UI that calls POST /api/origami/turn and parses the SSE
 * event stream. Renders messages + an activity log for tool calls.
 *
 * Workspace pane (Resources grid, plan cards, etc.) lands in Phase 3 —
 * see docs/ORIGAMI-MVP-PLAN.md "Workspace UX" section.
 */

import { useEffect, useRef, useState } from "react";
import { getAccessToken } from "@/lib/auth";
import { API_URL } from "@/lib/utils";

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  streaming?: boolean;  // true while tokens are still arriving for this message
};

type ActivityEntry = {
  id: string;
  tool: string;
  status: "running" | "success" | "error";
  startedAt: number;
  completedAt?: number;
  summary?: Record<string, unknown>;
  error?: string;
};

type OrigamiEvent =
  | { type: "turn_started"; conversation_id?: string; session_id?: string; tier?: string }
  | { type: "message_token"; token: string }
  | { type: "message_complete"; text: string }
  | { type: "tool_started"; tool_name: string; tool_call_id: string }
  | {
      type: "tool_completed";
      tool_name: string;
      tool_call_id: string;
      result_summary?: Record<string, unknown>;
    }
  | { type: "tool_failed"; tool_name: string; tool_call_id?: string; error: string }
  | { type: "done"; finish_reason?: string }
  | { type: "error"; code: string; message: string };

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function OrigamiChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activity, setActivity] = useState<ActivityEntry[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom whenever messages change
    scrollerRef.current?.scrollTo({ top: scrollerRef.current.scrollHeight });
  }, [messages, activity]);

  async function send() {
    const text = draft.trim();
    if (!text || busy) return;

    const userMsg: ChatMessage = { id: uid(), role: "user", text };
    setMessages((m) => [...m, userMsg]);
    setDraft("");
    setBusy(true);

    const token = getAccessToken();
    if (!token) {
      setMessages((m) => [
        ...m,
        { id: uid(), role: "assistant", text: "You're not signed in." },
      ]);
      setBusy(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/origami/turn`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text }),
      });

      if (!res.ok || !res.body) {
        const txt = await res.text();
        setMessages((m) => [
          ...m,
          { id: uid(), role: "assistant", text: `Error: ${res.status} ${txt}` },
        ]);
        setBusy(false);
        return;
      }

      // Stream + parse SSE
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by double newlines
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6);
          try {
            const ev: OrigamiEvent = JSON.parse(json);
            handleEvent(ev);
          } catch (e) {
            console.warn("Origami: bad SSE chunk", json, e);
          }
        }
      }
    } catch (e) {
      setMessages((m) => [
        ...m,
        {
          id: uid(),
          role: "assistant",
          text: `Network error: ${e instanceof Error ? e.message : String(e)}`,
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  function handleEvent(ev: OrigamiEvent) {
    switch (ev.type) {
      case "turn_started":
        // No-op for skeleton; will use conversation_id in Phase 2
        break;
      case "message_token":
        // Append to an in-flight assistant message, or start one if none
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last?.role === "assistant" && last.streaming) {
            return [
              ...m.slice(0, -1),
              { ...last, text: last.text + ev.token },
            ];
          }
          return [
            ...m,
            { id: uid(), role: "assistant", text: ev.token, streaming: true },
          ];
        });
        break;
      case "message_complete":
        // Reconcile to the full text (in case tokens were dropped) and mark
        // the message as no-longer-streaming so the typewriter cursor stops.
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last?.role === "assistant" && last.streaming) {
            return [
              ...m.slice(0, -1),
              { ...last, text: ev.text, streaming: false },
            ];
          }
          // No prior streaming message — append fully formed (non-stream path)
          return [
            ...m,
            { id: uid(), role: "assistant", text: ev.text },
          ];
        });
        break;
      case "tool_started":
        setActivity((a) => [
          ...a,
          {
            id: ev.tool_call_id,
            tool: ev.tool_name,
            status: "running",
            startedAt: Date.now(),
          },
        ]);
        break;
      case "tool_completed":
        setActivity((a) =>
          a.map((entry) =>
            entry.id === ev.tool_call_id
              ? {
                  ...entry,
                  status: "success" as const,
                  completedAt: Date.now(),
                  summary: ev.result_summary,
                }
              : entry,
          ),
        );
        break;
      case "tool_failed":
        setActivity((a) =>
          a.map((entry) =>
            entry.id === ev.tool_call_id
              ? {
                  ...entry,
                  status: "error" as const,
                  completedAt: Date.now(),
                  error: ev.error,
                }
              : entry,
          ),
        );
        break;
      case "done":
        // Ensure any still-streaming assistant message is marked complete
        setMessages((m) => {
          const last = m[m.length - 1];
          if (last?.role === "assistant" && last.streaming) {
            return [...m.slice(0, -1), { ...last, streaming: false }];
          }
          return m;
        });
        break;
      case "error":
        setMessages((m) => [
          ...m,
          {
            id: uid(),
            role: "assistant",
            text: `Origami error (${ev.code}): ${ev.message}`,
          },
        ]);
        break;
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] text-[#eee]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a]">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">Origami</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">
            Phase 1 skeleton
          </span>
        </div>
        <button
          className="text-xs text-[#888] hover:text-[#ccc]"
          onClick={() => setShowActivity((v) => !v)}
        >
          {showActivity ? "Hide activity" : `Activity (${activity.length})`}
        </button>
      </div>

      {/* Body */}
      <div className="flex flex-1 min-h-0">
        {/* Chat scroller */}
        <div
          ref={scrollerRef}
          className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
        >
          {messages.length === 0 && (
            <div className="text-sm text-[#777]">
              Hi — I'm Origami. Ask me about your org, models, or usage.
            </div>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`max-w-[85%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "ml-auto bg-[#7c3aed] text-white"
                  : "mr-auto bg-[#1a1a1a] text-[#ddd]"
              }`}
            >
              {m.text}
              {m.streaming && (
                <span className="inline-block w-1.5 h-3.5 bg-[#7c3aed] ml-1 align-middle animate-pulse" />
              )}
            </div>
          ))}
          {busy && messages[messages.length - 1]?.role !== "assistant" && (
            <div className="text-xs text-[#666] italic">Origami is thinking…</div>
          )}
        </div>

        {/* Activity panel (toggle) */}
        {showActivity && (
          <div className="w-80 border-l border-[#1a1a1a] overflow-y-auto px-3 py-3 text-xs">
            <div className="text-[#888] uppercase tracking-wider mb-2">
              Activity log
            </div>
            {activity.length === 0 && (
              <div className="text-[#555]">No tool calls yet.</div>
            )}
            {activity.map((a) => (
              <div
                key={a.id}
                className="mb-2 p-2 rounded bg-[#111] border border-[#1a1a1a]"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono">{a.tool}</span>
                  <span
                    className={
                      a.status === "success"
                        ? "text-green-400"
                        : a.status === "error"
                          ? "text-red-400"
                          : "text-yellow-400"
                    }
                  >
                    {a.status}
                  </span>
                </div>
                {a.completedAt && (
                  <div className="text-[#666] mt-1">
                    {a.completedAt - a.startedAt}ms
                  </div>
                )}
                {a.summary && (
                  <pre className="text-[#777] mt-1 overflow-x-auto">
                    {JSON.stringify(a.summary, null, 2)}
                  </pre>
                )}
                {a.error && (
                  <div className="text-red-400 mt-1">{a.error}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-[#1a1a1a] px-3 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            disabled={busy}
            placeholder="Ask Origami…"
            className="flex-1 bg-[#111] border border-[#1a1a1a] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#7c3aed] disabled:opacity-50"
          />
          <button
            onClick={send}
            disabled={busy || !draft.trim()}
            className="px-4 py-2 bg-[#7c3aed] text-white rounded text-sm font-medium hover:bg-[#6d28d9] disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
