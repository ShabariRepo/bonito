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
curl -X POST https://gateway.getbonito.com/v1/chat/completions \\
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
          <CodeBlock code="POST https://gateway.getbonito.com/v1/chat/completions" />

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
    base_url="https://gateway.getbonito.com/v1",
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
            code={`curl https://gateway.getbonito.com/v1/chat/completions \\
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
