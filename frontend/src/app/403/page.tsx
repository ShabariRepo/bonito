"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Home, ShieldAlert, Lock } from "lucide-react";

export default function Forbidden() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f0e8] flex items-center justify-center relative overflow-hidden">
      {/* Restriction bars */}
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute w-2 bg-gradient-to-b from-[#f97316]/20 to-[#f97316]/5 h-full"
          style={{ left: `${15 + i * 14}%` }}
          initial={{ opacity: 0, scaleY: 0 }}
          animate={{ opacity: 1, scaleY: 1 }}
          transition={{
            duration: 0.4,
            delay: i * 0.1,
            ease: "easeOut",
          }}
        />
      ))}

      <div className="text-center px-6 relative z-10">
        {/* Locked chest with fish */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="mb-8"
        >
          <div className="relative inline-block">
            <motion.div
              animate={{ rotate: [0, -5, 5, -5, 0] }}
              transition={{ duration: 1.5, delay: 0.8, repeat: Infinity, repeatDelay: 2 }}
            >
              <Lock className="w-16 h-16 text-[#f97316] mx-auto mb-2" />
            </motion.div>
            <motion.pre
              initial={{ opacity: 0, x: 60 }}
              animate={{ opacity: 1, x: 60 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="text-[#7c3aed]/60 text-xs font-mono absolute -right-12 top-4 select-none"
              aria-hidden="true"
            >
{`><(((°>`}
            </motion.pre>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="inline-flex items-center gap-2 bg-orange-500/10 border border-orange-500/30 text-orange-400 text-sm font-medium px-4 py-1.5 rounded-full mb-6"
        >
          <ShieldAlert className="w-4 h-4" />
          Access denied
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-4xl md:text-6xl font-bold tracking-tight mb-4"
        >
          Restricted waters
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-[#888] text-lg max-w-md mx-auto mb-10"
        >
          You don&apos;t have permission to swim in these waters. Check your credentials or contact your admin.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link
            href="/"
            className="inline-flex items-center gap-2 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold px-6 py-3 rounded-xl transition"
          >
            <Home className="w-4 h-4" />
            Back to shore
          </Link>
          <Link
            href="/settings"
            className="inline-flex items-center gap-2 bg-[#111] hover:bg-[#1a1a1a] border border-[#1a1a1a] text-[#ccc] font-medium px-6 py-3 rounded-xl transition"
          >
            <ShieldAlert className="w-4 h-4" />
            Check permissions
          </Link>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-xs text-[#333] font-mono"
        >
          ERROR 403 • FORBIDDEN
        </motion.p>
      </div>
    </div>
  );
}
