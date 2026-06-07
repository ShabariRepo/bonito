"use client";

/**
 * OrigamiPanel — embedded slide-in chat available from any dashboard page.
 *
 * Lives at the layout level so users on /agents, /providers, /gateway,
 * /knowledge-base, etc. can pop Origami open without losing context.
 * Cmd+J toggles. Hosts a stripped-down chat (no workspace pane) plus a
 * button that promotes the conversation to the full /origami route.
 *
 * State (messages, resources, etc.) is owned by useOrigamiSession so a
 * conversation started in the panel keeps going if the user later
 * navigates to /origami — that's wired in a follow-up by sharing the
 * session via context.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Wand2, X, Maximize2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { OrigamiChat } from "./OrigamiChat";
import { useOrigamiSession } from "./useOrigamiSession";

const TOGGLE_KEY = "j"; // Cmd+J (Mac) / Ctrl+J (Win/Linux)

export function OrigamiPanel() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const session = useOrigamiSession();

  // Keyboard shortcut to toggle the panel
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === TOGGLE_KEY) {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape" && open) {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      {/* Floating launcher — bottom-right when closed */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-30 flex items-center gap-2 px-4 py-2.5 rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-all hover:scale-105 group"
          aria-label="Ask Origami (Cmd+J)"
          title="Ask Origami — Cmd+J"
        >
          <Wand2 className="h-4 w-4" />
          <span className="text-sm font-medium">Ask Origami</span>
          <span className="text-[10px] opacity-60 px-1.5 py-0.5 rounded bg-primary-foreground/10 font-mono">
            ⌘J
          </span>
        </button>
      )}

      {/* Slide-in panel */}
      <div
        className={`fixed top-0 right-0 z-40 h-screen bg-card border-l border-border shadow-2xl transition-transform duration-300 ease-in-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        style={{ width: "min(440px, 100vw)" }}
        aria-hidden={!open}
      >
        <div className="flex flex-col h-full">
          {/* Panel header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Wand2 className="h-4 w-4 text-primary" />
              <span className="text-sm font-semibold">Origami</span>
              <Badge variant="outline" className="text-[10px] px-1.5">
                Panel
              </Badge>
            </div>
            <div className="flex items-center gap-1">
              <Button
                onClick={() => {
                  setOpen(false);
                  router.push("/origami");
                }}
                size="sm"
                variant="ghost"
                title="Open full workspace"
                className="h-8 w-8 p-0"
              >
                <Maximize2 className="h-4 w-4" />
              </Button>
              <Button
                onClick={() => setOpen(false)}
                size="sm"
                variant="ghost"
                title="Close (Esc)"
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Chat fills the rest */}
          <div className="flex-1 min-h-0">
            <OrigamiChat session={session} />
          </div>
        </div>
      </div>
    </>
  );
}
