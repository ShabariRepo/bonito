"use client";

/**
 * ThinkingMascot — per-theme "thinking…" sprite for Studio.
 *
 * Each theme gets its own low-poly mascot that animates while the
 * agent is mid-turn. Bonito → swimming fish with bubbles (delegates to
 * SwimmingFish). Oregon Trail → polygon bull pulling a wagon. The
 * other Origami themes (hacker / candy / wafū / dracula / lofi) get
 * theme-appropriate mascots so the wait UI carries the theme's vibe.
 *
 * One file deliberately — each mascot is small enough that a single
 * file keeps the dispatch trivial and the styles consistent.
 */

import { motion } from "framer-motion";
import { SwimmingFish } from "./SwimmingFish";
import type { ChatThemeId } from "../origami/chat-themes";

export function ThinkingMascot({
  themeId,
  size = 18,
  className = "",
}: {
  themeId: ChatThemeId;
  size?: number;
  className?: string;
}) {
  switch (themeId) {
    case "default":
      return <SwimmingFish size={size} className={className} />;
    case "oregon":
      return <OregonBullWagon size={size} className={className} />;
    case "hacker":
      return <HackerSnake size={size} className={className} />;
    case "candy":
      return <CandyLollipop size={size} className={className} />;
    case "japanese":
      return <WafuKoi size={size} className={className} />;
    case "dracula":
      return <DraculaBat size={size} className={className} />;
    case "lofi":
      return <LofiCoffee size={size} className={className} />;
    default:
      return <SwimmingFish size={size} className={className} />;
  }
}

