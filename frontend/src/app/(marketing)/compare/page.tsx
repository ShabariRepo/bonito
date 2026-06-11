"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, GitCompareArrows, Shield, Route, Bot, BarChart3, Cloud } from "lucide-react";
import { competitors } from "./competitors";

const categoryIcons: Record<string, typeof Shield> = {
  langfuse: BarChart3,
  helicone: BarChart3,
  portkey: Route,
  langsmith: GitCompareArrows,
  arize: BarChart3,
  litellm: Route,
  martian: Route,
  "kong-ai-gateway": Cloud,
  apigee: Cloud,
  zuplo: Route,
};

export default function ComparePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-12">
      {/* Hero */}
      <section className="pt-16 pb-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <GitCompareArrows className="w-5 h-5 text-[#7c3aed]" />
            </div>
            <span className="text-sm font-medium text-[#7c3aed] uppercase tracking-wider">Comparisons</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            How Bonito Compares
          </h1>
          <p className="mt-4 text-lg text-[#888] max-w-3xl">
            Bonito is the only neutral control plane above the hyperscalers. Six AI providers live in one OpenAI-compatible gateway — OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, Groq — with cross-provider routing, immutable audit ledger, RAG knowledge bases, governed Bonobot agents, and one cost ledger across all of them. The comparisons below cover the three categories of competitor: developer-tier observability and routing tools, API-gateway incumbents extending into LLM, and single-cloud platforms.
          </p>
        </motion.div>
      </section>

      {/* Why Bonito is different */}
      <section className="pb-12">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            {
              icon: Route,
              title: "AI Gateway + Routing",
              description: "Intelligent cost-optimized routing, failover chains, and A/B testing across all providers.",
            },
            {
              icon: Bot,
              title: "Governed AI Agents",
              description: "BonBon and Bonobot agents with default-deny security, budget controls, and audit trails.",
            },
            {
              icon: Cloud,
              title: "Structural Cloud-Neutrality",
              description: "The only position above AWS Bedrock, Google Vertex AI, and Azure AI that no hyperscaler can replicate without killing its own lock-in.",
            },
            {
              icon: Shield,
              title: "Enterprise Governance + Audit",
              description: "Immutable audit ledger across every model call, agent run, KB query. SSO/SAML (4 IdPs), RBAC, SOC-2 path, HIPAA, GDPR.",
            },
          ].map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5"
            >
              <div className="w-9 h-9 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center mb-3">
                <item.icon className="w-4.5 h-4.5 text-[#7c3aed]" />
              </div>
              <h3 className="font-semibold text-sm mb-1">{item.title}</h3>
              <p className="text-xs text-[#888] leading-relaxed">{item.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Competitor cards */}
      <section className="pb-24">
        <h2 className="text-2xl font-bold mb-8">Detailed Comparisons</h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {competitors.map((competitor, i) => {
            const Icon = categoryIcons[competitor.slug] || BarChart3;
            return (
              <motion.div
                key={competitor.slug}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.05 * i }}
              >
                <Link
                  href={`/compare/${competitor.slug}`}
                  className="block bg-[#111] border border-[#1a1a1a] hover:border-[#7c3aed]/40 rounded-xl p-6 transition-all group h-full"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-9 h-9 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
                      <Icon className="w-4.5 h-4.5 text-[#7c3aed]" />
                    </div>
                    <h3 className="font-semibold text-lg">
                      Bonito vs {competitor.name}
                    </h3>
                  </div>
                  <p className="text-sm text-[#888] mb-2">{competitor.tagline}</p>
                  <p className="text-sm text-[#666] leading-relaxed mb-4 line-clamp-3">
                    {competitor.description}
                  </p>
                  <div className="flex items-center gap-1.5 text-sm text-[#7c3aed] group-hover:gap-2.5 transition-all">
                    View full comparison <ArrowRight className="w-4 h-4" />
                  </div>
                </Link>
              </motion.div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
