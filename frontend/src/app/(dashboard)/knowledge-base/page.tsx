"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Plus,
  RefreshCw,
  Upload,
  File,
  Trash2,
  Users,
  Bot,
  Shield,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Database,
  Cloud,
  Server,
  Download,
  Eye,
  MoreHorizontal,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";
import { AnimatedCard } from "@/components/ui/animated-card";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import Link from "next/link";
import { KnowledgeBaseDetailView } from "@/components/knowledge-base/detail-view";

interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  source_type: string;
  status: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

interface Agent {
  id: string;
  name: string;
  description: string;
  knowledge_base_ids: string[];
}

const storageTypes = {
  upload: { name: "Bonito Managed", icon: Database, color: "text-violet-400", bgColor: "bg-violet-500/10" },
  s3: { name: "AWS S3", icon: Cloud, color: "text-amber-400", bgColor: "bg-amber-500/10" },
  gcs: { name: "GCP Storage", icon: Cloud, color: "text-red-400", bgColor: "bg-red-500/10" },
  azure_blob: { name: "Azure Blob", icon: Cloud, color: "text-blue-400", bgColor: "bg-blue-500/10" },
};

const statusColors: Record<string, string> = {
  pending: "text-yellow-400",
  syncing: "text-blue-400",
  ready: "text-green-400",
  error: "text-red-400",
};

const statusDotColors: Record<string, string> = {
  pending: "bg-yellow-400",
  syncing: "bg-blue-400", 
  ready: "bg-green-400",
  error: "bg-red-400",
};

export default function KnowledgeBasePage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [selectedKb, setSelectedKb] = useState<string | null>(null);

  const fetchKnowledgeBases = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiRequest("/api/knowledge-bases");
      if (res.ok) {
        const data: KnowledgeBase[] = await res.json();
        setKnowledgeBases(data);
      }
    } catch (err) {
      console.error("Failed to fetch knowledge bases:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAgents = useCallback(async () => {
    try {
      // Fetch all agents in the org for linking purposes
      // This would need to be implemented as a general agent list endpoint
      // For now, placeholder - in reality you'd fetch from /api/agents or similar
      setAgents([]);
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    }
  }, []);

  useEffect(() => {
    fetchKnowledgeBases();
    fetchAgents();
  }, [fetchKnowledgeBases, fetchAgents]);

  const getLinkedAgentCount = (kbId: string) => {
    return agents.filter(agent => agent.knowledge_base_ids.includes(kbId)).length;
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Knowledge Base"
        description="Manage your file storage and knowledge bases for AI agents"
        actions={
          <div className="flex gap-2">
            <button
              onClick={fetchKnowledgeBases}
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setCreateModalOpen(true)}
              className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Create Knowledge Base
            </motion.button>
          </div>
        }
      />

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <LoadingDots size="lg" />
        </div>
      ) : knowledgeBases.length === 0 ? (
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
            📚
          </motion.div>
          <h3 className="text-xl font-semibold">No knowledge bases yet</h3>
          <p className="text-muted-foreground mt-2 mb-6 max-w-sm">
            Create your first knowledge base to store documents and files that your AI agents can access.
          </p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setCreateModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-6 py-3 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Create Your First Knowledge Base
          </motion.button>
        </motion.div>
      ) : (
        <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          <AnimatePresence>
            {knowledgeBases.map((kb) => {
              const storageConfig = storageTypes[kb.source_type as keyof typeof storageTypes] || storageTypes.upload;
              const StorageIcon = storageConfig.icon;
              const linkedAgentCount = getLinkedAgentCount(kb.id);
              
              return (
                <motion.div
                  key={kb.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                >
                  <AnimatedCard 
                    glowColor="violet"
                    onClick={() => setSelectedKb(kb.id)}
                  >
                    {/* Header */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-lg",
                            storageConfig.bgColor
                          )}
                        >
                          <StorageIcon className={cn("h-6 w-6", storageConfig.color)} />
                        </div>
                        <div>
                          <h3 className="font-semibold text-white">{kb.name}</h3>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={cn(
                              "text-xs px-2 py-0.5 rounded-full border",
                              storageConfig.bgColor,
                              "border-white/10"
                            )}>
                              {storageConfig.name}
                            </span>
                            <div className="flex items-center gap-1">
                              <div
                                className={cn(
                                  "h-1.5 w-1.5 rounded-full",
                                  statusDotColors[kb.status] || "bg-gray-400"
                                )}
                              />
                              <span
                                className={cn(
                                  "text-xs capitalize",
                                  statusColors[kb.status] || "text-muted-foreground"
                                )}
                              >
                                {kb.status}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                      <button className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                    </div>

                    {/* Description */}
                    {kb.description && (
                      <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
                        {kb.description}
                      </p>
                    )}

                    {/* Stats */}
                    <div className="grid grid-cols-3 gap-4 border-t border-border pt-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Documents</p>
                        <p className="text-lg font-semibold text-white">{kb.document_count}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Chunks</p>
                        <p className="text-lg font-semibold text-white">{kb.chunk_count}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Agents</p>
                        <div className="flex items-center gap-1">
                          <p className="text-lg font-semibold text-white">{linkedAgentCount}</p>
                          <Bot className="h-3 w-3 text-muted-foreground" />
                        </div>
                      </div>
                    </div>

                    {/* Created date */}
                    <div className="mt-3 text-xs text-muted-foreground">
                      Created {new Date(kb.created_at).toLocaleDateString()}
                    </div>
                  </AnimatedCard>
                </motion.div>
              );
            })}
          </AnimatePresence>

          {/* Add new KB card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: knowledgeBases.length * 0.1 }}
            whileHover={{ y: -4 }}
            onClick={() => setCreateModalOpen(true)}
            className="flex min-h-[200px] cursor-pointer items-center justify-center rounded-lg border border-dashed border-border p-6 transition-colors hover:border-violet-500/50 hover:bg-accent/30"
          >
            <div className="text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-accent">
                <Plus className="h-6 w-6 text-muted-foreground" />
              </div>
              <p className="font-medium text-white">Add Knowledge Base</p>
              <p className="text-sm text-muted-foreground">
                Store files for your agents
              </p>
            </div>
          </motion.div>
        </div>
      )}

      {/* Create KB Modal */}
      <CreateKnowledgeBaseModal 
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSuccess={fetchKnowledgeBases}
      />

      {/* KB Detail View */}
      {selectedKb && (
        <KnowledgeBaseDetailView 
          kbId={selectedKb}
          onClose={() => setSelectedKb(null)}
        />
      )}
    </div>
  );
}

