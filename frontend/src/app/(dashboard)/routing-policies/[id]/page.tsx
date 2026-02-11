"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  GitBranch,
  DollarSign,
  Zap,
  Scale,
  ShieldAlert,
  FlaskConical,
  Save,
  Play,
  Copy,
  Link,
  Settings,
  BarChart3,
  Trash2,
  ArrowLeft,
  Plus,
  X,
  GripVertical,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { apiRequest } from "@/lib/auth";
import { useToast } from "@/hooks/use-toast";

const strategies = [
  { 
    id: "cost_optimized", 
    name: "Cost Optimized", 
    icon: DollarSign, 
    color: "text-emerald-400", 
    bg: "bg-emerald-500/10", 
    border: "border-emerald-500/20",
    description: "Routes requests to the lowest-cost model that meets requirements"
  },
  { 
    id: "latency_optimized", 
    name: "Latency Optimized", 
    icon: Zap, 
    color: "text-amber-400", 
    bg: "bg-amber-500/10", 
    border: "border-amber-500/20",
    description: "Prioritizes fastest response times"
  },
  { 
    id: "balanced", 
    name: "Balanced", 
    icon: Scale, 
    color: "text-violet-400", 
    bg: "bg-violet-500/10", 
    border: "border-violet-500/20",
    description: "Optimizes for the best cost-performance balance"
  },
  { 
    id: "failover", 
    name: "Failover", 
    icon: ShieldAlert, 
    color: "text-blue-400", 
    bg: "bg-blue-500/10", 
    border: "border-blue-500/20",
    description: "Uses primary model with automatic fallback to backup models"
  },
  { 
    id: "ab_test", 
    name: "A/B Test", 
    icon: FlaskConical, 
    color: "text-pink-400", 
    bg: "bg-pink-500/10", 
    border: "border-pink-500/20",
    description: "Splits traffic between models based on configured weights"
  },
];

interface Model {
  id: string;
  display_name: string;
  model_id: string;
  provider_type: string;
}

interface PolicyModel {
  model_id: string;
  weight?: number;
  role: string;
}

interface RoutingPolicy {
  id: string;
  name: string;
  description?: string;
  strategy: string;
  models: PolicyModel[];
  rules: {
    max_cost_per_request?: number;
    max_tokens?: number;
    allowed_capabilities?: string[];
    region_preference?: string;
  };
  is_active: boolean;
  api_key_prefix: string;
  created_at: string;
  model_names?: Record<string, string>;
}

interface TestResult {
  selected_model_id: string;
  selected_model_name: string;
  strategy_used: string;
  selection_reason: string;
  estimated_cost?: number;
  estimated_latency_ms?: number;
}

