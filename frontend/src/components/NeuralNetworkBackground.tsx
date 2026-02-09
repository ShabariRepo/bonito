"use client";

import { useEffect, useRef } from "react";

interface Node {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  opacity: number;
  baseOpacity: number;
  pulseSpeed: number;
  pulsePhase: number;
}

export default function NeuralNetworkBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: -9999, y: -9999 });

  useEffect(() => {
    // Respect prefers-reduced-motion
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mql.matches) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const NODE_COUNT = 70;
    const CONNECTION_DIST = 180;
    const MOUSE_RADIUS = 200;
    const MOUSE_FORCE = 0.8;

    const nodes: Node[] = [];

    function resize() {
      if (!canvas) return;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
    }

    function initNodes() {
      nodes.length = 0;
      const w = canvas!.width;
      const h = canvas!.height;
      for (let i = 0; i < NODE_COUNT; i++) {
        const baseOpacity = 0.05 + Math.random() * 0.1;
        nodes.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.4 * dpr,
          vy: (Math.random() - 0.5) * 0.4 * dpr,
          radius: (2 + Math.random() * 2) * dpr,
          opacity: baseOpacity,
          baseOpacity,
          pulseSpeed: 0.005 + Math.random() * 0.015,
          pulsePhase: Math.random() * Math.PI * 2,
        });
      }
    }

    function animate() {
      if (!ctx || !canvas) return;
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const mx = mouseRef.current.x * dpr;
      const my = mouseRef.current.y * dpr;
      const mDist = MOUSE_RADIUS * dpr;
      const connDist = CONNECTION_DIST * dpr;

      // Update nodes
      for (const node of nodes) {
        // Mouse interaction
        const dx = node.x - mx;
        const dy = node.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < mDist && dist > 0) {
          const force = (1 - dist / mDist) * MOUSE_FORCE * dpr;
          node.vx += (dx / dist) * force * 0.05;
          node.vy += (dy / dist) * force * 0.05;
        }

        // Damping
        node.vx *= 0.99;
        node.vy *= 0.99;

        node.x += node.vx;
        node.y += node.vy;

        // Wrap
        if (node.x < -20) node.x = w + 20;
        if (node.x > w + 20) node.x = -20;
        if (node.y < -20) node.y = h + 20;
        if (node.y > h + 20) node.y = -20;

        // Pulse
        node.pulsePhase += node.pulseSpeed;
        node.opacity = node.baseOpacity + Math.sin(node.pulsePhase) * 0.06;
      }

      // Draw connections
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[i].x - nodes[j].x;
          const dy = nodes[i].y - nodes[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < connDist) {
            const alpha = (1 - dist / connDist) * 0.12;
            ctx.beginPath();
            ctx.moveTo(nodes[i].x, nodes[i].y);
            ctx.lineTo(nodes[j].x, nodes[j].y);
            ctx.strokeStyle = `rgba(245, 240, 232, ${alpha})`;
            ctx.lineWidth = 0.8 * dpr;
            ctx.stroke();
          }
        }
      }

      // Draw nodes
      for (const node of nodes) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(245, 240, 232, ${node.opacity})`;
        ctx.fill();
      }

      animId = requestAnimationFrame(animate);
    }

    function onMouseMove(e: MouseEvent) {
      mouseRef.current.x = e.clientX;
      mouseRef.current.y = e.clientY;
    }

    function onMouseLeave() {
      mouseRef.current.x = -9999;
      mouseRef.current.y = -9999;
    }

    resize();
    initNodes();
    animate();

    window.addEventListener("resize", () => {
      resize();
      initNodes();
    });
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseleave", onMouseLeave);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseleave", onMouseLeave);
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
