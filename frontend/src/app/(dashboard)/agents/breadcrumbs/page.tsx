"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
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
  Panel,
  EdgeProps,
  getBezierPath,
  EdgeLabelRenderer,
  BaseEdge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import {
  Bot,
  Activity,
  MessageSquare,
  ChevronDown,
  Cpu,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { useAPI } from "@/lib/swr";
import { apiRequest } from "@/lib/auth";
import { cn } from "@/lib/utils";

import { BreadcrumbSummaryPanel } from "./BreadcrumbSummaryPanel";
import { BreadcrumbDetailPanel } from "./BreadcrumbDetailPanel";
import { BreadcrumbEdgePanel } from "./BreadcrumbEdgePanel";
import type { BreadcrumbNode, AgentMessage } from "./BreadcrumbSummaryPanel";

// ── Types ──────────────────────────────────────────────────────────

interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
}

interface InteractionCounts {
  total: number;
  invoke_agent: number;
  delegate_task: number;
}

interface BreadcrumbEdge {
  id: string;
  source: string;
  target: string;
  connection_type: "handoff" | "escalation" | "data_feed" | "trigger";
  label?: string | null;
  interactions: InteractionCounts;
}

interface BreadcrumbsData {
  project_id: string;
  date_from: string | null;
  date_to: string | null;
  nodes: BreadcrumbNode[];
  edges: BreadcrumbEdge[];
}

interface AgentMessageResponse {
  agent_id: string;
  project_id: string;
  total: number;
  limit: number;
  offset: number;
  messages: AgentMessage[];
}

// ── Panel state ───────────────────────────────────────────────────

type PanelView = "closed" | "summary" | "detail" | "edge";

// ── Color map ─────────────────────────────────────────────────────

const CONNECTION_COLORS: Record<string, string> = {
  handoff: "#06b6d4",
  escalation: "#ef4444",
  data_feed: "#10b981",
  trigger: "#f59e0b",
};

const CONNECTION_LABELS: Record<string, string> = {
  handoff: "Handoff",
  escalation: "Escalation",
  data_feed: "Data Feed",
  trigger: "Trigger",
};

// ── Date helpers ──────────────────────────────────────────────────

function formatDateInput(date: Date): string {
  return date.toISOString().split("T")[0];
}

function daysAgo(days: number): Date {
  const d = new Date();
  d.setDate(d.getDate() - days);
  d.setHours(0, 0, 0, 0);
  return d;
}

// ── Breadcrumb Agent Node ─────────────────────────────────────────

interface BreadcrumbNodeData extends BreadcrumbNode {
  run_count: number;
  [key: string]: unknown;
}

const BreadcrumbAgentNode = memo(
  ({ data, selected }: { data: BreadcrumbNodeData; selected?: boolean }) => {
    const statusDot = (status: string) => {
      const colors: Record<string, string> = {
        active: "bg-green-500 animate-pulse",
        paused: "bg-yellow-500",
        disabled: "bg-red-500",
      };
      return (
        <div
          className={`w-2 h-2 rounded-full ${colors[status] || "bg-gray-500"}`}
        />
      );
    };

    return (
      <div className="group">
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 !bg-cyan-500 !border-2 !border-cyan-400"
        />

        <Card
          className={cn(
            "w-72 bg-[#1a1a2e] border-2 transition-all duration-200 hover:shadow-lg hover:shadow-cyan-500/20 cursor-pointer",
            selected
              ? "border-cyan-500 shadow-lg shadow-cyan-500/30"
              : "border-gray-700 hover:border-cyan-500/50"
          )}
        >
          <CardContent className="p-4">
            {/* Header */}
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center space-x-2 flex-1 min-w-0">
                {statusDot(data.status)}
                <h3 className="font-semibold text-white text-sm truncate">
                  {data.name}
                </h3>
              </div>
              <Bot className="w-4 h-4 text-cyan-500 flex-shrink-0" />
            </div>

            {/* Model */}
            <div className="mb-3">
              <Badge
                variant="outline"
                className="text-xs bg-gray-500/10 text-gray-400 border-gray-500/30"
              >
                <Cpu className="w-3 h-3 mr-1" />
                {data.model_id}
              </Badge>
            </div>

            {/* Stats row */}
            <div className="flex items-center justify-between text-xs border-t border-gray-700 pt-2">
              <div className="flex items-center text-blue-400">
                <Activity className="w-3 h-3 mr-1" />
                {data.run_count} runs
              </div>
              <div className="flex items-center text-purple-400">
                <MessageSquare className="w-3 h-3 mr-1" />
                {data.message_count} msgs
              </div>
            </div>
          </CardContent>
        </Card>

        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 !bg-cyan-500 !border-2 !border-cyan-400"
        />
      </div>
    );
  }
);
BreadcrumbAgentNode.displayName = "BreadcrumbAgentNode";

