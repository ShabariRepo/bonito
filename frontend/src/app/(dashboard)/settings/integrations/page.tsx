"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
  Zap,
  Settings,
  X,
  ExternalLink,
  Power,
  PowerOff,
  RotateCw,
} from "lucide-react";
import { apiRequest } from "@/lib/auth";

// ── Integration type config ──

const INTEGRATION_TYPES = [
  { value: "datadog", label: "Datadog", description: "Send logs to Datadog via HTTP API", color: "text-purple-400", fields: ["api_key"], configFields: ["site", "source", "service", "tags", "env"] },
  { value: "splunk", label: "Splunk", description: "Send logs via HTTP Event Collector", color: "text-green-400", fields: ["hec_token"], configFields: ["hec_url", "index", "source", "sourcetype"] },
  { value: "cloudwatch", label: "AWS CloudWatch", description: "Send logs via boto3", color: "text-orange-400", fields: ["aws_access_key_id", "aws_secret_access_key"], configFields: ["region", "log_group", "log_stream"] },
  { value: "webhook", label: "Webhook", description: "Send logs to any HTTP endpoint", color: "text-blue-400", fields: ["secret"], configFields: ["url"] },
  { value: "elasticsearch", label: "Elasticsearch", description: "Send to Elasticsearch/OpenSearch (coming soon)", color: "text-yellow-400", fields: [], configFields: [], disabled: true },
  { value: "azure_monitor", label: "Azure Monitor", description: "Azure Log Analytics (coming soon)", color: "text-sky-400", fields: [], configFields: [], disabled: true },
  { value: "gcp_logging", label: "Google Cloud Logging", description: "Cloud Logging (coming soon)", color: "text-red-400", fields: [], configFields: [], disabled: true },
  { value: "cloud_storage", label: "Cloud Storage", description: "Batch export to S3/GCS/Azure Blob (coming soon)", color: "text-teal-400", fields: [], configFields: [], disabled: true },
];

interface Integration {
  id: string;
  name: string;
  integration_type: string;
  config: Record<string, any>;
  enabled: boolean;
  last_test_status: string | null;
  last_test_message: string | null;
  last_test_at: string | null;
  created_at: string;
}

