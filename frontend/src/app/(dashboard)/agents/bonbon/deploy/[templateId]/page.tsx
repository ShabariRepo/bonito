"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Headphones,
  BookOpen,
  TrendingUp,
  PenTool,
  Sparkles,
  ArrowLeft,
  ArrowRight,
  Check,
  Upload,
  Rocket,
  Code,
  ExternalLink,
  ChevronDown,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { StepWizard } from "@/components/ui/step-wizard";
import { useToast } from "@/components/ui/use-toast";
import { apiRequest } from "@/lib/auth";

interface Template {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  system_prompt: string;
  suggested_tone: string;
  widget_enabled: boolean;
  default_widget_config: {
    welcome_message: string;
    suggested_questions: string[];
    theme: string;
    accent_color: string;
  };
  tags: string[];
}

interface ModelRecommendation {
  primary: {
    model_id: string;
    name: string;
    provider: string;
    tier: string;
  };
  fallback: {
    model_id: string;
    name: string;
    provider: string;
    tier: string;
  };
  providers: string[];
}

interface Project {
  id: string;
  name: string;
}

const ICON_MAP: Record<string, React.ReactNode> = {
  Headphones: <Headphones className="h-8 w-8" />,
  BookOpen: <BookOpen className="h-8 w-8" />,
  TrendingUp: <TrendingUp className="h-8 w-8" />,
  PenTool: <PenTool className="h-8 w-8" />,
};

const PROVIDER_LABELS: Record<string, string> = {
  gcp: "Google Cloud",
  aws: "Amazon Web Services",
  azure: "Microsoft Azure",
};

const TONE_OPTIONS = [
  { value: "warm and professional", label: "Warm & Professional" },
  { value: "precise and helpful", label: "Precise & Helpful" },
  { value: "conversational and consultative", label: "Conversational & Consultative" },
  { value: "creative and on-brand", label: "Creative & On-brand" },
  { value: "formal and authoritative", label: "Formal & Authoritative" },
  { value: "casual and friendly", label: "Casual & Friendly" },
];

const INDUSTRY_OPTIONS = [
  "Technology",
  "Healthcare",
  "Finance",
  "E-commerce",
  "Education",
  "Real Estate",
  "Legal",
  "Manufacturing",
  "Hospitality",
  "Media",
  "Non-profit",
  "Other",
];

const STEPS = [
  { title: "Template", description: "Review your Solution Kit" },
  { title: "Configure", description: "Customize for your business" },
  { title: "Knowledge", description: "Add your data" },
  { title: "Model", description: "Pick your AI model" },
  { title: "Deploy", description: "Launch your agent" },
];

