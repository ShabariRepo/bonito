"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence, useInView } from "framer-motion";
import Link from "next/link";
import {
  Globe,
  ArrowRight,
  Sparkles,
  Shield,
  Zap,
  DollarSign,
  Bot,
  Database,
  BarChart3,
  Copy,
  Check,
  AlertCircle,
  Building2,
  Target,
  TrendingUp,
  RefreshCw,
  Link2,
  ThumbsUp,
} from "lucide-react";

// ─── Types ───

interface UseCase {
  title: string;
  description: string;
  bonito_features: string[];
  impact: string;
}

interface DiscoverResult {
  id: string;
  company_name: string;
  overview: string;
  industry: string;
  company_size: string;
  challenges: string[];
  use_cases: UseCase[];
  estimated_impact: string;
  recommended_plan: string;
}

// ─── Feature icon mapping ───

const featureIcons: Record<string, typeof Zap> = {
  "Gateway": Globe,
  "AI Gateway": Globe,
  "Multi-cloud AI Gateway": Globe,
  "Failover": Shield,
  "Intelligent Failover": Shield,
  "Cost Intelligence": DollarSign,
  "Cost Tracking": DollarSign,
  "Smart Routing": Zap,
  "Routing": Zap,
  "Routing Policies": Zap,
  "AI Agents": Bot,
  "Agents": Bot,
  "Bonobot": Bot,
  "BonBon": Bot,
  "Knowledge Base": Database,
  "RAG": Database,
  "Knowledge Base (RAG)": Database,
  "Compliance": Shield,
  "Governance": Shield,
  "Compliance & Governance": Shield,
  "Analytics": BarChart3,
  "Audit Trail": BarChart3,
  "SSO": Shield,
  "SAML SSO": Shield,
  "Model Playground": Sparkles,
  "Playground": Sparkles,
};

function getFeatureIcon(feature: string) {
  return featureIcons[feature] || Sparkles;
}

// ─── Animations ───

