"use client";

/**
 * OrigamiCraneLoader — a paper-folded crane that gently flaps while
 * Origami is doing background work (planning a build, streaming the
 * first tokens, executing tools).
 *
 * Pure SVG + CSS keyframes — no Framer Motion, no JS animation work
 * once mounted, so it's cheap to render on every chat re-paint.
 */

interface Props {
  size?: number;
  label?: string;
  /** Show without surrounding text container — for use inside buttons */
  inline?: boolean;
  className?: string;
}

export function OrigamiCraneLoader({
  size = 56,
  label = "Origami is folding…",
  inline = false,
  className = "",
}: Props) {
  const crane = (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={`origami-crane ${className}`}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="craneBodyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#a855f7" />
          <stop offset="100%" stopColor="#6d28d9" />
        </linearGradient>
        <linearGradient id="craneWingGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#c084fc" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <linearGradient id="craneTailGrad" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#6d28d9" />
          <stop offset="100%" stopColor="#4c1d95" />
        </linearGradient>
      </defs>

      {/* Tail — folded triangle pointing down-right */}
      <polygon
        points="50,52 86,78 64,68"
        fill="url(#craneTailGrad)"
        className="crane-tail"
      />

      {/* Right wing — outstretched, fades to point */}
      <polygon
        points="50,46 96,32 78,58"
        fill="url(#craneWingGrad)"
        className="crane-wing-right"
      />

      {/* Left wing — mirror */}
      <polygon
        points="50,46 4,32 22,58"
        fill="url(#craneWingGrad)"
        className="crane-wing-left"
      />

      {/* Body — central diamond, sits on top of wings */}
      <polygon
        points="50,46 62,72 50,82 38,72"
        fill="url(#craneBodyGrad)"
        className="crane-body"
      />

      {/* Neck — angled triangle pointing up */}
      <polygon
        points="50,46 56,18 46,28"
        fill="url(#craneBodyGrad)"
        className="crane-neck"
      />

      {/* Head — tiny beak */}
      <polygon
        points="56,18 62,22 54,24"
        fill="#4c1d95"
        className="crane-head"
      />

      <style>{`
        .origami-crane {
          transform-origin: 50% 60%;
          animation: crane-bob 2.4s ease-in-out infinite;
        }
        .crane-wing-left {
          transform-origin: 50% 46%;
          animation: wing-flap-left 1.6s ease-in-out infinite;
        }
        .crane-wing-right {
          transform-origin: 50% 46%;
          animation: wing-flap-right 1.6s ease-in-out infinite;
        }
        .crane-tail {
          transform-origin: 50% 52%;
          animation: tail-sway 2.8s ease-in-out infinite;
        }
        .crane-neck, .crane-head {
          transform-origin: 50% 46%;
          animation: neck-tilt 3.2s ease-in-out infinite;
        }
        @keyframes crane-bob {
          0%, 100% { transform: translateY(0); }
          50%      { transform: translateY(-3px); }
        }
        @keyframes wing-flap-left {
          0%, 100% { transform: rotate(0deg); }
          50%      { transform: rotate(-12deg); }
        }
        @keyframes wing-flap-right {
          0%, 100% { transform: rotate(0deg); }
          50%      { transform: rotate(12deg); }
        }
        @keyframes tail-sway {
          0%, 100% { transform: rotate(0deg); }
          50%      { transform: rotate(4deg); }
        }
        @keyframes neck-tilt {
          0%, 100% { transform: rotate(0deg); }
          25%      { transform: rotate(-2deg); }
          75%      { transform: rotate(2deg); }
        }
        @media (prefers-reduced-motion: reduce) {
          .origami-crane,
          .crane-wing-left,
          .crane-wing-right,
          .crane-tail,
          .crane-neck,
          .crane-head {
            animation: none !important;
          }
        }
      `}</style>
    </svg>
  );

  if (inline) return crane;

  return (
    <div className="flex flex-col items-center gap-2 py-2">
      {crane}
      {label && (
        <span className="text-xs text-muted-foreground italic">{label}</span>
      )}
    </div>
  );
}
