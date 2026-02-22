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
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion, AnimatePresence } from "framer-motion";
import {
  Key,
  GitBranch,
  Box,
  Cloud,
  X,
  Loader2,
  Network,
  AlertCircle,
  Activity,
  DollarSign,
  Zap,
  Scale,
  ShieldAlert,
  FlaskConical,
} from "lucide-react";
import { apiRequest } from "@/lib/auth";

/* ─── Types ─── */

interface GatewayKey {
  id: string;
  name: string;
  key_prefix: string;
  team_id: string | null;
  rate_limit: number;
  created_at: string;
  revoked_at: string | null;
}

interface RoutingPolicy {
  id: string;
  name: string;
  description?: string;
  strategy: string;
  models: Array<{ model_id: string; weight?: number; role: string }>;
  rules: Record<string, any>;
  is_active: boolean;
  api_key_prefix: string;
  created_at: string;
}

interface ModelEntry {
  id: string;
  model_id: string;
  display_name: string;
  provider_id: string;
  provider_type?: string;
  status?: string;
  [key: string]: any;
}

interface Provider {
  id: string;
  provider_type: string;
  status: string;
  name: string;
  region: string;
  model_count: number;
}

/* ─── Strategy styling ─── */

const strategyMeta: Record<string, { icon: typeof Zap; label: string }> = {
  cost_optimized: { icon: DollarSign, label: "Cost" },
  latency_optimized: { icon: Zap, label: "Latency" },
  balanced: { icon: Scale, label: "Balanced" },
  failover: { icon: ShieldAlert, label: "Failover" },
  ab_test: { icon: FlaskConical, label: "A/B" },
};

/* ─── Custom Node Components ─── */

function ApiKeyNode({ data }: { data: any }) {
  return (
    <div className="group">
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-blue-400 !border-2 !border-blue-300" />
      <div className="w-56 rounded-xl border-2 border-blue-500/40 bg-[#0d1424] p-4 shadow-lg shadow-blue-500/10 transition-all hover:border-blue-400/60 hover:shadow-blue-500/20">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/15">
            <Key className="h-4 w-4 text-blue-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-blue-100 truncate">{data.name}</p>
            <p className="text-[10px] font-mono text-blue-400/70">{data.prefix}</p>
          </div>
        </div>
        <div className="flex items-center justify-between text-[10px] text-blue-300/60 mt-1">
          <span>{data.rateLimit} req/min</span>
          <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-medium ${data.active ? "bg-blue-500/20 text-blue-300" : "bg-red-500/20 text-red-300"}`}>
            {data.active ? "Active" : "Revoked"}
          </span>
        </div>
      </div>
    </div>
  );
}

function RoutingPolicyNode({ data }: { data: any }) {
  const meta = strategyMeta[data.strategy] || { icon: GitBranch, label: data.strategy };
  const StrategyIcon = meta.icon;
  return (
    <div className="group">
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-violet-400 !border-2 !border-violet-300" />
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-violet-400 !border-2 !border-violet-300" />
      <div className="w-56 rounded-xl border-2 border-violet-500/40 bg-[#140d24] p-4 shadow-lg shadow-violet-500/10 transition-all hover:border-violet-400/60 hover:shadow-violet-500/20">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-500/15">
            <GitBranch className="h-4 w-4 text-violet-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-violet-100 truncate">{data.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[10px] mt-1">
          <StrategyIcon className="h-3 w-3 text-violet-400/70" />
          <span className="text-violet-300/70">{meta.label}</span>
          <span className="text-violet-400/40 mx-1">·</span>
          <span className="text-violet-300/60">{data.modelCount} model{data.modelCount !== 1 ? "s" : ""}</span>
          <span className={`ml-auto px-1.5 py-0.5 rounded-full text-[9px] font-medium ${data.isActive ? "bg-violet-500/20 text-violet-300" : "bg-zinc-500/20 text-zinc-400"}`}>
            {data.isActive ? "Active" : "Inactive"}
          </span>
        </div>
      </div>
    </div>
  );
}

function ModelNode({ data }: { data: any }) {
  return (
    <div className="group">
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-emerald-400 !border-2 !border-emerald-300" />
      <Handle type="source" position={Position.Right} className="!w-2.5 !h-2.5 !bg-emerald-400 !border-2 !border-emerald-300" />
      <div className="w-56 rounded-xl border-2 border-emerald-500/40 bg-[#0d1a14] p-4 shadow-lg shadow-emerald-500/10 transition-all hover:border-emerald-400/60 hover:shadow-emerald-500/20">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15">
            <Box className="h-4 w-4 text-emerald-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-emerald-100 truncate">{data.displayName}</p>
            <p className="text-[10px] font-mono text-emerald-400/60 truncate">{data.modelId}</p>
          </div>
        </div>
        <div className="flex items-center justify-between text-[10px] mt-1">
          <span className="text-emerald-300/60">{data.providerType?.toUpperCase() || "—"}</span>
          <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-medium ${
            data.status === "active" ? "bg-emerald-500/20 text-emerald-300" :
            data.status === "deployed" ? "bg-emerald-500/20 text-emerald-300" :
            "bg-zinc-500/20 text-zinc-400"
          }`}>
            {data.status || "available"}
          </span>
        </div>
      </div>
    </div>
  );
}

