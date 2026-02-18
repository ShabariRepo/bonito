"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Cloud,
  Check,
  Copy,
  Download,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Shield,
  Terminal,
  FileCode,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Rocket,
  Activity,
  Upload,
  ChevronDown,
  ChevronRight,
  Zap,
  Key,
  Eye,
  EyeOff,
  PartyPopper,
  Database,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";

// --- Types ---
type Provider = "aws" | "azure" | "gcp" | "openai" | "anthropic";
type IaCTool = "terraform" | "pulumi" | "cloudformation" | "bicep" | "manual";
type OnboardingPath = "quick" | "iac" | null;

interface PermissionCheck {
  name: string;
  description: string;
  status: "pending" | "checking" | "pass" | "fail" | "warn";
  message?: string;
}

interface IaCFile {
  filename: string;
  content: string;
}

interface IaCResult {
  code: string;
  filename: string;
  files: IaCFile[];
  instructions: string[];
  security_notes: string[];
}

interface ValidationResult {
  valid: boolean;
  identity?: string;
  permissions?: string[];
  errors?: string[];
  health?: {
    provider: string;
    status: string;
    checks: { name: string; status: string; message: string }[];
    checked_at: string;
  };
}

// --- Constants ---

const PROVIDERS: { id: Provider; name: string; icon: string; color: string; desc: string }[] = [
  { id: "aws", name: "AWS", icon: "☁️", color: "from-orange-500 to-yellow-500", desc: "Amazon Bedrock — Claude, Llama, Titan" },
  { id: "azure", name: "Azure", icon: "🔷", color: "from-blue-500 to-cyan-500", desc: "Azure AI Foundry — GPT-4o, Phi, Mistral" },
  { id: "gcp", name: "Google Cloud", icon: "🌐", color: "from-green-500 to-emerald-500", desc: "Vertex AI — Gemini, PaLM, Claude" },
  { id: "openai", name: "OpenAI", icon: "🤖", color: "from-green-500 to-blue-500", desc: "Direct API — GPT-4o, o1, o3-mini" },
  { id: "anthropic", name: "Anthropic", icon: "🧠", color: "from-purple-500 to-pink-500", desc: "Direct API — Claude 3.5 Sonnet, Claude Opus" },
];

const REQUIRED_PERMISSIONS: Record<Provider, { key: string; name: string; description: string; required: boolean }[]> = {
  aws: [
    { key: "sts", name: "STS Identity", description: "sts:GetCallerIdentity — Validate credentials", required: true },
    { key: "bedrock", name: "Bedrock Access", description: "bedrock:ListFoundationModels, bedrock:InvokeModel — List & use AI models", required: true },
    { key: "cost", name: "Cost Explorer", description: "ce:GetCostAndUsage, ce:GetCostForecast — Track AI spending", required: false },
  ],
  azure: [
    { key: "auth", name: "OAuth Authentication", description: "Service principal authentication via client credentials", required: true },
    { key: "subscription", name: "Subscription Access", description: "Read access to your Azure subscription", required: true },
  ],
  gcp: [
    { key: "auth", name: "Service Account Auth", description: "JWT authentication with service account key", required: true },
    { key: "vertex", name: "Vertex AI Access", description: "aiplatform.models.list, aiplatform.endpoints.predict — List & use AI models", required: true },
  ],
  openai: [
    { key: "api_key", name: "API Key Authentication", description: "Valid OpenAI API key with model access", required: true },
    { key: "models", name: "Model Access", description: "Access to GPT-4o, o1, and other OpenAI models", required: true },
  ],
  anthropic: [
    { key: "api_key", name: "API Key Authentication", description: "Valid Anthropic API key with model access", required: true },
    { key: "models", name: "Model Access", description: "Access to Claude 3.5 Sonnet, Opus, and other models", required: true },
  ],
};

