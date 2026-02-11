"use client";

import { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, CheckCircle, AlertCircle, ChevronLeft, Copy, Check, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { StepWizard } from "@/components/ui/step-wizard";
import { LoadingDots } from "@/components/ui/loading-dots";
import { API_URL } from "@/lib/utils";

type ProviderType = "aws" | "azure" | "gcp" | "openai" | "anthropic";

interface ConnectModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const providers: { type: ProviderType; name: string; description: string; color: string; bgColor: string; icon: string }[] = [
  { type: "aws", name: "AWS Bedrock", description: "Claude, Llama, Titan, Mistral and more", color: "text-amber-500", bgColor: "bg-amber-500/10", icon: "☁️" },
  { type: "azure", name: "Azure OpenAI", description: "GPT-4o, DALL-E, Whisper and more", color: "text-blue-500", bgColor: "bg-blue-500/10", icon: "🔷" },
  { type: "gcp", name: "GCP Vertex AI", description: "Gemini, PaLM, Imagen and more", color: "text-red-500", bgColor: "bg-red-500/10", icon: "🔺" },
  { type: "openai", name: "OpenAI", description: "GPT-4o, o1, o3-mini — direct API", color: "text-green-500", bgColor: "bg-green-500/10", icon: "🤖" },
  { type: "anthropic", name: "Anthropic", description: "Claude 3.5 Sonnet, Opus — direct API", color: "text-purple-500", bgColor: "bg-purple-500/10", icon: "🧠" },
];

const AWS_BEDROCK_REGIONS = [
  { value: "us-east-1", label: "US East (N. Virginia)" },
  { value: "us-west-2", label: "US West (Oregon)" },
  { value: "eu-west-1", label: "Europe (Ireland)" },
  { value: "eu-west-3", label: "Europe (Paris)" },
  { value: "eu-central-1", label: "Europe (Frankfurt)" },
  { value: "ap-northeast-1", label: "Asia Pacific (Tokyo)" },
  { value: "ap-southeast-1", label: "Asia Pacific (Singapore)" },
  { value: "ap-southeast-2", label: "Asia Pacific (Sydney)" },
  { value: "ap-south-1", label: "Asia Pacific (Mumbai)" },
  { value: "ca-central-1", label: "Canada (Central)" },
  { value: "sa-east-1", label: "South America (São Paulo)" },
];

const IAM_POLICY = `{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock-runtime:InvokeModel",
        "bedrock-runtime:InvokeModelWithResponseStream",
        "sts:GetCallerIdentity",
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    }
  ]
}`;

const steps = [
  { title: "Select Provider" },
  { title: "Credentials" },
  { title: "Connect" },
];

export function ConnectModal({ open, onClose, onSuccess }: ConnectModalProps) {
  const [step, setStep] = useState(0);
  const [selectedProvider, setSelectedProvider] = useState<ProviderType | null>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [connecting, setConnecting] = useState(false);
  const [result, setResult] = useState<"success" | "error" | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [connectInfo, setConnectInfo] = useState<{ model_count?: number; region?: string } | null>(null);
  const [copiedPolicy, setCopiedPolicy] = useState(false);
  const [showPolicy, setShowPolicy] = useState(false);

  const reset = useCallback(() => {
    setStep(0);
    setSelectedProvider(null);
    setCredentials({});
    setConnecting(false);
    setResult(null);
    setErrorMessage("");
    setConnectInfo(null);
    setCopiedPolicy(false);
    setShowPolicy(false);
  }, []);

  const handleClose = () => { reset(); onClose(); };

  const handleSelectProvider = (type: ProviderType) => {
    setSelectedProvider(type);
    setCredentials(type === "aws" ? { region: "us-east-1" } : {});
    // Direct API providers skip IAM/policy setup
    setShowPolicy(false);
    setStep(1);
  };

  const handleConnect = async () => {
    if (!selectedProvider) return;
    setConnecting(true);
    setResult(null);
    setStep(2);

    try {
      const res = await fetch(`${API_URL}/api/providers/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ provider_type: selectedProvider, credentials }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Connection failed");
      }

      const provider = await res.json();
      setConnectInfo({ model_count: provider.model_count, region: provider.region });
      setResult("success");
      setTimeout(() => { onSuccess(); handleClose(); }, 2500);
    } catch (err: any) {
      setResult("error");
      setErrorMessage(err.message || "Something went wrong");
    } finally {
      setConnecting(false);
    }
  };

  const copyPolicy = () => {
    navigator.clipboard.writeText(IAM_POLICY);
    setCopiedPolicy(true);
    setTimeout(() => setCopiedPolicy(false), 2000);
  };

  const updateCred = (key: string, value: string) => setCredentials((prev) => ({ ...prev, [key]: value }));

  const isCredentialsValid = () => {
    if (!selectedProvider) return false;
    if (selectedProvider === "aws") return (credentials.access_key_id?.length || 0) >= 16 && (credentials.secret_access_key?.length || 0) >= 20;
    if (selectedProvider === "azure") return ["tenant_id", "client_id", "client_secret", "subscription_id"].every((k) => credentials[k]?.length > 0);
    if (selectedProvider === "gcp") return (credentials.project_id?.length || 0) > 0 && (credentials.service_account_json?.length || 0) > 10;
    if (selectedProvider === "openai") return (credentials.api_key?.length || 0) >= 20;
    if (selectedProvider === "anthropic") return (credentials.api_key?.length || 0) >= 20;
    return false;
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ type: "spring", duration: 0.5 }}
        className="relative z-10 w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-xl border border-border bg-card p-6 shadow-2xl"
      >
        <button onClick={handleClose} className="absolute right-4 top-4 text-muted-foreground hover:text-foreground transition-colors">
          <X className="h-5 w-5" />
        </button>

        <h2 className="text-xl font-bold mb-6">Connect Cloud Provider</h2>

        <StepWizard steps={steps} currentStep={step}>
          {/* Step 0: Select Provider */}
          {step === 0 && (
            <div className="space-y-3">
              {providers.map((p) => (
                <motion.button
                  key={p.type}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  onClick={() => handleSelectProvider(p.type)}
                  className="flex w-full items-center gap-4 rounded-lg border border-border p-4 text-left transition-colors hover:bg-accent/50 hover:border-violet-500/30"
                >
                  <div className={cn("flex h-12 w-12 items-center justify-center rounded-lg text-2xl", p.bgColor)}>{p.icon}</div>
                  <div>
                    <p className="font-semibold">{p.name}</p>
                    <p className="text-sm text-muted-foreground">{p.description}</p>
                  </div>
                </motion.button>
              ))}
            </div>
          )}

          {/* Step 1: Credentials */}
          {step === 1 && selectedProvider && (
            <div className="space-y-4">
              <button onClick={() => setStep(0)} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ChevronLeft className="h-4 w-4" /> Back
              </button>

              {selectedProvider === "aws" && (
                <>
                  {/* IAM recommendation */}
                  <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-sm text-amber-400">
                      <Shield className="h-4 w-4" />
                      <span className="font-medium">We recommend creating a dedicated IAM user</span>
                    </div>
                    <p className="text-xs text-muted-foreground">Create an IAM user with programmatic access and attach the minimum required policy.</p>
                    <button
                      onClick={() => setShowPolicy(!showPolicy)}
                      className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
                    >
                      {showPolicy ? "Hide" : "View"} required IAM policy
                    </button>
                    <AnimatePresence>
                      {showPolicy && (
                        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                          <div className="relative mt-2">
                            <pre className="rounded-md bg-background p-3 text-[11px] font-mono text-muted-foreground overflow-x-auto">{IAM_POLICY}</pre>
                            <button
                              onClick={copyPolicy}
                              className="absolute top-2 right-2 rounded-md bg-accent p-1.5 text-muted-foreground hover:text-foreground transition-colors"
                            >
                              {copiedPolicy ? <Check className="h-3 w-3 text-emerald-500" /> : <Copy className="h-3 w-3" />}
                            </button>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  <Field label="Access Key ID" value={credentials.access_key_id || ""} onChange={(v) => updateCred("access_key_id", v)} placeholder="AKIA..." />
                  <Field label="Secret Access Key" value={credentials.secret_access_key || ""} onChange={(v) => updateCred("secret_access_key", v)} placeholder="wJalr..." type="password" />
                  <div>
                    <label className="mb-1.5 block text-sm font-medium">Region</label>
                    <select
                      value={credentials.region || "us-east-1"}
                      onChange={(e) => updateCred("region", e.target.value)}
                      className="w-full rounded-md border border-border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50"
                    >
                      {AWS_BEDROCK_REGIONS.map((r) => (
                        <option key={r.value} value={r.value}>{r.label} ({r.value})</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {selectedProvider === "azure" && (
                <>
                  <Field label="Tenant ID" value={credentials.tenant_id || ""} onChange={(v) => updateCred("tenant_id", v)} placeholder="xxxxxxxx-xxxx-..." />
                  <Field label="Client ID" value={credentials.client_id || ""} onChange={(v) => updateCred("client_id", v)} placeholder="xxxxxxxx-xxxx-..." />
                  <Field label="Client Secret" value={credentials.client_secret || ""} onChange={(v) => updateCred("client_secret", v)} type="password" placeholder="Enter client secret" />
                  <Field label="Subscription ID" value={credentials.subscription_id || ""} onChange={(v) => updateCred("subscription_id", v)} placeholder="xxxxxxxx-xxxx-..." />
                </>
              )}

              {selectedProvider === "gcp" && (
                <>
                  <Field label="Project ID" value={credentials.project_id || ""} onChange={(v) => updateCred("project_id", v)} placeholder="my-project-123" />
                  <div>
                    <label className="mb-1.5 block text-sm font-medium">Service Account JSON</label>
                    <textarea
                      value={credentials.service_account_json || ""}
                      onChange={(e) => updateCred("service_account_json", e.target.value)}
                      placeholder="Paste your service account JSON key here..."
                      rows={5}
                      className="w-full rounded-md border border-border bg-background px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-violet-500/50 resize-none"
                    />
                  </div>
                </>
              )}

              {selectedProvider === "openai" && (
                <>
                  <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-3 space-y-1">
                    <p className="text-sm text-green-400 font-medium">🤖 Direct OpenAI API</p>
                    <p className="text-xs text-muted-foreground">Get your API key from <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-violet-400 hover:text-violet-300 underline">platform.openai.com</a></p>
                  </div>
                  <Field label="API Key" value={credentials.api_key || ""} onChange={(v) => updateCred("api_key", v)} placeholder="sk-..." type="password" />
                  <Field label="Organization ID (Optional)" value={credentials.organization_id || ""} onChange={(v) => updateCred("organization_id", v)} placeholder="org-..." />
                </>
              )}

              {selectedProvider === "anthropic" && (
                <>
                  <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-3 space-y-1">
                    <p className="text-sm text-purple-400 font-medium">🧠 Direct Anthropic API</p>
                    <p className="text-xs text-muted-foreground">Get your API key from <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener noreferrer" className="text-violet-400 hover:text-violet-300 underline">console.anthropic.com</a></p>
                  </div>
                  <Field label="API Key" value={credentials.api_key || ""} onChange={(v) => updateCred("api_key", v)} placeholder="sk-ant-api03-..." type="password" />
                </>
              )}

              <motion.button
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.98 }}
                disabled={!isCredentialsValid()}
                onClick={handleConnect}
                className={cn(
                  "mt-2 w-full rounded-md py-2.5 text-sm font-medium transition-all",
                  isCredentialsValid()
                    ? "bg-violet-600 text-white hover:bg-violet-700"
                    : "bg-accent text-muted-foreground cursor-not-allowed"
                )}
              >
                Verify & Connect
              </motion.button>
            </div>
          )}

          {/* Step 2: Connecting / Result */}
          {step === 2 && (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              {connecting && !result && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                  <LoadingDots size="lg" className="justify-center" />
                  <div className="space-y-1">
                    <p className="text-sm font-medium">Validating credentials...</p>
                    <p className="text-xs text-muted-foreground">Connecting to {selectedProvider === "aws" ? "AWS" : selectedProvider === "azure" ? "Azure" : selectedProvider === "gcp" ? "GCP" : selectedProvider === "openai" ? "OpenAI" : "Anthropic"} and verifying access</p>
                  </div>
                </motion.div>
              )}

              {result === "success" && (
                <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300, damping: 20 }} className="space-y-4">
                  <motion.div
                    className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/20"
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 0.6 }}
                  >
                    <CheckCircle className="h-8 w-8 text-emerald-500" />
                  </motion.div>
                  <div>
                    <p className="text-lg font-semibold">Connected! 🎉</p>
                    {connectInfo && (
                      <p className="text-sm text-muted-foreground mt-1">
                        Found {connectInfo.model_count || 0} models in {connectInfo.region || "region"}
                      </p>
                    )}
                  </div>
                  {[...Array(12)].map((_, i) => (
                    <motion.div
                      key={i}
                      className={cn(
                        "absolute h-2 w-2 rounded-full",
                        ["bg-violet-500", "bg-emerald-500", "bg-amber-500", "bg-blue-500", "bg-pink-500"][i % 5]
                      )}
                      initial={{ x: 0, y: 0, opacity: 1 }}
                      animate={{ x: Math.cos((i * Math.PI * 2) / 12) * 120, y: Math.sin((i * Math.PI * 2) / 12) * 120, opacity: 0, scale: 0 }}
                      transition={{ duration: 1, ease: "easeOut" }}
                      style={{ left: "50%", top: "40%" }}
                    />
                  ))}
                </motion.div>
              )}

              {result === "error" && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                  <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-red-500/20">
                    <AlertCircle className="h-8 w-8 text-red-500" />
                  </div>
                  <div>
                    <p className="text-lg font-semibold">Connection Failed</p>
                    <p className="text-sm text-muted-foreground mt-1">{errorMessage}</p>
                  </div>
                  <div className="flex gap-3">
                    <button onClick={() => { setStep(1); setResult(null); }} className="rounded-md border border-border px-4 py-2 text-sm hover:bg-accent transition-colors">Edit Credentials</button>
                    <button onClick={handleConnect} className="rounded-md bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700 transition-colors">Retry</button>
                  </div>
                </motion.div>
              )}
            </div>
          )}
        </StepWizard>
      </motion.div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, type = "text" }: {
  label: string; value: string; onChange: (v: string) => void; placeholder?: string; type?: string;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-border bg-background px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/50 transition-shadow"
      />
    </div>
  );
}
