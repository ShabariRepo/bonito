"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  GitPullRequest,
  Github,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  ExternalLink,
  Zap,
} from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { useSearchParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface ReviewItem {
  repo: string;
  pr_number: number;
  pr_title: string | null;
  pr_author: string | null;
  status: string;
  created_at: string | null;
}

interface StatusData {
  connected: boolean;
  installation: {
    account: string;
    account_type: string;
    tier: string;
    installed_at: string | null;
  } | null;
  usage: number;
  limit: number;
  reviews: ReviewItem[];
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
    case "in_progress":
      return <Clock className="h-4 w-4 text-yellow-400 animate-pulse" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-red-400" />;
    case "skipped_rate_limit":
      return <AlertTriangle className="h-4 w-4 text-orange-400" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

function UsageBar({ used, limit }: { used: number; limit: number }) {
  const pct = Math.min((used / limit) * 100, 100);
  const color = pct >= 100 ? "bg-red-500" : pct >= 80 ? "bg-yellow-500" : "bg-emerald-500";

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted-foreground">Reviews this month</span>
        <span className="font-medium">
          {used} / {limit === 999999 ? "Unlimited" : limit}
        </span>
      </div>
      <div className="h-2.5 w-full rounded-full bg-accent/50 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

export default function CodeReviewPage() {
  const [data, setData] = useState<StatusData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const justInstalled = searchParams.get("installed") === "true";

  useEffect(() => {
    async function fetchStatus() {
      try {
        const res = await apiRequest("/api/v1/github/status");
        if (res.ok) {
          setData(await res.json());
        } else {
          setError("Failed to load status");
        }
      } catch (e) {
        setError("Failed to connect to API");
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
  }, []);

  if (loading) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="AI Code Review"
          description="Automated PR reviews powered by Bonito"
        />
        <div className="flex items-center justify-center py-20">
          <LoadingDots />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="AI Code Review"
        description="Automated PR reviews powered by Bonito. Security, performance, and correctness feedback on every pull request."
      />

      {justInstalled && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 flex items-center gap-3"
        >
          <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
          <p className="text-sm text-emerald-300">
            GitHub App installed successfully! Reviews will run automatically on your next PR.
          </p>
        </motion.div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {!data?.connected ? (
        /* ── Not Connected State ── */
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-16 text-center">
              <div className="rounded-full bg-accent/50 p-4 mb-6">
                <Github className="h-10 w-10 text-muted-foreground" />
              </div>
              <h2 className="text-xl font-semibold mb-2">Connect GitHub</h2>
              <p className="text-muted-foreground max-w-md mb-8">
                Install the Bonito Code Review app on your GitHub repos.
                Get AI-powered reviews on every pull request. Free tier includes 5 reviews per month.
              </p>
              <a
                href="https://github.com/apps/bonito-code-review/installations/new"
                className="inline-flex items-center gap-2 rounded-lg bg-white text-black px-6 py-3 font-medium hover:bg-gray-100 transition-colors"
              >
                <Github className="h-5 w-5" />
                Install GitHub App
                <ExternalLink className="h-4 w-4 opacity-50" />
              </a>
              <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-lg">
                {[
                  { icon: Zap, label: "Instant setup", desc: "Reviews start on next PR" },
                  { icon: GitPullRequest, label: "5 free reviews/mo", desc: "No credit card needed" },
                  { icon: CheckCircle2, label: "Smart analysis", desc: "Security, bugs, performance" },
                ].map((item, i) => (
                  <div key={i} className="text-center p-3">
                    <item.icon className="h-5 w-5 mx-auto mb-1.5 text-muted-foreground" />
                    <p className="text-sm font-medium">{item.label}</p>
                    <p className="text-xs text-muted-foreground">{item.desc}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        /* ── Connected State ── */
        <div className="space-y-6">
          {/* Status + Usage Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Connection
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-emerald-500/20 p-2">
                      <Github className="h-5 w-5 text-emerald-400" />
                    </div>
                    <div>
                      <p className="font-medium">{data.installation?.account}</p>
                      <p className="text-sm text-muted-foreground">
                        {data.installation?.account_type} account
                      </p>
                    </div>
                    <Badge variant="outline" className="ml-auto text-emerald-400 border-emerald-400/30">
                      Connected
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>Tier:</span>
                    <Badge variant="secondary" className="capitalize">
                      {data.installation?.tier}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Usage
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <UsageBar used={data.usage} limit={data.limit} />
                  {data.usage >= data.limit && data.limit < 999999 && (
                    <div className="rounded-md bg-orange-500/10 border border-orange-500/30 p-3 text-sm text-orange-300">
                      Monthly limit reached.{" "}
                      <a href="/settings" className="underline hover:text-orange-200">
                        Upgrade to Pro
                      </a>{" "}
                      for unlimited reviews.
                    </div>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </div>

          {/* Recent Reviews */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <GitPullRequest className="h-5 w-5" />
                  Recent Reviews
                </CardTitle>
              </CardHeader>
              <CardContent>
                {data.reviews.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <GitPullRequest className="h-8 w-8 mx-auto mb-3 opacity-50" />
                    <p>No reviews yet. Open a pull request to get started!</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {data.reviews.map((review, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-3 p-3 rounded-lg bg-accent/30 hover:bg-accent/50 transition-colors"
                      >
                        <StatusIcon status={review.status} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">
                            {review.pr_title || `PR #${review.pr_number}`}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {review.repo} #{review.pr_number}
                            {review.pr_author && ` by ${review.pr_author}`}
                          </p>
                        </div>
                        <Badge
                          variant="outline"
                          className={
                            review.status === "completed"
                              ? "text-emerald-400 border-emerald-400/30"
                              : review.status === "failed"
                              ? "text-red-400 border-red-400/30"
                              : "text-muted-foreground"
                          }
                        >
                          {review.status.replace("_", " ")}
                        </Badge>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}
    </div>
  );
}
