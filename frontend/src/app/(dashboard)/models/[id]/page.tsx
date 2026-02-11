"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, useInView } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { PageHeader } from "@/components/ui/page-header";
import { 
  Box, 
  DollarSign, 
  TrendingUp, 
  Activity, 
  ArrowLeft,
  Play,
  Cloud,
  Zap,
  Gauge
} from "lucide-react";
import { apiRequest } from "@/lib/auth";
import Link from "next/link";

interface ModelDetails {
  id: string;
  model_id: string;
  display_name: string;
  provider_type: string;
  capabilities: Record<string, any>;
  pricing_info: Record<string, any>;
  created_at: string;
  provider_info: {
    id: string;
    provider_type: string;
    status: string;
    region?: string;
  };
  usage_stats: {
    total_requests: number;
    total_tokens: number;
    total_cost: number;
    requests_by_day: Array<{
      date: string;
      requests: number;
      cost: number;
    }>;
  };
  context_window?: number;
  input_price_per_1k?: number;
  output_price_per_1k?: number;
}

/* ─── Animated counter ─── */
function AnimatedCounter({ 
  value, 
  prefix = "", 
  suffix = "", 
  decimals = 0 
}: {
  value: number; 
  prefix?: string; 
  suffix?: string; 
  decimals?: number;
}) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref as any, { once: true });

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const steps = Math.ceil(1.2 * 60);
    const increment = value / steps;
    let frame = 0;
    const timer = setInterval(() => {
      frame++;
      start += increment;
      if (frame >= steps) { 
        setCount(value); 
        clearInterval(timer); 
      } else setCount(start);
    }, 1000 / 60);
    return () => clearInterval(timer);
  }, [inView, value]);

  return (
    <span ref={ref}>
      {prefix}{count.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}{suffix}
    </span>
  );
}

/* ─── Mini line chart ─── */
function UsageChart({ data }: { data: Array<{ date: string; requests: number }> }) {
  if (!data.length) return null;
  
  const values = data.map(d => d.requests);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  
  const w = 200;
  const h = 60;
  const points = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 10) - 5;
    return `${x},${y}`;
  }).join(" ");
  
  const areaPoints = `0,${h} ${points} ${w},${h}`;
  
  return (
    <div className="h-16 w-full">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="usageGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
          </linearGradient>
        </defs>
        <motion.polygon
          points={areaPoints}
          fill="url(#usageGrad)"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1 }}
        />
        <motion.polyline
          points={points}
          fill="none"
          stroke="#8b5cf6"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
      </svg>
    </div>
  );
}

function getCapabilityIcon(cap: string) {
  switch (cap) {
    case "chat": return "💬";
    case "code": return "💻";
    case "vision": return "👁";
    case "embedding": return "🧮";
    case "image-generation": return "🎨";
    default: return "✨";
  }
}

function inferCapabilities(modelId: string): string[] {
  const id = modelId.toLowerCase();
  const caps: string[] = [];
  if (id.includes("embed")) return ["embedding"];
  if (id.includes("image") || id.includes("stable-diffusion") || id.includes("titan-image") || id.includes("nova-canvas")) return ["image-generation"];
  caps.push("chat");
  if (id.includes("claude") || id.includes("llama") || id.includes("mistral") || id.includes("codellama") || id.includes("deepseek")) caps.push("code");
  if (id.includes("claude-3") || id.includes("nova") || id.includes("claude-4")) caps.push("vision");
  return caps;
}

export default function ModelDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [model, setModel] = useState<ModelDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchModelDetails() {
      try {
        const res = await apiRequest(`/api/models/${params.id}/details`);
        if (res.ok) {
          const data = await res.json();
          setModel(data);
        } else {
          setError("Failed to fetch model details");
        }
      } catch (e) {
        console.error("Failed to fetch model details", e);
        setError("Failed to fetch model details");
      } finally {
        setLoading(false);
      }
    }

    if (params.id) {
      fetchModelDetails();
    }
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingDots size="lg" />
      </div>
    );
  }

  if (error || !model) {
    return (
      <div className="flex flex-col items-center justify-center h-96 text-center">
        <Box className="h-12 w-12 text-muted-foreground mb-4" />
        <h3 className="text-xl font-semibold">Model not found</h3>
        <p className="text-muted-foreground mt-2">
          The model you're looking for doesn't exist or you don't have access to it.
        </p>
        <Link href="/models" className="mt-4 text-violet-600 hover:text-violet-700">
          ← Back to models
        </Link>
      </div>
    );
  }

  const capabilities = Array.isArray(model.capabilities) 
    ? model.capabilities 
    : model.capabilities?.types && Array.isArray(model.capabilities.types)
    ? model.capabilities.types
    : inferCapabilities(model.model_id);

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-4">
        <Link href="/models" className="p-2 hover:bg-accent rounded-lg transition-colors">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <PageHeader
          title={model.display_name}
          description={`${model.provider_type} • ${model.model_id}`}
          actions={
            <Link
              href={`/playground?model=${model.id}`}
              className="inline-flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors"
            >
              <Play className="h-4 w-4" />
              Open in Playground
            </Link>
          }
        />
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <AnimatedCounter value={model.usage_stats.total_requests} />
            </div>
            <p className="text-xs text-muted-foreground">All time usage</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Tokens</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <AnimatedCounter value={model.usage_stats.total_tokens} />
            </div>
            <p className="text-xs text-muted-foreground">Input + output tokens</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              $<AnimatedCounter value={model.usage_stats.total_cost} decimals={2} />
            </div>
            <p className="text-xs text-muted-foreground">Lifetime spending</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Provider Status</CardTitle>
            <Cloud className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Badge variant={model.provider_info.status === 'active' ? 'success' : 'destructive'}>
                {model.provider_info.status}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground capitalize">{model.provider_type}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Usage Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            {model.usage_stats.requests_by_day.length > 0 ? (
              <UsageChart data={model.usage_stats.requests_by_day} />
            ) : (
              <div className="flex items-center justify-center h-16 text-muted-foreground">
                No usage data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Pricing Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {model.input_price_per_1k !== undefined && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Input (per 1K tokens)</span>
                <span className="font-medium">${model.input_price_per_1k}</span>
              </div>
            )}
            {model.output_price_per_1k !== undefined && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Output (per 1K tokens)</span>
                <span className="font-medium">${model.output_price_per_1k}</span>
              </div>
            )}
            {model.context_window && (
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Context Window</span>
                <span className="font-medium">{model.context_window.toLocaleString()} tokens</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Model Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-medium mb-2">Capabilities</h4>
            <div className="flex flex-wrap gap-2">
              {capabilities.map((cap: string) => (
                <Badge key={cap} variant="secondary" className="gap-1">
                  <span>{getCapabilityIcon(cap)}</span>
                  {cap}
                </Badge>
              ))}
            </div>
          </div>

          <div>
            <h4 className="font-medium mb-2">Model ID</h4>
            <code className="text-sm bg-accent px-2 py-1 rounded">{model.model_id}</code>
          </div>

          <div>
            <h4 className="font-medium mb-2">Created</h4>
            <span className="text-sm text-muted-foreground">
              {new Date(model.created_at).toLocaleDateString()}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}