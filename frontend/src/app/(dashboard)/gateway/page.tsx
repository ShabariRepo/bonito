"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  Zap,
  Key,
  Copy,
  Check,
  Plus,
  Trash2,
  Activity,
  Clock,
  DollarSign,
  Code,
  Terminal,
  Settings,
  BarChart3,
  ArrowRight,
} from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { ErrorBanner } from "@/components/ui/error-banner";
import { API_URL } from "@/lib/utils";

/* ─── Types ─── */

interface GatewayKey {
  id: string;
  name: string;
  key_prefix: string;
  team_id: string | null;
  rate_limit: number;
  created_at: string;
  revoked_at: string | null;
}

interface LogEntry {
  id: string;
  model_requested: string;
  model_used: string | null;
  provider: string | null;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  latency_ms: number;
  status: string;
  error_message: string | null;
  created_at: string;
}

interface UsageStats {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: number;
  by_model: { model: string; requests: number; cost: number; tokens: number }[];
  by_day: { date: string; requests: number; cost: number }[];
}

/* ─── Copy Button ─── */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleCopy} className="p-1.5 rounded hover:bg-accent transition-colors">
      {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4 text-muted-foreground" />}
    </button>
  );
}

/* ─── Code Snippets ─── */

function CodeSnippets({ baseUrl }: { baseUrl: string }) {
  const [tab, setTab] = useState<"curl" | "python" | "node">("curl");

  const snippets = {
    curl: `curl ${baseUrl}/v1/chat/completions \\
  -H "Authorization: Bearer bn-YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'`,
    python: `from openai import OpenAI

client = OpenAI(
    base_url="${baseUrl}/v1",
    api_key="bn-YOUR_API_KEY",
)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)`,
    node: `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "${baseUrl}/v1",
  apiKey: "bn-YOUR_API_KEY",
});

const response = await client.chat.completions.create({
  model: "gpt-4o",
  messages: [{ role: "user", content: "Hello!" }],
});
console.log(response.choices[0].message.content);`,
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Code className="h-4 w-4" /> Quick Start
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2 mb-3">
          {(["curl", "python", "node"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                tab === t ? "bg-violet-600 text-white" : "bg-accent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "curl" ? "cURL" : t === "python" ? "Python" : "Node.js"}
            </button>
          ))}
        </div>
        <div className="relative">
          <pre className="bg-black/80 rounded-lg p-4 text-sm text-green-400 overflow-x-auto font-mono leading-relaxed">
            {snippets[tab]}
          </pre>
          <div className="absolute top-2 right-2">
            <CopyButton text={snippets[tab]} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ─── Main Page ─── */

export default function GatewayPage() {
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [keys, setKeys] = useState<GatewayKey[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyResult, setNewKeyResult] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const baseUrl = API_URL;
  const gatewayUrl = `${baseUrl}/v1/chat/completions`;

  const fetchData = useCallback(async () => {
    setError(null);
    try {
      const [usageRes, keysRes, logsRes] = await Promise.all([
        apiRequest("/api/gateway/usage"),
        apiRequest("/api/gateway/keys"),
        apiRequest("/api/gateway/logs?limit=20"),
      ]);
      if (usageRes.ok) setUsage(await usageRes.json());
      if (keysRes.ok) setKeys(await keysRes.json());
      if (logsRes.ok) setLogs(await logsRes.json());
      // If all requests failed, show error
      if (!usageRes.ok && !keysRes.ok && !logsRes.ok) {
        throw new Error("All gateway requests failed");
      }
    } catch (e) {
      console.error("Failed to fetch gateway data:", e);
      setError("Failed to load gateway data. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const createKey = async () => {
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const res = await apiRequest("/api/gateway/keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newKeyName }),
      });
      if (res.ok) {
        const data = await res.json();
        setNewKeyResult(data.key);
        setNewKeyName("");
        fetchData();
      }
    } finally {
      setCreating(false);
    }
  };

  const revokeKey = async (id: string) => {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    const res = await apiRequest(`/api/gateway/keys/${id}`, { method: "DELETE" });
    if (res.ok) fetchData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingDots />
      </div>
    );
  }

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      <PageHeader
        title="API Gateway"
        description="Route AI requests through a unified OpenAI-compatible endpoint with automatic failover, cost tracking, and rate limiting."
      />

      {error && <ErrorBanner message={error} onRetry={fetchData} />}

      {/* Quick Navigation */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <a href="/gateway/keys" className="group">
          <Card className="border-violet-500/20 hover:border-violet-500/50 transition-colors">
            <CardContent className="flex items-center gap-4 py-4">
              <Key className="h-8 w-8 text-violet-500" />
              <div className="flex-1">
                <h3 className="font-semibold">API Keys</h3>
                <p className="text-sm text-muted-foreground">Manage keys and permissions</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
            </CardContent>
          </Card>
        </a>
        
        <a href="/gateway/usage" className="group">
          <Card className="border-blue-500/20 hover:border-blue-500/50 transition-colors">
            <CardContent className="flex items-center gap-4 py-4">
              <BarChart3 className="h-8 w-8 text-blue-500" />
              <div className="flex-1">
                <h3 className="font-semibold">Usage Analytics</h3>
                <p className="text-sm text-muted-foreground">Detailed usage insights</p>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
            </CardContent>
          </Card>
        </a>
        
        <Card className="border-green-500/20">
          <CardContent className="flex items-center gap-4 py-4">
            <Settings className="h-8 w-8 text-green-500" />
            <div className="flex-1">
              <h3 className="font-semibold">Configuration</h3>
              <p className="text-sm text-muted-foreground">Routing & fallback rules</p>
            </div>
            <span className="text-xs bg-green-500/20 text-green-300 px-2 py-1 rounded">Soon</span>
          </CardContent>
        </Card>
      </div>

      {/* Endpoint URL */}
      <Card className="border-violet-500/30 bg-violet-500/5">
        <CardContent className="flex items-center gap-4 py-4">
          <Terminal className="h-5 w-5 text-violet-500 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-muted-foreground mb-1">Gateway Endpoint</p>
            <code className="text-sm font-mono text-foreground break-all">{gatewayUrl}</code>
          </div>
          <CopyButton text={gatewayUrl} />
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Requests", value: usage?.total_requests?.toLocaleString() ?? "0", icon: Activity, color: "text-blue-500" },
          { label: "Input Tokens", value: (usage?.total_input_tokens ?? 0).toLocaleString(), icon: Zap, color: "text-amber-500" },
          { label: "Output Tokens", value: (usage?.total_output_tokens ?? 0).toLocaleString(), icon: Zap, color: "text-green-500" },
          { label: "Total Cost", value: `$${(usage?.total_cost ?? 0).toFixed(4)}`, icon: DollarSign, color: "text-violet-500" },
        ].map((stat) => (
          <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                    <p className="text-2xl font-bold mt-1">{stat.value}</p>
                  </div>
                  <stat.icon className={`h-8 w-8 ${stat.color} opacity-50`} />
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Usage by Model */}
      {usage?.by_model && usage.by_model.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Usage by Model</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {usage.by_model.map((m) => (
                <div key={m.model} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-foreground">{m.model}</span>
                  <div className="flex items-center gap-4 text-muted-foreground">
                    <span>{m.requests.toLocaleString()} reqs</span>
                    <span>{m.tokens.toLocaleString()} tokens</span>
                    <span className="text-violet-500 font-medium">${m.cost.toFixed(4)}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* API Keys */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Key className="h-4 w-4" /> API Keys
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Create key */}
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Key name..."
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createKey()}
                className="flex-1 bg-accent/50 border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
              <button
                onClick={createKey}
                disabled={creating || !newKeyName.trim()}
                className="flex items-center gap-1.5 px-3 py-2 bg-violet-600 text-white rounded-md text-sm font-medium hover:bg-violet-700 disabled:opacity-50 transition-colors"
              >
                <Plus className="h-4 w-4" /> Create
              </button>
            </div>

            {/* New key banner */}
            <AnimatePresence>
              {newKeyResult && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="bg-green-500/10 border border-green-500/30 rounded-lg p-3"
                >
                  <p className="text-xs text-green-400 mb-1 font-medium">
                    ⚠️ Copy your API key now — it won't be shown again!
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="text-sm font-mono text-green-300 break-all flex-1">{newKeyResult}</code>
                    <CopyButton text={newKeyResult} />
                  </div>
                  <button
                    onClick={() => setNewKeyResult(null)}
                    className="text-xs text-muted-foreground mt-2 hover:text-foreground"
                  >
                    Dismiss
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Key list */}
            <div className="space-y-2">
              {keys.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No API keys yet. Create one to get started.</p>
              ) : (
                keys.map((k) => (
                  <div key={k.id} className="flex items-center justify-between bg-accent/30 rounded-lg px-3 py-2.5">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium truncate">{k.name}</span>
                        {k.revoked_at ? (
                          <Badge variant="destructive" className="text-xs">Revoked</Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">Active</Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-3 mt-0.5">
                        <code className="text-xs text-muted-foreground font-mono">{k.key_prefix}</code>
                        <span className="text-xs text-muted-foreground">{k.rate_limit} req/min</span>
                      </div>
                    </div>
                    {!k.revoked_at && (
                      <button onClick={() => revokeKey(k.id)} className="p-1.5 rounded hover:bg-destructive/20 text-muted-foreground hover:text-destructive transition-colors">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Code Snippets */}
        <CodeSnippets baseUrl={baseUrl} />
      </div>

      {/* Recent Logs */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Clock className="h-4 w-4" /> Recent Requests
          </CardTitle>
        </CardHeader>
        <CardContent>
          {logs.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">No requests yet. Use the gateway endpoint to start routing requests.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="pb-2 font-medium">Model</th>
                    <th className="pb-2 font-medium">Provider</th>
                    <th className="pb-2 font-medium">Tokens</th>
                    <th className="pb-2 font-medium">Cost</th>
                    <th className="pb-2 font-medium">Latency</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log) => (
                    <tr key={log.id} className="border-b border-border/50">
                      <td className="py-2 font-mono text-xs">{log.model_requested}</td>
                      <td className="py-2">
                        {log.provider && <Badge variant="outline" className="text-xs">{log.provider}</Badge>}
                      </td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {log.input_tokens + log.output_tokens}
                      </td>
                      <td className="py-2 text-xs text-violet-500">${log.cost.toFixed(6)}</td>
                      <td className="py-2 text-xs text-muted-foreground">{log.latency_ms}ms</td>
                      <td className="py-2">
                        <Badge
                          variant={log.status === "success" ? "secondary" : "destructive"}
                          className="text-xs"
                        >
                          {log.status}
                        </Badge>
                      </td>
                      <td className="py-2 text-xs text-muted-foreground">
                        {new Date(log.created_at).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
