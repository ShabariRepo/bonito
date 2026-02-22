"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { PageHeader } from "@/components/ui/page-header";
import {
  Rocket, Globe, Cpu, Clock, Plus, Trash2, RefreshCw, DollarSign,
  ArrowUpRight, Scale, AlertCircle, CheckCircle, X, ChevronDown,
  Search, Zap
} from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { useAPI } from "@/lib/swr";

interface Model {
  id: string;
  model_id: string;
  display_name: string;
  provider_type?: string;
  capabilities?: { types?: string[] };
  pricing_info?: Record<string, any>;
}

interface Deployment {
  id: string;
  org_id: string;
  model_id: string;
  provider_id: string;
  config: {
    name?: string;
    cloud_resource_id?: string;
    endpoint_url?: string;
    provider_type?: string;
    model_display_name?: string;
    cloud_model_id?: string;
    cost_estimate?: {
      hourly: number;
      daily: number;
      monthly: number;
      unit: string;
      notes: string;
    };
    deploy_message?: string;
    tpm?: number;
    tier?: string;
    model_units?: number;
    commitment_term?: string;
    [key: string]: any;
  };
  status: string;
  created_at: string;
}

interface CostEstimate {
  hourly: number;
  daily: number;
  monthly: number;
  unit: string;
  notes: string;
  model_name: string;
  provider: string;
}

const statusConfig: Record<string, { variant: "success" | "warning" | "destructive" | "secondary"; label: string }> = {
  active: { variant: "success", label: "Active" },
  deploying: { variant: "warning", label: "Deploying" },
  pending: { variant: "warning", label: "Pending" },
  stopped: { variant: "secondary", label: "Stopped" },
  error: { variant: "destructive", label: "Error" },
  deleted: { variant: "destructive", label: "Deleted" },
};