// Create Knowledge Base Modal Component
function CreateKnowledgeBaseModal({ 
  open, 
  onClose, 
  onSuccess 
}: { 
  open: boolean; 
  onClose: () => void; 
  onSuccess: () => void; 
}) {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    source_type: "upload" as keyof typeof storageTypes,
  });
  const [cloudConfig, setCloudConfig] = useState({
    // AWS S3
    bucket_name: "",
    region: "",
    access_key_id: "",
    secret_access_key: "",
    // GCP
    project_id: "",
    service_account_json: "",
    // Azure
    container: "",
    connection_string: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!formData.name.trim()) {
      setError("Name is required");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload: any = {
        name: formData.name,
        description: formData.description || "",
        source_type: formData.source_type,
      };

      // Add cloud config if not upload type
      if (formData.source_type !== "upload") {
        const config: any = {};
        
        switch (formData.source_type) {
          case "s3":
            config.bucket_name = cloudConfig.bucket_name;
            config.region = cloudConfig.region;
            config.access_key_id = cloudConfig.access_key_id;
            config.secret_access_key = cloudConfig.secret_access_key;
            break;
          case "gcs":
            config.project_id = cloudConfig.project_id;
            config.bucket_name = cloudConfig.bucket_name;
            config.service_account_json = JSON.parse(cloudConfig.service_account_json);
            break;
          case "azure_blob":
            config.container = cloudConfig.container;
            config.connection_string = cloudConfig.connection_string;
            break;
        }
        payload.source_config = config;
      }

      const res = await apiRequest("/api/knowledge-bases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        onSuccess();
        onClose();
        // Reset form
        setFormData({ name: "", description: "", source_type: "upload" });
        setCloudConfig({
          bucket_name: "",
          region: "",
          access_key_id: "",
          secret_access_key: "",
          project_id: "",
          service_account_json: "",
          container: "",
          connection_string: "",
        });
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || `Failed to create knowledge base (${res.status})`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Network error");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl border bg-background p-6 shadow-2xl space-y-5"
      >
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Create Knowledge Base</h3>
            <p className="text-sm text-muted-foreground">
              Set up a new knowledge base to store files for your AI agents
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 hover:bg-accent transition-colors"
          >
            <X className="h-5 w-5 text-muted-foreground" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Basic info */}
          <div>
            <label className="block text-sm font-medium mb-1">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
              placeholder="My Knowledge Base"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm min-h-[60px]"
              placeholder="Brief description of what this knowledge base contains..."
            />
          </div>

          {/* Storage type selector */}
          <div>
            <label className="block text-sm font-medium mb-2">Storage Type</label>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(storageTypes).map(([key, config]) => {
                const StorageIcon = config.icon;
                return (
                  <button
                    key={key}
                    onClick={() => setFormData(prev => ({ ...prev, source_type: key as keyof typeof storageTypes }))}
                    className={cn(
                      "flex items-center gap-3 rounded-lg border-2 p-4 text-left transition-all",
                      formData.source_type === key
                        ? "border-violet-500 bg-violet-500/10"
                        : "border-border hover:border-violet-500/50"
                    )}
                  >
                    <StorageIcon className={cn("h-5 w-5", config.color)} />
                    <div>
                      <p className="font-medium text-sm">{config.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {key === "upload" && "Bonito manages storage"}
                        {key === "s3" && "Your AWS S3 bucket"}
                        {key === "gcs" && "Your GCP storage bucket"}
                        {key === "azure_blob" && "Your Azure container"}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Cloud storage configuration */}
          {formData.source_type !== "upload" && (
            <div className="border rounded-lg p-4 space-y-4">
              <h4 className="font-medium">Cloud Storage Configuration</h4>
              
              {formData.source_type === "s3" && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">Bucket Name *</label>
                    <input
                      type="text"
                      value={cloudConfig.bucket_name}
                      onChange={(e) => setCloudConfig(prev => ({ ...prev, bucket_name: e.target.value }))}
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      placeholder="my-bucket"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Region *</label>
                    <input
                      type="text"
                      value={cloudConfig.region}
                      onChange={(e) => setCloudConfig(prev => ({ ...prev, region: e.target.value }))}
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      placeholder="us-east-1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Access Key ID *</label>
                    <input
                      type="text"
                      value={cloudConfig.access_key_id}
                      onChange={(e) => setCloudConfig(prev => ({ ...prev, access_key_id: e.target.value }))}
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      placeholder="AKIA..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Secret Access Key *</label>
                    <input
                      type="password"
                      value={cloudConfig.secret_access_key}
                      onChange={(e) => setCloudConfig(prev => ({ ...prev, secret_access_key: e.target.value }))}
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      placeholder="Secret key..."
                    />
                  </div>
                </div>
              )}

              {formData.source_type === "gcs" && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium mb-1">Project ID *</label>
                      <input
                        type="text"
                        value={cloudConfig.project_id}
                        onChange={(e) => setCloudConfig(prev => ({ ...prev, project_id: e.target.value }))}
                        className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                        placeholder="my-project"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">Bucket Name *</label>
                      <input
                        type="text"
                        value={cloudConfig.bucket_name}
                        onChange={(e) => setCloudConfig(prev => ({ ...prev, bucket_name: e.target.value }))}
                        className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                        placeholder="my-bucket"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Service Account Key (JSON) *</label>
                    <textarea
                      value={cloudConfig.service_account_json}
                      onChange={(e) => setCloudConfig(prev => ({ ...prev, service_account_json: e.target.value }))}
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono min-h-[100px]"
                      placeholder='{"type": "service_account", ...}'
                    />
                  </div>
                </div>
              )}

              {formData.source_type === "azure_blob" && (
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">Container Name *</label>
                    <input
                      type="text"
                      value={cloudConfig.container}
                      onChange={(e) => setCloudConfig(prev => ({ ...prev, container: e.target.value }))}
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      placeholder="my-container"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Connection String *</label>
                    <input
                      type="password"
                      value={cloudConfig.connection_string}
                      onChange={(e) => setCloudConfig(prev => ({ ...prev, connection_string: e.target.value }))}
                      className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                      placeholder="DefaultEndpointsProtocol=https;AccountName=..."
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-md bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {error}
          </div>
        )}

        <div className="flex gap-3 pt-2">
          <button
            onClick={handleCreate}
            disabled={loading}
            className="flex-1 rounded-lg bg-violet-600 hover:bg-violet-500 py-2.5 text-sm font-medium text-white transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Plus className="h-4 w-4" />
            )}
            Create Knowledge Base
          </button>
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Cancel
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}