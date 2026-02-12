"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { PageHeader } from "@/components/ui/page-header";
import { Box, Sparkles, MessageSquare, Image, Code, Search, RefreshCw, AlertTriangle } from "lucide-react";
import { apiRequest } from "@/lib/auth";

interface Model {
  id: string;
  model_id: string;
  display_name: string;
  provider_id: string;
  capabilities: Record<string, any>;
  pricing_info: Record<string, any>;
  created_at: string;
  // fields from provider-level model list
  model_name?: string;
  provider?: string;
  provider_type?: string;
  status?: string;
  [key: string]: any;
}

interface ConnectedProvider {
  id: string;
  provider_type: string;
  status: string;
}

const capabilityIcon = (cap: string) => {
  switch (cap) {
    case "chat": return <MessageSquare className="h-3 w-3" />;
    case "code": return <Code className="h-3 w-3" />;
    case "vision": return <Image className="h-3 w-3" />;
    default: return <Sparkles className="h-3 w-3" />;
  }
};

function inferCapabilities(modelId: string): string[] {
  const id = modelId.toLowerCase();
  const caps: string[] = [];
  if (id.includes("embed")) return ["embedding"];
  if (id.includes("image") || id.includes("stable-diffusion") || id.includes("titan-image") || id.includes("nova-canvas")) return ["image-generation"];
  caps.push("chat");
  if (id.includes("claude") || id.includes("llama") || id.includes("mistral") || id.includes("codellama") || id.includes("deepseek")) caps.push("code");
  if (id.includes("claude-3") || id.includes("nova") || id.includes("claude-4")) caps.push("vision");
  return caps;
}

