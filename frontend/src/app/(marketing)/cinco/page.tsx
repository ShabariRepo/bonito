"use client";

import { useEffect, useRef, useMemo } from "react";
import Image from "next/image";

/* ─── Cinco de Mayo fiesta page ──────────────────────────────────────
   Pulsing Bonito logo over a warm Mexican fiesta background with
   floating sombreros, maracas, chili peppers, cacti, papel picado
   banners, and canvas-drawn fireworks / confetti bursts.
───────────────────────────────────────────────────────────────────── */

interface Firework {
  birth: number;
  x: number;
  y: number;
  color: string;
  particles: { angle: number; speed: number; decay: number }[];
}

const FIESTA_COLORS = [
  "#E53E3E", // red
  "#38A169", // green
  "#D69E2E", // gold
  "#ED8936", // orange
  "#E53E3E", // red
  "#F6E05E", // yellow
  "#FC8181", // pink
  "#68D391", // lime
];

const FLOATING_ITEMS = [
  { emoji: "🪇", size: 48 },
  { emoji: "🌶️", size: 40 },
  { emoji: "🪅", size: 50 },
  { emoji: "🌮", size: 44 },
  { emoji: "🎸", size: 48 },
  { emoji: "🌵", size: 44 },
  { emoji: "💀", size: 40 },
  { emoji: "🎺", size: 44 },
  { emoji: "🍹", size: 42 },
  { emoji: "🪇", size: 36 },
  { emoji: "🌶️", size: 38 },
  { emoji: "🌮", size: 40 },
  { emoji: "🎸", size: 46 },
  { emoji: "🌵", size: 42 },
  { emoji: "💀", size: 38 },
  { emoji: "🪅", size: 44 },
  { emoji: "🎺", size: 40 },
  { emoji: "🍹", size: 38 },
  { emoji: "🌶️", size: 34 },
  { emoji: "🌮", size: 36 },
  { emoji: "🪇", size: 42 },
  { emoji: "🎸", size: 40 },
  { emoji: "💀", size: 36 },
  { emoji: "🌵", size: 38 },
  { emoji: "🪅", size: 46 },
];

