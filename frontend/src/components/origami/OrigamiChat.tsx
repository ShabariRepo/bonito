"use client";

/**
 * OrigamiChat — the left-side chat panel. State (messages, busy, etc.) is
 * owned by useOrigamiSession (hoisted into OrigamiWorkspace) so the
 * right-side workspace can react to the same SSE event stream.
 *
 * Render-only: takes a session object from useOrigamiSession and shows
 * the chat history + plan cards + input.
 */

import { useEffect, useRef, useState } from "react";
import { PlanCard } from "./PlanCard";
import type { useOrigamiSession } from "./useOrigamiSession";

type Session = ReturnType<typeof useOrigamiSession>;

export function OrigamiChat({ session }: { session: Session }) {
  const [draft, setDraft] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [session.messages, session.busy]);

  async function onSend() {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    await session.send(text);
  }

  return (
    <>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1a1a1a]">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">Origami</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1a1a1a] text-[#888]">
            Phase 3
          </span>
        </div>
        <div className="text-[10px] text-[#666]">
          {session.busy ? "thinking…" : "ready"}
        </div>
      </div>

      {/* Body */}
      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
      >
        {session.messages.length === 0 && (
          <div className="text-sm text-[#777]">
            Hi — I&apos;m Origami. I can help you plan and deploy agents,
            knowledge bases, projects, and gateway keys. Tell me what you want
            to build.
          </div>
        )}
        {session.messages.map((m) => {
          if (m.role === "plan" && m.plan) {
            return (
              <PlanCard
                key={m.id}
                plan={m.plan}
                onEvent={(ev) => session.handleExternalEvent(ev as never)}
              />
            );
          }
          return (
            <div
              key={m.id}
              className={`max-w-[90%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
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
          );
        })}
        {session.busy && session.messages[session.messages.length - 1]?.role !== "assistant" && (
          <div className="text-xs text-[#666] italic">Origami is thinking…</div>
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
                onSend();
              }
            }}
            disabled={session.busy}
            placeholder="Tell Origami what to build…"
            className="flex-1 bg-[#111] border border-[#1a1a1a] rounded px-3 py-2 text-sm focus:outline-none focus:border-[#7c3aed] disabled:opacity-50"
          />
          <button
            onClick={onSend}
            disabled={session.busy || !draft.trim()}
            className="px-4 py-2 bg-[#7c3aed] text-white rounded text-sm font-medium hover:bg-[#6d28d9] disabled:opacity-40"
          >
            Send
          </button>
        </div>
      </div>
    </>
  );
}
