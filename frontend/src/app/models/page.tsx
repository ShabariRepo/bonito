"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { PageHeader } from "@/components/ui/page-header";
import { Box, Sparkles, MessageSquare, Image, Code, Search } from "lucide-react";
import { API_URL } from "@/lib/utils";

interface Model {
  model_id: string;
  model_name: string;
  provider: string;
  provider_type?: string;
  capabilities?: string[];
  status?: string;
  input_pricing?: string;
  output_pricing?: string;
  [key: string]: any;
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

export default function ModelsPage() {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [providerFilter, setProviderFilter] = useState<string>("all");

  useEffect(() => {
    async function fetchModels() {
      try {
        const res = await fetch(`${API_URL}/api/models/`);
        if (res.ok) {
          const data = await res.json();
          setModels(data);
        }
      } catch (e) {
        console.error("Failed to fetch models", e);
      } finally {
        setLoading(false);
      }
    }
    fetchModels();
  }, []);

  const providers = Array.from(new Set(models.map(m => m.provider || m.provider_type || "unknown")));

  const filtered = models.filter(m => {
    const name = (m.model_name || m.model_id || "").toLowerCase();
    const prov = (m.provider || m.provider_type || "").toLowerCase();
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
        description={`${models.length} models available across your connected providers`}
        actions={
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search models..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="rounded-md border bg-background pl-9 pr-3 py-1.5 text-sm w-64 focus:outline-none focus:ring-1 focus:ring-violet-500"
              />
            </div>
            <div className="flex rounded-lg border border-border overflow-hidden">
              <button
                onClick={() => setProviderFilter("all")}
                className={`px-3 py-1.5 text-xs font-medium transition-colors ${providerFilter === "all" ? "bg-violet-600 text-white" : "text-muted-foreground hover:text-foreground"}`}
              >
                All
              </button>
              {providers.map(p => (
                <button
                  key={p}
                  onClick={() => setProviderFilter(p)}
                  className={`px-3 py-1.5 text-xs font-medium capitalize transition-colors ${providerFilter.toLowerCase() === p.toLowerCase() ? "bg-violet-600 text-white" : "text-muted-foreground hover:text-foreground"}`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        }
      />

      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Box className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-xl font-semibold">No models found</h3>
          <p className="text-muted-foreground mt-2">
            {search ? "Try a different search term" : "Connect a provider to see available models"}
          </p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filtered.map((model, i) => {
            const capabilities = model.capabilities || inferCapabilities(model.model_id);
            return (
              <motion.div
                key={model.model_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.5) }}
              >
                <Card className="hover:border-violet-500/50 transition-colors cursor-pointer">
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
                          <Box className="h-5 w-5 text-violet-400" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <h3 className="font-semibold truncate">{model.model_name || model.model_id}</h3>
                          <p className="text-sm text-muted-foreground capitalize">{model.provider || model.provider_type}</p>
                        </div>
                      </div>
                      <Badge variant="success">{model.status || "available"}</Badge>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-1.5">
                      {capabilities.map((cap: string) => (
                        <Badge key={cap} variant="secondary" className="gap-1">
                          {capabilityIcon(cap)}
                          {cap}
                        </Badge>
                      ))}
                    </div>

                    <div className="mt-4 border-t border-border pt-4">
                      <code className="text-xs text-muted-foreground break-all">{model.model_id}</code>
                    </div>
                  </CardContent>
                </Card>
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
