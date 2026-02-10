"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  GitBranch,
  DollarSign,
  Zap,
  Scale,
  ShieldAlert,
  Plus,
  Trash2,
  Play,
  GripVertical,
  ChevronRight,
  TrendingDown,
  Clock,
  BarChart3,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { apiRequest } from "@/lib/auth";

const strategies = [
  { id: "cost-optimized", name: "Cost Optimized", icon: DollarSign, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20", desc: "Route to cheapest provider" },
  { id: "latency-optimized", name: "Low Latency", icon: Zap, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20", desc: "Route to fastest provider" },
  { id: "balanced", name: "Balanced", icon: Scale, color: "text-violet-400", bg: "bg-violet-500/10", border: "border-violet-500/20", desc: "Optimize cost & speed" },
  { id: "failover", name: "Failover", icon: ShieldAlert, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20", desc: "Primary with auto-fallback" },
];

interface Rule {
  id: string;
  name: string;
  strategy: string;
  conditions_json: Record<string, unknown>;
  priority: number;
  enabled: boolean;
  created_at: string;
}

interface SimResult {
  selected_provider: string;
  selected_model: string;
  strategy_used: string;
  decision_path: string[];
  options: { provider: string; model: string; estimated_latency_ms: number; cost_per_1k_tokens: number; region: string; selected: boolean; reason: string }[];
  estimated_cost_savings_pct: number;
  estimated_latency_ms: number;
}

interface Analytics {
  total_requests: number;
  requests_by_provider: Record<string, number>;
  cost_savings_pct: number;
  avg_latency_ms: number;
  latency_by_provider: Record<string, number>;
  routing_distribution: Record<string, number>;
}

export default function RoutingPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [simResult, setSimResult] = useState<SimResult | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [simPrompt, setSimPrompt] = useState("");
  const [showNewRule, setShowNewRule] = useState(false);
  const [newRuleName, setNewRuleName] = useState("");
  const [newRuleStrategy, setNewRuleStrategy] = useState("balanced");
  const [activeTab, setActiveTab] = useState<"rules" | "simulate" | "analytics">("rules");

  useEffect(() => {
    apiRequest("/api/routing/rules").then(r => r.json()).then(setRules).catch(() => {});
    apiRequest("/api/routing/analytics").then(r => r.json()).then(setAnalytics).catch(() => {});
  }, []);

  const createRule = async () => {
    if (!newRuleName) return;
    const res = await apiRequest("/api/routing/rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newRuleName, strategy: newRuleStrategy, priority: rules.length }),
    });
    if (res.ok) {
      const rule = await res.json();
      setRules([...rules, rule]);
      setNewRuleName("");
      setShowNewRule(false);
    }
  };

  const deleteRule = async (id: string) => {
    await apiRequest(`/api/routing/rules/${id}`, { method: "DELETE" });
    setRules(rules.filter(r => r.id !== id));
  };

  const runSimulation = async () => {
    if (!simPrompt) return;
    setSimulating(true);
    setSimResult(null);
    try {
      const res = await apiRequest("/api/routing/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt_description: simPrompt, model_type: "chat" }),
      });
      if (res.ok) {
        // Artificial delay for animation
        await new Promise(r => setTimeout(r, 1500));
        setSimResult(await res.json());
      }
    } finally {
      setSimulating(false);
    }
  };

  const tabs = [
    { id: "rules" as const, label: "Rules" },
    { id: "simulate" as const, label: "Simulate" },
    { id: "analytics" as const, label: "Analytics" },
  ];

  const providerColors: Record<string, string> = {
    aws_bedrock: "bg-amber-500",
    azure_openai: "bg-blue-500",
    gcp_vertex: "bg-emerald-500",
  };

  const providerNames: Record<string, string> = {
    aws_bedrock: "AWS Bedrock",
    azure_openai: "Azure OpenAI",
    gcp_vertex: "GCP Vertex AI",
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Model Routing</h1>
          <p className="text-muted-foreground mt-1">Intelligent cross-cloud model routing & optimization</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-secondary/50 p-1 w-fit">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              activeTab === tab.id ? "text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {activeTab === tab.id && (
              <motion.div
                layoutId="routing-tab"
                className="absolute inset-0 rounded-md bg-background shadow-sm"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative">{tab.label}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* RULES TAB */}
        {activeTab === "rules" && (
          <motion.div
            key="rules"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            {/* Strategy Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {strategies.map((s, i) => (
                <motion.div
                  key={s.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <Card className={`${s.bg} border ${s.border} hover:scale-[1.02] transition-transform cursor-pointer`}>
                    <CardContent className="p-4">
                      <div className="flex items-center gap-3">
                        <s.icon className={`h-5 w-5 ${s.color}`} />
                        <div>
                          <p className="font-semibold text-sm">{s.name}</p>
                          <p className="text-xs text-muted-foreground">{s.desc}</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>

            {/* Rules List */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <GitBranch className="h-5 w-5 text-violet-500" />
                  Routing Rules
                </CardTitle>
                <button
                  onClick={() => setShowNewRule(true)}
                  className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  Add Rule
                </button>
              </CardHeader>
              <CardContent>
                <AnimatePresence>
                  {showNewRule && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mb-4 overflow-hidden"
                    >
                      <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 p-4 space-y-3">
                        <input
                          type="text"
                          placeholder="Rule name..."
                          value={newRuleName}
                          onChange={e => setNewRuleName(e.target.value)}
                          className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                        />
                        <div className="flex gap-2 flex-wrap">
                          {strategies.map(s => (
                            <button
                              key={s.id}
                              onClick={() => setNewRuleStrategy(s.id)}
                              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium border transition-all ${
                                newRuleStrategy === s.id
                                  ? `${s.bg} ${s.border} ${s.color}`
                                  : "border-border text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              <s.icon className="h-3 w-3" />
                              {s.name}
                            </button>
                          ))}
                        </div>
                        <div className="flex gap-2">
                          <button onClick={createRule} className="rounded-md bg-violet-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors">
                            Create
                          </button>
                          <button onClick={() => setShowNewRule(false)} className="rounded-md border border-border px-3 py-1.5 text-sm font-medium hover:bg-accent transition-colors">
                            Cancel
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {rules.length === 0 ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="text-center py-12"
                  >
                    <GitBranch className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
                    <p className="text-lg font-medium text-muted-foreground">No routing rules yet</p>
                    <p className="text-sm text-muted-foreground/70 mt-1">Let AI traffic flow freely... or take control 🎛️</p>
                  </motion.div>
                ) : (
                  <div className="space-y-2">
                    {rules.map((rule, i) => {
                      const strat = strategies.find(s => s.id === rule.strategy);
                      return (
                        <motion.div
                          key={rule.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className="flex items-center gap-3 rounded-lg border border-border p-4 hover:border-violet-500/30 transition-colors group"
                        >
                          <GripVertical className="h-4 w-4 text-muted-foreground/40 cursor-grab" />
                          <span className="text-xs text-muted-foreground font-mono w-6">#{rule.priority}</span>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm">{rule.name}</p>
                            <div className="flex items-center gap-2 mt-1">
                              {strat && (
                                <Badge variant="secondary" className={`${strat.bg} ${strat.color} border-0 text-xs`}>
                                  <strat.icon className="h-3 w-3 mr-1" />
                                  {strat.name}
                                </Badge>
                              )}
                            </div>
                          </div>
                          <div className={`h-2 w-2 rounded-full ${rule.enabled ? "bg-emerald-500" : "bg-secondary"}`} />
                          <button
                            onClick={() => deleteRule(rule.id)}
                            className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-red-400 transition-all"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </motion.div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* SIMULATE TAB */}
        {activeTab === "simulate" && (
          <motion.div
            key="simulate"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Play className="h-5 w-5 text-violet-500" />
                  Route Simulation
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-3">
                  <input
                    type="text"
                    placeholder="Describe your request (e.g. 'Summarize a 10-page document')"
                    value={simPrompt}
                    onChange={e => setSimPrompt(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && runSimulation()}
                    className="flex-1 rounded-md border border-border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                  />
                  <button
                    onClick={runSimulation}
                    disabled={simulating || !simPrompt}
                    className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-violet-700 transition-colors disabled:opacity-50"
                  >
                    {simulating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
                    Simulate
                  </button>
                </div>

                <AnimatePresence>
                  {simulating && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="flex items-center justify-center py-12"
                    >
                      <div className="text-center">
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                          className="mx-auto mb-4"
                        >
                          <GitBranch className="h-8 w-8 text-violet-500" />
                        </motion.div>
                        <p className="text-sm text-muted-foreground">Evaluating routes across providers...</p>
                      </div>
                    </motion.div>
                  )}

                  {simResult && !simulating && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-4"
                    >
                      {/* Decision Path */}
                      <div className="rounded-lg border border-border p-4">
                        <p className="text-sm font-medium mb-3">Decision Path</p>
                        <div className="space-y-2">
                          {simResult.decision_path.map((step, i) => (
                            <motion.div
                              key={i}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: i * 0.15 }}
                              className="flex items-center gap-2 text-sm"
                            >
                              <ChevronRight className="h-3 w-3 text-violet-500 flex-shrink-0" />
                              <span className={i === simResult.decision_path.length - 1 ? "text-violet-400 font-medium" : "text-muted-foreground"}>
                                {step}
                              </span>
                            </motion.div>
                          ))}
                        </div>
                      </div>

                      {/* Provider Comparison */}
                      <div className="grid gap-2">
                        {simResult.options.map((opt, i) => (
                          <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.5 + i * 0.08 }}
                            className={`flex items-center gap-4 rounded-lg border p-3 ${
                              opt.selected ? "border-violet-500/50 bg-violet-500/5" : "border-border"
                            }`}
                          >
                            <div className={`h-2 w-2 rounded-full ${providerColors[opt.provider] || "bg-secondary"}`} />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium">
                                {providerNames[opt.provider] || opt.provider}
                                <span className="text-muted-foreground font-normal ml-2">{opt.model}</span>
                              </p>
                              <p className="text-xs text-muted-foreground">{opt.region}</p>
                            </div>
                            <div className="text-right text-xs space-y-0.5">
                              <p><Clock className="h-3 w-3 inline mr-1" />{opt.estimated_latency_ms}ms</p>
                              <p><DollarSign className="h-3 w-3 inline mr-0.5" />{opt.cost_per_1k_tokens}/1k</p>
                            </div>
                            {opt.selected ? (
                              <Badge variant="success" className="text-xs">Selected</Badge>
                            ) : (
                              <span className="text-xs text-muted-foreground max-w-[140px] truncate">{opt.reason}</span>
                            )}
                          </motion.div>
                        ))}
                      </div>

                      {/* Savings */}
                      <div className="flex gap-4">
                        <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 p-3 flex-1 text-center">
                          <p className="text-2xl font-bold text-emerald-400">{simResult.estimated_cost_savings_pct}%</p>
                          <p className="text-xs text-muted-foreground">Cost Savings</p>
                        </div>
                        <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-3 flex-1 text-center">
                          <p className="text-2xl font-bold text-amber-400">{simResult.estimated_latency_ms}ms</p>
                          <p className="text-xs text-muted-foreground">Estimated Latency</p>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* ANALYTICS TAB */}
        {activeTab === "analytics" && analytics && (
          <motion.div
            key="analytics"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="space-y-6"
          >
            {/* Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0 }}>
                <Card>
                  <CardContent className="p-6 text-center">
                    <BarChart3 className="h-5 w-5 text-violet-500 mx-auto mb-2" />
                    <p className="text-3xl font-bold">{analytics.total_requests.toLocaleString()}</p>
                    <p className="text-sm text-muted-foreground">Total Requests Routed</p>
                  </CardContent>
                </Card>
              </motion.div>
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
                <Card className="bg-emerald-500/5 border-emerald-500/20">
                  <CardContent className="p-6 text-center">
                    <TrendingDown className="h-5 w-5 text-emerald-400 mx-auto mb-2" />
                    <p className="text-3xl font-bold text-emerald-400">{analytics.cost_savings_pct}%</p>
                    <p className="text-sm text-muted-foreground">Cost Savings</p>
                  </CardContent>
                </Card>
              </motion.div>
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                <Card>
                  <CardContent className="p-6 text-center">
                    <Clock className="h-5 w-5 text-amber-400 mx-auto mb-2" />
                    <p className="text-3xl font-bold">{analytics.avg_latency_ms}ms</p>
                    <p className="text-sm text-muted-foreground">Avg Latency</p>
                  </CardContent>
                </Card>
              </motion.div>
            </div>

            {/* Distribution */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Routing Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(analytics.requests_by_provider).map(([provider, count], i) => {
                      const total = analytics.total_requests;
                      const pct = Math.round((count / total) * 100);
                      return (
                        <motion.div
                          key={provider}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.1 }}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <div className={`h-2.5 w-2.5 rounded-full ${providerColors[provider] || "bg-secondary"}`} />
                              <span className="text-sm font-medium">{providerNames[provider] || provider}</span>
                            </div>
                            <span className="text-sm text-muted-foreground">{count.toLocaleString()} ({pct}%)</span>
                          </div>
                          <div className="h-2 rounded-full bg-secondary overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${pct}%` }}
                              transition={{ duration: 0.8, delay: 0.2 + i * 0.1 }}
                              className={`h-full rounded-full ${providerColors[provider] || "bg-violet-500"}`}
                            />
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Latency by Provider</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {Object.entries(analytics.latency_by_provider).map(([provider, latency], i) => {
                      const maxLatency = Math.max(...Object.values(analytics.latency_by_provider));
                      const pct = Math.round((latency / maxLatency) * 100);
                      return (
                        <motion.div
                          key={provider}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.1 }}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <div className={`h-2.5 w-2.5 rounded-full ${providerColors[provider] || "bg-secondary"}`} />
                              <span className="text-sm font-medium">{providerNames[provider] || provider}</span>
                            </div>
                            <span className="text-sm text-muted-foreground">{latency}ms</span>
                          </div>
                          <div className="h-2 rounded-full bg-secondary overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${pct}%` }}
                              transition={{ duration: 0.8, delay: 0.2 + i * 0.1 }}
                              className={`h-full rounded-full ${providerColors[provider] || "bg-violet-500"}`}
                            />
                          </div>
                        </motion.div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Strategy Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Strategy Usage</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(analytics.routing_distribution).map(([strategy, pct], i) => {
                    const strat = strategies.find(s => s.id === strategy);
                    return (
                      <motion.div
                        key={strategy}
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: i * 0.08 }}
                        className={`rounded-lg border p-4 text-center ${strat?.bg || ""} ${strat?.border || "border-border"}`}
                      >
                        {strat && <strat.icon className={`h-5 w-5 mx-auto mb-2 ${strat.color}`} />}
                        <p className="text-2xl font-bold">{pct}%</p>
                        <p className="text-xs text-muted-foreground">{strat?.name || strategy}</p>
                      </motion.div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
