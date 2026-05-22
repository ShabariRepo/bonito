"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Check,
  X,
  Minus,
  Shield,
  Zap,
  GitCompareArrows,
  ChevronLeft,
} from "lucide-react";
import { Competitor } from "../competitors";

function FeatureIcon({ value }: { value: string | boolean }) {
  if (value === true)
    return (
      <span className="flex items-center justify-center w-6 h-6 rounded-full bg-green-500/10">
        <Check className="w-3.5 h-3.5 text-green-400" />
      </span>
    );
  if (value === false)
    return (
      <span className="flex items-center justify-center w-6 h-6 rounded-full bg-red-500/10">
        <X className="w-3.5 h-3.5 text-red-400" />
      </span>
    );
  return (
    <span className="flex items-center gap-1.5 text-xs text-yellow-400">
      <Minus className="w-3.5 h-3.5" />
      {value}
    </span>
  );
}

export default function ComparisonContent({ competitor }: { competitor: Competitor }) {
  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 lg:px-12">
      {/* Breadcrumb */}
      <div className="pt-8">
        <Link
          href="/compare"
          className="inline-flex items-center gap-1.5 text-sm text-[#888] hover:text-[#f5f0e8] transition"
        >
          <ChevronLeft className="w-4 h-4" />
          All Comparisons
        </Link>
      </div>

      {/* Hero */}
      <section className="pt-8 pb-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <GitCompareArrows className="w-5 h-5 text-[#7c3aed]" />
            </div>
            <span className="text-sm font-medium text-[#7c3aed] uppercase tracking-wider">
              Comparison
            </span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            Bonito vs {competitor.name}
          </h1>
          <p className="mt-2 text-base text-[#888]">{competitor.tagline}</p>
          <p className="mt-4 text-sm text-[#999] leading-relaxed max-w-3xl">
            {competitor.description}
          </p>
        </motion.div>
      </section>

      {/* Two column: what they do well / where Bonito goes further */}
      <section className="pb-12">
        <div className="grid md:grid-cols-2 gap-6">
          {/* What competitor does well */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <Zap className="w-5 h-5 text-blue-400" />
              <h2 className="text-lg font-semibold">
                What {competitor.name} does well
              </h2>
            </div>
            <ul className="space-y-3">
              {competitor.whatTheyDoWell.map((item, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-[#ccc]">
                  <Check className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Where Bonito goes further */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-[#111] border border-[#7c3aed]/30 rounded-xl p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <Shield className="w-5 h-5 text-[#7c3aed]" />
              <h2 className="text-lg font-semibold">Where Bonito goes further</h2>
            </div>
            <ul className="space-y-3">
              {competitor.whereBonitoGoesFurther.map((item, i) => (
                <li key={i} className="flex items-start gap-2.5 text-sm text-[#ccc]">
                  <Check className="w-4 h-4 text-[#7c3aed] mt-0.5 shrink-0" />
                  <span className="leading-relaxed">{item}</span>
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </section>

      {/* Feature comparison tables */}
      <section className="pb-12">
        <h2 className="text-2xl font-bold mb-8">Feature-by-Feature Comparison</h2>
        <div className="space-y-8">
          {competitor.features.map((category, ci) => (
            <motion.div
              key={category.category}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * ci }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl overflow-hidden"
            >
              <div className="px-6 py-4 border-b border-[#1a1a1a]">
                <h3 className="font-semibold text-sm text-[#e5e0d8]">
                  {category.category}
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#1a1a1a]">
                      <th className="text-left py-3 px-6 font-medium text-[#888] w-1/2">
                        Feature
                      </th>
                      <th className="text-center py-3 px-4 font-medium text-[#7c3aed] w-1/4">
                        Bonito
                      </th>
                      <th className="text-center py-3 px-4 font-medium text-[#888] w-1/4">
                        {competitor.name}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {category.features.map((feature, fi) => (
                      <tr
                        key={fi}
                        className={
                          fi < category.features.length - 1
                            ? "border-b border-[#1a1a1a]/50"
                            : ""
                        }
                      >
                        <td className="py-3 px-6 text-[#ccc]">{feature.name}</td>
                        <td className="py-3 px-4">
                          <div className="flex justify-center">
                            <FeatureIcon value={feature.bonito} />
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex justify-center">
                            <FeatureIcon value={feature.competitor} />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Key Differentiators */}
      <section className="pb-12">
        <h2 className="text-2xl font-bold mb-6">Key Differentiators</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[
            {
              title: "Full AI Control Plane",
              description:
                "Bonito is not just observability or just a gateway. It is the complete control plane for enterprise AI: routing, agents, governance, cost management, and multi-cloud infrastructure in one platform.",
            },
            {
              title: "Governed AI Agents",
              description:
                "BonBon and Bonobot agents come with default-deny security, per-agent budget controls, credential isolation, and full audit trails. Enterprise-grade agent deployment from day one.",
            },
            {
              title: "Multi-Cloud Native",
              description:
                "Connect your actual AWS, Azure, and GCP accounts. Bonito manages provider credentials, syncs model catalogs, deploys models, and tracks costs across all three clouds from one dashboard.",
            },
          ].map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * i }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-5"
            >
              <h3 className="font-semibold text-sm mb-2">{item.title}</h3>
              <p className="text-xs text-[#888] leading-relaxed">{item.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="pb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gradient-to-br from-[#7c3aed]/10 to-[#0a0a0a] border border-[#7c3aed]/20 rounded-2xl p-8 md:p-12 text-center"
        >
          <h2 className="text-2xl md:text-3xl font-bold mb-3">
            Ready to try Bonito?
          </h2>
          <p className="text-[#888] text-sm md:text-base max-w-xl mx-auto mb-6">
            Start free and connect your first cloud provider in under 5 minutes.
            See how Bonito goes beyond {competitor.name} with routing, agents,
            and full multi-cloud management.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/register"
              className="px-6 py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-sm font-semibold rounded-lg transition inline-flex items-center gap-2"
            >
              Get Started Free <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/pricing"
              className="px-6 py-3 border border-[#333] hover:border-[#555] text-[#ccc] text-sm font-semibold rounded-lg transition"
            >
              View Pricing
            </Link>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
