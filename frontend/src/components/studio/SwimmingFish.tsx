"use client";

/**
 * SwimmingFish — low-poly purple + orange Bonito mascot, swimming left↔right.
 *
 * Replaces the generic Loader2 spinner in Studio's "thinking…" affordances
 * so the wait UI carries Bonito's identity. Pure SVG so it scales cleanly;
 * Framer Motion drives the body translate + the horizontal flip at each
 * lap so the fish faces the direction it's swimming.
 */

import { motion } from "framer-motion";

export function SwimmingFish({
  size = 18,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <motion.span
      style={{
        width: size * 1.55,
        height: size,
        display: "inline-block",
      }}
      animate={{
        x: [-6, 6, 6, -6, -6],
        scaleX: [1, 1, -1, -1, 1],
      }}
      transition={{
        duration: 2.8,
        times: [0, 0.45, 0.5, 0.95, 1],
        repeat: Infinity,
        ease: "easeInOut",
      }}
      className={className}
      aria-label="Bonito is thinking"
      role="status"
    >
      <svg
        viewBox="0 0 24 16"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", display: "block" }}
      >
        {/* Tail fin — bright orange triangles with notch */}
        <polygon points="5,8 1,3.5 3,8 1,12.5" fill="#f97316" />
        {/* Body — upper half (light purple) */}
        <polygon points="5,8 10,2.8 19,5.8 22,8" fill="#a78bfa" />
        {/* Body — lower half (deep purple) */}
        <polygon points="5,8 22,8 19,10.2 10,13.2" fill="#7c3aed" />
        {/* Dorsal fin */}
        <polygon points="11,3.5 12,0.4 14,4" fill="#f97316" />
        {/* Bottom fin */}
        <polygon points="12,12.4 13,14.6 15,12" fill="#fb923c" />
        {/* Highlight stripe across the midline */}
        <polygon
          points="5,8 22,8 19,8.4 5.5,8.4"
          fill="#fdba74"
          opacity="0.8"
        />
        {/* Eye */}
        <circle cx="18.6" cy="7" r="0.95" fill="white" />
        <circle cx="18.6" cy="7" r="0.45" fill="#1a1a1a" />
      </svg>
    </motion.span>
  );
}
