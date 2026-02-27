"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Cloud,
  Plus,
  RefreshCw,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Trash2,
  Pencil,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Eye,
  EyeOff,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";
import { AnimatedCard } from "@/components/ui/animated-card";
import { StatusBadge } from "@/components/ui/status-badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import Link from "next/link";

interface Provider {
  id: string;
  provider_type: string;
  status: string;
  name: string;
  region: string;
  model_count: number;
  created_at: string;
}

interface ProviderSummary {
  id: string;
  provider_type: string;
  status: string;
  name: string;
  region: string;
  model_count: number;
  masked_credentials: Record<string, string>;
  last_validated: string | null;
  created_at: string;
}

const providerStyles: Record<
  string,
  { color: string; glowColor: string; icon: string; bgColor: string }
> = {
  aws: { color: "text-amber-500", glowColor: "amber", icon: "☁️", bgColor: "bg-amber-500/10" },
  azure: { color: "text-blue-500", glowColor: "blue", icon: "🔷", bgColor: "bg-blue-500/10" },
  gcp: { color: "text-red-500", glowColor: "red", icon: "🔺", bgColor: "bg-red-500/10" },
  openai: { color: "text-green-500", glowColor: "green", icon: "🤖", bgColor: "bg-green-500/10" },
  anthropic: { color: "text-purple-500", glowColor: "purple", icon: "🧠", bgColor: "bg-purple-500/10" },
  groq: { color: "text-orange-500", glowColor: "orange", icon: "⚡", bgColor: "bg-orange-500/10" },
};

const statusColors: Record<string, string> = {
  active: "text-green-400",
  healthy: "text-green-400",
  degraded: "text-yellow-400",
  error: "text-red-400",
  pending: "text-muted-foreground",
};

const statusDotColors: Record<string, string> = {
  active: "bg-green-400",
  healthy: "bg-green-400",
  degraded: "bg-yellow-400",
  error: "bg-red-400",
  pending: "bg-muted-foreground",
};

// Credential field definitions per provider (for update modal)
const CRED_FIELDS: Record<
  string,
  { key: string; label: string; secret?: boolean; placeholder?: string }[]
> = {
  aws: [
    { key: "access_key_id", label: "Access Key ID", placeholder: "AKIA..." },
    { key: "secret_access_key", label: "Secret Access Key", secret: true },
    { key: "region", label: "Region", placeholder: "us-east-1" },
  ],
  azure: [
    { key: "tenant_id", label: "Tenant ID" },
    { key: "client_id", label: "Client ID" },
    { key: "client_secret", label: "Client Secret", secret: true },
    { key: "subscription_id", label: "Subscription ID" },
    { key: "resource_group", label: "Resource Group" },
    { key: "endpoint", label: "Endpoint" },
  ],
  gcp: [
    { key: "project_id", label: "Project ID" },
    { key: "service_account_json", label: "Service Account Key (JSON)", secret: true },
    { key: "region", label: "Region", placeholder: "us-central1" },
  ],
  openai: [
    { key: "api_key", label: "API Key", secret: true, placeholder: "sk-..." },
    { key: "organization_id", label: "Organization ID", placeholder: "org-..." },
  ],
  anthropic: [
    { key: "api_key", label: "API Key", secret: true, placeholder: "sk-ant-api03-..." },
  ],
  groq: [
    { key: "api_key", label: "API Key", secret: true, placeholder: "gsk_..." },
  ],
};

