"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Home, RefreshCw, AlertCircle } from "lucide-react";

export default function InternalServerError() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f0e8] flex items-center justify-center relative overflow-hidden">
      {/* Sinking bubbles (reversed) */}
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-[#ef4444]/10 border border-[#ef4444]/20"
          style={{
            width: Math.random() * 10 + 6,
            height: Math.random() * 10 + 6,
            left: `${Math.random() * 100}%`,
            top: -20,
          }}
          animate={{
            y: [0, 800],
            opacity: [0, 0.5, 0],
            x: [0, (Math.random() - 0.5) * 100],
          }}
          transition={{
            duration: Math.random() * 2 + 3,
            delay: Math.random() * 2,
            repeat: Infinity,
            ease: "easeIn",
          }}
        />
      ))}

      <div className="text-center px-6 relative z-10">
        {/* Belly-up fish with X eyes */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{
            opacity: 1,
            y: 0,
            rotate: [0, -2, 2, -2, 0],
          }}
          transition={{
            opacity: { duration: 0.6 },
            y: { duration: 0.6 },
            rotate: { duration: 2, delay: 0.8, repeat: Infinity, repeatDelay: 1 }
          }}
          className="mb-8"
        >
          <pre
            className="text-[#ef4444] text-sm md:text-base font-mono select-none inline-block"
            aria-hidden="true"
          >
{`      ___
    /  X  \\
<°)))><    |
    \\__X__/`}
          </pre>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400 text-sm font-medium px-4 py-1.5 rounded-full mb-6"
        >
          <AlertCircle className="w-4 h-4" />
          Internal server error
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-4xl md:text-6xl font-bold tracking-tight mb-4"
        >
          Server ran aground
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-[#888] text-lg max-w-md mx-auto mb-10"
        >
          Our servers hit a reef. We&apos;ve been notified and are working to fix it. Try refreshing in a moment.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <button
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold px-6 py-3 rounded-xl transition"
          >
            <RefreshCw className="w-4 h-4" />
            Reload page
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-[#111] hover:bg-[#1a1a1a] border border-[#1a1a1a] text-[#ccc] font-medium px-6 py-3 rounded-xl transition"
          >
            <Home className="w-4 h-4" />
            Back to shore
          </Link>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-xs text-[#333] font-mono"
        >
          ERROR 500 • INTERNAL SERVER ERROR
        </motion.p>
      </div>
    </div>
  );
}
