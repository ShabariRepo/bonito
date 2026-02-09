"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { BookOpen, Zap, Cloud, DollarSign, Shield, Key, ArrowRight, Terminal } from "lucide-react";

const guides = [
  {
    icon: Zap,
    title: "Getting Started",
    desc: "Create your account, connect your first AI provider, and make your first API call in under 5 minutes.",
    sections: ["Create an account", "Add a provider (OpenAI, Anthropic, etc.)", "Generate an API key", "Make your first request through the gateway"],
  },
  {
    icon: Terminal,
    title: "API Reference",
    desc: "Complete reference for the Bonito REST API including authentication, providers, routing, and analytics endpoints.",
    sections: ["Authentication & API keys", "Provider management", "Gateway routing", "Cost & analytics endpoints"],
  },
];

const concepts = [
  { icon: Cloud, title: "Providers", desc: "Connect and manage multiple AI providers from a single dashboard. Supported: OpenAI, Anthropic, AWS Bedrock, Google Vertex, Azure OpenAI, Cohere." },
  { icon: Key, title: "API Gateway", desc: "Route AI requests intelligently across providers with automatic failover, load balancing, and rate limiting." },
  { icon: DollarSign, title: "Cost Management", desc: "Track spending across all providers in real-time. Set budgets, receive alerts, and get optimization recommendations." },
  { icon: Shield, title: "Compliance & Governance", desc: "Audit trails, access controls, and compliance reporting. Enterprise plans include SOC2 and HIPAA readiness." },
];

export default function DocsPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12">
      {/* Hero */}
      <section className="pt-20 pb-16">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-6xl font-bold tracking-tight"
        >
          Documentation
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-4 text-lg text-[#888] max-w-2xl"
        >
          Everything you need to integrate Bonito into your AI infrastructure.
        </motion.p>
      </section>

      {/* Quick Start */}
      <section className="pb-16">
        <div className="bg-gradient-to-br from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-2xl p-8 md:p-12">
          <h2 className="text-2xl font-bold mb-3">Quick Start</h2>
          <p className="text-[#888] mb-6">Get up and running in 5 minutes.</p>
          <div className="bg-[#0a0a0a] rounded-lg p-6 font-mono text-sm text-[#ccc] overflow-x-auto">
            <div className="text-[#666]"># 1. Sign up at getbonito.com/register</div>
            <div className="text-[#666]"># 2. Add your first provider in the dashboard</div>
            <div className="text-[#666]"># 3. Generate a gateway API key</div>
            <div className="text-[#666]"># 4. Route requests through Bonito</div>
            <div className="mt-3">
              <span className="text-[#7c3aed]">curl</span> -X POST https://gateway.getbonito.com/v1/chat/completions \
            </div>
            <div className="pl-4">-H &quot;Authorization: Bearer YOUR_BONITO_KEY&quot; \</div>
            <div className="pl-4">-H &quot;Content-Type: application/json&quot; \</div>
            <div className="pl-4">-d &apos;&#123;&quot;model&quot;: &quot;gpt-4&quot;, &quot;messages&quot;: [&#123;&quot;role&quot;: &quot;user&quot;, &quot;content&quot;: &quot;Hello&quot;&#125;]&#125;&apos;</div>
          </div>
        </div>
      </section>

      {/* Guides */}
      <section className="pb-24">
        <h2 className="text-3xl font-bold mb-8">Guides</h2>
        <div className="grid md:grid-cols-2 gap-6">
          {guides.map((guide, i) => (
            <motion.div
              key={guide.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-8 hover:border-[#7c3aed]/30 transition"
            >
              <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center mb-4">
                <guide.icon className="w-5 h-5 text-[#7c3aed]" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{guide.title}</h3>
              <p className="text-sm text-[#888] mb-4">{guide.desc}</p>
              <ul className="space-y-2">
                {guide.sections.map((s) => (
                  <li key={s} className="text-sm text-[#666] flex items-center gap-2">
                    <ArrowRight className="w-3 h-3 text-[#7c3aed]" />
                    {s}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Key Concepts */}
      <section className="pb-24">
        <h2 className="text-3xl font-bold mb-8">Key Concepts</h2>
        <div className="grid md:grid-cols-2 gap-6">
          {concepts.map((c, i) => (
            <motion.div
              key={c.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 hover:border-[#7c3aed]/30 transition"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center flex-shrink-0">
                  <c.icon className="w-5 h-5 text-[#7c3aed]" />
                </div>
                <div>
                  <h3 className="font-semibold mb-1">{c.title}</h3>
                  <p className="text-sm text-[#888] leading-relaxed">{c.desc}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Help */}
      <section className="pb-24 text-center">
        <p className="text-[#888]">
          Need help?{" "}
          <Link href="/contact" className="text-[#7c3aed] hover:underline">Contact our team</Link>
          {" "}or join our community Discord.
        </p>
      </section>
    </div>
  );
}
