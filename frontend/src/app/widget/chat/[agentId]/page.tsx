"use client";

import { useState, useRef, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Send, Bot, User } from "lucide-react";
import { API_URL } from "@/lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface WidgetConfig {
  agent_id: string;
  agent_name: string;
  welcome_message: string;
  suggested_questions: string[];
  theme: string;
  accent_color: string;
}

export default function WidgetChatPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const agentId = params.agentId as string;
  const themeParam = searchParams.get("theme") || "light";

  const [config, setConfig] = useState<WidgetConfig | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isDark = themeParam === "dark";
  const accentColor = config?.accent_color || "#6366f1";

  useEffect(() => {
    fetchConfig();
  }, [agentId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Send accent color to parent
  useEffect(() => {
    if (config?.accent_color && window.parent !== window) {
      window.parent.postMessage(
        { source: "bonbon-widget", type: "accent", color: config.accent_color },
        "*"
      );
    }
  }, [config]);

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/widget/${agentId}/config`);
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      }
    } catch {
      /* widget not available */
    } finally {
      setConfigLoading(false);
    }
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text.trim(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/widget/${agentId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text.trim(),
          session_id: sessionId,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        setMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: data.content || "I'm sorry, I couldn't process that.",
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${Date.now()}`,
            role: "assistant",
            content: "Sorry, something went wrong. Please try again.",
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: "Unable to connect. Please check your connection.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleClose = () => {
    if (window.parent !== window) {
      window.parent.postMessage({ source: "bonbon-widget", type: "close" }, "*");
    }
  };

  if (configLoading) {
    return (
      <div
        className="h-screen flex items-center justify-center"
        style={{ backgroundColor: isDark ? "#1a1a2e" : "#ffffff" }}
      >
        <div
          className="w-8 h-8 rounded-full border-2 border-t-transparent animate-spin"
          style={{ borderColor: `${accentColor} transparent ${accentColor} ${accentColor}` }}
        />
      </div>
    );
  }

  if (!config) {
    return (
      <div
        className="h-screen flex items-center justify-center p-6 text-center"
        style={{
          backgroundColor: isDark ? "#1a1a2e" : "#ffffff",
          color: isDark ? "#9ca3af" : "#6b7280",
        }}
      >
        <p className="text-sm">Widget not available for this agent.</p>
      </div>
    );
  }

  return (
    <div
      className="h-screen flex flex-col"
      style={{
        backgroundColor: isDark ? "#1a1a2e" : "#ffffff",
        color: isDark ? "#e5e7eb" : "#111827",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 shrink-0"
        style={{ backgroundColor: accentColor }}
      >
        <div className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-white" />
          <span className="text-white font-medium text-sm">{config.agent_name}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {/* Welcome */}
        {messages.length === 0 && (
          <div className="space-y-3">
            <div
              className="rounded-xl px-3 py-2.5 text-sm max-w-[85%]"
              style={{
                backgroundColor: isDark ? "#2a2a3e" : "#f3f4f6",
                color: isDark ? "#e5e7eb" : "#111827",
              }}
            >
              {config.welcome_message}
            </div>
            {config.suggested_questions.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {config.suggested_questions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(q)}
                    className="text-xs px-3 py-1.5 rounded-full transition-colors hover:opacity-80"
                    style={{
                      border: `1px solid ${isDark ? "#374151" : "#e5e7eb"}`,
                      color: isDark ? "#9ca3af" : "#6b7280",
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className="rounded-xl px-3 py-2.5 text-sm max-w-[85%] whitespace-pre-wrap"
              style={
                msg.role === "user"
                  ? { backgroundColor: accentColor, color: "#ffffff" }
                  : {
                      backgroundColor: isDark ? "#2a2a3e" : "#f3f4f6",
                      color: isDark ? "#e5e7eb" : "#111827",
                    }
              }
            >
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div
              className="rounded-xl px-4 py-3"
              style={{ backgroundColor: isDark ? "#2a2a3e" : "#f3f4f6" }}
            >
              <div className="flex gap-1">
                {[0, 150, 300].map((delay) => (
                  <div
                    key={delay}
                    className="w-2 h-2 rounded-full animate-bounce"
                    style={{
                      backgroundColor: isDark ? "#6b7280" : "#9ca3af",
                      animationDelay: `${delay}ms`,
                    }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Talk to human */}
      <div
        className="px-4 py-2 text-center shrink-0"
        style={{ borderTop: `1px solid ${isDark ? "#374151" : "#e5e7eb"}` }}
      >
        <button
          className="text-xs hover:underline"
          style={{ color: isDark ? "#6b7280" : "#9ca3af" }}
        >
          Talk to a human →
        </button>
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 px-3 py-3 shrink-0"
        style={{ borderTop: `1px solid ${isDark ? "#374151" : "#e5e7eb"}` }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={loading}
          className="flex-1 text-sm outline-none bg-transparent"
          style={{ color: isDark ? "#e5e7eb" : "#111827" }}
        />
        <button
          type="submit"
          disabled={!input.trim() || loading}
          className="p-2 rounded-lg transition-opacity disabled:opacity-40"
          style={{ backgroundColor: accentColor, color: "#ffffff" }}
        >
          <Send className="h-4 w-4" />
        </button>
      </form>

      {/* Branding */}
      <div
        className="text-center py-1.5 text-xs shrink-0"
        style={{ color: isDark ? "#4b5563" : "#d1d5db" }}
      >
        Powered by <a href="https://getbonito.com" target="_blank" rel="noopener noreferrer" className="hover:underline" style={{ color: isDark ? "#6b7280" : "#9ca3af" }}>Bonito</a>
      </div>
    </div>
  );
}
