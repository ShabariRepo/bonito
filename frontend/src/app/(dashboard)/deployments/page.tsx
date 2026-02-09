"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { Rocket, MoreVertical, Globe, Cpu, Clock, Plus, Trash2, RefreshCw } from "lucide-react";
import { API_URL } from "@/lib/utils";

interface Deployment {
  id: string;
  name: string;
  model_id: string;
  provider: string;
  region: string;
  status: string;
  replicas: number;
  endpoint_url: string | null;
  created_at: string;
  updated_at: string;
}

const statusVariant = (s: string) => {
  switch (s) {
    case "active": return "success" as const;
    case "deploying": return "warning" as const;
    case "stopped": return "destructive" as const;
    default: return "secondary" as const;
  }
};

export default function DeploymentsPage() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newModel, setNewModel] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const fetchDeployments = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/deployments/`);
      if (res.ok) setDeployments(await res.json());
    } catch (e) {
      console.error("Failed to fetch deployments", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDeployments(); }, [fetchDeployments]);

  const createDeployment = async () => {
    if (!newName || !newModel) return;
    setCreating(true);
    try {
      const res = await fetch(`${API_URL}/api/deployments/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, model_id: newModel }),
      });
      if (res.ok) {
        setShowCreate(false);
        setNewName("");
        setNewModel("");
        fetchDeployments();
      }
    } finally {
      setCreating(false);
    }
  };

  const deleteDeployment = async (id: string) => {
    try {
      await fetch(`${API_URL}/api/deployments/${id}`, { method: "DELETE" });
      setDeleteConfirm(null);
      fetchDeployments();
    } catch {}
  };

  const toggleStatus = async (d: Deployment) => {
    const newStatus = d.status === "active" ? "stopped" : "active";
    try {
      await fetch(`${API_URL}/api/deployments/${d.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      fetchDeployments();
    } catch {}
  };

  if (loading) {
    return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Deployments</h1>
          <p className="text-muted-foreground mt-1">Manage your model deployments</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={fetchDeployments}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
          >
            <Rocket className="h-4 w-4" />
            New Deployment
          </motion.button>
        </div>
      </div>

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
              className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl space-y-4"
            >
              <h2 className="text-lg font-semibold">Create Deployment</h2>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Deployment Name</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g., GPT-4 Production"
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-muted-foreground">Model ID</label>
                <input
                  type="text"
                  value={newModel}
                  onChange={(e) => setNewModel(e.target.value)}
                  placeholder="e.g., anthropic.claude-3-sonnet"
                  className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                />
              </div>
              <div className="flex gap-2 pt-2">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={createDeployment}
                  disabled={creating || !newName || !newModel}
                  className="flex-1 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50 transition-colors"
                >
                  {creating ? "Creating..." : "Create"}
                </motion.button>
                <button
                  onClick={() => setShowCreate(false)}
                  className="rounded-md border border-border px-4 py-2.5 text-sm font-medium hover:bg-accent transition-colors"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

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
          <p className="text-muted-foreground mt-2">Deploy models to start serving AI requests</p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowCreate(true)}
            className="mt-6 flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700"
          >
            <Plus className="h-4 w-4" />
            Create First Deployment
          </motion.button>
        </motion.div>
      ) : (
        <div className="space-y-3">
          {deployments.map((d, i) => (
            <motion.div
              key={d.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className="hover:border-violet-500/30 transition-colors">
                <CardContent className="flex items-center justify-between py-5">
                  <div className="flex items-center gap-4">
                    <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-accent">
                      <Rocket className="h-5 w-5 text-violet-400" />
                    </div>
                    <div>
                      <p className="font-medium">{d.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {d.model_id} · {d.provider || "auto"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    {d.region && (
                      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                        <Globe className="h-3.5 w-3.5" />
                        {d.region}
                      </div>
                    )}
                    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                      <Cpu className="h-3.5 w-3.5" />
                      {d.replicas} replica{d.replicas !== 1 ? "s" : ""}
                    </div>
                    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
                      <Clock className="h-3.5 w-3.5" />
                      {new Date(d.created_at).toLocaleDateString()}
                    </div>
                    <Badge variant={statusVariant(d.status)}>{d.status}</Badge>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => toggleStatus(d)}
                        className="rounded px-2 py-1 text-xs border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                      >
                        {d.status === "active" ? "Stop" : "Start"}
                      </button>
                      {deleteConfirm === d.id ? (
                        <div className="flex gap-1">
                          <button
                            onClick={() => deleteDeployment(d.id)}
                            className="rounded px-2 py-1 text-xs bg-red-500/15 text-red-400 hover:bg-red-500/25"
                          >
                            Delete
                          </button>
                          <button
                            onClick={() => setDeleteConfirm(null)}
                            className="rounded px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirm(d.id)}
                          className="rounded p-1 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
