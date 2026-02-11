"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  GitBranch,
  DollarSign,
  Zap,
  Scale,
  ShieldAlert,
  FlaskConical,
  Plus,
  Settings,
  Copy,
  Eye,
  Power,
  PowerOff,
  BarChart3,
  Users,
  Clock,
  TrendingUp,
  Trash2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { apiRequest } from "@/lib/auth";
import Link from "next/link";
import { useToast } from "@/hooks/use-toast";

const strategies = [
  { id: "cost_optimized", name: "Cost Optimized", icon: DollarSign, color: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
  { id: "latency_optimized", name: "Latency Optimized", icon: Zap, color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/20" },
  { id: "balanced", name: "Balanced", icon: Scale, color: "text-violet-400", bg: "bg-violet-500/10", border: "border-violet-500/20" },
  { id: "failover", name: "Failover", icon: ShieldAlert, color: "text-blue-400", bg: "bg-blue-500/10", border: "border-blue-500/20" },
  { id: "ab_test", name: "A/B Test", icon: FlaskConical, color: "text-pink-400", bg: "bg-pink-500/10", border: "border-pink-500/20" },
];

interface RoutingPolicy {
  id: string;
  name: string;
  description?: string;
  strategy: string;
  models: Array<{
    model_id: string;
    weight?: number;
    role: string;
  }>;
  rules: {
    max_cost_per_request?: number;
    max_tokens?: number;
    allowed_capabilities?: string[];
    region_preference?: string;
  };
  is_active: boolean;
  api_key_prefix: string;
  created_at: string;
}

interface PolicyStats {
  request_count: number;
  total_cost: number;
  avg_latency_ms: number;
  success_rate: number;
}

export default function RoutingPoliciesPage() {
  const [policies, setPolicies] = useState<RoutingPolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [statsCache, setStatsCache] = useState<Record<string, PolicyStats>>({});
  const { toast } = useToast();

  useEffect(() => {
    fetchPolicies();
  }, []);

  const fetchPolicies = async () => {
    try {
      const response = await apiRequest("/api/routing-policies");
      if (response.ok) {
        const data = await response.json();
        setPolicies(data);
        
        // Fetch stats for each policy
        data.forEach(async (policy: RoutingPolicy) => {
          try {
            const statsResponse = await apiRequest(`/api/routing-policies/${policy.id}/stats`);
            if (statsResponse.ok) {
              const stats = await statsResponse.json();
              setStatsCache(prev => ({ ...prev, [policy.id]: stats }));
            }
          } catch (error) {
            // Silently fail stats loading
          }
        });
      }
    } catch (error) {
      console.error("Failed to fetch routing policies:", error);
      toast({
        title: "Error",
        description: "Failed to load routing policies",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const togglePolicyStatus = async (policyId: string, isActive: boolean) => {
    try {
      const response = await apiRequest(`/api/routing-policies/${policyId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_active: isActive }),
      });
      
      if (response.ok) {
        setPolicies(prev => 
          prev.map(policy => 
            policy.id === policyId ? { ...policy, is_active: isActive } : policy
          )
        );
        toast({
          title: "Success",
          description: `Policy ${isActive ? "activated" : "deactivated"}`,
        });
      } else {
        throw new Error("Failed to update policy");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to update policy status",
        variant: "destructive",
      });
    }
  };

  const copyApiEndpoint = (apiKeyPrefix: string) => {
    const endpoint = `https://api.bonito.ai/v1/chat/completions`;
    const curlCommand = `curl -X POST ${endpoint} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${apiKeyPrefix}" \\
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "model": "any-model-name"
  }'`;
    
    navigator.clipboard.writeText(curlCommand);
    toast({
      title: "Copied!",
      description: "API endpoint copied to clipboard",
    });
  };

  const deletePolicy = async (policyId: string) => {
    if (!confirm("Are you sure you want to delete this policy? This cannot be undone.")) {
      return;
    }

    try {
      const response = await apiRequest(`/api/routing-policies/${policyId}`, {
        method: "DELETE",
      });
      
      if (response.ok) {
        setPolicies(prev => prev.filter(policy => policy.id !== policyId));
        toast({
          title: "Success",
          description: "Policy deleted successfully",
        });
      } else {
        throw new Error("Failed to delete policy");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete policy",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <GitBranch className="h-8 w-8 text-violet-500 mx-auto mb-4 animate-pulse" />
          <p className="text-muted-foreground">Loading routing policies...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Routing Policies</h1>
          <p className="text-muted-foreground mt-1">Create custom routing endpoints with predefined model strategies</p>
        </div>
        <Link href="/routing-policies/new">
          <button className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors">
            <Plus className="h-4 w-4" />
            Create Policy
          </button>
        </Link>
      </div>

      {/* Strategy Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {strategies.map((strategy, i) => (
          <motion.div
            key={strategy.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Card className={`${strategy.bg} border ${strategy.border} hover:scale-[1.02] transition-transform`}>
              <CardContent className="p-4 text-center">
                <strategy.icon className={`h-6 w-6 mx-auto mb-2 ${strategy.color}`} />
                <p className="font-medium text-sm">{strategy.name}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Policies List */}
      <div className="space-y-4">
        {policies.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <GitBranch className="h-12 w-12 text-muted-foreground/30 mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">No routing policies yet</h3>
              <p className="text-muted-foreground mb-4">
                Create your first routing policy to start directing AI traffic with custom strategies.
              </p>
              <Link href="/routing-policies/new">
                <button className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 transition-colors">
                  <Plus className="h-4 w-4" />
                  Create Policy
                </button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <AnimatePresence>
              {policies.map((policy, i) => {
                const strategy = strategies.find(s => s.id === policy.strategy);
                const stats = statsCache[policy.id];
                
                return (
                  <motion.div
                    key={policy.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <Card className="hover:shadow-md transition-shadow group">
                      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${strategy?.bg || 'bg-secondary'}`}>
                            {strategy ? (
                              <strategy.icon className={`h-4 w-4 ${strategy.color}`} />
                            ) : (
                              <GitBranch className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                          <div>
                            <CardTitle className="text-base">{policy.name}</CardTitle>
                            <p className="text-sm text-muted-foreground line-clamp-1">
                              {policy.description || "No description"}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Switch
                            checked={policy.is_active}
                            onCheckedChange={(checked) => togglePolicyStatus(policy.id, checked)}
                            size="sm"
                          />
                          {policy.is_active ? (
                            <Power className="h-4 w-4 text-emerald-500" />
                          ) : (
                            <PowerOff className="h-4 w-4 text-muted-foreground" />
                          )}
                        </div>
                      </CardHeader>
                      
                      <CardContent className="space-y-4">
                        {/* Strategy and Models */}
                        <div className="flex items-center justify-between">
                          <Badge variant="secondary" className={`${strategy?.bg} ${strategy?.color} border-0`}>
                            {strategy?.name || policy.strategy}
                          </Badge>
                          <span className="text-sm text-muted-foreground">
                            {policy.models.length} model{policy.models.length !== 1 ? 's' : ''}
                          </span>
                        </div>

                        {/* Stats */}
                        {stats && (
                          <div className="grid grid-cols-3 gap-3 pt-3 border-t border-border">
                            <div className="text-center">
                              <p className="text-sm font-semibold">{stats.request_count}</p>
                              <p className="text-xs text-muted-foreground">Requests</p>
                            </div>
                            <div className="text-center">
                              <p className="text-sm font-semibold">${stats.total_cost.toFixed(2)}</p>
                              <p className="text-xs text-muted-foreground">Total Cost</p>
                            </div>
                            <div className="text-center">
                              <p className="text-sm font-semibold">{Math.round(stats.avg_latency_ms)}ms</p>
                              <p className="text-xs text-muted-foreground">Avg Latency</p>
                            </div>
                          </div>
                        )}

                        {/* API Key */}
                        <div className="flex items-center justify-between p-2 bg-secondary/30 rounded-md text-xs">
                          <code className="font-mono text-muted-foreground">
                            {policy.api_key_prefix}•••••••••••••
                          </code>
                          <button
                            onClick={() => copyApiEndpoint(policy.api_key_prefix)}
                            className="text-muted-foreground hover:text-foreground transition-colors"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center justify-between pt-3 border-t border-border">
                          <div className="flex items-center gap-2">
                            <Link href={`/routing-policies/${policy.id}`}>
                              <button className="inline-flex items-center gap-1.5 text-xs text-violet-600 hover:text-violet-700 transition-colors">
                                <Eye className="h-3 w-3" />
                                View Details
                              </button>
                            </Link>
                            <Link href={`/routing-policies/${policy.id}/edit`}>
                              <button className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
                                <Settings className="h-3 w-3" />
                                Edit
                              </button>
                            </Link>
                          </div>
                          <button
                            onClick={() => deletePolicy(policy.id)}
                            className="opacity-0 group-hover:opacity-100 text-xs text-red-500 hover:text-red-600 transition-all"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}