"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  Upload,
  File,
  FileText,
  FileImage,
  FileCode,
  Trash2,
  Download,
  Eye,
  Bot,
  Users,
  Plus,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
  MoreHorizontal,
  Settings,
  Link,
  Unlink,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";

interface Document {
  id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  status: string;
  created_at: string;
  error_message?: string;
}

interface Agent {
  id: string;
  name: string;
  description: string;
  status: string;
}

interface KnowledgeBaseDetail {
  id: string;
  name: string;
  description: string;
  source_type: string;
  status: string;
  document_count: number;
  chunk_count: number;
  created_at: string;
}

const fileTypeIcons = {
  pdf: FileText,
  txt: FileText,
  docx: FileText,
  csv: FileCode,
  json: FileCode,
  xlsx: FileCode,
  jpg: FileImage,
  png: FileImage,
  default: File,
};

const statusColors: Record<string, string> = {
  pending: "text-yellow-400",
  processing: "text-blue-400",
  ready: "text-green-400",
  error: "text-red-400",
};

export function KnowledgeBaseDetailView({
  kbId,
  onClose,
}: {
  kbId: string;
  onClose: () => void;
}) {
  const [kb, setKb] = useState<KnowledgeBaseDetail | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [linkedAgents, setLinkedAgents] = useState<Agent[]>([]);
  const [allAgents, setAllAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [agentSearchQuery, setAgentSearchQuery] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchKbDetails = useCallback(async () => {
    try {
      setLoading(true);
      const [kbRes, docsRes, linkedRes] = await Promise.all([
        apiRequest(`/api/knowledge-bases/${kbId}`),
        apiRequest(`/api/knowledge-bases/${kbId}/documents`),
        apiRequest(`/api/knowledge-bases/${kbId}/linked-agents`),
      ]);

      if (kbRes.ok) setKb(await kbRes.json());
      if (docsRes.ok) setDocuments(await docsRes.json());
      if (linkedRes.ok) setLinkedAgents(await linkedRes.json());
    } catch (err) {
      console.error("Failed to fetch KB details:", err);
    } finally {
      setLoading(false);
    }
  }, [kbId]);

  const fetchAllAgents = useCallback(async () => {
    try {
      // This would need to be implemented - fetch all agents in the org
      // For now, placeholder
      setAllAgents([]);
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    }
  }, []);

  useEffect(() => {
    fetchKbDetails();
    fetchAllAgents();
  }, [fetchKbDetails, fetchAllAgents]);

  const handleFileUpload = async (files: FileList) => {
    if (!files.length || kb?.source_type !== "upload") return;

    setUploading(true);
    const uploadedFiles: string[] = [];

    try {
      for (const file of Array.from(files)) {
        // Check file type
        const allowedTypes = [".pdf", ".docx", ".txt", ".md", ".html", ".csv", ".json"];
        const fileExt = "." + file.name.split(".").pop()?.toLowerCase();
        if (!allowedTypes.includes(fileExt)) {
          alert(`Unsupported file type: ${fileExt}. Allowed: ${allowedTypes.join(", ")}`);
          continue;
        }

        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
          alert(`File ${file.name} is too large. Maximum size is 10MB.`);
          continue;
        }

        const formData = new FormData();
        formData.append("file", file);

        const res = await apiRequest(`/api/knowledge-bases/${kbId}/documents`, {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          uploadedFiles.push(file.name);
        }
      }

      if (uploadedFiles.length > 0) {
        await fetchKbDetails(); // Refresh the view
      }
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileUpload(e.dataTransfer.files);
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm("Are you sure you want to delete this document?")) return;

    try {
      const res = await apiRequest(`/api/knowledge-bases/${kbId}/documents/${docId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        await fetchKbDetails();
      }
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const handleLinkAgent = async (agentId: string) => {
    try {
      const res = await apiRequest(`/api/knowledge-bases/${kbId}/link-agent/${agentId}`, {
        method: "POST",
      });

      if (res.ok) {
        await fetchKbDetails();
        setShowAgentModal(false);
      }
    } catch (err) {
      console.error("Link failed:", err);
    }
  };

  const handleUnlinkAgent = async (agentId: string) => {
    try {
      const res = await apiRequest(`/api/knowledge-bases/${kbId}/unlink-agent/${agentId}`, {
        method: "DELETE",
      });

      if (res.ok) {
        await fetchKbDetails();
      }
    } catch (err) {
      console.error("Unlink failed:", err);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const getFileIcon = (fileType: string) => {
    const IconComponent = fileTypeIcons[fileType as keyof typeof fileTypeIcons] || fileTypeIcons.default;
    return IconComponent;
  };

  if (loading || !kb) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      >
        <div className="flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-violet-500" />
        </div>
      </motion.div>
    );
  }

  const filteredAvailableAgents = allAgents.filter(
    (agent) =>
      !linkedAgents.some((linked) => linked.id === agent.id) &&
      agent.name.toLowerCase().includes(agentSearchQuery.toLowerCase())
  );

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="absolute inset-4 rounded-xl border bg-background shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center gap-4 p-6 border-b border-border">
          <button
            onClick={onClose}
            className="rounded-md p-2 hover:bg-accent transition-colors"
          >
            <ArrowLeft className="h-5 w-5 text-muted-foreground" />
          </button>
          <div className="flex-1">
            <h2 className="text-xl font-semibold">{kb.name}</h2>
            <p className="text-sm text-muted-foreground">{kb.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm capitalize px-2 py-1 rounded-full border border-border",
                statusColors[kb.status]
              )}
            >
              {kb.status}
            </span>
            <button className="rounded-md p-2 hover:bg-accent transition-colors">
              <Settings className="h-5 w-5 text-muted-foreground" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Main content area */}
          <div className="flex-1 overflow-y-auto">
            {/* Stats bar */}
            <div className="grid grid-cols-3 gap-4 p-6 border-b border-border">
              <div>
                <p className="text-sm text-muted-foreground">Documents</p>
                <p className="text-2xl font-semibold">{kb.document_count}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Chunks</p>
                <p className="text-2xl font-semibold">{kb.chunk_count}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Linked Agents</p>
                <p className="text-2xl font-semibold">{linkedAgents.length}</p>
              </div>
            </div>

            {/* Upload area (only for upload type KBs) */}
            {kb.source_type === "upload" && (
              <div className="p-6 border-b border-border">
                <div
                  className={cn(
                    "relative rounded-lg border-2 border-dashed transition-colors p-6",
                    dragOver
                      ? "border-violet-500 bg-violet-500/10"
                      : "border-border hover:border-violet-500/50"
                  )}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                  }}
                  onDrop={handleDrop}
                >
                  <div className="text-center">
                    <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                    <p className="text-sm font-medium">
                      Drag and drop files here, or{" "}
                      <button
                        onClick={() => fileInputRef.current?.click()}
                        className="text-violet-500 hover:text-violet-400 underline"
                      >
                        click to browse
                      </button>
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Supports PDF, DOCX, TXT, CSV, JSON up to 10MB
                    </p>
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".pdf,.docx,.txt,.md,.html,.csv,.json"
                    onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
                    className="hidden"
                  />
                  {uploading && (
                    <div className="absolute inset-0 bg-background/80 flex items-center justify-center">
                      <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Documents list */}
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Documents</h3>
              </div>

              {documents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <File className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>No documents uploaded yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map((doc) => {
                    const FileIcon = getFileIcon(doc.file_type);
                    return (
                      <motion.div
                        key={doc.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors group"
                      >
                        <FileIcon className="h-5 w-5 text-muted-foreground" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{doc.file_name}</p>
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            <span>{formatFileSize(doc.file_size)}</span>
                            <span className={statusColors[doc.status]}>{doc.status}</span>
                            <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                          </div>
                          {doc.error_message && (
                            <p className="text-xs text-red-400 mt-1">{doc.error_message}</p>
                          )}
                        </div>
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                          <button
                            onClick={() => handleDeleteDocument(doc.id)}
                            className="p-1 rounded hover:bg-red-500/20 text-red-400 hover:text-red-300 transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar - Agent management */}
          <div className="w-80 border-l border-border bg-background/50">
            <div className="p-4 border-b border-border">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Linked Agents</h3>
                <button
                  onClick={() => setShowAgentModal(true)}
                  className="rounded-md p-1 hover:bg-accent transition-colors text-violet-500"
                >
                  <Plus className="h-4 w-4" />
                </button>
              </div>
              
              {linkedAgents.length === 0 ? (
                <div className="text-center py-6 text-muted-foreground">
                  <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p className="text-sm">No agents linked</p>
                  <button
                    onClick={() => setShowAgentModal(true)}
                    className="text-xs text-violet-500 hover:text-violet-400 mt-1"
                  >
                    Link your first agent
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {linkedAgents.map((agent) => (
                    <div
                      key={agent.id}
                      className="flex items-center gap-2 p-2 rounded border border-border group hover:bg-accent/50 transition-colors"
                    >
                      <Bot className="h-4 w-4 text-violet-400" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{agent.name}</p>
                        <p className="text-xs text-muted-foreground truncate">{agent.description}</p>
                      </div>
                      <button
                        onClick={() => handleUnlinkAgent(agent.id)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-500/20 text-red-400"
                      >
                        <Unlink className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Link Agent Modal */}
        <AnimatePresence>
          {showAgentModal && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-10 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
              onClick={(e) => {
                if (e.target === e.currentTarget) setShowAgentModal(false);
              }}
            >
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 20 }}
                className="w-full max-w-md rounded-xl border bg-background p-6 shadow-2xl"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold">Link Agent</h3>
                  <button
                    onClick={() => setShowAgentModal(false)}
                    className="rounded-md p-1 hover:bg-accent transition-colors"
                  >
                    <X className="h-4 w-4 text-muted-foreground" />
                  </button>
                </div>

                <div className="relative mb-4">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <input
                    type="text"
                    placeholder="Search agents..."
                    value={agentSearchQuery}
                    onChange={(e) => setAgentSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 rounded-md border bg-background text-sm"
                  />
                </div>

                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {filteredAvailableAgents.length === 0 ? (
                    <p className="text-center py-6 text-muted-foreground text-sm">
                      {allAgents.length === 0 ? "No agents available" : "No matching agents"}
                    </p>
                  ) : (
                    filteredAvailableAgents.map((agent) => (
                      <button
                        key={agent.id}
                        onClick={() => handleLinkAgent(agent.id)}
                        className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:bg-accent/50 transition-colors text-left"
                      >
                        <Bot className="h-5 w-5 text-violet-400" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm truncate">{agent.name}</p>
                          <p className="text-xs text-muted-foreground truncate">{agent.description}</p>
                        </div>
                        <Link className="h-4 w-4 text-muted-foreground" />
                      </button>
                    ))
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
}