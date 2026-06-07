"use client";

import { useEffect, useRef, useState } from "react";
import { Palette, Check } from "lucide-react";
import { CHAT_THEME_LIST, type ChatThemeId } from "./chat-themes";

interface Props {
  themeId: ChatThemeId;
  onChange: (id: ChatThemeId) => void;
  /** Compact mode hides the label, just shows the icon */
  compact?: boolean;
}

export function ChatThemePicker({ themeId, onChange, compact = true }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  // Click-outside dismiss
  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    window.addEventListener("mousedown", onDown);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded hover:bg-accent/30"
        title="Pick a chat theme"
      >
        <Palette className="h-3.5 w-3.5" />
        {!compact && <span>Theme</span>}
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-1.5 z-50 w-56 rounded-md border border-border bg-popover shadow-lg overflow-hidden"
          role="menu"
        >
          <div className="px-3 py-2 text-[10px] uppercase tracking-wider text-muted-foreground border-b border-border">
            Chat theme
          </div>
          <ul className="py-1 max-h-72 overflow-y-auto">
            {CHAT_THEME_LIST.map((t) => {
              const active = t.id === themeId;
              return (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onChange(t.id);
                      setOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 flex items-center gap-2 text-sm hover:bg-accent/40 transition ${
                      active ? "bg-accent/50" : ""
                    }`}
                    role="menuitem"
                  >
                    {/* Color swatch row */}
                    <div className="flex shrink-0 rounded overflow-hidden border border-border/60">
                      {t.swatch.map((c, i) => (
                        <span
                          key={i}
                          className="block w-3 h-4"
                          style={{ backgroundColor: c }}
                        />
                      ))}
                    </div>
                    <span className="flex-1 truncate">{t.label}</span>
                    {active && <Check className="h-3.5 w-3.5 text-primary" />}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
