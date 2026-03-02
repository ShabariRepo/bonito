"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Zap,
  Cloud,
  DollarSign,
  Shield,
  Key,
  ArrowRight,
  Terminal,
  Box,
  Route,
  Bell,
  Rocket,
  Server,
  Lock,
  ChevronRight,
  Copy,
  Check,
  BookOpen,
  Bot,
  Network,
  Plug,
  Database,
  Sparkles,
  Clock,
  BarChart3,
} from "lucide-react";

/* ─── Sidebar sections ─── */
const sections = [
  { id: "getting-started", label: "Getting Started", icon: Zap },
  { id: "provider-setup", label: "Provider Setup", icon: Cloud },
  { id: "permissions", label: "Permissions & IAM", icon: Lock },
  { id: "model-management", label: "Model Management", icon: Box },
  { id: "deployments", label: "Deployments", icon: Rocket },
  { id: "gateway-api", label: "Gateway API", icon: Key },
  { id: "routing-policies", label: "Routing Policies", icon: Route },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "cost-management", label: "Cost Management", icon: DollarSign },
  { id: "cli", label: "CLI Tool", icon: Terminal },
  { id: "bonbon", label: "BonBon Agents", icon: Bot },
  { id: "bonobot", label: "Bonobot", icon: Network },
  { id: "mcp", label: "MCP Integration", icon: Plug },
  { id: "knowledge-bases", label: "Knowledge Bases", icon: Database },
  { id: "managed-inference", label: "Managed Inference", icon: Sparkles },
  { id: "triggers", label: "Triggers", icon: Clock },
  { id: "observability", label: "Observability", icon: BarChart3 },
  { id: "troubleshooting", label: "Troubleshooting", icon: Shield },
];

