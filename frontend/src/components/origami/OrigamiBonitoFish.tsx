"use client";

/**
 * OrigamiBonitoFish — folded-paper bonito tuna in Bonito brand purple.
 * Used as the hero illustration on every custom error page (404 / 403 /
 * 500 / 503 / global-error) instead of the previous `><(((°>` ASCII.
 *
 * Anatomy (purple, all triangles):
 *  - elongated diamond body
 *  - forked tail (two triangles)
 *  - top dorsal fin (triangle)
 *  - side pectoral fin (triangle)
 *  - three folded lateral stripes on the back
 *  - small dark eye
 *
 * Moods change posture + animation:
 *  - swimming     gentle bob + tail flick + bubbles
 *  - lost         floats slowly, with question-mark bubbles  (404)
 *  - locked       calm, small padlock badge overlay          (403)
 *  - capsized     rotated 180°, slight wobble                (500 / generic error)
 *  - maintenance  stationary, small wrench badge             (503)
 */

import { Lock, Wrench, HelpCircle } from "lucide-react";

export type BonitoFishMood =
  | "swimming"
  | "lost"
  | "locked"
  | "capsized"
  | "maintenance";

interface Props {
  /** Visual mood — drives posture + which badge is rendered */
  mood?: BonitoFishMood;
  /** Pixel size (square). Default 220. */
  size?: number;
  className?: string;
}

const MOOD_CLASS: Record<BonitoFishMood, string> = {
  swimming: "fish-swim",
  lost: "fish-lost",
  locked: "fish-locked",
  capsized: "fish-capsized",
  maintenance: "fish-maintenance",
};

