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
import { Plus, ArrowLeft, Settings, Play, Zap, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
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
    // TODO: Open create agent modal
    toast({
      title: "Coming Soon",
      description: "Agent creation modal will be implemented",
    });
  };

  const handleCreateTrigger = () => {
    // TODO: Open create trigger modal
    toast({
      title: "Coming Soon", 
      description: "Trigger creation modal will be implemented",
    });
  };

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
    </div>
  );
}