const CRED_FIELDS: Record<Provider, { key: string; label: string; type?: string; placeholder?: string; required?: boolean }[]> = {
  aws: [
    { key: "access_key_id", label: "Access Key ID", placeholder: "AKIA...", required: true },
    { key: "secret_access_key", label: "Secret Access Key", type: "password", placeholder: "Your secret access key", required: true },
    { key: "region", label: "Region", placeholder: "us-east-1" },
  ],
  azure: [
    { key: "tenant_id", label: "Tenant ID", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", required: true },
    { key: "client_id", label: "Client ID", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", required: true },
    { key: "client_secret", label: "Client Secret", type: "password", placeholder: "Your client secret", required: true },
    { key: "subscription_id", label: "Subscription ID", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", required: true },
  ],
  gcp: [
    { key: "project_id", label: "Project ID", placeholder: "my-project-123" },
    { key: "key_file", label: "Service Account Key (JSON)", type: "file", required: true },
  ],
  openai: [
    { key: "api_key", label: "API Key", type: "password", placeholder: "sk-...", required: true },
    { key: "organization_id", label: "Organization ID (Optional)", placeholder: "org-..." },
  ],
  anthropic: [
    { key: "api_key", label: "API Key", type: "password", placeholder: "sk-ant-api03-...", required: true },
  ],
};

const IAC_TOOLS: { id: IaCTool; name: string; icon: React.ReactNode; desc: string; providers: Provider[] }[] = [
  { id: "terraform", name: "Terraform", icon: <FileCode className="h-5 w-5" />, desc: "HashiCorp Terraform (HCL)", providers: ["aws", "azure", "gcp"] },
  { id: "pulumi", name: "Pulumi", icon: <FileCode className="h-5 w-5" />, desc: "Pulumi (Python)", providers: ["aws", "azure", "gcp"] },
  { id: "cloudformation", name: "CloudFormation", icon: <Cloud className="h-5 w-5" />, desc: "AWS CloudFormation (YAML)", providers: ["aws"] },
  { id: "bicep", name: "Bicep", icon: <FileCode className="h-5 w-5" />, desc: "Azure Bicep", providers: ["azure"] },
  { id: "manual", name: "Manual Setup", icon: <Terminal className="h-5 w-5" />, desc: "Step-by-step CLI instructions", providers: ["aws", "azure", "gcp"] },
];

// Document Context storage config fields per cloud provider
const DOC_STORAGE_FIELDS: Record<string, { key: string; label: string; placeholder: string }[]> = {
  aws: [
    { key: "bucket", label: "S3 Bucket Name", placeholder: "bonito-kb-{org}" },
    { key: "prefix", label: "Prefix (folder)", placeholder: "documents/" },
  ],
  azure: [
    { key: "storage_account", label: "Storage Account", placeholder: "bonitokb{org}" },
    { key: "container_name", label: "Container Name", placeholder: "documents" },
  ],
  gcp: [
    { key: "bucket", label: "GCS Bucket Name", placeholder: "bonito-kb-{org}" },
    { key: "prefix", label: "Prefix (folder)", placeholder: "documents/" },
  ],
};

const DOC_STORAGE_PROVIDERS: { id: string; name: string; icon: string }[] = [
  { id: "aws", name: "Amazon S3", icon: "☁️" },
  { id: "azure", name: "Azure Blob Storage", icon: "🔷" },
  { id: "gcp", name: "Google Cloud Storage", icon: "🌐" },
];

// IAM Policy JSON for quick reference
const IAM_POLICIES: Record<Provider, string> = {
  aws: JSON.stringify({
    Version: "2012-10-17",
    Statement: [
      {
        Sid: "BedrockAccess",
        Effect: "Allow",
        Action: ["bedrock:ListFoundationModels", "bedrock:GetFoundationModel", "bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        Resource: "*",
      },
      {
        Sid: "CostExplorerReadOnly",
        Effect: "Allow",
        Action: ["ce:GetCostAndUsage", "ce:GetCostForecast", "ce:GetDimensionValues"],
        Resource: "*",
      },
      {
        Sid: "STSValidation",
        Effect: "Allow",
        Action: ["sts:GetCallerIdentity"],
        Resource: "*",
      },
    ],
  }, null, 2),
  azure: `Required Azure RBAC roles:
• Cognitive Services User (on AI Services resource group)
• Cost Management Reader (on subscription)
• Reader (on subscription)`,
  gcp: `Required GCP IAM roles:
• roles/aiplatform.user (Vertex AI User)
• roles/billing.viewer (Billing Viewer)
• roles/monitoring.viewer (Monitoring Viewer)`,
  openai: `No IAM setup needed — just an API key.
Get yours at platform.openai.com/api-keys`,
  anthropic: `No IAM setup needed — just an API key.
Get yours at console.anthropic.com/settings/keys`,
};


export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0); // 0=welcome, 1=connect, 2=success
  const [providers, setProviders] = useState<Provider[]>([]);
  const [path, setPath] = useState<OnboardingPath>(null);
  const [showConfetti, setShowConfetti] = useState(false);

  // Quick connect state
  const [activeProvider, setActiveProvider] = useState<Provider | null>(null);
  const [credInputs, setCredInputs] = useState<Record<string, Record<string, string>>>({});
  const [permChecks, setPermChecks] = useState<Record<string, PermissionCheck[]>>({});
  const [validated, setValidated] = useState<Record<string, boolean>>({});
  const [validating, setValidating] = useState(false);
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [expandedPolicy, setExpandedPolicy] = useState<string | null>(null);

  // AI Context state
  const [kbEnabled, setKbEnabled] = useState(false);
  const [kbProvider, setKbProvider] = useState<Provider | null>(null);
  const [kbConfig, setKbConfig] = useState<Record<string, string>>({});

  // IaC state
  const [iacTool, setIacTool] = useState<IaCTool | null>(null);
  const [iacResults, setIacResults] = useState<Record<Provider, IaCResult | null>>({} as any);
  const [iacLoading, setIacLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeFile, setActiveFile] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const toggleProvider = (p: Provider) => {
    const next = providers.includes(p) ? providers.filter((x) => x !== p) : [...providers, p];
    setProviders(next);
  };

  const initPermChecks = (provider: Provider) => {
    const checks = REQUIRED_PERMISSIONS[provider].map((p) => ({
      name: p.name,
      description: p.description,
      status: "pending" as const,
    }));
    setPermChecks((prev) => ({ ...prev, [provider]: checks }));
  };

  const startQuickConnect = () => {
    setPath("quick");
    setStep(1);
    providers.forEach(initPermChecks);
    setActiveProvider(providers[0]);
  };

  const startIaCFlow = () => {
    setPath("iac");
    setStep(1);
  };

  const handleValidate = async (provider: Provider) => {
    const creds = credInputs[provider];
    if (!creds) return;
    setValidating(true);

    // Set all checks to "checking"
    setPermChecks((prev) => ({
      ...prev,
      [provider]: (prev[provider] || []).map((c) => ({ ...c, status: "checking" as const })),
    }));

    try {
      const res = await apiRequest(`/api/onboarding/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, credentials: creds }),
      });

      if (!res.ok) throw new Error("Validation request failed");
      const result: ValidationResult = await res.json();

      // Map health checks back to permission checks with staggered animation
      const healthChecks = result.health?.checks || [];
      const permDefs = REQUIRED_PERMISSIONS[provider];
      const updatedChecks: PermissionCheck[] = permDefs.map((perm) => {
        // Find matching health check
        const match = healthChecks.find((h) =>
          h.name.toLowerCase().includes(perm.key.toLowerCase()) ||
          perm.key.toLowerCase().includes(h.name.toLowerCase().split(" ")[0])
        );
        if (match) {
          return {
            name: perm.name,
            description: perm.description,
            status: match.status === "healthy" ? "pass" as const : match.status === "degraded" ? "warn" as const : "fail" as const,
            message: match.message,
          };
        }
        // Check permissions list
        const permMatch = result.permissions?.find((p) => p.toLowerCase().includes(perm.key));
        if (permMatch) {
          return {
            name: perm.name,
            description: perm.description,
            status: permMatch.includes("✅") ? "pass" as const : "fail" as const,
            message: permMatch,
          };
        }
        return { name: perm.name, description: perm.description, status: "pending" as const };
      });

      // Stagger the updates for visual effect
      for (let i = 0; i < updatedChecks.length; i++) {
        await new Promise((r) => setTimeout(r, 400));
        setPermChecks((prev) => {
          const checks = [...(prev[provider] || [])];
          checks[i] = updatedChecks[i];
          return { ...prev, [provider]: checks };
        });
      }

      if (result.valid) {
        setValidated((prev) => ({ ...prev, [provider]: true }));

        // Also persist credentials
        try {
          let backendCreds: Record<string, string> = { ...creds };
          if (provider === "aws" && !backendCreds.region) backendCreds.region = "us-east-1";
          if (provider === "gcp") {
            if (backendCreds.key_file && !backendCreds.service_account_json) {
              backendCreds.service_account_json = backendCreds.key_file;
              delete backendCreds.key_file;
            }
            delete backendCreds.service_account_email;
          }
          if (provider === "azure") {
            if (backendCreds.resource_group_name && !backendCreds.resource_group) {
              backendCreds.resource_group = backendCreds.resource_group_name;
              delete backendCreds.resource_group_name;
            }
          }
          await apiRequest(`/api/providers/connect`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ provider_type: provider, credentials: backendCreds }),
          });
        } catch {
          // Silent — credentials validated but persist failed
        }

        // Check if ALL selected providers are validated
        const allValidated = providers.every((p) => p === provider ? true : validated[p]);
        if (allValidated) {
          await new Promise((r) => setTimeout(r, 600));
          setShowConfetti(true);
        }
      }
    } catch {
      setPermChecks((prev) => ({
        ...prev,
        [provider]: (prev[provider] || []).map((c) => ({
          ...c,
          status: "fail" as const,
          message: "Connection failed — check your credentials",
        })),
      }));
    } finally {
      setValidating(false);
    }
  };

  const handleFileUpload = (provider: Provider, key: string, file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      setCredInputs((prev) => ({
        ...prev,
        [provider]: { ...prev[provider], [key]: e.target?.result as string },
      }));
    };
    reader.readAsText(file);
  };

  const handleGenerateIaC = async (provider: Provider) => {
    if (!iacTool) return;
    setActiveProvider(provider);
    setIacLoading(true);
    try {
      const kbPayload: Record<string, unknown> = {};
      if (kbEnabled && kbProvider && kbProvider === provider) {
        kbPayload.enable_knowledge_base = true;
        if (kbProvider === "aws") {
          kbPayload.kb_bucket_name = kbConfig.bucket || "";
          kbPayload.kb_prefix = kbConfig.prefix || "";
        } else if (kbProvider === "azure") {
          kbPayload.kb_bucket_name = kbConfig.storage_account || "";
          kbPayload.kb_prefix = kbConfig.container_name || "";
        } else if (kbProvider === "gcp") {
          kbPayload.kb_bucket_name = kbConfig.bucket || "";
          kbPayload.kb_prefix = kbConfig.prefix || "";
        }
      }
      const res = await apiRequest(`/api/onboarding/generate-iac`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider, iac_tool: iacTool, ...kbPayload }),
      });
      if (!res.ok) throw new Error("Failed to generate");
      const result = await res.json();
      setIacResults((prev) => ({ ...prev, [provider]: result }));
      if (result.files?.length) setActiveFile(result.files[0].filename);
    } catch {
      // Silent
    } finally {
      setIacLoading(false);
    }
  };

  const handleDownloadZip = async (provider: Provider) => {
    if (!iacTool) return;
    setDownloading(true);
    try {
      const res = await apiRequest(`/api/onboarding/download-iac?provider=${provider}&tool=${iacTool}`);
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bonito-${provider}-${iacTool}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {} finally {
      setDownloading(false);
    }
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getDisplayCode = (result: IaCResult): string => {
    if (activeFile && result.files?.length) {
      const file = result.files.find((f) => f.filename === activeFile);
      if (file) return file.content;
    }
    return result.code;
  };

  const allProvidersValidated = providers.length > 0 && providers.every((p) => validated[p]);

  const goToDashboard = () => {
    router.push("/dashboard");
  };

  // Progress percentage
  const progressPct = step === 0 ? 33 : step === 1 ? 66 : 100;

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Confetti overlay */}
        {showConfetti && (
          <div className="fixed inset-0 pointer-events-none z-50">
            {[...Array(60)].map((_, i) => (
              <motion.div
                key={i}
                className="absolute w-2 h-2 rounded-full"
                style={{
                  left: `${Math.random() * 100}%`,
                  backgroundColor: ["#8b5cf6", "#d946ef", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"][i % 6],
                }}
                initial={{ top: "-5%", opacity: 1, scale: 1 }}
                animate={{
                  top: `${100 + Math.random() * 20}%`,
                  opacity: 0,
                  rotate: Math.random() * 720 - 360,
                  x: Math.random() * 200 - 100,
                }}
                transition={{ duration: 2 + Math.random() * 2, delay: Math.random() * 0.5, ease: "easeOut" }}
              />
            ))}
          </div>
        )}

        {/* Progress bar */}
        <div className="mb-8">
          <div className="h-1 bg-accent rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-violet-600 to-fuchsia-500"
              animate={{ width: `${progressPct}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        <AnimatePresence mode="wait">
          {/* ═══════════════ STEP 0: WELCOME ═══════════════ */}
          {step === 0 && (
            <motion.div key="welcome" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-8">
              <div className="text-center space-y-3">
                <h1 className="text-3xl font-bold">
                  Welcome to{" "}
                  <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">
                    Bonito
                  </span>
                </h1>
                <p className="text-muted-foreground text-lg">
                  Connect your cloud providers to get started. Select one or more.
                </p>
              </div>

              {/* Provider cards */}
              <div className="grid gap-4 md:grid-cols-3">
                {PROVIDERS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => toggleProvider(p.id)}
                    className={cn(
                      "relative rounded-xl border-2 p-6 text-left transition-all hover:scale-[1.02]",
                      providers.includes(p.id)
                        ? "border-violet-500 bg-violet-500/10"
                        : "border-border hover:border-violet-500/50"
                    )}
                  >
                    {providers.includes(p.id) && (
                      <div className="absolute top-3 right-3">
                        <Check className="h-5 w-5 text-violet-400" />
                      </div>
                    )}
                    <div className="text-3xl mb-3">{p.icon}</div>
                    <h3 className="font-semibold text-lg">{p.name}</h3>
                    <p className="text-sm text-muted-foreground mt-1">{p.desc}</p>
                  </button>
                ))}
              </div>

              {/* Two paths */}
              {providers.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-2 max-w-2xl mx-auto">
                    <button
                      onClick={startQuickConnect}
                      className="flex items-center gap-4 rounded-xl border-2 border-violet-500 bg-violet-500/10 p-5 text-left transition-all hover:bg-violet-500/20"
                    >
                      <div className="rounded-lg bg-violet-500/20 p-3">
                        <Zap className="h-6 w-6 text-violet-400" />
                      </div>
                      <div>
                        <h3 className="font-semibold">Already have credentials?</h3>
                        <p className="text-sm text-muted-foreground">Paste your keys — connect in seconds</p>
                      </div>
                      <ArrowRight className="h-5 w-5 text-violet-400 ml-auto" />
                    </button>

                    <button
                      onClick={startIaCFlow}
                      className="flex items-center gap-4 rounded-xl border-2 border-border p-5 text-left transition-all hover:border-violet-500/50"
                    >
                      <div className="rounded-lg bg-accent p-3">
                        <FileCode className="h-6 w-6 text-muted-foreground" />
                      </div>
                      <div>
                        <h3 className="font-semibold">Need to create credentials?</h3>
                        <p className="text-sm text-muted-foreground">We'll generate Terraform / CloudFormation</p>
                      </div>
                      <ArrowRight className="h-5 w-5 text-muted-foreground ml-auto" />
                    </button>
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* ═══════════════ STEP 1: QUICK CONNECT ═══════════════ */}
          {step === 1 && path === "quick" && (
            <motion.div key="quick" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-6">
              <div className="text-center space-y-2">
                <h2 className="text-2xl font-bold">Connect Your Providers</h2>
                <p className="text-muted-foreground">Paste your credentials and we'll validate each permission in real time.</p>
              </div>

              {/* Provider tabs */}
              {providers.length > 1 && (
                <div className="flex gap-2 justify-center">
                  {providers.map((p) => (
                    <button
                      key={p}
                      onClick={() => { setActiveProvider(p); if (!permChecks[p]) initPermChecks(p); }}
                      className={cn(
                        "px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2",
                        activeProvider === p
                          ? "bg-violet-500 text-white"
                          : "bg-accent text-muted-foreground hover:bg-accent/80"
                      )}
                    >
                      {validated[p] && <CheckCircle2 className="h-4 w-4 text-green-400" />}
                      {p.toUpperCase()}
                    </button>
                  ))}
                </div>
              )}

              {activeProvider && (
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Left: Credential form */}
                  <div className="space-y-4">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Key className="h-4 w-4 text-violet-400" />
                      {activeProvider.toUpperCase()} Credentials
                    </h3>

                    {CRED_FIELDS[activeProvider].map((field) => (
                      <div key={field.key}>
                        <label className="text-sm text-muted-foreground mb-1 flex items-center gap-1.5">
                          {field.label}
                          {field.required && <span className="text-red-400">*</span>}
                        </label>
                        {field.type === "file" ? (
                          <div className="space-y-2">
                            <label className="flex items-center justify-center gap-2 w-full rounded-md border border-dashed bg-zinc-950/50 px-3 py-4 text-sm cursor-pointer hover:border-violet-500/50 transition-colors">
                              <Upload className="h-4 w-4 text-muted-foreground" />
                              <span className="text-muted-foreground">
                                {credInputs[activeProvider]?.[field.key] ? "File loaded ✓" : "Upload JSON key file"}
                              </span>
                              <input
                                type="file"
                                accept=".json"
                                className="hidden"
                                onChange={(e) => {
                                  const f = e.target.files?.[0];
                                  if (f) handleFileUpload(activeProvider, field.key, f);
                                }}
                              />
                            </label>
                            <textarea
                              className="w-full rounded-md border bg-zinc-950 px-3 py-2 text-sm font-mono min-h-[80px]"
                              placeholder="Or paste JSON key contents..."
                              value={credInputs[activeProvider]?.[field.key] || ""}
                              onChange={(e) =>
                                setCredInputs((prev) => ({
                                  ...prev,
                                  [activeProvider!]: { ...prev[activeProvider!], [field.key]: e.target.value },
                                }))
                              }
                            />
                          </div>
                        ) : (
                          <div className="relative">
                            <input
                              type={field.type === "password" && !showPasswords[field.key] ? "password" : "text"}
                              className="w-full rounded-md border bg-zinc-950 px-3 py-2 text-sm font-mono pr-10"
                              placeholder={field.placeholder}
                              value={credInputs[activeProvider]?.[field.key] || ""}
                              onChange={(e) =>
                                setCredInputs((prev) => ({
                                  ...prev,
                                  [activeProvider!]: { ...prev[activeProvider!], [field.key]: e.target.value },
                                }))
                              }
                            />
                            {field.type === "password" && (
                              <button
                                onClick={() => setShowPasswords((p) => ({ ...p, [field.key]: !p[field.key] }))}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                              >
                                {showPasswords[field.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    ))}

                    <button
                      onClick={() => handleValidate(activeProvider)}
                      disabled={validating || validated[activeProvider]}
                      className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {validating ? (
                        <><Loader2 className="h-4 w-4 animate-spin" /> Validating...</>
                      ) : validated[activeProvider] ? (
                        <><CheckCircle2 className="h-4 w-4" /> Connected</>
                      ) : (
                        <><Shield className="h-4 w-4" /> Validate & Connect</>
                      )}
                    </button>
                  </div>

                  {/* Right: Permission checklist */}
                  <div className="space-y-4">
                    <h3 className="font-semibold flex items-center gap-2">
                      <Shield className="h-4 w-4 text-violet-400" />
                      Permission Checks
                    </h3>

                    <div className="rounded-lg border bg-card p-4 space-y-3">
                      {(permChecks[activeProvider] || REQUIRED_PERMISSIONS[activeProvider].map((p) => ({
                        name: p.name,
                        description: p.description,
                        status: "pending" as const,
                      }))).map((check, i) => (
                        <motion.div
                          key={check.name}
                          className="flex items-start gap-3"
                          initial={false}
                          animate={check.status === "pass" ? { scale: [1, 1.02, 1] } : {}}
                          transition={{ duration: 0.3 }}
                        >
                          <div className="mt-0.5">
                            {check.status === "pending" && (
                              <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                            )}
                            {check.status === "checking" && (
                              <Loader2 className="h-5 w-5 text-violet-400 animate-spin" />
                            )}
                            {check.status === "pass" && (
                              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 500 }}>
                                <CheckCircle2 className="h-5 w-5 text-green-400" />
                              </motion.div>
                            )}
                            {check.status === "warn" && (
                              <AlertCircle className="h-5 w-5 text-yellow-400" />
                            )}
                            {check.status === "fail" && (
                              <AlertCircle className="h-5 w-5 text-red-400" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className={cn(
                              "text-sm font-medium",
                              check.status === "pass" && "text-green-400",
                              check.status === "fail" && "text-red-400",
                              check.status === "warn" && "text-yellow-400",
                            )}>
                              {check.name}
                            </p>
                            <p className="text-xs text-muted-foreground">{check.description}</p>
                            {check.message && check.status !== "pending" && (
                              <p className={cn(
                                "text-xs mt-0.5",
                                check.status === "pass" && "text-green-400/70",
                                check.status === "fail" && "text-red-400/70",
                                check.status === "warn" && "text-yellow-400/70",
                              )}>
                                {check.message}
                              </p>
                            )}
                          </div>
                        </motion.div>
                      ))}
                    </div>

                    {/* Required permissions reference */}
                    <div className="space-y-2">
                      <button
                        onClick={() => setExpandedPolicy(expandedPolicy === activeProvider ? null : activeProvider)}
                        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                      >
                        {expandedPolicy === activeProvider ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                        What permissions does Bonito need?
                      </button>

                      <AnimatePresence>
                        {expandedPolicy === activeProvider && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden"
                          >
                            <div className="rounded-lg border bg-zinc-950 overflow-hidden">
                              <div className="flex items-center justify-between px-3 py-2 border-b bg-zinc-900/50">
                                <span className="text-xs text-muted-foreground font-mono">
                                  {activeProvider === "aws" ? "IAM Policy JSON" : "Required Roles"}
                                </span>
                                <button
                                  onClick={() => copyCode(IAM_POLICIES[activeProvider])}
                                  className="text-xs px-2 py-0.5 rounded bg-violet-600 hover:bg-violet-500 text-white"
                                >
                                  {copied ? "Copied!" : "Copy"}
                                </button>
                              </div>
                              <pre className="p-3 text-xs overflow-x-auto max-h-48 text-zinc-400">
                                <code>{IAM_POLICIES[activeProvider]}</code>
                              </pre>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </div>
              )}

              {/* Success state — all providers connected */}
              {allProvidersValidated && showConfetti && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-center space-y-6 pt-4"
                >
                  <div className="flex flex-wrap gap-3 justify-center">
                    {providers.map((p) => (
                      <div key={p} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400">
                        <CheckCircle2 className="h-4 w-4" />
                        {p.toUpperCase()} Connected
                      </div>
                    ))}
                  </div>

                  {/* Knowledge Base toggle — optional */}
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className="max-w-2xl mx-auto text-left space-y-4"
                  >
                    <button
                      onClick={() => setKbEnabled(!kbEnabled)}
                      className={cn(
                        "w-full flex items-center gap-4 rounded-xl border-2 p-5 text-left transition-all",
                        kbEnabled
                          ? "border-violet-500 bg-violet-500/10"
                          : "border-border hover:border-violet-500/50"
                      )}
                    >
                      <div className={cn(
                        "rounded-lg p-3",
                        kbEnabled ? "bg-violet-500/20" : "bg-accent"
                      )}>
                        <Database className={cn("h-6 w-6", kbEnabled ? "text-violet-400" : "text-muted-foreground")} />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold">AI Context</h3>
                        <p className="text-sm text-muted-foreground">
                          Give your models context from your own documents
                        </p>
                      </div>
                      <div className={cn(
                        "w-11 h-6 rounded-full transition-colors flex items-center px-0.5",
                        kbEnabled ? "bg-violet-500" : "bg-zinc-700"
                      )}>
                        <motion.div
                          className="w-5 h-5 rounded-full bg-white"
                          animate={{ x: kbEnabled ? 20 : 0 }}
                          transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        />
                      </div>
                    </button>

                    <AnimatePresence>
                      {kbEnabled && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden space-y-4"
                        >
                          {/* Pick ONE storage provider */}
                          <div className="space-y-2">
                            <p className="text-sm text-muted-foreground">Where are your documents stored?</p>
                            <div className="flex gap-2">
                              {providers.filter((p) => ["aws", "azure", "gcp"].includes(p)).map((p) => (
                                <button
                                  key={p}
                                  onClick={() => { setKbProvider(p); setKbConfig({}); }}
                                  className={cn(
                                    "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                                    kbProvider === p
                                      ? "bg-violet-500 text-white"
                                      : "bg-accent text-muted-foreground hover:bg-accent/80"
                                  )}
                                >
                                  {p === "aws" ? "Amazon S3" : p === "azure" ? "Azure Blob" : "Google Cloud Storage"}
                                </button>
                              ))}
                            </div>
                          </div>

                          {/* Storage config for chosen provider */}
                          {kbProvider && (
                            <motion.div
                              initial={{ opacity: 0, y: 5 }}
                              animate={{ opacity: 1, y: 0 }}
                              className="rounded-lg border bg-card p-4 space-y-3"
                            >
                              <h4 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                                <BookOpen className="h-4 w-4 text-violet-400" />
                                {kbProvider === "aws" ? "S3" : kbProvider === "azure" ? "Azure Blob" : "GCS"} Configuration
                              </h4>
                              <div className="grid gap-3 sm:grid-cols-2">
                                {KB_FIELDS[kbProvider]?.map((field) => (
                                  <div key={field.key}>
                                    <label className="text-xs text-muted-foreground mb-1 block">{field.label}</label>
                                    <input
                                      type="text"
                                      className="w-full rounded-md border bg-zinc-950 px-3 py-2 text-sm font-mono"
                                      placeholder={field.placeholder}
                                      value={kbConfig[field.key] || ""}
                                      onChange={(e) =>
                                        setKbConfig((prev) => ({ ...prev, [field.key]: e.target.value }))
                                      }
                                    />
                                  </div>
                                ))}
                              </div>
                            </motion.div>
                          )}

                          <p className="text-xs text-muted-foreground bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2">
                            💡 You can configure AI Context later from the dashboard. Storage read permissions are included in the IaC code when enabled.
                          </p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>

                  <button
                    onClick={goToDashboard}
                    className="px-8 py-3 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-500 text-white font-semibold text-lg hover:opacity-90 transition-opacity"
                  >
                    Go to Dashboard <ArrowRight className="inline h-5 w-5 ml-1" />
                  </button>
                </motion.div>
              )}

              {/* Back button */}
              <div className="flex items-center justify-between">
                <button
                  onClick={() => { setStep(0); setPath(null); }}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ArrowLeft className="h-4 w-4" /> Back
                </button>
              </div>
            </motion.div>
          )}

          {/* ═══════════════ STEP 1: IAC FLOW ═══════════════ */}
          {step === 1 && path === "iac" && (
            <motion.div key="iac" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="space-y-6">
              {/* IaC tool selection (if not picked yet) */}
              {!iacTool ? (
                <div className="space-y-6">
                  <div className="text-center space-y-3">
                    <h2 className="text-2xl font-bold">Choose Your Setup Tool</h2>
                    <p className="text-muted-foreground">
                      We'll generate production-tested infrastructure code with least-privilege access.
                    </p>
                  </div>

                  <div className="grid gap-3 max-w-2xl mx-auto">
                    {IAC_TOOLS.filter((t) => providers.some((p) => t.providers.includes(p))).map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setIacTool(t.id)}
                        className="flex items-center gap-4 rounded-lg border-2 border-border p-4 text-left transition-all hover:border-violet-500/50"
                      >
                        <div className="rounded-lg p-2 bg-accent text-muted-foreground">{t.icon}</div>
                        <div className="flex-1">
                          <h3 className="font-semibold">{t.name}</h3>
                          <p className="text-sm text-muted-foreground">{t.desc}</p>
                        </div>
                        <div className="flex gap-1">
                          {t.providers.filter((p) => providers.includes(p as Provider)).map((p) => (
                            <span key={p} className="text-xs px-1.5 py-0.5 rounded bg-accent text-muted-foreground">
                              {p.toUpperCase()}
                            </span>
                          ))}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Code view */
                <div className="space-y-6">
                  <div className="text-center space-y-3">
                    <h2 className="text-2xl font-bold">Run This Code</h2>
                    <p className="text-muted-foreground">
                      Enterprise-secure templates with least-privilege IAM. Download or copy.
                    </p>
                  </div>

                  {/* Provider tabs */}
                  <div className="flex gap-2 justify-center">
                    {providers.map((p) => (
                      <button
                        key={p}
                        onClick={() => { setActiveProvider(p); if (!iacResults[p]) handleGenerateIaC(p); }}
                        className={cn(
                          "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                          activeProvider === p ? "bg-violet-500 text-white" : "bg-accent text-muted-foreground hover:bg-accent/80"
                        )}
                      >
                        {p.toUpperCase()}
                      </button>
                    ))}
                  </div>

                  {/* Knowledge Base toggle for IaC flow */}
                  {providers.some((p) => ["aws", "azure", "gcp"].includes(p)) && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="max-w-2xl mx-auto space-y-4"
                    >
                      <button
                        onClick={() => {
                          setKbEnabled(!kbEnabled);
                          // Clear cached IaC results so they regenerate with/without KB
                          setIacResults({} as any);
                          if (activeProvider) {
                            setTimeout(() => handleGenerateIaC(activeProvider), 100);
                          }
                        }}
                        className={cn(
                          "w-full flex items-center gap-4 rounded-xl border-2 p-4 text-left transition-all",
                          kbEnabled
                            ? "border-violet-500 bg-violet-500/10"
                            : "border-border hover:border-violet-500/50"
                        )}
                      >
                        <div className={cn(
                          "rounded-lg p-2.5",
                          kbEnabled ? "bg-violet-500/20" : "bg-accent"
                        )}>
                          <Database className={cn("h-5 w-5", kbEnabled ? "text-violet-400" : "text-muted-foreground")} />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-sm">AI Context</h3>
                          <p className="text-xs text-muted-foreground">
                            Include storage read permissions for document sync
                          </p>
                        </div>
                        <div className={cn(
                          "w-11 h-6 rounded-full transition-colors flex items-center px-0.5",
                          kbEnabled ? "bg-violet-500" : "bg-zinc-700"
                        )}>
                          <motion.div
                            className="w-5 h-5 rounded-full bg-white"
                            animate={{ x: kbEnabled ? 20 : 0 }}
                            transition={{ type: "spring", stiffness: 500, damping: 30 }}
                          />
                        </div>
                      </button>

                      <AnimatePresence>
                        {kbEnabled && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="overflow-hidden space-y-3"
                          >
                            {/* Pick ONE storage provider */}
                            <div className="space-y-2">
                              <p className="text-xs text-muted-foreground">Where are your documents stored?</p>
                              <div className="flex gap-2">
                                {providers.filter((p) => ["aws", "azure", "gcp"].includes(p)).map((p) => (
                                  <button
                                    key={p}
                                    onClick={() => {
                                      setKbProvider(p);
                                      setKbConfig({});
                                      // Regenerate IaC for the active provider with KB settings
                                      setIacResults({} as any);
                                      if (activeProvider) setTimeout(() => handleGenerateIaC(activeProvider), 100);
                                    }}
                                    className={cn(
                                      "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                                      kbProvider === p
                                        ? "bg-violet-500 text-white"
                                        : "bg-accent text-muted-foreground hover:bg-accent/80"
                                    )}
                                  >
                                    {p === "aws" ? "Amazon S3" : p === "azure" ? "Azure Blob" : "Google Cloud Storage"}
                                  </button>
                                ))}
                              </div>
                            </div>

                            {kbProvider && (
                              <div className="rounded-lg border bg-card p-4 space-y-3">
                                <h4 className="text-sm font-semibold text-muted-foreground flex items-center gap-2">
                                  <BookOpen className="h-4 w-4 text-violet-400" />
                                  {kbProvider === "aws" ? "S3" : kbProvider === "azure" ? "Azure Blob" : "GCS"} Configuration
                                </h4>
                                <div className="grid gap-3 sm:grid-cols-2">
                                  {KB_FIELDS[kbProvider]?.map((field) => (
                                    <div key={field.key}>
                                      <label className="text-xs text-muted-foreground mb-1 block">{field.label}</label>
                                      <input
                                        type="text"
                                        className="w-full rounded-md border bg-zinc-950 px-3 py-2 text-sm font-mono"
                                        placeholder={field.placeholder}
                                        value={kbConfig[field.key] || ""}
                                        onChange={(e) =>
                                          setKbConfig((prev) => ({ ...prev, [field.key]: e.target.value }))
                                        }
                                      />
                                    </div>
                                  ))}
                                </div>
                                <p className="text-xs text-muted-foreground bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2">
                                  💡 The generated IaC code includes storage read permissions when AI Context is enabled. Re-download if you&apos;ve already applied it.
                                </p>
                              </div>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </motion.div>
                  )}

                  {activeProvider && iacResults[activeProvider] ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-3 justify-end">
                        <button
                          onClick={() => handleDownloadZip(activeProvider)}
                          disabled={downloading}
                          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
                        >
                          {downloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                          Download ZIP
                        </button>
                      </div>

                      {/* File tabs */}
                      {iacResults[activeProvider]!.files?.length > 1 && (
                        <div className="flex gap-1 border-b overflow-x-auto">
                          {iacResults[activeProvider]!.files.map((f) => (
                            <button
                              key={f.filename}
                              onClick={() => setActiveFile(f.filename)}
                              className={cn(
                                "px-3 py-1.5 text-xs font-mono rounded-t transition-colors whitespace-nowrap",
                                activeFile === f.filename
                                  ? "bg-zinc-950 text-zinc-300 border border-b-0 border-border"
                                  : "text-muted-foreground hover:text-foreground"
                              )}
                            >
                              {f.filename}
                            </button>
                          ))}
                        </div>
                      )}

                      <div className="relative rounded-lg border bg-zinc-950 overflow-hidden">
                        <div className="flex items-center justify-between px-4 py-2 border-b bg-zinc-900/50">
                          <span className="text-sm text-muted-foreground font-mono">
                            {activeFile || iacResults[activeProvider]!.filename}
                          </span>
                          <button
                            onClick={() => copyCode(getDisplayCode(iacResults[activeProvider]!))}
                            className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded bg-violet-600 hover:bg-violet-500 text-white"
                          >
                            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                            {copied ? "Copied!" : "Copy"}
                          </button>
                        </div>
                        <pre className="p-4 text-sm overflow-x-auto max-h-96 text-zinc-300">
                          <code>{getDisplayCode(iacResults[activeProvider]!)}</code>
                        </pre>
                      </div>

                      {/* Instructions */}
                      <div className="rounded-lg border p-4 space-y-3">
                        <h3 className="font-semibold flex items-center gap-2">
                          <Terminal className="h-4 w-4 text-violet-400" /> Instructions
                        </h3>
                        <ol className="space-y-2 text-sm">
                          {iacResults[activeProvider]!.instructions.map((inst, i) => (
                            <li key={i} className="flex gap-2">
                              <span className="text-violet-400 font-mono text-xs mt-0.5">{i + 1}.</span>
                              <span className="text-muted-foreground">{inst}</span>
                            </li>
                          ))}
                        </ol>
                      </div>

                      {/* Security notes */}
                      <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-4 space-y-2">
                        <h3 className="font-semibold flex items-center gap-2 text-green-400">
                          <Shield className="h-4 w-4" /> Security
                        </h3>
                        <ul className="space-y-1 text-sm text-muted-foreground">
                          {iacResults[activeProvider]!.security_notes.map((note, i) => (
                            <li key={i}>{note}</li>
                          ))}
                        </ul>
                      </div>

                      {/* After running Terraform, validate */}
                      <div className="rounded-lg border border-violet-500/20 bg-violet-500/5 p-4 text-center space-y-3">
                        <p className="text-sm text-muted-foreground">
                          After running the code, paste your credentials to connect:
                        </p>
                        <button
                          onClick={() => { setPath("quick"); providers.forEach(initPermChecks); }}
                          className="px-6 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium transition-colors"
                        >
                          <Key className="inline h-4 w-4 mr-2" />
                          Enter Credentials
                        </button>
                      </div>
                    </div>
                  ) : activeProvider && iacLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
                    </div>
                  ) : (
                    <div className="text-center py-12 text-muted-foreground">
                      Select a provider tab above to generate code.
                    </div>
                  )}

                  {/* Auto-generate for first provider */}
                  {!activeProvider && providers.length > 0 && (() => {
                    setTimeout(() => { setActiveProvider(providers[0]); handleGenerateIaC(providers[0]); }, 100);
                    return null;
                  })()}
                </div>
              )}

              <div className="flex items-center justify-between">
                <button
                  onClick={() => { if (iacTool) { setIacTool(null); } else { setStep(0); setPath(null); } }}
                  className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  <ArrowLeft className="h-4 w-4" /> Back
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
