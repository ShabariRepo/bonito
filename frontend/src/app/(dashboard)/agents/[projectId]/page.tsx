"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Plus, ArrowLeft, Settings, Play, Zap, Users, Loader2, Clock, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";
import { AgentNode } from "@/components/agents/agent-node";
import { TriggerNode } from "@/components/agents/trigger-node";
import { AgentDetailPanel } from "@/components/agents/agent-detail-panel";
import { GroupManagementPanel } from "@/components/agents/group-management-panel";

interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  budget_monthly: number | null;
  budget_spent: number;
  created_at: string;
}

interface GraphData {
  project_id: string;
  nodes: Array<{
    id: string;
    type: string;
    data: any;
    position?: { x: number; y: number };
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type: string;
    data: any;
  }>;
}

// Custom node types for React Flow
const nodeTypes = {
  agent: AgentNode,
  trigger: TriggerNode,
} as const satisfies Record<string, React.ComponentType<any>>;

export default function ProjectCanvasPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params?.projectId as string;
  const { toast } = useToast();

  const [project, setProject] = useState<Project | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);
  const [detailPanelOpen, setDetailPanelOpen] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [groupPanelOpen, setGroupPanelOpen] = useState(false);

  // Create Agent modal state
  const [createAgentOpen, setCreateAgentOpen] = useState(false);
  const [creatingAgent, setCreatingAgent] = useState(false);
  const [agentForm, setAgentForm] = useState({
    name: "",
    description: "",
    system_prompt: "",
    model_id: "auto",
    tool_policy_mode: "all",
  });

  // Create Trigger modal state
  const [createTriggerOpen, setCreateTriggerOpen] = useState(false);
  const [creatingTrigger, setCreatingTrigger] = useState(false);
  const [triggerForm, setTriggerForm] = useState({
    agent_id: "",
    trigger_type: "webhook",
    cron_expression: "",
    event_type: "",
  });

  useEffect(() => {
    if (projectId) {
      fetchProjectData();
      fetchGraphData();
    }
  }, [projectId]);

  const fetchProjectData = async () => {
    try {
      const res = await apiRequest(`/api/projects/${projectId}`);
      if (res.ok) {
        const data = await res.json();
        setProject(data);
      }
    } catch (error) {
      console.error("Failed to fetch project:", error);
      toast({
        title: "Error",
        description: "Failed to load project",
        variant: "destructive",
      });
    }
  };

  const fetchGraphData = async () => {
    try {
      const res = await apiRequest(`/api/projects/${projectId}/graph`);
      if (!res.ok) return;
      const data: GraphData = await res.json();
      
      // Convert graph data to React Flow format
      const flowNodes: Node[] = data.nodes.map((node, index) => ({
        id: node.id,
        type: node.type,
        position: node.position || { x: 100 + (index % 4) * 300, y: 100 + Math.floor(index / 4) * 200 },
        data: node.data,
        draggable: true,
      }));

      const flowEdges: Edge[] = data.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: "smoothstep",
        animated: true,
        style: { stroke: "#06b6d4", strokeWidth: 2 },
        label: edge.data.label,
        labelStyle: { fill: "#06b6d4", fontWeight: 500 },
        labelBgStyle: { fill: "#1a1a2e", fillOpacity: 0.8 },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    } catch (error) {
      console.error("Failed to fetch graph data:", error);
      toast({
        title: "Error",
        description: "Failed to load agent graph",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const onConnect = useCallback(
    (params: Connection) => {
      // TODO: Create connection via API
      setEdges((eds) => addEdge(params, eds));
    },
    [setEdges]
  );

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.type === "agent") {
      setSelectedAgentId(node.id);
      setDetailPanelOpen(true);
    }
  }, []);

  const handleCreateAgent = () => {
    setAgentForm({ name: "", description: "", system_prompt: "", model_id: "auto", tool_policy_mode: "all" });
    setCreateAgentOpen(true);
  };

  const submitCreateAgent = async () => {
    if (!agentForm.name.trim() || !agentForm.system_prompt.trim()) {
      toast({ title: "Missing fields", description: "Name and system prompt are required.", variant: "destructive" });
      return;
    }
    setCreatingAgent(true);
    try {
      const body: Record<string, any> = {
        name: agentForm.name.trim(),
        system_prompt: agentForm.system_prompt.trim(),
        model_id: agentForm.model_id || "auto",
        tool_policy: { mode: agentForm.tool_policy_mode },
      };
      if (agentForm.description.trim()) body.description = agentForm.description.trim();
      const res = await apiRequest(`/api/projects/${projectId}/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || "Failed to create agent");
      }
      toast({ title: "Agent Created", description: `${agentForm.name} has been added to the canvas.` });
      setCreateAgentOpen(false);
      fetchGraphData();
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setCreatingAgent(false);
    }
  };

  const handleCreateTrigger = () => {
    setTriggerForm({ agent_id: "", trigger_type: "webhook", cron_expression: "", event_type: "" });
    setCreateTriggerOpen(true);
  };

  const submitCreateTrigger = async () => {
    if (!triggerForm.agent_id) {
      toast({ title: "Missing agent", description: "Please select an agent for this trigger.", variant: "destructive" });
      return;
    }
    setCreatingTrigger(true);
    try {
      const config: Record<string, any> = {};
      if (triggerForm.trigger_type === "schedule" && triggerForm.cron_expression.trim()) {
        config.cron = triggerForm.cron_expression.trim();
      } else if (triggerForm.trigger_type === "event" && triggerForm.event_type.trim()) {
        config.event_type = triggerForm.event_type.trim();
      }
      const res = await apiRequest(`/api/agents/${triggerForm.agent_id}/triggers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          trigger_type: triggerForm.trigger_type,
          config,
          enabled: true,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail || "Failed to create trigger");
      }
      toast({ title: "Trigger Created", description: `${triggerForm.trigger_type} trigger added.` });
      setCreateTriggerOpen(false);
      fetchGraphData();
    } catch (err: any) {
      toast({ title: "Error", description: err.message, variant: "destructive" });
    } finally {
      setCreatingTrigger(false);
    }
  };

  // Derive agent list from current nodes for the trigger modal
  const agentNodes = nodes.filter((n) => n.type === "agent");

  if (loading) {
    return (
      <div className="h-[calc(100vh-4rem)] lg:h-screen bg-[#0a0a1a] flex items-center justify-center">
        <Card className="w-96 p-6 bg-[#1a1a2e] border-gray-800">
          <CardContent className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-white">Loading agent canvas...</span>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-4rem)] lg:h-screen bg-[#0a0a1a] text-white relative overflow-hidden">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 bg-[#1a1a2e]/90 backdrop-blur-sm border-b border-gray-800 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => router.back()}
              className="text-gray-400 hover:text-white"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            {project && (
              <div>
                <h1 className="text-xl font-bold text-white">{project.name}</h1>
                {project.description && (
                  <p className="text-sm text-gray-400">{project.description}</p>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setGroupPanelOpen(true)}
              className="bg-[#2a2a4e] border-gray-600 text-white hover:bg-[#3a3a6e]"
            >
              <Users className="h-4 w-4 mr-2" />
              Manage Groups
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCreateTrigger}
              className="bg-[#2a2a4e] border-gray-600 text-white hover:bg-[#3a3a6e]"
            >
              <Zap className="h-4 w-4 mr-2" />
              Add Trigger
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleCreateAgent}
              className="bg-[#2a2a4e] border-gray-600 text-white hover:bg-[#3a3a6e]"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Agent
            </Button>
          </div>
        </div>
      </div>

      {/* React Flow Canvas */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes}
        fitView
        className="bg-[#0a0a1a]"
        style={{ marginTop: "80px" }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#333"
        />
        
        <Controls
          className="!bg-[#1a1a2e] !border-gray-700 [&>button]:!bg-[#1a1a2e] [&>button]:!border-gray-700 [&>button]:!text-white"
        />
        
        <MiniMap
          className="!bg-[#1a1a2e] !border-gray-700"
          nodeColor="#06b6d4"
          maskColor="rgba(26, 26, 46, 0.8)"
        />

        {/* Legend */}
        <Panel position="bottom-left" className="bg-[#1a1a2e]/90 backdrop-blur-sm border border-gray-700 rounded-lg p-3">
          <div className="space-y-2 text-xs">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded bg-blue-500"></div>
              <span>Agent</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 rounded bg-yellow-500"></div>
              <span>Trigger</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-0.5 bg-cyan-500"></div>
              <span>Connection</span>
            </div>
          </div>
        </Panel>
      </ReactFlow>

      {/* Agent Detail Panel */}
      <AgentDetailPanel
        isOpen={detailPanelOpen}
        onClose={() => {
          setDetailPanelOpen(false);
          setSelectedAgentId(null);
        }}
        agentId={selectedAgentId}
        onAgentUpdate={fetchGraphData}
      />

      {/* Group Management Panel */}
      <GroupManagementPanel
        isOpen={groupPanelOpen}
        onClose={() => setGroupPanelOpen(false)}
        projectId={projectId}
        onGroupChange={fetchGraphData}
      />

      {/* Empty State */}
      {nodes.length === 0 && !loading && (
        <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
          <Card className="w-96 p-8 bg-[#1a1a2e]/90 backdrop-blur-sm border-gray-800 text-center">
            <CardHeader>
              <CardTitle className="text-white">No Agents Yet</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-400 mb-6">
                Create your first agent to start building your AI workflow.
              </p>
              <Button
                onClick={handleCreateAgent}
                className="pointer-events-auto bg-blue-600 hover:bg-blue-700"
              >
                <Plus className="h-4 w-4 mr-2" />
                Create Agent
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* ─── Create Agent Modal ─── */}
      <Dialog open={createAgentOpen} onOpenChange={setCreateAgentOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Agent</DialogTitle>
            <DialogDescription>Add a new AI agent to this project.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            <div className="space-y-2">
              <Label htmlFor="agent-name">
                Name <span className="text-red-400">*</span>
              </Label>
              <Input
                id="agent-name"
                placeholder="e.g. Customer Support Agent"
                value={agentForm.name}
                onChange={(e) => setAgentForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="agent-desc">Description</Label>
              <Input
                id="agent-desc"
                placeholder="Brief description of what this agent does"
                value={agentForm.description}
                onChange={(e) => setAgentForm((f) => ({ ...f, description: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="agent-prompt">
                System Prompt <span className="text-red-400">*</span>
              </Label>
              <Textarea
                id="agent-prompt"
                placeholder="You are a helpful assistant that..."
                rows={5}
                value={agentForm.system_prompt}
                onChange={(e) => setAgentForm((f) => ({ ...f, system_prompt: e.target.value }))}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="agent-model">Model</Label>
              <Input
                id="agent-model"
                placeholder="auto"
                value={agentForm.model_id}
                onChange={(e) => setAgentForm((f) => ({ ...f, model_id: e.target.value }))}
              />
              <p className="text-xs text-muted-foreground">
                Use &quot;auto&quot; for smart routing, or specify a model like &quot;gpt-4o&quot; or &quot;claude-3.5-sonnet&quot;.
              </p>
            </div>

            <div className="space-y-2">
              <Label>Tool Policy</Label>
              <div className="grid grid-cols-3 gap-2">
                {([
                  { value: "all", label: "Allow All" },
                  { value: "none", label: "No Tools" },
                  { value: "selected", label: "Selected" },
                ] as const).map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setAgentForm((f) => ({ ...f, tool_policy_mode: opt.value }))}
                    className={cn(
                      "rounded-lg border px-3 py-2 text-sm font-medium transition-all",
                      agentForm.tool_policy_mode === opt.value
                        ? "border-violet-500 bg-violet-500/10 text-white"
                        : "border-gray-700 text-gray-400 hover:border-gray-500"
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setCreateAgentOpen(false)}>
                Cancel
              </Button>
              <Button onClick={submitCreateAgent} disabled={creatingAgent}>
                {creatingAgent ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creating...</>
                ) : (
                  <><Plus className="h-4 w-4 mr-2" /> Create Agent</>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* ─── Create Trigger Modal ─── */}
      <Dialog open={createTriggerOpen} onOpenChange={setCreateTriggerOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Add Trigger</DialogTitle>
            <DialogDescription>Create a trigger to invoke an agent automatically.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-2">
            {/* Agent selector */}
            <div className="space-y-2">
              <Label>
                Agent <span className="text-red-400">*</span>
              </Label>
              {agentNodes.length === 0 ? (
                <p className="text-sm text-yellow-400 bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-3 py-2">
                  No agents in this project yet. Create an agent first.
                </p>
              ) : (
                <div className="grid gap-2">
                  {agentNodes.map((node) => (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => setTriggerForm((f) => ({ ...f, agent_id: node.id }))}
                      className={cn(
                        "flex items-center gap-3 rounded-lg border px-3 py-2 text-sm text-left transition-all",
                        triggerForm.agent_id === node.id
                          ? "border-violet-500 bg-violet-500/10 text-white"
                          : "border-gray-700 text-gray-400 hover:border-gray-500"
                      )}
                    >
                      <div className="h-2 w-2 rounded-full bg-blue-500 shrink-0" />
                      {String(node.data?.name || node.id)}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Trigger type */}
            <div className="space-y-2">
              <Label>Trigger Type</Label>
              <div className="grid grid-cols-3 gap-2">
                {([
                  { value: "webhook", label: "Webhook", icon: Globe },
                  { value: "schedule", label: "Schedule", icon: Clock },
                  { value: "event", label: "Event", icon: Zap },
                ] as const).map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setTriggerForm((f) => ({ ...f, trigger_type: opt.value }))}
                    className={cn(
                      "flex flex-col items-center gap-1.5 rounded-lg border px-3 py-3 text-sm font-medium transition-all",
                      triggerForm.trigger_type === opt.value
                        ? "border-violet-500 bg-violet-500/10 text-white"
                        : "border-gray-700 text-gray-400 hover:border-gray-500"
                    )}
                  >
                    <opt.icon className="h-4 w-4" />
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Type-specific fields */}
            {triggerForm.trigger_type === "webhook" && (
              <div className="rounded-lg border border-gray-700 bg-zinc-950/50 p-3 space-y-1">
                <p className="text-sm text-gray-300">A unique webhook URL will be generated when you create this trigger.</p>
                <p className="text-xs text-muted-foreground">Send a POST request to invoke the agent.</p>
              </div>
            )}

            {triggerForm.trigger_type === "schedule" && (
              <div className="space-y-2">
                <Label htmlFor="trigger-cron">Cron Expression</Label>
                <Input
                  id="trigger-cron"
                  placeholder="0 9 * * 1-5"
                  value={triggerForm.cron_expression}
                  onChange={(e) => setTriggerForm((f) => ({ ...f, cron_expression: e.target.value }))}
                />
                <p className="text-xs text-muted-foreground">
                  Examples: <code className="bg-zinc-800 px-1 rounded">0 9 * * *</code> (daily 9am),{" "}
                  <code className="bg-zinc-800 px-1 rounded">*/15 * * * *</code> (every 15 min)
                </p>
              </div>
            )}

            {triggerForm.trigger_type === "event" && (
              <div className="space-y-2">
                <Label htmlFor="trigger-event">Event Type</Label>
                <Input
                  id="trigger-event"
                  placeholder="e.g. ticket.created, order.completed"
                  value={triggerForm.event_type}
                  onChange={(e) => setTriggerForm((f) => ({ ...f, event_type: e.target.value }))}
                />
                <p className="text-xs text-muted-foreground">
                  The agent will run whenever this event is emitted.
                </p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={() => setCreateTriggerOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={submitCreateTrigger}
                disabled={creatingTrigger || agentNodes.length === 0}
              >
                {creatingTrigger ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Creating...</>
                ) : (
                  <><Zap className="h-4 w-4 mr-2" /> Create Trigger</>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}