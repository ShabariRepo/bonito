"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, useInView } from "framer-motion";
import Link from "next/link";
import { useAuth } from "@/components/auth/auth-context";
import Script from "next/script";
import Image from "next/image";
import { Cloud, Zap, DollarSign, Sparkles, Check, ArrowRight } from "lucide-react";
import SchematicBackground from "@/components/SchematicBackground";

// ---------- Section Animations ----------

function FadeInSection({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.7, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ---------- Main Page ----------

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/dashboard");
    }
  }, [loading, user, router]);

  if (loading || user) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0a0a0a]">
        <div className="w-8 h-8 border-2 border-[#7c3aed] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const features = [
    { icon: Cloud, title: "Multi-Cloud AI", desc: "Connect OpenAI, Anthropic, AWS Bedrock, Google Vertex — all from one control plane." },
    { icon: Zap, title: "API Gateway", desc: "Intelligent routing, load balancing, and failover across all your AI providers." },
    { icon: DollarSign, title: "Cost Intelligence", desc: "Real-time spend tracking, budget alerts, and optimization recommendations." },
    { icon: Sparkles, title: "AI Copilot", desc: "Built-in assistant that helps you manage infrastructure with natural language." },
  ];

  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "forever",
      features: ["Up to 3 providers", "Basic analytics", "Community support", "1 team member"],
      cta: "Get Started",
      highlighted: false,
    },
    {
      name: "Pro",
      price: "$499",
      period: "/mo",
      features: ["Unlimited providers", "Advanced analytics", "Priority support", "Unlimited team", "API gateway", "Cost optimization"],
      cta: "Start Free Trial",
      highlighted: true,
    },
    {
      name: "Enterprise",
      price: "$2K–5K",
      period: "/mo",
      features: ["Everything in Pro", "Dedicated support", "Custom SLAs", "SSO & SAML", "Compliance (SOC2, HIPAA)", "On-premise option"],
      cta: "Contact Sales",
      highlighted: false,
    },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f0e8] overflow-x-hidden scroll-smooth">
      <SchematicBackground />
      {/* Top gradient overlay for contrast — softened to let schematic show through */}
      <div className="fixed inset-0 pointer-events-none z-[1] bg-gradient-to-b from-[#0a0a0a]/80 via-[#0a0a0a]/40 to-transparent" style={{ height: "35vh" }} />

      <Script
        id="json-ld-org"
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Organization",
            name: "Bonito",
            url: "https://getbonito.com",
            logo: "https://getbonito.com/bonito-logo-400.png",
            description: "Unified multi-cloud AI management platform. Connect, route, monitor, and optimize your entire AI infrastructure.",
            contactPoint: {
              "@type": "ContactPoint",
              email: "support@getbonito.com",
              contactType: "customer support",
            },
          }),
        }}
      />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <Image src="/bonito-logo-400.png" alt="Bonito" width={40} height={27} priority className="object-contain" />
          <span className="text-xl font-semibold text-white">Bonito</span>
        </div>
        <div className="hidden md:flex items-center gap-6">
          <Link href="/pricing" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">Pricing</Link>
          <Link href="/docs" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">Docs</Link>
          <Link href="/blog" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">Blog</Link>
          <Link href="/about" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">About</Link>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">
            Sign In
          </Link>
          <Link
            href="/register"
            className="px-5 py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-sm font-semibold rounded-lg transition"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 pt-20 pb-32 md:pt-32 md:pb-40">
        <FadeInSection className="max-w-3xl">
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.1]">
            The Unified
            <span className="text-[#7c3aed]"> AI Control Plane</span>
          </h1>
          <p className="mt-6 text-lg md:text-xl text-[#888] max-w-2xl leading-relaxed">
            Manage every AI provider, model, and deployment from a single dashboard. 
            Route intelligently. Control costs. Ship faster.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4">
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-xl text-lg transition group"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <Link
              href="#features"
              className="inline-flex items-center justify-center px-8 py-4 border border-[#333] hover:border-[#555] text-[#999] hover:text-[#f5f0e8] rounded-xl text-lg transition"
            >
              Learn More
            </Link>
          </div>
        </FadeInSection>
      </section>

      {/* Social Proof */}
      <section className="relative z-10 border-y border-[#1a1a1a] py-16 bg-[#0a0a0a]/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <FadeInSection>
            <p className="text-center text-sm text-[#666] uppercase tracking-widest mb-10">
              Trusted by teams managing AI at scale
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6 opacity-40">
              {["BidBaby", "BubbleDash", "OkapiDigital", "OddWons", "ApexConsultants"].map((name) => (
                <div key={name} className="text-xl font-bold tracking-tight text-[#f5f0e8]">
                  {name}
                </div>
              ))}
            </div>
          </FadeInSection>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 py-24 md:py-32">
        <FadeInSection className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold">Everything you need to manage AI</h2>
          <p className="mt-4 text-[#888] text-lg max-w-2xl mx-auto">
            One platform to connect, route, monitor, and optimize your entire AI infrastructure.
          </p>
        </FadeInSection>
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((f, i) => (
            <FadeInSection key={f.title} delay={i * 0.1}>
              <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-8 hover:border-[#7c3aed]/30 transition group">
                <div className="w-12 h-12 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center mb-5 group-hover:bg-[#7c3aed]/20 transition">
                  <f.icon className="w-6 h-6 text-[#7c3aed]" />
                </div>
                <h3 className="text-xl font-semibold mb-3">{f.title}</h3>
                <p className="text-[#888] leading-relaxed">{f.desc}</p>
              </div>
            </FadeInSection>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 py-24 md:py-32">
        <FadeInSection className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold">Simple, transparent pricing</h2>
          <p className="mt-4 text-[#888] text-lg">Start free. Scale when you&apos;re ready.</p>
        </FadeInSection>
        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {plans.map((plan, i) => (
            <FadeInSection key={plan.name} delay={i * 0.1}>
              <div
                className={`rounded-xl p-8 border ${
                  plan.highlighted
                    ? "bg-[#7c3aed]/5 border-[#7c3aed]/40 ring-1 ring-[#7c3aed]/20"
                    : "bg-[#111] border-[#1a1a1a]"
                } flex flex-col`}
              >
                <h3 className="text-lg font-semibold">{plan.name}</h3>
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className="text-[#888] ml-1">{plan.period}</span>
                </div>
                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-3 text-sm text-[#999]">
                      <Check className="w-4 h-4 text-[#7c3aed] flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/register"
                  className={`block text-center py-3 rounded-lg font-semibold transition ${
                    plan.highlighted
                      ? "bg-[#7c3aed] hover:bg-[#6d28d9] text-white"
                      : "bg-[#1a1a1a] hover:bg-[#222] text-[#f5f0e8]"
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            </FadeInSection>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 py-24">
        <FadeInSection>
          <div className="bg-gradient-to-br from-[#7c3aed]/20 to-[#7c3aed]/5 border border-[#7c3aed]/20 rounded-2xl p-12 md:p-16 text-center">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Ready to take control?</h2>
            <p className="text-[#888] text-lg mb-8 max-w-xl mx-auto">
              Join teams who manage their AI infrastructure with confidence.
            </p>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-8 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-xl text-lg transition"
            >
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </FadeInSection>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[#1a1a1a] py-12">
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="text-sm text-[#666]">© 2026 Bonito. All rights reserved.</div>
          <div className="flex items-center gap-6 text-sm text-[#666]">
            <Link href="/pricing" className="hover:text-[#999] transition">Pricing</Link>
            <Link href="/about" className="hover:text-[#999] transition">About</Link>
            <Link href="/blog" className="hover:text-[#999] transition">Blog</Link>
            <Link href="/docs" className="hover:text-[#999] transition">Docs</Link>
            <Link href="/contact" className="hover:text-[#999] transition">Contact</Link>
            <Link href="/privacy" className="hover:text-[#999] transition">Privacy</Link>
            <Link href="/terms" className="hover:text-[#999] transition">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
