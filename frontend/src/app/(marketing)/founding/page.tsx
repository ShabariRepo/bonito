"use client";

import { motion } from "framer-motion";
import { Check, Crown, Lock, Zap, Shield, Users, ArrowRight } from "lucide-react";
import Link from "next/link";

const features = [
  "Up to 5 cloud providers (AWS, Azure, GCP, OpenAI, Anthropic, Groq)",
  "500,000 gateway API calls / month",
  "Advanced routing & load balancing",
  "Deployment provisioning across all clouds",
  "AI Context — 5 knowledge bases with RAG",
  "5 BonBon AI agents included",
  "Cost analytics & budget alerts",
  "AI copilot assistant",
  "Audit trail & compliance logging",
  "CLI + MCP server access",
  "Email support (24h response)",
  "Unlimited team members",
];

const benefits = [
  {
    icon: Lock,
    title: "Locked at $499/mo for 12 months",
    description: "50% off Pro ($999/mo). Your rate is guaranteed for a full year regardless of future price changes.",
  },
  {
    icon: Crown,
    title: "Founding customer status",
    description: "Direct line to the founding team. Your feedback shapes the roadmap. Named in our launch credits.",
  },
  {
    icon: Zap,
    title: "Priority onboarding",
    description: "1-on-1 onboarding call with the founder. We'll get your team live in under a week.",
  },
  {
    icon: Shield,
    title: "Early access to Enterprise features",
    description: "SSO, RBAC, and governance features as they ship — before they hit GA.",
  },
];

export default function FoundingPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12">
      {/* Hero */}
      <section className="pt-20 pb-16 text-center max-w-3xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 bg-[#7c3aed]/10 border border-[#7c3aed]/30 text-[#a78bfa] text-sm font-medium px-4 py-1.5 rounded-full mb-6"
        >
          <Users className="w-4 h-4" />
          Limited to 10 teams
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="text-4xl md:text-6xl font-bold tracking-tight"
        >
          Become a{" "}
          <span className="bg-gradient-to-r from-[#7c3aed] to-[#a78bfa] bg-clip-text text-transparent">
            Founding Customer
          </span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-6 text-lg text-[#888] max-w-2xl mx-auto leading-relaxed"
        >
          We&apos;re opening 10 founding spots for teams that want to shape the future of enterprise AI operations.
          Get full Pro access at half the price — locked for 12 months.
        </motion.p>

        {/* Price */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mt-10 flex items-center justify-center gap-4"
        >
          <div className="text-[#555] line-through text-2xl">$999</div>
          <div className="flex items-baseline gap-1">
            <span className="text-5xl font-bold text-white">$499</span>
            <span className="text-[#888] text-lg">/mo</span>
          </div>
          <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm font-semibold px-3 py-1 rounded-full">
            50% OFF
          </div>
        </motion.div>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="mt-3 text-sm text-[#666]"
        >
          Annual commitment &middot; $5,988/year (save $6,000 vs. monthly Pro)
        </motion.p>
      </section>

      {/* CTA */}
      <motion.section
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="text-center pb-16"
      >
        <a
          href="mailto:hello@trybonito.com?subject=Founding%2010%20—%20Interest&body=Hi%20Bonito%20team%2C%0A%0AI%27m%20interested%20in%20the%20Founding%2010%20offer.%0A%0ACompany%3A%20%0ATeam%20size%3A%20%0ACurrent%20AI%20providers%3A%20%0A%0AThanks!"
          className="inline-flex items-center gap-2 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold px-8 py-4 rounded-xl text-lg transition"
        >
          Claim Your Spot
          <ArrowRight className="w-5 h-5" />
        </a>
        <p className="mt-3 text-sm text-[#555]">
          Or email <span className="text-[#888]">hello@trybonito.com</span> directly
        </p>
      </motion.section>

      {/* Benefits */}
      <section className="pb-16">
        <div className="grid md:grid-cols-2 gap-6">
          {benefits.map((benefit, i) => (
            <motion.div
              key={benefit.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 + i * 0.05 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-8"
            >
              <benefit.icon className="w-8 h-8 text-[#7c3aed] mb-4" />
              <h3 className="text-lg font-semibold mb-2">{benefit.title}</h3>
              <p className="text-sm text-[#888] leading-relaxed">{benefit.description}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* What's included */}
      <section className="pb-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-[#111] border border-[#1a1a1a] rounded-xl p-10"
        >
          <h2 className="text-2xl font-bold mb-2">Everything in Pro</h2>
          <p className="text-[#888] mb-8">Full Pro plan — no feature restrictions, no surprises.</p>
          <div className="grid md:grid-cols-2 gap-4">
            {features.map((feature) => (
              <div key={feature} className="flex items-start gap-3">
                <Check className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
                <span className="text-sm text-[#ccc]">{feature}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* FAQ */}
      <section className="pb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.55 }}
        >
          <h2 className="text-2xl font-bold mb-8">Questions</h2>
          <div className="space-y-6">
            {[
              {
                q: "What happens after 12 months?",
                a: "You'll have the option to renew at the founding rate or move to the standard Pro plan. We'll never surprise you with a price increase.",
              },
              {
                q: "Can I upgrade to Enterprise later?",
                a: "Absolutely. If your needs grow, we'll credit your remaining founding commitment toward an Enterprise plan.",
              },
              {
                q: "Is there a contract?",
                a: "12-month commitment, billed monthly at $499. You can cancel anytime but the founding rate is only available for the initial term.",
              },
              {
                q: "How many spots are left?",
                a: "We're capping this at 10 founding teams. Once they're filled, this page goes away. Email us to check availability.",
              },
              {
                q: "What if I'm already on Free?",
                a: "You can upgrade directly. Your existing data, agents, and configurations carry over seamlessly.",
              },
            ].map((faq) => (
              <div key={faq.q} className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6">
                <h3 className="font-semibold mb-2">{faq.q}</h3>
                <p className="text-sm text-[#888]">{faq.a}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* Bottom CTA */}
      <section className="pb-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-gradient-to-b from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-2xl p-12"
        >
          <h2 className="text-3xl font-bold mb-4">Shape the platform with us</h2>
          <p className="text-[#888] max-w-lg mx-auto mb-8">
            Founding customers get a direct line to our engineering team. Your use cases become our priorities.
          </p>
          <a
            href="mailto:hello@trybonito.com?subject=Founding%2010%20—%20Interest&body=Hi%20Bonito%20team%2C%0A%0AI%27m%20interested%20in%20the%20Founding%2010%20offer.%0A%0ACompany%3A%20%0ATeam%20size%3A%20%0ACurrent%20AI%20providers%3A%20%0A%0AThanks!"
            className="inline-flex items-center gap-2 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold px-8 py-4 rounded-xl text-lg transition"
          >
            Claim Your Spot
            <ArrowRight className="w-5 h-5" />
          </a>
        </motion.div>
      </section>
    </div>
  );
}
