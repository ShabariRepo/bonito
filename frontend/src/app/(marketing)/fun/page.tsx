"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";

interface Ripple {
  id: number;
  x: number;
  y: number;
  birth: number;
}

interface Wave {
  id: number;
  y: number;
  speed: number;
  amplitude: number;
  frequency: number;
  phase: number;
  opacity: number;
}

export default function FunPage() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const rippleCounter = useRef(0);
  const animRef = useRef<number>(0);

  // Pulse ripples from logo center
  useEffect(() => {
    const interval = setInterval(() => {
      rippleCounter.current += 1;
      setRipples((prev) => [
        ...prev.filter((r) => Date.now() - r.birth < 2500),
        {
          id: rippleCounter.current,
          x: 0,
          y: 0,
          birth: Date.now(),
        },
      ]);
    }, 1200);
    return () => clearInterval(interval);
  }, []);

  // Canvas waves
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    // Generate wave layers
    const waves: Wave[] = Array.from({ length: 6 }, (_, i) => ({
      id: i,
      y: canvas.height * 0.5 + (i - 2.5) * 60,
      speed: 0.3 + Math.random() * 0.4,
      amplitude: 12 + Math.random() * 18,
      frequency: 0.003 + Math.random() * 0.004,
      phase: Math.random() * Math.PI * 2,
      opacity: 0.08 + Math.random() * 0.12,
    }));

    let startTime = performance.now();

    const draw = (now: number) => {
      const t = (now - startTime) / 1000;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const cx = canvas.width / 2;
      const cy = canvas.height / 2;

      // Draw cartoon waves
      waves.forEach((wave) => {
        const baseY = cy + (wave.y - canvas.height * 0.5);

        ctx.beginPath();
        ctx.moveTo(0, baseY);

        for (let x = 0; x <= canvas.width; x += 2) {
          // Distance from center affects amplitude (fade near logo)
          const distFromCenter = Math.abs(x - cx);
          const logoGap = 90;
          const fadeFactor = distFromCenter < logoGap
            ? distFromCenter / logoGap * 0.3
            : Math.min(1, 0.3 + (distFromCenter - logoGap) / 200);

          const y =
            baseY +
            Math.sin(x * wave.frequency + t * wave.speed + wave.phase) *
              wave.amplitude *
              fadeFactor +
            Math.sin(x * wave.frequency * 2.3 + t * wave.speed * 0.7) *
              wave.amplitude *
              0.3 *
              fadeFactor;

          ctx.lineTo(x, y);
        }

        // Complete the wave shape
        ctx.lineTo(canvas.width, canvas.height);
        ctx.lineTo(0, canvas.height);
        ctx.closePath();

        // Fill with subtle gradient
        const grad = ctx.createLinearGradient(0, baseY - wave.amplitude, 0, baseY + wave.amplitude + 100);
        grad.addColorStop(0, `rgba(124, 58, 237, ${wave.opacity})`);
        grad.addColorStop(0.5, `rgba(99, 102, 241, ${wave.opacity * 0.6})`);
        grad.addColorStop(1, `rgba(124, 58, 237, 0)`);
        ctx.fillStyle = grad;
        ctx.fill();

        // Stroke the wave line
        ctx.beginPath();
        ctx.moveTo(0, baseY);
        for (let x = 0; x <= canvas.width; x += 2) {
          const distFromCenter = Math.abs(x - cx);
          const logoGap = 90;
          const fadeFactor = distFromCenter < logoGap
            ? distFromCenter / logoGap * 0.3
            : Math.min(1, 0.3 + (distFromCenter - logoGap) / 200);

          const y =
            baseY +
            Math.sin(x * wave.frequency + t * wave.speed + wave.phase) *
              wave.amplitude *
              fadeFactor +
            Math.sin(x * wave.frequency * 2.3 + t * wave.speed * 0.7) *
              wave.amplitude *
              0.3 *
              fadeFactor;

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
      {/* Wave canvas */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full"
        style={{ zIndex: 1 }}
      />

      {/* Logo container with ripples */}
      <div className="relative z-10 flex items-center justify-center" style={{ width: 160, height: 160 }}>
        {/* Ripple rings */}
        {ripples.map((ripple) => {
          const age = Date.now() - ripple.birth;
          const progress = age / 2500;
          const scale = 1 + progress * 4;
          const opacity = Math.max(0, 1 - progress);
          return (
            <div
              key={ripple.id}
              className="absolute inset-0 rounded-full border-2 border-purple-500/60"
              style={{
                transform: `scale(${scale})`,
                opacity: opacity * 0.6,
                transition: "none",
                pointerEvents: "none",
              }}
            />
          );
        })}

        {/* Glow behind logo */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(124, 58, 237, 0.3) 0%, rgba(124, 58, 237, 0.1) 40%, transparent 70%)",
            transform: "scale(1.5)",
            animation: "pulse-glow 2.4s ease-in-out infinite",
          }}
        />

        {/* Logo */}
        <div
          className="relative z-10"
          style={{ animation: "logo-pulse 2.4s ease-in-out infinite" }}
        >
          <Image
            src="/bonito-logo.png"
            alt="Bonito"
            width={100}
            height={100}
            className="object-contain drop-shadow-[0_0_30px_rgba(124,58,237,0.5)]"
            priority
          />
        </div>
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0 z-[2] pointer-events-none overflow-hidden">
        {Array.from({ length: 20 }).map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full bg-purple-500/20"
            style={{
              width: 2 + Math.random() * 4,
              height: 2 + Math.random() * 4,
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float-particle ${8 + Math.random() * 12}s ease-in-out infinite`,
              animationDelay: `${Math.random() * -20}s`,
            }}
          />
        ))}
      </div>

      {/* CSS Animations */}
      <style jsx>{`
        @keyframes pulse-glow {
          0%, 100% { transform: scale(1.5); opacity: 0.6; }
          50% { transform: scale(1.8); opacity: 1; }
        }
        @keyframes logo-pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.08); }
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
