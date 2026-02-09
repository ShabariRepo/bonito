"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare, X, Send, Sparkles, User, Zap, DollarSign,
  Shield, TrendingDown, ChevronRight, Wrench, PanelRightClose,
} from "lucide-react";
import { LoadingDots } from "@/components/ui/loading-dots";
import { API_URL } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  tools?: string[];
  timestamp: Date;
}

interface Suggestion {
  type: string;
  title: string;
  description: string;
  query?: string;
  action?: string;
  priority: string;
}

const QUICK_ACTIONS = [
  { label: "Cost Summary", query: "Give me a cost summary for this month", icon: DollarSign },
  { label: "Compliance Check", query: "What's our compliance status?", icon: Shield },
  { label: "Optimize Spending", query: "How can we optimize our AI spending?", icon: TrendingDown },
];

const TOOL_LABELS: Record<string, string> = {
  get_cost_summary: "Cost data",
  get_compliance_status: "Compliance checks",
  get_provider_status: "Provider health",
  get_model_recommendations: "Model catalog",
  get_usage_stats: "Gateway stats",
};

export function ChatPanel() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, streaming]);

  // Fetch suggestions when panel opens
  useEffect(() => {
    if (open && suggestions.length === 0) {
      fetch(`${API_URL}/api/ai/suggestions`)
        .then(r => r.json())
        .then(data => setSuggestions(data.suggestions || []))
        .catch(() => {});
    }
  }, [open]);

  const sendMessage = useCallback(async (text?: string) => {
    const msg = text || input;
    if (!msg.trim() || loading || streaming) return;
    setInput("");

    const userMsg: Message = { role: "user", content: msg, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);

    // Build history for context
    const history = messages.slice(-20).map(m => ({ role: m.role, content: m.content }));

    // Try streaming copilot first
    try {
      setStreaming(true);
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch(`${API_URL}/api/ai/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg, history, stream: true }),
        signal: controller.signal,
      });

      if (!res.ok || !res.body) throw new Error("Stream unavailable");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let content = "";
      let tools: string[] = [];

      // Add placeholder assistant message
      const assistantIdx = messages.length + 1; // +1 for the user msg we just added
      setMessages(prev => [...prev, { role: "assistant", content: "", tools: [], timestamp: new Date() }]);

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
              tools = payload.tools || [];
            } else if (payload.type === "content") {
              content += payload.text;
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last && last.role === "assistant") {
                  updated[updated.length - 1] = { ...last, content, tools };
                }
                return updated;
              });
            }
          } catch {}
        }
      }

      // Final update
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant") {
          updated[updated.length - 1] = { ...last, content, tools };
        }
        return updated;
      });
    } catch (e: any) {
      if (e.name === "AbortError") return;
      // Fallback to non-streaming chat
      try {
        setLoading(true);
        setStreaming(false);
        const res = await fetch(`${API_URL}/api/ai/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: msg, history }),
        });
        if (res.ok) {
          const data = await res.json();
          setMessages(prev => {
            // Remove empty assistant msg if present
            const cleaned = prev.filter(m => !(m.role === "assistant" && !m.content));
            return [...cleaned, {
              role: "assistant",
              content: data.message || "I'm not sure how to help with that.",
              timestamp: new Date(),
            }];
          });
        }
      } catch {
        setMessages(prev => {
          const cleaned = prev.filter(m => !(m.role === "assistant" && !m.content));
          return [...cleaned, { role: "assistant", content: "Sorry, something went wrong.", timestamp: new Date() }];
        });
      } finally {
        setLoading(false);
      }
    } finally {
      setStreaming(false);
      setLoading(false);
      abortRef.current = null;
    }
  }, [input, messages, loading, streaming]);

  const isEmpty = messages.length === 0;

  return (
    <>
      {/* Toggle button */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setOpen(!open)}
        className="fixed bottom-6 right-6 z-50 h-12 w-12 rounded-full bg-violet-600 text-white shadow-lg flex items-center justify-center hover:bg-violet-700 transition-colors"
      >
        <AnimatePresence mode="wait">
          {open ? (
            <motion.div key="x" initial={{ rotate: -90 }} animate={{ rotate: 0 }} exit={{ rotate: 90 }}>
              <X className="h-5 w-5" />
            </motion.div>
          ) : (
            <motion.div key="chat" initial={{ rotate: 90 }} animate={{ rotate: 0 }} exit={{ rotate: -90 }}>
              <MessageSquare className="h-5 w-5" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Sliding Panel */}
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[2px] lg:hidden"
              onClick={() => setOpen(false)}
            />

            {/* Panel — slides from right */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 400, damping: 35 }}
              className="fixed top-0 right-0 z-50 h-full w-full max-w-md border-l border-border bg-card shadow-2xl flex flex-col"
            >
              {/* Header */}
              <div className="flex items-center gap-2 border-b border-border px-4 py-3 shrink-0">
                <Sparkles className="h-5 w-5 text-violet-500" />
                <div className="flex-1">
                  <h3 className="text-sm font-semibold">Bonito Copilot</h3>
                  <p className="text-[10px] text-muted-foreground">Powered by Groq · sub-second responses</p>
                </div>
                <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <button onClick={() => setOpen(false)} className="ml-2 p-1 rounded hover:bg-accent transition-colors">
                  <PanelRightClose className="h-4 w-4 text-muted-foreground" />
                </button>
              </div>

              {/* Quick Actions Bar */}
              <div className="flex gap-2 px-4 py-2.5 border-b border-border shrink-0 overflow-x-auto">
                {QUICK_ACTIONS.map(action => (
                  <button
                    key={action.label}
                    onClick={() => sendMessage(action.query)}
                    className="flex items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:border-violet-500/40 hover:text-violet-400 transition-colors whitespace-nowrap shrink-0"
                  >
                    <action.icon className="h-3 w-3" />
                    {action.label}
                  </button>
                ))}
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {isEmpty && (
                  <div className="text-center py-8">
                    <motion.div animate={{ y: [0, -5, 0] }} transition={{ duration: 2, repeat: Infinity }}>
                      <Zap className="h-8 w-8 text-violet-500 mx-auto mb-3" />
                    </motion.div>
                    <p className="text-sm font-medium">Your AI Operations Copilot</p>
                    <p className="text-xs text-muted-foreground mt-1 mb-5">
                      Ask about costs, compliance, models, or provider health
                    </p>

                    {/* Suggestions from API */}
                    {suggestions.length > 0 && (
                      <div className="space-y-2 text-left max-w-xs mx-auto">
                        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Suggestions</p>
                        {suggestions.filter(s => s.query).map((s, i) => (
                          <button
                            key={i}
                            onClick={() => sendMessage(s.query!)}
                            className="w-full flex items-center gap-2 rounded-lg border border-border p-2.5 text-left hover:border-violet-500/30 transition-colors group"
                          >
                            <div className="flex-1">
                              <p className="text-xs font-medium">{s.title}</p>
                              <p className="text-[10px] text-muted-foreground">{s.description}</p>
                            </div>
                            <ChevronRight className="h-3 w-3 text-muted-foreground group-hover:text-violet-400 transition-colors" />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {messages.map((msg, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex gap-2 ${msg.role === "user" ? "justify-end" : ""}`}
                  >
                    {msg.role === "assistant" && (
                      <div className="shrink-0 h-6 w-6 rounded-full bg-violet-500/15 flex items-center justify-center mt-1">
                        <Sparkles className="h-3 w-3 text-violet-400" />
                      </div>
                    )}
                    <div className={`max-w-[85%] space-y-1.5 ${msg.role === "user" ? "text-right" : ""}`}>
                      {/* Tool badges */}
                      {msg.tools && msg.tools.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {msg.tools.map(t => (
                            <span key={t} className="inline-flex items-center gap-1 rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] text-violet-400">
                              <Wrench className="h-2.5 w-2.5" />
                              {TOOL_LABELS[t] || t}
                            </span>
                          ))}
                        </div>
                      )}

                      <div className={`rounded-lg px-3 py-2 text-sm ${
                        msg.role === "user"
                          ? "bg-violet-600 text-white"
                          : "bg-accent text-foreground"
                      }`}>
                        {msg.role === "assistant" ? (
                          <div
                            className="prose prose-sm prose-invert max-w-none [&_strong]:text-foreground [&_p]:my-1 [&_ul]:my-1 [&_li]:my-0.5"
                            dangerouslySetInnerHTML={{
                              __html: formatMarkdown(msg.content),
                            }}
                          />
                        ) : (
                          <p>{msg.content}</p>
                        )}
                      </div>
                    </div>
                    {msg.role === "user" && (
                      <div className="shrink-0 h-6 w-6 rounded-full bg-violet-600 flex items-center justify-center mt-1">
                        <User className="h-3 w-3 text-white" />
                      </div>
                    )}
                  </motion.div>
                ))}

                {loading && !streaming && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-2">
                    <div className="h-6 w-6 rounded-full bg-violet-500/15 flex items-center justify-center">
                      <Sparkles className="h-3 w-3 text-violet-400" />
                    </div>
                    <div className="bg-accent rounded-lg px-3 py-2">
                      <LoadingDots size="sm" />
                    </div>
                  </motion.div>
                )}

                <div ref={bottomRef} />
              </div>

              {/* Input */}
              <div className="border-t border-border p-3 shrink-0">
                <div className="flex items-center gap-2">
                  <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                    placeholder="Ask about costs, compliance, models..."
                    className="flex-1 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground"
                  />
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => sendMessage()}
                    disabled={!input.trim() || loading || streaming}
                    className="rounded-md bg-violet-600 p-1.5 text-white disabled:opacity-40 hover:bg-violet-700 transition-colors"
                  >
                    <Send className="h-4 w-4" />
                  </motion.button>
                </div>
                <p className="text-[10px] text-muted-foreground mt-1.5 text-center">
                  Bonito Copilot · Groq LLaMA 3.3 · Enterprise features require upgrade
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

/** Minimal markdown → HTML for assistant messages */
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
