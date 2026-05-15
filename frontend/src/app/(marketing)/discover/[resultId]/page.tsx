"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  Sparkles,
  ArrowRight,
  AlertCircle,
  Building2,
  Target,
  TrendingUp,
  Globe,
  Shield,
  Zap,
  DollarSign,
  Bot,
  Database,
  BarChart3,
  Copy,
  Check,
  RefreshCw,
  Link2,
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

// ─── Plan badge ───

function PlanBadge({ plan }: { plan: string }) {
  const colors: Record<string, string> = {
    free: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    pro: "bg-[#7c3aed]/10 text-[#a78bfa] border-[#7c3aed]/20",
    enterprise: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  };
  const labels: Record<string, string> = {
    free: "Free Tier",
    pro: "Pro Plan",
    enterprise: "Enterprise",
  };
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border ${colors[plan] || colors.pro}`}>
      {labels[plan] || "Pro Plan"}
    </span>
  );
}

// ─── Fade animation ───

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

// ─── Page ───

export default function DiscoverResultPage() {
  const params = useParams();
  const resultId = params.resultId as string;
  const [result, setResult] = useState<DiscoverResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchResult = async () => {
      try {
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "";
        const res = await fetch(`${apiBase}/api/discover/${resultId}`);
        if (!res.ok) {
          setNotFound(true);
          return;
        }
        const data = await res.json();
        setResult(data);
      } catch {
        setNotFound(true);
      } finally {
        setLoading(false);
      }
    };
    fetchResult();
  }, [resultId]);

  const handleCopy = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 md:px-12 py-32 relative z-10 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#7c3aed] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (notFound || !result) {
    return (
      <div className="max-w-4xl mx-auto px-6 md:px-12 py-32 relative z-10 text-center">
        <div className="w-16 h-16 rounded-2xl bg-[#333]/30 flex items-center justify-center mx-auto mb-6">
          <AlertCircle className="w-8 h-8 text-[#666]" />
        </div>
        <h2 className="text-2xl font-bold text-[#f5f0e8] mb-3">Report not found</h2>
        <p className="text-[#888] mb-8">This report may have expired or the link is invalid.</p>
        <Link
          href="/discover"
          className="inline-flex items-center gap-2 px-6 py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-lg transition text-sm"
        >
          Generate a new report
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-6 md:px-12 py-20 md:py-28 relative z-10 space-y-8">
      {/* Header */}
      <FadeIn>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#7c3aed]/10 border border-[#7c3aed]/20 text-[#a78bfa] text-xs font-semibold tracking-wider uppercase mb-4">
              <Sparkles className="w-3 h-3" />
              Bonito Discovery Report
            </div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl md:text-4xl font-bold text-[#f5f0e8]">{result.company_name}</h1>
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
            <Link
              href="/discover"
              className="flex items-center gap-2 px-4 py-2 rounded-lg border border-[#333] text-[#888] hover:text-[#f5f0e8] hover:border-[#7c3aed]/40 transition text-sm"
            >
              <RefreshCw className="w-4 h-4" />
              New search
            </Link>
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
              <div className="flex items-center justify-between">
                <div className="flex flex-wrap gap-2">
                  {uc.bonito_features.map((feat, j) => (
                    <span key={j} className="text-xs px-2 py-1 rounded-md bg-[#7c3aed]/10 text-[#a78bfa] border border-[#7c3aed]/20">
                      {feat}
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-1.5 text-xs text-emerald-400 shrink-0 ml-4">
                  <TrendingUp className="w-3.5 h-3.5" />
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
