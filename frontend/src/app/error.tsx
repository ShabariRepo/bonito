"use client";

import { useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { RefreshCw, Home, AlertTriangle } from "lucide-react";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f0e8] flex items-center justify-center relative overflow-hidden">
      {/* Glitch lines */}
      {[...Array(5)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute h-px bg-[#7c3aed]/20 w-full"
          style={{ top: `${20 + i * 15}%` }}
          animate={{
            opacity: [0, 0.4, 0],
            scaleX: [0, 1, 0],
          }}
          transition={{
            duration: 2,
            delay: i * 0.3,
            repeat: Infinity,
            repeatDelay: 3,
          }}
        />
      ))}

      <div className="text-center px-6 relative z-10">
        {/* Capsized fish */}
        <motion.pre
          initial={{ opacity: 0, rotate: 0 }}
          animate={{ opacity: 1, rotate: 180 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="text-[#ef4444] text-xs md:text-sm font-mono mb-8 select-none inline-block"
          aria-hidden="true"
        >
{`><(((°>`}
        </motion.pre>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-medium px-4 py-1.5 rounded-full mb-6"
        >
          <AlertTriangle className="w-4 h-4" />
          Something went wrong
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-4xl md:text-6xl font-bold tracking-tight mb-4"
        >
          Fish out of water
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-[#888] text-lg max-w-md mx-auto mb-10"
        >
          Our bonito hit a snag. Don&apos;t worry — it&apos;s not you, it&apos;s us. Let&apos;s try that again.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <button
            onClick={() => reset()}
            className="inline-flex items-center gap-2 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold px-6 py-3 rounded-xl transition"
          >
            <RefreshCw className="w-4 h-4" />
            Try again
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-[#111] hover:bg-[#1a1a1a] border border-[#1a1a1a] text-[#ccc] font-medium px-6 py-3 rounded-xl transition"
          >
            <Home className="w-4 h-4" />
            Back to shore
          </Link>
        </motion.div>

        {error.digest && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="mt-8 text-xs text-[#333] font-mono"
          >
            Error ID: {error.digest}
          </motion.p>
        )}
      </div>
    </div>
  );
}
