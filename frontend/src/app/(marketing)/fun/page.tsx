"use client";

import { useEffect, useRef, useMemo } from "react";
import Image from "next/image";

interface Wave {
  y: number;
  speed: number;
  amplitude: number;
  frequency: number;
  phase: number;
  opacity: number;
}

interface CanvasRipple {
  birth: number;
  // Organic shape: radius varies by angle using these harmonics
  offsets: number[];
}

export default function FunPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const ripplesRef = useRef<CanvasRipple[]>([]);
  const lastRippleRef = useRef<number>(0);

  // Stable particle positions (SSR-safe)
  const particles = useMemo(() => {
    const seed = 42;
    const rng = (i: number) => {
      const x = Math.sin(seed + i * 127.1) * 43758.5453;
      return x - Math.floor(x);
    };
    return Array.from({ length: 25 }, (_, i) => ({
      size: 2 + rng(i * 3) * 5,
      left: rng(i * 3 + 1) * 100,
      top: rng(i * 3 + 2) * 100,
      duration: 10 + rng(i * 7) * 15,
      delay: rng(i * 11) * -20,
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

    // Wave layers
    const waves: Wave[] = Array.from({ length: 6 }, (_, i) => ({
      y: 0.5 + (i - 2.5) * 0.08,
      speed: 0.3 + (i * 0.618 % 1) * 0.4,
      amplitude: 14 + (i * 0.382 % 1) * 16,
      frequency: 0.003 + (i * 0.236 % 1) * 0.004,
      phase: (i * 1.618) % (Math.PI * 2),
      opacity: 0.06 + (i * 0.472 % 1) * 0.1,
    }));

    const LOGO_RADIUS = Math.min(w, h) * 0.35; // half of 70vmin logo
    const RIPPLE_LIFETIME = 3500;
    const RIPPLE_INTERVAL_BASE = 1800;
    const RIPPLE_INTERVAL_JITTER = 600;
    const MAX_RIPPLE_RADIUS = Math.max(w, h) * 0.6;
    const HARMONICS = 8;

    const startTime = performance.now();

    const draw = (now: number) => {
      const t = (now - startTime) / 1000;
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;

      // --- Spawn ripples organically ---
      const timeSinceLast = now - lastRippleRef.current;
      const nextInterval = RIPPLE_INTERVAL_BASE + Math.sin(now * 0.001) * RIPPLE_INTERVAL_JITTER;
      if (timeSinceLast > nextInterval) {
        const offsets: number[] = [];
        for (let k = 0; k < HARMONICS; k++) {
          offsets.push((Math.random() - 0.5) * 2 * (0.03 / (k + 1)));
        }
        ripplesRef.current.push({ birth: now, offsets });
        lastRippleRef.current = now;
        // Cap at 6 active
        if (ripplesRef.current.length > 6) {
          ripplesRef.current.shift();
        }
      }

      // --- Draw ripples (canvas, organic shapes) ---
      ripplesRef.current = ripplesRef.current.filter((r) => now - r.birth < RIPPLE_LIFETIME);
      for (const ripple of ripplesRef.current) {
        const age = (now - ripple.birth) / RIPPLE_LIFETIME;
        // Ease-out expansion: fast start, slow end (like real water)
        const easedAge = 1 - Math.pow(1 - age, 2.5);
        const baseRadius = LOGO_RADIUS * 0.85 + easedAge * MAX_RIPPLE_RADIUS;
        // Opacity: quick fade in, long fade out
        const fadeIn = Math.min(1, age * 8);
        const fadeOut = Math.pow(1 - age, 1.5);
        const alpha = fadeIn * fadeOut * 0.45;

        if (alpha < 0.005) continue;

        // Draw organic ring
        ctx.beginPath();
        const steps = 180;
        for (let s = 0; s <= steps; s++) {
          const angle = (s / steps) * Math.PI * 2;
          // Perturb radius with harmonics for organic wobble
          let rVar = 1;
          for (let k = 0; k < ripple.offsets.length; k++) {
            rVar += ripple.offsets[k] * Math.sin(angle * (k + 2) + t * 0.3 * (k + 1));
          }
          // Add subtle time-based breathing
          rVar += Math.sin(angle * 3 + t * 0.8) * 0.008 * (1 - age);
          const r = baseRadius * rVar;
          const px = cx + Math.cos(angle) * r;
          const py = cy + Math.sin(angle) * r;
          if (s === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.closePath();

        // Thinner stroke as ripple expands
        const lineWidth = Math.max(0.5, 2.5 * (1 - easedAge * 0.7));
        ctx.strokeStyle = `rgba(147, 93, 255, ${alpha})`;
        ctx.lineWidth = lineWidth;
        ctx.stroke();

        // Very subtle fill glow on inner ripples
        if (age < 0.3) {
          ctx.fillStyle = `rgba(124, 58, 237, ${alpha * 0.06})`;
          ctx.fill();
        }
      }

      // --- Draw waves ---
      waves.forEach((wave) => {
        const baseY = cy + (wave.y - 0.5) * h;

        ctx.beginPath();
        ctx.moveTo(0, baseY);

        for (let x = 0; x <= w; x += 2) {
          const distFromCenter = Math.abs(x - cx);
          const logoGap = LOGO_RADIUS * 1.1;
          const fadeFactor = distFromCenter < logoGap
            ? Math.pow(distFromCenter / logoGap, 2) * 0.2
            : Math.min(1, 0.2 + (distFromCenter - logoGap) / 300);

          const y =
            baseY +
            Math.sin(x * wave.frequency + t * wave.speed + wave.phase) *
              wave.amplitude * fadeFactor +
            Math.sin(x * wave.frequency * 2.3 + t * wave.speed * 0.7) *
              wave.amplitude * 0.3 * fadeFactor;

          ctx.lineTo(x, y);
        }

        ctx.lineTo(w, h);
        ctx.lineTo(0, h);
        ctx.closePath();

        const grad = ctx.createLinearGradient(0, baseY - wave.amplitude, 0, baseY + wave.amplitude + 100);
        grad.addColorStop(0, `rgba(124, 58, 237, ${wave.opacity})`);
        grad.addColorStop(0.5, `rgba(99, 102, 241, ${wave.opacity * 0.6})`);
        grad.addColorStop(1, `rgba(124, 58, 237, 0)`);
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(0, baseY);
        for (let x = 0; x <= w; x += 2) {
          const distFromCenter = Math.abs(x - cx);
          const logoGap = LOGO_RADIUS * 1.1;
          const fadeFactor = distFromCenter < logoGap
            ? Math.pow(distFromCenter / logoGap, 2) * 0.2
            : Math.min(1, 0.2 + (distFromCenter - logoGap) / 300);

          const y =
            baseY +
            Math.sin(x * wave.frequency + t * wave.speed + wave.phase) *
              wave.amplitude * fadeFactor +
            Math.sin(x * wave.frequency * 2.3 + t * wave.speed * 0.7) *
              wave.amplitude * 0.3 * fadeFactor;

          ctx.lineTo(x, y);
        }
        ctx.strokeStyle = `rgba(124, 58, 237, ${wave.opacity * 1.5})`;
        ctx.lineWidth = 1.5;
        ctx.stroke();
      });

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#0a0a0a] flex items-center justify-center">
      {/* Wave + ripple canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ zIndex: 1 }}
      />

      {/* Logo container -- fills most of the viewport */}
      <div className="relative z-10 flex items-center justify-center" style={{ width: "70vmin", height: "70vmin" }}>
        {/* Glow behind logo */}
        <div
          className="absolute rounded-full"
          style={{
            width: "90vmin",
            height: "90vmin",
            background: "radial-gradient(circle, rgba(124, 58, 237, 0.25) 0%, rgba(124, 58, 237, 0.08) 35%, transparent 65%)",
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
            className="object-contain drop-shadow-[0_0_120px_rgba(124,58,237,0.5)]"
            priority
          />
        </div>
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0 z-[2] pointer-events-none overflow-hidden">
        {particles.map((p, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-purple-500/20"
            style={{
              width: p.size,
              height: p.size,
              left: `${p.left}%`,
              top: `${p.top}%`,
              animation: `float-particle ${p.duration}s ease-in-out infinite`,
              animationDelay: `${p.delay}s`,
            }}
          />
        ))}
      </div>

      {/* CSS Animations */}
      <style jsx>{`
        @keyframes pulse-glow {
          0%, 100% { transform: scale(1); opacity: 0.6; }
          50% { transform: scale(1.15); opacity: 1; }
        }
        @keyframes logo-pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.04); }
        }
        @keyframes float-particle {
          0%, 100% { transform: translateY(0) translateX(0); opacity: 0.2; }
          25% { transform: translateY(-30px) translateX(10px); opacity: 0.5; }
          50% { transform: translateY(-10px) translateX(-15px); opacity: 0.3; }
          75% { transform: translateY(-40px) translateX(5px); opacity: 0.6; }
        }
      `}</style>
    </div>
  );
}
