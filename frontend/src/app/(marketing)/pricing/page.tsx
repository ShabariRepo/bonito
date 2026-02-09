"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { Check, X, ArrowRight, HelpCircle } from "lucide-react";
import { useState } from "react";

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "For individuals exploring multi-cloud AI management.",
    features: [
      "1 AI provider connection",
      "100 API calls / month",
      "Basic dashboard & analytics",
      "Community support (Discord)",
      "1 team member",
      "Standard logging",
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
      "Up to 3 AI providers",
      "50,000 API calls / month",
      "API gateway with intelligent routing",
      "Cost analytics & optimization",
      "AI copilot assistant",
      "Email support (24h response)",
      "Unlimited team members",
      "Advanced logging & audit trail",
      "Budget alerts & notifications",
      "Custom model routing rules",
    ],
    cta: "Start Free Trial",
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "$2K–$5K",
    period: "/mo",
    description: "For organizations with complex AI infrastructure needs.",
    features: [
      "Unlimited AI providers",
      "Unlimited API calls",
      "Custom routing & load balancing",
      "SSO / SAML (coming soon)",
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

const comparisonFeatures = [
  { name: "AI Providers", free: "1", pro: "3", enterprise: "Unlimited" },
  { name: "API Calls / month", free: "100", pro: "50,000", enterprise: "Unlimited" },
  { name: "Team Members", free: "1", pro: "Unlimited", enterprise: "Unlimited" },
  { name: "Dashboard", free: true, pro: true, enterprise: true },
  { name: "Cost Analytics", free: false, pro: true, enterprise: true },
  { name: "API Gateway", free: false, pro: true, enterprise: true },
  { name: "Intelligent Routing", free: false, pro: true, enterprise: true },
  { name: "AI Copilot", free: false, pro: true, enterprise: true },
  { name: "Budget Alerts", free: false, pro: true, enterprise: true },
  { name: "Audit Trail", free: false, pro: true, enterprise: true },
  { name: "Custom Integrations", free: false, pro: false, enterprise: true },
  { name: "SSO / SAML", free: false, pro: false, enterprise: "Coming soon" },
  { name: "SLA Guarantee", free: false, pro: false, enterprise: "99.9%" },
  { name: "Dedicated Support", free: false, pro: false, enterprise: true },
  { name: "On-Premise Option", free: false, pro: false, enterprise: true },
  { name: "Compliance Ready", free: false, pro: false, enterprise: true },
];

const faqs = [
  {
    q: "What is Bonito?",
    a: "Bonito is a unified control plane for managing multi-cloud AI infrastructure. It lets you connect providers like OpenAI, Anthropic, AWS Bedrock, and Google Vertex AI from a single dashboard — with intelligent routing, cost tracking, and governance built in.",
  },
  {
    q: "How does billing work?",
    a: "You are billed monthly based on your plan tier. The Free plan requires no credit card. Pro and Enterprise plans are billed at the start of each billing cycle. Bonito charges for the platform — your AI provider costs (OpenAI, etc.) are billed separately by those providers.",
  },
  {
    q: "Can I switch plans at any time?",
    a: "Yes. You can upgrade or downgrade at any time. When upgrading, you get immediate access to new features. When downgrading, your current plan stays active until the end of the billing period.",
  },
  {
    q: "What cloud providers are supported?",
    a: "Bonito supports OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure OpenAI, Cohere, and more. We are constantly adding new provider integrations based on customer demand.",
  },
  {
    q: "Is there a free trial for Pro?",
    a: "Yes — Pro comes with a 14-day free trial with full access to all Pro features. No credit card required to start.",
  },
  {
    q: "What kind of support do you offer?",
    a: "Free users get access to our community Discord. Pro users receive email support with 24-hour response times. Enterprise customers get a dedicated support engineer with priority response.",
  },
  {
    q: "Is my data secure?",
    a: "Absolutely. Bonito never stores your AI request/response data. We use encryption at rest and in transit. Enterprise plans include SOC2 and HIPAA compliance options.",
  },
];

function CellValue({ value }: { value: boolean | string }) {
  if (value === true) return <Check className="w-5 h-5 text-[#7c3aed] mx-auto" />;
  if (value === false) return <X className="w-5 h-5 text-[#333] mx-auto" />;
  return <span className="text-sm text-[#ccc]">{value}</span>;
}

export default function PricingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

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

      {/* Plan Cards */}
      <section className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto pb-24">
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
              {comparisonFeatures.map((f) => (
                <tr key={f.name} className="border-b border-[#1a1a1a]/50 hover:bg-[#111] transition">
                  <td className="py-3.5 px-4 text-sm text-[#ccc]">{f.name}</td>
                  <td className="py-3.5 px-4 text-center"><CellValue value={f.free} /></td>
                  <td className="py-3.5 px-4 text-center"><CellValue value={f.pro} /></td>
                  <td className="py-3.5 px-4 text-center"><CellValue value={f.enterprise} /></td>
                </tr>
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
          <h2 className="text-3xl font-bold mb-4">Ready to get started?</h2>
          <p className="text-[#888] mb-8 max-w-xl mx-auto">
            Join teams who manage their AI infrastructure with confidence. Start free, upgrade anytime.
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
