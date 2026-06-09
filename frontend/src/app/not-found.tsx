"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Home } from "lucide-react";
import { OrigamiBonitoFish } from "@/components/origami/OrigamiBonitoFish";

const bubbles = Array.from({ length: 12 }, (_, i) => ({
  id: i,
  size: Math.random() * 12 + 4,
  left: Math.random() * 100,
  delay: Math.random() * 4,
  duration: Math.random() * 3 + 4,
}));

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f0e8] flex items-center justify-center relative overflow-hidden">
      {/* Underwater bubbles */}
      {bubbles.map((b) => (
        <motion.div
          key={b.id}
          className="absolute rounded-full bg-[#7c3aed]/10 border border-[#7c3aed]/20"
          style={{
            width: b.size,
            height: b.size,
            left: `${b.left}%`,
            bottom: -20,
          }}
          animate={{
            y: [0, -800],
            opacity: [0, 0.6, 0],
            scale: [1, 1.2, 0.8],
          }}
          transition={{
            duration: b.duration,
            delay: b.delay,
            repeat: Infinity,
            ease: "easeOut",
          }}
        />
      ))}

      <div className="text-center px-6 relative z-10">
        {/* Purple origami bonito — replaces the old ASCII fish */}
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="flex justify-center mb-6"
        >
          <OrigamiBonitoFish mood="lost" size={200} />
        </motion.div>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="text-[#7c3aed] font-mono text-sm mb-4 tracking-wider"
        >
          ERROR 404
        </motion.p>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-4xl md:text-6xl font-bold tracking-tight mb-4"
        >
          This one got away
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="text-[#888] text-lg max-w-md mx-auto mb-10"
        >
          The page you&apos;re looking for swam off to deeper waters. Let&apos;s get you back on course.
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
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center gap-2 bg-[#111] hover:bg-[#1a1a1a] border border-[#1a1a1a] text-[#ccc] font-medium px-6 py-3 rounded-xl transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Go back
          </button>
        </motion.div>

        {/* Subtle wave */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-16 text-[#1a1a1a] text-sm font-mono select-none"
        >
          ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~
        </motion.div>
      </div>
    </div>
  );
}