function StatusDot({ status }: { status: string | null }) {
  if (status === "success") return <CheckCircle className="h-4 w-4 text-emerald-400" />;
  if (status === "failed") return <XCircle className="h-4 w-4 text-red-400" />;
  return <div className="h-3 w-3 rounded-full bg-gray-600" />;
}

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  // Create form state
  const [createType, setCreateType] = useState("");
  const [createName, setCreateName] = useState("");
  const [createConfig, setCreateConfig] = useState<Record<string, string>>({});
  const [createCreds, setCreateCreds] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  const fetchIntegrations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiRequest("/api/log-integrations");
      if (res.ok) {
        const data = await res.json();
        setIntegrations(data.items || []);
      }
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchIntegrations(); }, [fetchIntegrations]);

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const res = await apiRequest(`/api/log-integrations/${id}/test`, { method: "POST" });
      if (res.ok) {
        await fetchIntegrations();
      }
    } catch {} finally {
      setTesting(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this integration? This cannot be undone.")) return;
    setDeleting(id);
    try {
      await apiRequest(`/api/log-integrations/${id}`, { method: "DELETE" });
      await fetchIntegrations();
    } catch {} finally {
      setDeleting(null);
    }
  };

  const handleToggle = async (integration: Integration) => {
    try {
      await apiRequest(`/api/log-integrations/${integration.id}`, {
        method: "PUT",
        body: JSON.stringify({ enabled: !integration.enabled }),
      });
      await fetchIntegrations();
    } catch {}
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setCreateError("");
    try {
      const res = await apiRequest("/api/log-integrations", {
        method: "POST",
        body: JSON.stringify({
          name: createName,
          integration_type: createType,
          config: createConfig,
          credentials: createCreds,
        }),
      });
      if (res.ok) {
        setShowCreate(false);
        setCreateName("");
        setCreateType("");
        setCreateConfig({});
        setCreateCreds({});
        await fetchIntegrations();
      } else {
        const data = await res.json().catch(() => ({}));
        setCreateError(data.detail || "Failed to create integration");
      }
    } catch {
      setCreateError("Network error");
    } finally {
      setCreating(false);
    }
  };

  const selectedType = INTEGRATION_TYPES.find(t => t.value === createType);

  if (loading) return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Log Integrations"
        description="Connect platform logs to external observability tools"
        breadcrumbs={[
          { label: "Settings", href: "/settings" },
          { label: "Integrations" },
        ]}
        actions={
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Add Integration
          </motion.button>
        }
      />

      {/* Integration Cards */}
      {integrations.length === 0 && (
        <Card>
          <CardContent className="p-12 text-center">
            <Zap className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-lg font-medium">No integrations configured</p>
            <p className="text-sm text-muted-foreground mt-1">
              Connect your platform logs to Datadog, Splunk, CloudWatch, or any webhook endpoint.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {integrations.map((integration) => {
          const typeInfo = INTEGRATION_TYPES.find(t => t.value === integration.integration_type);
          return (
            <motion.div
              key={integration.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card className="hover:border-violet-500/15 transition-colors">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <StatusDot status={integration.last_test_status} />
                      <div>
                        <h3 className="font-medium">{integration.name}</h3>
                        <p className={`text-xs ${typeInfo?.color || "text-muted-foreground"}`}>
                          {typeInfo?.label || integration.integration_type}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleToggle(integration)}
                        className={`p-1.5 rounded-md transition-colors ${integration.enabled ? "text-emerald-400 hover:bg-emerald-500/15" : "text-muted-foreground hover:bg-accent"}`}
                        title={integration.enabled ? "Disable" : "Enable"}
                      >
                        {integration.enabled ? <Power className="h-4 w-4" /> : <PowerOff className="h-4 w-4" />}
                      </button>
                      <button
                        onClick={() => handleTest(integration.id)}
                        disabled={testing === integration.id}
                        className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                        title="Test connection"
                      >
                        {testing === integration.id ? <LoadingDots size="sm" /> : <Zap className="h-4 w-4" />}
                      </button>
                      <button
                        onClick={() => handleDelete(integration.id)}
                        disabled={deleting === integration.id}
                        className="p-1.5 rounded-md text-muted-foreground hover:text-red-400 hover:bg-red-500/15 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Config summary */}
                  {integration.config && Object.keys(integration.config).length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {Object.entries(integration.config).map(([k, v]) => (
                        <span key={k} className="text-xs bg-accent rounded px-1.5 py-0.5 text-muted-foreground">
                          {k}: {String(v).substring(0, 30)}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Last test */}
                  {integration.last_test_at && (
                    <p className={`text-xs mt-2 ${integration.last_test_status === "success" ? "text-emerald-400" : "text-red-400"}`}>
                      Last test: {integration.last_test_message || integration.last_test_status}
                    </p>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {/* Available Integration Types */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Available Integrations</h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          {INTEGRATION_TYPES.map((type) => (
            <Card key={type.value} className={type.disabled ? "opacity-50" : "hover:border-violet-500/15 transition-colors"}>
              <CardContent className="p-4">
                <h3 className={`font-medium ${type.color}`}>{type.label}</h3>
                <p className="text-xs text-muted-foreground mt-1">{type.description}</p>
                {type.disabled && <span className="text-xs text-muted-foreground mt-2 inline-block">Coming soon</span>}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Create Modal */}
      <AnimatePresence>
        {showCreate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm"
              onClick={() => setShowCreate(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative z-50 w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-xl max-h-[90vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Add Log Integration</h2>
                <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <form onSubmit={handleCreate} className="space-y-4">
                {/* Name */}
                <div>
                  <label className="text-sm font-medium">Name</label>
                  <input
                    type="text"
                    value={createName}
                    onChange={(e) => setCreateName(e.target.value)}
                    placeholder="My Datadog Integration"
                    required
                    className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  />
                </div>

                {/* Type */}
                <div>
                  <label className="text-sm font-medium">Type</label>
                  <div className="mt-1 grid grid-cols-2 gap-2">
                    {INTEGRATION_TYPES.filter(t => !t.disabled).map((type) => (
                      <button
                        key={type.value}
                        type="button"
                        onClick={() => { setCreateType(type.value); setCreateConfig({}); setCreateCreds({}); }}
                        className={`rounded-md border p-3 text-left text-sm transition-colors ${
                          createType === type.value
                            ? "border-violet-500 bg-violet-500/10"
                            : "border-border hover:border-violet-500/30"
                        }`}
                      >
                        <p className={`font-medium ${type.color}`}>{type.label}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">{type.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Dynamic fields */}
                {selectedType && (
                  <>
                    {/* Config fields */}
                    {selectedType.configFields.map((field) => (
                      <div key={field}>
                        <label className="text-sm font-medium capitalize">{field.replace(/_/g, " ")}</label>
                        <input
                          type="text"
                          value={createConfig[field] || ""}
                          onChange={(e) => setCreateConfig({ ...createConfig, [field]: e.target.value })}
                          placeholder={field}
                          className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                        />
                      </div>
                    ))}

                    {/* Credential fields */}
                    {selectedType.fields.map((field) => (
                      <div key={field}>
                        <label className="text-sm font-medium capitalize">{field.replace(/_/g, " ")} 🔒</label>
                        <input
                          type="password"
                          value={createCreds[field] || ""}
                          onChange={(e) => setCreateCreds({ ...createCreds, [field]: e.target.value })}
                          placeholder={`Enter ${field}`}
                          required
                          className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                        />
                      </div>
                    ))}
                  </>
                )}

                {createError && (
                  <p className="text-sm text-red-400">{createError}</p>
                )}

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreate(false)}
                    className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating || !createType || !createName}
                    className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors disabled:opacity-50"
                  >
                    {creating ? <LoadingDots size="sm" /> : "Create Integration"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
