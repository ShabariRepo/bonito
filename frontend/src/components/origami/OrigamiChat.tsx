"use client";

import { useEffect, useRef, useState } from "react";
import { Send, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PlanCard } from "./PlanCard";
import { OrigamiCraneLoader } from "./OrigamiCraneLoader";
import { OrigamiCraneWatermark } from "./OrigamiCraneWatermark";
import { ChatThemePicker } from "./ChatThemePicker";
import { useOrigamiChatTheme } from "./useOrigamiChatTheme";
import type { useOrigamiSession } from "./useOrigamiSession";

type Session = ReturnType<typeof useOrigamiSession>;

export function OrigamiChat({ session }: { session: Session }) {
  const [draft, setDraft] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);
  const { theme, themeId, setThemeId } = useOrigamiChatTheme();

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

  // Watermark is only shown on the default theme — themed surfaces have
  // their own color identity that conflicts with the lavender crane.
  const showWatermark = themeId === "default";

  return (
    <div className={`flex flex-col h-full ${theme.font}`}>
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-3 border-b shrink-0 ${theme.surfaceBg} ${theme.separatorClass}`}
      >
        <div className="flex items-center gap-2">
          <MessageSquare className={`h-4 w-4 ${theme.mutedTextClass}`} />
          <span className="text-sm font-semibold">Chat</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs ${theme.mutedTextClass}`}>
            {session.busy ? "thinking…" : "ready"}
          </span>
          <ChatThemePicker themeId={themeId} onChange={setThemeId} />
        </div>
      </div>

      {/* Scrolling body */}
      <div
        ref={scrollerRef}
        className={`flex-1 overflow-y-auto px-4 py-4 space-y-3 relative ${theme.scrollBg}`}
      >
        {showWatermark && <OrigamiCraneWatermark size={320} opacity={0.06} />}
        <div className="relative z-10 space-y-3">
          {session.messages.length === 0 && (
            <div className={`text-sm ${theme.mutedTextClass}`}>
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
                    ? `ml-auto ${theme.userBubble}`
                    : `mr-auto ${theme.assistantBubble}`
                }`}
              >
                {m.text}
                {m.streaming && (
                  <span
                    className={`inline-block w-1.5 h-3.5 ml-1 align-middle animate-pulse rounded-sm ${theme.cursorClass}`}
                  />
                )}
              </div>
            );
          })}
          {session.busy &&
            session.messages[session.messages.length - 1]?.role !== "assistant" && (
              <div className="flex items-center justify-start pl-1">
                <OrigamiCraneLoader size={48} label="Origami is folding a plan…" />
              </div>
            )}
        </div>
      </div>

      {/* Composer */}
      <div className={`px-3 py-3 shrink-0 ${theme.composerBg}`}>
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
            className={`flex-1 ${theme.inputClass}`}
          />
          <Button
            onClick={onSend}
            disabled={session.busy || !draft.trim()}
            size="icon"
            aria-label="Send"
            className={theme.sendBtnClass}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
