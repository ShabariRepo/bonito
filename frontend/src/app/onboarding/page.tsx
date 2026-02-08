"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { StepWizard } from "@/components/ui/step-wizard";
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
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Rocket,
  Activity,
  Upload,
  Heart,
} from "lucide-react";
import { cn } from "@/lib/utils";

// --- Types ---
type Provider = "aws" | "azure" | "gcp";
type IaCTool = "terraform" | "pulumi" | "cloudformation" | "bicep" | "manual";

interface OnboardingState {
  current_step: number;
  completed: boolean;
  selected_providers: Provider[];
  selected_iac_tool: IaCTool | null;
  provider_credentials_validated: Record<string, boolean>;
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

interface HealthCheck {
  name: string;
  status: "healthy" | "degraded" | "error";
  message: string;
}

interface ConnectionHealth {
  provider: string;
  status: "healthy" | "degraded" | "error";
  checks: HealthCheck[];
  checked_at: string;
}

interface ValidationResult {
  valid: boolean;
  identity?: string;
  permissions?: string[];
  errors?: string[];
  health?: ConnectionHealth;
}

// --- Constants ---
const STEPS = [
  { title: "Welcome", description: "Choose your cloud providers" },
  { title: "IaC Tool", description: "Pick your infrastructure tool" },
  { title: "Setup Code", description: "Generate and run the code" },
  { title: "Credentials", description: "Validate your connection" },
  { title: "Complete", description: "You're all set!" },
];

const PROVIDERS: { id: Provider; name: string; icon: string; color: string; desc: string }[] = [
  { id: "aws", name: "AWS", icon: "☁️", color: "from-orange-500 to-yellow-500", desc: "Amazon Bedrock — Claude, Llama, Titan" },
  { id: "azure", name: "Azure", icon: "🔷", color: "from-blue-500 to-cyan-500", desc: "Azure AI Foundry — GPT-4o, Phi, Mistral" },
  { id: "gcp", name: "Google Cloud", icon: "🌐", color: "from-green-500 to-emerald-500", desc: "Vertex AI — Gemini, PaLM, Claude" },
];

const IAC_TOOLS: { id: IaCTool; name: string; icon: React.ReactNode; desc: string; providers: Provider[] }[] = [
  { id: "terraform", name: "Terraform", icon: <FileCode className="h-5 w-5" />, desc: "HashiCorp Terraform (HCL)", providers: ["aws", "azure", "gcp"] },
  { id: "pulumi", name: "Pulumi", icon: <FileCode className="h-5 w-5" />, desc: "Pulumi (Python)", providers: ["aws", "azure", "gcp"] },
  { id: "cloudformation", name: "CloudFormation", icon: <Cloud className="h-5 w-5" />, desc: "AWS CloudFormation (YAML)", providers: ["aws"] },
  { id: "bicep", name: "Bicep", icon: <FileCode className="h-5 w-5" />, desc: "Azure Bicep", providers: ["azure"] },
  { id: "manual", name: "Manual Setup", icon: <Terminal className="h-5 w-5" />, desc: "Step-by-step CLI instructions", providers: ["aws", "azure", "gcp"] },
];

// Credential fields per provider — matched to Terraform output names
const CRED_FIELDS: Record<Provider, { key: string; label: string; type?: string; placeholder?: string; required?: boolean }[]> = {
  aws: [
    { key: "access_key_id", label: "Access Key ID", placeholder: "AKIA...", required: true },
    { key: "secret_access_key", label: "Secret Access Key", type: "password", placeholder: "terraform output secret_access_key", required: true },
    { key: "role_arn", label: "Role ARN", placeholder: "arn:aws:iam::123456789:role/bonito-role (from terraform output role_arn)" },
  ],
  azure: [
    { key: "tenant_id", label: "Tenant ID", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", required: true },
    { key: "client_id", label: "Client ID", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", required: true },
    { key: "client_secret", label: "Client Secret", type: "password", placeholder: "terraform output client_secret", required: true },
    { key: "subscription_id", label: "Subscription ID", placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", required: true },
    { key: "resource_group_name", label: "Resource Group Name", placeholder: "rg-bonito-production" },
  ],
  gcp: [
    { key: "project_id", label: "Project ID", placeholder: "my-project-123" },
    { key: "service_account_email", label: "Service Account Email", placeholder: "bonito-sa@project.iam.gserviceaccount.com" },
    { key: "key_file", label: "Service Account Key (JSON)", type: "file", placeholder: "Upload or paste the JSON key file", required: true },
  ],
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

// --- API helpers ---
async function fetchProgress(token: string): Promise<OnboardingState> {
  const res = await fetch(`${API_BASE}/onboarding/progress`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to fetch progress");
  return res.json();
}

async function saveProgress(token: string, data: Partial<OnboardingState>): Promise<OnboardingState> {
  const res = await fetch(`${API_BASE}/onboarding/progress`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to save progress");
  return res.json();
}

async function generateIaC(
  token: string,
  provider: Provider,
  tool: IaCTool,
  opts?: Record<string, string>,
): Promise<IaCResult> {
  const res = await fetch(`${API_BASE}/onboarding/generate-iac`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ provider, iac_tool: tool, ...opts }),
  });
  if (!res.ok) throw new Error("Failed to generate IaC");
  return res.json();
}

async function downloadIaCZip(token: string, provider: Provider, tool: IaCTool): Promise<void> {
  const res = await fetch(
    `${API_BASE}/onboarding/download-iac?provider=${provider}&tool=${tool}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!res.ok) throw new Error("Failed to download");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `bonito-${provider}-${tool}.zip`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function validateCreds(
  token: string,
  provider: Provider,
  credentials: Record<string, string>,
): Promise<ValidationResult> {
  const res = await fetch(`${API_BASE}/onboarding/validate`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ provider, credentials }),
  });
  if (!res.ok) throw new Error("Failed to validate");
  return res.json();
}

// --- Main Component ---
export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [iacTool, setIacTool] = useState<IaCTool | null>(null);
  const [iacResults, setIacResults] = useState<Record<Provider, IaCResult | null>>({} as any);
  const [activeProvider, setActiveProvider] = useState<Provider | null>(null);
  const [validated, setValidated] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [credInputs, setCredInputs] = useState<Record<string, Record<string, string>>>({});
  const [validationResults, setValidationResults] = useState<Record<string, ValidationResult>>({});
  const [activeFile, setActiveFile] = useState<string | null>(null);

  // Load saved state on mount
  useEffect(() => {
    const token = localStorage.getItem("bonito_token");
    if (!token) return;
    fetchProgress(token)
      .then((state) => {
        if (state.completed) {
          router.push("/dashboard");
          return;
        }
        setStep(state.current_step - 1);
        if (state.selected_providers?.length) setProviders(state.selected_providers as Provider[]);
        if (state.selected_iac_tool) setIacTool(state.selected_iac_tool as IaCTool);
        if (state.provider_credentials_validated) setValidated(state.provider_credentials_validated);
      })
      .catch(() => {}); // First visit, no saved state
  }, [router]);

  const save = useCallback(
    (data: Partial<OnboardingState>) => {
      const token = localStorage.getItem("bonito_token");
      if (token) saveProgress(token, data).catch(() => {});
    },
    [],
  );

  const goNext = () => {
    const next = Math.min(step + 1, STEPS.length - 1);
    setStep(next);
    save({ current_step: next + 1 });
  };

  const goBack = () => {
    const prev = Math.max(step - 1, 0);
    setStep(prev);
    save({ current_step: prev + 1 });
  };

  const toggleProvider = (p: Provider) => {
    const next = providers.includes(p) ? providers.filter((x) => x !== p) : [...providers, p];
    setProviders(next);
    save({ selected_providers: next });
  };

  const selectIacTool = (t: IaCTool) => {
    setIacTool(t);
    save({ selected_iac_tool: t });
  };

  const handleGenerateIaC = async (provider: Provider) => {
    if (!iacTool) return;
    setActiveProvider(provider);
    setLoading(true);
    try {
      const token = localStorage.getItem("bonito_token") || "";
      const result = await generateIaC(token, provider, iacTool);
      setIacResults((prev) => ({ ...prev, [provider]: result }));
      // Default to first file tab
      if (result.files?.length) {
        setActiveFile(result.files[0].filename);
      }
    } catch {
      // Fallback: generate client-side preview
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadZip = async (provider: Provider) => {
    if (!iacTool) return;
    setDownloading(true);
    try {
      const token = localStorage.getItem("bonito_token") || "";
      await downloadIaCZip(token, provider, iacTool);
    } catch {
      // Silent fail — user can still copy-paste
    } finally {
      setDownloading(false);
    }
  };

  const [persistStatus, setPersistStatus] = useState<Record<string, string>>({});

  const handleValidate = async (provider: Provider) => {
    const creds = credInputs[provider];
    if (!creds) return;
    setLoading(true);
    try {
      const token = localStorage.getItem("bonito_token") || "";
      const result = await validateCreds(token, provider, creds);
      setValidationResults((prev) => ({ ...prev, [provider]: result }));
      if (result.valid) {
        // Persist credentials via POST /api/providers/connect AFTER successful validation
        setPersistStatus((prev) => ({ ...prev, [provider]: "saving" }));
        try {
          // Map frontend credential keys to backend expected keys
          let backendCreds: Record<string, string> = { ...creds };
          if (provider === "aws") {
            // Ensure region is set
            if (!backendCreds.region) backendCreds.region = "us-east-1";
          } else if (provider === "gcp") {
            // Map key_file → service_account_json
            if (backendCreds.key_file && !backendCreds.service_account_json) {
              backendCreds.service_account_json = backendCreds.key_file;
              delete backendCreds.key_file;
            }
            // Map service_account_email out (not expected by backend)
            delete backendCreds.service_account_email;
          } else if (provider === "azure") {
            // Map resource_group_name → resource_group
            if (backendCreds.resource_group_name && !backendCreds.resource_group) {
              backendCreds.resource_group = backendCreds.resource_group_name;
              delete backendCreds.resource_group_name;
            }
          }

          const connectRes = await fetch(`${API_BASE}/providers/connect`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              provider_type: provider,
              credentials: backendCreds,
            }),
          });
          if (connectRes.ok) {
            setPersistStatus((prev) => ({ ...prev, [provider]: "saved" }));
          } else {
            const errData = await connectRes.json().catch(() => ({}));
            setPersistStatus((prev) => ({
              ...prev,
              [provider]: `save_error: ${errData.detail || "Failed to save"}`,
            }));
          }
        } catch {
          setPersistStatus((prev) => ({
            ...prev,
            [provider]: "save_error: Network error while saving credentials",
          }));
        }

        setValidated((prev) => ({ ...prev, [provider]: true }));
        save({ provider_credentials_validated: { ...validated, [provider]: true } });
      }
    } catch {
      setValidationResults((prev) => ({
        ...prev,
        [provider]: { valid: false, errors: ["Validation request failed"] },
      }));
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (provider: Provider, key: string, file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setCredInputs((prev) => ({
        ...prev,
        [provider]: { ...prev[provider], [key]: content },
      }));
    };
    reader.readAsText(file);
  };

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleComplete = () => {
    save({ completed: true, current_step: 5 });
    router.push("/dashboard");
  };

  const canAdvance = () => {
    switch (step) {
      case 0: return providers.length > 0;
      case 1: return iacTool !== null;
      case 2: return true; // Can always proceed from code view
      case 3: return providers.every((p) => validated[p]);
      default: return true;
    }
  };

  // Get the currently displayed code (either active file or combined)
  const getDisplayCode = (result: IaCResult): string => {
    if (activeFile && result.files?.length) {
      const file = result.files.find((f) => f.filename === activeFile);
      if (file) return file.content;
    }
    return result.code;
  };

  const getDisplayFilename = (result: IaCResult): string => {
    if (activeFile && result.files?.length) {
      return activeFile;
    }
    return result.filename;
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="h-1 bg-accent rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-violet-600 to-fuchsia-500"
              animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        <StepWizard steps={STEPS} currentStep={step}>
          <AnimatePresence mode="wait">
            {/* STEP 1: Welcome + Provider Selection */}
            {step === 0 && (
              <motion.div key="step-0" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                <div className="text-center space-y-3">
                  <h1 className="text-3xl font-bold">
                    Welcome to <span className="bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent">Bonito</span>
                  </h1>
                  <p className="text-muted-foreground text-lg">
                    Connect your cloud providers to get started. Select one or more.
                  </p>
                </div>

                <div className="grid gap-4 md:grid-cols-3">
                  {PROVIDERS.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => toggleProvider(p.id)}
                      className={cn(
                        "relative rounded-xl border-2 p-6 text-left transition-all hover:scale-[1.02]",
                        providers.includes(p.id)
                          ? "border-violet-500 bg-violet-500/10"
                          : "border-border hover:border-violet-500/50",
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
              </motion.div>
            )}

            {/* STEP 2: IaC Tool Selection */}
            {step === 1 && (
              <motion.div key="step-1" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
                <div className="text-center space-y-3">
                  <h2 className="text-2xl font-bold">Choose Your Setup Tool</h2>
                  <p className="text-muted-foreground">
                    We&apos;ll generate production-tested infrastructure code for least-privilege access.
                  </p>
                </div>

                <div className="grid gap-3 max-w-2xl mx-auto">
                  {IAC_TOOLS.filter((t) =>
                    providers.some((p) => t.providers.includes(p)),
                  ).map((t) => (
                    <button
                      key={t.id}
                      onClick={() => selectIacTool(t.id)}
                      className={cn(
                        "flex items-center gap-4 rounded-lg border-2 p-4 text-left transition-all",
                        iacTool === t.id
                          ? "border-violet-500 bg-violet-500/10"
                          : "border-border hover:border-violet-500/50",
                      )}
                    >
                      <div className={cn(
                        "rounded-lg p-2",
                        iacTool === t.id ? "bg-violet-500/20 text-violet-400" : "bg-accent text-muted-foreground",
                      )}>
                        {t.icon}
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold">{t.name}</h3>
                        <p className="text-sm text-muted-foreground">{t.desc}</p>
                      </div>
                      {iacTool === t.id && <Check className="h-5 w-5 text-violet-400" />}
                      {!t.providers.some((p) => providers.includes(p as Provider)) ? null : (
                        <div className="flex gap-1">
                          {t.providers
                            .filter((p) => providers.includes(p as Provider))
                            .map((p) => (
                              <span key={p} className="text-xs px-1.5 py-0.5 rounded bg-accent text-muted-foreground">
                                {p.toUpperCase()}
                              </span>
                            ))}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {/* STEP 3: Generated Code + Download */}
            {step === 2 && (
              <motion.div key="step-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div className="text-center space-y-3">
                  <h2 className="text-2xl font-bold">Run This Code</h2>
                  <p className="text-muted-foreground">
                    Production-tested Terraform from our infrastructure repo. Download or copy-paste.
                  </p>
                </div>

                {/* Provider tabs */}
                <div className="flex gap-2 justify-center">
                  {providers.map((p) => (
                    <button
                      key={p}
                      onClick={() => {
                        setActiveProvider(p);
                        if (!iacResults[p]) handleGenerateIaC(p);
                      }}
                      className={cn(
                        "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                        activeProvider === p
                          ? "bg-violet-500 text-white"
                          : "bg-accent text-muted-foreground hover:bg-accent/80",
                      )}
                    >
                      {p.toUpperCase()}
                    </button>
                  ))}
                </div>

                {activeProvider && iacResults[activeProvider] ? (
                  <div className="space-y-4">
                    {/* Action buttons: Download ZIP + Copy */}
                    <div className="flex items-center gap-3 justify-end">
                      <button
                        onClick={() => handleDownloadZip(activeProvider)}
                        disabled={downloading}
                        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition-colors disabled:opacity-50"
                      >
                        {downloading ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Download className="h-4 w-4" />
                        )}
                        Download Files (.zip)
                      </button>
                    </div>

                    {/* File tabs (for multi-file templates) */}
                    {iacResults[activeProvider]!.files?.length > 1 && (
                      <div className="flex gap-1 border-b">
                        {iacResults[activeProvider]!.files.map((f) => (
                          <button
                            key={f.filename}
                            onClick={() => setActiveFile(f.filename)}
                            className={cn(
                              "px-3 py-1.5 text-xs font-mono rounded-t transition-colors",
                              activeFile === f.filename
                                ? "bg-zinc-950 text-zinc-300 border border-b-0 border-border"
                                : "text-muted-foreground hover:text-foreground",
                            )}
                          >
                            {f.filename}
                          </button>
                        ))}
                        <button
                          onClick={() => setActiveFile(null)}
                          className={cn(
                            "px-3 py-1.5 text-xs font-mono rounded-t transition-colors",
                            activeFile === null
                              ? "bg-zinc-950 text-zinc-300 border border-b-0 border-border"
                              : "text-muted-foreground hover:text-foreground",
                          )}
                        >
                          All Files
                        </button>
                      </div>
                    )}

                    {/* Code block */}
                    <div className="relative rounded-lg border bg-zinc-950 overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-2 border-b bg-zinc-900/50">
                        <span className="text-sm text-muted-foreground font-mono">
                          {getDisplayFilename(iacResults[activeProvider]!)}
                        </span>
                        <button
                          onClick={() => copyCode(getDisplayCode(iacResults[activeProvider]!))}
                          className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded bg-violet-600 hover:bg-violet-500 text-white transition-colors"
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
                  </div>
                ) : activeProvider && loading ? (
                  <div className="flex items-center justify-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin text-violet-400" />
                  </div>
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    <p>Select a provider tab above to generate the setup code.</p>
                  </div>
                )}

                {/* Auto-generate on mount if only one provider */}
                {providers.length === 1 && !activeProvider && (
                  <div className="hidden">
                    {(() => {
                      if (!activeProvider && providers[0]) {
                        setTimeout(() => handleGenerateIaC(providers[0]), 100);
                      }
                      return null;
                    })()}
                  </div>
                )}
              </motion.div>
            )}

            {/* STEP 4: Credential Validation */}
            {step === 3 && (
              <motion.div key="step-3" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div className="text-center space-y-3">
                  <h2 className="text-2xl font-bold">Validate Your Credentials</h2>
                  <p className="text-muted-foreground">
                    Paste the Terraform output values to verify the connection.
                  </p>
                </div>

                <div className="space-y-6 max-w-2xl mx-auto">
                  {providers.map((p) => (
                    <div key={p} className={cn(
                      "rounded-lg border p-6 space-y-4 transition-all",
                      validated[p] ? "border-green-500/50 bg-green-500/5" : "border-border",
                    )}>
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-lg">{p.toUpperCase()}</h3>
                        {validated[p] && (
                          <span className="flex items-center gap-1.5 text-sm text-green-400">
                            <CheckCircle2 className="h-4 w-4" /> Connected
                          </span>
                        )}
                      </div>

                      {!validated[p] && (
                        <>
                          <div className="space-y-3">
                            {CRED_FIELDS[p].map((field) => (
                              <div key={field.key}>
                                <label className="text-sm text-muted-foreground mb-1 flex items-center gap-1.5">
                                  {field.label}
                                  {field.required && <span className="text-red-400">*</span>}
                                  <span className="text-xs text-violet-400/60 font-mono ml-auto">
                                    {field.key}
                                  </span>
                                </label>
                                {field.type === "file" ? (
                                  <div className="space-y-2">
                                    <label className="flex items-center justify-center gap-2 w-full rounded-md border border-dashed bg-zinc-950/50 px-3 py-4 text-sm cursor-pointer hover:border-violet-500/50 transition-colors">
                                      <Upload className="h-4 w-4 text-muted-foreground" />
                                      <span className="text-muted-foreground">
                                        {credInputs[p]?.[field.key] ? "File loaded ✓" : "Click to upload JSON key file"}
                                      </span>
                                      <input
                                        type="file"
                                        accept=".json,application/json"
                                        className="hidden"
                                        onChange={(e) => {
                                          const file = e.target.files?.[0];
                                          if (file) handleFileUpload(p, field.key, file);
                                        }}
                                      />
                                    </label>
                                    <div className="text-xs text-muted-foreground text-center">or paste below</div>
                                    <textarea
                                      className="w-full rounded-md border bg-zinc-950 px-3 py-2 text-sm font-mono min-h-[100px]"
                                      placeholder={field.placeholder || `Paste your ${field.label}...`}
                                      value={credInputs[p]?.[field.key] || ""}
                                      onChange={(e) =>
                                        setCredInputs((prev) => ({
                                          ...prev,
                                          [p]: { ...prev[p], [field.key]: e.target.value },
                                        }))
                                      }
                                    />
                                  </div>
                                ) : (
                                  <input
                                    type={field.type || "text"}
                                    className="w-full rounded-md border bg-zinc-950 px-3 py-2 text-sm font-mono"
                                    placeholder={field.placeholder || field.label}
                                    value={credInputs[p]?.[field.key] || ""}
                                    onChange={(e) =>
                                      setCredInputs((prev) => ({
                                        ...prev,
                                        [p]: { ...prev[p], [field.key]: e.target.value },
                                      }))
                                    }
                                  />
                                )}
                              </div>
                            ))}
                          </div>

                          {/* Validation errors */}
                          {validationResults[p] && !validationResults[p].valid && (
                            <div className="rounded-md bg-red-500/10 border border-red-500/20 p-3">
                              <div className="flex items-center gap-2 text-red-400 text-sm font-medium">
                                <AlertCircle className="h-4 w-4" /> Validation Failed
                              </div>
                              <ul className="mt-1 text-sm text-red-300/80 space-y-1">
                                {validationResults[p].errors?.map((e: string, i: number) => (
                                  <li key={i}>• {e}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <button
                            onClick={() => handleValidate(p)}
                            disabled={loading}
                            className="w-full py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                          >
                            {loading ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Shield className="h-4 w-4" />
                            )}
                            Validate Connection
                          </button>
                        </>
                      )}

                      {/* Credential persistence status */}
                      {validated[p] && persistStatus[p] === "saving" && (
                        <div className="flex items-center gap-2 text-sm text-violet-400">
                          <Loader2 className="h-4 w-4 animate-spin" /> Saving credentials securely…
                        </div>
                      )}
                      {validated[p] && persistStatus[p] === "saved" && (
                        <div className="flex items-center gap-2 text-sm text-green-400">
                          <Shield className="h-4 w-4" /> Credentials saved securely
                        </div>
                      )}
                      {validated[p] && persistStatus[p]?.startsWith("save_error") && (
                        <div className="flex items-center gap-2 text-sm text-yellow-400">
                          <AlertCircle className="h-4 w-4" /> {persistStatus[p].replace("save_error: ", "")}
                        </div>
                      )}

                      {/* Connection Health Status (shown after successful validation) */}
                      {validated[p] && validationResults[p]?.health && (
                        <div className="space-y-3">
                          {/* Overall status */}
                          <div className="flex items-center gap-2">
                            <Activity className={cn(
                              "h-4 w-4",
                              validationResults[p].health!.status === "healthy" && "text-green-400",
                              validationResults[p].health!.status === "degraded" && "text-yellow-400",
                              validationResults[p].health!.status === "error" && "text-red-400",
                            )} />
                            <span className="text-sm font-medium">
                              Connection {validationResults[p].health!.status === "healthy" ? "Healthy" :
                                validationResults[p].health!.status === "degraded" ? "Degraded" : "Error"}
                            </span>
                            {validationResults[p].identity && (
                              <span className="text-xs text-muted-foreground ml-auto">
                                {validationResults[p].identity}
                              </span>
                            )}
                          </div>

                          {/* Individual checks */}
                          <div className="space-y-1.5">
                            {validationResults[p].health!.checks.map((check, i) => (
                              <div key={i} className="flex items-center gap-2 text-sm">
                                <div className={cn(
                                  "h-2 w-2 rounded-full",
                                  check.status === "healthy" && "bg-green-400",
                                  check.status === "degraded" && "bg-yellow-400",
                                  check.status === "error" && "bg-red-400",
                                )} />
                                <span className="font-medium text-xs">{check.name}</span>
                                <span className="text-xs text-muted-foreground">{check.message}</span>
                              </div>
                            ))}
                          </div>

                          {/* Permissions list */}
                          {validationResults[p].permissions && (
                            <div className="text-xs text-muted-foreground space-y-0.5 pt-1 border-t border-border/50">
                              {validationResults[p].permissions!.map((perm, i) => (
                                <div key={i}>{perm}</div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Fallback: show permissions without health (backward compat) */}
                      {validated[p] && !validationResults[p]?.health && validationResults[p]?.valid && (
                        <div className="rounded-md bg-green-500/10 border border-green-500/20 p-3 text-sm">
                          <p className="text-green-400 font-medium">✅ {validationResults[p].identity}</p>
                          {validationResults[p].permissions && (
                            <ul className="mt-1 text-green-300/80 space-y-0.5">
                              {validationResults[p].permissions!.map((perm: string, i: number) => (
                                <li key={i}>{perm}</li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* STEP 5: Success */}
            {step === 4 && (
              <motion.div key="step-4" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center space-y-8 py-8">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", delay: 0.2 }}
                  className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-500"
                >
                  <Rocket className="h-10 w-10 text-white" />
                </motion.div>

                <div className="space-y-3">
                  <h2 className="text-3xl font-bold">You&apos;re All Set! 🎉</h2>
                  <p className="text-lg text-muted-foreground max-w-md mx-auto">
                    Your cloud providers are connected with enterprise-grade security.
                    Head to the dashboard to start managing your AI models.
                  </p>
                </div>

                <div className="flex flex-wrap gap-3 justify-center">
                  {providers.map((p) => {
                    const health = validationResults[p]?.health;
                    return (
                      <div key={p} className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400">
                        {health ? (
                          <Heart className={cn(
                            "h-4 w-4",
                            health.status === "healthy" && "text-green-400",
                            health.status === "degraded" && "text-yellow-400",
                          )} />
                        ) : (
                          <CheckCircle2 className="h-4 w-4" />
                        )}
                        {p.toUpperCase()} Connected
                        {health && health.status !== "healthy" && (
                          <span className="text-xs text-yellow-400">(degraded)</span>
                        )}
                      </div>
                    );
                  })}
                </div>

                <button
                  onClick={handleComplete}
                  className="px-8 py-3 rounded-lg bg-gradient-to-r from-violet-600 to-fuchsia-500 text-white font-semibold text-lg hover:opacity-90 transition-opacity"
                >
                  Go to Dashboard <ArrowRight className="inline h-5 w-5 ml-1" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </StepWizard>

        {/* Navigation */}
        {step < 4 && (
          <div className="flex items-center justify-between mt-8">
            <button
              onClick={goBack}
              disabled={step === 0}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground disabled:opacity-30 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" /> Back
            </button>

            <button
              onClick={goNext}
              disabled={!canAdvance()}
              className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium disabled:opacity-30 transition-colors"
            >
              {step === 3 ? "Complete Setup" : "Continue"} <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