export function OrigamiBonitoFish({
  mood = "swimming",
  size = 220,
  className = "",
}: Props) {
  return (
    <div
      className={`origami-fish-wrap ${className}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 220 220"
        width={size}
        height={size}
        className={`origami-fish ${MOOD_CLASS[mood]}`}
      >
        <defs>
          <linearGradient id="fishBody" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#c084fc" />
            <stop offset="60%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#4c1d95" />
          </linearGradient>
          <linearGradient id="fishBelly" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#a78bfa" />
            <stop offset="100%" stopColor="#6d28d9" />
          </linearGradient>
          <linearGradient id="fishTail" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#7c3aed" />
            <stop offset="100%" stopColor="#4c1d95" />
          </linearGradient>
          <linearGradient id="fishFin" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#c084fc" />
            <stop offset="100%" stopColor="#7c3aed" />
          </linearGradient>
        </defs>

        {/* Whole fish container; mood class translates / rotates this group */}
        <g className="fish-group">
          {/* Tail — two folded triangles on the right */}
          <g className="fish-tail">
            <polygon
              points="178,110 215,75 188,110"
              fill="url(#fishTail)"
              opacity="0.95"
            />
            <polygon
              points="178,110 215,145 188,110"
              fill="url(#fishTail)"
              opacity="0.85"
            />
          </g>

          {/* Pectoral fin — under-belly triangle */}
          <polygon
            points="95,130 130,155 110,138"
            fill="url(#fishFin)"
            opacity="0.85"
            className="fish-pec"
          />

          {/* Body — upper half (back, darker purple) */}
          <polygon
            points="20,110 95,72 175,108 185,110 175,112 95,148"
            fill="url(#fishBody)"
          />

          {/* Body — lower belly highlight (lighter triangle along the bottom) */}
          <polygon
            points="40,118 175,118 175,112 95,148"
            fill="url(#fishBelly)"
            opacity="0.65"
          />

          {/* Dorsal fin — triangle on top */}
          <polygon
            points="85,75 110,40 135,75"
            fill="url(#fishFin)"
            className="fish-dorsal"
          />

          {/* Lateral stripes — folded mid-tone triangles along the back */}
          <polygon points="92,90 110,82 110,96" fill="#4c1d95" opacity="0.6" />
          <polygon points="118,88 138,80 138,98" fill="#4c1d95" opacity="0.55" />
          <polygon points="146,92 162,86 162,100" fill="#4c1d95" opacity="0.5" />

          {/* Snout fold accent — small lighter triangle at the front (left tip) */}
          <polygon
            points="20,110 38,104 38,116"
            fill="#a78bfa"
            opacity="0.75"
          />

          {/* Eye */}
          <circle cx="40" cy="108" r="3.5" fill="#1a0b3d" />
          <circle cx="39" cy="107" r="1" fill="#f5f0e8" />
        </g>

        {/* Floating bubbles — visible when swimming/lost moods */}
        <g className="fish-bubbles">
          <circle cx="200" cy="60" r="3" fill="#a78bfa" opacity="0.6" />
          <circle cx="205" cy="40" r="2" fill="#a78bfa" opacity="0.5" />
          <circle cx="195" cy="30" r="1.5" fill="#a78bfa" opacity="0.4" />
        </g>

        <style>{`
          .origami-fish { display: block; }

          .fish-group {
            transform-origin: 110px 110px;
            animation: bob 3.4s ease-in-out infinite;
          }
          .fish-tail {
            transform-origin: 178px 110px;
            animation: tail-flick 1.6s ease-in-out infinite;
          }
          .fish-dorsal {
            transform-origin: 110px 75px;
            animation: dorsal-sway 4s ease-in-out infinite;
          }
          .fish-pec {
            transform-origin: 105px 145px;
            animation: pec-flutter 1.2s ease-in-out infinite;
          }
          .fish-bubbles circle {
            animation: bubble-rise 3.5s ease-in infinite;
            transform-origin: center;
          }
          .fish-bubbles circle:nth-child(2) { animation-delay: 0.8s; }
          .fish-bubbles circle:nth-child(3) { animation-delay: 1.6s; }

          /* Mood-driven posture overrides */
          .fish-capsized .fish-group {
            animation: capsized-wobble 4s ease-in-out infinite;
          }
          .fish-capsized .fish-tail,
          .fish-capsized .fish-dorsal,
          .fish-capsized .fish-pec {
            animation-duration: 6s; /* slower; the fish is barely alive */
            opacity: 0.85;
          }
          .fish-capsized .fish-bubbles { display: none; }

          .fish-lost .fish-group { animation: lost-drift 5s ease-in-out infinite; }

          .fish-locked .fish-group { animation: locked-still 6s ease-in-out infinite; }
          .fish-locked .fish-tail,
          .fish-locked .fish-pec { animation-duration: 3s; }

          .fish-maintenance .fish-group {
            animation: none;
            transform: translateY(2px);
          }
          .fish-maintenance .fish-tail,
          .fish-maintenance .fish-dorsal,
          .fish-maintenance .fish-pec,
          .fish-maintenance .fish-bubbles { animation: none; }

          @keyframes bob {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50%      { transform: translateY(-6px) rotate(-1.5deg); }
          }
          @keyframes tail-flick {
            0%, 100% { transform: rotate(0deg); }
            50%      { transform: rotate(-12deg); }
          }
          @keyframes dorsal-sway {
            0%, 100% { transform: rotate(0deg); }
            50%      { transform: rotate(2deg); }
          }
          @keyframes pec-flutter {
            0%, 100% { transform: rotate(0deg); }
            50%      { transform: rotate(8deg); }
          }
          @keyframes bubble-rise {
            0%   { transform: translateY(0); opacity: 0; }
            20%  { opacity: 0.6; }
            100% { transform: translateY(-50px); opacity: 0; }
          }
          @keyframes capsized-wobble {
            0%, 100% { transform: rotate(180deg) translateY(0); }
            50%      { transform: rotate(184deg) translateY(-3px); }
          }
          @keyframes lost-drift {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            33%      { transform: translate(-6px, -4px) rotate(-3deg); }
            66%      { transform: translate(4px, 2px) rotate(2deg); }
          }
          @keyframes locked-still {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50%      { transform: translateY(-2px) rotate(-0.5deg); }
          }

          @media (prefers-reduced-motion: reduce) {
            .origami-fish *, .fish-group, .fish-tail, .fish-dorsal,
            .fish-pec, .fish-bubbles circle {
              animation: none !important;
            }
          }
        `}</style>
      </svg>

      {/* Mood badges — overlaid on the fish to add context without a second illustration */}
      {mood === "locked" && (
        <div className="fish-badge">
          <Lock className="h-4 w-4" />
        </div>
      )}
      {mood === "maintenance" && (
        <div className="fish-badge">
          <Wrench className="h-4 w-4" />
        </div>
      )}
      {mood === "lost" && (
        <div className="fish-badge">
          <HelpCircle className="h-4 w-4" />
        </div>
      )}

      <style>{`
        .origami-fish-wrap { position: relative; display: inline-block; }
        .fish-badge {
          position: absolute;
          right: 18%;
          top: 12%;
          width: 32px; height: 32px;
          border-radius: 9999px;
          background: rgb(124 58 237);
          color: white;
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 6px 16px rgba(124, 58, 237, 0.35);
          animation: badge-pulse 2.4s ease-in-out infinite;
        }
        @keyframes badge-pulse {
          0%, 100% { transform: scale(1); }
          50%      { transform: scale(1.08); }
        }
        @media (prefers-reduced-motion: reduce) {
          .fish-badge { animation: none; }
        }
      `}</style>
    </div>
  );
}
