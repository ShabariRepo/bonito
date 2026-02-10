"use client";

import { AlertCircle, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";

interface ErrorBannerProps {
  message?: string;
  onRetry?: () => void;
}

/**
 * Reusable error banner for data-fetch failures.
 * Displays a user-friendly message with an optional retry button.
 */
export function ErrorBanner({
  message = "Something went wrong while loading data. Please try again.",
  onRetry,
}: ErrorBannerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-red-500/20 bg-red-500/5 p-4"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm text-red-300">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-red-400 hover:text-red-300 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Retry
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
