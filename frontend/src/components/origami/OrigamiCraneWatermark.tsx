"use client";

/**
 * OrigamiCraneWatermark — classic side-profile origami paper crane,
 * rendered as a silhouette with internal fold-lines (the thin gaps
 * between polygons act as the fold creases).
 *
 * Shape inspired by the classic 折鶴 (orizuru) — tall back wing, sharp
 * upward tail spike, diamond body, slender neck extending forward to a
 * small beak. Each polygon is a folded panel; tiny gaps between them
 * read as the paper's crease lines at watermark opacity.
 *
 * Single-color so it picks up the theme's accent. Pass `color` and
 * `opacity` from the active chat theme.
 */

interface Props {
  /** Pixel size of the crane (square). Default 320. */
  size?: number;
  /** Fill color (any CSS color). Default brand lavender. */
  color?: string;
  /** Watermark opacity (0-1). Default 0.08. */
  opacity?: number;
  className?: string;
}

export function OrigamiCraneWatermark({
  size = 320,
  color = "#a78bfa",
  opacity = 0.08,
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
        style={{ opacity }}
      >
        {/* The crane is built from abutting polygons; the hairline gaps
            between them naturally read as fold creases. All share the
            same fill so the silhouette reads as one piece of paper. */}
        <g fill={color} stroke="none">
          {/* Tail — long sharp spike pointing up-right */}
          <polygon points="58,42 96,4 66,55" />

          {/* Back wing — large triangle pointing up-left */}
          <polygon points="48,42 12,18 44,55" />

          {/* Body — upper sliver between the two wings */}
          <polygon points="48,42 58,42 53,52" />

          {/* Body — central diamond / hull */}
          <polygon points="44,55 66,55 60,75 50,72" />

          {/* Front wing fold — extending down-right from the body */}
          <polygon points="66,55 92,92 60,75" />

          {/* Neck — slender triangle reaching forward-down to the left */}
          <polygon points="44,55 18,68 28,62" />

          {/* Beak — small pointed wedge at the head */}
          <polygon points="18,68 6,64 16,72" />
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
