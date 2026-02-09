"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  Key,
  Copy,
  Check,
  Plus,
  Trash2,
  Settings,
  Shield,
  X,
} from "lucide-react";
import { API_URL } from "@/lib/utils";

/* ─── Types ─── */

interface GatewayKey {
  id: string;
  name: string;
  key_prefix: string;
  team_id: string | null;
  rate_limit: number;
  allowed_models: {
    models?: string[];
    providers?: string[];
  } | null;
  created_at: string;
  revoked_at: string | null;
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

/* ─── Key Creation Modal ─── */

function CreateKeyModal({ 
  isOpen, 
  onClose, 
  onCreate 
}: { 
  isOpen: boolean; 
  onClose: () => void; 
  onCreate: (keyData: any) => void; 
}) {
  const [name, setName] = useState("");
  const [teamId, setTeamId] = useState("");
  const [rateLimit, setRateLimit] = useState(60);
  const [modelRestrictions, setModelRestrictions] = useState<string[]>([]);
  const [providerRestrictions, setProviderRestrictions] = useState<string[]>([]);
  const [newModel, setNewModel] = useState("");
  const [creating, setCreating] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setCreating(true);
    try {
      const allowedModels = modelRestrictions.length > 0 || providerRestrictions.length > 0 ? {
        models: modelRestrictions.length > 0 ? modelRestrictions : undefined,
        providers: providerRestrictions.length > 0 ? providerRestrictions : undefined,
      } : null;

      await onCreate({
        name,
        team_id: teamId || null,
        rate_limit: rateLimit,
        allowed_models: allowedModels,
      });
      
      // Reset form
      setName("");
      setTeamId("");
      setRateLimit(60);
      setModelRestrictions([]);
      setProviderRestrictions([]);
      onClose();
    } finally {
      setCreating(false);
    }
  };

  const addModel = () => {
    if (newModel && !modelRestrictions.includes(newModel)) {
      setModelRestrictions([...modelRestrictions, newModel]);
      setNewModel("");
    }
  };

  const removeModel = (model: string) => {
    setModelRestrictions(modelRestrictions.filter(m => m !== model));
  };

