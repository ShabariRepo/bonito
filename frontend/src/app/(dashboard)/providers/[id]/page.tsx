"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowLeft, RefreshCw, Trash2, Activity, Box, Zap, Shield, Globe, DollarSign } from "lucide-react";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge } from "@/components/ui/status-badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  provider_model_id: string;
  capabilities: string[];
  context_window: number;
  pricing_tier: string;
  input_price_per_1k: number | null;
  output_price_per_1k: number | null;
  status: string;
}

interface ProviderDetail {
  id: string;
  provider_type: string;
  status: string;
  name: string;
  region: string;
  model_count: number;
  created_at: string;
  models: ModelInfo[];
  connection_health: string;
}

const tierColors: Record<string, string> = {
  economy: "bg-emerald-500/10 text-emerald-500",
  standard: "bg-blue-500/10 text-blue-500",
  premium: "bg-violet-500/10 text-violet-500",
};

const capabilityIcons: Record<string, typeof Box> = {
  text: Box,
  vision: Globe,
  code: Zap,
  embeddings: Shield,
};

export default function ProviderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const [provider, setProvider] = useState<ProviderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchProvider = async () => {
    try {
      const res = await apiRequest(`/api/providers/${params.id}`);
      if (res.ok) setProvider(await res.json());
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProvider(); }, [params.id]);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const res = await apiRequest(`/api/providers/${params.id}/verify`, { method: "POST" });
      if (res.ok) await fetchProvider();
    } finally {
      setVerifying(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Disconnect this provider? This won't delete any deployed models.")) return;
    setDeleting(true);
    try {
      await apiRequest(`/api/providers/${params.id}`, { method: "DELETE" });
      router.push("/providers");
    } finally {
      setDeleting(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center py-20"><LoadingDots size="lg" /></div>;
  if (!provider) return <div className="py-20 text-center text-muted-foreground">Provider not found</div>;

  return (
    <div className="space-y-8">
      <PageHeader
        title={provider.name}
        description={`${provider.region} · ${provider.model_count} models available`}
        breadcrumbs={[
          { label: "Providers", href: "/providers" },
          { label: provider.name },
        ]}
        actions={
          <div className="flex gap-2">
            <Link
              href={`/providers/${params.id}/playground`}
              className="inline-flex items-center gap-2 rounded-md border border-violet-500/30 bg-violet-500/10 px-3 py-2 text-sm text-violet-400 hover:bg-violet-500/20 transition-colors"
            >
              <Zap className="h-4 w-4" /> Playground
            </Link>
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={handleVerify}
              disabled={verifying}
              className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm hover:bg-accent transition-colors disabled:opacity-50"
            >
              {verifying ? <LoadingDots size="sm" /> : <><RefreshCw className="h-4 w-4" /> Verify</>}
            </motion.button>
            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={handleDelete}
              disabled={deleting}
              className="inline-flex items-center gap-2 rounded-md border border-red-500/30 px-3 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" /> Disconnect
            </motion.button>
          </div>
        }
      />

      {/* Health card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-6 rounded-lg border border-border p-6"
      >
        <div className="flex items-center gap-3">
          <motion.div
            animate={{ scale: [1, 1.15, 1] }}
            transition={{ duration: 1.5, repeat: Infinity }}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-full",
              provider.status === "active" ? "bg-emerald-500/20" : "bg-red-500/20"
            )}
          >
            <Activity className={cn("h-5 w-5", provider.status === "active" ? "text-emerald-500" : "text-red-500")} />
          </motion.div>
          <div>
            <p className="text-sm text-muted-foreground">Connection Health</p>
            <p className="font-semibold capitalize">{provider.connection_health}</p>
          </div>
        </div>
        <div className="h-8 w-px bg-border" />
        <div>
          <p className="text-sm text-muted-foreground">Status</p>
          <StatusBadge status={provider.status as any} />
        </div>
        <div className="h-8 w-px bg-border" />
        <div>
          <p className="text-sm text-muted-foreground">Connected</p>
          <p className="text-sm font-medium">{new Date(provider.created_at).toLocaleDateString()}</p>
        </div>
      </motion.div>

      {/* Models list */}
      <div>
        <h2 className="text-xl font-bold mb-4">Available Models</h2>
        <div className="space-y-3">
          {provider.models.map((model, i) => (
            <motion.div
              key={model.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center justify-between rounded-lg border border-border p-4 hover:bg-accent/30 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent">
                  <Box className="h-5 w-5 text-violet-400" />
                </div>
                <div>
                  <p className="font-medium">{model.name}</p>
                  <p className="text-xs text-muted-foreground font-mono">{model.provider_model_id}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="hidden md:flex items-center gap-1.5">
                  {model.capabilities.slice(0, 3).map((cap) => (
                    <Badge key={cap} variant="secondary" className="text-[10px]">{cap}</Badge>
                  ))}
                  {model.capabilities.length > 3 && (
                    <Badge variant="secondary" className="text-[10px]">+{model.capabilities.length - 3}</Badge>
                  )}
                </div>
                {model.context_window > 0 && (
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {model.context_window >= 1000000
                      ? `${(model.context_window / 1000000).toFixed(1)}M`
                      : `${(model.context_window / 1000).toFixed(0)}K`} ctx
                  </span>
                )}
                <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", tierColors[model.pricing_tier] || tierColors.standard)}>
                  {model.pricing_tier}
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
