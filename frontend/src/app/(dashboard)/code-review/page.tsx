"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  GitPullRequest,
  Github,
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
  Loader2,
  Zap,
  Shield,
  Bug,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/auth";
import { PageHeader } from "@/components/ui/page-header";
import { AnimatedCard } from "@/components/ui/animated-card";
import { StatusBadge } from "@/components/ui/status-badge";

interface ReviewItem {
  repo: string;
  pr_number: number;
  pr_title: string | null;
  pr_author: string | null;
  status: string;
  created_at: string | null;
}

interface CodeReviewStatus {
  connected: boolean;
  installation: {
    account: string;
    account_type: string;
    tier: string;
    installed_at: string | null;
  } | null;
  persona: string;
  available_personas: string[];
  usage: number;
  limit: number;
  reviews: ReviewItem[];
}

const PERSONA_INFO: Record<string, { name: string; emoji: string; desc: string }> = {
  default: { name: "Professional", emoji: "🐟", desc: "Straight-up technical review. No drama." },
  gilfoyle: { name: "Gilfoyle", emoji: "😈", desc: "Brutal. Condescending. Technically devastating." },
  dinesh: { name: "Dinesh", emoji: "😤", desc: "Passive-aggressive. Compares everything to his own code." },
  richard: { name: "Richard", emoji: "😰", desc: "Anxious genius. Obsesses over efficiency." },
  jared: { name: "Jared", emoji: "🤗", desc: "Impossibly supportive. Accidentally unsettling." },
  erlich: { name: "Erlich", emoji: "🌿", desc: "Grandiose visionary. Barely reads the code." },
};

const INSTALL_URL = "https://github.com/apps/bonito-code-review/installations/new";

function statusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-red-500" />;
    case "in_progress":
      return <Loader2 className="h-4 w-4 text-blue-400 animate-spin" />;
    case "skipped_rate_limit":
      return <Clock className="h-4 w-4 text-amber-500" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

function statusLabel(status: string) {
  switch (status) {
    case "completed": return "Reviewed";
    case "failed": return "Failed";
    case "in_progress": return "Reviewing";
    case "skipped_rate_limit": return "Limit reached";
    case "pending": return "Pending";
    default: return status;
  }
}

