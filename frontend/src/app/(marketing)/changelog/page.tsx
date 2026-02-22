"use client";

import { motion } from "framer-motion";
import { Zap, Cloud, DollarSign, Shield, BarChart3, Bot, Rocket, Lock, Route, Bell, Terminal } from "lucide-react";

const entries = [
  {
    date: "February 2026",
    items: [
      { icon: Rocket, title: "Deployment Provisioning", desc: "Deploy AI models directly into your cloud from the Bonito UI. AWS Provisioned Throughput (reserved capacity), Azure OpenAI deployments (Standard/GlobalStandard TPM), and GCP Vertex AI serverless — all without leaving the dashboard." },
      { icon: Lock, title: "Least-Privilege Permissions", desc: "Two IAM modes for every provider: Quick Start (managed roles for fast setup) and Enterprise (separate least-privilege policies per capability). Only grant the exact permissions each feature needs." },
      { icon: Route, title: "Routing Policies", desc: "Cost-optimized routing, failover chains, and A/B testing with weight-based model selection. Route requests intelligently across providers and models with dry-run testing." },
      { icon: Bell, title: "Notifications", desc: "In-app notification system for deployment lifecycle events, spend alerts, model activation confirmations, and provider health updates. Configurable alert rules with email and in-app delivery." },
      { icon: Terminal, title: "Bonito CLI", desc: "Python CLI (bonito-cli) for terminal-based management. Manage providers, models, gateway keys, routing policies, and costs from your terminal or CI/CD pipelines." },
      { icon: Bot, title: "AI Copilot", desc: "Natural language assistant for managing your AI infrastructure. Ask questions about costs, configure routing, and analyze provider health." },
      { icon: BarChart3, title: "Enhanced Cost Analytics", desc: "Breakdown by model, provider, team, and application. Export reports in CSV and PDF formats." },
    ],
  },
  {
    date: "January 2026",
    items: [
      { icon: Zap, title: "One-Click Model Activation", desc: "Enable models directly from the Bonito dashboard without leaving to your cloud console. Supports individual enable and bulk activation (up to 20 models at once). Works across AWS Bedrock entitlements, Azure deployments, and GCP API enablement." },
      { icon: Zap, title: "API Gateway v2", desc: "OpenAI-compatible gateway endpoint with intelligent request routing, automatic failover, and support for routing policies. One API key for all your providers." },
      { icon: Cloud, title: "Google Vertex AI Support", desc: "Full integration with Google Vertex AI including Gemini models. Connect and manage alongside your other providers." },
      { icon: Shield, title: "Audit Trail", desc: "Complete audit logging for every API call, configuration change, and team action. Export for compliance reporting." },
    ],
  },
  {
    date: "December 2025",
    items: [
      { icon: DollarSign, title: "Budget Alerts", desc: "Set spending thresholds per provider, per team, or globally. Receive email and in-app notifications before you exceed them." },
      { icon: Cloud, title: "Azure OpenAI Integration", desc: "Connect your Azure OpenAI deployments alongside AWS Bedrock for multi-cloud routing strategies." },
    ],
  },
  {
    date: "November 2025",
    items: [
      { icon: Zap, title: "Public Launch", desc: "Bonito is live! Unified multi-cloud AI management with support for AWS Bedrock, Azure OpenAI, and Google Cloud Vertex AI." },
    ],
  },
];

export default function ChangelogPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12">
      <section className="pt-20 pb-16">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-6xl font-bold tracking-tight"
        >
          Changelog
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-4 text-lg text-[#888]"
        >
          What&apos;s new in Bonito. We ship fast.
        </motion.p>
      </section>

      <section className="pb-24">
        <div className="space-y-16">
          {entries.map((entry, ei) => (
            <motion.div
              key={entry.date}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: ei * 0.1 }}
            >
              <h2 className="text-sm font-semibold text-[#7c3aed] uppercase tracking-wider mb-6">{entry.date}</h2>
              <div className="space-y-6 border-l-2 border-[#1a1a1a] pl-6">
                {entry.items.map((item) => (
                  <div key={item.title} className="relative">
                    <div className="absolute -left-[31px] top-1 w-4 h-4 rounded-full bg-[#7c3aed]/20 border-2 border-[#7c3aed] flex items-center justify-center">
                      <div className="w-1.5 h-1.5 rounded-full bg-[#7c3aed]" />
                    </div>
                    <h3 className="font-semibold mb-1">{item.title}</h3>
                    <p className="text-sm text-[#888] leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