function ProviderNode({ data }: { data: any }) {
  const providerEmoji: Record<string, string> = { aws: "☁️", azure: "🔷", gcp: "🔺" };
  return (
    <div className="group">
      <Handle type="target" position={Position.Left} className="!w-2.5 !h-2.5 !bg-amber-400 !border-2 !border-amber-300" />
      <div className="w-56 rounded-xl border-2 border-amber-500/40 bg-[#1a150d] p-4 shadow-lg shadow-amber-500/10 transition-all hover:border-amber-400/60 hover:shadow-amber-500/20">
        <div className="flex items-center gap-2.5 mb-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/15 text-lg">
            {providerEmoji[data.providerType] || "☁️"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-amber-100 truncate">{data.name}</p>
            <p className="text-[10px] text-amber-400/60">{data.region}</p>
          </div>
        </div>
        <div className="flex items-center justify-between text-[10px] mt-1">
          <span className="text-amber-300/60">{data.modelCount} model{data.modelCount !== 1 ? "s" : ""}</span>
          <span className={`flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-medium ${
            data.status === "active" || data.status === "healthy" ? "bg-emerald-500/20 text-emerald-300" :
            data.status === "degraded" ? "bg-yellow-500/20 text-yellow-300" :
            "bg-red-500/20 text-red-300"
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full ${
              data.status === "active" || data.status === "healthy" ? "bg-emerald-400 animate-pulse" :
              data.status === "degraded" ? "bg-yellow-400" :
              "bg-red-400"
            }`} />
            {data.status}
          </span>
        </div>
      </div>
    </div>
  );
}

const nodeTypes = {
  apiKey: ApiKeyNode,
  routingPolicy: RoutingPolicyNode,
  model: ModelNode,
  provider: ProviderNode,
} as const satisfies Record<string, React.ComponentType<any>>;

/* ─── Detail Panel ─── */

function DetailPanel({
  selectedNode,
  onClose,
}: {
  selectedNode: Node | null;
  onClose: () => void;
}) {
  if (!selectedNode) return null;

  const { type } = selectedNode;
  const data = selectedNode.data as Record<string, any>;
  const colors: Record<string, { border: string; bg: string; text: string; accent: string }> = {
    apiKey: { border: "border-blue-500/30", bg: "bg-blue-500/5", text: "text-blue-300", accent: "text-blue-400" },
    routingPolicy: { border: "border-violet-500/30", bg: "bg-violet-500/5", text: "text-violet-300", accent: "text-violet-400" },
    model: { border: "border-emerald-500/30", bg: "bg-emerald-500/5", text: "text-emerald-300", accent: "text-emerald-400" },
    provider: { border: "border-amber-500/30", bg: "bg-amber-500/5", text: "text-amber-300", accent: "text-amber-400" },
  };
  const c = colors[type || "apiKey"] || colors.apiKey;

  const typeLabels: Record<string, string> = {
    apiKey: "API Key",
    routingPolicy: "Routing Policy",
    model: "Model",
    provider: "Provider",
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20, scale: 0.95 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 20, scale: 0.95 }}
      transition={{ duration: 0.2 }}
      className={`absolute top-4 right-4 w-72 rounded-xl border ${c.border} ${c.bg} backdrop-blur-md p-4 shadow-2xl z-50`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className={`text-xs font-medium uppercase tracking-wider ${c.accent}`}>
          {typeLabels[type || ""] || type}
        </span>
        <button onClick={onClose} className="p-1 rounded-md hover:bg-white/10 transition-colors">
          <X className="h-3.5 w-3.5 text-zinc-400" />
        </button>
      </div>

      <h3 className="text-sm font-semibold text-zinc-100 mb-3">
        {data.name || data.displayName || data.modelId || "Unknown"}
      </h3>

      <div className="space-y-2 text-xs">
        {type === "apiKey" && (
          <>
            <Row label="Prefix" value={data.prefix} mono />
            <Row label="Rate Limit" value={`${data.rateLimit} req/min`} />
            <Row label="Status" value={data.active ? "Active" : "Revoked"} />
            <Row label="Created" value={new Date(data.createdAt).toLocaleDateString()} />
          </>
        )}
        {type === "routingPolicy" && (
          <>
            <Row label="Strategy" value={strategyMeta[data.strategy]?.label || data.strategy} />
            <Row label="Models" value={`${data.modelCount} configured`} />
            <Row label="Status" value={data.isActive ? "Active" : "Inactive"} />
            {data.description && <Row label="Description" value={data.description} />}
          </>
        )}
        {type === "model" && (
          <>
            <Row label="Model ID" value={data.modelId} mono />
            <Row label="Provider" value={data.providerType?.toUpperCase() || "—"} />
            <Row label="Status" value={data.status || "available"} />
          </>
        )}
        {type === "provider" && (
          <>
            <Row label="Type" value={data.providerType?.toUpperCase()} />
            <Row label="Region" value={data.region} />
            <Row label="Models" value={`${data.modelCount} deployed`} />
            <Row label="Status" value={data.status} />
          </>
        )}
      </div>
    </motion.div>
  );
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-2">
      <span className="text-zinc-500 shrink-0">{label}</span>
      <span className={`text-zinc-300 text-right truncate ${mono ? "font-mono" : ""}`}>{value}</span>
    </div>
  );
}