// ─── Oregon Trail — polygon bull pulling a wooden wagon ──────────────
function OregonBullWagon({ size, className }: { size: number; className?: string }) {
  return (
    <motion.span
      style={{ width: size * 2.6, height: size * 1.1, display: "inline-block" }}
      animate={{ x: [-4, 4, -4] }}
      transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
      className={className}
      aria-label="Studio is thinking — wagon trail"
      role="status"
    >
      <svg
        viewBox="0 0 42 18"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Wagon body — wooden box */}
        <polygon points="20,7 34,7 34,12 20,12" fill="#8b5a2b" />
        {/* Wagon canopy — cream */}
        <path
          d="M 20 7 Q 27 1.5 34 7 Z"
          fill="#f5e6c8"
          stroke="#3d2817"
          strokeWidth="0.4"
        />
        {/* Wagon canopy stripes */}
        <line x1="23" y1="4.6" x2="23" y2="7" stroke="#8b5a2b" strokeWidth="0.3" />
        <line x1="27" y1="3.5" x2="27" y2="7" stroke="#8b5a2b" strokeWidth="0.3" />
        <line x1="31" y1="4.6" x2="31" y2="7" stroke="#8b5a2b" strokeWidth="0.3" />
        {/* Wagon wheels — spin while moving */}
        {[22, 32].map((cx) => (
          <motion.g
            key={cx}
            style={{ originX: `${cx}px`, originY: "14px" }}
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
          >
            <circle cx={cx} cy={14} r={2} fill="#3d2817" />
            <circle cx={cx} cy={14} r={1.4} fill="#8b5a2b" />
            <line x1={cx - 1.4} y1={14} x2={cx + 1.4} y2={14} stroke="#3d2817" strokeWidth="0.3" />
            <line x1={cx} y1={12.6} x2={cx} y2={15.4} stroke="#3d2817" strokeWidth="0.3" />
          </motion.g>
        ))}
        {/* Yoke connecting bull to wagon */}
        <line x1="14" y1="9" x2="20" y2="9" stroke="#3d2817" strokeWidth="0.5" />
        {/* Bull body */}
        <polygon points="4,8 14,8 14,12 4,12" fill="#5c3a1e" />
        <polygon points="4,8 8,5 14,5 14,8" fill="#7a4a26" />
        {/* Bull head */}
        <polygon points="2,9 4,7 4,12 2,11" fill="#3d2817" />
        {/* Horns */}
        <polygon points="3.2,7.2 2.4,5.8 3,6.8" fill="#f5e6c8" />
        <polygon points="3.8,7.2 4.6,5.8 4,6.8" fill="#f5e6c8" />
        {/* Eye */}
        <circle cx="2.6" cy="9.2" r="0.35" fill="white" />
        {/* Legs — alternating gait */}
        {[5, 8, 11, 13].map((x, i) => (
          <motion.line
            key={x}
            x1={x}
            y1={12}
            x2={x}
            y2={15}
            stroke="#3d2817"
            strokeWidth="0.7"
            animate={{ y1: [12, 11.5, 12] }}
            transition={{
              duration: 0.6,
              delay: i * 0.15,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
        {/* Dust kicked up behind */}
        {[0, 0.4, 0.8].map((delay, i) => (
          <motion.circle
            key={i}
            cx={1}
            cy={15}
            r={0.4}
            fill="#d4a574"
            animate={{
              cx: [1, -2],
              opacity: [0, 0.6, 0],
              r: [0.3, 0.7],
            }}
            transition={{
              duration: 1.4,
              delay,
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        ))}
      </svg>
    </motion.span>
  );
}

// ─── Hacker — segmented green snake worming forward ──────────────────
function HackerSnake({ size, className }: { size: number; className?: string }) {
  const segments = [0, 1, 2, 3, 4];
  return (
    <motion.span
      style={{ width: size * 1.8, height: size, display: "inline-block" }}
      className={className}
      aria-label="Studio is thinking"
      role="status"
    >
      <svg
        viewBox="0 0 30 16"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {segments.map((i) => (
          <motion.rect
            key={i}
            x={5 + i * 4}
            y={6}
            width={3.4}
            height={3.4}
            fill="#10b981"
            stroke="#34d399"
            strokeWidth="0.3"
            animate={{
              y: [6, 4, 6, 8, 6],
              opacity: [0.4, 1, 0.4],
            }}
            transition={{
              duration: 1.2,
              delay: i * 0.12,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
        {/* Head — slightly bigger + filled */}
        <motion.rect
          x={26}
          y={5.6}
          width={3.8}
          height={3.8}
          fill="#34d399"
          animate={{ opacity: [1, 0.6, 1] }}
          transition={{ duration: 1.0, repeat: Infinity }}
        />
      </svg>
    </motion.span>
  );
}

// ─── Candy — bouncing lollipop on a stick ────────────────────────────
function CandyLollipop({ size, className }: { size: number; className?: string }) {
  return (
    <motion.span
      style={{ width: size, height: size * 1.4, display: "inline-block" }}
      animate={{ y: [0, -3, 0], rotate: [-6, 6, -6] }}
      transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
      className={className}
      aria-label="Studio is thinking"
      role="status"
    >
      <svg
        viewBox="0 0 16 22"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%" }}
      >
        {/* Stick */}
        <rect x="7.5" y="11" width="1" height="10" fill="#fde047" />
        {/* Candy disc — concentric polygons */}
        <polygon points="8,1 14,4 14,10 8,13 2,10 2,4" fill="#f472b6" />
        <polygon points="8,3 12,5 12,9 8,11 4,9 4,5" fill="#fbcfe8" />
        <polygon points="8,5 10,6 10,8 8,9 6,8 6,6" fill="#f472b6" />
        {/* Highlight */}
        <ellipse cx="6" cy="5" rx="1.5" ry="0.8" fill="white" opacity="0.6" />
      </svg>
    </motion.span>
  );
}

// ─── Wafū — red koi fish, calmer than the Bonito fish ────────────────
function WafuKoi({ size, className }: { size: number; className?: string }) {
  return (
    <motion.span
      style={{ width: size * 1.55, height: size, display: "inline-block" }}
      animate={{ x: [-4, 4, 4, -4, -4], scaleX: [1, 1, -1, -1, 1] }}
      transition={{
        duration: 3.2,
        times: [0, 0.45, 0.5, 0.95, 1],
        repeat: Infinity,
        ease: "easeInOut",
      }}
      className={className}
      aria-label="Studio is thinking"
      role="status"
    >
      <svg
        viewBox="0 0 24 16"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Tail */}
        <polygon points="5,8 1,3.5 3,8 1,12.5" fill="#9f1b0f" />
        {/* Body — deep red */}
        <polygon points="5,8 10,2.8 19,5.8 22,8" fill="#9f1b0f" />
        <polygon points="5,8 22,8 19,10.2 10,13.2" fill="#7a140b" />
        {/* White belly stripe */}
        <polygon points="5.5,8 22,8 19,8.6 6,8.6" fill="#faf3e0" opacity="0.95" />
        {/* Fins */}
        <polygon points="11,3.5 12,0.4 14,4" fill="#9f1b0f" />
        <polygon points="12,12.4 13,14.6 15,12" fill="#7a140b" />
        {/* Scale dots */}
        <circle cx="11" cy="6" r="0.6" fill="#faf3e0" opacity="0.7" />
        <circle cx="14" cy="6.2" r="0.5" fill="#faf3e0" opacity="0.7" />
        {/* Eye */}
        <circle cx="18.6" cy="7" r="0.95" fill="white" />
        <circle cx="18.6" cy="7" r="0.45" fill="#1a1a1a" />
      </svg>
    </motion.span>
  );
}

// ─── Dracula — polygon bat flapping its wings ────────────────────────
function DraculaBat({ size, className }: { size: number; className?: string }) {
  return (
    <motion.span
      style={{ width: size * 1.6, height: size, display: "inline-block" }}
      animate={{ y: [0, -2, 0, 2, 0] }}
      transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}
      className={className}
      aria-label="Studio is thinking"
      role="status"
    >
      <svg
        viewBox="0 0 26 16"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Left wing — flaps */}
        <motion.polygon
          points="13,8 4,3 6,9 13,9"
          fill="#bd93f9"
          stroke="#ff79c6"
          strokeWidth="0.3"
          animate={{ rotate: [0, -20, 0] }}
          transition={{ duration: 0.5, repeat: Infinity, ease: "easeInOut" }}
          style={{ originX: "13px", originY: "9px" }}
        />
        {/* Right wing — flaps in opposite phase */}
        <motion.polygon
          points="13,8 22,3 20,9 13,9"
          fill="#bd93f9"
          stroke="#ff79c6"
          strokeWidth="0.3"
          animate={{ rotate: [0, 20, 0] }}
          transition={{ duration: 0.5, repeat: Infinity, ease: "easeInOut" }}
          style={{ originX: "13px", originY: "9px" }}
        />
        {/* Body */}
        <polygon points="11,7 15,7 15,11 11,11" fill="#282a36" />
        {/* Ears */}
        <polygon points="11.5,7 11,5 12.5,6.5" fill="#282a36" />
        <polygon points="14.5,7 15,5 13.5,6.5" fill="#282a36" />
        {/* Eyes */}
        <circle cx="12.4" cy="8.3" r="0.4" fill="#50fa7b" />
        <circle cx="13.6" cy="8.3" r="0.4" fill="#50fa7b" />
      </svg>
    </motion.span>
  );
}

// ─── Lofi — steaming coffee mug ──────────────────────────────────────
function LofiCoffee({ size, className }: { size: number; className?: string }) {
  return (
    <motion.span
      style={{ width: size, height: size * 1.4, display: "inline-block" }}
      className={className}
      aria-label="Studio is thinking"
      role="status"
    >
      <svg
        viewBox="0 0 16 22"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Steam ribbons */}
        {[0, 0.6, 1.2].map((delay, i) => (
          <motion.path
            key={i}
            d={`M ${5 + i * 2.5} 9 q -1 -2 0.5 -3 q 1.5 -1 0 -3`}
            stroke="#d4a574"
            strokeWidth="0.6"
            fill="none"
            strokeLinecap="round"
            opacity={0.7}
            animate={{
              opacity: [0, 0.8, 0],
              y: [0, -3],
            }}
            transition={{
              duration: 1.8,
              delay,
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        ))}
        {/* Mug body */}
        <polygon points="2,10 12,10 11,20 3,20" fill="#a67c5b" />
        {/* Mug shadow */}
        <polygon points="2,10 12,10 11.5,12 2.5,12" fill="#5c4033" />
        {/* Handle */}
        <path
          d="M 12 12 q 3 0 3 3 q 0 3 -3 3"
          stroke="#a67c5b"
          strokeWidth="1.2"
          fill="none"
        />
        {/* Coffee surface */}
        <ellipse cx="7" cy="10" rx="5" ry="0.9" fill="#3a2818" />
      </svg>
    </motion.span>
  );
}
