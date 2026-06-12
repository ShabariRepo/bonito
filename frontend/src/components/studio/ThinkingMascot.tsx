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
    case "pitch":
      return <PitchPlayer size={size} className={className} />;
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

// ─── Pitch — polygon footballer dribbling a soccer ball ─────────────
// Player runs left↔right (mirrors direction on flip, like the Bonito
// fish), legs alternate in a running cadence, ball at their feet
// spins on its own axis. Small grass tufts pop up from underneath
// each footfall to sell the impact on turf.
function PitchPlayer({ size, className }: { size: number; className?: string }) {
  const SKIN = "#f5d4a8";
  const JERSEY = "#dc2626";          // bold red (works on green field)
  const JERSEY_TRIM = "#fbbf24";     // gold sleeve trim
  const SHORTS = "#1a1a1a";
  const SOCK = "#ffffff";
  const SHOE = "#1a1a1a";
  const BALL_LIGHT = "#ffffff";
  const BALL_DARK = "#1a1a1a";
  const GRASS_TUFT = "#34d399";
  return (
    <motion.span
      style={{ width: size * 2.2, height: size * 1.4, display: "inline-block" }}
      animate={{ x: [-3, 3, 3, -3, -3], scaleX: [1, 1, -1, -1, 1] }}
      transition={{
        duration: 3.0,
        times: [0, 0.45, 0.5, 0.95, 1],
        repeat: Infinity,
        ease: "easeInOut",
      }}
      className={className}
      aria-label="Studio is thinking — dribbling"
      role="status"
    >
      <svg
        viewBox="0 0 26 18"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Head */}
        <polygon points="4,1.5 6,1.5 6.5,3.5 6,5 4,5 3.5,3.5" fill={SKIN} />
        {/* Hair */}
        <polygon points="3.5,3 4,1 6,1 6.5,3" fill="#3a2818" />

        {/* Jersey — red trapezoid with gold sleeve trim band */}
        <polygon points="2,5.5 8,5.5 8.5,11 1.5,11" fill={JERSEY} />
        <polygon points="2,5.5 2.5,5.5 2,7 1.6,7" fill={JERSEY_TRIM} />
        <polygon points="7.5,5.5 8,5.5 8.4,7 7.8,7" fill={JERSEY_TRIM} />
        {/* Jersey number-style chest stripe (subtle) */}
        <rect x="4.5" y="7" width="1" height="2.5" fill={JERSEY_TRIM} opacity="0.65" />

        {/* Arms — slightly back, runner's pump */}
        <polygon points="1.5,6 0.5,9 1.5,9.5 2.5,6.5" fill={SKIN} />
        <polygon points="8,6.5 9,6 10,9 9,9.5" fill={SKIN} />

        {/* Shorts */}
        <polygon points="2,11 8,11 7.5,13.5 2.5,13.5" fill={SHORTS} />

        {/* Back leg — slightly bent, planted */}
        <motion.g
          animate={{ y: [0, 0, -0.6, 0] }}
          transition={{
            duration: 0.7,
            times: [0, 0.4, 0.55, 1],
            repeat: Infinity,
            ease: "easeOut",
          }}
        >
          <polygon points="3,13.5 4.5,13.5 4,16 2.5,16" fill={SOCK} />
          <polygon points="2,16 5,16 5.2,17 1.8,17" fill={SHOE} />
        </motion.g>

        {/* Front leg — kicks forward toward the ball */}
        <motion.g
          style={{ originX: "6.5px", originY: "13.5px" }}
          animate={{ rotate: [-5, 15, 0, -5] }}
          transition={{
            duration: 0.7,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        >
          <polygon points="6,13.5 7.5,13.5 8,16 6.5,16" fill={SOCK} />
          <polygon points="6,16 9,16 9.2,17 5.8,17" fill={SHOE} />
        </motion.g>

        {/* Soccer ball — spins continuously on its own axis */}
        <motion.g
          style={{ originX: "13px", originY: "15.5px" }}
          animate={{ rotate: [0, 360] }}
          transition={{ duration: 0.7, repeat: Infinity, ease: "linear" }}
        >
          <circle cx="13" cy="15.5" r="2.1" fill={BALL_LIGHT} />
          {/* Classic black pentagonal patches */}
          <polygon
            points="13,14.1 14.3,14.85 13.85,16.2 12.15,16.2 11.7,14.85"
            fill={BALL_DARK}
          />
          <polygon
            points="11.1,14.6 11.5,15.1 11.1,15.5 10.7,15.1"
            fill={BALL_DARK}
          />
          <polygon
            points="14.9,14.6 15.3,15.1 14.9,15.5 14.5,15.1"
            fill={BALL_DARK}
          />
          <polygon
            points="11.4,16.7 11.8,17.1 11.4,17.5 11,17.1"
            fill={BALL_DARK}
          />
          <polygon
            points="14.6,16.7 15,17.1 14.6,17.5 14.2,17.1"
            fill={BALL_DARK}
          />
        </motion.g>

        {/* Grass tufts — pop up from under each footfall and fade */}
        {[
          { x: 3, delay: 0.0  },
          { x: 7, delay: 0.35 },
          { x: 1.5, delay: 0.7 },
        ].map(({ x, delay }, i) => (
          <motion.polygon
            key={`tuft-${i}`}
            points={`${x},17.5 ${x - 0.4},16.7 ${x},17.1 ${x + 0.3},16.6 ${x + 0.5},17.4`}
            fill={GRASS_TUFT}
            animate={{
              opacity: [0, 0.85, 0],
              y: [0, -0.8, -1.4],
            }}
            transition={{
              duration: 0.9,
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

// ─── Wafū — sumo wrestler in shiko squat, dirt pops on impact ────────
// Classic deep-squat pose: round head + topknot up top, big belly in
// the middle, both knees bent wide and out to form a triangular base.
// Body rocks gently side-to-side; each foot lifts a few pixels then
// slams down with a burst of dirt particles underneath. Wider polygon
// silhouette than the previous version, matching the low-poly sumo
// reference Shabari sent.
function WafuSumo({ size, className }: { size: number; className?: string }) {
  const SKIN = "#f5ead0";       // light flesh tone
  const SKIN_SHADE = "#dccda4"; // belly shadow / under-arm shade
  const MAWASHI = "#1a1a1a";    // dark loincloth (classic black)
  const HAIR = "#1a1a1a";       // topknot + brow + eyes
  const DIRT = "#8b7355";
  return (
    <motion.span
      style={{ width: size * 1.8, height: size * 1.8, display: "inline-block" }}
      animate={{ rotate: [-1.5, 1.5, -1.5] }}
      transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
      className={className}
      aria-label="Studio is thinking — sumo shiko"
      role="status"
    >
      <svg
        viewBox="0 0 30 32"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", overflow: "visible" }}
      >
        {/* Topknot — small black dome on top of the head */}
        <polygon points="13,1 17,1 18,3.5 12,3.5" fill={HAIR} />
        {/* Head — hexagonal skin polygon */}
        <polygon points="11,3.5 19,3.5 21,7 19,10.5 11,10.5 9,7" fill={SKIN} />
        {/* Brow band — slight horizontal shade above eyes */}
        <polygon points="11,7 19,7 19,7.6 11,7.6" fill={SKIN_SHADE} />
        {/* Eyes */}
        <circle cx="13" cy="8.2" r="0.5" fill={HAIR} />
        <circle cx="17" cy="8.2" r="0.5" fill={HAIR} />
        {/* Mouth — small horizontal line */}
        <rect x="14" y="9.5" width="2" height="0.5" fill={HAIR} />

        {/* Shoulders + upper torso — wide polygon flowing into belly */}
        <polygon points="6,11 24,11 26,16 4,16" fill={SKIN} />
        {/* Big round belly — the dominant feature */}
        <polygon
          points="4,16 26,16 27,22 22,25 8,25 3,22"
          fill={SKIN}
        />
        {/* Belly shadow — subtle crescent at bottom of belly */}
        <polygon
          points="6,22 24,22 22,25 8,25"
          fill={SKIN_SHADE}
        />

        {/* Arms — hang from the shoulders, slightly forward / out, with
            hands resting near the knees (the shiko pose). */}
        <polygon points="5,12 8,11.5 8,21 5,21.5" fill={SKIN} />
        <polygon points="22,11.5 25,12 25,21.5 22,21" fill={SKIN} />
        {/* Hands resting on thighs */}
        <polygon points="3,21 8,20 9,22 3,23" fill={SKIN} />
        <polygon points="22,20 27,21 27,23 21,22" fill={SKIN} />

        {/* Mawashi — black band across waist + front flap between legs */}
        <rect x="6" y="19.5" width="18" height="2" fill={MAWASHI} />
        <polygon points="13,21 17,21 16.5,26 13.5,26" fill={MAWASHI} />

        {/* LEFT LEG — shiko stance, thigh going down-out, calf coming
            back in to a wide flat foot. The whole g flexes a tiny bit
            on the foot-down phase so the stomp reads physically. */}
        <motion.g
          animate={{ y: [0, -1.2, 0, 0] }}
          transition={{
            duration: 1.0,
            times: [0, 0.25, 0.5, 1],
            repeat: Infinity,
            ease: "easeOut",
          }}
        >
          {/* Thigh: hip (8,22) → knee (1,26) */}
          <polygon points="6,22 11,22 8,28 1,27" fill={SKIN} />
          {/* Calf: knee → ankle */}
          <polygon points="1,27 8,28 7,31 2,30" fill={SKIN_SHADE} />
          {/* Foot — flat black slab */}
          <rect x="0.5" y="30" width="8" height="1.5" fill={HAIR} />
        </motion.g>

        {/* RIGHT LEG — mirror, counter-phase stomp */}
        <motion.g
          animate={{ y: [0, 0, -1.2, 0] }}
          transition={{
            duration: 1.0,
            times: [0, 0.4, 0.65, 1],
            repeat: Infinity,
            ease: "easeOut",
          }}
        >
          <polygon points="19,22 24,22 29,27 22,28" fill={SKIN} />
          <polygon points="22,28 29,27 28,30 23,31" fill={SKIN_SHADE} />
          <rect x="21.5" y="30" width="8" height="1.5" fill={HAIR} />
        </motion.g>

        {/* DIRT POPS — bursts from under each foot the moment it lands.
            Left side fires on the first stomp half, right side on the
            second half. Each particle fades up + grows outward. */}
        {[
          // Left foot impact pops
          { x: 1.5, delay: 0.42, dx: -1.6 },
          { x: 4.0, delay: 0.45, dx:  0   },
          { x: 6.5, delay: 0.42, dx:  1.6 },
          // Right foot impact pops
          { x: 22.5, delay: 0.92, dx: -1.6 },
          { x: 25.0, delay: 0.95, dx:  0   },
          { x: 27.5, delay: 0.92, dx:  1.6 },
        ].map(({ x, delay, dx }, i) => (
          <motion.circle
            key={`dirt-${i}`}
            cx={x}
            cy={31.5}
            r={0.5}
            fill={DIRT}
            animate={{
              cy: [31.5, 29.5],
              cx: [x, x + dx],
              r: [0.4, 1.2],
              opacity: [0, 0.75, 0],
            }}
            transition={{
              duration: 0.55,
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
