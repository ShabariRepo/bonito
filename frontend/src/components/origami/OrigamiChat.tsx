"use client";

import { useEffect, useRef, useState } from "react";
import { Send, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PlanCard } from "./PlanCard";
import { OrigamiCraneLoader } from "./OrigamiCraneLoader";
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
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-semibold">Chat</span>
        </div>
        <span className="text-xs text-muted-foreground">
          {session.busy ? "thinking…" : "ready"}
        </span>
      </div>

      {/* Scrolling body */}
      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
      >
        {session.messages.length === 0 && (
          <div className="text-sm text-muted-foreground">
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
                  ? "ml-auto bg-primary text-primary-foreground"
                  : "mr-auto bg-muted text-foreground border border-border"
              }`}
            >
              {m.text}
              {m.streaming && (
                <span className="inline-block w-1.5 h-3.5 bg-primary ml-1 align-middle animate-pulse rounded-sm" />
              )}
            </div>
          );
        })}
        {session.busy && session.messages[session.messages.length - 1]?.role !== "assistant" && (
          <div className="flex items-center justify-start pl-1">
            <OrigamiCraneLoader size={48} label="Origami is folding a plan…" />
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="border-t border-border px-3 py-3 shrink-0">
        <div className="flex gap-2">
          <Input
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
            className="flex-1"
          />
          <Button
            onClick={onSend}
            disabled={session.busy || !draft.trim()}
            size="icon"
            aria-label="Send"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