  const toggleProvider = (provider: string) => {
    setProviderRestrictions(prev => 
      prev.includes(provider) 
        ? prev.filter(p => p !== provider)
        : [...prev, provider]
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-card border border-border rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Create API Key</h2>
          <button onClick={onClose} className="p-1 hover:bg-accent rounded">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Name */}
          <div>
            <label className="text-sm font-medium">Key Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full mt-1 bg-accent/50 border border-border rounded px-3 py-2 text-sm"
              placeholder="Production API, Development, etc."
            />
          </div>

          {/* Team ID */}
          <div>
            <label className="text-sm font-medium">Team ID (Optional)</label>
            <input
              type="text"
              value={teamId}
              onChange={(e) => setTeamId(e.target.value)}
              className="w-full mt-1 bg-accent/50 border border-border rounded px-3 py-2 text-sm"
              placeholder="team-production"
            />
          </div>

          {/* Rate Limit */}
          <div>
            <label className="text-sm font-medium">Rate Limit (req/min)</label>
            <input
              type="number"
              value={rateLimit}
              onChange={(e) => setRateLimit(parseInt(e.target.value) || 60)}
              min="1"
              max="10000"
              className="w-full mt-1 bg-accent/50 border border-border rounded px-3 py-2 text-sm"
            />
          </div>

          {/* Provider Restrictions */}
          <div>
            <label className="text-sm font-medium">Allowed Providers</label>
            <div className="flex gap-2 mt-2">
              {["aws", "azure", "gcp"].map(provider => (
                <button
                  key={provider}
                  onClick={() => toggleProvider(provider)}
                  className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                    providerRestrictions.includes(provider)
                      ? "bg-violet-600 text-white border-violet-600"
                      : "bg-accent border-border text-muted-foreground"
                  }`}
                >
                  {provider.toUpperCase()}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Leave empty to allow all providers</p>
          </div>

          {/* Model Restrictions */}
          <div>
            <label className="text-sm font-medium">Allowed Models</label>
            <div className="flex gap-2 mt-1">
              <input
                type="text"
                value={newModel}
                onChange={(e) => setNewModel(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && addModel()}
                className="flex-1 bg-accent/50 border border-border rounded px-3 py-1 text-sm"
                placeholder="gpt-4o, claude-3-5-sonnet, etc."
              />
              <button
                onClick={addModel}
                className="px-3 py-1 bg-violet-600 text-white rounded text-sm"
              >
                Add
              </button>
            </div>
            {modelRestrictions.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {modelRestrictions.map(model => (
                  <span
                    key={model}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-violet-600/20 text-violet-300 rounded text-xs"
                  >
                    {model}
                    <button onClick={() => removeModel(model)}>
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <p className="text-xs text-muted-foreground mt-1">Leave empty to allow all models</p>
          </div>

          <div className="flex gap-2 pt-4">
            <button
              onClick={onClose}
              className="flex-1 py-2 border border-border rounded text-sm hover:bg-accent"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={creating || !name.trim()}
              className="flex-1 py-2 bg-violet-600 text-white rounded text-sm hover:bg-violet-700 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Key"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

/* ─── Main Page ─── */

export default function GatewayKeysPage() {
  const [keys, setKeys] = useState<GatewayKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyResult, setNewKeyResult] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/gateway/keys`);
      if (res.ok) setKeys(await res.json());
    } catch (e) {
      console.error("Failed to fetch keys:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchKeys(); }, [fetchKeys]);

  const createKey = async (keyData: any) => {
    const res = await fetch(`${API_URL}/api/gateway/keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(keyData),
    });
    if (res.ok) {
      const data = await res.json();
      setNewKeyResult(data.key);
      fetchKeys();
    }
  };

  const revokeKey = async (id: string) => {
    if (!confirm("Revoke this API key? This cannot be undone.")) return;
    const res = await fetch(`${API_URL}/api/gateway/keys/${id}`, { method: "DELETE" });
    if (res.ok) fetchKeys();
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
        title="API Keys"
        description="Manage API keys for gateway access with fine-grained permissions and rate limiting."
        actions={
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Key
          </button>
        }
      />

      {/* New Key Banner */}
      <AnimatePresence>
        {newKeyResult && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="bg-green-500/10 border border-green-500/30 rounded-lg p-4"
          >
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-green-400 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium text-green-300 mb-2">
                  ⚠️ API Key Created Successfully
                </p>
                <p className="text-xs text-green-400 mb-3">
                  Copy your API key now — it won't be shown again!
                </p>
                <div className="flex items-center gap-2 bg-black/30 rounded p-3">
                  <code className="text-sm font-mono text-green-300 break-all flex-1">{newKeyResult}</code>
                  <CopyButton text={newKeyResult} />
                </div>
                <button
                  onClick={() => setNewKeyResult(null)}
                  className="text-xs text-green-400 mt-2 hover:text-green-300"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Keys List */}
      <div className="grid gap-4">
        {keys.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <Key className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No API keys yet</h3>
              <p className="text-muted-foreground mb-4">
                Create your first API key to start using the gateway
              </p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors"
              >
                <Plus className="h-4 w-4" />
                Create Key
              </button>
            </CardContent>
          </Card>
        ) : (
          keys.map((key) => (
            <motion.div key={key.id} layout>
              <Card className={key.revoked_at ? "opacity-60" : ""}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-semibold">{key.name}</h3>
                        {key.revoked_at ? (
                          <Badge variant="destructive">Revoked</Badge>
                        ) : (
                          <Badge variant="secondary">Active</Badge>
                        )}
                      </div>
                      
                      <div className="space-y-2 text-sm text-muted-foreground">
                        <div className="flex items-center gap-4">
                          <span>
                            <strong>Key:</strong> <code className="font-mono">{key.key_prefix}</code>
                          </span>
                          <span>
                            <strong>Rate Limit:</strong> {key.rate_limit} req/min
                          </span>
                          {key.team_id && (
                            <span>
                              <strong>Team:</strong> {key.team_id}
                            </span>
                          )}
                        </div>
                        
                        <div>
                          <strong>Created:</strong> {new Date(key.created_at).toLocaleDateString()}
                          {key.revoked_at && (
                            <span className="ml-4">
                              <strong>Revoked:</strong> {new Date(key.revoked_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>

                        {key.allowed_models && (
                          <div className="space-y-1">
                            {key.allowed_models.providers && (
                              <div>
                                <strong>Allowed Providers:</strong>
                                <div className="flex gap-1 mt-1">
                                  {key.allowed_models.providers.map(provider => (
                                    <Badge key={provider} variant="outline" className="text-xs">
                                      {provider.toUpperCase()}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}
                            {key.allowed_models.models && (
                              <div>
                                <strong>Allowed Models:</strong>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {key.allowed_models.models.map(model => (
                                    <Badge key={model} variant="outline" className="text-xs font-mono">
                                      {model}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-2 ml-4">
                      {!key.revoked_at && (
                        <button
                          onClick={() => revokeKey(key.id)}
                          className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))
        )}
      </div>

      <CreateKeyModal 
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={createKey}
      />
    </div>
  );
}