// ── Custom Interaction Edge ───────────────────────────────────────

interface InteractionEdgeData {
  interaction_count: number;
  connection_type: string;
  breakdown?: Record<string, number>;
  [key: string]: unknown;
}

function InteractionEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
}: EdgeProps<Edge<InteractionEdgeData>>) {
  const [hovered, setHovered] = useState(false);

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  const color =
    CONNECTION_COLORS[data?.connection_type || "handoff"] || "#06b6d4";
  const count = data?.interaction_count ?? 0;
  const breakdown = data?.breakdown;

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        style={{
          ...style,
          stroke: color,
          strokeWidth: Math.min(2 + count * 0.3, 6),
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: "absolute",
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: "all",
            zIndex: hovered ? 1000 : 1,
          }}
          className="nodrag nopan"
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          {/* Badge */}
          <div
            className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium shadow-lg border border-gray-700 cursor-pointer hover:border-gray-500 transition-colors"
            style={{ backgroundColor: "#1a1a2e" }}
          >
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: color }}
            />
            <span className="text-white">{count}</span>
          </div>

          {/* Hover tooltip */}
          {hovered && breakdown && Object.keys(breakdown).length > 0 && (
            <div
              className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-44 rounded-lg border border-gray-700 bg-[#1a1a2e] p-2.5 shadow-xl"
              style={{ zIndex: 1000 }}
            >
              <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1.5">
                {CONNECTION_LABELS[data?.connection_type || "handoff"]}
              </div>
              {Object.entries(breakdown).map(([key, val]) =>
                val ? (
                  <div
                    key={key}
                    className="flex items-center justify-between text-xs py-0.5"
                  >
                    <span className="text-gray-300">
                      {key.replace(/_/g, " ")}
                    </span>
                    <span className="text-white font-medium">{val}</span>
                  </div>
                ) : null
              )}
              <div className="mt-2 pt-1.5 border-t border-gray-700 text-[10px] text-cyan-500">
                Click to view messages
              </div>
            </div>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

// ── Node / Edge type registries ───────────────────────────────────

const nodeTypes = {
  breadcrumbAgent: BreadcrumbAgentNode,
} as const satisfies Record<string, React.ComponentType<any>>;

const edgeTypes = {
  interaction: InteractionEdge,
} as const satisfies Record<string, React.ComponentType<any>>;

// ── Main page component ───────────────────────────────────────────

export default function BreadcrumbsPage() {
  // Project selector
  const { data: projects, isLoading: projectsLoading } =
    useAPI<Project[]>("/api/projects");

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
    null
  );
  const [projectDropdownOpen, setProjectDropdownOpen] = useState(false);

  // Date range — default last 7 days
  const [dateFrom, setDateFrom] = useState(() => formatDateInput(daysAgo(7)));
  const [dateTo, setDateTo] = useState(() => formatDateInput(new Date()));

  // Breadcrumbs data
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbsData | null>(null);
  const [breadcrumbsLoading, setBreadcrumbsLoading] = useState(false);

  // React Flow
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Panel state
  const [panelView, setPanelView] = useState<PanelView>("closed");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<{
    source: string;
    target: string;
    connectionType: string;
  } | null>(null);

  // Summary panel data
  const [summaryMessages, setSummaryMessages] = useState<AgentMessage[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryTotal, setSummaryTotal] = useState(0);

  // Auto-select first project when loaded
  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  // Fetch breadcrumbs when project or dates change
  useEffect(() => {
    if (!selectedProjectId) return;

    const fetchBreadcrumbs = async () => {
      setBreadcrumbsLoading(true);
      try {
        const params = new URLSearchParams({
          date_from: dateFrom,
          date_to: dateTo,
        });
        const res = await apiRequest(
          `/api/projects/${selectedProjectId}/breadcrumbs?${params}`
        );
        if (res.ok) {
          const data: BreadcrumbsData = await res.json();
          setBreadcrumbs(data);
          buildGraph(data);
        }
      } catch (err) {
        console.error("Failed to fetch breadcrumbs:", err);
      } finally {
        setBreadcrumbsLoading(false);
      }
    };

    fetchBreadcrumbs();
  }, [selectedProjectId, dateFrom, dateTo]);

  // Build React Flow graph from breadcrumbs data
  const buildGraph = useCallback(
    (data: BreadcrumbsData) => {
      const COLS = 3;
      const GAP_X = 340;
      const GAP_Y = 220;

      const flowNodes: Node[] = data.nodes.map((node, i) => ({
        id: node.id,
        type: "breadcrumbAgent",
        position: node.position || {
          x: 80 + (i % COLS) * GAP_X,
          y: 80 + Math.floor(i / COLS) * GAP_Y,
        },
        data: {
          ...node,
          run_count: node.total_runs,
        },
        draggable: true,
      }));

      const flowEdges: Edge[] = data.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: "interaction",
        animated: true,
        data: {
          interaction_count: edge.interactions.total,
          connection_type: edge.connection_type,
          breakdown: {
            invoke_agent: edge.interactions.invoke_agent,
            delegate_task: edge.interactions.delegate_task,
          },
        },
      }));

      setNodes(flowNodes);
      setEdges(flowEdges);
    },
    [setNodes, setEdges]
  );

  // Fetch summary messages (5 most recent)
  const fetchSummaryMessages = async (agentId: string) => {
    if (!selectedProjectId) return;
    setSummaryLoading(true);
    setSummaryMessages([]);
    setSummaryTotal(0);
    try {
      const params = new URLSearchParams({
        date_from: dateFrom,
        date_to: dateTo,
        limit: "5",
      });
      const res = await apiRequest(
        `/api/projects/${selectedProjectId}/breadcrumbs/agents/${agentId}/messages?${params}`
      );
      if (res.ok) {
        const data: AgentMessageResponse = await res.json();
        setSummaryMessages(data.messages);
        setSummaryTotal(data.total);
      }
    } catch (err) {
      console.error("Failed to fetch summary messages:", err);
    } finally {
      setSummaryLoading(false);
    }
  };

  // Node click — open summary panel
  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      setSelectedAgentId(node.id);
      setSelectedEdge(null);
      setPanelView("summary");
      fetchSummaryMessages(node.id);
    },
    [selectedProjectId, dateFrom, dateTo]
  );

  // Edge click — open edge panel
  const onEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: Edge) => {
      const connectionType =
        (edge.data as InteractionEdgeData)?.connection_type || "handoff";
      setSelectedEdge({
        source: edge.source,
        target: edge.target,
        connectionType,
      });
      setSelectedAgentId(null);
      setPanelView("edge");
    },
    []
  );

  // Close all panels
  const closePanel = () => {
    setPanelView("closed");
    setSelectedAgentId(null);
    setSelectedEdge(null);
    setSummaryMessages([]);
  };

  // Summary → Detail
  const expandToDetail = () => {
    setPanelView("detail");
  };

  // Detail → Summary
  const backToSummary = () => {
    setPanelView("summary");
    if (selectedAgentId) {
      fetchSummaryMessages(selectedAgentId);
    }
  };

  // Date change from detail panel
  const handleDateChange = (from: string, to: string) => {
    setDateFrom(from);
    setDateTo(to);
  };

  // Selected project name
  const selectedProject = useMemo(
    () => projects?.find((p) => p.id === selectedProjectId),
    [projects, selectedProjectId]
  );

  // Selected agent
  const selectedAgent = useMemo(
    () => breadcrumbs?.nodes.find((a) => a.id === selectedAgentId),
    [breadcrumbs, selectedAgentId]
  );

  // Source/target agents for edge panel
  const sourceAgent = useMemo(
    () =>
      selectedEdge
        ? breadcrumbs?.nodes.find((a) => a.id === selectedEdge.source)
        : undefined,
    [breadcrumbs, selectedEdge]
  );
  const targetAgent = useMemo(
    () =>
      selectedEdge
        ? breadcrumbs?.nodes.find((a) => a.id === selectedEdge.target)
        : undefined,
    [breadcrumbs, selectedEdge]
  );

  // ── Loading state ──

  if (projectsLoading) {
    return (
      <div className="space-y-6 p-6">
        <PageHeader
          title="Breadcrumbs"
          description="Visualize agent interactions across your projects"
          breadcrumbs={[
            { label: "Agents", href: "/agents" },
            { label: "Breadcrumbs" },
          ]}
        />
        <CardSkeleton count={3} />
      </div>
    );
  }

  // ── Empty state — no projects ──

  if (!projects || projects.length === 0) {
    return (
      <div className="space-y-6 p-6">
        <PageHeader
          title="Breadcrumbs"
          description="Visualize agent interactions across your projects"
          breadcrumbs={[
            { label: "Agents", href: "/agents" },
            { label: "Breadcrumbs" },
          ]}
        />
        <Card className="text-center py-12">
          <CardContent>
            <Bot className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h2 className="text-lg font-semibold mb-2">No Projects</h2>
            <p className="text-muted-foreground">
              Create a project with agents to see interaction breadcrumbs.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] lg:h-screen overflow-hidden">
      {/* ── Header / controls ── */}
      <div className="p-6 pb-4 space-y-4 flex-shrink-0">
        <PageHeader
          title="Breadcrumbs"
          description="Visualize agent interactions across your projects"
          breadcrumbs={[
            { label: "Agents", href: "/agents" },
            { label: "Breadcrumbs" },
          ]}
        />

        <div className="flex flex-wrap items-end gap-4">
          {/* Project selector */}
          <div className="relative">
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              Project
            </label>
            <button
              onClick={() => setProjectDropdownOpen(!projectDropdownOpen)}
              className="flex items-center justify-between w-64 rounded-md border border-gray-700 bg-[#1a1a2e] px-3 py-2 text-sm text-white hover:border-gray-500 transition-colors"
            >
              <span className="truncate">
                {selectedProject?.name || "Select project..."}
              </span>
              <ChevronDown className="h-4 w-4 text-gray-400 ml-2 flex-shrink-0" />
            </button>
            {projectDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setProjectDropdownOpen(false)}
                />
                <div className="absolute top-full left-0 mt-1 w-64 z-50 rounded-md border border-gray-700 bg-[#1a1a2e] shadow-xl py-1 max-h-60 overflow-y-auto">
                  {projects.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => {
                        setSelectedProjectId(p.id);
                        setProjectDropdownOpen(false);
                        closePanel();
                      }}
                      className={cn(
                        "w-full text-left px-3 py-2 text-sm transition-colors",
                        p.id === selectedProjectId
                          ? "bg-cyan-500/10 text-cyan-400"
                          : "text-gray-300 hover:bg-gray-800"
                      )}
                    >
                      {p.name}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Date from */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              From
            </label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-md border border-gray-700 bg-[#1a1a2e] px-3 py-2 text-sm text-white [color-scheme:dark]"
            />
          </div>

          {/* Date to */}
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1.5">
              To
            </label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-md border border-gray-700 bg-[#1a1a2e] px-3 py-2 text-sm text-white [color-scheme:dark]"
            />
          </div>
        </div>
      </div>

      {/* ── Canvas area ── */}
      <div className="flex-1 relative bg-[#0a0a1a]">
        {breadcrumbsLoading ? (
          <div className="flex items-center justify-center h-full">
            <Card className="w-80 p-6 bg-[#1a1a2e] border-gray-800">
              <CardContent className="flex items-center justify-center p-0">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500" />
                <span className="ml-3 text-white text-sm">
                  Loading breadcrumbs...
                </span>
              </CardContent>
            </Card>
          </div>
        ) : breadcrumbs && breadcrumbs.nodes.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <Card className="w-96 p-8 bg-[#1a1a2e]/90 border-gray-800 text-center">
              <CardContent className="p-0">
                <Activity className="mx-auto h-10 w-10 text-gray-500 mb-3" />
                <h3 className="text-white font-medium mb-1">
                  No activity in this period
                </h3>
                <p className="text-gray-400 text-sm">
                  Try expanding the date range or selecting a different project.
                </p>
              </CardContent>
            </Card>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            className="bg-[#0a0a1a]"
            nodesDraggable
            nodesConnectable={false}
            elementsSelectable
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color="#333"
            />

            <Controls className="!bg-[#1a1a2e] !border-gray-700 [&>button]:!bg-[#1a1a2e] [&>button]:!border-gray-700 [&>button]:!text-white" />

            <MiniMap
              className="!bg-[#1a1a2e] !border-gray-700"
              nodeColor="#06b6d4"
              maskColor="rgba(26, 26, 46, 0.8)"
            />

            {/* Legend */}
            <Panel
              position="bottom-left"
              className="bg-[#1a1a2e]/90 backdrop-blur-sm border border-gray-700 rounded-lg p-3"
            >
              <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">
                Connection Types
              </div>
              <div className="space-y-1.5 text-xs">
                {Object.entries(CONNECTION_COLORS).map(([type, color]) => (
                  <div key={type} className="flex items-center space-x-2">
                    <div
                      className="w-6 h-0.5 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    <span className="text-gray-300 capitalize">
                      {type.replace(/_/g, " ")}
                    </span>
                  </div>
                ))}
              </div>
            </Panel>
          </ReactFlow>
        )}

        {/* ── Summary Panel ── */}
        {selectedAgent && (
          <BreadcrumbSummaryPanel
            agent={selectedAgent}
            messages={summaryMessages}
            messagesLoading={summaryLoading}
            totalMessages={summaryTotal}
            open={panelView === "summary"}
            onClose={closePanel}
            onExpand={expandToDetail}
          />
        )}

        {/* ── Detail Panel ── */}
        {panelView === "detail" && selectedAgentId && breadcrumbs && selectedProjectId && (
          <BreadcrumbDetailPanel
            projectId={selectedProjectId}
            agents={breadcrumbs.nodes}
            initialAgentId={selectedAgentId}
            dateFrom={dateFrom}
            dateTo={dateTo}
            onDateChange={handleDateChange}
            onClose={closePanel}
            onBack={backToSummary}
          />
        )}

        {/* ── Edge Panel ── */}
        {panelView === "edge" &&
          selectedEdge &&
          sourceAgent &&
          targetAgent &&
          selectedProjectId && (
            <BreadcrumbEdgePanel
              projectId={selectedProjectId}
              sourceAgent={sourceAgent}
              targetAgent={targetAgent}
              connectionType={selectedEdge.connectionType}
              dateFrom={dateFrom}
              dateTo={dateTo}
              onClose={closePanel}
            />
          )}
      </div>
    </div>
  );
}
