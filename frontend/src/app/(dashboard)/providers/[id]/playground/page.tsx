"use client";

import { useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Send, Loader2, Zap, Clock, DollarSign, Hash, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

interface ModelInfo {
  id: string;
  name: string;
  provider_model_id: string;
  capabilities: string[];
  context_window: number;
  pricing_tier: string;
}

interface InvocationResponse {
  response_text: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  estimated_cost: number;
  model_id: string;
}

export default function PlaygroundPage() {
  const params = useParams();
  const providerId = params.id as string;

  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [prompt, setPrompt] = useState("");
  const [maxTokens, setMaxTokens] = useState(1024);
  const [temperature, setTemperature] = useState(0.7);
  const [loading, setLoading] = useState(false);
  const [loadingModels, setLoadingModels] = useState(true);
  const [response, setResponse] = useState<InvocationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [displayedText, setDisplayedText] = useState("");
  const textRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiRequest(`/api/providers/${providerId}/models`)
      .then((r) => r.json())
      .then((data) => {
        // Filter to text-capable models only
        const textModels = data.filter((m: ModelInfo) =>
          m.capabilities.some((c: string) => ["text", "code", "streaming"].includes(c))
        );
        setModels(textModels);
        if (textModels.length > 0) setSelectedModel(textModels[0].provider_model_id);
      })
      .catch(() => {})
      .finally(() => setLoadingModels(false));
  }, [providerId]);

  // Typing animation
  useEffect(() => {
    if (!response) { setDisplayedText(""); return; }
    const text = response.response_text;
    let i = 0;
    setDisplayedText("");
    const interval = setInterval(() => {
      i += 3; // 3 chars at a time for speed
      setDisplayedText(text.slice(0, i));
      if (i >= text.length) clearInterval(interval);
      textRef.current?.scrollTo({ top: textRef.current.scrollHeight });
    }, 10);
    return () => clearInterval(interval);
  }, [response]);

  const handleInvoke = async () => {
    if (!selectedModel || !prompt.trim()) return;
    setLoading(true);
    setResponse(null);
    setError(null);

    try {
      const res = await apiRequest(`/api/providers/${providerId}/invoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_id: selectedModel,
          prompt: prompt.trim(),
          max_tokens: maxTokens,
          temperature,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Invocation failed");
      }
      setResponse(await res.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handleInvoke();
  };

  const selectedModelInfo = models.find((m) => m.provider_model_id === selectedModel);

  if (loadingModels) {
    return <div className="flex items-center justify-center py-20"><LoadingDots size="lg" /></div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Model Playground"
        description="Test models with prompts and see real responses"
        breadcrumbs={[
          { label: "Providers", href: "/providers" },
          { label: "Provider", href: `/providers/${providerId}` },
          { label: "Playground" },
        ]}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Controls */}
        <div className="space-y-4">
          {/* Model selector */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg border border-border p-4 space-y-3"
          >
            <label className="block text-sm font-medium">Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
            >
              {models.map((m) => (
                <option key={m.provider_model_id} value={m.provider_model_id}>
                  {m.name}
                </option>
              ))}
            </select>

            {selectedModelInfo && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {selectedModelInfo.capabilities.slice(0, 4).map((cap) => (
                  <Badge key={cap} variant="secondary" className="text-[10px]">{cap}</Badge>
                ))}
                {selectedModelInfo.context_window > 0 && (
                  <Badge variant="secondary" className="text-[10px]">
                    {selectedModelInfo.context_window >= 1_000_000
                      ? `${(selectedModelInfo.context_window / 1_000_000).toFixed(1)}M`
                      : `${(selectedModelInfo.context_window / 1000).toFixed(0)}K`} ctx
                  </Badge>
                )}
              </div>
            )}
          </motion.div>

          {/* Parameters */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="rounded-lg border border-border p-4 space-y-4"
          >
            <h3 className="text-sm font-medium">Parameters</h3>
            <div>
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Max Tokens</span>
                <span>{maxTokens}</span>
              </div>
              <input
                type="range"
                min={1}
                max={4096}
                value={maxTokens}
                onChange={(e) => setMaxTokens(Number(e.target.value))}
                className="w-full accent-violet-500"
              />
            </div>
            <div>
              <div className="flex justify-between text-xs text-muted-foreground mb-1">
                <span>Temperature</span>
                <span>{temperature.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                value={temperature * 100}
                onChange={(e) => setTemperature(Number(e.target.value) / 100)}
                className="w-full accent-violet-500"
              />
            </div>
          </motion.div>
        </div>

        {/* Right: Prompt & Response */}
        <div className="lg:col-span-2 space-y-4">
          {/* Prompt */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="rounded-lg border border-border p-4"
          >
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter your prompt here... (⌘+Enter to send)"
              rows={6}
              className="w-full resize-none bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground"
            />
            <div className="flex justify-end pt-2 border-t border-border mt-2">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handleInvoke}
                disabled={loading || !prompt.trim() || !selectedModel}
                className={cn(
                  "inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-all",
                  loading || !prompt.trim()
                    ? "bg-accent text-muted-foreground cursor-not-allowed"
                    : "bg-violet-600 text-white hover:bg-violet-700"
                )}
              >
                {loading ? (
                  <><Loader2 className="h-4 w-4 animate-spin" /> Generating...</>
                ) : (
                  <><Sparkles className="h-4 w-4" /> Run</>
                )}
              </motion.button>
            </div>
          </motion.div>

          {/* Response */}
          <AnimatePresence mode="wait">
            {loading && !response && (
              <motion.div
                key="loading"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-lg border border-border p-8 flex flex-col items-center gap-3"
              >
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                >
                  <Sparkles className="h-8 w-8 text-violet-500" />
                </motion.div>
                <p className="text-sm text-muted-foreground">Generating response...</p>
              </motion.div>
            )}

            {error && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-lg border border-red-500/30 bg-red-500/5 p-4"
              >
                <p className="text-sm text-red-400">{error}</p>
              </motion.div>
            )}

            {response && (
              <motion.div
                key="response"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-3"
              >
                {/* Stats bar */}
                <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {response.latency_ms.toFixed(0)}ms
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Hash className="h-3 w-3" /> {response.input_tokens} in / {response.output_tokens} out
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <DollarSign className="h-3 w-3" /> ${response.estimated_cost.toFixed(6)}
                  </span>
                </div>

                {/* Response text */}
                <div
                  ref={textRef}
                  className="rounded-lg border border-border p-4 max-h-[500px] overflow-y-auto"
                >
                  <pre className="whitespace-pre-wrap text-sm font-mono leading-relaxed">
                    {displayedText}
                    {displayedText.length < (response?.response_text?.length || 0) && (
                      <motion.span
                        animate={{ opacity: [1, 0] }}
                        transition={{ duration: 0.5, repeat: Infinity }}
                        className="text-violet-500"
                      >
                        ▊
                      </motion.span>
                    )}
                  </pre>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
