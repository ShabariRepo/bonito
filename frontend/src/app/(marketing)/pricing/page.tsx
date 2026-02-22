"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Check, X, ArrowRight, HelpCircle, Bot, Zap } from "lucide-react";
import { Fragment, useState } from "react";

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "For individuals exploring multi-cloud AI management.",
    features: [
      "1 cloud provider connection",
      "100 gateway API calls / month",
      "Model catalog & playground",
      "Standard request logging",
      "Community support (Discord)",
      "1 team member",
    ],
    cta: "Get Started Free",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$499",
    period: "/mo",
    description: "For teams shipping AI products across multiple providers.",
    features: [
      "Up to 3 cloud providers",
      "50,000 gateway API calls / month",
      "Intelligent routing policies (cost, failover, A/B)",
      "Deployment provisioning (AWS, Azure, GCP)",
      "One-click model activation",
      "AI Context — knowledge base with RAG",
      "Cost analytics & budget alerts",
      "AI copilot assistant",
      "CLI tool (bonito-cli)",
      "Audit trail & compliance logging",
      "In-app & email notifications",
      "Email support (24h response)",
      "Unlimited team members",
    ],
    cta: "Start Free Trial",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$2K–$5K",
    period: "/mo",
    description: "For organizations with complex AI infrastructure and governance needs.",
    features: [
      "Unlimited cloud providers",
      "Unlimited gateway API calls",
      "Advanced routing & load balancing",
      "SSO / SAML with JIT provisioning",
      "Role-based access control (RBAC)",
      "AI Context — unlimited KBs with team isolation",
      "Least-privilege IAM templates (Terraform)",
      "99.9% SLA guarantee",
      "Dedicated support engineer",
      "Custom integrations & webhooks",
      "Compliance (SOC2, HIPAA ready)",
      "On-premise deployment option",
      "Priority feature requests",
      "Quarterly business reviews",
    ],
    cta: "Contact Sales",
    highlighted: false,
  },
];

const agentPlans = [
  {
    name: "Hosted Agent",
    price: "$349",
    period: "/mo per agent",
    description: "AI agents running on Bonito infrastructure. Fully managed.",
    features: [
      "Managed agent hosting",
      "Up to 5 resource connectors",
      "Scoped AI Context per agent group",
      "Budget enforcement & rate limiting",
      "Session history & audit trail",
      "Visual agent canvas (drag & drop)",
      "Agent-to-agent connections",
      "Triggers (schedule, webhook, event)",
    ],
    cta: "Add to Pro or Enterprise",
  },
  {
    name: "VPC Agent",
    price: "$599",
    period: "/mo per agent",
    description: "Self-hosted agents in your own VPC. Full data sovereignty.",
    features: [
      "Everything in Hosted Agent",
      "Deployed in your cloud VPC",
      "All connector tiers + custom REST/GraphQL",
      "Zero data leaves your network",
      "Custom tool policies",
      "Dedicated compute resources",
      "SSO-scoped agent access",
      "Enterprise SLA included",
    ],
    cta: "Contact Sales",
  },
];

