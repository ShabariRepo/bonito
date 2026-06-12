"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { motion, useInView } from "framer-motion";
import Link from "next/link";
import { useAuth } from "@/components/auth/auth-context";
import Script from "next/script";
import Image from "next/image";
import { Cloud, Zap, DollarSign, Sparkles, Check, ArrowRight, Building2, ShoppingCart, Headphones, Bot, MonitorPlay, HeartPulse, Briefcase, Landmark } from "lucide-react";
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
    { icon: Cloud, title: "Multi-Cloud AI", desc: "Connect OpenAI, Anthropic, AWS Bedrock, Google Vertex, all from one control plane." },
    { icon: Zap, title: "API Gateway", desc: "Intelligent routing, load balancing, and failover across all your AI providers." },
    { icon: DollarSign, title: "Cost Intelligence", desc: "Real-time spend tracking, budget alerts, and optimization recommendations." },
    { icon: Sparkles, title: "AI Copilot", desc: "Built-in assistant that helps you manage infrastructure with natural language." },
  ];

  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "forever",
      features: ["Up to 3 providers", "25K API calls / month", "Automatic failover", "1 BonBon agent", "Basic analytics", "Community support"],
      cta: "Get Started",
      highlighted: false,
    },
    {
      name: "Starter",
      price: "$99",
      period: "/mo",
      features: ["100K API calls / month", "Intelligent routing (cost, A/B)", "Cost analytics & alerts", "2 BonBon agents", "CLI access", "Email support"],
      cta: "Start Free Trial",
      highlighted: true,
    },
    {
      name: "Pro",
      price: "$499",
      period: "/mo",
      features: ["500K calls, 5 providers", "RAG knowledge bases", "5 BonBon agents", "Audit trail & compliance", "Advanced load balancing", "Unlimited team"],
      cta: "Start Free Trial",
      highlighted: false,
    },
    {
      name: "Enterprise",
      price: "$2K-5K",
      period: "/mo",
      features: ["Everything in Pro", "Dedicated support", "Custom SLAs", "SSO & SAML", "Compliance (SOC2, HIPAA)", "On-premise option"],
      cta: "Contact Sales",
      highlighted: false,
    },
  ];

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f0e8] overflow-x-hidden scroll-smooth">
      <SchematicBackground />
      {/* Top gradient overlay for contrast, softened to let schematic show through */}
      <div className="fixed inset-0 pointer-events-none z-[1] bg-gradient-to-b from-[#0a0a0a]/80 via-[#0a0a0a]/40 to-transparent" style={{ height: "35vh" }} />

      <Script
        id="json-ld-org"
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Organization",
            name: "Bonito",
            alternateName: "Bonito AI",
            url: "https://getbonito.com",
            logo: "https://getbonito.com/bonito-logo-400.png",
            description: "The Unified AI Control Plane — one API to connect providers, route intelligently, control costs, and ship faster. Supports OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq.",
            foundingDate: "2025",
            founder: {
              "@type": "Person",
              name: "Shabari",
              jobTitle: "Founder & CEO",
            },
            contactPoint: [
              {
                "@type": "ContactPoint",
                email: "support@getbonito.com",
                contactType: "customer support",
              },
              {
                "@type": "ContactPoint",
                email: "shabari@bonito.ai",
                contactType: "sales",
              },
            ],
            sameAs: [
              "https://www.producthunt.com/products/bonito-cli",
              "https://pypi.org/project/bonito-cli/",
              "https://x.com/BonitoAI",
            ],
            knowsAbout: [
              "AI infrastructure",
              "LLM gateway",
              "Multi-cloud AI management",
              "AI cost optimization",
              "AI agent orchestration",
              "Enterprise AI governance",
              "RAG knowledge bases",
              "AI routing and failover",
            ],
          }),
        }}
      />
      <Script
        id="json-ld-howto"
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "HowTo",
            name: "How to Set Up Bonito AI Control Plane",
            description: "Get started with Bonito in 3 steps — connect your AI providers, send requests through one API, and let Bonito handle routing, failover, and cost tracking.",
            step: [
              {
                "@type": "HowToStep",
                position: 1,
                name: "Connect your AI providers",
                text: "Add your cloud AI provider credentials (AWS Bedrock, Azure OpenAI, Google Vertex AI, OpenAI, Anthropic, or Groq). Credentials are stored securely in HashiCorp Vault.",
              },
              {
                "@type": "HowToStep",
                position: 2,
                name: "Send requests to one API endpoint",
                text: "Use Bonito's OpenAI-compatible API endpoint (POST /v1/chat/completions) with your bn- prefix API key. Works with any existing OpenAI SDK client.",
              },
              {
                "@type": "HowToStep",
                position: 3,
                name: "Route, monitor, and optimize",
                text: "Configure routing policies (cost, latency, balanced, failover, A/B test). Bonito handles automatic failover, tracks costs in real-time, and provides optimization recommendations.",
              },
            ],
          }),
        }}
      />

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-6 max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <Image src="/bonito-icon.png" alt="Bonito" width={40} height={20} priority className="object-contain" />
          <span className="text-xl font-semibold text-white">Bonito</span>
        </div>
        <div className="hidden md:flex items-center gap-6">
          <Link href="/use-cases" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">Use Cases</Link>
          <Link href="/pricing" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">Pricing</Link>
          <Link href="/blog" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">Blog</Link>
          <Link href="/docs" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">Docs</Link>
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

      {/* Hero — thesis-shaped, not feature-list-shaped */}
      <section className="relative z-10 max-w-[1600px] mx-auto px-6 md:px-12 lg:px-20 pt-20 pb-24 md:pt-32 md:pb-32">
        <FadeInSection className="max-w-6xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#7c3aed]/10 border border-[#7c3aed]/20 text-[#a78bfa] text-xs font-semibold tracking-wider uppercase mb-6">
            <span className="h-1.5 w-1.5 rounded-full bg-[#7c3aed]" />
            Structurally cloud-neutral
          </div>
          <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.05]">
            The control plane the
            <span className="text-[#7c3aed]"> hyperscalers can&rsquo;t build</span>.
          </h1>
          <p className="mt-6 text-lg md:text-xl text-[#aaa] max-w-4xl mx-auto leading-relaxed">
            Every AI workload eventually needs three things: multi-cloud routing,
            cost governance, and audit. Bonito is the layer where they converge.
            One ledger across OpenAI, Anthropic, Bedrock, Vertex, Azure, and
            Groq. AWS will never route to Azure. We will.
          </p>
          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4 max-w-5xl mx-auto text-left">
            <div className="rounded-lg border border-[#1a1a1a] bg-[#111] p-4">
              <p className="text-xs uppercase tracking-wider text-[#7c3aed] font-semibold">Cloud-neutral moat</p>
              <p className="mt-1.5 text-sm text-[#bbb] leading-relaxed">
                Hyperscalers can&rsquo;t copy us &mdash; it would kill their
                lock-in business model. Structural defense, not a feature.
              </p>
            </div>
            <div className="rounded-lg border border-[#1a1a1a] bg-[#111] p-4">
              <p className="text-xs uppercase tracking-wider text-[#7c3aed] font-semibold">One audit ledger</p>
              <p className="mt-1.5 text-sm text-[#bbb] leading-relaxed">
                Every model call, every agent run, every KB query in one
                immutable log. Compliance teams answer their questions once.
              </p>
            </div>
            <div className="rounded-lg border border-[#1a1a1a] bg-[#111] p-4">
              <p className="text-xs uppercase tracking-wider text-[#7c3aed] font-semibold">Build by talking</p>
              <p className="mt-1.5 text-sm text-[#bbb] leading-relaxed">
                Origami spins up agents, KBs, and gateway keys from chat. New
                category, not a wrapper on someone else&rsquo;s SDK.
              </p>
            </div>
          </div>
          <div className="mt-10 flex flex-col sm:flex-row gap-4 sm:justify-center">
            <Link
              href="/register"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-xl text-lg transition group"
            >
              Get Started Free
              <ArrowRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <Link
              href="/discover"
              className="inline-flex items-center justify-center px-8 py-4 border border-[#333] hover:border-[#555] text-[#999] hover:text-[#f5f0e8] rounded-xl text-lg transition"
            >
              See it on your stack
            </Link>
          </div>

          {/* Founder bio surfaced on /about instead of inline — "Built by"
              reads dev-built; enterprise buyers expect an About page. */}
          <div className="mt-10 flex items-center justify-center gap-3 text-sm text-[#888]">
            <Link
              href="/about"
              className="inline-flex items-center gap-2 text-[#999] hover:text-[#a78bfa] transition"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[#7c3aed]" />
              About the team & thesis
            </Link>
            <span className="text-[#555]">·</span>
            <span>In stealth with enterprise design partners since Feb 2026</span>
          </div>

          <div className="mt-8">
            <a
              href="https://www.producthunt.com/products/bonito-cli?embed=true&utm_source=badge-featured&utm_medium=badge&utm_campaign=badge-bonito-cli"
              target="_blank"
              rel="noopener noreferrer"
            >
              <img
                alt="Bonito CLI - Deploy AI agents across any provider from one YAML file | Product Hunt"
                width={250}
                height={54}
                src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=1146468&theme=light&t=1778759307880"
              />
            </a>
          </div>
        </FadeInSection>
      </section>

      {/* Why hyperscalers can't build this — the structural moat argument
          made explicit. Addresses Blackbirds' "category entry not creation"
          critique by naming the wedge directly. */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 py-16 md:py-24 border-t border-[#1a1a1a]">
        <FadeInSection className="max-w-3xl mx-auto text-center">
          <p className="text-xs uppercase tracking-wider text-[#7c3aed] font-semibold">Why this is structurally defensible</p>
          <h2 className="mt-3 text-3xl md:text-4xl font-bold tracking-tight">
            Every other &ldquo;AI gateway&rdquo; is owned by someone with a cloud to sell.
          </h2>
          <div className="mt-6 space-y-4 text-[#bbb] text-lg leading-relaxed max-w-2xl mx-auto">
            <p>
              AWS Bedrock won&rsquo;t route to Azure. Microsoft won&rsquo;t optimize cost
              across Google. Google won&rsquo;t audit calls to OpenAI. Their business
              models structurally prevent it &mdash; honest multi-cloud kills the
              lock-in their margins depend on.
            </p>
            <p>
              Bonito doesn&rsquo;t sell a cloud. That&rsquo;s the moat. We&rsquo;re the only
              consolidated platform allowed to be cloud-neutral by design,
              and the hyperscalers cannot copy us without unwinding their own thesis.
            </p>
            <p className="text-[#888] text-base italic">
              The category is &ldquo;sovereign AI infrastructure for the
              multi-cloud reality.&rdquo; Not an LLM router with extra features.
            </p>
          </div>
        </FadeInSection>
      </section>

      {/* Use Cases */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 md:px-12 py-20 md:py-28">
        <FadeInSection className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold">Built for real workloads</h2>
          <p className="mt-4 text-[#888] text-lg max-w-2xl mx-auto">
            See how teams across industries use Bonito to manage AI at scale.
          </p>
        </FadeInSection>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {[
            { icon: Briefcase, label: "Enterprise AI Rollout", href: "/use-cases#enterprise-ai-rollout" },
            { icon: Headphones, label: "Customer Experience", href: "/use-cases#cx-platform" },
            { icon: ShoppingCart, label: "Product Marketplace", href: "/use-cases#product-marketplace" },
            { icon: Building2, label: "Enterprise AI Ops", href: "/use-cases#enterprise-ai-ops" },
            { icon: Bot, label: "AI Agent Workflows", href: "/use-cases#ai-agent-workflows" },
            { icon: MonitorPlay, label: "Ad-Tech / Programmatic", href: "/use-cases#ad-tech-programmatic" },
            { icon: HeartPulse, label: "Healthcare / Clinical AI", href: "/use-cases#healthcare-clinical-ai" },
            { icon: Landmark, label: "Banking & Financial Services", href: "/use-cases#banking-financial-services" },
          ].map((uc, i) => (
            <FadeInSection key={uc.label} delay={i * 0.05}>
              <Link
                href={uc.href}
                className="group flex flex-col items-center gap-3 p-6 bg-[#111] border border-[#1a1a1a] rounded-xl hover:border-[#7c3aed]/40 transition text-center"
              >
                <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center group-hover:bg-[#7c3aed]/20 transition">
                  <uc.icon className="w-5 h-5 text-[#7c3aed]" />
                </div>
                <span className="text-sm font-medium text-[#ccc] group-hover:text-[#f5f0e8] transition">{uc.label}</span>
              </Link>
            </FadeInSection>
          ))}
          <FadeInSection delay={0.35}>
            <Link
              href="/use-cases"
              className="group flex flex-col items-center justify-center gap-3 p-6 border border-dashed border-[#333] rounded-xl hover:border-[#7c3aed]/40 transition text-center"
            >
              <ArrowRight className="w-5 h-5 text-[#666] group-hover:text-[#7c3aed] transition" />
              <span className="text-sm font-medium text-[#666] group-hover:text-[#f5f0e8] transition">View all use cases</span>
            </Link>
          </FadeInSection>
        </div>
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
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
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
                  href={plan.name === "Enterprise" ? "/contact" : "/register"}
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
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/register"
                className="inline-flex items-center gap-2 px-8 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-xl text-lg transition"
              >
                Get Started Free <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                href="/discover"
                className="inline-flex items-center gap-2 px-8 py-4 border border-[#7c3aed]/30 hover:border-[#7c3aed]/60 text-[#ccc] hover:text-white rounded-xl text-lg transition"
              >
                Try Discover
              </Link>
            </div>
          </div>
        </FadeInSection>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[#1a1a1a] py-12">
        <div className="max-w-7xl mx-auto px-6 md:px-12 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <span className="text-sm text-[#666]">© 2026 Bonito. All rights reserved.</span>
            <a
              href="https://www.producthunt.com/products/bonito-cli?embed=true&utm_source=badge-featured&utm_medium=badge&utm_campaign=badge-bonito-cli"
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0"
            >
              <img
                alt="Bonito CLI - Deploy AI agents across any provider from one YAML file | Product Hunt"
                width={150}
                height={33}
                src="https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=1146468&theme=dark&t=1778759307880"
              />
            </a>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-[#666]">
            <Link href="/use-cases" className="hover:text-[#999] transition">Use Cases</Link>
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

      {/* BonBon Chat Widget */}
      <Script
        src="/widget.js"
        data-agent-id="82c23927-a92d-4420-a0f7-f771e7a23361"
        data-theme="dark"
        strategy="lazyOnload"
      />
    </div>
  );
}
