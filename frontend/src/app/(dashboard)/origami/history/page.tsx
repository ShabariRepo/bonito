"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquare,
  Download,
  Wand2,
  Bot,
  User,
  Rocket,
  Calendar,
  Hash,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { apiRequest } from "@/lib/auth";
import { API_URL } from "@/lib/utils";
import { getAccessToken } from "@/lib/auth";

type ConversationListItem = {
  conversation_id: string;
  title: string;
  preview: string;
  message_count: number;
  plan_count: number;
  first_at: string | null;
  last_at: string | null;
};

type Message = {
  id: string;
  role: "user" | "assistant" | "plan" | "system";
  content: string;
  model_used: string | null;
  synthesized: boolean;
  extra_metadata: Record<string, unknown> | null;
  created_at: string | null;
};

function fmtAgo(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const ms = Date.now() - d.getTime();
  const m = Math.floor(ms / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const days = Math.floor(h / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}

function fmtFullTime(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString();
}

export default function OrigamiHistoryPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[] | null>(null);
  const [loadingMessages, setLoadingMessages] = useState(false);

  useEffect(() => {
    apiRequest("/api/origami/conversations")
      .then((r) => {
        const data = r as unknown as { conversations: ConversationListItem[] };
        setConversations(data.conversations || []);
        if (data.conversations?.[0]) {
          setSelectedId(data.conversations[0].conversation_id);
        }
      })
      .catch(() => setConversations([]))
      .finally(() => setLoadingList(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setLoadingMessages(true);
    setMessages(null);
    apiRequest(`/api/origami/conversations/${selectedId}`)
      .then((r) => {
        const data = r as unknown as { messages: Message[] };
        setMessages(data.messages || []);
      })
      .catch(() => setMessages([]))
      .finally(() => setLoadingMessages(false));
  }, [selectedId]);

  function download(fmt: "json" | "md") {
    if (!selectedId) return;
    const token = getAccessToken();
    if (!token) return;
    // Construct a download via fetch + blob so we can attach auth header
    fetch(`${API_URL}/api/origami/conversations/${selectedId}/download?fmt=${fmt}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `origami-conversation-${selectedId.slice(0, 8)}.${fmt}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      });
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Conversation history"
        description="Every Origami chat you've had, with the assistant's replies and plan cards. View, search, and download."
        breadcrumbs={[
          { label: "Origami", href: "/origami" },
          { label: "History" },
        ]}
        actions={
          <Link href="/origami">
            <Button variant="outline" size="sm" className="gap-1.5">
              <Wand2 className="h-3.5 w-3.5" />
              New chat
            </Button>
          </Link>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 min-h-[calc(100vh-14rem)]">
        {/* Left: conversation list */}
        <Card className="lg:col-span-2 p-0 overflow-hidden flex flex-col">
          <CardHeader className="border-b border-border">
            <CardTitle className="text-base flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              Conversations
              <Badge variant="outline" className="ml-auto text-xs">
                {conversations.length}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 flex-1 overflow-y-auto">
            {loadingList && (
              <div className="px-4 py-6 text-sm text-muted-foreground">
                Loading…
              </div>
            )}
            {!loadingList && conversations.length === 0 && (
              <div className="px-4 py-6 text-sm text-muted-foreground italic">
                You haven&apos;t talked to Origami yet.{" "}
                <Link href="/origami" className="text-primary underline">
                  Start a chat
                </Link>
                .
              </div>
            )}
            <ul>
              {conversations.map((c) => {
                const active = c.conversation_id === selectedId;
                return (
                  <li key={c.conversation_id}>
                    <button
                      onClick={() => setSelectedId(c.conversation_id)}
                      className={`w-full text-left px-4 py-3 border-b border-border transition-colors ${
                        active ? "bg-accent" : "hover:bg-accent/30"
                      }`}
                    >
                      <div className="font-medium text-sm truncate">
                        {c.title || "(no title)"}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1 flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {fmtAgo(c.last_at)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Hash className="h-3 w-3" />
                          {c.message_count} msg
                        </span>
                        {c.plan_count > 0 && (
                          <span className="flex items-center gap-1 text-primary">
                            <Rocket className="h-3 w-3" />
                            {c.plan_count} plan{c.plan_count === 1 ? "" : "s"}
                          </span>
                        )}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          </CardContent>
        </Card>

        {/* Right: selected conversation transcript */}
        <Card className="lg:col-span-3 p-0 overflow-hidden flex flex-col">
          <CardHeader className="border-b border-border flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base">
              {selectedId ? "Transcript" : "Pick a conversation"}
            </CardTitle>
            {selectedId && (
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => download("md")}
                  className="gap-1.5"
                >
                  <Download className="h-3.5 w-3.5" />
                  Markdown
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => download("json")}
                  className="gap-1.5"
                >
                  <Download className="h-3.5 w-3.5" />
                  JSON
                </Button>
              </div>
            )}
          </CardHeader>
          <CardContent className="p-4 flex-1 overflow-y-auto">
            {!selectedId && (
              <div className="text-sm text-muted-foreground italic">
                Select a conversation on the left to view it.
              </div>
            )}
            {loadingMessages && (
              <div className="text-sm text-muted-foreground">Loading messages…</div>
            )}
            {messages && messages.length === 0 && (
              <div className="text-sm text-muted-foreground italic">
                This conversation is empty.
              </div>
            )}
            <AnimatePresence>
              {messages?.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.15 }}
                  className="mb-4"
                >
                  <MessageBubble message={m} />
                </motion.div>
              ))}
            </AnimatePresence>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  if (message.role === "plan") {
    const plan = (message.extra_metadata?.plan_card || {}) as Record<string, unknown>;
    const changes = (plan.changes as Array<Record<string, unknown>>) || [];
    return (
      <div className="rounded-lg border border-primary/30 bg-muted/40 p-3">
        <div className="flex items-center gap-2 mb-2 text-xs uppercase tracking-wider text-primary font-semibold">
          <Rocket className="h-3.5 w-3.5" />
          Plan card
          <span className="ml-auto text-[10px] font-normal text-muted-foreground">
            {fmtFullTime(message.created_at)}
          </span>
        </div>
        <p className="text-sm text-foreground mb-2">{(plan.intent as string) || "(no intent)"}</p>
        <ul className="space-y-1 text-xs">
          {changes.map((c, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-primary mt-0.5">→</span>
              <span className="font-mono text-muted-foreground">{c.action as string}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const isUser = message.role === "user";
  const Icon = isUser ? User : Bot;
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className="shrink-0">
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center ${
            isUser ? "bg-primary text-primary-foreground" : "bg-muted text-foreground border border-border"
          }`}
        >
          <Icon className="h-3.5 w-3.5" />
        </div>
      </div>
      <div
        className={`max-w-[80%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground border border-border"
        }`}
      >
        <div>{message.content}</div>
        <div className="mt-1 flex items-center gap-2 text-[10px] opacity-60">
          <span>{fmtFullTime(message.created_at)}</span>
          {message.synthesized && (
            <Badge variant="outline" className="text-[9px] py-0 px-1 h-3.5">
              synthesized
            </Badge>
          )}
          {message.model_used && (
            <span className="font-mono">{message.model_used}</span>
          )}
        </div>
      </div>
    </div>
  );
}