export default function PolicyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const policyId = params.id as string;
  const isNew = policyId === "new";

  const [policy, setPolicy] = useState<RoutingPolicy | null>(null);
  const [availableModels, setAvailableModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testPrompt, setTestPrompt] = useState("Summarize this document");

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategy, setStrategy] = useState("balanced");
  const [models, setModels] = useState<PolicyModel[]>([]);
  const [maxCost, setMaxCost] = useState<string>("");
  const [maxTokens, setMaxTokens] = useState<string>("");
  const [regionPreference, setRegionPreference] = useState("");
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    fetchAvailableModels();
    if (!isNew) {
      fetchPolicy();
    }
  }, [policyId, isNew]);

  const fetchAvailableModels = async () => {
    try {
      const response = await apiRequest("/api/models");
      if (response.ok) {
        const data = await response.json();
        setAvailableModels(data);
      }
    } catch (error) {
      console.error("Failed to fetch models:", error);
    }
  };

  const fetchPolicy = async () => {
    try {
      const response = await apiRequest(`/api/routing-policies/${policyId}`);
      if (response.ok) {
        const data = await response.json();
        setPolicy(data);
        
        // Populate form
        setName(data.name);
        setDescription(data.description || "");
        setStrategy(data.strategy);
        setModels(data.models);
        setMaxCost(data.rules.max_cost_per_request?.toString() || "");
        setMaxTokens(data.rules.max_tokens?.toString() || "");
        setRegionPreference(data.rules.region_preference || "");
        setIsActive(data.is_active);
      } else {
        toast({
          title: "Error",
          description: "Policy not found",
          variant: "destructive",
        });
        router.push("/routing-policies");
      }
    } catch (error) {
      console.error("Failed to fetch policy:", error);
      toast({
        title: "Error",
        description: "Failed to load policy",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!name.trim()) {
      toast({
        title: "Error",
        description: "Policy name is required",
        variant: "destructive",
      });
      return;
    }

    if (models.length === 0) {
      toast({
        title: "Error", 
        description: "At least one model must be selected",
        variant: "destructive",
      });
      return;
    }

    // Validate A/B test weights
    if (strategy === "ab_test") {
      const totalWeight = models.reduce((sum, model) => sum + (model.weight || 0), 0);
      if (totalWeight !== 100) {
        toast({
          title: "Error",
          description: "A/B test weights must sum to 100%",
          variant: "destructive",
        });
        return;
      }
    }

    // Validate failover requires at least 2 models
    if (strategy === "failover" && models.length < 2) {
      toast({
        title: "Error",
        description: "Failover strategy requires at least 2 models",
        variant: "destructive",
      });
      return;
    }

    setSaving(true);
    
    try {
      const payload = {
        name,
        description: description || undefined,
        strategy,
        models,
        rules: {
          max_cost_per_request: maxCost ? parseFloat(maxCost) : undefined,
          max_tokens: maxTokens ? parseInt(maxTokens) : undefined,
          region_preference: regionPreference || undefined,
        },
        is_active: isActive,
      };

      const url = isNew ? "/api/routing-policies" : `/api/routing-policies/${policyId}`;
      const method = isNew ? "POST" : "PUT";

      const response = await apiRequest(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const savedPolicy = await response.json();
        toast({
          title: "Success",
          description: `Policy ${isNew ? "created" : "updated"} successfully`,
        });
        
        if (isNew) {
          router.push(`/routing-policies/${savedPolicy.id}`);
        } else {
          setPolicy(savedPolicy);
        }
      } else {
        const error = await response.json();
        throw new Error(error.detail || "Failed to save policy");
      }
    } catch (error) {
      console.error("Failed to save policy:", error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to save policy",
        variant: "destructive",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleTestPolicy = async () => {
    if (!testPrompt.trim()) return;
    
    setTesting(true);
    setTestResult(null);
    
    try {
      const response = await apiRequest(`/api/routing-policies/${policyId}/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: testPrompt }),
      });
      
      if (response.ok) {
        const result = await response.json();
        setTestResult(result);
      } else {
        throw new Error("Failed to test policy");
      }
    } catch (error) {
      console.error("Failed to test policy:", error);
      toast({
        title: "Error",
        description: "Failed to test policy",
        variant: "destructive",
      });
    } finally {
      setTesting(false);
    }
  };

  const addModel = (modelId: string) => {
    const model = availableModels.find(m => m.id === modelId);
    if (!model) return;

    const newModel: PolicyModel = {
      model_id: modelId,
      weight: strategy === "ab_test" ? 50 : undefined,
      role: strategy === "failover" && models.length === 0 ? "primary" : "fallback",
    };

    setModels([...models, newModel]);
  };

  const removeModel = (index: number) => {
    setModels(models.filter((_, i) => i !== index));
  };

  const updateModelWeight = (index: number, weight: number) => {
    setModels(models.map((model, i) => 
      i === index ? { ...model, weight } : model
    ));
  };

  const updateModelRole = (index: number, role: string) => {
    setModels(models.map((model, i) => 
      i === index ? { ...model, role } : model
    ));
  };

  const copyApiEndpoint = () => {
    if (!policy) return;
    
    const endpoint = `https://api.bonito.ai/v1/chat/completions`;
    const curlCommand = `curl -X POST ${endpoint} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${policy.api_key_prefix}" \\
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

  const selectedStrategy = strategies.find(s => s.id === strategy);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="text-center">
          <GitBranch className="h-8 w-8 text-violet-500 mx-auto mb-4 animate-pulse" />
          <p className="text-muted-foreground">Loading policy...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/routing-policies")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">
              {isNew ? "Create Routing Policy" : policy?.name || "Edit Policy"}
            </h1>
            <p className="text-muted-foreground mt-1">
              {isNew 
                ? "Configure a new routing policy with custom model selection strategy"
                : "Modify routing policy settings and model configurations"
              }
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {!isNew && (
            <Button
              variant="outline"
              size="sm"
              onClick={copyApiEndpoint}
            >
              <Copy className="h-4 w-4 mr-2" />
              Copy Endpoint
            </Button>
          )}
          <Button
            onClick={handleSave}
            disabled={saving}
            className="bg-violet-600 hover:bg-violet-700"
          >
            <Save className="h-4 w-4 mr-2" />
            {saving ? "Saving..." : isNew ? "Create Policy" : "Save Changes"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Configuration */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Info */}
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Policy Name</label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Production Chat, Internal Coding"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Description</label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description of this policy's purpose"
                  rows={2}
                />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <label className="block text-sm font-medium">Active</label>
                  <p className="text-sm text-muted-foreground">Enable this routing policy</p>
                </div>
                <Switch
                  checked={isActive}
                  onCheckedChange={setIsActive}
                />
              </div>
            </CardContent>
          </Card>

          {/* Strategy Selection */}
          <Card>
            <CardHeader>
              <CardTitle>Routing Strategy</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {strategies.map((strat) => (
                  <div
                    key={strat.id}
                    className={`cursor-pointer rounded-lg border p-4 transition-all hover:scale-[1.02] ${
                      strategy === strat.id
                        ? `${strat.bg} ${strat.border} shadow-sm`
                        : "border-border hover:border-muted-foreground/30"
                    }`}
                    onClick={() => setStrategy(strat.id)}
                  >
                    <div className="flex items-center gap-3 mb-2">
                      <strat.icon className={`h-5 w-5 ${strategy === strat.id ? strat.color : "text-muted-foreground"}`} />
                      <span className="font-medium text-sm">{strat.name}</span>
                      {strategy === strat.id && (
                        <div className={`h-2 w-2 rounded-full ${strat.color.replace('text-', 'bg-')}`} />
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {strat.description}
                    </p>
                  </div>
                ))}
              </div>
              {selectedStrategy && (
                <div className={`mt-4 p-3 rounded-lg ${selectedStrategy.bg} border ${selectedStrategy.border}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <selectedStrategy.icon className={`h-4 w-4 ${selectedStrategy.color}`} />
                    <span className="text-sm font-medium">Selected: {selectedStrategy.name}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{selectedStrategy.description}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Model Configuration */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Model Configuration</CardTitle>
              <Select onValueChange={addModel}>
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Add model" />
                </SelectTrigger>
                <SelectContent>
                  {availableModels
                    .filter(model => !models.some(m => m.model_id === model.id))
                    .map(model => (
                      <SelectItem key={model.id} value={model.id}>
                        {model.display_name}
                      </SelectItem>
                    ))
                  }
                </SelectContent>
              </Select>
            </CardHeader>
            <CardContent>
              {models.length === 0 ? (
                <div className="text-center py-8 border-2 border-dashed border-border rounded-lg">
                  <Plus className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No models configured</p>
                  <p className="text-xs text-muted-foreground/70">Add models using the dropdown above</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {models.map((model, index) => {
                    const modelInfo = availableModels.find(m => m.id === model.model_id);
                    return (
                      <div
                        key={index}
                        className="flex items-center gap-3 p-3 border border-border rounded-lg group hover:border-muted-foreground/30 transition-colors"
                      >
                        <GripVertical className="h-4 w-4 text-muted-foreground/40 cursor-grab" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-sm">{modelInfo?.display_name || "Unknown Model"}</p>
                          <p className="text-xs text-muted-foreground">{modelInfo?.provider_type}</p>
                        </div>
                        
                        {strategy === "ab_test" && (
                          <div className="flex items-center gap-2">
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              value={model.weight || 0}
                              onChange={(e) => updateModelWeight(index, parseInt(e.target.value) || 0)}
                              className="w-16 text-center text-sm"
                            />
                            <span className="text-xs text-muted-foreground">%</span>
                          </div>
                        )}

                        {strategy === "failover" && (
                          <Select
                            value={model.role}
                            onValueChange={(value) => updateModelRole(index, value)}
                          >
                            <SelectTrigger className="w-24">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="primary">Primary</SelectItem>
                              <SelectItem value="fallback">Fallback</SelectItem>
                            </SelectContent>
                          </Select>
                        )}

                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeModel(index)}
                          className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-600 h-8 w-8"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    );
                  })}
                  
                  {/* Weight validation for A/B test */}
                  {strategy === "ab_test" && models.length > 0 && (
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-amber-500" />
                        <span className="text-sm font-medium">
                          Total Weight: {models.reduce((sum, m) => sum + (m.weight || 0), 0)}%
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        Weights must sum to exactly 100% for A/B testing
                      </p>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Rules & Constraints */}
          <Card>
            <CardHeader>
              <CardTitle>Rules & Constraints</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Max Cost per Request</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={maxCost}
                    onChange={(e) => setMaxCost(e.target.value)}
                    placeholder="0.05"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Max Tokens</label>
                  <Input
                    type="number"
                    min="1"
                    value={maxTokens}
                    onChange={(e) => setMaxTokens(e.target.value)}
                    placeholder="4000"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Region Preference</label>
                <Select value={regionPreference} onValueChange={setRegionPreference}>
                  <SelectTrigger>
                    <SelectValue placeholder="No preference" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">No preference</SelectItem>
                    <SelectItem value="us-east-1">US East (Virginia)</SelectItem>
                    <SelectItem value="us-west-2">US West (Oregon)</SelectItem>
                    <SelectItem value="eu-west-1">EU West (Ireland)</SelectItem>
                    <SelectItem value="ap-southeast-1">Asia Pacific (Singapore)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* API Endpoint */}
          {!isNew && policy && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Link className="h-4 w-4" />
                  API Endpoint
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">API Key</label>
                    <div className="flex items-center gap-2 p-2 bg-secondary/30 rounded-md">
                      <code className="text-xs font-mono flex-1">{policy.api_key_prefix}•••••••••••••</code>
                      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={copyApiEndpoint}>
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-muted-foreground mb-1">Endpoint</label>
                    <code className="block text-xs p-2 bg-secondary/30 rounded-md">
                      POST https://api.bonito.ai/v1/chat/completions
                    </code>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Policy Testing */}
          {!isNew && policy && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Play className="h-4 w-4" />
                  Test Policy
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Input
                  value={testPrompt}
                  onChange={(e) => setTestPrompt(e.target.value)}
                  placeholder="Enter test prompt..."
                />
                <Button
                  onClick={handleTestPolicy}
                  disabled={testing || !testPrompt.trim()}
                  size="sm"
                  className="w-full"
                  variant="outline"
                >
                  {testing ? "Testing..." : "Run Test"}
                </Button>
                
                <AnimatePresence>
                  {testResult && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="space-y-2 overflow-hidden"
                    >
                      <div className="p-3 border border-border rounded-lg bg-secondary/20">
                        <p className="text-sm font-medium mb-1">{testResult.selected_model_name}</p>
                        <p className="text-xs text-muted-foreground line-clamp-2">{testResult.selection_reason}</p>
                        <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
                          <span>${testResult.estimated_cost?.toFixed(4) || 0}</span>
                          <span>{testResult.estimated_latency_ms}ms</span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </CardContent>
            </Card>
          )}

          {/* Quick Stats */}
          {!isNew && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <BarChart3 className="h-4 w-4" />
                  Quick Stats
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Requests (24h)</span>
                    <span className="text-sm font-medium">23</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Total Cost</span>
                    <span className="text-sm font-medium">$12.45</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Avg Latency</span>
                    <span className="text-sm font-medium">145ms</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Success Rate</span>
                    <span className="text-sm font-medium text-emerald-600">98.7%</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}