/* ─── Layout Helper ─── */

function buildGraph(
  keys: GatewayKey[],
  policies: RoutingPolicy[],
  models: ModelEntry[],
  providers: Provider[]
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const COL_X = [0, 320, 640, 960]; // left-to-right column positions
  const ROW_GAP = 140;
  const COL_OFFSET_Y = 40;

  // Build a lookup: model_id → ModelEntry
  const modelMap = new Map<string, ModelEntry>();
  models.forEach((m) => {
    modelMap.set(m.model_id, m);
    modelMap.set(m.id, m);
  });

  // Build a lookup: provider_id → Provider
  const providerMap = new Map<string, Provider>();
  providers.forEach((p) => providerMap.set(p.id, p));

  // Track which models & providers are connected (to add unconnected ones later)
  const connectedModelIds = new Set<string>();
  const connectedProviderIds = new Set<string>();

  // ─── Column 0: API Keys
  const activeKeys = keys.filter((k) => !k.revoked_at);
  activeKeys.forEach((key, i) => {
    nodes.push({
      id: `key-${key.id}`,
      type: "apiKey",
      position: { x: COL_X[0], y: COL_OFFSET_Y + i * ROW_GAP },
      data: {
        name: key.name,
        prefix: key.key_prefix,
        rateLimit: key.rate_limit,
        active: !key.revoked_at,
        createdAt: key.created_at,
      },
      draggable: true,
    });
  });

  // ─── Column 1: Routing Policies
  policies.forEach((policy, i) => {
    nodes.push({
      id: `policy-${policy.id}`,
      type: "routingPolicy",
      position: { x: COL_X[1], y: COL_OFFSET_Y + i * ROW_GAP },
      data: {
        name: policy.name,
        strategy: policy.strategy,
        modelCount: policy.models.length,
        isActive: policy.is_active,
        description: policy.description,
      },
      draggable: true,
    });

    // Edge: every active key → every active policy
    activeKeys.forEach((key) => {
      edges.push({
        id: `e-key-${key.id}-policy-${policy.id}`,
        source: `key-${key.id}`,
        target: `policy-${policy.id}`,
        type: "smoothstep",
        animated: true,
        style: { stroke: "#6366f1", strokeWidth: 1.5, opacity: 0.5 },
      });
    });

    // Edge: policy → each of its models
    policy.models.forEach((pm) => {
      const model = modelMap.get(pm.model_id);
      if (model) {
        connectedModelIds.add(model.id);
        edges.push({
          id: `e-policy-${policy.id}-model-${model.id}`,
          source: `policy-${policy.id}`,
          target: `model-${model.id}`,
          type: "smoothstep",
          animated: false,
          style: { stroke: "#7c3aed", strokeWidth: 1.5, opacity: 0.6 },
        });
      }
    });
  });

  // ─── Column 2: Models
  // Include all models (connected or not) — place connected ones first
  const sortedModels = [...models].sort((a, b) => {
    const aConnected = connectedModelIds.has(a.id) ? 0 : 1;
    const bConnected = connectedModelIds.has(b.id) ? 0 : 1;
    return aConnected - bConnected;
  });

  sortedModels.forEach((model, i) => {
    nodes.push({
      id: `model-${model.id}`,
      type: "model",
      position: { x: COL_X[2], y: COL_OFFSET_Y + i * ROW_GAP },
      data: {
        displayName: model.display_name || model.model_id,
        modelId: model.model_id,
        providerType: model.provider_type,
        status: model.status,
        providerId: model.provider_id,
      },
      draggable: true,
    });

    // Edge: model → provider
    if (model.provider_id && providerMap.has(model.provider_id)) {
      connectedProviderIds.add(model.provider_id);
      edges.push({
        id: `e-model-${model.id}-provider-${model.provider_id}`,
        source: `model-${model.id}`,
        target: `provider-${model.provider_id}`,
        type: "smoothstep",
        animated: false,
        style: { stroke: "#f59e0b", strokeWidth: 1.5, opacity: 0.4 },
      });
    }
  });

  // ─── Column 3: Providers
  providers.forEach((provider, i) => {
    nodes.push({
      id: `provider-${provider.id}`,
      type: "provider",
      position: { x: COL_X[3], y: COL_OFFSET_Y + i * ROW_GAP },
      data: {
        name: provider.name,
        providerType: provider.provider_type,
        region: provider.region,
        modelCount: provider.model_count,
        status: provider.status,
      },
      draggable: true,
    });
  });

  // If no policies but there are keys and models, connect keys directly to models
  if (policies.length === 0 && activeKeys.length > 0 && models.length > 0) {
    activeKeys.forEach((key) => {
      models.forEach((model) => {
        edges.push({
          id: `e-key-${key.id}-model-${model.id}`,
          source: `key-${key.id}`,
          target: `model-${model.id}`,
          type: "smoothstep",
          animated: true,
          style: { stroke: "#6366f1", strokeWidth: 1, opacity: 0.3 },
        });
      });
    });
  }

  return { nodes, edges };
}

