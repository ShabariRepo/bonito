"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search, Sparkles, ArrowRight, Command, X, Zap,
  DollarSign, Box, Users, Shield, Loader2,
} from "lucide-react";
import { API_URL } from "@/lib/utils";
import { useRouter } from "next/navigation";

const SUGGESTIONS = [
  { text: "What's our spend this month?", icon: DollarSign },
  { text: "Show compliance status", icon: Shield },
  { text: "Recommend cheaper models", icon: Box },
  { text: "Who has admin access?", icon: Users },
  { text: "How can we optimize spending?", icon: Zap },
];

export function CommandBar() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [streamTools, setStreamTools] = useState<string[]>([]);
  const [streamDone, setStreamDone] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [history, setHistory] = useState<string[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const router = useRouter();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen(prev => !prev);
      }
      if (e.key === "Escape") {
        if (abortRef.current) abortRef.current.abort();
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (open) {
      setResult(null);
      setStreamContent("");
      setStreamTools([]);
      setStreamDone(false);
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const submit = useCallback(async (q?: string) => {
    const text = q || query;
    if (!text.trim() || loading) return;

    setLoading(true);
    setResult(null);
    setStreamContent("");
    setStreamTools([]);
    setStreamDone(false);

    // Try streaming copilot
    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch(`${API_URL}/api/ai/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: [], stream: true }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) throw new Error("Not available");

      setLoading(false);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let content = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const payload = JSON.parse(line.slice(6));
            if (payload.type === "tools") {
              setStreamTools(payload.tools || []);
            } else if (payload.type === "content") {
              content += payload.text;
              setStreamContent(content);
            } else if (payload.type === "done") {
              setStreamDone(true);
            }
          } catch {}
        }
      }

      setStreamDone(true);
      setHistory(prev => [text, ...prev.filter(h => h !== text)].slice(0, 5));
    } catch (e: any) {
      if (e.name === "AbortError") { setLoading(false); return; }

      // Fallback to non-streaming
      try {
        const res = await fetch(`${API_URL}/api/ai/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text }),
        });
        if (res.ok) {
          const data = await res.json();
          setResult(data);
          setHistory(prev => [text, ...prev.filter(h => h !== text)].slice(0, 5));
        }
      } catch {}
      setLoading(false);
    } finally {
      abortRef.current = null;
    }
  }, [query, loading]);

  const handleNav = (path: string) => {
    router.push(path);
    setOpen(false);
  };

  const showSuggestions = !result && !streamContent && !loading && !query;
  const hasStreamResult = streamContent.length > 0;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-black/50 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        >
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            onClick={e => e.stopPropagation()}
            className="w-full max-w-xl rounded-xl border border-border bg-card shadow-2xl overflow-hidden"
          >
            {/* Input */}
            <div className="flex items-center gap-3 border-b border-border px-4 py-3">
              <Sparkles className="h-5 w-5 text-violet-500 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => { setQuery(e.target.value); setResult(null); setStreamContent(""); setStreamDone(false); }}
                onKeyDown={e => {
                  if (e.key === "Enter") submit();
                  if (e.key === "ArrowDown") setSelectedIdx(i => Math.min(i + 1, SUGGESTIONS.length - 1));
                  if (e.key === "ArrowUp") setSelectedIdx(i => Math.max(i - 1, 0));
                }}
                placeholder="Ask Bonito Copilot anything..."
                className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground"
              />
              {loading && <Loader2 className="h-4 w-4 animate-spin text-violet-500" />}
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <kbd className="rounded border border-border px-1.5 py-0.5 text-[10px]">↵</kbd>
              </div>
            </div>

            {/* Suggestions */}
            {showSuggestions && (
              <div className="p-2">
                <p className="px-2 py-1 text-xs text-muted-foreground font-medium">Try asking</p>
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={s.text}
                    onClick={() => { setQuery(s.text); submit(s.text); }}
                    className={`w-full flex items-center gap-3 rounded-md px-3 py-2 text-sm text-left transition-colors ${
                      selectedIdx === i ? "bg-accent text-foreground" : "text-muted-foreground hover:bg-accent/50"
                    }`}
                  >
                    <s.icon className="h-4 w-4 shrink-0" />
                    {s.text}
                  </button>
                ))}
                {history.length > 0 && (
                  <>
                    <p className="px-2 py-1 mt-2 text-xs text-muted-foreground font-medium">Recent</p>
                    {history.map(h => (
                      <button
                        key={h}
                        onClick={() => { setQuery(h); submit(h); }}
                        className="w-full flex items-center gap-3 rounded-md px-3 py-2 text-sm text-left text-muted-foreground hover:bg-accent/50 transition-colors"
                      >
                        <Search className="h-4 w-4 shrink-0" />
                        {h}
                      </button>
                    ))}
                  </>
                )}
              </div>
            )}

            {/* Streaming Result */}
            {hasStreamResult && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                className="border-t border-border overflow-hidden"
              >
                <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
                  {/* Tool badges */}
                  {streamTools.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {streamTools.map(t => (
                        <span key={t} className="inline-flex items-center gap-1 rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] text-violet-400">
                          <Zap className="h-2.5 w-2.5" />
                          {t.replace(/^get_/, "").replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="flex items-start gap-3">
                    <div className="rounded-lg bg-violet-500/15 p-1.5 mt-0.5 shrink-0">
                      <Sparkles className="h-4 w-4 text-violet-400" />
                    </div>
                    <div className="flex-1 text-sm prose prose-sm prose-invert max-w-none [&_strong]:text-foreground">
                      <div dangerouslySetInnerHTML={{
                        __html: formatMarkdown(streamContent),
                      }} />
                      {!streamDone && (
                        <span className="inline-block w-1.5 h-4 bg-violet-400 animate-pulse ml-0.5 align-text-bottom rounded-sm" />
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Legacy non-streaming result */}
            <AnimatePresence>
              {result && !hasStreamResult && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="border-t border-border overflow-hidden"
                >
                  <div className="p-4 space-y-3">
                    <div className="flex items-start gap-3">
                      <div className="rounded-lg bg-violet-500/15 p-1.5 mt-0.5">
                        <Sparkles className="h-4 w-4 text-violet-400" />
                      </div>
                      <div className="flex-1 space-y-2">
                        <p className="text-sm" dangerouslySetInnerHTML={{
                          __html: (result.message || "").replace(/\*\*(.+?)\*\*/g, '<strong class="text-foreground">$1</strong>')
                        }} />

                        {result.data && typeof result.data === "object" && (
                          <div className="rounded-md bg-accent/50 p-3 space-y-1">
                            {Object.entries(result.data).map(([key, val]: [string, any]) => (
                              <div key={key} className="flex justify-between text-xs">
                                <span className="text-muted-foreground">{key.replace(/_/g, " ")}</span>
                                <span className="font-medium">{Array.isArray(val) ? `${val.length} items` : String(val)}</span>
                              </div>
                            ))}
                          </div>
                        )}

                        {result.action?.type === "navigate" && (
                          <button
                            onClick={() => handleNav(result.action.path)}
                            className="flex items-center gap-2 rounded-md bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 transition-colors"
                          >
                            View Details
                            <ArrowRight className="h-3 w-3" />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Footer */}
            <div className="flex items-center justify-between border-t border-border px-4 py-2 text-[10px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-violet-400" />
                Bonito Copilot · Groq
              </span>
              <div className="flex items-center gap-2">
                <span>ESC to close</span>
                <span>·</span>
                <span className="flex items-center gap-0.5"><Command className="h-3 w-3" />K to toggle</span>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/** Minimal markdown → HTML */
function formatMarkdown(text: string): string {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, '<code class="bg-accent/60 px-1 rounded text-xs">$1</code>')
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>[\s\S]*<\/li>)/g, "<ul class='list-disc pl-4'>$1</ul>")
    .replace(/\n{2,}/g, "</p><p>")
    .replace(/\n/g, "<br/>")
    .replace(/^(.*)$/, "<p>$1</p>");
}
