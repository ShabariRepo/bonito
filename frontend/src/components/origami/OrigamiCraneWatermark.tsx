"use client";

/**
 * OrigamiCraneWatermark — large, faded lavender origami crane that sits
 * behind the chat content as ambient branding. NOT the loader version —
 * this one is intentionally static (very slow breath only) and tuned
 * for legibility of overlaid text.
 *
 * Wire it inside a `relative`-positioned chat scroll container; the
 * watermark itself is `absolute inset-0`, `pointer-events-none`, and
 * fades the SVG to ~7% opacity so user / assistant bubbles stay sharp.
 */

interface Props {
  /** Pixel size of the crane (square). Default 320. */
  size?: number;
  /** Override watermark opacity (0-1). Default 0.07. */
  opacity?: number;
  className?: string;
}

export function OrigamiCraneWatermark({
  size = 320,
  opacity = 0.07,
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
        <defs>
          {/* Lavender palette — lighter than the loader's deep purple so the
              text-foreground colour can layer on top without clashing */}
          <linearGradient id="craneWmBody" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#e9d5ff" />
            <stop offset="100%" stopColor="#c4b5fd" />
          </linearGradient>
          <linearGradient id="craneWmWing" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ddd6fe" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
          <linearGradient id="craneWmTail" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#c4b5fd" />
            <stop offset="100%" stopColor="#a78bfa" />
          </linearGradient>
        </defs>

        {/* Tail */}
        <polygon points="50,52 86,78 64,68" fill="url(#craneWmTail)" />

        {/* Wings outstretched */}
        <polygon points="50,46 96,32 78,58" fill="url(#craneWmWing)" />
        <polygon points="50,46 4,32 22,58" fill="url(#craneWmWing)" />

        {/* Body diamond */}
        <polygon points="50,46 62,72 50,82 38,72" fill="url(#craneWmBody)" />

        {/* Neck */}
        <polygon points="50,46 56,18 46,28" fill="url(#craneWmBody)" />

        {/* Head beak */}
        <polygon points="56,18 62,22 54,24" fill="#a78bfa" />

        <style>{`
          .origami-crane-watermark {
            transform-origin: 50% 60%;
            animation: crane-watermark-breathe 8s ease-in-out infinite;
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
