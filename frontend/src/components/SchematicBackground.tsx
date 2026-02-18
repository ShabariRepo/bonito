"use client";

import { useEffect, useRef } from "react";

// ─── Shape formations (normalized to ±1 range) ─────────────
// Each shape: array of [x1, y1, x2, y2] line segments
const SHAPES: number[][][] = [
  // Hexagon
  (() => {
    const s: number[][] = [];
    for (let i = 0; i < 6; i++) {
      const a1 = (i * 60 - 30) * Math.PI / 180;
      const a2 = ((i + 1) * 60 - 30) * Math.PI / 180;
      s.push([Math.cos(a1), Math.sin(a1), Math.cos(a2), Math.sin(a2)]);
    }
    return s;
  })(),
  // Rectangle
  [
    [-1.2, -0.7, 1.2, -0.7],
    [1.2, -0.7, 1.2, 0.7],
    [1.2, 0.7, -1.2, 0.7],
    [-1.2, 0.7, -1.2, -0.7],
  ],
  // Triangle
  (() => {
    const s: number[][] = [];
    for (let i = 0; i < 3; i++) {
      const a1 = (i * 120 - 90) * Math.PI / 180;
      const a2 = ((i + 1) * 120 - 90) * Math.PI / 180;
      s.push([Math.cos(a1), Math.sin(a1), Math.cos(a2), Math.sin(a2)]);
    }
    return s;
  })(),
  // Diamond
  [
    [0, -1.1, 1.1, 0],
    [1.1, 0, 0, 1.1],
    [0, 1.1, -1.1, 0],
    [-1.1, 0, 0, -1.1],
  ],
  // Circuit L-path
  [
    [-1.1, -0.5, 0, -0.5],
    [0, -0.5, 0, 0.3],
    [0, 0.3, 0.9, 0.3],
    [0.9, 0.3, 0.9, 0.8],
    [-1.1, -0.5, -1.1, 0.1],
  ],
  // Parallel traces
  [
    [-1.1, -0.4, 1.1, -0.4],
    [-1.1, 0, 0.3, 0],
    [0.3, 0, 0.3, 0.4],
    [0.3, 0.4, 1.1, 0.4],
  ],
  // Arrow / chevron
  [
    [-0.8, -0.8, 0.4, 0],
    [0.4, 0, -0.8, 0.8],
    [-0.3, -0.5, 0.9, 0],
    [0.9, 0, -0.3, 0.5],
  ],
  // Bracket / stepped path
  [
    [-1, -0.6, -0.3, -0.6],
    [-0.3, -0.6, -0.3, -0.1],
    [-0.3, -0.1, 0.3, -0.1],
    [0.3, -0.1, 0.3, 0.5],
    [0.3, 0.5, 1, 0.5],
  ],
  // Pentagon
  (() => {
    const s: number[][] = [];
    for (let i = 0; i < 5; i++) {
      const a1 = (i * 72 - 90) * Math.PI / 180;
      const a2 = ((i + 1) * 72 - 90) * Math.PI / 180;
      s.push([Math.cos(a1), Math.sin(a1), Math.cos(a2), Math.sin(a2)]);
    }
    return s;
  })(),
  // Cross / plus with arms
  [
    [-1, 0, 1, 0],
    [0, -1, 0, 1],
    [-0.6, -0.6, 0.6, -0.6],
    [-0.6, 0.6, 0.6, 0.6],
  ],
];

// ─── Types ──────────────────────────────────────────────────
interface Stick {
  x1: number; y1: number;
  x2: number; y2: number;
  tx1: number; ty1: number;
  tx2: number; ty2: number;
  opacity: number;
  targetOpacity: number;
  vx: number; vy: number;
  group: number; // -1 = free
  dashed: boolean;
}