export default function ProvidersPage() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [summaries, setSummaries] = useState<Record<string, ProviderSummary>>({});
  const [loading, setLoading] = useState(true);
  const [revalidating, setRevalidating] = useState<string | null>(null);
  const [revalidateResult, setRevalidateResult] = useState<
    Record<string, { success: boolean; message: string }>
  >({});
  const [disconnecting, setDisconnecting] = useState<string | null>(null);
  const [confirmDisconnect, setConfirmDisconnect] = useState<string | null>(null);
  const [editingProvider, setEditingProvider] = useState<ProviderSummary | null>(null);
  const [editCreds, setEditCreds] = useState<Record<string, string>>({});
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSuccess, setEditSuccess] = useState(false);

  const fetchProviders = useCallback(async () => {
    try {
      const res = await apiRequest("/api/providers/");
      if (res.ok) {
        const data: Provider[] = await res.json();
        setProviders(data);
        // Fetch summaries for each provider
        const summaryMap: Record<string, ProviderSummary> = {};
        await Promise.all(
          data.map(async (p) => {
            try {
              const sRes = await apiRequest(`/api/providers/${p.id}/summary`);
              if (sRes.ok) {
                summaryMap[p.id] = await sRes.json();
              }
            } catch {}
          })
        );
        setSummaries(summaryMap);
      }
    } catch (err) {
      console.error("Failed to fetch providers:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleRevalidate = async (providerId: string) => {
    setRevalidating(providerId);
    setRevalidateResult((prev) => ({ ...prev, [providerId]: undefined as any }));
    try {
      const res = await apiRequest(`/api/providers/${providerId}/verify`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setRevalidateResult((prev) => ({
          ...prev,
          [providerId]: { success: data.success, message: data.message },
        }));
        // Refresh provider list to reflect status change
        fetchProviders();
      } else if (res.status === 429) {
        setRevalidateResult((prev) => ({
          ...prev,
          [providerId]: { success: false, message: "Rate limited — wait a moment and try again" },
        }));
      } else {
        const body = await res.json().catch(() => null);
        const msg = body?.error?.message || body?.detail || "Verification request failed";
        setRevalidateResult((prev) => ({
          ...prev,
          [providerId]: { success: false, message: msg },
        }));
      }
    } catch {
      setRevalidateResult((prev) => ({
        ...prev,
        [providerId]: { success: false, message: "Network error — check your connection" },
      }));
    } finally {
      setRevalidating(null);
    }
  };

  const handleDisconnect = async (providerId: string) => {
    setDisconnecting(providerId);
    try {
      const res = await apiRequest(`/api/providers/${providerId}`, {
        method: "DELETE",
      });
      if (res.ok || res.status === 204) {
        setProviders((prev) => prev.filter((p) => p.id !== providerId));
        setSummaries((prev) => {
          const next = { ...prev };
          delete next[providerId];
          return next;
        });
      }
    } catch (err) {
      console.error("Failed to disconnect provider:", err);
    } finally {
      setDisconnecting(null);
      setConfirmDisconnect(null);
    }
  };

  const openEditModal = (summary: ProviderSummary) => {
    setEditingProvider(summary);
    // Start all fields blank — backend merges with existing values from Vault
    // Only fields the user fills in will be updated
    setEditCreds({});
    setEditError(null);
    setEditSuccess(false);
  };

  const handleUpdateCredentials = async () => {
    if (!editingProvider) return;
    setEditLoading(true);
    setEditError(null);
    setEditSuccess(false);
    try {
      // Pre-parse service_account_json so it arrives as an object, not a string
      // with literal newlines that break json.loads() on the backend
      const creds = { ...editCreds };
      if (creds.service_account_json && typeof creds.service_account_json === "string") {
        try {
          creds.service_account_json = JSON.parse(creds.service_account_json);
        } catch {
          setEditError("Invalid JSON in Service Account Key — please paste the full JSON key file");
          setEditLoading(false);
          return;
        }
      }
      const res = await apiRequest(
        `/api/providers/${editingProvider.id}/credentials`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credentials: creds }),
        }
      );
      if (res.ok) {
        setEditSuccess(true);
        fetchProviders();
        setTimeout(() => setEditingProvider(null), 1500);
      } else if (res.status === 429) {
        setEditError("Rate limited — please wait a moment and try again");
      } else {
        const data = await res.json().catch(() => ({}));
        setEditError(data.detail || `Failed to update credentials (${res.status})`);
      }
    } catch (err) {
      setEditError(err instanceof Error ? `Network error: ${err.message}` : "Network error — check your connection");
    } finally {
      setEditLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Cloud Providers"
        description="Connect and manage your cloud AI providers"
        actions={
          <div className="flex gap-2">
            <button
              onClick={fetchProviders}
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <Link href="/onboarding">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
              >
                <Plus className="h-4 w-4" />
                Connect Provider
              </motion.button>
            </Link>
          </div>
        }
      />

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <LoadingDots size="lg" />
        </div>
      ) : providers.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 text-center"
        >
          <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            className="text-6xl mb-4"
          >
            ☁️
          </motion.div>
          <h3 className="text-xl font-semibold">No clouds connected yet</h3>
          <p className="text-muted-foreground mt-2 mb-6 max-w-sm">
            Connect your AWS, Azure, or GCP account to start managing AI models
            across clouds.
          </p>
          <Link href="/onboarding">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-6 py-3 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Let&apos;s fix that
            </motion.button>
          </Link>
        </motion.div>
      ) : (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence>
            {providers.map((p) => {
              const style = providerStyles[p.provider_type] || providerStyles.aws;
              const summary = summaries[p.id];
              return (
                <motion.div
                  key={p.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                >
                  <AnimatedCard glowColor={style.glowColor}>
                    {/* Header */}
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-lg text-2xl",
                            style.bgColor
                          )}
                        >
                          {style.icon}
                        </div>
                        <div>
                          <h3 className="font-semibold">{p.name}</h3>
                          <p className="text-sm text-muted-foreground">{p.region}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div
                          className={cn(
                            "h-2 w-2 rounded-full",
                            statusDotColors[p.status] || "bg-gray-400"
                          )}
                        />
                        <span
                          className={cn(
                            "text-xs font-medium capitalize",
                            statusColors[p.status] || "text-muted-foreground"
                          )}
                        >
                          {p.status}
                        </span>
                      </div>
                    </div>

                    {/* Masked credential summary */}
                    {summary?.masked_credentials &&
                      Object.keys(summary.masked_credentials).length > 0 && (
                        <div className="mt-4 space-y-1.5 rounded-md bg-zinc-950/50 border border-border/50 p-3">
                          {Object.entries(summary.masked_credentials)
                            .filter(
                              ([key, val]) =>
                                val && val !== "" && key !== "region" && key !== "resource_group" && key !== "endpoint"
                            )
                            .map(([key, val]) => (
                              <div
                                key={key}
                                className="flex items-center justify-between text-xs"
                              >
                                <span className="text-muted-foreground font-mono">
                                  {key}
                                </span>
                                <span className="font-mono text-zinc-400">{val}</span>
                              </div>
                            ))}
                        </div>
                      )}

                    {/* Stats row */}
                    <div className="mt-4 grid grid-cols-2 gap-4 border-t border-border pt-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Models</p>
                        <p className="text-lg font-semibold">{p.model_count}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Last Validated</p>
                        <p className="text-sm font-medium">
                          {summary?.last_validated
                            ? new Date(summary.last_validated).toLocaleDateString()
                            : new Date(p.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    {/* Revalidation result */}
                    {revalidateResult[p.id] && (
                      <div
                        className={cn(
                          "mt-3 rounded-md p-2 text-xs flex items-center gap-1.5",
                          revalidateResult[p.id].success
                            ? "bg-green-500/10 text-green-400"
                            : "bg-red-500/10 text-red-400"
                        )}
                      >
                        {revalidateResult[p.id].success ? (
                          <CheckCircle2 className="h-3.5 w-3.5" />
                        ) : (
                          <AlertCircle className="h-3.5 w-3.5" />
                        )}
                        {revalidateResult[p.id].message}
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="mt-4 flex flex-col sm:flex-row gap-2">
                      <button
                        onClick={() => handleRevalidate(p.id)}
                        disabled={revalidating === p.id}
                        className="flex-1 flex items-center justify-center gap-1.5 rounded-md border border-border px-3 py-2.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-50 min-h-[44px] touch-manipulation"
                      >
                        {revalidating === p.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <ShieldCheck className="h-3.5 w-3.5" />
                        )}
                        Re-validate
                      </button>
                      <button
                        onClick={() => summary && openEditModal(summary)}
                        disabled={!summary}
                        className="flex-1 flex items-center justify-center gap-1.5 rounded-md border border-border px-3 py-2.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors disabled:opacity-50 min-h-[44px] touch-manipulation"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                        Update
                      </button>
                      <button
                        onClick={() => setConfirmDisconnect(p.id)}
                        className="flex items-center justify-center gap-1.5 rounded-md border border-red-500/30 px-3 py-2.5 text-xs font-medium text-red-400 hover:bg-red-500/10 transition-colors min-h-[44px] min-w-[44px] touch-manipulation"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>

                    {/* Disconnect confirmation */}
                    {confirmDisconnect === p.id && (
                      <div className="mt-3 rounded-md bg-red-500/10 border border-red-500/20 p-3">
                        <p className="text-sm text-red-300 mb-2">
                          Disconnect {p.name}? This will remove all saved
                          credentials.
                        </p>
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleDisconnect(p.id)}
                            disabled={disconnecting === p.id}
                            className="flex-1 rounded-md bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-500 disabled:opacity-50"
                          >
                            {disconnecting === p.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin mx-auto" />
                            ) : (
                              "Yes, Disconnect"
                            )}
                          </button>
                          <button
                            onClick={() => setConfirmDisconnect(null)}
                            className="flex-1 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </AnimatedCard>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {/* Add provider card */}
          <Link href="/onboarding">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: providers.length * 0.1 }}
              whileHover={{ y: -4 }}
              className="flex min-h-[200px] cursor-pointer items-center justify-center rounded-lg border border-dashed border-border p-6 transition-colors hover:border-violet-500/50 hover:bg-accent/30"
            >
              <div className="text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent">
                  <Plus className="h-6 w-6 text-muted-foreground" />
                </div>
                <p className="font-medium">Add Provider</p>
                <p className="text-sm text-muted-foreground">
                  Connect AWS, Azure, or GCP
                </p>
              </div>
            </motion.div>
          </Link>
        </div>
      )}

      {/* Update Credentials Modal */}
      <AnimatePresence>
        {editingProvider && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
            onClick={(e) => {
              if (e.target === e.currentTarget) setEditingProvider(null);
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="w-full max-w-lg rounded-xl border bg-background p-6 shadow-2xl space-y-5"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold">Update Credentials</h3>
                  <p className="text-sm text-muted-foreground">
                    {editingProvider.name} ({editingProvider.provider_type.toUpperCase()})
                  </p>
                </div>
                <button
                  onClick={() => setEditingProvider(null)}
                  className="rounded-md p-1 hover:bg-accent transition-colors"
                >
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>

              <p className="text-xs text-muted-foreground mb-3">
                Only fill in the fields you want to change. Blank fields keep their current values.
              </p>
              <div className="space-y-3">
                {(CRED_FIELDS[editingProvider.provider_type] || []).map((field) => {
                  const currentMasked = editingProvider.masked_credentials[field.key];
                  return (
                    <div key={field.key}>
                      <label className="text-sm text-muted-foreground mb-1 block">
                        {field.label}
                      </label>
                      {field.key === "service_account_json" ? (
                        <textarea
                          className="w-full rounded-md border bg-zinc-950 px-3 py-2 text-sm font-mono min-h-[80px]"
                          placeholder="Paste new JSON to update, or leave blank to keep current"
                          value={editCreds[field.key] || ""}
                          onChange={(e) =>
                            setEditCreds((prev) => ({
                              ...prev,
                              [field.key]: e.target.value,
                            }))
                          }
                        />
                      ) : (
                        <input
                          type={field.secret ? "password" : "text"}
                          className="w-full rounded-md border bg-zinc-950 px-3 py-2 text-sm font-mono"
                          placeholder={currentMasked ? `Keep current (${currentMasked})` : field.placeholder || field.label}
                          value={editCreds[field.key] || ""}
                          onChange={(e) =>
                            setEditCreds((prev) => ({
                              ...prev,
                              [field.key]: e.target.value,
                            }))
                          }
                        />
                      )}
                      {/* Show current value for secret fields */}
                      {field.secret && currentMasked && (
                        <p className="text-xs text-muted-foreground mt-0.5 font-mono">
                          Current: {currentMasked}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              {editError && (
                <div className="rounded-md bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  {editError}
                </div>
              )}

              {editSuccess && (
                <div className="rounded-md bg-green-500/10 border border-green-500/20 p-3 text-sm text-green-400 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Credentials updated and validated successfully
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleUpdateCredentials}
                  disabled={editLoading}
                  className="flex-1 rounded-lg bg-violet-600 hover:bg-violet-500 py-2.5 text-sm font-medium text-white transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {editLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Shield className="h-4 w-4" />
                  )}
                  Validate &amp; Update
                </button>
                <button
                  onClick={() => setEditingProvider(null)}
                  className="rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