export default function DeploymentsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [modelSearch, setModelSearch] = useState("");
  const [modelDropdownOpen, setModelDropdownOpen] = useState(false);
  const [deployName, setDeployName] = useState("");
  const [costEstimate, setCostEstimate] = useState<CostEstimate | null>(null);
  const [estimating, setEstimating] = useState(false);

  // AWS config
  const [modelUnits, setModelUnits] = useState(1);
  const [commitmentTerm, setCommitmentTerm] = useState("1_week");

  // Azure config
  const [tpm, setTpm] = useState(10);
  const [tier, setTier] = useState("Standard");

  const { data: deploymentsData, isLoading: depLoading, mutate: mutateDeployments } = useAPI<Deployment[]>("/api/deployments/");
  const { data: modelsData, isLoading: modLoading } = useAPI<Model[]>("/api/models/");
  const deployments = deploymentsData || [];
  const models = modelsData || [];
  const loading = depLoading || modLoading;

  const fetchData = useCallback(() => { mutateDeployments(); }, [mutateDeployments]);

  // Get provider type for selected model
  const selectedProvider = selectedModel?.provider_type || "";

  // Build config for the selected provider
  const buildConfig = () => {
    const config: Record<string, any> = {};
    if (deployName) config.name = deployName;
    
    if (selectedProvider === "aws") {
      config.model_units = modelUnits;
      config.commitment_term = commitmentTerm;
    } else if (selectedProvider === "azure") {
      config.tpm = tpm;
      config.tier = tier;
    }
    return config;
  };

  // Estimate cost
  const fetchEstimate = async () => {
    if (!selectedModel) return;
    setEstimating(true);
    setCostEstimate(null);
    try {
      const config = buildConfig();
      const res = await apiRequest("/api/deployments/estimate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_id: selectedModel.id, config }),
      });
      if (res.ok) {
        setCostEstimate(await res.json());
      }
    } catch (e) {
      console.error("Cost estimation failed", e);
    } finally {
      setEstimating(false);
    }
  };

  // Refresh estimate when config changes
  useEffect(() => {
    if (selectedModel) {
      const timer = setTimeout(fetchEstimate, 300);
      return () => clearTimeout(timer);
    }
  }, [selectedModel, modelUnits, commitmentTerm, tpm, tier]);

  const handleCreate = async () => {
    if (!selectedModel) return;
    setCreating(true);
    setError(null);
    try {
      const res = await apiRequest("/api/deployments/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_id: selectedModel.id,
          config: buildConfig(),
        }),
      });
      if (res.ok) {
        setShowCreate(false);
        resetCreateForm();
        fetchData();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || `Deployment failed (${res.status})`);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setCreating(false);
    }
  };

  const resetCreateForm = () => {
    setSelectedModel(null);
    setModelSearch("");
    setDeployName("");
    setCostEstimate(null);
    setModelUnits(1);
    setCommitmentTerm("1_week");
    setTpm(10);
    setTier("Standard");
    setError(null);
  };

  const handleDelete = async (id: string) => {
    setDeleting(id);
    try {
      await apiRequest(`/api/deployments/${id}`, { method: "DELETE" });
      setDeleteConfirm(null);
      fetchData();
    } catch (e) {
      console.error("Delete failed", e);
    } finally {
      setDeleting(null);
    }
  };

  const handleRefreshStatus = async (id: string) => {
    setRefreshing(id);
    try {
      await apiRequest(`/api/deployments/${id}/status`, { method: "POST" });
      fetchData();
    } catch (e) {
      console.error("Status refresh failed", e);
    } finally {
      setRefreshing(null);
    }
  };

  // Filter models for dropdown — only chat-capable, enabled models
  const NON_CHAT_PATTERNS = [/embed/i, /babbage/i, /^ada$/i, /ada-00/i, /^dall-e/i, /^tts-/i, /^whisper/i, /rerank/i, /\bbert\b/i, /\bbart\b/i, /moderation/i];
  const deployableModels = models.filter(m => {
    const caps = m.capabilities?.types || [];
    const isNonChat = caps.length > 0 && caps.every(c => ["embeddings", "embedding", "rerank"].includes(c.toLowerCase()));
    const isKnownNonChat = NON_CHAT_PATTERNS.some(p => p.test(m.model_id));
    return !isNonChat && !isKnownNonChat;
  });

  const filteredModels = deployableModels.filter(m =>
    !modelSearch ||
    m.display_name.toLowerCase().includes(modelSearch.toLowerCase()) ||
    m.model_id.toLowerCase().includes(modelSearch.toLowerCase())
  );

  if (loading) {
    return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Deployments"
        description="Provision and manage model infrastructure across your cloud accounts"
        actions={
          <div className="flex gap-2">
            <button
              onClick={() => fetchData()}
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => { resetCreateForm(); setShowCreate(true); }}
              className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
            >
              <Rocket className="h-4 w-4" />
              New Deployment
            </motion.button>
          </div>
        }
      />

      {/* Create Deployment Modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={() => setShowCreate(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-lg rounded-xl border border-border bg-card shadow-2xl max-h-[90vh] overflow-y-auto"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-6 border-b border-border">
                <div>
                  <h2 className="text-lg font-semibold">Create Deployment</h2>
                  <p className="text-sm text-muted-foreground mt-0.5">Provision model infrastructure on your cloud</p>
                </div>
                <button onClick={() => setShowCreate(false)} className="p-1 rounded-md hover:bg-accent">
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>

              <div className="p-6 space-y-5">
                {/* Model Selector */}
                <div className="relative">
                  <label className="text-sm font-medium mb-1.5 block">Select Model</label>
                  <button
                    onClick={() => setModelDropdownOpen(!modelDropdownOpen)}
                    className="w-full p-2.5 border rounded-lg bg-background text-left flex items-center justify-between"
                  >
                    <span className={selectedModel ? "text-foreground" : "text-muted-foreground"}>
                      {selectedModel ? `${selectedModel.display_name} (${selectedModel.provider_type})` : "Choose a model..."}
                    </span>
                    <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${modelDropdownOpen ? "rotate-180" : ""}`} />
                  </button>
                  {modelDropdownOpen && (
                    <div className="absolute z-50 mt-1 w-full bg-card border border-border rounded-lg shadow-xl max-h-64 flex flex-col">
                      <div className="p-2 border-b border-border">
                        <input
                          type="text"
                          placeholder="Search models..."
                          value={modelSearch}
                          onChange={(e) => setModelSearch(e.target.value)}
                          className="w-full px-3 py-1.5 text-sm border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-violet-500"
                          autoFocus
                        />
                      </div>
                      <div className="overflow-y-auto">
                        {filteredModels.length === 0 ? (
                          <div className="p-4 text-sm text-muted-foreground text-center">No models found</div>
                        ) : (
                          filteredModels.map(m => (
                            <button
                              key={m.id}
                              onClick={() => {
                                setSelectedModel(m);
                                setModelDropdownOpen(false);
                                setModelSearch("");
                                setDeployName("");
                              }}
                              className={`w-full px-3 py-2 text-left hover:bg-accent transition-colors ${
                                selectedModel?.id === m.id ? "bg-violet-500/10 text-violet-400" : ""
                              }`}
                            >
                              <div className="text-sm font-medium">{m.display_name}</div>
                              <div className="text-xs text-muted-foreground">{m.model_id} · {m.provider_type?.toUpperCase()}</div>
                            </button>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Deployment Name */}
                {selectedModel && (
                  <div>
                    <label className="text-sm font-medium mb-1.5 block">Deployment Name</label>
                    <input
                      type="text"
                      value={deployName}
                      onChange={(e) => setDeployName(e.target.value)}
                      placeholder={`bonito-${selectedModel.model_id.split('.').pop()?.split('/').pop()?.slice(0, 20) || "model"}`}
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                    />
                  </div>
                )}

                {/* Provider-specific config */}
                {selectedProvider === "aws" && (
                  <div className="space-y-4 p-4 rounded-lg bg-accent/30 border border-border">
                    <h3 className="text-sm font-medium flex items-center gap-2">
                      <span className="text-lg">☁️</span> AWS Bedrock Deployment
                    </h3>
                    <div>
                      <label className="text-sm text-muted-foreground mb-1 block">Deployment Type</label>
                      <div className="grid grid-cols-2 gap-2 mb-3">
                        <button
                          onClick={() => { setModelUnits(0); setCommitmentTerm("1_week"); }}
                          className={`p-2.5 rounded-lg border text-left transition-colors ${
                            modelUnits === 0
                              ? "border-violet-500 bg-violet-500/10"
                              : "border-border hover:border-violet-500/30"
                          }`}
                        >
                          <div className="text-xs font-medium">On-Demand</div>
                          <div className="text-xs text-muted-foreground">Pay per request, no fixed cost</div>
                        </button>
                        <button
                          onClick={() => setModelUnits(1)}
                          className={`p-2.5 rounded-lg border text-left transition-colors ${
                            modelUnits > 0
                              ? "border-violet-500 bg-violet-500/10"
                              : "border-border hover:border-violet-500/30"
                          }`}
                        >
                          <div className="text-xs font-medium">Provisioned Throughput</div>
                          <div className="text-xs text-muted-foreground">Reserved capacity, predictable perf</div>
                        </button>
                      </div>
                    </div>
                    {modelUnits > 0 && (
                      <>
                        <div>
                          <label className="text-sm text-muted-foreground mb-1 block">Model Units</label>
                          <div className="flex items-center gap-3">
                            <input
                              type="range"
                              min={1}
                              max={10}
                              value={modelUnits}
                              onChange={(e) => setModelUnits(parseInt(e.target.value))}
                              className="flex-1 accent-violet-600"
                            />
                            <span className="text-sm font-mono w-8 text-right">{modelUnits}</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">Each unit provides dedicated throughput</p>
                        </div>
                        <div>
                          <label className="text-sm text-muted-foreground mb-1 block">Commitment Term</label>
                          <div className="grid grid-cols-4 gap-2">
                            {[
                              { value: "1_week", label: "1 week", sub: "Minimum term" },
                              { value: "1_month", label: "1 month", sub: "~20% savings" },
                              { value: "3_month", label: "3 months", sub: "~40% savings" },
                              { value: "6_month", label: "6 months", sub: "~50% savings" },
                            ].map(opt => (
                              <button
                                key={opt.value}
                                onClick={() => setCommitmentTerm(opt.value)}
                                className={`p-2.5 rounded-lg border text-left transition-colors ${
                                  commitmentTerm === opt.value
                                    ? "border-violet-500 bg-violet-500/10"
                                    : "border-border hover:border-violet-500/30"
                                }`}
                              >
                                <div className="text-xs font-medium">{opt.label}</div>
                                <div className="text-xs text-muted-foreground">{opt.sub}</div>
                              </button>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {selectedProvider === "azure" && (
                  <div className="space-y-4 p-4 rounded-lg bg-accent/30 border border-border">
                    <h3 className="text-sm font-medium flex items-center gap-2">
                      <span className="text-lg">🔷</span> Azure OpenAI Deployment
                    </h3>
                    <div>
                      <label className="text-sm text-muted-foreground mb-1 block">Tokens Per Minute (thousands)</label>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={1}
                          max={120}
                          value={tpm}
                          onChange={(e) => setTpm(parseInt(e.target.value))}
                          className="flex-1 accent-violet-600"
                        />
                        <span className="text-sm font-mono w-12 text-right">{tpm}K</span>
                      </div>
                    </div>
                    <div>
                      <label className="text-sm text-muted-foreground mb-1 block">Tier</label>
                      <div className="grid grid-cols-3 gap-2">
                        {[
                          { value: "Standard", label: "Standard", sub: "Regional, pay-per-use" },
                          { value: "GlobalStandard", label: "Global Standard", sub: "Multi-region, higher limits" },
                          { value: "Provisioned", label: "Provisioned", sub: "Dedicated compute, reserved" },
                        ].map(opt => (
                          <button
                            key={opt.value}
                            onClick={() => setTier(opt.value)}
                            className={`p-2.5 rounded-lg border text-left transition-colors ${
                              tier === opt.value
                                ? "border-violet-500 bg-violet-500/10"
                                : "border-border hover:border-violet-500/30"
                            }`}
                          >
                            <div className="text-xs font-medium">{opt.label}</div>
                            <div className="text-xs text-muted-foreground">{opt.sub}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {selectedProvider === "gcp" && (
                  <div className="p-4 rounded-lg bg-accent/30 border border-border">
                    <h3 className="text-sm font-medium flex items-center gap-2 mb-2">
                      <span className="text-lg">🔺</span> Google Vertex AI
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      Vertex AI models are serverless — no dedicated deployment needed. You&apos;re billed per request with no fixed infrastructure cost.
                    </p>
                  </div>
                )}

                {/* Cost Estimate */}
                {selectedModel && costEstimate && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 rounded-lg border border-emerald-500/30 bg-emerald-500/5"
                  >
                    <div className="flex items-center gap-2 mb-3">
                      <DollarSign className="h-4 w-4 text-emerald-400" />
                      <h4 className="text-sm font-medium">Cost Estimate</h4>
                      {estimating && <LoadingDots size="sm" />}
                    </div>
                    {costEstimate.monthly > 0 ? (
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <div className="text-xs text-muted-foreground">Hourly</div>
                          <div className="text-lg font-semibold">${costEstimate.hourly.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">Daily</div>
                          <div className="text-lg font-semibold">${costEstimate.daily.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-muted-foreground">Monthly</div>
                          <div className="text-lg font-semibold text-emerald-400">${costEstimate.monthly.toFixed(2)}</div>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-emerald-400">No fixed cost — pay per request</p>
                    )}
                    <p className="text-xs text-muted-foreground mt-2">{costEstimate.notes}</p>
                  </motion.div>
                )}

                {/* Error */}
                {error && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400 flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="flex gap-3 p-6 border-t border-border">
                <button
                  onClick={() => setShowCreate(false)}
                  className="flex-1 rounded-lg border border-border px-4 py-2.5 text-sm font-medium hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleCreate}
                  disabled={!selectedModel || creating}
                  className="flex-1 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
                >
                  {creating ? (
                    <>Deploying...</>
                  ) : (
                    <><Rocket className="h-4 w-4" /> Deploy</>
                  )}
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Deployments List */}
      {deployments.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 text-center"
        >
          <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            className="text-5xl mb-4"
          >
            🚀
          </motion.div>
          <h3 className="text-xl font-semibold">No deployments yet</h3>
          <p className="text-muted-foreground mt-2 max-w-md">
            Deploy AI models on your cloud infrastructure. Provision AWS Bedrock throughput,
            Azure OpenAI endpoints, or verify Vertex AI access — all from here.
          </p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => { resetCreateForm(); setShowCreate(true); }}
            className="mt-6 flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700"
          >
            <Plus className="h-4 w-4" />
            Create First Deployment
          </motion.button>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {deployments.map((d, i) => {
            const config = d.config || {};
            const estimate = config.cost_estimate;
            const providerType = config.provider_type || "unknown";
            const emoji = providerType === "aws" ? "☁️" : providerType === "azure" ? "🔷" : providerType === "gcp" ? "🔺" : "☁️";
            const st = statusConfig[d.status] || statusConfig.pending;

            return (
              <motion.div
                key={d.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <Card className="hover:border-violet-500/30 transition-colors">
                  <CardContent className="py-5">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                      {/* Left: Info */}
                      <div className="flex items-center gap-4">
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-accent text-2xl">
                          {emoji}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-semibold">{config.name || config.model_display_name || "Deployment"}</p>
                            <Badge variant={st.variant}>{st.label}</Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {config.model_display_name || config.cloud_model_id || ""} · {providerType.toUpperCase()}
                          </p>
                          {config.deploy_message && d.status !== "active" && (
                            <p className="text-xs text-muted-foreground mt-1">{config.deploy_message}</p>
                          )}
                        </div>
                      </div>

                      {/* Middle: Config details */}
                      <div className="flex items-center gap-6 text-sm text-muted-foreground">
                        {providerType === "aws" && config.config_applied?.model_units && (
                          <div className="flex items-center gap-1.5">
                            <Cpu className="h-3.5 w-3.5" />
                            {config.config_applied.model_units} unit{config.config_applied.model_units > 1 ? "s" : ""}
                          </div>
                        )}
                        {providerType === "azure" && config.tpm && (
                          <div className="flex items-center gap-1.5">
                            <Zap className="h-3.5 w-3.5" />
                            {config.tpm}K TPM
                          </div>
                        )}
                        {estimate && estimate.monthly > 0 && (
                          <div className="flex items-center gap-1.5">
                            <DollarSign className="h-3.5 w-3.5" />
                            ~${estimate.monthly.toFixed(0)}/mo
                          </div>
                        )}
                        {estimate && estimate.monthly === 0 && (
                          <div className="flex items-center gap-1.5">
                            <DollarSign className="h-3.5 w-3.5" />
                            Pay-per-use
                          </div>
                        )}
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5" />
                          {new Date(d.created_at).toLocaleDateString()}
                        </div>
                      </div>

                      {/* Right: Actions */}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleRefreshStatus(d.id)}
                          disabled={refreshing === d.id}
                          className="rounded-md px-2 py-1.5 text-xs border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-50"
                          title="Refresh status from cloud"
                        >
                          <RefreshCw className={`h-3.5 w-3.5 ${refreshing === d.id ? "animate-spin" : ""}`} />
                        </button>
                        {config.endpoint_url && (
                          <a
                            href={config.endpoint_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded-md px-2 py-1.5 text-xs border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                            title="Open endpoint"
                          >
                            <ArrowUpRight className="h-3.5 w-3.5" />
                          </a>
                        )}
                        {deleteConfirm === d.id ? (
                          <div className="flex gap-1">
                            <button
                              onClick={() => handleDelete(d.id)}
                              disabled={deleting === d.id}
                              className="rounded-md px-2.5 py-1.5 text-xs bg-red-500/15 text-red-400 hover:bg-red-500/25 disabled:opacity-50"
                            >
                              {deleting === d.id ? "..." : "Confirm Delete"}
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(d.id)}
                            className="rounded-md p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                            title="Delete deployment"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
