"use client";

/**
 * StudioChat — the full-bleed chat surface at `/studio`.
 *
 * Claude-Code-like layout: one column, snapshot-aware empty state, plan
 * cards rendered inline as Origami already does. No theme picker, no
 * watermark — clean by design. Phase 3 will polish plan-card visuals.
 */

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, MessageSquarePlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { PlanCard } from "../origami/PlanCard";
import SchematicBackground from "../SchematicBackground";
import { StudioMarkdown } from "./StudioMarkdown";
import { StudioOpener } from "./StudioOpener";
import { StudioReminderBanner } from "./StudioReminderBanner";
import { SwimmingFish } from "./SwimmingFish";
import { useStudioSession } from "./useStudioSession";

export function StudioChat() {
  const session = useStudioSession();
  const [draft, setDraft] = useState("");
  const scrollerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  // Container the schematic canvas sizes against, so the animation
  // stays inside Studio's chat surface instead of spilling across the
  // dashboard layout / sidebar.
  const chatRef = useRef<HTMLDivElement>(null);

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
    // Height accounts for the (dashboard) layout chrome above Studio:
    // notification-bell row (~52px on lg+), p-8 padding (32px top), and
    // the bottom padding (32px). Using 100dvh so mobile address-bar
    // collapse doesn't push the composer below the fold either.
    <div
      ref={chatRef}
      className="relative flex flex-col h-[calc(100dvh-9rem)] -mt-2 -mx-4 md:-mx-8 overflow-hidden"
    >
      {/* Animated schematic backdrop — same canvas used on the
          marketing landing, but here it's scoped to the chat container
          via `absolute inset-0` + a containerRef sizing hint. The
          schematic stays inside Studio's chat surface and doesn't
          spill over the sidebar or the dashboard chrome. */}
      <SchematicBackground
        className="absolute inset-0 pointer-events-none"
        containerRef={chatRef}
      />

      {/* All chat content sits in a z-10 layer above the canvas. */}
      <div className="relative z-10 flex flex-col h-full">
      {/* Header — minimal, brand + state */}
      <div className="border-b border-border/60 px-6 py-3 shrink-0 bg-background/50 backdrop-blur-sm">
        <div className="flex items-center justify-between max-w-3xl mx-auto">
          <div>
            <h1 className="text-base font-semibold text-foreground tracking-tight">
              Bonito
            </h1>
            <p className="text-[11px] text-muted-foreground -mt-0.5">Studio</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            {session.busy ? (
              <span className="inline-flex items-center gap-2">
                <SwimmingFish size={14} />
                thinking…
              </span>
            ) : (
              <span>ready</span>
            )}
            {session.messages.length > 0 && !session.busy && (
              <button
                onClick={session.clearChat}
                className="inline-flex items-center gap-1 hover:text-foreground transition-colors"
                title="Start a fresh conversation (history clears, org context stays)"
              >
                <MessageSquarePlus size={12} />
                New chat
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Snapshot-driven reminders — gentle nudges (no providers, broken
          providers). Renders nothing when the snapshot is healthy. */}
      <StudioReminderBanner snapshot={session.snapshot} />

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
                  autoDeploy
                  onEvent={(ev) => session.handleExternalEvent(ev as never)}
                />
              );
            }
            if (m.role === "user") {
              return (
                <div
                  key={m.id}
                  className="ml-auto max-w-[85%] px-4 py-2.5 rounded-2xl rounded-br-md text-sm bg-primary text-primary-foreground whitespace-pre-wrap"
                >
                  {m.text}
                </div>
              );
            }
            return (
              <div
                key={m.id}
                className="mr-auto max-w-[85%] px-4 py-2.5 rounded-2xl rounded-bl-md text-sm bg-muted text-foreground"
              >
                <StudioMarkdown text={m.text} />
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
                <SwimmingFish size={20} />
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
            <Textarea
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                // Enter sends; Shift+Enter inserts a newline like every
                // other modern chat composer.
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSend();
                }
              }}
              disabled={session.busy}
              placeholder="Tell Bonito what you want to do…"
              // min-h matches the prior h-10 visually for short prompts;
              // textarea grows with content up to the max-h cap so long
              // prompts stay readable without a separate modal.
              className="flex-1 min-h-[40px] max-h-[160px] resize-none py-2 leading-snug"
              rows={1}
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
            Bonito Studio · plans run automatically, no surprises
          </p>
        </div>
      </div>
      </div>{/* close z-10 chat layer */}
    </div>
  );
}