function FadeIn({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─── Loading sequence ───

const loadingSteps = [
  "Researching company...",
  "Analysing industry landscape...",
  "Identifying AI opportunities...",
  "Mapping Bonito capabilities...",
  "Generating your personalised report...",
];

function LoadingState({ companyName }: { companyName: string }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStep((s) => (s < loadingSteps.length - 1 ? s + 1 : s));
    }, 1800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center py-32 gap-8">
      <div className="relative">
        <div className="w-16 h-16 rounded-2xl bg-[#7c3aed]/20 flex items-center justify-center">
          <Sparkles className="w-8 h-8 text-[#7c3aed] animate-pulse" />
        </div>
        <div className="absolute -inset-4 rounded-3xl border border-[#7c3aed]/20 animate-ping" style={{ animationDuration: "2s" }} />
      </div>

      <div className="text-center space-y-3">
        <h3 className="text-xl font-semibold text-[#f5f0e8]">
          Analysing <span className="text-[#7c3aed]">{companyName}</span>
        </h3>
        <AnimatePresence mode="wait">
          <motion.p
            key={step}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="text-[#888] text-sm"
          >
            {loadingSteps[step]}
          </motion.p>
        </AnimatePresence>
      </div>

      {/* Progress dots */}
      <div className="flex gap-2">
        {loadingSteps.map((_, i) => (
          <div
            key={i}
            className={`w-2 h-2 rounded-full transition-all duration-500 ${
              i <= step ? "bg-[#7c3aed]" : "bg-[#333]"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Plan badge ───

function PlanBadge({ plan }: { plan: string }) {
  const colors: Record<string, string> = {
    free: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    pro: "bg-[#7c3aed]/10 text-[#a78bfa] border-[#7c3aed]/20",
    enterprise: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    scale: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  };
  const labels: Record<string, string> = {
    free: "Free Tier",
    pro: "Pro Plan",
    enterprise: "Enterprise",
    scale: "Scale",
  };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${colors[plan] || colors.enterprise}`}>
      {labels[plan] || "Enterprise"}
    </span>
  );
}

// ─── Results display ───

function ResultsDisplay({ result, onReset }: { result: DiscoverResult; onReset: () => void }) {
  const [copied, setCopied] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);

  const shareUrl = typeof window !== "undefined"
    ? `${window.location.origin}/discover/${result.id}`
    : "";

  const handleCopy = () => {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <FadeIn>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-3xl md:text-4xl font-bold text-[#f5f0e8]">{result.company_name}</h2>
              <PlanBadge plan={result.recommended_plan} />
            </div>
            <p className="text-[#888] text-sm">
              {result.industry} &middot; {result.company_size.charAt(0).toUpperCase() + result.company_size.slice(1)}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#333] text-[#888] hover:text-[#f5f0e8] hover:border-[#7c3aed]/40 transition text-sm"
            >
              {copied ? <Check className="w-4 h-4" /> : <Link2 className="w-4 h-4" />}
              {copied ? "Copied" : "Share"}
            </button>
            <button
              onClick={onReset}
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#333] text-[#888] hover:text-[#f5f0e8] hover:border-[#7c3aed]/40 transition text-sm"
            >
              <RefreshCw className="w-4 h-4" />
              New search
            </button>
          </div>
        </div>
      </FadeIn>

      {/* Overview */}
      <FadeIn delay={0.1}>
        <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <Building2 className="w-5 h-5 text-[#7c3aed]" />
            <h3 className="text-sm font-semibold text-[#7c3aed] uppercase tracking-wider">Company Overview</h3>
          </div>
          <p className="text-[#ccc] leading-relaxed">{result.overview}</p>
        </div>
      </FadeIn>

      {/* Challenges */}
      <FadeIn delay={0.15}>
        <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-[#f59e0b]" />
            <h3 className="text-sm font-semibold text-[#f59e0b] uppercase tracking-wider">AI Challenges You Likely Face</h3>
          </div>
          <div className="grid md:grid-cols-2 gap-3">
            {result.challenges.map((challenge, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-[#0a0a0a] border border-[#1a1a1a]">
                <AlertCircle className="w-4 h-4 text-[#f59e0b] mt-0.5 shrink-0" />
                <p className="text-sm text-[#aaa]">{challenge}</p>
              </div>
            ))}
          </div>
        </div>
      </FadeIn>

      {/* Use Cases */}
      <FadeIn delay={0.2}>
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5 text-[#7c3aed]" />
          <h3 className="text-sm font-semibold text-[#7c3aed] uppercase tracking-wider">How Bonito Helps {result.company_name}</h3>
        </div>
        <div className="grid gap-4">
          {result.use_cases.map((uc, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.25 + i * 0.08 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 hover:border-[#7c3aed]/30 transition group"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <h4 className="text-lg font-semibold text-[#f5f0e8] group-hover:text-[#a78bfa] transition">
                  {uc.title}
                </h4>
                <div className="flex gap-1.5 shrink-0">
                  {uc.bonito_features.slice(0, 3).map((feat, j) => {
                    const Icon = getFeatureIcon(feat);
                    return (
                      <div
                        key={j}
                        className="w-8 h-8 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center"
                        title={feat}
                      >
                        <Icon className="w-4 h-4 text-[#7c3aed]" />
                      </div>
                    );
                  })}
                </div>
              </div>
              <p className="text-[#999] text-sm leading-relaxed mb-3">{uc.description}</p>
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {uc.bonito_features.map((feat, j) => (
                    <span key={j} className="text-xs px-2 py-1 rounded-md bg-[#7c3aed]/10 text-[#a78bfa] border border-[#7c3aed]/20">
                      {feat}
                    </span>
                  ))}
                </div>
                <div className="flex items-start gap-1.5 text-xs text-emerald-400">
                  <TrendingUp className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                  <span>{uc.impact}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </FadeIn>

      {/* Impact Summary */}
      <FadeIn delay={0.4}>
        <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-[#7c3aed]/20 via-[#111] to-[#111] border border-[#7c3aed]/30 p-6">
          <div className="absolute top-0 right-0 w-64 h-64 bg-[#7c3aed]/5 rounded-full blur-3xl" />
          <div className="relative">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp className="w-5 h-5 text-[#a78bfa]" />
              <h3 className="text-sm font-semibold text-[#a78bfa] uppercase tracking-wider">Estimated Impact</h3>
            </div>
            <p className="text-[#f5f0e8] text-lg leading-relaxed">{result.estimated_impact}</p>
            <div className="mt-4 flex items-center gap-3">
              <span className="text-sm text-[#888]">Recommended plan:</span>
              <PlanBadge plan={result.recommended_plan} />
            </div>
          </div>
        </div>
      </FadeIn>

      {/* Feedback */}
      <FadeIn delay={0.43}>
        <div className="flex items-center justify-center">
          {!feedbackSent ? (
            <button
              onClick={async () => {
                setFeedbackSent(true);
                const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
                try { await fetch(`${apiBase}/api/discover/${result.id}/feedback`, { method: "POST" }); } catch {}
                setTimeout(() => { window.location.href = "/contact"; }, 1500);
              }}
              className="flex items-center gap-3 px-6 py-3 rounded-xl border border-[#1a1a1a] bg-[#111] hover:border-[#7c3aed]/40 hover:bg-[#7c3aed]/5 transition group"
            >
              <ThumbsUp className="w-5 h-5 text-[#666] group-hover:text-[#a78bfa] transition" />
              <span className="text-sm text-[#888] group-hover:text-[#f5f0e8] transition">Was this helpful?</span>
            </button>
          ) : (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center gap-3 px-6 py-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5"
            >
              <Check className="w-5 h-5 text-emerald-400" />
              <span className="text-sm text-emerald-400">Thanks! Redirecting you...</span>
            </motion.div>
          )}
        </div>
      </FadeIn>

      {/* CTA */}
      <FadeIn delay={0.45}>
        <div className="flex flex-col sm:flex-row gap-4 items-center justify-center pt-4">
          <Link
            href="/request-access"
            className="flex items-center gap-2 px-8 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-lg transition text-sm group"
          >
            Get Started Free
            <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
          </Link>
          <Link
            href="/pricing"
            className="flex items-center gap-2 px-8 py-4 border border-[#333] text-[#999] hover:text-[#f5f0e8] hover:border-[#7c3aed]/40 rounded-lg transition text-sm"
          >
            View Pricing
          </Link>
        </div>
      </FadeIn>
    </div>
  );
}

// ─── Main Page ───

export default function DiscoverPage() {
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DiscoverResult | null>(null);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!websiteUrl.trim()) return;

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${apiBase}/api/discover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          website_url: websiteUrl.trim(),
        }),
      });

      if (res.status === 429) {
        setError("Too many requests. Please wait a moment and try again.");
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || "Something went wrong. Please try again.");
        return;
      }

      const data: DiscoverResult = await res.json();
      setResult(data);

      // Update URL without reload for shareability
      window.history.pushState({}, "", `/discover/${data.id}`);
    } catch {
      setError("Network error. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setWebsiteUrl("");
    setError("");
    window.history.pushState({}, "", "/discover");
    setTimeout(() => inputRef.current?.focus(), 100);
  };

  return (
    <div className="max-w-4xl mx-auto px-6 md:px-12 py-20 md:py-32 relative z-10">
      {/* Hero — always visible */}
      <AnimatePresence mode="wait">
        {!result && !loading && (
          <motion.div
            key="hero"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
            className="text-center mb-16"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#7c3aed]/10 border border-[#7c3aed]/20 text-[#a78bfa] text-xs font-semibold tracking-wider uppercase mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              AI-Powered Discovery
            </div>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-4">
              See what <span className="text-[#7c3aed]">Bonito</span> can do<br />for your company
            </h1>
            <p className="text-[#888] text-lg max-w-2xl mx-auto">
              Enter your website URL and our AI will research your business, identify your AI challenges, and show you exactly how Bonito's platform fits.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input form */}
      <AnimatePresence mode="wait">
        {!result && !loading && (
          <motion.div
            key="form"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <form onSubmit={handleSubmit} className="max-w-xl mx-auto">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[#666]" />
                  <input
                    ref={inputRef}
                    type="text"
                    value={websiteUrl}
                    onChange={(e) => setWebsiteUrl(e.target.value)}
                    placeholder="Enter your website URL..."
                    className="w-full pl-12 pr-4 py-4 bg-[#111] border border-[#333] rounded-xl text-[#f5f0e8] placeholder-[#555] focus:outline-none focus:border-[#7c3aed] transition text-base"
                    autoFocus
                  />
                </div>
                <button
                  type="submit"
                  disabled={!websiteUrl.trim()}
                  className="px-6 py-4 bg-[#7c3aed] hover:bg-[#6d28d9] disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition flex items-center gap-2 text-sm"
                >
                  Discover
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>

              {error && (
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-4 text-sm text-red-400 text-center"
                >
                  {error}
                </motion.p>
              )}
            </form>

            {/* Social proof hint */}
            <div className="mt-12 text-center">
              <p className="text-[#555] text-xs uppercase tracking-widest mb-4">Trusted by teams using</p>
              <div className="flex items-center justify-center gap-6 text-sm font-medium">
                <span style={{ color: "#FF9900" }}>AWS Bedrock</span>
                <span className="text-[#333]">&middot;</span>
                <span style={{ color: "#0078D4" }}>Azure AI</span>
                <span className="text-[#333]">&middot;</span>
                <span style={{ color: "#4285F4" }}>Google Vertex</span>
                <span className="text-[#333]">&middot;</span>
                <span style={{ color: "#10A37F" }}>OpenAI</span>
                <span className="text-[#333]">&middot;</span>
                <span style={{ color: "#D97757" }}>Anthropic</span>
                <span className="text-[#333]">&middot;</span>
                <span style={{ color: "#F55036" }}>Groq</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading */}
      <AnimatePresence mode="wait">
        {loading && (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <LoadingState companyName={companyName} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence mode="wait">
        {result && !loading && (
          <motion.div
            key="results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <ResultsDisplay result={result} onReset={handleReset} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