const comparisonFeatures = [
  // ── Core Platform
  { category: "Core Platform", name: "Cloud Providers", free: "1", pro: "3", enterprise: "Unlimited" },
  { category: "Core Platform", name: "Gateway API Calls / month", free: "100", pro: "50,000", enterprise: "Unlimited" },
  { category: "Core Platform", name: "Team Members", free: "1", pro: "Unlimited", enterprise: "Unlimited" },
  { category: "Core Platform", name: "Model Catalog & Playground", free: true, pro: true, enterprise: true },
  { category: "Core Platform", name: "One-Click Model Activation", free: true, pro: true, enterprise: true },
  // ── AI Gateway
  { category: "AI Gateway", name: "Unified API Endpoint (OpenAI-compatible)", free: true, pro: true, enterprise: true },
  { category: "AI Gateway", name: "Routing Policies (cost, latency, failover)", free: false, pro: true, enterprise: true },
  { category: "AI Gateway", name: "Deployment Provisioning", free: false, pro: true, enterprise: true },
  { category: "AI Gateway", name: "A/B Testing & Weighted Routing", free: false, pro: true, enterprise: true },
  { category: "AI Gateway", name: "Per-Key Model Restrictions", free: false, pro: true, enterprise: true },
  { category: "AI Gateway", name: "Rate Limiting (per key & org)", free: false, pro: true, enterprise: true },
  { category: "AI Gateway", name: "Advanced Load Balancing", free: false, pro: false, enterprise: true },
  // ── AI Context (RAG)
  { category: "AI Context (RAG)", name: "Knowledge Base Upload & Indexing", free: false, pro: true, enterprise: true },
  { category: "AI Context (RAG)", name: "Vector Search (pgvector)", free: false, pro: true, enterprise: true },
  { category: "AI Context (RAG)", name: "Context Injection at Query Time", free: false, pro: true, enterprise: true },
  { category: "AI Context (RAG)", name: "Knowledge Bases per Org", free: false, pro: "5", enterprise: "Unlimited" },
  { category: "AI Context (RAG)", name: "Team-Isolated Knowledge Bases", free: false, pro: false, enterprise: true },
  // ── Analytics & Cost
  { category: "Analytics & Cost", name: "Cost Analytics & Breakdown", free: false, pro: true, enterprise: true },
  { category: "Analytics & Cost", name: "Budget Alerts & Spend Caps", free: false, pro: true, enterprise: true },
  { category: "Analytics & Cost", name: "Usage Trends & Forecasting", free: false, pro: true, enterprise: true },
  { category: "Analytics & Cost", name: "Per-Team Cost Attribution", free: false, pro: false, enterprise: true },
  // ── Security & Compliance
  { category: "Security & Compliance", name: "Audit Trail", free: false, pro: true, enterprise: true },
  { category: "Security & Compliance", name: "SSO / SAML", free: false, pro: false, enterprise: true },
  { category: "Security & Compliance", name: "Role-Based Access Control (RBAC)", free: false, pro: false, enterprise: true },
  { category: "Security & Compliance", name: "IaC Templates (Terraform)", free: false, pro: false, enterprise: true },
  { category: "Security & Compliance", name: "SLA Guarantee", free: false, pro: false, enterprise: "99.9%" },
  { category: "Security & Compliance", name: "Compliance Ready (SOC2, HIPAA)", free: false, pro: false, enterprise: true },
  { category: "Security & Compliance", name: "On-Premise Deployment", free: false, pro: false, enterprise: true },
  // ── Tools & Integrations
  { category: "Tools & Integrations", name: "AI Copilot Assistant", free: false, pro: true, enterprise: true },
  { category: "Tools & Integrations", name: "CLI Tool (bonito-cli)", free: false, pro: true, enterprise: true },
  { category: "Tools & Integrations", name: "In-App & Email Notifications", free: false, pro: true, enterprise: true },
  { category: "Tools & Integrations", name: "Custom Integrations & Webhooks", free: false, pro: false, enterprise: true },
  // ── Bonobot (AI Agents)
  { category: "Bonobot AI Agents", name: "Visual Agent Canvas", free: false, pro: "Add-on", enterprise: "Add-on" },
  { category: "Bonobot AI Agents", name: "Agent Execution Engine", free: false, pro: "Add-on", enterprise: "Add-on" },
  { category: "Bonobot AI Agents", name: "Per-Agent AI Context & Budget", free: false, pro: "Add-on", enterprise: "Add-on" },
  { category: "Bonobot AI Agents", name: "Agent-to-Agent Connections", free: false, pro: "Add-on", enterprise: "Add-on" },
  { category: "Bonobot AI Agents", name: "Resource Connectors", free: false, pro: "5 / agent", enterprise: "Unlimited" },
  { category: "Bonobot AI Agents", name: "VPC-Deployed Agents", free: false, pro: false, enterprise: "Add-on" },
  // ── Support
  { category: "Support", name: "Community Discord", free: true, pro: true, enterprise: true },
  { category: "Support", name: "Email Support (24h)", free: false, pro: true, enterprise: true },
  { category: "Support", name: "Dedicated Support Engineer", free: false, pro: false, enterprise: true },
  { category: "Support", name: "Priority Feature Requests", free: false, pro: false, enterprise: true },
  { category: "Support", name: "Quarterly Business Reviews", free: false, pro: false, enterprise: true },
];

