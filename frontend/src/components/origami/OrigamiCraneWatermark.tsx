"use client";

/**
 * OrigamiCraneWatermark — line-art origami crane, drawn as stroke-only
 * paths matching the reference orizuru silhouette (tail spike up-right,
 * two wing/fold points dropping to the bottom-left, body diamond
 * center, neck + beak extending to the upper-left).
 *
 * Outline is one closed path; the visible internal fold creases are
 * three short additional segments. Stroke uses `currentColor` so the
 * parent's text color cascades — pass `color` to override directly.
 */

interface Props {
  /** Pixel size of the crane (square). Default 320. */
  size?: number;
  /** Stroke color (any CSS color). Default white. */
  color?: string;
  /** Watermark opacity (0-1). Default 0.12. Strokes need slightly more
   *  than fills to read at the same visual weight. */
  opacity?: number;
  /** Stroke width in viewBox units. Default 2.2. */
  strokeWidth?: number;
  className?: string;
}

export function OrigamiCraneWatermark({
  size = 320,
  color = "#ffffff",
  opacity = 0.12,
  strokeWidth = 2.2,
  className = "",
}: Props) {
  return (
    <div
      className={`absolute inset-0 flex items-center justify-center pointer-events-none select-none z-0 ${className}`}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 100 100"
        width={size}
        height={size}
        className="origami-crane-watermark"
        style={{ opacity, color }}
      >
        <g
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeLinejoin="round"
          strokeLinecap="round"
        >
          {/* Outer silhouette — single closed path traced clockwise
              from the tail tip. Vertices (approx):
                A tail tip       (88, 8)
                B body upper-back (55, 36)
                C body bottom-back (47, 82)
                D back-wing fold  (32, 60)
                E front-wing tip  (8, 82)
                F front fold base (30, 48)
                G beak tip        (8, 28)
                H neck base       (30, 35)
           */}
          <path d="
            M 88 8
            L 55 36
            L 47 82
            L 32 60
            L 8 82
            L 30 48
            L 8 28
            L 30 35
            Z
          " />

          {/* Internal fold creases */}
          {/* 1. Central back-to-belly fold (the spine of the crane) */}
          <path d="M 55 36 L 47 82" />
          {/* 2. Body diagonal — back-wing fold to body front */}
          <path d="M 32 60 L 55 36" />
          {/* 3. Front belly fold — front wing top up to body front */}
          <path d="M 30 48 L 47 82" />
          {/* 4. Neck crease — neck base into body */}
          <path d="M 30 35 L 30 48" />
        </g>

        <style>{`
          .origami-crane-watermark {
            transform-origin: 50% 60%;
            animation: crane-watermark-breathe 9s ease-in-out infinite;
          }
          @keyframes crane-watermark-breathe {
            0%, 100% { transform: scale(1) translateY(0); }
            50%      { transform: scale(1.02) translateY(-2px); }
          }
          @media (prefers-reduced-motion: reduce) {
            .origami-crane-watermark { animation: none; }
          }
        `}</style>
      </svg>
    </div>
  );
}