export default function CincoPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const fireworksRef = useRef<Firework[]>([]);
  const lastFireworkRef = useRef<number>(0);

  // Deterministic floating item positions
  const floatingItems = useMemo(() => {
    const seed = 55;
    const rng = (i: number) => {
      const x = Math.sin(seed + i * 127.1) * 43758.5453;
      return x - Math.floor(x);
    };
    return FLOATING_ITEMS.map((item, i) => ({
      ...item,
      left: rng(i * 3 + 1) * 100,
      top: rng(i * 3 + 2) * 100,
      duration: 12 + rng(i * 7) * 18,
      delay: rng(i * 11) * -20,
      rotateStart: rng(i * 13) * 360,
    }));
  }, []);

  // Papel picado banner triangles
  const bannerFlags = useMemo(() => {
    const colors = ["#E53E3E", "#38A169", "#D69E2E", "#ED8936", "#F6E05E", "#FC8181", "#68D391", "#805AD5"];
    return Array.from({ length: 20 }, (_, i) => ({
      color: colors[i % colors.length],
      delay: i * 0.15,
    }));
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let w = 0, h = 0;
    const resize = () => {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const FIREWORK_LIFETIME = 2000;
    const FIREWORK_INTERVAL = 1800;

    const draw = (now: number) => {
      ctx.clearRect(0, 0, w, h);

      // --- Spawn fireworks ---
      if (now - lastFireworkRef.current > FIREWORK_INTERVAL + Math.sin(now * 0.001) * 500) {
        const color = FIESTA_COLORS[Math.floor(Math.random() * FIESTA_COLORS.length)];
        const particles = Array.from({ length: 30 }, () => ({
          angle: Math.random() * Math.PI * 2,
          speed: 1.5 + Math.random() * 3,
          decay: 0.92 + Math.random() * 0.05,
        }));
        fireworksRef.current.push({
          birth: now,
          x: w * 0.15 + Math.random() * w * 0.7,
          y: h * 0.1 + Math.random() * h * 0.35,
          color,
          particles,
        });
        lastFireworkRef.current = now;
        if (fireworksRef.current.length > 6) fireworksRef.current.shift();
      }

      // --- Draw fireworks ---
      fireworksRef.current = fireworksRef.current.filter((f) => now - f.birth < FIREWORK_LIFETIME);
      for (const fw of fireworksRef.current) {
        const age = (now - fw.birth) / FIREWORK_LIFETIME;
        const globalAlpha = age < 0.1 ? age / 0.1 : Math.max(0, 1 - (age - 0.3) / 0.7);

        for (const p of fw.particles) {
          const dist = p.speed * age * 120 * (1 - age * 0.4);
          const px = fw.x + Math.cos(p.angle) * dist;
          const py = fw.y + Math.sin(p.angle) * dist + age * age * 40; // gravity

          const sparkSize = Math.max(0.5, 3 * (1 - age));
          ctx.beginPath();
          ctx.arc(px, py, sparkSize, 0, Math.PI * 2);
          ctx.fillStyle = fw.color;
          ctx.globalAlpha = globalAlpha * 0.8;
          ctx.fill();

          // Trailing glow
          if (age < 0.5) {
            ctx.beginPath();
            ctx.arc(px, py, sparkSize * 3, 0, Math.PI * 2);
            ctx.fillStyle = fw.color;
            ctx.globalAlpha = globalAlpha * 0.15;
            ctx.fill();
          }
        }
      }
      ctx.globalAlpha = 1;

      // --- Confetti rain ---
      const confettiCount = 40;
      for (let i = 0; i < confettiCount; i++) {
        const seed = i * 0.618;
        const x = ((seed * 1000 + now * 0.02 * (0.5 + (seed % 1) * 0.5)) % (w + 40)) - 20;
        const y = ((seed * 777 + now * 0.04 * (0.3 + (seed * 1.3 % 1) * 0.7)) % (h + 40)) - 20;
        const rot = now * 0.002 * (0.5 + seed) + seed * 100;
        const color = FIESTA_COLORS[i % FIESTA_COLORS.length];
        const size = 4 + (seed * 3 % 1) * 4;

        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(rot);
        ctx.fillStyle = color;
        ctx.globalAlpha = 0.5 + Math.sin(now * 0.003 + i) * 0.2;
        ctx.fillRect(-size / 2, -size / 4, size, size / 2);
        ctx.restore();
      }
      ctx.globalAlpha = 1;

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden flex items-center justify-center"
      style={{
        background: "linear-gradient(160deg, #1a0a2e 0%, #2d1b4e 25%, #1a0a2e 50%, #0d1f0d 75%, #1a0a2e 100%)",
      }}
    >
      {/* Warm fiesta radial overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at 50% 50%, rgba(214, 158, 46, 0.08) 0%, transparent 60%)",
        }}
      />

      {/* Papel picado banner — top */}
      <div className="absolute top-0 left-0 right-0 z-[5] flex justify-center overflow-hidden">
        <div className="flex gap-0" style={{ animation: "sway 4s ease-in-out infinite" }}>
          {bannerFlags.map((flag, i) => (
            <div
              key={i}
              className="relative"
              style={{
                width: "clamp(40px, 5vw, 70px)",
                height: "clamp(50px, 7vw, 90px)",
                animationDelay: `${flag.delay}s`,
              }}
            >
              {/* String */}
              <div className="absolute top-0 left-0 right-0 h-[3px]" style={{ backgroundColor: "#8B6914" }} />
              {/* Flag body */}
              <div
                className="absolute top-[3px] left-[2px] right-[2px]"
                style={{
                  height: "calc(100% - 3px)",
                  backgroundColor: flag.color,
                  clipPath: "polygon(0 0, 100% 0, 50% 100%)",
                  opacity: 0.85,
                  animation: `flag-wave ${2 + (i % 3) * 0.5}s ease-in-out infinite`,
                  animationDelay: `${flag.delay}s`,
                }}
              >
                {/* Cut-out pattern */}
                <div
                  className="absolute inset-0"
                  style={{
                    clipPath: "polygon(25% 20%, 35% 20%, 35% 40%, 65% 40%, 65% 20%, 75% 20%, 75% 55%, 50% 75%, 25% 55%)",
                    backgroundColor: "rgba(0,0,0,0.15)",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Papel picado banner — bottom */}
      <div className="absolute bottom-0 left-0 right-0 z-[5] flex justify-center overflow-hidden rotate-180">
        <div className="flex gap-0" style={{ animation: "sway 5s ease-in-out infinite reverse" }}>
          {bannerFlags.map((flag, i) => (
            <div
              key={`b-${i}`}
              className="relative"
              style={{
                width: "clamp(40px, 5vw, 70px)",
                height: "clamp(40px, 5vw, 60px)",
              }}
            >
              <div className="absolute top-0 left-0 right-0 h-[3px]" style={{ backgroundColor: "#8B6914" }} />
              <div
                className="absolute top-[3px] left-[2px] right-[2px]"
                style={{
                  height: "calc(100% - 3px)",
                  backgroundColor: flag.color,
                  clipPath: "polygon(0 0, 100% 0, 50% 100%)",
                  opacity: 0.6,
                  animation: `flag-wave ${2.5 + (i % 4) * 0.3}s ease-in-out infinite`,
                  animationDelay: `${flag.delay + 0.5}s`,
                }}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Canvas — fireworks & confetti */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ zIndex: 2 }}
      />

      {/* Floating emoji items */}
      <div className="absolute inset-0 z-[3] pointer-events-none overflow-hidden">
        {floatingItems.map((item, i) => (
          <div
            key={i}
            className="absolute select-none"
            style={{
              fontSize: item.size,
              left: `${item.left}%`,
              top: `${item.top}%`,
              animation: `float-fiesta ${item.duration}s ease-in-out infinite`,
              animationDelay: `${item.delay}s`,
              transform: `rotate(${item.rotateStart}deg)`,
              filter: "drop-shadow(0 0 8px rgba(0,0,0,0.3))",
            }}
          >
            {item.emoji}
          </div>
        ))}
      </div>

      {/* Logo container */}
      <div className="relative z-10 flex flex-col items-center justify-center" style={{ width: "70vmin", height: "70vmin" }}>
        {/* Fiesta glow behind logo */}
        <div
          className="absolute rounded-full"
          style={{
            width: "95vmin",
            height: "95vmin",
            background: "radial-gradient(circle, rgba(214, 158, 46, 0.2) 0%, rgba(229, 62, 62, 0.1) 30%, rgba(56, 161, 105, 0.05) 55%, transparent 70%)",
            animation: "pulse-glow 3s ease-in-out infinite",
          }}
        />

        {/* Logo */}
        <div
          className="relative z-10 w-full h-full"
          style={{ animation: "logo-pulse 3s ease-in-out infinite" }}
        >
          <Image
            src="/bonito-logo.png"
            alt="Bonito"
            fill
            className="object-contain"
            style={{ filter: "drop-shadow(0 0 80px rgba(214, 158, 46, 0.4)) drop-shadow(0 0 160px rgba(229, 62, 62, 0.2))" }}
            priority
          />
        </div>

        {/* Cinco de Mayo text */}
        <div
          className="absolute -bottom-4 z-20 text-center"
          style={{ animation: "text-bounce 2s ease-in-out infinite" }}
        >
          <p
            className="text-4xl md:text-5xl font-extrabold tracking-wider"
            style={{
              background: "linear-gradient(135deg, #E53E3E, #D69E2E, #38A169, #E53E3E)",
              backgroundSize: "300% 300%",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              animation: "gradient-shift 4s ease infinite",
              textShadow: "none",
              filter: "drop-shadow(0 2px 10px rgba(214, 158, 46, 0.3))",
            }}
          >
            CINCO DE MAYO
          </p>
          <p className="text-lg md:text-xl mt-1 font-medium" style={{ color: "rgba(246, 224, 94, 0.7)" }}>
            fiesta edition
          </p>
        </div>
      </div>

      {/* CSS Animations */}
      <style jsx>{`
        @keyframes pulse-glow {
          0%, 100% { transform: scale(1); opacity: 0.6; }
          50% { transform: scale(1.12); opacity: 1; }
        }
        @keyframes logo-pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.04); }
        }
        @keyframes float-fiesta {
          0%, 100% {
            transform: translateY(0) translateX(0) rotate(0deg);
            opacity: 0.5;
          }
          25% {
            transform: translateY(-40px) translateX(15px) rotate(10deg);
            opacity: 0.8;
          }
          50% {
            transform: translateY(-15px) translateX(-20px) rotate(-5deg);
            opacity: 0.6;
          }
          75% {
            transform: translateY(-50px) translateX(10px) rotate(8deg);
            opacity: 0.9;
          }
        }
        @keyframes sway {
          0%, 100% { transform: translateX(-5px) rotate(-1deg); }
          50% { transform: translateX(5px) rotate(1deg); }
        }
        @keyframes flag-wave {
          0%, 100% { transform: scaleY(1) rotate(0deg); }
          50% { transform: scaleY(1.05) rotate(1deg); }
        }
        @keyframes text-bounce {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-6px); }
        }
        @keyframes gradient-shift {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
      `}</style>
    </div>
  );
}
