"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface LoadingDotsProps {
  className?: string;
  color?: string;
  size?: "sm" | "md" | "lg";
}

const sizes = { sm: "h-1.5 w-1.5", md: "h-2.5 w-2.5", lg: "h-3.5 w-3.5" };

export function LoadingDots({ className, color = "bg-violet-500", size = "md" }: LoadingDotsProps) {
  return (
    <div className={cn("flex items-center gap-1.5", className)}>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className={cn("rounded-full", sizes[size], color)}
          animate={{ scale: [1, 1.4, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.2, ease: "easeInOut" }}
        />
      ))}
    </div>
  );
}
