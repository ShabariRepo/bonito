"use client";

import { motion } from "framer-motion";
import { Shield, Code, DollarSign, Zap, Users, Globe } from "lucide-react";

const values = [
  { icon: Shield, title: "Security-First", desc: "We never store your AI request or response data. Encryption everywhere, compliance built in." },
  { icon: Code, title: "Developer Experience", desc: "Clean APIs, intuitive dashboards, and tools that get out of your way so you can ship faster." },
  { icon: DollarSign, title: "Cost Transparency", desc: "No hidden fees, no surprise bills. Full visibility into every dollar spent on AI infrastructure." },
];

const stats = [
  { value: "50M+", label: "API calls routed" },
  { value: "99.9%", label: "Uptime SLA" },
  { value: "5", label: "Cloud providers" },
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
          Bonito is the unified control plane for multi-cloud AI. We help engineering teams connect,
          route, monitor, and optimize their AI infrastructure from a single platform — so they can
          focus on building great products instead of wrangling providers.
        </motion.p>
      </section>

      {/* What We Do */}
      <section className="pb-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl font-bold mb-6">What Bonito Does</h2>
            <div className="space-y-4 text-[#888] leading-relaxed">
              <p>
                Modern AI teams use multiple providers — OpenAI for GPT, Anthropic for Claude,
                AWS Bedrock for enterprise workloads, Google Vertex for specialized models. Managing
                them separately means scattered dashboards, unpredictable costs, and fragile integrations.
              </p>
              <p>
                Bonito unifies all of this. One API gateway with intelligent routing and failover.
                One dashboard for cost tracking across every provider. One audit trail for compliance.
                One place to manage your entire AI stack.
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

      {/* Team */}
      <section className="pb-24">
        <div className="bg-[#111] border border-[#1a1a1a] rounded-2xl p-12 text-center">
          <Users className="w-12 h-12 text-[#7c3aed] mx-auto mb-6" />
          <h2 className="text-3xl font-bold mb-4">Built by engineers who&apos;ve managed AI at scale</h2>
          <p className="text-[#888] max-w-2xl mx-auto leading-relaxed">
            Our team has built and operated AI infrastructure at companies processing millions of
            requests per day. We know the pain of managing multiple providers, juggling API keys,
            and explaining surprise cloud bills — because we&apos;ve lived it. Bonito is the tool we
            wished existed.
          </p>
        </div>
      </section>
    </div>
  );
}