const PROVIDER_LABELS: Record<string, string> = {
  aws: "AWS",
  azure: "Azure",
  gcp: "GCP",
};

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [connectedProviders, setConnectedProviders] = useState<ConnectedProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<Record<string, number> | null>(null);
  const [search, setSearch] = useState("");
  const [providerFilter, setProviderFilter] = useState<string>("all");

  const fetchModels = useCallback(async (autoSync = false) => {
    try {
      // Fetch connected providers and models in parallel
      const [provRes, modRes] = await Promise.all([
        apiRequest("/api/providers/"),
        apiRequest("/api/models/"),
      ]);

      if (provRes.ok) {
        const provData = await provRes.json();
        const active = (Array.isArray(provData) ? provData : []).filter(
          (p: ConnectedProvider) => p.status === "active"
        );
        setConnectedProviders(active);
      }

      if (modRes.ok) {
        let data = await modRes.json();
        if (data.length === 0 && autoSync) {
          // Auto-sync from providers on first load
          const syncRes = await apiRequest("/api/models/sync", { method: "POST" });
          if (syncRes.ok) {
            const syncData = await syncRes.json();
            setSyncResult(syncData.details || null);
          }
          const retry = await apiRequest("/api/models/");
          if (retry.ok) data = await retry.json();
        }
        setModels(data);
      }
    } catch (e) {
      console.error("Failed to fetch models", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels(true);
  }, [fetchModels]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await apiRequest("/api/models/sync", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setSyncResult(data.details || null);
      }
      // Re-fetch models after sync
      const modRes = await apiRequest("/api/models/");
      if (modRes.ok) {
        setModels(await modRes.json());
      }
    } catch (e) {
      console.error("Sync failed", e);
    } finally {
      setSyncing(false);
    }
  };

  // Derive provider name from model_id heuristics or provider field
  const getProviderLabel = (m: Model) => {
    if (m.provider) return m.provider;
    if (m.provider_type) return m.provider_type;
    const id = m.model_id?.toLowerCase() || "";
    if (id.includes("anthropic") || id.includes("claude") || id.includes("amazon") || id.includes("meta") || id.includes("mistral") || id.includes("cohere") || id.includes("ai21") || id.includes("stability")) return "aws";
    if (id.includes("gpt") || id.includes("dall-e") || id.includes("whisper") || id.includes("phi")) return "azure";
    if (id.includes("gemini") || id.includes("palm") || id.includes("imagen") || id.includes("code-bison") || id.includes("text-bison")) return "gcp";
    return "unknown";
  };

  // Use connected providers as the source of truth for tabs (not just models in DB)
  const providerTabs = Array.from(
    new Set([
      ...connectedProviders.map(p => p.provider_type),
      ...models.map(m => getProviderLabel(m)),
    ])
  ).sort();

  // Track which connected providers have 0 synced models
  const modelCountByProvider: Record<string, number> = {};
  for (const m of models) {
    const p = getProviderLabel(m);
    modelCountByProvider[p] = (modelCountByProvider[p] || 0) + 1;
  }

  const filtered = models.filter(m => {
    const name = (m.display_name || m.model_name || m.model_id || "").toLowerCase();
    const prov = getProviderLabel(m).toLowerCase();
    const matchesSearch = !search || name.includes(search.toLowerCase()) || m.model_id.toLowerCase().includes(search.toLowerCase());
    const matchesProvider = providerFilter === "all" || prov.includes(providerFilter.toLowerCase());
    return matchesSearch && matchesProvider;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingDots size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Model Catalog"
        description={`${models.length} models available across ${connectedProviders.length} connected provider${connectedProviders.length !== 1 ? "s" : ""}`}
        actions={
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search models..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="rounded-md border bg-background pl-9 pr-3 py-2 text-sm w-full sm:w-64 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <div className="flex rounded-lg border border-border overflow-hidden">
                <button
                  onClick={() => setProviderFilter("all")}
                  className={`px-3 py-2 text-xs font-medium transition-colors min-h-[44px] ${providerFilter === "all" ? "bg-violet-600 text-white" : "text-muted-foreground hover:text-foreground"}`}
                >
                  All
                </button>
                {providerTabs.map(p => {
                  const count = modelCountByProvider[p] || 0;
                  const hasWarning = connectedProviders.some(cp => cp.provider_type === p) && count === 0;
                  return (
                    <button
                      key={p}
                      onClick={() => setProviderFilter(p)}
                      className={`px-3 py-2 text-xs font-medium transition-colors min-h-[44px] flex items-center gap-1.5 ${providerFilter.toLowerCase() === p.toLowerCase() ? "bg-violet-600 text-white" : "text-muted-foreground hover:text-foreground"}`}
                    >
                      {PROVIDER_LABELS[p] || p.toUpperCase()}
                      {hasWarning && <AlertTriangle className="h-3 w-3 text-yellow-500" />}
                    </button>
                  );
                })}
              </div>
              <button
                onClick={handleSync}
                disabled={syncing}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-violet-500/50 transition-colors min-h-[44px] disabled:opacity-50"
                title="Sync models from all providers"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${syncing ? "animate-spin" : ""}`} />
                {syncing ? "Syncing..." : "Sync"}
              </button>
            </div>
          </div>
        }
      />

      {/* Sync result banner */}
      {syncResult && (
        <div className="rounded-lg border border-border bg-card p-3 flex items-center justify-between">
          <div className="flex items-center gap-3 text-sm">
            <RefreshCw className="h-4 w-4 text-violet-400" />
            <span>
              Synced:{" "}
              {Object.entries(syncResult).map(([prov, count], i) => (
                <span key={prov}>
                  {i > 0 && " · "}
                  <span className="font-medium">{PROVIDER_LABELS[prov] || prov.toUpperCase()}</span>{" "}
                  <span className={count === 0 ? "text-yellow-500" : "text-green-500"}>{count} models</span>
                </span>
              ))}
            </span>
          </div>
          <button onClick={() => setSyncResult(null)} className="text-muted-foreground hover:text-foreground text-xs">✕</button>
        </div>
      )}

      {/* Warning for providers with 0 models */}
      {providerFilter !== "all" && (modelCountByProvider[providerFilter] || 0) === 0 && connectedProviders.some(p => p.provider_type === providerFilter) && (
        <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-yellow-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium">No models synced for {PROVIDER_LABELS[providerFilter] || providerFilter.toUpperCase()}</p>
            <p className="text-sm text-muted-foreground mt-1">
              This provider is connected but has no models in the catalog. This usually means the sync failed — credentials may have expired, or the provider API returned an error.
              Try clicking <strong>Sync</strong> above, or check your provider credentials in{" "}
              <Link href="/providers" className="text-violet-400 hover:underline">Settings → Providers</Link>.
            </p>
          </div>
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Box className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-xl font-semibold">No models found</h3>
          <p className="text-muted-foreground mt-2">
            {search ? "Try a different search term" : "Connect a provider to see available models"}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((model, i) => {
            const capsRaw = model.capabilities;
            const capabilities: string[] = Array.isArray(capsRaw)
              ? capsRaw
              : capsRaw?.types && Array.isArray(capsRaw.types)
              ? capsRaw.types
              : inferCapabilities(model.model_id);
            const status = model.pricing_info?.status || model.status || "available";
            return (
              <motion.div
                key={model.id || model.model_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.5) }}
              >
                <Link href={`/models/${model.id}`}>
                  <Card className="hover:border-violet-500/50 transition-colors cursor-pointer">
                    <CardContent className="pt-6">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
                            <Box className="h-5 w-5 text-violet-400" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <h3 className="font-semibold truncate hover:text-violet-600 transition-colors">{model.display_name || model.model_name || model.model_id}</h3>
                            <p className="text-sm text-muted-foreground capitalize">{getProviderLabel(model)}</p>
                          </div>
                        </div>
                        <Badge variant="success">{status}</Badge>
                      </div>

                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {capabilities.map((cap: string) => (
                        <Badge key={cap} variant="secondary" className="gap-1">
                          {capabilityIcon(cap)}
                          {cap}
                        </Badge>
                      ))}
                    </div>

                    {model.pricing_info?.pricing_tier && (
                      <div className="mt-2">
                        <Badge variant="outline" className="text-xs capitalize">{model.pricing_info.pricing_tier}</Badge>
                      </div>
                    )}

                    <div className="mt-4 border-t border-border pt-4">
                      <code className="text-xs text-muted-foreground break-all">{model.model_id}</code>
                    </div>
                  </CardContent>
                </Card>
                </Link>
              </motion.div>
            );
          })}
        </div>
      )}

      <p className="text-center text-sm text-muted-foreground">
        Showing {filtered.length} of {models.length} models
      </p>
    </div>
  );
}
