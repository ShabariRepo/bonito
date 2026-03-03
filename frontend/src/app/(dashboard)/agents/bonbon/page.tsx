"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Headphones,
  BookOpen,
  TrendingUp,
  PenTool,
  Sparkles,
  ArrowRight,
  Zap,
  Siren,
  GitPullRequest,
  Rocket,
  FileCode,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import { apiRequest } from "@/lib/auth";

interface Template {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  suggested_tone: string;
  widget_enabled: boolean;
  tags: string[];
  tier: "simple" | "advanced";
}

const ICON_MAP: Record<string, React.ReactNode> = {
  Headphones: <Headphones className="h-6 w-6" />,
  BookOpen: <BookOpen className="h-6 w-6" />,
  TrendingUp: <TrendingUp className="h-6 w-6" />,
  PenTool: <PenTool className="h-6 w-6" />,
  Siren: <Siren className="h-6 w-6" />,
  GitPullRequest: <GitPullRequest className="h-6 w-6" />,
  Rocket: <Rocket className="h-6 w-6" />,
  FileCode: <FileCode className="h-6 w-6" />,
};

const CATEGORY_COLORS: Record<string, string> = {
  Support: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
  Internal: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  Sales: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Marketing: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  DevOps: "bg-red-500/10 text-red-400 border-red-500/20",
};

const CARD_ACCENTS: Record<string, string> = {
  customer_service: "hover:border-indigo-500/40",
  knowledge_assistant: "hover:border-sky-500/40",
  sales_qualifier: "hover:border-emerald-500/40",
  content_assistant: "hover:border-amber-500/40",
  incident_responder: "hover:border-red-500/40",
  code_reviewer: "hover:border-purple-500/40",
  deploy_monitor: "hover:border-orange-500/40",
  devops_docs: "hover:border-cyan-500/40",
};

const ICON_BG: Record<string, string> = {
  customer_service: "bg-indigo-500/10 text-indigo-400",
  knowledge_assistant: "bg-sky-500/10 text-sky-400",
  sales_qualifier: "bg-emerald-500/10 text-emerald-400",
  content_assistant: "bg-amber-500/10 text-amber-400",
  incident_responder: "bg-red-500/10 text-red-400",
  code_reviewer: "bg-purple-500/10 text-purple-400",
  deploy_monitor: "bg-orange-500/10 text-orange-400",
  devops_docs: "bg-cyan-500/10 text-cyan-400",
};

export default function BonBonPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const { toast } = useToast();

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const res = await apiRequest("/api/bonbon/templates");
      if (res.ok) {
        const data = await res.json();
        setTemplates(data);
      }
    } catch (error) {
      console.error("Failed to fetch templates:", error);
      toast({
        title: "Error",
        description: "Failed to load Solution Kits",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-8 p-6">
        <div className="text-center space-y-2">
          <div className="h-8 bg-muted rounded w-48 mx-auto animate-pulse" />
          <div className="h-4 bg-muted rounded w-96 mx-auto animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="space-y-2">
                <div className="h-10 w-10 bg-muted rounded-lg" />
                <div className="h-5 bg-muted rounded w-3/4" />
                <div className="h-4 bg-muted rounded w-full" />
              </CardHeader>
              <CardContent>
                <div className="h-10 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 p-6">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="flex items-center justify-center gap-2">
          <Sparkles className="h-6 w-6 text-violet-400" />
          <h1 className="text-3xl font-bold">BonBon Solution Kits</h1>
        </div>
        <p className="text-muted-foreground text-lg max-w-xl mx-auto">
          Deploy a production-ready AI agent in minutes. Pick a kit, customize it for your business, and go live.
        </p>
      </div>

      {/* Feature badges */}
      <div className="flex items-center justify-center gap-3 flex-wrap">
        <Badge variant="outline" className="gap-1.5 py-1 px-3">
          <Zap className="h-3 w-3 text-violet-400" />
          Auto model selection
        </Badge>
        <Badge variant="outline" className="gap-1.5 py-1 px-3">
          <Sparkles className="h-3 w-3 text-violet-400" />
          Production-quality prompts
        </Badge>
        <Badge variant="outline" className="gap-1.5 py-1 px-3">
          <Headphones className="h-3 w-3 text-violet-400" />
          Embeddable widget
        </Badge>
      </div>

      {/* Template cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
        {templates.map((template) => (
          <Card
            key={template.id}
            className={`group cursor-pointer border-2 transition-all duration-200 hover:shadow-lg ${
              CARD_ACCENTS[template.id] || "hover:border-violet-500/40"
            }`}
            onClick={() => router.push(`/agents/bonbon/deploy/${template.id}`)}
          >
            <CardHeader className="space-y-3">
              <div className="flex items-start justify-between">
                <div
                  className={`p-2.5 rounded-lg ${
                    ICON_BG[template.id] || "bg-violet-500/10 text-violet-400"
                  }`}
                >
                  {ICON_MAP[template.icon] || <Sparkles className="h-6 w-6" />}
                </div>
                <div className="flex items-center gap-1.5">
                  <Badge
                    variant="outline"
                    className={
                      template.tier === "advanced"
                        ? "bg-violet-500/10 text-violet-400 border-violet-500/20"
                        : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                    }
                  >
                    {template.tier === "advanced" ? "Advanced · $99/mo" : "Simple · $49/mo"}
                  </Badge>
                  <Badge
                    variant="outline"
                    className={CATEGORY_COLORS[template.category] || ""}
                  >
                    {template.category}
                  </Badge>
                </div>
              </div>
              <div>
                <CardTitle className="text-lg">{template.name}</CardTitle>
                <CardDescription className="mt-1.5 line-clamp-2">
                  {template.description}
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="flex items-center justify-between">
                <div className="flex gap-1.5">
                  {template.widget_enabled && (
                    <Badge variant="secondary" className="text-xs">
                      Widget-ready
                    </Badge>
                  )}
                  <Badge variant="secondary" className="text-xs">
                    {template.suggested_tone}
                  </Badge>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1 group-hover:text-violet-400 transition-colors"
                >
                  Deploy
                  <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