export default function DeployPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const templateId = params.templateId as string;

  const [step, setStep] = useState(0);
  const [template, setTemplate] = useState<Template | null>(null);
  const [modelRec, setModelRec] = useState<ModelRecommendation | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(false);
  const [deployed, setDeployed] = useState(false);
  const [deployedAgentId, setDeployedAgentId] = useState<string | null>(null);

  // Form state
  const [agentName, setAgentName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [tone, setTone] = useState("");
  const [industry, setIndustry] = useState("");
  const [projectId, setProjectId] = useState("");
  const [useRecommendedModel, setUseRecommendedModel] = useState(true);
  const [customModelId, setCustomModelId] = useState("");

  useEffect(() => {
    Promise.all([fetchTemplate(), fetchModelRec(), fetchProjects()]).finally(() =>
      setLoading(false)
    );
  }, [templateId]);

  const fetchTemplate = async () => {
    try {
      const res = await apiRequest(`/api/bonbon/templates/${templateId}`);
      if (res.ok) {
        const data = await res.json();
        setTemplate(data);
        setAgentName(data.name);
        setTone(data.suggested_tone);
      } else {
        toast({ title: "Error", description: "Template not found", variant: "destructive" });
        router.push("/agents/bonbon");
      }
    } catch {
      router.push("/agents/bonbon");
    }
  };

  const fetchModelRec = async () => {
    try {
      const res = await apiRequest("/api/bonbon/recommend-models");
      if (res.ok) {
        const data = await res.json();
        setModelRec(data);
      }
    } catch {
      /* non-critical */
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await apiRequest("/api/projects");
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
        if (data.length > 0) setProjectId(data[0].id);
      }
    } catch {
      /* handled */
    }
  };

  const handleDeploy = async () => {
    if (!projectId) {
      toast({ title: "Error", description: "Please select a project", variant: "destructive" });
      return;
    }

    setDeploying(true);
    try {
      const res = await apiRequest("/api/bonbon/deploy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_id: templateId,
          project_id: projectId,
          name: agentName || undefined,
          company_name: companyName || undefined,
          tone: tone || undefined,
          industry: industry || undefined,
          model_id: useRecommendedModel ? undefined : customModelId || undefined,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setDeployed(true);
        setDeployedAgentId(data.agent.id);
        toast({ title: "🚀 Agent Deployed!", description: `${agentName} is now live` });
      } else {
        const err = await res.json().catch(() => ({}));
        toast({
          title: "Deployment Failed",
          description: err.detail || "Something went wrong",
          variant: "destructive",
        });
      }
    } catch {
      toast({ title: "Error", description: "Deployment failed", variant: "destructive" });
    } finally {
      setDeploying(false);
    }
  };

  if (loading || !template) {
    return (
      <div className="max-w-3xl mx-auto p-6 space-y-8">
        <div className="h-8 bg-muted rounded w-64 animate-pulse" />
        <div className="h-64 bg-muted rounded animate-pulse" />
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      {/* Back button */}
      <Button variant="ghost" size="sm" onClick={() => router.push("/agents/bonbon")} className="gap-1.5">
        <ArrowLeft className="h-4 w-4" />
        Back to Solution Kits
      </Button>

      <StepWizard steps={STEPS} currentStep={step}>
        {/* Step 1: Template Overview */}
        {step === 0 && (
          <Card>
            <CardHeader className="space-y-4">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-violet-500/10 text-violet-400">
                  {ICON_MAP[template.icon] || <Sparkles className="h-8 w-8" />}
                </div>
                <div>
                  <CardTitle className="text-xl">{template.name}</CardTitle>
                  <CardDescription className="mt-1">{template.description}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Category</p>
                  <Badge variant="outline">{template.category}</Badge>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Default Tone</p>
                  <Badge variant="outline">{template.suggested_tone}</Badge>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Widget</p>
                  <Badge variant={template.widget_enabled ? "default" : "secondary"}>
                    {template.widget_enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">Tags</p>
                  <div className="flex gap-1 flex-wrap">
                    {template.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-4 flex justify-end">
                <Button onClick={() => setStep(1)} className="gap-1.5">
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Configure */}
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Configure Your Agent</CardTitle>
              <CardDescription>Customize the agent for your business</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="projectId">Project</Label>
                <Select value={projectId} onValueChange={setProjectId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a project" />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map((p) => (
                      <SelectItem key={p.id} value={p.id}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="agentName">Agent Name</Label>
                <Input
                  id="agentName"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="e.g., Acme Support Bot"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="companyName">Company Name</Label>
                <Input
                  id="companyName"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Your company name (used in the system prompt)"
                />
              </div>

              <div className="space-y-2">
                <Label>Tone</Label>
                <Select value={tone} onValueChange={setTone}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a tone" />
                  </SelectTrigger>
                  <SelectContent>
                    {TONE_OPTIONS.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Industry</Label>
                <Select value={industry} onValueChange={setIndustry}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select your industry" />
                  </SelectTrigger>
                  <SelectContent>
                    {INDUSTRY_OPTIONS.map((ind) => (
                      <SelectItem key={ind} value={ind}>
                        {ind}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="pt-4 flex justify-between">
                <Button variant="outline" onClick={() => setStep(0)} className="gap-1.5">
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
                <Button onClick={() => setStep(2)} className="gap-1.5">
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 3: Knowledge */}
        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle>Add Knowledge</CardTitle>
              <CardDescription>
                Give your agent context about your business. You can skip this and add knowledge later.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="border-2 border-dashed border-border rounded-xl p-12 text-center hover:border-violet-500/40 transition-colors cursor-pointer">
                <Upload className="h-10 w-10 mx-auto text-muted-foreground mb-3" />
                <p className="text-sm font-medium">Drag & drop files here</p>
                <p className="text-xs text-muted-foreground mt-1">
                  PDF, TXT, DOCX, or MD — up to 10MB each
                </p>
                <Button variant="outline" size="sm" className="mt-4">
                  Browse Files
                </Button>
              </div>

              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <span className="w-full border-t" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-card px-2 text-muted-foreground">or</span>
                </div>
              </div>

              <div className="text-center py-4">
                <p className="text-sm text-muted-foreground">
                  Connect an existing AI Context (Knowledge Base) after deployment
                </p>
              </div>

              <div className="pt-4 flex justify-between">
                <Button variant="outline" onClick={() => setStep(1)} className="gap-1.5">
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
                <Button onClick={() => setStep(3)} className="gap-1.5">
                  {/* Skip or continue */}
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 4: Model */}
        {step === 3 && (
          <Card>
            <CardHeader>
              <CardTitle>Choose AI Model</CardTitle>
              <CardDescription>
                We recommend a model based on your connected cloud providers
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              {modelRec && (
                <>
                  {/* Recommended model card */}
                  <div
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                      useRecommendedModel
                        ? "border-violet-500 bg-violet-500/5"
                        : "border-border hover:border-border/80"
                    }`}
                    onClick={() => setUseRecommendedModel(true)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={`h-5 w-5 rounded-full border-2 flex items-center justify-center ${
                            useRecommendedModel
                              ? "border-violet-500 bg-violet-500"
                              : "border-muted-foreground"
                          }`}
                        >
                          {useRecommendedModel && <Check className="h-3 w-3 text-white" />}
                        </div>
                        <div>
                          <p className="font-medium flex items-center gap-2">
                            {modelRec.primary.name}
                            <Badge className="bg-violet-500/10 text-violet-400 border-violet-500/20 text-xs">
                              Recommended
                            </Badge>
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {PROVIDER_LABELS[modelRec.primary.provider] || modelRec.primary.provider}{" "}
                            · Fast & cost-effective
                          </p>
                        </div>
                      </div>
                      <Badge variant="secondary">{modelRec.primary.tier}</Badge>
                    </div>
                    {modelRec.fallback && (
                      <p className="text-xs text-muted-foreground mt-2 ml-8">
                        Fallback: {modelRec.fallback.name} ({modelRec.fallback.provider.toUpperCase()})
                      </p>
                    )}
                  </div>

                  {/* Custom model option */}
                  <div
                    className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                      !useRecommendedModel
                        ? "border-violet-500 bg-violet-500/5"
                        : "border-border hover:border-border/80"
                    }`}
                    onClick={() => setUseRecommendedModel(false)}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-5 w-5 rounded-full border-2 flex items-center justify-center ${
                          !useRecommendedModel
                            ? "border-violet-500 bg-violet-500"
                            : "border-muted-foreground"
                        }`}
                      >
                        {!useRecommendedModel && <Check className="h-3 w-3 text-white" />}
                      </div>
                      <div>
                        <p className="font-medium">Choose a different model</p>
                        <p className="text-sm text-muted-foreground">
                          Select from your connected providers
                        </p>
                      </div>
                    </div>
                    {!useRecommendedModel && (
                      <div className="mt-3 ml-8">
                        <Input
                          placeholder="e.g., gpt-4o, gemini-2.0-flash"
                          value={customModelId}
                          onChange={(e) => setCustomModelId(e.target.value)}
                        />
                      </div>
                    )}
                  </div>

                  {modelRec.providers.length > 0 && (
                    <p className="text-xs text-muted-foreground">
                      Connected providers:{" "}
                      {modelRec.providers
                        .map((p) => PROVIDER_LABELS[p] || p.toUpperCase())
                        .join(", ")}
                    </p>
                  )}
                </>
              )}

              <div className="pt-4 flex justify-between">
                <Button variant="outline" onClick={() => setStep(2)} className="gap-1.5">
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
                <Button onClick={() => setStep(4)} className="gap-1.5">
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 5: Deploy */}
        {step === 4 && !deployed && (
          <Card>
            <CardHeader>
              <CardTitle>Ready to Deploy</CardTitle>
              <CardDescription>Review your configuration and launch your agent</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="bg-muted/50 rounded-lg p-4 space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Template</span>
                  <span className="font-medium">{template.name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Agent Name</span>
                  <span className="font-medium">{agentName || template.name}</span>
                </div>
                {companyName && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Company</span>
                    <span className="font-medium">{companyName}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Tone</span>
                  <span className="font-medium">{tone}</span>
                </div>
                {industry && (
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Industry</span>
                    <span className="font-medium">{industry}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Model</span>
                  <span className="font-medium">
                    {useRecommendedModel
                      ? modelRec?.primary.name || "Auto"
                      : customModelId || "Auto"}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Widget</span>
                  <span className="font-medium">
                    {template.widget_enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
              </div>

              <div className="pt-4 flex justify-between">
                <Button variant="outline" onClick={() => setStep(3)} className="gap-1.5">
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </Button>
                <Button
                  onClick={handleDeploy}
                  disabled={deploying}
                  className="gap-1.5 bg-violet-600 hover:bg-violet-700"
                >
                  {deploying ? (
                    <>
                      <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Deploying...
                    </>
                  ) : (
                    <>
                      <Rocket className="h-4 w-4" />
                      Deploy Agent
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step 5: Success */}
        {step === 4 && deployed && (
          <Card className="border-green-500/30">
            <CardContent className="pt-8 pb-8 text-center space-y-6">
              <div className="mx-auto w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center">
                <Check className="h-8 w-8 text-green-500" />
              </div>
              <div className="space-y-2">
                <h2 className="text-2xl font-bold">Agent Deployed! 🎉</h2>
                <p className="text-muted-foreground">
                  <span className="font-medium text-foreground">{agentName}</span> is now live and
                  ready to chat.
                </p>
              </div>
              <div className="flex items-center justify-center gap-3">
                <Button
                  onClick={() => {
                    const project = projects.find((p) => p.id === projectId);
                    router.push(`/agents/${projectId}`);
                  }}
                  className="gap-1.5"
                >
                  <ExternalLink className="h-4 w-4" />
                  Open Agent
                </Button>
                {template.widget_enabled && (
                  <Button variant="outline" className="gap-1.5">
                    <Code className="h-4 w-4" />
                    Get Widget Code
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </StepWizard>
    </div>
  );
}