/* ─── Loading Skeleton ─── */

function TopologySkeleton() {
  return (
    <div className="h-full flex items-center justify-center bg-[#0a0a0a]">
      <div className="flex flex-col items-center gap-4">
        <div className="relative">
          <Network className="h-10 w-10 text-violet-500/50" />
          <Loader2 className="h-5 w-5 text-violet-400 absolute -top-1 -right-1 animate-spin" />
        </div>
        <div className="space-y-2 text-center">
          <p className="text-sm text-zinc-400">Building network topology…</p>
          <div className="flex items-center gap-3">
            {[0, 1, 2, 3].map((i) => (
              <motion.div
                key={i}
                className="h-2 w-12 rounded-full bg-zinc-800"
                animate={{ opacity: [0.3, 0.7, 0.3] }}
                transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─── Empty State ─── */

function EmptyState() {
  return (
    <div className="h-full flex items-center justify-center bg-[#0a0a0a]">
      <div className="flex flex-col items-center gap-4 text-center max-w-sm">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-zinc-800/50 border border-zinc-700/50">
          <Network className="h-8 w-8 text-zinc-500" />
        </div>
        <div>
          <h3 className="text-base font-semibold text-zinc-300 mb-1">No topology to display</h3>
          <p className="text-sm text-zinc-500">
            Connect a cloud provider, configure routing policies, and create API keys to see your network topology here.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ─── Main Component ─── */

export function NetworkTopology() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  // Raw data
  const [keys, setKeys] = useState<GatewayKey[]>([]);
  const [policies, setPolicies] = useState<RoutingPolicy[]>([]);
  const [models, setModels] = useState<ModelEntry[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [keysRes, policiesRes, modelsRes, providersRes] = await Promise.allSettled([
        apiRequest("/api/gateway/keys"),
        apiRequest("/api/routing-policies"),
        apiRequest("/api/models/"),
        apiRequest("/api/providers/"),
      ]);

      const keysOk = keysRes.status === "fulfilled" && keysRes.value.ok;
      const policiesOk = policiesRes.status === "fulfilled" && policiesRes.value.ok;
      const modelsOk = modelsRes.status === "fulfilled" && modelsRes.value.ok;
      const providersOk = providersRes.status === "fulfilled" && providersRes.value.ok;

      const keysData: GatewayKey[] = keysOk ? await keysRes.value.json() : [];
      const policiesData: RoutingPolicy[] = policiesOk ? await policiesRes.value.json() : [];
      const allModels: ModelEntry[] = modelsOk ? await modelsRes.value.json() : [];
      const providersData: Provider[] = providersOk ? await providersRes.value.json() : [];

      // Collect model IDs referenced by routing policies
      const policyModelIds = new Set<string>();
      policiesData.forEach((p) => p.models.forEach((m) => policyModelIds.add(m.model_id)));

      // Include: (1) models in routing policies, (2) up to 4 per provider as representatives
      const perProviderCount = new Map<string, number>();
      let modelsData = allModels.filter((m) => {
        // Always include models referenced by policies
        if (policyModelIds.has(m.model_id) || policyModelIds.has(m.id)) return true;
        // Include a few representative models per provider
        const pid = m.provider_id || "unknown";
        const count = perProviderCount.get(pid) || 0;
        if (count < 4) {
          perProviderCount.set(pid, count + 1);
          return true;
        }
        return false;
      });

      setKeys(keysData);
      setPolicies(policiesData);
      setModels(modelsData);
      setProviders(providersData);

      const graph = buildGraph(keysData, policiesData, modelsData, providersData);
      setNodes(graph.nodes);
      setEdges(graph.edges);
    } catch (err) {
      console.error("Failed to fetch topology data:", err);
      setError("Failed to load network data. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const isEmpty = !loading && nodes.length === 0;

  if (loading) return <TopologySkeleton />;
  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-[#0a0a0a]">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertCircle className="h-8 w-8 text-red-400/60" />
          <p className="text-sm text-red-300">{error}</p>
          <button
            onClick={fetchAll}
            className="text-xs text-violet-400 hover:text-violet-300 underline transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  if (isEmpty) return <EmptyState />;

  return (
    <div className="h-full w-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        className="bg-[#0a0a0a]"
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
        maxZoom={1.5}
        defaultEdgeOptions={{
          type: "smoothstep",
        }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="#1a1a1a"
        />

        <Controls
          className="!bg-[#141414] !border-zinc-800 !rounded-xl [&>button]:!bg-[#141414] [&>button]:!border-zinc-800 [&>button]:!text-zinc-400 [&>button:hover]:!bg-zinc-800 [&>button:hover]:!text-zinc-200"
          showInteractive={false}
        />

        <MiniMap
          className="!bg-[#141414] !border-zinc-800 !rounded-xl"
          nodeColor={(node) => {
            switch (node.type) {
              case "apiKey": return "#3b82f6";
              case "routingPolicy": return "#7c3aed";
              case "model": return "#10b981";
              case "provider": return "#f59e0b";
              default: return "#555";
            }
          }}
          maskColor="rgba(10, 10, 10, 0.85)"
          pannable
          zoomable
        />

        {/* Legend */}
        <Panel position="bottom-left">
          <div className="bg-[#141414]/90 backdrop-blur-md border border-zinc-800 rounded-xl p-3 shadow-xl">
            <p className="text-[10px] font-medium text-zinc-500 uppercase tracking-wider mb-2">Flow</p>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-sm bg-blue-500" />
                <span className="text-zinc-400">API Keys</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-sm bg-violet-500" />
                <span className="text-zinc-400">Routing</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-sm bg-emerald-500" />
                <span className="text-zinc-400">Models</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-sm bg-amber-500" />
                <span className="text-zinc-400">Providers</span>
              </div>
            </div>
          </div>
        </Panel>

        {/* Stats */}
        <Panel position="top-right">
          <div className="bg-[#141414]/90 backdrop-blur-md border border-zinc-800 rounded-xl p-3 shadow-xl">
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <Key className="h-3 w-3 text-blue-400" />
                <span className="text-zinc-400">{keys.filter(k => !k.revoked_at).length}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <GitBranch className="h-3 w-3 text-violet-400" />
                <span className="text-zinc-400">{policies.length}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Box className="h-3 w-3 text-emerald-400" />
                <span className="text-zinc-400">{models.length}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Cloud className="h-3 w-3 text-amber-400" />
                <span className="text-zinc-400">{providers.length}</span>
              </div>
            </div>
          </div>
        </Panel>
      </ReactFlow>

      {/* Detail Panel */}
      <AnimatePresence>
        {selectedNode && (
          <DetailPanel
            selectedNode={selectedNode}
            onClose={() => setSelectedNode(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
