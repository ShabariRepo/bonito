"use client";

import { motion } from "framer-motion";
import { Shield, Code, DollarSign, Zap, Users, Globe, Rocket, Route } from "lucide-react";

const values = [
  { icon: Shield, title: "Security-First", desc: "We never store your AI request or response data. Encryption everywhere, least-privilege IAM templates, and compliance built in." },
  { icon: Code, title: "Developer Experience", desc: "OpenAI-compatible gateway, Python CLI, clean APIs, and an intuitive dashboard. Tools that get out of your way so you can ship faster." },
  { icon: DollarSign, title: "Cost Transparency", desc: "No hidden fees, no surprise bills. Full visibility into every dollar spent on AI across all your cloud providers." },
];

const capabilities = [
  { icon: Globe, title: "Multi-Cloud Gateway", desc: "One API endpoint for AWS Bedrock, Azure OpenAI, and GCP Vertex AI. OpenAI-compatible format works with any existing SDK." },
  { icon: Route, title: "Intelligent Routing", desc: "Cost-optimized routing, failover chains, and A/B testing across models and providers. Route traffic based on cost, latency, or capability." },
  { icon: Rocket, title: "Deployment Provisioning", desc: "Deploy models directly into your cloud — AWS Provisioned Throughput, Azure OpenAI deployments, GCP serverless — all from one dashboard." },
  { icon: Shield, title: "Enterprise IAM", desc: "Quick Start managed roles for evaluation, or Enterprise least-privilege policies with exact minimum permissions per capability. Terraform templates included." },
];

const stats = [
  { value: "3", label: "Cloud providers" },
  { value: "100+", label: "Models available" },
  { value: "99.9%", label: "Uptime SLA" },
  { value: "< 10ms", label: "Routing overhead" },
];

export default function AboutPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12">
      {/* Hero */}
      <section className="pt-20 pb-16 max-w-3xl">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-6xl font-bold tracking-tight"
        >
          Making enterprise AI
          <span className="text-[#7c3aed]"> accessible</span> and
          <span className="text-[#7c3aed]"> manageable</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-6 text-lg text-[#888] leading-relaxed"
        >
          Bonito is the unified control plane for multi-cloud AI. Connect your AWS Bedrock, Azure OpenAI, and
          Google Cloud Vertex AI accounts, then manage all your models, deployments, routing, and costs from a
          single platform — so you can focus on building great products instead of wrangling providers.
        </motion.p>
      </section>

      {/* What We Do */}
      <section className="pb-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl font-bold mb-6">What Bonito Does</h2>
            <div className="space-y-4 text-[#888] leading-relaxed">
              <p>
                Modern AI teams use models across multiple cloud providers — Claude on AWS Bedrock, GPT-4o
                on Azure OpenAI, Gemini on GCP Vertex AI. Managing them separately means scattered dashboards,
                unpredictable costs, and fragile integrations.
              </p>
              <p>
                Bonito unifies all of this. One OpenAI-compatible API gateway with intelligent routing and failover.
                One dashboard for cost tracking across every provider. One place to deploy models, activate new ones,
                set up routing policies, and manage your entire AI stack.
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.2 + i * 0.1 }}
                className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center"
              >
                <div className="text-2xl md:text-3xl font-bold text-[#7c3aed]">{stat.value}</div>
                <div className="text-xs text-[#666] mt-1">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Capabilities */}
      <section className="pb-24">
        <h2 className="text-3xl font-bold mb-12">Platform Capabilities</h2>
        <div className="grid sm:grid-cols-2 gap-6">
          {capabilities.map((c, i) => (
            <motion.div
              key={c.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6"
            >
              <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center mb-4">
                <c.icon className="w-5 h-5 text-[#7c3aed]" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{c.title}</h3>
              <p className="text-sm text-[#888] leading-relaxed">{c.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Values */}
      <section className="pb-24">
        <h2 className="text-3xl font-bold mb-12">Our Values</h2>
        <div className="grid md:grid-cols-3 gap-6">
          {values.map((v, i) => (
            <motion.div
              key={v.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-8"
            >
              <div className="w-12 h-12 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center mb-5">
                <v.icon className="w-6 h-6 text-[#7c3aed]" />
              </div>
              <h3 className="text-lg font-semibold mb-3">{v.title}</h3>
              <p className="text-sm text-[#888] leading-relaxed">{v.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Founder */}
      <section className="pb-24">
        <div className="bg-[#111] border border-[#1a1a1a] rounded-2xl p-10 md:p-12">
          <div className="grid md:grid-cols-[auto_1fr] gap-8 md:gap-12 items-start">
            {/* Founder identity column */}
            <div className="flex flex-col items-center md:items-start gap-3 shrink-0">
              <div className="h-28 w-28 rounded-2xl bg-gradient-to-br from-[#7c3aed]/30 to-[#7c3aed]/10 border border-[#7c3aed]/30 flex items-center justify-center text-[#a78bfa] text-3xl font-semibold tracking-tight">
                SS
              </div>
              <div className="text-center md:text-left">
                <p className="text-base font-semibold text-[#f5f0e8]">Shabari Shenoy</p>
                <p className="text-xs text-[#888]">Founder &amp; CEO</p>
              </div>
              <a
                href="https://www.linkedin.com/in/shabari-shenoy/"
                target="_blank"
                rel="noreferrer"
                className="text-xs text-[#888] hover:text-[#a78bfa] transition mt-1"
              >
                LinkedIn &rarr;
              </a>
            </div>

            {/* Bio column */}
            <div>
              <p className="text-xs uppercase tracking-wider text-[#7c3aed] font-semibold mb-3">
                The founder
              </p>
              <h2 className="text-2xl md:text-3xl font-bold tracking-tight mb-5 leading-tight">
                A career spent inside large enterprise stacks — and what's missing in every one of them.
              </h2>
              <div className="space-y-4 text-[#bbb] leading-relaxed">
                <p>
                  Shabari has spent the last decade building and operating production
                  infrastructure across financial services, telecommunications, and
                  enterprise software — most recently at TD and Fidelity (via Cognizant).
                  Across every engagement the same pattern: AI workloads sprawling across
                  three or four clouds, no consolidated view of cost, no audit trail
                  that compliance can answer with, and no team comfortable making the
                  routing decisions that matter.
                </p>
                <p>
                  Bonito is the layer Shabari kept watching enterprises try (and fail) to
                  build internally. One ledger across OpenAI, Anthropic, Bedrock, Vertex,
                  Azure, and Groq. One audit log. One control surface. Structurally
                  cloud-neutral because no hyperscaler can be — their lock-in margins
                  depend on it.
                </p>
                <p className="text-[#888] italic">
                  In stealth with enterprise design partners since February 2026.
                  Reach Shabari directly at{" "}
                  <a
                    href="mailto:shabari@bonito.ai"
                    className="text-[#ccc] not-italic hover:text-[#a78bfa] transition"
                  >
                    shabari@bonito.ai
                  </a>
                  .
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
