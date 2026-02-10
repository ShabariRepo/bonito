"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { LoadingDots } from "@/components/ui/loading-dots";
import { Shield, Plus, X, Lock, DollarSign, Globe, Database, Trash2 } from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { ErrorBanner } from "@/components/ui/error-banner";

const TYPE_META: Record<string, { icon: typeof Shield; color: string; label: string }> = {
  model_access: { icon: Lock, color: "text-violet-400", label: "Model Access" },
  spend_limits: { icon: DollarSign, color: "text-amber-400", label: "Spend Limits" },
  region_restrictions: { icon: Globe, color: "text-blue-400", label: "Region Restrictions" },
  data_classification: { icon: Database, color: "text-emerald-400", label: "Data Classification" },
};

function ToggleSwitch({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) {
  return (
    <button onClick={onToggle} className={`relative w-11 h-6 rounded-full transition-colors ${enabled ? "bg-violet-600" : "bg-gray-600"}`}>
      <motion.div
        className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow"
        animate={{ left: enabled ? 22 : 2 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
      />
    </button>
  );
}

export default function GovernancePage() {
  const [policies, setPolicies] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("model_access");
  const [newDesc, setNewDesc] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchPolicies = async () => {
    setError(null);
    try {
      const res = await apiRequest("/api/policies/");
      if (res.ok) {
        setPolicies(await res.json());
      } else {
        throw new Error("Failed to load policies");
      }
    } catch (e) {
      console.error("Failed to load policies", e);
      setError("Failed to load governance policies. Please check your connection and try again.");
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchPolicies(); }, []);

  const togglePolicy = async (id: string, enabled: boolean) => {
    await apiRequest(`/api/policies/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: !enabled }),
    });
    fetchPolicies();
  };

  const createPolicy = async () => {
    if (!newName) return;
    await apiRequest("/api/policies/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName, type: newType, description: newDesc, rules_json: {}, enabled: true }),
    });
    setShowCreate(false); setNewName(""); setNewDesc("");
    fetchPolicies();
  };

  const deletePolicy = async (id: string) => {
    await apiRequest(`/api/policies/${id}`, { method: "DELETE" });
    setDeleteConfirm(null);
    fetchPolicies();
  };

  if (loading) return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Governance"
        description="Policies and guardrails for your AI infrastructure"
        actions={
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Policy
          </motion.button>
        }
      />

      {error && <ErrorBanner message={error} onRetry={fetchPolicies} />}

      {policies.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-20 text-center"
        >
          <motion.div animate={{ y: [0, -8, 0] }} transition={{ duration: 3, repeat: Infinity }} className="text-5xl mb-4">
            🎲
          </motion.div>
          <h3 className="text-xl font-semibold">No guardrails yet</h3>
          <p className="text-muted-foreground mt-2">AI without rules is just chaos</p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowCreate(true)}
            className="mt-6 flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700"
          >
            <Plus className="h-4 w-4" />
            Create First Policy
          </motion.button>
        </motion.div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {policies.map((policy, i) => {
            const meta = TYPE_META[policy.type] || TYPE_META.model_access;
            const Icon = meta.icon;
            return (
              <motion.div
                key={policy.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.08 }}
              >
                <Card className={`hover:border-violet-500/20 transition-all ${!policy.enabled ? "opacity-60" : ""}`}>
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div className={`rounded-lg p-2 bg-accent ${meta.color}`}>
                          <Icon className="h-4 w-4" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-sm">{policy.name}</h3>
                          <span className={`text-xs ${meta.color}`}>{meta.label}</span>
                        </div>
                      </div>
                      <ToggleSwitch enabled={policy.enabled} onToggle={() => togglePolicy(policy.id, policy.enabled)} />
                    </div>
                    {policy.description && (
                      <p className="text-sm text-muted-foreground mb-3">{policy.description}</p>
                    )}
                    <div className="flex items-center justify-between">
                      <div className="flex flex-wrap gap-1.5">
                        {Object.entries(policy.rules_json || {}).slice(0, 3).map(([k]) => (
                          <span key={k} className="rounded bg-accent px-2 py-0.5 text-xs text-muted-foreground">
                            {k.replace(/_/g, " ")}
                          </span>
                        ))}
                      </div>
                      <div className="relative">
                        {deleteConfirm === policy.id ? (
                          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-1">
                            <button onClick={() => deletePolicy(policy.id)} className="rounded px-2 py-1 text-xs bg-red-500/15 text-red-400 hover:bg-red-500/25">Delete</button>
                            <button onClick={() => setDeleteConfirm(null)} className="rounded px-2 py-1 text-xs text-muted-foreground hover:text-foreground">Cancel</button>
                          </motion.div>
                        ) : (
                          <button onClick={() => setDeleteConfirm(policy.id)} className="rounded p-1 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors">
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

      {/* Create Modal */}
      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
            onClick={() => setShowCreate(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl"
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold">Create Policy</h2>
                <button onClick={() => setShowCreate(false)} className="rounded-md p-1 hover:bg-accent"><X className="h-5 w-5" /></button>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Policy Name</label>
                  <input
                    type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g., Production Model Whitelist"
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Type</label>
                  <div className="mt-1 grid grid-cols-2 gap-2">
                    {Object.entries(TYPE_META).map(([key, meta]) => {
                      const Icon = meta.icon;
                      return (
                        <button
                          key={key}
                          onClick={() => setNewType(key)}
                          className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-all ${
                            newType === key ? "border-violet-500 bg-violet-500/10 text-violet-400" : "border-border text-muted-foreground hover:border-violet-500/30"
                          }`}
                        >
                          <Icon className="h-3.5 w-3.5" />
                          {meta.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-muted-foreground">Description</label>
                  <textarea
                    value={newDesc} onChange={(e) => setNewDesc(e.target.value)}
                    placeholder="Describe what this policy enforces..."
                    rows={3}
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 resize-none"
                  />
                </div>
                <motion.button
                  whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.99 }}
                  onClick={createPolicy} disabled={!newName}
                  className="w-full rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Create Policy
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