interface Group {
  stickIds: number[];
  cx: number; cy: number;
  scale: number;
  shapeIdx: number;
  phase: "forming" | "holding" | "dissolving" | "idle";
  timer: number;
  formDur: number;
  holdDur: number;
  dissolveDur: number;
  idleDur: number;
}

// ─── Helpers ────────────────────────────────────────────────
function rand(min: number, max: number) {
  return min + Math.random() * (max - min);
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

// ─── Component ──────────────────────────────────────────────
export default function SchematicBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mql.matches) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;
    let animId: number;
    let lastTime = 0;

    // Responsive config
    const isMobile = window.innerWidth < 768;
    const NUM_GROUPS = isMobile ? 5 : 9;
    const STICKS_PER_GROUP = 8;
    const FREE_STICKS = isMobile ? 16 : 28;
    const TOTAL_STICKS = NUM_GROUPS * STICKS_PER_GROUP + FREE_STICKS;

    // Visual config
    const BASE_OPACITY = 0.09;
    const FORM_OPACITY = 0.22;
    const LERP_SPEED = 2.5;
    const LINE_COLOR = "175, 180, 190"; // neutral grey
    const DOT_R = 2;
    const GRID_SPACING = 50;
    const GRID_DOT_OPACITY = 0.035;
    const GRID_DOT_R = 0.8;

    const sticks: Stick[] = [];
    const groups: Group[] = [];

    // ── Init ──────────────────────────────────────────────
    function makeStick(group: number): Stick {
      const x = Math.random() * w;
      const y = Math.random() * h;
      const angle = Math.random() * Math.PI * 2;
      const len = rand(22, 55);
      const dx = Math.cos(angle) * len / 2;
      const dy = Math.sin(angle) * len / 2;
      return {
        x1: x - dx, y1: y - dy,
        x2: x + dx, y2: y + dy,
        tx1: x - dx, ty1: y - dy,
        tx2: x + dx, ty2: y + dy,
        opacity: BASE_OPACITY,
        targetOpacity: BASE_OPACITY,
        vx: rand(-6, 6),
        vy: rand(-6, 6),
        group,
        dashed: Math.random() < 0.2, // 20% of sticks are dashed
      };
    }

    function init() {
      sticks.length = 0;
      groups.length = 0;

      for (let g = 0; g < NUM_GROUPS; g++) {
        const ids: number[] = [];
        for (let i = 0; i < STICKS_PER_GROUP; i++) {
          ids.push(sticks.length);
          sticks.push(makeStick(g));
        }
        groups.push({
          stickIds: ids,
          cx: rand(w * 0.12, w * 0.88),
          cy: rand(h * 0.12, h * 0.88),
          scale: rand(isMobile ? 30 : 45, isMobile ? 55 : 85),
          shapeIdx: Math.floor(Math.random() * SHAPES.length),
          phase: "idle",
          timer: rand(0.3, 3), // staggered start
          formDur: rand(1.2, 2),
          holdDur: rand(1.5, 3),
          dissolveDur: rand(1, 2),
          idleDur: rand(1, 3),
        });
      }

      for (let i = 0; i < FREE_STICKS; i++) {
        sticks.push(makeStick(-1));
      }
    }

    function resize() {
      if (!canvas || !ctx) return;
      w = window.innerWidth;
      h = window.innerHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = w + "px";
      canvas.style.height = h + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    // ── Formation assignment ──────────────────────────────
    function assignFormation(g: Group) {
      const shape = SHAPES[g.shapeIdx];
      for (let i = 0; i < g.stickIds.length; i++) {
        const stick = sticks[g.stickIds[i]];
        if (i < shape.length) {
          const seg = shape[i];
          stick.tx1 = g.cx + seg[0] * g.scale;
          stick.ty1 = g.cy + seg[1] * g.scale;
          stick.tx2 = g.cx + seg[2] * g.scale;
          stick.ty2 = g.cy + seg[3] * g.scale;
          stick.targetOpacity = FORM_OPACITY;
          stick.dashed = false; // solid lines in formation
        } else {
          // Extra sticks orbit nearby
          const a = Math.random() * Math.PI * 2;
          const d = g.scale * rand(1.3, 2);
          const cx = g.cx + Math.cos(a) * d;
          const cy = g.cy + Math.sin(a) * d;
          const rot = Math.random() * Math.PI;
          const len = rand(12, 28);
          stick.tx1 = cx - Math.cos(rot) * len;
          stick.ty1 = cy - Math.sin(rot) * len;
          stick.tx2 = cx + Math.cos(rot) * len;
          stick.ty2 = cy + Math.sin(rot) * len;
          stick.targetOpacity = BASE_OPACITY * 0.6;
        }
      }
    }

    function dissolveFormation(g: Group) {
      for (const id of g.stickIds) {
        const stick = sticks[id];
        const mx = (stick.x1 + stick.x2) / 2;
        const my = (stick.y1 + stick.y2) / 2;
        const a = Math.random() * Math.PI * 2;
        const d = rand(80, 200);
        const cx = mx + Math.cos(a) * d;
        const cy = my + Math.sin(a) * d;
        const rot = Math.random() * Math.PI;
        const len = rand(18, 40);
        stick.tx1 = cx - Math.cos(rot) * len;
        stick.ty1 = cy - Math.sin(rot) * len;
        stick.tx2 = cx + Math.cos(rot) * len;
        stick.ty2 = cy + Math.sin(rot) * len;
        stick.targetOpacity = BASE_OPACITY;
        stick.vx = rand(-8, 8);
        stick.vy = rand(-8, 8);
        stick.dashed = Math.random() < 0.2;
      }
    }

    // ── Update ────────────────────────────────────────────
    function update(dt: number) {
      dt = Math.min(dt, 0.1);
      const t = Math.min(1, LERP_SPEED * dt);

      // Update group state machines
      for (const g of groups) {
        g.timer -= dt;
        if (g.timer <= 0) {
          switch (g.phase) {
            case "idle":
              g.phase = "forming";
              g.timer = g.formDur;
              g.shapeIdx = Math.floor(Math.random() * SHAPES.length);
              g.cx = rand(w * 0.1, w * 0.9);
              g.cy = rand(h * 0.1, h * 0.9);
              g.scale = rand(isMobile ? 30 : 45, isMobile ? 55 : 85);
              assignFormation(g);
              break;
            case "forming":
              g.phase = "holding";
              g.timer = g.holdDur;
              break;
            case "holding":
              g.phase = "dissolving";
              g.timer = g.dissolveDur;
              dissolveFormation(g);
              break;
            case "dissolving":
              g.phase = "idle";
              g.timer = rand(1, 3);
              break;
          }
        }
      }

      // Update sticks
      for (const stick of sticks) {
        if (stick.group === -1) {
          // Free-floating: drift
          stick.x1 += stick.vx * dt;
          stick.y1 += stick.vy * dt;
          stick.x2 += stick.vx * dt;
          stick.y2 += stick.vy * dt;
          stick.vx += rand(-1.5, 1.5) * dt;
          stick.vy += rand(-1.5, 1.5) * dt;
          stick.vx *= 0.998;
          stick.vy *= 0.998;

          // Wrap
          const cx = (stick.x1 + stick.x2) / 2;
          const cy = (stick.y1 + stick.y2) / 2;
          if (cx < -120) { stick.x1 += w + 240; stick.x2 += w + 240; }
          if (cx > w + 120) { stick.x1 -= w + 240; stick.x2 -= w + 240; }
          if (cy < -120) { stick.y1 += h + 240; stick.y2 += h + 240; }
          if (cy > h + 120) { stick.y1 -= h + 240; stick.y2 -= h + 240; }

          stick.opacity = lerp(stick.opacity, BASE_OPACITY, t * 0.3);
        } else {
          // Grouped: lerp to target
          stick.x1 = lerp(stick.x1, stick.tx1, t);
          stick.y1 = lerp(stick.y1, stick.ty1, t);
          stick.x2 = lerp(stick.x2, stick.tx2, t);
          stick.y2 = lerp(stick.y2, stick.ty2, t);
          stick.opacity = lerp(stick.opacity, stick.targetOpacity, t);
        }
      }
    }

    // ── Draw ──────────────────────────────────────────────
    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, w, h);

      // Faint dot grid (schematic paper feel)
      ctx.fillStyle = `rgba(${LINE_COLOR}, ${GRID_DOT_OPACITY})`;
      for (let gx = 0; gx < w; gx += GRID_SPACING) {
        for (let gy = 0; gy < h; gy += GRID_SPACING) {
          ctx.beginPath();
          ctx.arc(gx, gy, GRID_DOT_R, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Draw sticks
      for (const stick of sticks) {
        if (stick.opacity < 0.005) continue;

        ctx.beginPath();
        if (stick.dashed) {
          ctx.setLineDash([5, 4]);
        } else {
          ctx.setLineDash([]);
        }
        ctx.moveTo(stick.x1, stick.y1);
        ctx.lineTo(stick.x2, stick.y2);
        ctx.strokeStyle = `rgba(${LINE_COLOR}, ${stick.opacity})`;
        ctx.lineWidth = stick.group >= 0 && stick.opacity > BASE_OPACITY * 1.5 ? 1.4 : 1;
        ctx.stroke();

        // Endpoint dots
        ctx.setLineDash([]);
        const dotOp = stick.opacity * (stick.group >= 0 ? 1.4 : 0.8);
        const r = stick.group >= 0 && stick.opacity > BASE_OPACITY * 1.5 ? DOT_R : DOT_R * 0.6;

        ctx.beginPath();
        ctx.arc(stick.x1, stick.y1, r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${LINE_COLOR}, ${dotOp})`;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(stick.x2, stick.y2, r, 0, Math.PI * 2);
        ctx.fill();
      }

      // Small crosshairs at active formation centers
      for (const g of groups) {
        if (g.phase !== "forming" && g.phase !== "holding") continue;
        const progress = g.phase === "forming"
          ? 1 - g.timer / g.formDur
          : 1;
        const op = progress * 0.05;
        const sz = 5;

        ctx.beginPath();
        ctx.moveTo(g.cx - sz, g.cy);
        ctx.lineTo(g.cx + sz, g.cy);
        ctx.moveTo(g.cx, g.cy - sz);
        ctx.lineTo(g.cx, g.cy + sz);
        ctx.strokeStyle = `rgba(${LINE_COLOR}, ${op})`;
        ctx.lineWidth = 0.5;
        ctx.setLineDash([]);
        ctx.stroke();

        // Small right-angle marks at formation corners (schematic detail)
        const shape = SHAPES[g.shapeIdx];
        if (progress > 0.7) {
          const markOp = (progress - 0.7) / 0.3 * 0.06;
          const markSz = 4;
          for (const seg of shape) {
            // Mark at start of each segment
            const px = g.cx + seg[0] * g.scale;
            const py = g.cy + seg[1] * g.scale;
            ctx.beginPath();
            ctx.moveTo(px - markSz, py);
            ctx.lineTo(px, py);
            ctx.lineTo(px, py - markSz);
            ctx.strokeStyle = `rgba(${LINE_COLOR}, ${markOp})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
    }

    // ── Loop ──────────────────────────────────────────────
    function loop(time: number) {
      const dt = lastTime ? (time - lastTime) / 1000 : 0.016;
      lastTime = time;
      update(dt);
      draw();
      animId = requestAnimationFrame(loop);
    }

    resize();
    init();
    animId = requestAnimationFrame(loop);

    const onResize = () => { resize(); init(); };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    />
  );
}