/* ─── Code block component ─── */
function CodeBlock({ code, language = "bash" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="relative group bg-[#0a0a0a] border border-[#1a1a1a] rounded-lg overflow-hidden my-4">
      <button
        onClick={() => {
          navigator.clipboard.writeText(code);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        }}
        className="absolute top-3 right-3 p-1.5 rounded bg-[#1a1a1a] hover:bg-[#222] text-[#666] hover:text-[#ccc] transition opacity-0 group-hover:opacity-100"
        title="Copy"
      >
        {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
      </button>
      <pre className="p-4 overflow-x-auto text-sm font-mono text-[#ccc] leading-relaxed">
        {code}
      </pre>
    </div>
  );
}

/* ─── Section heading ─── */
function SectionHeading({ id, title }: { id: string; title: string }) {
  return (
    <h2 id={id} className="text-2xl font-bold mt-16 mb-6 scroll-mt-24 flex items-center gap-3">
      <span className="w-1 h-6 bg-[#7c3aed] rounded-full" />
      {title}
    </h2>
  );
}

function SubHeading({ title }: { title: string }) {
  return <h3 className="text-lg font-semibold mt-8 mb-3 text-[#e5e0d8]">{title}</h3>;
}

function Paragraph({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-[#999] leading-relaxed mb-4">{children}</p>;
}

function Callout({ children, variant = "info" }: { children: React.ReactNode; variant?: "info" | "warning" | "tip" }) {
  const colors = {
    info: "border-[#7c3aed]/30 bg-[#7c3aed]/5",
    warning: "border-yellow-500/30 bg-yellow-500/5",
    tip: "border-green-500/30 bg-green-500/5",
  };
  const labels = { info: "Note", warning: "Warning", tip: "Tip" };
  return (
    <div className={`border rounded-lg p-4 my-4 ${colors[variant]}`}>
      <span className="text-xs font-semibold uppercase tracking-wider text-[#888] block mb-1">{labels[variant]}</span>
      <div className="text-sm text-[#ccc] leading-relaxed">{children}</div>
    </div>
  );
}

function StepList({ steps }: { steps: string[] }) {
  return (
    <ol className="space-y-2 my-4">
      {steps.map((s, i) => (
        <li key={i} className="flex items-start gap-3 text-sm text-[#ccc]">
          <span className="w-6 h-6 rounded-full bg-[#7c3aed]/20 text-[#7c3aed] flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
            {i + 1}
          </span>
          <span className="leading-relaxed">{s}</span>
        </li>
      ))}
    </ol>
  );
}

/* ─── Main page ─── */
export default function DocsPage() {
  const [active, setActive] = useState("getting-started");

  const handleNavClick = (id: string) => {
    setActive(id);
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-12">
      {/* Hero */}
      <section className="pt-16 pb-10">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-[#7c3aed]" />
            </div>
            <span className="text-sm font-medium text-[#7c3aed] uppercase tracking-wider">Documentation</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">Bonito Docs</h1>
          <p className="mt-3 text-lg text-[#888] max-w-2xl">
            Everything you need to connect your cloud AI providers, deploy models, and route requests through a single gateway.
          </p>
        </motion.div>
      </section>

      <div className="flex gap-10 pb-24">
        {/* ─── Left sidebar ─── */}
        <aside className="hidden lg:block w-56 shrink-0">
          <nav className="sticky top-24 space-y-1">
            {sections.map((s) => (
              <button
                key={s.id}
                onClick={() => handleNavClick(s.id)}
                className={`w-full text-left flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition ${
                  active === s.id
                    ? "bg-[#7c3aed]/10 text-[#7c3aed] font-medium"
                    : "text-[#888] hover:text-[#f5f0e8] hover:bg-[#111]"
                }`}
              >
                <s.icon className="w-4 h-4 shrink-0" />
                {s.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* ─── Right content ─── */}
        <main className="min-w-0 flex-1 max-w-3xl">

          {/* ── Getting Started ── */}
          <SectionHeading id="getting-started" title="Getting Started" />
          <Paragraph>
            Bonito is a unified AI gateway that connects your own cloud AI providers — AWS Bedrock, Azure OpenAI, and Google Cloud Vertex AI — and lets you manage all your models from a single dashboard. You get one API endpoint, one place to track costs, and one control plane for your entire AI stack.
          </Paragraph>

          <SubHeading title="Quick start (5 minutes)" />
          <StepList
            steps={[
              "Sign up at getbonito.com/register — one account covers your entire organization.",
              "Go to Providers → Add Provider and connect at least one cloud provider (AWS, Azure, or GCP).",
              "Bonito validates your credentials and syncs all available models automatically.",
              "Enable the models you want — click Enable on any model or use bulk activation for up to 20 at once.",
              "Go to Gateway → Create Key to generate an API key.",
              "Point any OpenAI-compatible SDK at gateway.getbonito.com/v1 with your new key.",
            ]}
          />

          <CodeBlock
            code={`# Make your first request through Bonito
curl -X POST https://getbonito.com/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_BONITO_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "anthropic.claude-3-sonnet-20240229-v1:0",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 256
  }'`}
          />

          <Callout variant="tip">
            Bonito&apos;s gateway is fully compatible with the OpenAI Chat Completions format. Any tool that supports OpenAI (LangChain, LlamaIndex, custom apps) works out of the box — just change the base URL and API key.
          </Callout>

          {/* ── Provider Setup ── */}
          <SectionHeading id="provider-setup" title="Provider Setup" />
          <Paragraph>
            Connect your cloud provider accounts so Bonito can discover your available models, route requests, and track costs. Each provider requires different credentials.
          </Paragraph>

          <SubHeading title="AWS Bedrock" />
          <Paragraph>
            To connect AWS, you need an IAM Access Key ID and Secret Access Key. Bonito validates them using STS and checks Bedrock permissions automatically.
          </Paragraph>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-lg p-4 my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] border-b border-[#1a1a1a]">
                  <th className="text-left py-2 pr-4 font-medium">Field</th>
                  <th className="text-left py-2 font-medium">Description</th>
                </tr>
              </thead>
              <tbody className="text-[#ccc]">
                <tr className="border-b border-[#1a1a1a]/50"><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Access Key ID</td><td className="py-2">Your IAM access key</td></tr>
                <tr><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Secret Access Key</td><td className="py-2">Your IAM secret key</td></tr>
              </tbody>
            </table>
          </div>

          <SubHeading title="Azure OpenAI" />
          <Paragraph>
            Azure requires a service principal with access to your Azure OpenAI resource. The endpoint must be a custom-subdomain URL (e.g., <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">https://your-resource.openai.azure.com/</code>), not a generic regional endpoint.
          </Paragraph>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-lg p-4 my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] border-b border-[#1a1a1a]">
                  <th className="text-left py-2 pr-4 font-medium">Field</th>
                  <th className="text-left py-2 font-medium">Description</th>
                </tr>
              </thead>
              <tbody className="text-[#ccc]">
                <tr className="border-b border-[#1a1a1a]/50"><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Tenant ID</td><td className="py-2">Azure AD tenant ID</td></tr>
                <tr className="border-b border-[#1a1a1a]/50"><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Client ID</td><td className="py-2">Service principal application ID</td></tr>
                <tr className="border-b border-[#1a1a1a]/50"><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Client Secret</td><td className="py-2">Service principal secret</td></tr>
                <tr className="border-b border-[#1a1a1a]/50"><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Subscription ID</td><td className="py-2">Your Azure subscription</td></tr>
                <tr className="border-b border-[#1a1a1a]/50"><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Resource Group</td><td className="py-2">Resource group with your OpenAI resource</td></tr>
                <tr><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Endpoint URL</td><td className="py-2">Custom subdomain endpoint URL</td></tr>
              </tbody>
            </table>
          </div>
          <Callout variant="warning">
            A generic regional endpoint like <code className="text-xs">https://eastus.api.cognitive.microsoft.com/</code> will not work. You must use an Azure OpenAI resource with a custom subdomain.
          </Callout>

          <SubHeading title="Google Cloud (Vertex AI)" />
          <Paragraph>
            GCP requires your Project ID and a Service Account JSON key file. Paste the entire JSON contents — Bonito validates the format in the browser before sending.
          </Paragraph>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-lg p-4 my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] border-b border-[#1a1a1a]">
                  <th className="text-left py-2 pr-4 font-medium">Field</th>
                  <th className="text-left py-2 font-medium">Description</th>
                </tr>
              </thead>
              <tbody className="text-[#ccc]">
                <tr className="border-b border-[#1a1a1a]/50"><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Project ID</td><td className="py-2">Your GCP project ID</td></tr>
                <tr><td className="py-2 pr-4 font-mono text-xs text-[#7c3aed]">Service Account JSON</td><td className="py-2">Full JSON key file contents</td></tr>
              </tbody>
            </table>
          </div>

          <Callout variant="tip">
            You can update credentials at any time without re-entering everything. Go to Providers → click a provider → change only the fields you need. Blank fields keep their current values.
          </Callout>

          {/* ── Permissions & IAM ── */}
          <SectionHeading id="permissions" title="Permissions & IAM" />
          <Paragraph>
            Bonito supports two IAM setup modes for every provider. Choose based on your security requirements.
          </Paragraph>

          <div className="grid sm:grid-cols-2 gap-4 my-6">
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4 text-[#7c3aed]" />
                <h4 className="font-semibold text-sm">Quick Start</h4>
              </div>
              <p className="text-xs text-[#888] leading-relaxed">Attach a single managed role with broad permissions. Fast to set up, ideal for evaluation and testing.</p>
            </div>
            <div className="bg-[#111] border border-[#7c3aed]/30 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="w-4 h-4 text-[#7c3aed]" />
                <h4 className="font-semibold text-sm">Enterprise (Recommended)</h4>
              </div>
              <p className="text-xs text-[#888] leading-relaxed">Separate least-privilege policies per capability. Only grant the exact permissions each feature needs.</p>
            </div>
          </div>

          <SubHeading title="AWS Bedrock permissions" />
          <Paragraph>
            In Enterprise mode, each capability has its own policy so you only grant what you need:
          </Paragraph>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-lg p-4 my-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] border-b border-[#1a1a1a]">
                  <th className="text-left py-2 pr-4 font-medium">Policy</th>
                  <th className="text-left py-2 pr-4 font-medium">Actions</th>
                  <th className="text-left py-2 font-medium">Required?</th>
                </tr>
              </thead>
              <tbody className="text-[#ccc] text-xs">
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-medium">Core</td>
                  <td className="py-2 pr-4 font-mono">ListFoundationModels, GetFoundationModel, InvokeModel, InvokeModelWithResponseStream, sts:GetCallerIdentity</td>
                  <td className="py-2 text-green-400">Always</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-medium">Provisioning</td>
                  <td className="py-2 pr-4 font-mono">Create/Get/Update/Delete/ListProvisionedModelThroughput</td>
                  <td className="py-2 text-[#888]">If deploying reserved capacity</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-medium">Model Activation</td>
                  <td className="py-2 pr-4 font-mono">PutFoundationModelEntitlement</td>
                  <td className="py-2 text-[#888]">If enabling models from Bonito UI</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4 font-medium">Cost Tracking</td>
                  <td className="py-2 pr-4 font-mono">ce:GetCostAndUsage, GetCostForecast, GetDimensionValues, GetTags</td>
                  <td className="py-2 text-[#888]">If you want spend visibility</td>
                </tr>
              </tbody>
            </table>
          </div>

          <Paragraph>Example IAM policy (core only — minimum to get started):</Paragraph>
          <CodeBlock
            language="json"
            code={`{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}`}
          />

          <SubHeading title="Azure permissions" />
          <Paragraph>
            <strong>Quick Start:</strong> Assign <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">Cognitive Services Contributor</code> on the Azure OpenAI resource.
          </Paragraph>
          <Paragraph>
            <strong>Enterprise:</strong> Create a custom role with only the exact permissions Bonito uses — account read, deployments read/write/delete, models read, and inference actions.
          </Paragraph>
          <CodeBlock
            language="bash"
            code={`az role definition create --role-definition '{
  "Name": "Bonito AI Operator",
  "Actions": [
    "Microsoft.CognitiveServices/accounts/read",
    "Microsoft.CognitiveServices/accounts/deployments/read",
    "Microsoft.CognitiveServices/accounts/deployments/write",
    "Microsoft.CognitiveServices/accounts/deployments/delete",
    "Microsoft.CognitiveServices/accounts/models/read"
  ],
  "DataActions": [
    "Microsoft.CognitiveServices/accounts/OpenAI/deployments/chat/completions/action",
    "Microsoft.CognitiveServices/accounts/OpenAI/deployments/completions/action",
    "Microsoft.CognitiveServices/accounts/OpenAI/deployments/embeddings/action"
  ],
  "AssignableScopes": ["/subscriptions/YOUR_SUBSCRIPTION_ID"]
}'`}
          />
          <Paragraph>
            Optionally add <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">Cost Management Reader</code> at subscription scope for spend visibility.
          </Paragraph>

          <SubHeading title="GCP permissions" />
          <Paragraph>
            <strong>Quick Start:</strong> Assign <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">roles/aiplatform.user</code> to the service account.
          </Paragraph>
          <Paragraph>
            <strong>Enterprise:</strong> Create a custom role with discovery (publishers.get, publisherModels.get), invocation (endpoints.predict), endpoint management (create/get/list/update/delete/deploy/undeploy), model metadata (models.list, models.get), and project validation (resourcemanager.projects.get).
          </Paragraph>
          <Callout variant="tip">
            Bonito&apos;s IaC templates (Terraform) support both modes for all providers. Set <code className="text-xs">iam_mode = &quot;least_privilege&quot;</code> for enterprise or <code className="text-xs">&quot;managed&quot;</code> for quick start.
          </Callout>

          {/* ── Model Management ── */}
          <SectionHeading id="model-management" title="Model Management" />
          <Paragraph>
            Once a provider is connected, Bonito automatically syncs all available models. You can view, search, filter, and enable models from a single catalog.
          </Paragraph>

          <SubHeading title="One-click model activation" />
          <Paragraph>
            Models with a 🔒 icon exist in your provider&apos;s catalog but aren&apos;t yet enabled in your cloud account. Instead of switching to each provider&apos;s console, enable them directly from Bonito:
          </Paragraph>
          <StepList
            steps={[
              "Go to the Models page and find the model you want to enable.",
              "Click the Enable button on the model card.",
              "Bonito handles the provider-specific activation (Bedrock entitlements, Azure deployments, GCP API enablement).",
              "Some models may require approval from the provider and won't activate instantly.",
            ]}
          />
          <Callout variant="tip">
            Use bulk activation to enable up to 20 models at once — select them and click &quot;Enable Selected&quot;.
          </Callout>

          <SubHeading title="Playground" />
          <Paragraph>
            Test any enabled chat model directly in the browser. The Playground supports single-model chat and side-by-side comparison mode (up to 4 models). Token usage and cost appear after each response. Only chat-capable, enabled models are shown in the picker.
          </Paragraph>

          {/* ── Deployments ── */}
          <SectionHeading id="deployments" title="Deployments" />
          <Paragraph>
            Deploy AI models directly into your cloud from the Bonito UI — no console-hopping required. Bonito creates real deployments in your cloud account.
          </Paragraph>

          <div className="bg-[#111] border border-[#1a1a1a] rounded-lg p-4 my-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] border-b border-[#1a1a1a]">
                  <th className="text-left py-2 pr-4 font-medium">Provider</th>
                  <th className="text-left py-2 pr-4 font-medium">Deployment Type</th>
                  <th className="text-left py-2 font-medium">What Bonito Creates</th>
                </tr>
              </thead>
              <tbody className="text-[#ccc] text-xs">
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-3 pr-4 font-medium">AWS Bedrock</td>
                  <td className="py-3 pr-4">On-demand or Provisioned Throughput</td>
                  <td className="py-3">On-demand: validates access. PT: creates reserved capacity with commitment (1 week–6 months)</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-3 pr-4 font-medium">Azure OpenAI</td>
                  <td className="py-3 pr-4">Model deployment with TPM capacity</td>
                  <td className="py-3">Creates a deployment on your Azure OpenAI resource (Standard or GlobalStandard tier)</td>
                </tr>
                <tr>
                  <td className="py-3 pr-4 font-medium">GCP Vertex AI</td>
                  <td className="py-3 pr-4">Serverless (no provisioning needed)</td>
                  <td className="py-3">Verifies access — GCP models are serverless by default</td>
                </tr>
              </tbody>
            </table>
          </div>

          <Callout variant="warning">
            AWS Provisioned Throughput costs real money ($20+/hr per model unit) and requires a minimum 1-month commitment. Use on-demand for testing. Also requires the <code className="text-xs">bedrock:CreateProvisionedModelThroughput</code> IAM permission.
          </Callout>

          <Callout variant="info">
            Azure deployments require TPM quota for the model in your subscription. If you get a quota error, request an increase in Azure Portal → Quotas.
          </Callout>

          {/* ── Gateway API ── */}
          <SectionHeading id="gateway-api" title="Gateway API" />
          <Paragraph>
            Bonito provides an OpenAI-compatible API endpoint so you can use any connected model with tools that support the OpenAI format. One API key, all your providers.
          </Paragraph>

          <SubHeading title="Endpoint" />
          <CodeBlock code="POST https://getbonito.com/v1/chat/completions" />

          <SubHeading title="Authentication" />
          <Paragraph>
            Generate API keys from the Gateway page in the dashboard. Include your key in the Authorization header:
          </Paragraph>
          <CodeBlock code='Authorization: Bearer YOUR_BONITO_API_KEY' />

          <SubHeading title="Example: Python (OpenAI SDK)" />
          <CodeBlock
            language="python"
            code={`from openai import OpenAI

client = OpenAI(
    base_url="https://getbonito.com/v1",
    api_key="YOUR_BONITO_API_KEY"
)

response = client.chat.completions.create(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)`}
          />

          <SubHeading title="Example: curl" />
          <CodeBlock
            code={`curl https://getbonito.com/v1/chat/completions \\
  -H "Authorization: Bearer YOUR_BONITO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "anthropic.claude-3-sonnet-20240229-v1:0",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 256
  }'`}
          />

          <SubHeading title="Model names" />
          <Paragraph>
            Use the provider-native model IDs shown on the Models page in Bonito. For example: <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">anthropic.claude-3-sonnet-20240229-v1:0</code> for AWS Bedrock, <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">gpt-4o</code> for Azure, <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">gemini-1.5-pro</code> for GCP.
          </Paragraph>
          <Paragraph>
            When using a routing policy, pass the policy name as the model field instead of a specific model ID.
          </Paragraph>

          {/* ── Routing Policies ── */}
          <SectionHeading id="routing-policies" title="Routing Policies" />
          <Paragraph>
            Routing policies let you automatically select the best model for each request based on your priorities. Create policies from Routing → Create Policy in the dashboard.
          </Paragraph>

          <div className="space-y-4 my-6">
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1 flex items-center gap-2"><DollarSign className="w-4 h-4 text-green-400" /> Cost-Optimized</h4>
              <p className="text-xs text-[#888] leading-relaxed">Automatically selects the cheapest capable model for each request. Route routine traffic to economy models and save 40–70% versus using a single premium model for everything.</p>
            </div>
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1 flex items-center gap-2"><Shield className="w-4 h-4 text-yellow-400" /> Failover Chain</h4>
              <p className="text-xs text-[#888] leading-relaxed">Define a primary model and one or more fallbacks. If the primary fails or is unavailable, Bonito automatically tries the next model in the chain. Great for high-availability use cases.</p>
            </div>
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1 flex items-center gap-2"><Route className="w-4 h-4 text-blue-400" /> A/B Testing</h4>
              <p className="text-xs text-[#888] leading-relaxed">Split traffic between models using percentage weights (must sum to 100). Test new models in production with controlled rollout — e.g., send 90% to your current model and 10% to a new one.</p>
            </div>
          </div>

          <Callout variant="tip">
            Use the &quot;Test&quot; button on any routing policy to dry-run model selection and verify your configuration before going live.
          </Callout>

          {/* ── Notifications ── */}
          <SectionHeading id="notifications" title="Notifications" />
          <Paragraph>
            Bonito sends in-app notifications for important events across the platform so you never miss a deployment status change or cost alert.
          </Paragraph>

          <SubHeading title="Notification types" />
          <ul className="space-y-2 my-4">
            {[
              "Deployment lifecycle — creation, scaling, completion, and failure alerts for deployments across all providers.",
              "Spend alerts — get notified when costs approach or exceed your configured budget thresholds.",
              "Model activation — confirmation when models are enabled or if activation requires provider approval.",
              "Provider health — alerts when a provider connection has issues or needs credential rotation.",
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[#ccc]">
                <ArrowRight className="w-3.5 h-3.5 text-[#7c3aed] mt-1 shrink-0" />
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
          <Paragraph>
            The notification bell in the dashboard header shows your unread count. Click to see the full list with read/unread states. You can configure alert rules for budget thresholds with email and in-app delivery preferences.
          </Paragraph>

          {/* ── Cost Management ── */}
          <SectionHeading id="cost-management" title="Cost Management" />
          <Paragraph>
            Monitor AI spending across all connected providers from a single dashboard. Bonito pulls real cost data from your cloud accounts and shows breakdowns by model, provider, and time period.
          </Paragraph>
          <SubHeading title="What you get" />
          <ul className="space-y-2 my-4">
            {[
              "Aggregated costs across AWS, Azure, and GCP with daily/weekly/monthly views.",
              "Cost forecast with projected spending and confidence bounds.",
              "Per-model and per-provider breakdowns to identify expensive workloads.",
              "Budget alerts — set thresholds and get notified before you exceed them.",
              "Optimization recommendations — Bonito suggests cheaper model alternatives and cross-provider routing opportunities.",
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[#ccc]">
                <ArrowRight className="w-3.5 h-3.5 text-[#7c3aed] mt-1 shrink-0" />
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>
          <Callout variant="info">
            Cost tracking requires the cost-related IAM permissions for each provider (AWS Cost Explorer, Azure Cost Management Reader, GCP Billing Viewer). These are optional — the platform works without them, you just won&apos;t see spend data.
          </Callout>

          {/* ── CLI ── */}
          <SectionHeading id="cli" title="CLI Tool" />
          <Paragraph>
            <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">bonito-cli</code> is a Python CLI for managing your Bonito resources from the terminal. It&apos;s useful for scripting, CI/CD pipelines, and terminal-first workflows.
          </Paragraph>

          <SubHeading title="Installation" />
          <CodeBlock code="pip install bonito-cli" />

          <SubHeading title="Authentication" />
          <CodeBlock
            code={`# Login with your Bonito credentials
bonito auth login

# Or set your API key directly
export BONITO_API_KEY=your-key-here`}
          />

          <SubHeading title="Common commands" />
          <CodeBlock
            code={`# List connected providers
bonito providers list

# List available models
bonito models list

# Create a gateway API key
bonito gateway keys create --name "my-key"

# List routing policies
bonito routing list

# Check costs
bonito costs summary`}
          />

          <Paragraph>
            Run <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs text-[#7c3aed]">bonito --help</code> for the full list of commands and options.
          </Paragraph>

          {/* ── BonBon Agents ── */}
          <SectionHeading id="bonbon" title="BonBon Agents" />
          <Paragraph>
            BonBon is Bonito&apos;s managed agent service. Create AI agents with custom system prompts, connect them to knowledge bases for RAG, and deploy them as embeddable chat widgets or API endpoints — all without managing infrastructure.
          </Paragraph>

          <SubHeading title="Agent tiers" />
          <div className="grid sm:grid-cols-2 gap-4 my-6">
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Bot className="w-4 h-4 text-[#7c3aed]" />
                <h4 className="font-semibold text-sm">Simple — $199/mo</h4>
              </div>
              <p className="text-xs text-[#888] leading-relaxed">Single-model agent with a system prompt, optional knowledge base, and an embeddable widget. Ideal for FAQ bots, customer support, and internal assistants.</p>
            </div>
            <div className="bg-[#111] border border-[#7c3aed]/30 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-[#7c3aed]" />
                <h4 className="font-semibold text-sm">Advanced — $399/mo</h4>
              </div>
              <p className="text-xs text-[#888] leading-relaxed">Multi-model agent with MCP tool integration, multiple knowledge bases, advanced routing, Bonobot orchestration, and full API access. Built for complex workflows.</p>
            </div>
          </div>

          <SubHeading title="Creating an agent" />
          <StepList
            steps={[
              "Go to Agents → Create Agent in the dashboard.",
              "Choose a tier (Simple or Advanced) and give your agent a name.",
              "Write a system prompt that defines your agent's personality, constraints, and behavior.",
              "Optionally attach a knowledge base for RAG-powered responses.",
              "Select the backing model (or models for Advanced tier).",
              "Deploy — Bonito gives you a widget embed code and an API endpoint.",
            ]}
          />

          <CodeBlock
            code={`# Create an agent via CLI
bonito agents create \\
  --name "Support Bot" \\
  --tier simple \\
  --model "anthropic.claude-3-sonnet-20240229-v1:0" \\
  --system-prompt "You are a helpful support agent for Acme Corp..."

# List your agents
bonito agents list

# Get agent details
bonito agents get --id ag_abc123`}
          />

          <SubHeading title="System prompts" />
          <Paragraph>
            System prompts define how your agent behaves. Write clear instructions about the agent&apos;s role, tone, constraints, and what it should or shouldn&apos;t do. You can update the system prompt at any time without redeploying.
          </Paragraph>
          <CodeBlock
            language="text"
            code={`You are a customer support agent for Acme Corp.

Rules:
- Only answer questions about Acme products and services.
- If you don't know the answer, say so and offer to connect with a human.
- Be friendly, concise, and professional.
- Never make up pricing or feature information — use the knowledge base.
- Respond in the same language as the customer.`}
          />

          <SubHeading title="RAG integration" />
          <Paragraph>
            Connect a knowledge base to give your agent access to your documents. When a user asks a question, Bonito retrieves relevant chunks from your KB and includes them in the context before the model generates a response.
          </Paragraph>
          <CodeBlock
            code={`# Attach a knowledge base to an agent
bonito agents update --id ag_abc123 \\
  --knowledge-base kb_xyz789

# Attach multiple KBs (Advanced tier only)
bonito agents update --id ag_abc123 \\
  --knowledge-base kb_xyz789 \\
  --knowledge-base kb_docs456`}
          />

          <SubHeading title="Widget embedding" />
          <Paragraph>
            Every BonBon agent gets an embeddable chat widget. Add it to any website with a single script tag:
          </Paragraph>
          <CodeBlock
            language="html"
            code={`<!-- Add to your website -->
<script
  src="https://getbonito.com/widget.js"
  data-agent-id="ag_abc123"
  data-theme="dark"
  data-position="bottom-right"
  async
></script>`}
          />
          <Callout variant="tip">
            You can also use the agent via the API directly. Send messages to <code className="text-xs">POST /v1/agents/ag_abc123/chat</code> with the same OpenAI-compatible format.
          </Callout>

          {/* ── Bonobot ── */}
          <SectionHeading id="bonobot" title="Bonobot Orchestrator" />
          <Paragraph>
            Bonobot is Bonito&apos;s multi-agent orchestration layer. It acts as a front-door agent that classifies user intent, delegates to specialized sub-agents, and synthesizes their responses into a unified reply. Think of it as a dispatcher that routes conversations to the right expert.
          </Paragraph>

          <SubHeading title="How it works" />
          <StepList
            steps={[
              "A user sends a message to the Bonobot endpoint.",
              "The orchestrator classifies the user's intent using a fast classification model.",
              "Based on the intent, it delegates the request to one or more specialized BonBon agents.",
              "Each sub-agent processes its part using its own system prompt, model, and knowledge base.",
              "Bonobot synthesizes the responses and returns a single, coherent answer.",
            ]}
          />

          <SubHeading title="Delegation map" />
          <Paragraph>
            The delegation map defines which sub-agents handle which intents. Configure it as a JSON mapping of intent patterns to agent IDs:
          </Paragraph>
          <CodeBlock
            language="json"
            code={`{
  "delegation_map": {
    "billing": {
      "agent_id": "ag_billing01",
      "description": "Handles billing, invoices, and payment questions"
    },
    "technical_support": {
      "agent_id": "ag_techsup01",
      "description": "Handles technical issues, bugs, and troubleshooting"
    },
    "sales": {
      "agent_id": "ag_sales01",
      "description": "Handles pricing, demos, and feature inquiries"
    },
    "general": {
      "agent_id": "ag_general01",
      "description": "Fallback for anything that doesn't match a specific intent"
    }
  }
}`}
          />

          <SubHeading title="Creating a Bonobot" />
          <CodeBlock
            code={`# Create an orchestrator
bonito bonobot create \\
  --name "Customer Hub" \\
  --classifier-model "anthropic.claude-3-haiku-20240307-v1:0" \\
  --delegation-map ./delegation.json

# Update the delegation map
bonito bonobot update --id bot_abc123 \\
  --delegation-map ./updated-delegation.json

# Test intent classification
bonito bonobot classify --id bot_abc123 \\
  --message "I need a refund for my last invoice"`}
          />

          <Callout variant="info">
            Bonobot requires the Advanced agent tier ($399/mo). Each sub-agent in the delegation map must be an existing BonBon agent.
          </Callout>

          <SubHeading title="Response synthesis" />
          <Paragraph>
            When a request touches multiple intents (e.g., &quot;I want to upgrade my plan and fix a bug&quot;), Bonobot can delegate to multiple agents in parallel and merge their responses. Enable multi-delegation in the orchestrator settings:
          </Paragraph>
          <CodeBlock
            language="json"
            code={`{
  "multi_delegation": true,
  "synthesis_model": "anthropic.claude-3-sonnet-20240229-v1:0",
  "synthesis_prompt": "Combine the following specialist responses into a single, coherent answer."
}`}
          />

          {/* ── MCP Integration ── */}
          <SectionHeading id="mcp" title="MCP Integration" />
          <Paragraph>
            MCP (Model Context Protocol) lets your BonBon agents call external tools — databases, APIs, code execution, file systems, and more. Register MCP servers with Bonito and connect them to your agents so they can take actions, not just answer questions.
          </Paragraph>

          <SubHeading title="Supported transports" />
          <div className="grid sm:grid-cols-2 gap-4 my-6">
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1">SSE (Server-Sent Events)</h4>
              <p className="text-xs text-[#888] leading-relaxed">Connect to remote MCP servers over HTTP. Best for hosted tools, third-party integrations, and production deployments.</p>
            </div>
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1">stdio (Standard I/O)</h4>
              <p className="text-xs text-[#888] leading-relaxed">Run MCP servers as local subprocesses. Best for development, local tools, and self-hosted servers.</p>
            </div>
          </div>

          <SubHeading title="Registering an MCP server" />
          <CodeBlock
            language="json"
            code={`{
  "name": "github-tools",
  "transport": "sse",
  "url": "https://mcp.example.com/github/sse",
  "headers": {
    "Authorization": "Bearer ghp_xxxxxxxxxxxx"
  },
  "tools": ["create_issue", "search_repos", "get_pull_request"]
}`}
          />
          <CodeBlock
            code={`# Register via CLI
bonito mcp register \\
  --name "github-tools" \\
  --transport sse \\
  --url "https://mcp.example.com/github/sse"

# List registered MCP servers
bonito mcp list

# Test a tool call
bonito mcp test --server "github-tools" --tool "search_repos" \\
  --params '{"query": "bonito"}'`}
          />

          <SubHeading title="stdio configuration" />
          <Paragraph>
            For stdio-based MCP servers, provide the command and arguments to launch the server process:
          </Paragraph>
          <CodeBlock
            language="json"
            code={`{
  "name": "sqlite-tools",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-sqlite", "./data/mydb.sqlite"],
  "env": {
    "NODE_ENV": "production"
  }
}`}
          />

          <SubHeading title="Connecting MCP to agents" />
          <Paragraph>
            Once registered, attach MCP servers to your BonBon agents. The agent&apos;s model will automatically see the available tools and can call them during conversations:
          </Paragraph>
          <CodeBlock
            code={`# Connect MCP server to an agent
bonito agents update --id ag_abc123 \\
  --mcp-server "github-tools" \\
  --mcp-server "sqlite-tools"

# Remove an MCP server from an agent
bonito agents update --id ag_abc123 \\
  --remove-mcp-server "sqlite-tools"`}
          />
          <Callout variant="warning">
            MCP tool execution happens server-side. Make sure your MCP servers are secured — Bonito passes through authentication headers but does not sandbox tool execution.
          </Callout>

          {/* ── Knowledge Bases ── */}
          <SectionHeading id="knowledge-bases" title="Knowledge Bases" />
          <Paragraph>
            Knowledge Bases power RAG (Retrieval-Augmented Generation) for your BonBon agents. Upload documents, and Bonito chunks, embeds, and indexes them so your agents can retrieve relevant context at query time.
          </Paragraph>

          <SubHeading title="Creating a knowledge base" />
          <StepList
            steps={[
              "Go to Knowledge Bases → Create in the dashboard, or use the CLI.",
              "Give it a name and optional description.",
              "Choose an embedding model (defaults to a high-quality model on your connected providers).",
              "Configure chunking strategy (size, overlap).",
              "Upload your documents.",
            ]}
          />
          <CodeBlock
            code={`# Create a knowledge base
bonito kb create --name "Product Docs" \\
  --embedding-model "amazon.titan-embed-text-v2:0" \\
  --chunk-size 512 \\
  --chunk-overlap 50

# Upload documents
bonito kb upload --id kb_xyz789 ./docs/*.pdf
bonito kb upload --id kb_xyz789 ./faq.md
bonito kb upload --id kb_xyz789 https://example.com/api-reference.html

# Check indexing status
bonito kb status --id kb_xyz789`}
          />

          <SubHeading title="Supported file formats" />
          <Paragraph>
            Bonito accepts PDF, Markdown, plain text, HTML, DOCX, and CSV files. Each file is parsed, split into chunks, and embedded using your chosen embedding model.
          </Paragraph>

          <SubHeading title="Chunking strategies" />
          <div className="bg-[#111] border border-[#1a1a1a] rounded-lg p-4 my-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] border-b border-[#1a1a1a]">
                  <th className="text-left py-2 pr-4 font-medium">Strategy</th>
                  <th className="text-left py-2 pr-4 font-medium">Description</th>
                  <th className="text-left py-2 font-medium">Best For</th>
                </tr>
              </thead>
              <tbody className="text-[#ccc] text-xs">
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">fixed</td>
                  <td className="py-2 pr-4">Split by token count with configurable overlap</td>
                  <td className="py-2">General purpose, predictable chunk sizes</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">semantic</td>
                  <td className="py-2 pr-4">Split at natural boundaries (paragraphs, sections)</td>
                  <td className="py-2">Long-form documents, articles</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">sentence</td>
                  <td className="py-2 pr-4">Split by sentence with grouping</td>
                  <td className="py-2">FAQ, short-form content</td>
                </tr>
              </tbody>
            </table>
          </div>

          <SubHeading title="Embedding models" />
          <Paragraph>
            Bonito uses embedding models from your connected providers. Any enabled embedding model can be used:
          </Paragraph>
          <ul className="space-y-2 my-4">
            {[
              "AWS Bedrock: amazon.titan-embed-text-v2:0, cohere.embed-english-v3",
              "Azure OpenAI: text-embedding-ada-002, text-embedding-3-small, text-embedding-3-large",
              "GCP Vertex AI: textembedding-gecko, text-embedding-004",
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[#ccc]">
                <ArrowRight className="w-3.5 h-3.5 text-[#7c3aed] mt-1 shrink-0" />
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>

          <SubHeading title="Querying" />
          <Paragraph>
            You can query a knowledge base directly to test retrieval before connecting it to an agent:
          </Paragraph>
          <CodeBlock
            code={`# Query a knowledge base directly
bonito kb query --id kb_xyz789 \\
  --query "What is the refund policy?" \\
  --top-k 5

# Connect KB to an agent (see BonBon Agents section)
bonito agents update --id ag_abc123 \\
  --knowledge-base kb_xyz789`}
          />
          <Callout variant="tip">
            Start with a chunk size of 512 tokens and 50-token overlap. Adjust based on your content — shorter chunks work better for precise Q&amp;A, longer chunks for summarization tasks.
          </Callout>

          {/* ── Managed Inference ── */}
          <SectionHeading id="managed-inference" title="Managed Inference" />
          <Paragraph>
            Managed Inference gives you zero-config access to AI models without connecting any cloud provider. No API keys, no cloud accounts, no setup — just start making requests. Bonito handles provider selection, routing, and billing.
          </Paragraph>

          <SubHeading title="How it works" />
          <StepList
            steps={[
              "Sign up for Bonito and create a gateway API key — that's it.",
              "Use any supported model by name in your API requests.",
              "Bonito routes your request to the optimal provider automatically.",
              "You're billed through Bonito based on token usage — no separate cloud bills.",
            ]}
          />

          <CodeBlock
            language="python"
            code={`from openai import OpenAI

# No cloud provider setup needed — just your Bonito key
client = OpenAI(
    base_url="https://getbonito.com/v1",
    api_key="YOUR_BONITO_API_KEY"
)

# Use any supported model
response = client.chat.completions.create(
    model="claude-3-sonnet",  # Bonito routes to the best provider
    messages=[{"role": "user", "content": "Explain quantum computing"}]
)

print(response.choices[0].message.content)`}
          />

          <SubHeading title="Supported models" />
          <Paragraph>
            Managed Inference supports a curated set of popular models across providers. Use simplified model names — Bonito resolves them to provider-specific IDs:
          </Paragraph>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-lg p-4 my-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] border-b border-[#1a1a1a]">
                  <th className="text-left py-2 pr-4 font-medium">Model</th>
                  <th className="text-left py-2 pr-4 font-medium">Provider</th>
                  <th className="text-left py-2 font-medium">Use Case</th>
                </tr>
              </thead>
              <tbody className="text-[#ccc] text-xs">
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">claude-3-sonnet</td>
                  <td className="py-2 pr-4">Anthropic</td>
                  <td className="py-2">General purpose, balanced performance</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">claude-3-haiku</td>
                  <td className="py-2 pr-4">Anthropic</td>
                  <td className="py-2">Fast, cost-effective tasks</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">gpt-4o</td>
                  <td className="py-2 pr-4">OpenAI</td>
                  <td className="py-2">Multimodal, high performance</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">gpt-4o-mini</td>
                  <td className="py-2 pr-4">OpenAI</td>
                  <td className="py-2">Lightweight, budget-friendly</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">gemini-1.5-pro</td>
                  <td className="py-2 pr-4">Google</td>
                  <td className="py-2">Long context, multimodal</td>
                </tr>
              </tbody>
            </table>
          </div>

          <SubHeading title="When to use Managed vs BYOC" />
          <div className="grid sm:grid-cols-2 gap-4 my-6">
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1">Managed Inference</h4>
              <ul className="text-xs text-[#888] leading-relaxed space-y-1 mt-2">
                <li>• Quick start — no cloud setup</li>
                <li>• Don&apos;t want to manage API keys</li>
                <li>• Prototyping and development</li>
                <li>• Teams without cloud accounts</li>
              </ul>
            </div>
            <div className="bg-[#111] border border-[#7c3aed]/30 rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1">Bring Your Own Cloud</h4>
              <ul className="text-xs text-[#888] leading-relaxed space-y-1 mt-2">
                <li>• Data residency requirements</li>
                <li>• Existing cloud commitments/discounts</li>
                <li>• Full provider control</li>
                <li>• Enterprise compliance needs</li>
              </ul>
            </div>
          </div>

          <Callout variant="info">
            Managed Inference and BYOC (Bring Your Own Cloud) can be used simultaneously. Use managed models for quick experiments and your own providers for production workloads.
          </Callout>

          {/* ── Triggers ── */}
          <SectionHeading id="triggers" title="Triggers" />
          <Paragraph>
            Triggers let you invoke BonBon agents automatically based on events — incoming webhooks, cron schedules, slash commands, or custom events. Instead of waiting for a user to open a chat widget, triggers bring your agents into workflows programmatically.
          </Paragraph>

          <SubHeading title="Trigger types" />
          <div className="space-y-4 my-6">
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1 flex items-center gap-2"><Key className="w-4 h-4 text-[#7c3aed]" /> Webhook</h4>
              <p className="text-xs text-[#888] leading-relaxed">HTTP endpoint that invokes your agent when called. Connect to GitHub, Stripe, Slack, or any service that sends webhooks. The request payload is passed as context to the agent.</p>
            </div>
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1 flex items-center gap-2"><Clock className="w-4 h-4 text-green-400" /> Scheduled (Cron)</h4>
              <p className="text-xs text-[#888] leading-relaxed">Run your agent on a schedule using cron expressions. Great for daily reports, periodic data processing, health checks, and recurring tasks.</p>
            </div>
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1 flex items-center gap-2"><Terminal className="w-4 h-4 text-blue-400" /> Slash Command</h4>
              <p className="text-xs text-[#888] leading-relaxed">Register slash commands in Slack or Discord that invoke your agent. Users type <code className="text-xs bg-[#0a0a0a] px-1 rounded">/ask-support how do I reset my password?</code> and get an agent response inline.</p>
            </div>
            <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5">
              <h4 className="font-semibold text-sm mb-1 flex items-center gap-2"><Zap className="w-4 h-4 text-yellow-400" /> Event</h4>
              <p className="text-xs text-[#888] leading-relaxed">Trigger agents from internal Bonito events — new document indexed in a KB, agent error threshold exceeded, or cost alert fired.</p>
            </div>
          </div>

          <SubHeading title="Creating triggers" />
          <CodeBlock
            code={`# Create a webhook trigger
bonito triggers create \\
  --agent-id ag_abc123 \\
  --type webhook \\
  --name "GitHub PR Review"

# Output: Webhook URL → https://getbonito.com/hooks/tr_wh_abc123

# Create a scheduled trigger (daily at 9 AM UTC)
bonito triggers create \\
  --agent-id ag_abc123 \\
  --type cron \\
  --schedule "0 9 * * *" \\
  --name "Daily Summary" \\
  --input "Generate a summary of yesterday's support tickets"

# Create a slash command trigger
bonito triggers create \\
  --agent-id ag_abc123 \\
  --type slash-command \\
  --platform slack \\
  --command "/ask-support" \\
  --name "Slack Support"

# List triggers for an agent
bonito triggers list --agent-id ag_abc123`}
          />

          <SubHeading title="Webhook payload" />
          <Paragraph>
            When a webhook trigger fires, the HTTP request body is passed to the agent as context. You can define a template to extract specific fields:
          </Paragraph>
          <CodeBlock
            language="json"
            code={`{
  "trigger_id": "tr_wh_abc123",
  "payload_template": "New {{event}} from {{repository.full_name}}: {{pull_request.title}}",
  "headers_to_forward": ["X-GitHub-Event"],
  "secret": "whsec_xxxxxxxx"
}`}
          />
          <Callout variant="tip">
            Use the <code className="text-xs">secret</code> field to verify webhook signatures. Bonito validates the HMAC signature on incoming requests and rejects unverified payloads.
          </Callout>

          {/* ── Observability ── */}
          <SectionHeading id="observability" title="Observability" />
          <Paragraph>
            Bonito provides built-in observability for every request flowing through the gateway and every agent interaction. Track tokens, latency, costs, and errors across your entire AI stack without any additional tooling.
          </Paragraph>

          <SubHeading title="Request tracing" />
          <Paragraph>
            Every API request gets a unique trace ID. View the full lifecycle of a request — from gateway receipt through provider routing to response delivery:
          </Paragraph>
          <CodeBlock
            code={`# View recent requests
bonito logs list --limit 20

# Get details for a specific trace
bonito logs get --trace-id tr_xxxxxxxxxxxx

# Filter by model, status, or time range
bonito logs list \\
  --model "claude-3-sonnet" \\
  --status error \\
  --since "2024-01-15T00:00:00Z"`}
          />

          <SubHeading title="What&apos;s tracked" />
          <div className="bg-[#111] border border-[#1a1a1a] rounded-lg p-4 my-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[#888] border-b border-[#1a1a1a]">
                  <th className="text-left py-2 pr-4 font-medium">Metric</th>
                  <th className="text-left py-2 font-medium">Description</th>
                </tr>
              </thead>
              <tbody className="text-[#ccc] text-xs">
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">Tokens (in/out)</td>
                  <td className="py-2">Input and output token counts per request</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">Latency</td>
                  <td className="py-2">Time to first token (TTFT) and total response time</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">Cost</td>
                  <td className="py-2">Estimated cost per request based on provider pricing</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">Model</td>
                  <td className="py-2">Which model and provider served the request</td>
                </tr>
                <tr className="border-b border-[#1a1a1a]/50">
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">Status</td>
                  <td className="py-2">Success, error, rate-limited, or timed-out</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4 font-mono text-[#7c3aed]">Agent</td>
                  <td className="py-2">Which BonBon agent handled the request (if applicable)</td>
                </tr>
              </tbody>
            </table>
          </div>

          <SubHeading title="Per-agent analytics" />
          <Paragraph>
            Each BonBon agent has its own analytics dashboard showing conversation volume, average response time, token usage, cost breakdown, and error rates over time.
          </Paragraph>
          <CodeBlock
            code={`# Get agent analytics
bonito agents analytics --id ag_abc123 \\
  --period 7d

# Export analytics as CSV
bonito agents analytics --id ag_abc123 \\
  --period 30d \\
  --format csv > agent-analytics.csv`}
          />

          <SubHeading title="Cost monitoring" />
          <Paragraph>
            Observability integrates with Cost Management to show real-time spend. Set budget alerts per agent, per model, or globally:
          </Paragraph>
          <CodeBlock
            code={`# Set a per-agent budget alert
bonito alerts create \\
  --scope agent \\
  --agent-id ag_abc123 \\
  --threshold 500 \\
  --period monthly \\
  --notify email,in-app

# Set a global daily spend alert
bonito alerts create \\
  --scope global \\
  --threshold 100 \\
  --period daily`}
          />
          <Callout variant="info">
            Observability data is retained for 90 days by default. Contact support for extended retention or data export to your own analytics pipeline.
          </Callout>

          {/* ── Troubleshooting ── */}
          <SectionHeading id="troubleshooting" title="Troubleshooting" />

          <SubHeading title='"Connected! Found 0 models"' />
          <Paragraph>
            Your credentials connected successfully, but model listing failed silently. Check:
          </Paragraph>
          <ul className="space-y-2 my-4">
            {[
              "Azure: Make sure your Endpoint URL is an Azure OpenAI resource endpoint with a custom subdomain, not a generic regional endpoint. Also verify the resource group is correct.",
              "GCP: Ensure the Vertex AI API is enabled in your project.",
              "AWS: Verify your IAM user has Bedrock permissions and you're in a region where Bedrock is available.",
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-[#ccc]">
                <ArrowRight className="w-3.5 h-3.5 text-[#7c3aed] mt-1 shrink-0" />
                <span className="leading-relaxed">{item}</span>
              </li>
            ))}
          </ul>

          <SubHeading title="Models showing a 🔒 lock icon" />
          <Paragraph>
            The model exists in your provider&apos;s catalog but isn&apos;t enabled. Click the Enable button in Bonito, or enable it directly in your cloud console (AWS Bedrock → Model Access, Azure → create a deployment, GCP → enable the Vertex AI API).
          </Paragraph>

          <SubHeading title="Playground returns a 500 error" />
          <Paragraph>
            This typically means the model isn&apos;t a chat model (embedding or completion-only models can&apos;t be used in the Playground), the model isn&apos;t enabled in your account, or the model isn&apos;t available in your region.
          </Paragraph>

          <SubHeading title="Rate limit or timeout errors" />
          <Paragraph>
            Wait 30–60 seconds and try again. This can happen when making many rapid changes. If 502 errors persist, the backend service may need attention — contact <a href="mailto:support@getbonito.com" className="text-[#7c3aed] hover:underline">support@getbonito.com</a>.
          </Paragraph>

          {/* ── Help ── */}
          <div className="mt-16 bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
            <h3 className="font-semibold mb-2">Need more help?</h3>
            <p className="text-sm text-[#888] mb-4">
              Can&apos;t find what you&apos;re looking for? Our team is here to help.
            </p>
            <div className="flex items-center justify-center gap-4 flex-wrap">
              <Link
                href="/contact"
                className="px-5 py-2.5 rounded-lg bg-[#7c3aed] text-white text-sm font-semibold hover:bg-[#6d28d9] transition"
              >
                Contact Support
              </Link>
              <a
                href="mailto:support@getbonito.com"
                className="px-5 py-2.5 rounded-lg border border-[#333] text-sm font-medium text-[#ccc] hover:border-[#7c3aed] transition"
              >
                support@getbonito.com
              </a>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