export default function CodeReviewPage() {
  const [data, setData] = useState<CodeReviewStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingPersona, setUpdatingPersona] = useState(false);

  // Check for ?installed=true query param (redirect from GitHub)
  const [justInstalled, setJustInstalled] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("installed") === "true") {
        setJustInstalled(true);
        // Clean up URL
        window.history.replaceState({}, "", "/code-review");
      }
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, []);

  async function fetchStatus() {
    try {
      setLoading(true);
      const res = await apiRequest("/api/v1/github/status");
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else {
        setError("Failed to load status");
      }
    } catch (e) {
      setError("Failed to connect to server");
    } finally {
      setLoading(false);
    }
  }

  async function updatePersona(persona: string) {
    try {
      setUpdatingPersona(true);
      const res = await apiRequest("/api/v1/github/persona", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ persona }),
      });
      if (res.ok && data) {
        setData({ ...data, persona });
      }
    } catch (e) {
      // silently fail
    } finally {
      setUpdatingPersona(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="AI Code Review"
          description="Automated PR reviews powered by Bonito"
        />
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  const connected = data?.connected ?? false;
  const usagePercent = data ? Math.min((data.usage / data.limit) * 100, 100) : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Code Review"
        description="Automated PR reviews powered by Bonito"
      />

      {justInstalled && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 flex items-center gap-3"
        >
          <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
          <p className="text-sm text-emerald-300">
            GitHub App installed successfully! Reviews will run automatically on your next PR.
          </p>
        </motion.div>
      )}

      {!connected ? (
        /* ── Not Connected State ── */
        <div className="space-y-6">
          <AnimatedCard className="p-8 text-center space-y-6">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="mx-auto w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center"
            >
              <Github className="h-8 w-8 text-white" />
            </motion.div>

            <div className="space-y-2">
              <h2 className="text-xl font-semibold">Connect GitHub to get started</h2>
              <p className="text-muted-foreground max-w-md mx-auto">
                Install the Bonito Code Review app on your repositories.
                Every PR gets an automated review for security, bugs, and performance.
              </p>
            </div>

            <motion.a
              href={INSTALL_URL}
              target="_blank"
              rel="noopener noreferrer"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-white text-black font-medium hover:bg-white/90 transition-colors"
            >
              <Github className="h-5 w-5" />
              Install GitHub App
              <ExternalLink className="h-4 w-4 opacity-50" />
            </motion.a>

            <p className="text-xs text-muted-foreground">
              Free tier: 5 PR reviews per month. No credit card required.
            </p>
          </AnimatedCard>

          {/* Feature cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              {
                icon: Shield,
                title: "Security Analysis",
                desc: "SQL injection, auth bypass, data exposure, dependency vulnerabilities",
                color: "text-red-400",
              },
              {
                icon: Bug,
                title: "Bug Detection",
                desc: "Logic errors, edge cases, null handling, race conditions",
                color: "text-amber-400",
              },
              {
                icon: TrendingUp,
                title: "Performance",
                desc: "N+1 queries, unbounded loops, memory leaks, slow patterns",
                color: "text-emerald-400",
              },
            ].map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.1 }}
              >
                <AnimatedCard className="p-5 space-y-3">
                  <feature.icon className={cn("h-6 w-6", feature.color)} />
                  <h3 className="font-medium">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">{feature.desc}</p>
                </AnimatedCard>
              </motion.div>
            ))}
          </div>
        </div>
      ) : (
        /* ── Connected State ── */
        <div className="space-y-6">
          {/* Status + Usage Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Connection Status */}
            <AnimatedCard className="p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-muted-foreground">Connection</h3>
                <StatusBadge status="active" label="Connected" />
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
                  <Github className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-medium">{data?.installation?.account}</p>
                  <p className="text-xs text-muted-foreground capitalize">
                    {data?.installation?.account_type} &middot; {data?.installation?.tier} tier
                  </p>
                </div>
              </div>
              <a
                href={INSTALL_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
              >
                Manage repositories <ExternalLink className="h-3 w-3" />
              </a>
            </AnimatedCard>

            {/* Usage */}
            <AnimatedCard className="p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-muted-foreground">Usage This Month</h3>
                <span className="text-2xl font-bold">
                  {data?.usage}<span className="text-sm font-normal text-muted-foreground">/{data?.limit}</span>
                </span>
              </div>
              {/* Progress bar */}
              <div className="space-y-2">
                <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${usagePercent}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className={cn(
                      "h-full rounded-full",
                      usagePercent >= 100
                        ? "bg-red-500"
                        : usagePercent >= 80
                        ? "bg-amber-500"
                        : "bg-emerald-500"
                    )}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  {data?.limit && data.usage >= data.limit
                    ? "Monthly limit reached. Upgrade for unlimited reviews."
                    : `${(data?.limit ?? 0) - (data?.usage ?? 0)} reviews remaining`}
                </p>
              </div>
              {data?.installation?.tier === "free" && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Zap className="h-3 w-3 text-amber-400" />
                  <span>Upgrade to Pro for unlimited reviews</span>
                </div>
              )}
            </AnimatedCard>
          </div>

          {/* Persona Selector */}
          <AnimatedCard className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-muted-foreground">Review Personality</h3>
                <p className="text-xs text-muted-foreground mt-1">Choose who reviews your code</p>
              </div>
              {updatingPersona && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
              {Object.entries(PERSONA_INFO).map(([id, info]) => (
                <motion.button
                  key={id}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => updatePersona(id)}
                  disabled={updatingPersona}
                  className={cn(
                    "p-3 rounded-lg border text-left transition-colors",
                    data?.persona === id
                      ? "border-emerald-500/50 bg-emerald-500/10"
                      : "border-white/5 bg-white/[0.02] hover:border-white/10"
                  )}
                >
                  <span className="text-xl">{info.emoji}</span>
                  <p className="text-sm font-medium mt-1">{info.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{info.desc}</p>
                </motion.button>
              ))}
            </div>
          </AnimatedCard>

          {/* Recent Reviews */}
          <AnimatedCard className="p-5 space-y-4">
            <h3 className="text-sm font-medium text-muted-foreground">Recent Reviews</h3>
            {data?.reviews && data.reviews.length > 0 ? (
              <div className="space-y-2">
                {data.reviews.map((review, i) => (
                  <motion.div
                    key={`${review.repo}-${review.pr_number}-${i}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-center gap-3 p-3 rounded-lg bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors"
                  >
                    {statusIcon(review.status)}
                    <GitPullRequest className="h-4 w-4 text-muted-foreground shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {review.pr_title || `PR #${review.pr_number}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {review.repo} #{review.pr_number}
                        {review.pr_author && ` by ${review.pr_author}`}
                      </p>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {statusLabel(review.status)}
                    </span>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <GitPullRequest className="h-8 w-8 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No reviews yet. Open a PR to trigger your first review.</p>
              </div>
            )}
          </AnimatedCard>
        </div>
      )}
    </div>
  );
}