const faqs = [
  {
    q: "What is Bonito?",
    a: "Bonito is a unified AI control plane that connects your cloud AI providers — AWS Bedrock, Azure OpenAI, and Google Cloud Vertex AI — and lets you manage everything from a single dashboard. You get intelligent routing, deployment provisioning, knowledge base RAG, AI agents, cost tracking, and governance controls — all through one API endpoint.",
  },
  {
    q: "How does billing work?",
    a: "You are billed monthly based on your plan tier. The Free plan requires no credit card. Pro and Enterprise plans are billed at the start of each billing cycle. Bonobot agents are billed per-agent per-month as an add-on. Bonito charges for the platform — your AI provider costs (AWS, Azure, GCP) are billed separately by those providers through your own cloud accounts.",
  },
  {
    q: "What is AI Context?",
    a: "AI Context is our built-in RAG (Retrieval-Augmented Generation) pipeline. Upload your documents — PDFs, text files, markdown — and Bonito automatically chunks, embeds, and indexes them using vector search. When you or your agents make a query, relevant context is injected automatically. Your documents never leave your infrastructure, and every model in your catalog gets access to the same knowledge.",
  },
  {
    q: "What are Bonobot agents?",
    a: "Bonobot is our enterprise AI agent framework. Each agent gets its own system prompt, model selection, knowledge base, tool access, budget, and rate limits. Agents can be connected together for handoffs and workflows, and managed visually on a drag-and-drop canvas. All agent inference routes through Bonito's gateway — so you get the same cost tracking, audit trail, and governance as regular API calls.",
  },
  {
    q: "What's the difference between Hosted and VPC agents?",
    a: "Hosted agents run on Bonito's managed infrastructure — we handle scaling, uptime, and maintenance. VPC agents are deployed into your own cloud VPC, so all data stays within your network. Both use the same agent engine and capabilities. VPC is ideal for organizations with strict data residency or compliance requirements.",
  },
  {
    q: "Can I switch plans at any time?",
    a: "Yes. You can upgrade or downgrade at any time. When upgrading, you get immediate access to new features. When downgrading, your current plan stays active until the end of the billing period.",
  },
  {
    q: "What cloud providers are supported?",
    a: "Bonito supports AWS Bedrock, Azure OpenAI, and Google Cloud Vertex AI. You connect your own cloud accounts and Bonito discovers all available models, handles routing, and tracks costs across providers. We support 380+ models across all three clouds.",
  },
  {
    q: "Do I need to change my cloud setup?",
    a: "Minimally. You need IAM credentials with the right permissions (Bonito offers Quick Start managed roles or Enterprise least-privilege Terraform templates). Your existing cloud resources stay as-is — Bonito connects to them, not the other way around.",
  },
  {
    q: "Is there a free trial for Pro?",
    a: "Yes — Pro comes with a 14-day free trial with full access to all Pro features. No credit card required to start.",
  },
  {
    q: "How does SSO / SAML work?",
    a: "Enterprise customers can configure SAML SSO with any identity provider (Okta, Azure AD, Google Workspace, etc.). Users are automatically provisioned on first login via JIT (Just-In-Time) provisioning. Admins can enforce SSO-only login and set up a break-glass admin account for emergencies.",
  },
  {
    q: "Is my data secure?",
    a: "Absolutely. Bonito never stores your AI request/response data. Prompts and completions pass through the gateway but are never persisted. Credentials are stored in HashiCorp Vault with encryption at rest. Enterprise plans include SOC2 and HIPAA compliance options. Agent knowledge bases use isolated vector stores per organization.",
  },
  {
    q: "Do you offer volume discounts for agents?",
    a: "Yes. Organizations deploying 5+ agents receive 15% off per-agent pricing. At 10+ agents, the discount increases to 25%. Contact sales for custom pricing on larger deployments.",
  },
];

