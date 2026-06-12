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
      return <WafuSumo size={size} className={className} />;
    case "dracula":
      return <DraculaBat size={size} className={className} />;
    case "lofi":
      return <LofiCoffee size={size} className={className} />;
    default:
      return <SwimmingFish size={size} className={className} />;
  }
}

// ─── Oregon Trail — Apple II green-on-black bull + wagon ─────────────
// Pixelated silhouettes in bright phosphor green, evoking the original
// 1985 Apple II Oregon Trail title screen. No gradients, no strokes —
// just chunky rectangles, the way an 8-bit CRT would render it.
function OregonBullWagon({ size, className }: { size: number; className?: string }) {
  const GREEN = "#00ff66";
  return (
    <motion.span
      style={{ width: size * 2.6, height: size * 1.1, display: "inline-block" }}
      animate={{ x: [-3, 3, -3] }}
      transition={{ duration: 2.6, repeat: Infinity, ease: "easeInOut" }}
      className={className}
      aria-label="Studio is thinking — Oregon Trail"
      role="status"
    >
      <svg
        viewBox="0 0 42 18"
        xmlns="http://www.w3.org/2000/svg"
        shapeRendering="crispEdges"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Wagon canopy — three blocky ribs in green */}
        <rect x="20" y="3.5" width="14" height="3.5" fill={GREEN} />
        <rect x="20" y="2.5" width="4" height="4.5" fill={GREEN} />
        <rect x="25" y="2.5" width="4" height="4.5" fill={GREEN} />
        <rect x="30" y="2.5" width="4" height="4.5" fill={GREEN} />
        {/* Wagon canopy slits — black gaps between ribs */}
        <rect x="24" y="2.5" width="1" height="4.5" fill="#000" />
        <rect x="29" y="2.5" width="1" height="4.5" fill="#000" />
        {/* Wagon body — block underneath canopy */}
        <rect x="20" y="7" width="14" height="5" fill={GREEN} />
        {/* Wagon wheels — chunky pixel rings, spin in place */}
        {[22, 32].map((cx) => (
          <motion.g
            key={cx}
            style={{ originX: `${cx}px`, originY: "14px" }}
            animate={{ rotate: [0, 360] }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
          >
            <rect x={cx - 2} y={12.5} width={4} height={4} fill={GREEN} />
            <rect x={cx - 1} y={13.5} width={2} height={2} fill="#000" />
            <rect x={cx - 2} y={14} width={4} height={0.5} fill="#000" />
            <rect x={cx - 0.25} y={12.5} width={0.5} height={4} fill="#000" />
          </motion.g>
        ))}
        {/* Yoke — pixel beam */}
        <rect x="14" y="9" width="6" height="0.6" fill={GREEN} />
        {/* Bull body — chunky silhouette */}
        <rect x="4" y="7" width="10" height="5" fill={GREEN} />
        <rect x="6" y="5.5" width="8" height="1.5" fill={GREEN} />
        {/* Bull head + snout */}
        <rect x="2.5" y="7.5" width="2" height="3" fill={GREEN} />
        <rect x="1.5" y="8" width="1" height="2" fill={GREEN} />
        {/* Horns — two short green pixels */}
        <rect x="3" y="6.5" width="0.6" height="1.2" fill={GREEN} />
        <rect x="4.2" y="6.5" width="0.6" height="1.2" fill={GREEN} />
        {/* Eye — single black square so the bull reads */}
        <rect x="2.8" y="8.6" width="0.6" height="0.6" fill="#000" />
        {/* Legs — alternating gait */}
        {[5, 7, 11, 13].map((x, i) => (
          <motion.rect
            key={x}
            x={x}
            y={12}
            width={1}
            height={3}
            fill={GREEN}
            animate={{ y: [12, 11.6, 12] }}
            transition={{
              duration: 0.5,
              delay: i * 0.12,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
        {/* Dust kicked up behind — green CRT dots */}
        {[0, 0.4, 0.8].map((delay, i) => (
          <motion.rect
            key={i}
            x={1}
            y={15}
            width={0.7}
            height={0.7}
            fill={GREEN}
            animate={{
              x: [1, -2.5],
              opacity: [0, 0.7, 0],
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

// ─── Wafū — sumo wrestler stomping, dirt pops on impact ──────────────
// Squat polygon body, mawashi belt, topknot. Weight rocks side-to-side;
// each foot lifts then slams down, dust bursts out from under it. The
// stomp rhythm is offset between the two feet so something is always
// in motion.
function WafuSumo({ size, className }: { size: number; className?: string }) {
  // Palette pulled from the Wafū theme so the sumo lives in its world.
  const SKIN = "#f5ead0";
  const MAWASHI = "#9f1b0f"; // belt
  const HAIR = "#1a1a1a";    // topknot + brow
  const DIRT = "#8b7355";    // earth pops
  return (
    <motion.span
      style={{ width: size * 1.6, height: size * 1.5, display: "inline-block" }}
      animate={{ rotate: [-2, 2, -2] }}
      transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
      className={className}
      aria-label="Studio is thinking — sumo stomping"
      role="status"
    >
      <svg
        viewBox="0 0 26 26"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Topknot — small dark blob above the head */}
        <polygon points="11,3 13,1 15,3 14,4 12,4" fill={HAIR} />
        {/* Head — round-ish skin polygon */}
        <polygon points="9,4 17,4 18,7 16,9 10,9 8,7" fill={SKIN} />
        {/* Brow line */}
        <rect x="10" y="6.2" width="6" height="0.5" fill={HAIR} />
        {/* Eyes — two tiny black dots */}
        <circle cx="11.5" cy="7" r="0.4" fill={HAIR} />
        <circle cx="14.5" cy="7" r="0.4" fill={HAIR} />
        {/* Shoulders / chest — wide squat polygon */}
        <polygon points="5,10 21,10 22,15 4,15" fill={SKIN} />
        {/* Mawashi belt — dark red band across waist */}
        <rect x="4" y="14.5" width="18" height="2" fill={MAWASHI} />
        {/* Mawashi knot detail */}
        <polygon points="12,16.5 14,16.5 13.5,18 12.5,18" fill={MAWASHI} />
        {/* Belly bulge below belt */}
        <polygon points="5,16.5 21,16.5 19,20 7,20" fill={SKIN} />
        {/* Arms — stout, slightly out to balance */}
        <polygon points="4,10.5 1,12 1,16 4,15" fill={SKIN} />
        <polygon points="22,10.5 25,12 25,16 22,15" fill={SKIN} />

        {/* Left thigh + foot — stomps first */}
        <motion.g
          style={{ originX: "9px", originY: "20px" }}
          animate={{ rotate: [0, -8, 0, 0, 0] }}
          transition={{
            duration: 1.0,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <motion.polygon
            points="7,20 11,20 11,24 7,24"
            fill={SKIN}
            animate={{ y: [0, -1.2, 0, 0] }}
            transition={{
              duration: 1.0,
              times: [0, 0.25, 0.5, 1],
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
          {/* Foot */}
          <motion.rect
            x={6.5}
            y={23.5}
            width={5}
            height={1.5}
            fill={HAIR}
            animate={{ y: [0, -1.2, 0, 0] }}
            transition={{
              duration: 1.0,
              times: [0, 0.25, 0.5, 1],
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        </motion.g>

        {/* Right thigh + foot — stomps in counter-phase */}
        <motion.g
          style={{ originX: "17px", originY: "20px" }}
          animate={{ rotate: [0, 0, 8, 0, 0] }}
          transition={{
            duration: 1.0,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <motion.polygon
            points="15,20 19,20 19,24 15,24"
            fill={SKIN}
            animate={{ y: [0, 0, -1.2, 0] }}
            transition={{
              duration: 1.0,
              times: [0, 0.4, 0.65, 1],
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
          <motion.rect
            x={14.5}
            y={23.5}
            width={5}
            height={1.5}
            fill={HAIR}
            animate={{ y: [0, 0, -1.2, 0] }}
            transition={{
              duration: 1.0,
              times: [0, 0.4, 0.65, 1],
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        </motion.g>

        {/* DIRT POPS — bursts from under each foot at the moment it
            slams. Three particles per side, each fades up + out. The
            delay timing matches the foot-down half of the cycle. */}
        {[
          { x: 5, delayBase: 0.45 },  // left foot side
          { x: 9, delayBase: 0.45 },
          { x: 13, delayBase: 0.95 }, // right foot side
          { x: 17, delayBase: 0.95 },
          { x: 21, delayBase: 0.95 },
        ].map(({ x, delayBase }, i) => (
          <motion.circle
            key={`dirt-${i}`}
            cx={x}
            cy={25}
            r={0.6}
            fill={DIRT}
            animate={{
              cy: [25, 23],
              cx: [x, x + (i % 2 === 0 ? -1.2 : 1.2)],
              r: [0.4, 1.1],
              opacity: [0, 0.7, 0],
            }}
            transition={{
              duration: 0.55,
              delay: delayBase + (i % 2) * 0.05,
              repeat: Infinity,
              ease: "easeOut",
              repeatDelay: 0,
            }}
          />
        ))}
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
