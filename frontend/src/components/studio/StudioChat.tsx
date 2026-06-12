"use client";

/**
 * StudioChat — the full-bleed chat surface at `/studio`.
 *
 * Claude-Code-like layout: one column, snapshot-aware empty state, plan
 * cards rendered inline as Origami already does. No theme picker, no
 * watermark — clean by design. Phase 3 will polish plan-card visuals.
 */

import { useEffect, useRef, useState } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PlanCard } from "../origami/PlanCard";
import { StudioOpener } from "./StudioOpener";
import { useStudioSession } from "./useStudioSession";

export function StudioChat() {
  const session = useStudioSession();
  const [draft, setDraft] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollerRef.current?.scrollTo({
      top: scrollerRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [session.messages, session.busy]);

  async function onSend(text?: string) {
    const message = (text ?? draft).trim();
    if (!message) return;
    setDraft("");
    await session.send(message);
  }

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] -mt-2 -mx-4 md:-mx-8">
      {/* Header — minimal, brand + state */}
      <div className="border-b border-border/60 px-6 py-3 shrink-0 bg-background/50 backdrop-blur-sm">
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          <div>
            <h1 className="text-base font-semibold text-foreground tracking-tight">
              Bonito
            </h1>
            <p className="text-[11px] text-muted-foreground -mt-0.5">Studio</p>
          </div>
          <div className="text-xs text-muted-foreground">
            {session.busy ? (
              <span className="inline-flex items-center gap-1.5">
                <Loader2 size={11} className="animate-spin" />
                thinking…
              </span>
            ) : (
              <span>ready</span>
            )}
          </div>
        </div>
      </div>

      {/* Scrolling body */}
      <div
        ref={scrollerRef}
        className="flex-1 overflow-y-auto px-4 md:px-6 py-4"
      >
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Empty state — snapshot-aware opener */}
          {session.messages.length === 0 && !session.snapshotLoading && (
            <StudioOpener
              snapshot={session.snapshot}
              onChipClick={(prompt) => {
                setDraft("");
                onSend(prompt);
                inputRef.current?.focus();
              }}
            />
          )}

          {/* Loading state for snapshot */}
          {session.messages.length === 0 && session.snapshotLoading && (
            <div className="pt-12 text-center">
              <Loader2
                size={20}
                className="animate-spin text-muted-foreground mx-auto"
              />
              <p className="text-xs text-muted-foreground mt-2">
                Reading your org…
              </p>
            </div>
          )}

          {/* Messages */}
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
                className={
                  m.role === "user"
                    ? "ml-auto max-w-[85%] px-4 py-2.5 rounded-2xl rounded-br-md text-sm bg-primary text-primary-foreground whitespace-pre-wrap"
                    : "mr-auto max-w-[85%] px-4 py-2.5 rounded-2xl rounded-bl-md text-sm bg-muted text-foreground whitespace-pre-wrap leading-relaxed"
                }
              >
                {m.text}
                {m.streaming && (
                  <span className="inline-block w-1.5 h-3.5 ml-1 align-middle animate-pulse rounded-sm bg-current opacity-60" />
                )}
              </div>
            );
          })}

          {/* Thinking indicator when nothing has streamed yet for this turn */}
          {session.busy &&
            session.messages[session.messages.length - 1]?.role === "user" && (
              <div className="flex items-center gap-2 pl-1">
                <Loader2 size={14} className="animate-spin text-muted-foreground" />
                <span className="text-xs text-muted-foreground">
                  thinking…
                </span>
              </div>
            )}
        </div>
      </div>

      {/* Composer */}
      <div className="border-t border-border/60 px-4 md:px-6 py-3 shrink-0 bg-background/50">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2 items-end">
            <Input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSend();
                }
              }}
              disabled={session.busy}
              placeholder="Tell Bonito what you want to do…"
              className="flex-1 h-10"
              autoFocus
            />
            <Button
              onClick={() => onSend()}
              disabled={session.busy || !draft.trim()}
              size="icon"
              aria-label="Send"
              className="h-10 w-10"
            >
              <Send size={15} />
            </Button>
          </div>
          <p className="text-[10px] text-muted-foreground/70 mt-1.5 text-center">
            Bonito Studio · plan-cards run on confirmation, no surprises
          </p>
        </div>
      </div>
    </div>
  );
}