function CellValue({ value }: { value: boolean | string }) {
  if (value === true) return <Check className="w-5 h-5 text-[#7c3aed] mx-auto" />;
  if (value === false) return <X className="w-5 h-5 text-[#333] mx-auto" />;
  return <span className="text-sm text-[#ccc]">{value}</span>;
}

export default function PricingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  // Group features by category for the comparison table
  const categories = Array.from(new Set(comparisonFeatures.map((f) => f.category)));

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12">
      {/* Hero */}
      <section className="pt-20 pb-16 text-center">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-6xl font-bold tracking-tight"
        >
          Simple, transparent pricing
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-4 text-lg text-[#888] max-w-2xl mx-auto"
        >
          Start free, scale when you&apos;re ready. No hidden fees, no surprises.
        </motion.p>
      </section>

      {/* Platform Plan Cards */}
      <section className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto pb-16">
        {plans.map((plan, i) => (
          <motion.div
            key={plan.name}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`rounded-xl p-8 border flex flex-col ${
              plan.highlighted
                ? "bg-[#7c3aed]/5 border-[#7c3aed]/40 ring-1 ring-[#7c3aed]/20"
                : "bg-[#111] border-[#1a1a1a]"
            }`}
          >
            <h3 className="text-lg font-semibold">{plan.name}</h3>
            <p className="text-sm text-[#888] mt-1">{plan.description}</p>
            <div className="mt-6 mb-6">
              <span className="text-4xl font-bold">{plan.price}</span>
              <span className="text-[#888] ml-1">{plan.period}</span>
            </div>
            <ul className="space-y-3 mb-8 flex-1">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-3 text-sm text-[#999]">
                  <Check className="w-4 h-4 text-[#7c3aed] flex-shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href={plan.name === "Enterprise" ? "/contact" : "/register"}
              className={`block text-center py-3 rounded-lg font-semibold transition ${
                plan.highlighted
                  ? "bg-[#7c3aed] hover:bg-[#6d28d9] text-white"
                  : "bg-[#1a1a1a] hover:bg-[#222] text-[#f5f0e8]"
              }`}
            >
              {plan.cta}
            </Link>
          </motion.div>
        ))}
      </section>

      {/* Bonobot Agent Add-on */}
      <section className="pb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-[#7c3aed]/30 bg-[#7c3aed]/10 text-[#7c3aed] text-sm font-medium mb-4">
            <Bot className="w-4 h-4" /> Add-on
          </div>
          <h2 className="text-3xl font-bold">Bonobot — Enterprise AI Agents</h2>
          <p className="mt-3 text-[#888] max-w-2xl mx-auto">
            Deploy intelligent agents scoped to your departments. Each agent gets its own context, models, tools, and budget — all managed through a visual canvas.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {agentPlans.map((plan, i) => (
            <motion.div
              key={plan.name}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.1 }}
              className="rounded-xl p-8 border bg-[#111] border-[#1a1a1a] flex flex-col"
            >
              <div className="flex items-center gap-2 mb-1">
                <Bot className="w-5 h-5 text-[#7c3aed]" />
                <h3 className="text-lg font-semibold">{plan.name}</h3>
              </div>
              <p className="text-sm text-[#888] mt-1">{plan.description}</p>
              <div className="mt-6 mb-6">
                <span className="text-4xl font-bold">{plan.price}</span>
                <span className="text-[#888] ml-1">{plan.period}</span>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-3 text-sm text-[#999]">
                    <Zap className="w-4 h-4 text-[#7c3aed] flex-shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <div className="text-center py-3 rounded-lg font-semibold bg-[#1a1a1a] text-[#888] text-sm">
                {plan.cta}
              </div>
            </motion.div>
          ))}
        </div>

        <p className="text-center text-sm text-[#666] mt-6">
          Volume discounts: 15% off at 5+ agents, 25% off at 10+ agents.{" "}
          <Link href="/contact" className="text-[#7c3aed] hover:text-[#8b5cf6]">
            Contact sales
          </Link>{" "}
          for custom pricing.
        </p>
      </section>

      {/* Comparison Table */}
      <section className="pb-24">
        <h2 className="text-3xl font-bold text-center mb-12">Feature Comparison</h2>
        <div className="overflow-x-auto">
          <table className="w-full max-w-5xl mx-auto">
            <thead>
              <tr className="border-b border-[#1a1a1a]">
                <th className="text-left py-4 px-4 text-sm font-semibold text-[#999]">Feature</th>
                <th className="text-center py-4 px-4 text-sm font-semibold">Free</th>
                <th className="text-center py-4 px-4 text-sm font-semibold text-[#7c3aed]">Pro</th>
                <th className="text-center py-4 px-4 text-sm font-semibold">Enterprise</th>
              </tr>
            </thead>
            <tbody>
              {categories.map((category) => (
                <Fragment key={`cat-${category}`}>
                  <tr className="border-b border-[#1a1a1a]">
                    <td colSpan={4} className="pt-6 pb-2 px-4 text-xs font-bold uppercase tracking-wider text-[#7c3aed]">
                      {category}
                    </td>
                  </tr>
                  {comparisonFeatures
                    .filter((f) => f.category === category)
                    .map((f) => (
                      <tr key={f.name} className="border-b border-[#1a1a1a]/50 hover:bg-[#111] transition">
                        <td className="py-3.5 px-4 text-sm text-[#ccc]">{f.name}</td>
                        <td className="py-3.5 px-4 text-center"><CellValue value={f.free} /></td>
                        <td className="py-3.5 px-4 text-center"><CellValue value={f.pro} /></td>
                        <td className="py-3.5 px-4 text-center"><CellValue value={f.enterprise} /></td>
                      </tr>
                    ))}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* FAQ */}
      <section className="pb-24 max-w-3xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12">Frequently Asked Questions</h2>
        <div className="space-y-3">
          {faqs.map((faq, i) => (
            <div key={i} className="border border-[#1a1a1a] rounded-lg overflow-hidden">
              <button
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-[#111] transition"
              >
                <span className="font-medium text-sm">{faq.q}</span>
                <HelpCircle className={`w-4 h-4 text-[#666] flex-shrink-0 transition-transform ${openFaq === i ? "rotate-180" : ""}`} />
              </button>
              {openFaq === i && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="px-6 pb-4"
                >
                  <p className="text-sm text-[#888] leading-relaxed">{faq.a}</p>
                </motion.div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24">
        <div className="bg-gradient-to-br from-[#7c3aed]/20 to-[#7c3aed]/5 border border-[#7c3aed]/20 rounded-2xl p-12 text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to unify your AI infrastructure?</h2>
          <p className="text-[#888] mb-8 max-w-xl mx-auto">
            Join teams managing 380+ models across AWS, Azure, and GCP from a single control plane. Start free, upgrade anytime.
          </p>
          <Link
            href="/register"
            className="inline-flex items-center gap-2 px-8 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-xl text-lg transition"
          >
            Get Started Free <ArrowRight className="w-5 h-5" />
          </Link>
        </div>
      </section>
    </div>
  );
}
