"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Home, RefreshCw, Wrench, Clock } from "lucide-react";
import { useEffect, useState } from "react";

export default function ServiceUnavailable() {
  const [countdown, setCountdown] = useState(60);

  useEffect(() => {
    const interval = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 60));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f0e8] flex items-center justify-center relative overflow-hidden">
      {/* Tool particles floating */}
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute"
          style={{
            left: `${Math.random() * 100}%`,
            top: `${Math.random() * 100}%`,
          }}
          animate={{
            y: [0, -30, 0],
            rotate: [0, 360],
            opacity: [0.1, 0.3, 0.1],
          }}
          transition={{
            duration: 3 + Math.random() * 2,
            delay: Math.random() * 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <Wrench className="w-6 h-6 text-[#fbbf24]/20" />
        </motion.div>
      ))}

      <div className="text-center px-6 relative z-10">
        {/* Fish in drydock/maintenance */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mb-8 relative"
        >
          <div className="relative inline-block">
            {/* Scaffolding bars */}
            <div className="absolute -left-8 top-0 bottom-0 w-1 bg-[#fbbf24]/30"></div>
            <div className="absolute -right-8 top-0 bottom-0 w-1 bg-[#fbbf24]/30"></div>
            <div className="absolute left-0 right-0 -top-2 h-1 bg-[#fbbf24]/30"></div>

            <pre
              className="text-[#7c3aed] text-sm md:text-base font-mono select-none relative z-10"
              aria-hidden="true"
            >
{`     ___
   /    \\
><(((°>  |
   \\____/`}
            </pre>

            {/* Wrench icon overlay */}
            <motion.div
              className="absolute -right-2 -bottom-2"
              animate={{
                rotate: [0, -15, 15, -15, 0],
              }}
              transition={{
                duration: 1.5,
                delay: 0.8,
                repeat: Infinity,
                repeatDelay: 1,
              }}
            >
              <Wrench className="w-8 h-8 text-[#fbbf24]" />
            </motion.div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm font-medium px-4 py-1.5 rounded-full mb-6"
        >
          <Clock className="w-4 h-4" />
          Temporarily unavailable
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-4xl md:text-6xl font-bold tracking-tight mb-4"
        >
          In the drydock
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-[#888] text-lg max-w-md mx-auto mb-4"
        >
          We&apos;re performing scheduled maintenance to keep our waters crystal clear. We&apos;ll be back soon.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="text-[#666] text-sm mb-10 font-mono"
        >
          Auto-retry in {countdown}s
        </motion.div>

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
            Try now
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
          ERROR 503 • SERVICE UNAVAILABLE
        </motion.p>
      </div>
    </div>
  );
}
