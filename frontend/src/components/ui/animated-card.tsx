"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface AnimatedCardProps {
  children: ReactNode;
  className?: string;
  glowColor?: string;
  onClick?: () => void;
  layoutId?: string;
}

export function AnimatedCard({ children, className, glowColor = "violet", onClick, layoutId }: AnimatedCardProps) {
  return (
    <motion.div
      layoutId={layoutId}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      transition={{ duration: 0.3 }}
      onClick={onClick}
      className={cn(
        "group relative rounded-lg border border-border bg-card p-6 cursor-pointer transition-colors",
        "hover:border-opacity-60",
        glowColor === "amber" && "hover:border-amber-500/50 hover:shadow-[0_0_30px_-10px_rgba(245,158,11,0.15)]",
        glowColor === "blue" && "hover:border-blue-500/50 hover:shadow-[0_0_30px_-10px_rgba(59,130,246,0.15)]",
        glowColor === "red" && "hover:border-red-500/50 hover:shadow-[0_0_30px_-10px_rgba(239,68,68,0.15)]",
        glowColor === "violet" && "hover:border-violet-500/50 hover:shadow-[0_0_30px_-10px_rgba(139,92,246,0.15)]",
        glowColor === "emerald" && "hover:border-emerald-500/50 hover:shadow-[0_0_30px_-10px_rgba(16,185,129,0.15)]",
        className
      )}
    >
      {children}
    </motion.div>
  );
}
