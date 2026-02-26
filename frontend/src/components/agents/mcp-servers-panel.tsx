"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus,
  Server,
  Trash2,
  RefreshCw,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  Loader2,
  Zap,
  Cloud,
  Terminal,
  Globe,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { useToast } from "@/components/ui/use-toast";
import { apiRequest } from "@/lib/auth";

interface MCPServer {
  id: string;
  agent_id: string;
  name: string;
  transport_type: "stdio" | "http";
  endpoint_config: Record<string, any>;
  auth_config: { type: string; configured?: boolean; header?: string };
  enabled: boolean;
  discovered_tools?: Array<{
    name: string;
    description: string;
    input_schema?: Record<string, any>;
  }>;
  last_connected_at?: string;
  created_at: string;
  updated_at: string;
}

interface MCPTemplate {
  id: string;
  name: string;
  description: string;
  transport_type: string;
  endpoint_config: Record<string, any>;
  auth_config: Record<string, any>;
  category: string;
}

interface MCPServersPanelProps {
  agentId: string;
}

export function MCPServersPanel({ agentId }: MCPServersPanelProps) {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [templates, setTemplates] = useState<MCPTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [testingServerId, setTestingServerId] = useState<string | null>(null);
  const { toast } = useToast();

  // Add form state
  const [formName, setFormName] = useState("");
  const [formTransport, setFormTransport] = useState<"stdio" | "http">("stdio");
  const [formCommand, setFormCommand] = useState("");
  const [formArgs, setFormArgs] = useState("");
  const [formEnv, setFormEnv] = useState("");
  const [formUrl, setFormUrl] = useState("");
  const [formAuthType, setFormAuthType] = useState("none");
  const [formAuthToken, setFormAuthToken] = useState("");
  const [formTemplateId, setFormTemplateId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchServers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiRequest(`/api/agents/${agentId}/mcp-servers`);
      if (res.ok) {
        setServers(await res.json());
      }
    } catch (error) {
      console.error("Failed to fetch MCP servers:", error);
    } finally {
      setLoading(false);
    }
  }, [agentId]);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await apiRequest("/api/mcp-templates");
      if (res.ok) {
        setTemplates(await res.json());
      }
    } catch (error) {
      console.error("Failed to fetch MCP templates:", error);
    }
  }, []);

  useEffect(() => {
    fetchServers();
    fetchTemplates();
  }, [fetchServers, fetchTemplates]);

  const resetForm = () => {
    setFormName("");
    setFormTransport("stdio");
    setFormCommand("");
    setFormArgs("");
    setFormEnv("");
    setFormUrl("");
    setFormAuthType("none");
    setFormAuthToken("");
    setFormTemplateId("");
  };

  const handleTemplateSelect = (templateId: string) => {
    setFormTemplateId(templateId);
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setFormName(template.name);
      setFormTransport(template.transport_type as "stdio" | "http");
      if (template.transport_type === "stdio") {
        setFormCommand(template.endpoint_config.command || "");
        setFormArgs((template.endpoint_config.args || []).join(" "));
        setFormEnv(
          Object.entries(template.endpoint_config.env || {})
            .map(([k, v]) => `${k}=${v}`)
            .join("\n")
        );
      } else {
        setFormUrl(template.endpoint_config.url || "");
      }
      setFormAuthType(template.auth_config.type || "none");
    }
  };

  const handleAddServer = async () => {
    if (!formName.trim()) {
      toast({ title: "Error", description: "Name is required", variant: "destructive" });
      return;
    }

    setSubmitting(true);
    try {
      const endpointConfig: Record<string, any> = {};
      if (formTransport === "stdio") {
        endpointConfig.command = formCommand;
        endpointConfig.args = formArgs.split(/\s+/).filter(Boolean);
        if (formEnv.trim()) {
          endpointConfig.env = Object.fromEntries(
            formEnv
              .split("\n")
              .filter((l) => l.includes("="))
              .map((l) => {
                const idx = l.indexOf("=");
                return [l.slice(0, idx), l.slice(idx + 1)];
              })
          );
        }
      } else {
        endpointConfig.url = formUrl;
      }

      const authConfig: Record<string, any> = { type: formAuthType };
      if (formAuthType === "bearer_token") {
        authConfig.token = formAuthToken;
      } else if (formAuthType === "api_key") {
        authConfig.key = formAuthToken;
        authConfig.header = "X-API-Key";
      }

      const body: Record<string, any> = {
        name: formName,
        transport_type: formTransport,
        endpoint_config: endpointConfig,
        auth_config: authConfig,
        enabled: true,
      };
      if (formTemplateId) {
        body.template_id = formTemplateId;
      }

      const res = await apiRequest(`/api/agents/${agentId}/mcp-servers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to add MCP server");
      }

      toast({ title: "MCP Server Added", description: `${formName} registered successfully` });
      setShowAddDialog(false);
      resetForm();
      await fetchServers();
    } catch (error: any) {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteServer = async (serverId: string, serverName: string) => {
    try {
      const res = await apiRequest(`/api/agents/${agentId}/mcp-servers/${serverId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        toast({ title: "Removed", description: `${serverName} removed` });
        await fetchServers();
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to remove server", variant: "destructive" });
    }
  };

  const handleToggleServer = async (server: MCPServer) => {
    try {
      const res = await apiRequest(`/api/agents/${agentId}/mcp-servers/${server.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !server.enabled }),
      });
      if (res.ok) {
        await fetchServers();
      }
    } catch (error) {
      toast({ title: "Error", description: "Failed to toggle server", variant: "destructive" });
    }
  };

  const handleTestServer = async (serverId: string) => {
    setTestingServerId(serverId);
    try {
      const res = await apiRequest(`/api/agents/${agentId}/mcp-servers/${serverId}/test`, {
        method: "POST",
      });
      if (res.ok) {
        const result = await res.json();
        if (result.status === "connected") {
          toast({
            title: "Connection Successful",
            description: `Discovered ${result.tools_discovered} tools (${result.latency_ms}ms)`,
          });
          await fetchServers();
        } else {
          toast({
            title: "Connection Failed",
            description: result.error || "Unknown error",
            variant: "destructive",
          });
        }
      }
    } catch (error) {
      toast({ title: "Error", description: "Test failed", variant: "destructive" });
    } finally {
      setTestingServerId(null);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "aws":
        return <Cloud className="w-4 h-4 text-orange-400" />;
      case "gcp":
        return <Cloud className="w-4 h-4 text-blue-400" />;
      case "azure":
        return <Cloud className="w-4 h-4 text-cyan-400" />;
      default:
        return <Server className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">MCP Servers</h3>
          <p className="text-sm text-gray-400">
            Connect external tools via Model Context Protocol
          </p>
        </div>
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button size="sm" className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              Add MCP Server
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-[#1a1a2e] border-gray-700 text-white max-w-2xl max-h-[85vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add MCP Server</DialogTitle>
              <DialogDescription className="text-gray-400">
                Connect to an MCP server to give this agent access to external tools.
              </DialogDescription>
            </DialogHeader>

            {/* Template Picker */}
            {templates.length > 0 && (
              <div className="space-y-2">
                <Label>Quick Start — Cloud Templates</Label>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                  {templates.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => handleTemplateSelect(template.id)}
                      className={`p-3 rounded-lg border text-left transition-colors ${
                        formTemplateId === template.id
                          ? "border-blue-500 bg-blue-500/10"
                          : "border-gray-700 bg-[#2a2a4e] hover:border-gray-500"
                      }`}
                    >
                      <div className="flex items-center space-x-2 mb-1">
                        {getCategoryIcon(template.category)}
                        <span className="text-sm font-medium">{template.name}</span>
                      </div>
                      <p className="text-xs text-gray-400 line-clamp-2">{template.description}</p>
                    </button>
                  ))}
                </div>
                <div className="relative py-2">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-gray-700" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-[#1a1a2e] px-2 text-gray-500">or configure manually</span>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <Label>Name</Label>
                <Input
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder="e.g., AWS S3, GitHub, Custom API"
                  className="bg-[#2a2a4e] border-gray-600 text-white"
                />
              </div>

              <div>
                <Label>Transport Type</Label>
                <Select
                  value={formTransport}
                  onValueChange={(v) => setFormTransport(v as "stdio" | "http")}
                >
                  <SelectTrigger className="bg-[#2a2a4e] border-gray-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#2a2a4e] border-gray-600 text-white">
                    <SelectItem value="stdio">
                      <div className="flex items-center space-x-2">
                        <Terminal className="w-4 h-4" />
                        <span>stdio (Local Process)</span>
                      </div>
                    </SelectItem>
                    <SelectItem value="http">
                      <div className="flex items-center space-x-2">
                        <Globe className="w-4 h-4" />
                        <span>HTTP / SSE (Remote)</span>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {formTransport === "stdio" ? (
                <>
                  <div>
                    <Label>Command</Label>
                    <Input
                      value={formCommand}
                      onChange={(e) => setFormCommand(e.target.value)}
                      placeholder="e.g., npx, python, node"
                      className="bg-[#2a2a4e] border-gray-600 text-white"
                    />
                  </div>
                  <div>
                    <Label>Arguments (space-separated)</Label>
                    <Input
                      value={formArgs}
                      onChange={(e) => setFormArgs(e.target.value)}
                      placeholder="e.g., -y @aws/mcp-server-s3"
                      className="bg-[#2a2a4e] border-gray-600 text-white"
                    />
                  </div>
                  <div>
                    <Label>Environment Variables (KEY=VALUE, one per line)</Label>
                    <Textarea
                      value={formEnv}
                      onChange={(e) => setFormEnv(e.target.value)}
                      placeholder={"AWS_REGION=us-east-1\nAWS_PROFILE=default"}
                      className="bg-[#2a2a4e] border-gray-600 text-white min-h-[80px]"
                    />
                  </div>
                </>
              ) : (
                <div>
                  <Label>Endpoint URL</Label>
                  <Input
                    value={formUrl}
                    onChange={(e) => setFormUrl(e.target.value)}
                    placeholder="https://mcp-server.example.com/sse"
                    className="bg-[#2a2a4e] border-gray-600 text-white"
                  />
                </div>
              )}

              <div>
                <Label>Authentication</Label>
                <Select value={formAuthType} onValueChange={setFormAuthType}>
                  <SelectTrigger className="bg-[#2a2a4e] border-gray-600 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#2a2a4e] border-gray-600 text-white">
                    <SelectItem value="none">No Authentication</SelectItem>
                    <SelectItem value="bearer_token">Bearer Token</SelectItem>
                    <SelectItem value="api_key">API Key</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {formAuthType !== "none" && (
                <div>
                  <Label>
                    {formAuthType === "bearer_token" ? "Bearer Token" : "API Key"}
                  </Label>
                  <Input
                    type="password"
                    value={formAuthToken}
                    onChange={(e) => setFormAuthToken(e.target.value)}
                    placeholder={
                      formAuthType === "bearer_token"
                        ? "Enter bearer token..."
                        : "Enter API key..."
                    }
                    className="bg-[#2a2a4e] border-gray-600 text-white"
                  />
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                variant="ghost"
                onClick={() => {
                  setShowAddDialog(false);
                  resetForm();
                }}
              >
                Cancel
              </Button>
              <Button
                onClick={handleAddServer}
                disabled={submitting}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4 mr-2" />
                )}
                Add Server
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Server List */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : servers.length === 0 ? (
        <Card className="bg-[#2a2a4e] border-gray-700 border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Server className="w-12 h-12 text-gray-500 mb-4" />
            <h4 className="text-white font-medium mb-2">No MCP Servers Connected</h4>
            <p className="text-sm text-gray-400 text-center max-w-md mb-4">
              Connect MCP servers to give this agent access to external tools like AWS S3,
              GitHub, databases, and more.
            </p>
            <Button
              size="sm"
              className="bg-blue-600 hover:bg-blue-700"
              onClick={() => setShowAddDialog(true)}
            >
              <Plus className="w-4 h-4 mr-2" />
              Add First MCP Server
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {servers.map((server) => (
            <Card key={server.id} className="bg-[#2a2a4e] border-gray-700">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div
                      className={`p-2 rounded-lg ${
                        server.enabled ? "bg-green-500/10" : "bg-gray-500/10"
                      }`}
                    >
                      {server.transport_type === "stdio" ? (
                        <Terminal
                          className={`w-5 h-5 ${
                            server.enabled ? "text-green-400" : "text-gray-400"
                          }`}
                        />
                      ) : (
                        <Globe
                          className={`w-5 h-5 ${
                            server.enabled ? "text-green-400" : "text-gray-400"
                          }`}
                        />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h4 className="text-white font-medium">{server.name}</h4>
                        <Badge
                          variant="outline"
                          className={
                            server.enabled
                              ? "bg-green-500/10 text-green-400 border-green-500/30"
                              : "bg-gray-500/10 text-gray-400 border-gray-500/30"
                          }
                        >
                          {server.enabled ? "Active" : "Disabled"}
                        </Badge>
                        <Badge variant="outline" className="bg-blue-500/10 text-blue-400 border-blue-500/30">
                          {server.transport_type}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        {server.transport_type === "stdio"
                          ? `${server.endpoint_config.command} ${(server.endpoint_config.args || []).join(" ")}`
                          : server.endpoint_config.url}
                      </p>
                      {server.discovered_tools && server.discovered_tools.length > 0 && (
                        <p className="text-xs text-gray-500 mt-1">
                          <Zap className="w-3 h-3 inline mr-1" />
                          {server.discovered_tools.length} tools discovered
                          {server.last_connected_at &&
                            ` • Last connected ${new Date(server.last_connected_at).toLocaleString()}`}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Switch
                      checked={server.enabled}
                      onCheckedChange={() => handleToggleServer(server)}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTestServer(server.id)}
                      disabled={testingServerId === server.id}
                    >
                      {testingServerId === server.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-400 hover:text-red-300"
                      onClick={() => handleDeleteServer(server.id, server.name)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>

                {/* Discovered Tools (Expandable) */}
                {server.discovered_tools && server.discovered_tools.length > 0 && (
                  <Accordion type="single" collapsible className="mt-3">
                    <AccordionItem value="tools" className="border-gray-700">
                      <AccordionTrigger className="text-sm text-gray-300 hover:text-white py-2">
                        <div className="flex items-center space-x-2">
                          <Zap className="w-4 h-4" />
                          <span>
                            {server.discovered_tools.length} Available Tools
                          </span>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-2 pl-6">
                          {server.discovered_tools.map((tool, idx) => (
                            <div
                              key={idx}
                              className="p-2 rounded bg-[#1a1a2e] border border-gray-700"
                            >
                              <div className="flex items-center space-x-2">
                                <code className="text-xs text-blue-400 font-mono">
                                  {tool.name}
                                </code>
                              </div>
                              {tool.description && (
                                <p className="text-xs text-gray-400 mt-1">
                                  {tool.description}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
