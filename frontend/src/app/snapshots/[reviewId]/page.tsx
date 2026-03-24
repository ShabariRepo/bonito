"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  GitPullRequest,
  FileText,
  Shield,
  Zap,
  Bug,
  TrendingUp,
  Palette,
  ArrowRight,
  ExternalLink,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SnapshotItem {
  id: string;
  title: string;
  severity: "critical" | "warning" | "suggestion" | "info";
  category: "security" | "performance" | "logic" | "architecture" | "style";
  file_path: string;
  start_line: number | null;
  end_line: number | null;
  code_block: string;
  annotation: string;
  sort_order: number;
  created_at: string;
}

interface SnapshotsResponse {
  review_id: string;
  repo: string;
  pr_number: number;
  pr_title: string | null;
  pr_author: string | null;
  snapshots: SnapshotItem[];
}

const SEVERITY_CONFIG = {
  critical: {
    icon: Shield,
    color: "text-red-500",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/30",
    label: "Critical",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
    label: "Warning",
  },
  suggestion: {
    icon: TrendingUp,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
    label: "Suggestion",
  },
  info: {
    icon: FileText,
    color: "text-gray-500",
    bgColor: "bg-gray-500/10",
    borderColor: "border-gray-500/30",
    label: "Info",
  },
};

const CATEGORY_CONFIG = {
  security: {
    icon: Shield,
    color: "text-red-400",
    label: "Security",
  },
  performance: {
    icon: Zap,
    color: "text-amber-400",
    label: "Performance",
  },
  logic: {
    icon: Bug,
    color: "text-orange-400",
    label: "Logic",
  },
  architecture: {
    icon: TrendingUp,
    color: "text-blue-400",
    label: "Architecture",
  },
  style: {
    icon: Palette,
    color: "text-purple-400",
    label: "Style",
  },
};

function SeverityBadge({ severity }: { severity: SnapshotItem["severity"] }) {
  const config = SEVERITY_CONFIG[severity];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-sm font-medium",
        config.bgColor,
        config.borderColor,
        config.color,
        "border"
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      {config.label}
    </div>
  );
}

function CategoryTag({ category }: { category: SnapshotItem["category"] }) {
  const config = CATEGORY_CONFIG[category];
  const Icon = config.icon;

  return (
    <div className={cn("inline-flex items-center gap-1 text-xs", config.color)}>
      <Icon className="h-3 w-3" />
      {config.label}
    </div>
  );
}

function CodeBlock({ code, filePath, startLine, endLine }: {
  code: string;
  filePath: string;
  startLine: number | null;
  endLine: number | null;
}) {
  const lineNumbers = startLine && endLine ? `L${startLine}-${endLine}` : "";

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="font-mono">{filePath}</span>
        {lineNumbers && <span>{lineNumbers}</span>}
      </div>
      <div className="relative">
        <pre className="p-4 bg-gray-950 rounded-lg border border-white/10 text-sm overflow-x-auto">
          <code className="text-gray-200 font-mono whitespace-pre">
            {code}
          </code>
        </pre>
      </div>
    </div>
  );
}

function SnapshotCard({ snapshot, index }: { snapshot: SnapshotItem; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="p-6 border border-white/10 bg-white/[0.02] backdrop-blur rounded-xl space-y-4"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h3 className="text-lg font-medium text-white">{snapshot.title}</h3>
          <div className="flex items-center gap-3">
            <SeverityBadge severity={snapshot.severity} />
            <CategoryTag category={snapshot.category} />
          </div>
        </div>
      </div>

      <CodeBlock
        code={snapshot.code_block}
        filePath={snapshot.file_path}
        startLine={snapshot.start_line}
        endLine={snapshot.end_line}
      />

      <div className="p-4 bg-white/[0.03] border border-white/5 rounded-lg">
        <p className="text-sm text-gray-300 leading-relaxed">
          {snapshot.annotation}
        </p>
      </div>
    </motion.div>
  );
}

export default function SnapshotsPage({ params }: { params: { reviewId: string } }) {
  const [data, setData] = useState<SnapshotsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSnapshots();
  }, [params.reviewId]);

  async function fetchSnapshots() {
    try {
      setLoading(true);
      const res = await fetch(`/api/v1/github/snapshots/${params.reviewId}`);
      if (res.ok) {
        const json = await res.json();
        setData(json);
      } else if (res.status === 404) {
        setError("Review not found");
      } else {
        setError("Failed to load snapshots");
      }
    } catch (e) {
      setError("Failed to connect to server");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-white" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <AlertTriangle className="h-16 w-16 text-red-400 mx-auto" />
          <h1 className="text-2xl font-bold text-white">Snapshots not found</h1>
          <p className="text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  if (!data || !data.snapshots.length) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <FileText className="h-16 w-16 text-gray-400 mx-auto" />
          <h1 className="text-2xl font-bold text-white">No snapshots available</h1>
          <p className="text-gray-400">This review doesn't have any code snapshots.</p>
        </div>
      </div>
    );
  }

  const githubUrl = `https://github.com/${data.repo}/pull/${data.pr_number}`;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-white/[0.02] backdrop-blur">
        <div className="max-w-6xl mx-auto px-6 py-6">
          <div className="flex items-start justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <GitPullRequest className="h-4 w-4" />
                <span>Pull Request #{data.pr_number}</span>
              </div>
              <h1 className="text-2xl font-bold">
                {data.pr_title || `PR #${data.pr_number}`}
              </h1>
              <div className="flex items-center gap-4 text-sm text-gray-400">
                <span>{data.repo}</span>
                {data.pr_author && (
                  <>
                    <span>•</span>
                    <span>by {data.pr_author}</span>
                  </>
                )}
              </div>
            </div>
            <a
              href={githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-white text-black font-medium rounded-lg hover:bg-white/90 transition-colors"
            >
              View on GitHub
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex items-center gap-6">
          <h2 className="text-lg font-medium">
            {data.snapshots.length} Key Snapshots
          </h2>
          <div className="flex items-center gap-4 text-sm text-gray-400">
            {Object.entries(
              data.snapshots.reduce((acc, s) => {
                acc[s.severity] = (acc[s.severity] || 0) + 1;
                return acc;
              }, {} as Record<string, number>)
            ).map(([severity, count]) => (
              <div key={severity} className="flex items-center gap-1">
                <div
                  className={cn(
                    "w-2 h-2 rounded-full",
                    SEVERITY_CONFIG[severity as keyof typeof SEVERITY_CONFIG]?.color?.replace('text-', 'bg-')
                  )}
                />
                <span>
                  {count} {severity}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Snapshots */}
      <div className="max-w-6xl mx-auto px-6 pb-12">
        <div className="space-y-8">
          {data.snapshots.map((snapshot, index) => (
            <SnapshotCard key={snapshot.id} snapshot={snapshot} index={index} />
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-white/10 bg-white/[0.02] backdrop-blur">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="text-center space-y-4">
            <h3 className="text-xl font-semibold">Powered by Bonito AI Code Review</h3>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Get automated code reviews on every pull request. Catch security issues,
              bugs, and performance problems before they reach production.
            </p>
            <motion.a
              href="https://getbonito.com"
              target="_blank"
              rel="noopener noreferrer"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="inline-flex items-center gap-2 px-6 py-3 bg-emerald-500 text-white font-medium rounded-lg hover:bg-emerald-600 transition-colors"
            >
              Get Started Free
              <ArrowRight className="h-4 w-4" />
            </motion.a>
          </div>
        </div>
      </div>
    </div>
  );
}