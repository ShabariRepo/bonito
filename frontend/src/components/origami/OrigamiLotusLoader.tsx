"use client";

/**
 * OrigamiLotusLoader — eight purple petals open and close in a smooth
 * radial wave. Used while Origami is executing a plan (deploying
 * resources), where the build-and-bloom metaphor matches.
 */

interface Props {
  size?: number;
  label?: string;
  inline?: boolean;
  className?: string;
}

/** Eight petals, each rotated around the center. Indices 0..7 → 0°, 45°, ... */
const PETAL_ROTATIONS = [0, 45, 90, 135, 180, 225, 270, 315];

export function OrigamiLotusLoader({
  size = 56,
  label = "Origami is deploying…",
  inline = false,
  className = "",
}: Props) {
  const lotus = (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      className={`origami-lotus ${className}`}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="lotusOuter" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#c084fc" />
          <stop offset="100%" stopColor="#6d28d9" />
        </linearGradient>
        <linearGradient id="lotusInner" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#a855f7" />
          <stop offset="100%" stopColor="#7c3aed" />
        </linearGradient>
        <radialGradient id="lotusCenter" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fbbf24" />
          <stop offset="60%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#7c3aed" />
        </radialGradient>
      </defs>

      {/* Outer petals — longer, behind */}
      <g className="lotus-outer">
        {PETAL_ROTATIONS.map((deg, i) => (
          <polygon
            key={`outer-${i}`}
            points="50,16 56,42 50,58 44,42"
            fill="url(#lotusOuter)"
            transform={`rotate(${deg + 22.5} 50 50)`}
            className="lotus-petal"
            style={{ animationDelay: `${i * 0.12}s` }}
          />
        ))}
      </g>

      {/* Inner petals — shorter, on top, slightly rotated for layered look */}
      <g className="lotus-inner">
        {PETAL_ROTATIONS.map((deg, i) => (
          <polygon
            key={`inner-${i}`}
            points="50,28 55,46 50,56 45,46"
            fill="url(#lotusInner)"
            transform={`rotate(${deg} 50 50)`}
            className="lotus-petal-inner"
            style={{ animationDelay: `${i * 0.12 + 0.4}s` }}
          />
        ))}
      </g>

      {/* Center pod */}
      <circle cx="50" cy="50" r="5" fill="url(#lotusCenter)" className="lotus-center" />

      <style>{`
        .origami-lotus {
          transform-origin: 50% 50%;
          animation: lotus-rotate 14s linear infinite;
        }
        .lotus-petal {
          transform-origin: 50% 50%;
          animation: petal-pulse 2.4s ease-in-out infinite;
        }
        .lotus-petal-inner {
          transform-origin: 50% 50%;
          animation: petal-pulse-inner 2.4s ease-in-out infinite;
        }
        .lotus-center {
          transform-origin: 50% 50%;
          animation: center-pulse 2.4s ease-in-out infinite;
        }
        @keyframes lotus-rotate {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes petal-pulse {
          0%, 100% { transform: scale(1) rotate(var(--r, 0deg)); opacity: 0.9; }
          50%      { transform: scale(1.08); opacity: 1; }
        }
        @keyframes petal-pulse-inner {
          0%, 100% { transform: scale(1); opacity: 0.85; }
          50%      { transform: scale(1.12); opacity: 1; }
        }
        @keyframes center-pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50%      { transform: scale(1.25); opacity: 0.95; }
        }
        @media (prefers-reduced-motion: reduce) {
          .origami-lotus, .lotus-petal, .lotus-petal-inner, .lotus-center {
            animation: none !important;
          }
        }
      `}</style>
    </svg>
  );

  if (inline) return lotus;

  return (
    <div className="flex flex-col items-center gap-2 py-2">
      {lotus}
      {label && (
        <span className="text-xs text-muted-foreground italic">{label}</span>
      )}
    </div>
  );
}
