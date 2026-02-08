"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Status = "connected" | "active" | "error" | "pending" | "disconnected";

const config: Record<Status, { bg: string; dot: string; text: string; label: string }> = {
  connected: { bg: "bg-emerald-500/10", dot: "bg-emerald-500", text: "text-emerald-500", label: "Connected" },
  active: { bg: "bg-emerald-500/10", dot: "bg-emerald-500", text: "text-emerald-500", label: "Active" },
  error: { bg: "bg-red-500/10", dot: "bg-red-500", text: "text-red-500", label: "Error" },
  pending: { bg: "bg-amber-500/10", dot: "bg-amber-500", text: "text-amber-500", label: "Pending" },
  disconnected: { bg: "bg-zinc-500/10", dot: "bg-zinc-500", text: "text-zinc-500", label: "Disconnected" },
};

export function StatusBadge({ status, label }: { status: Status; label?: string }) {
  const c = config[status] || config.disconnected;
  return (
    <span className={cn("inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium", c.bg, c.text)}>
      <span className="relative flex h-2 w-2">
        {(status === "connected" || status === "active") && (
          <motion.span
            className={cn("absolute inline-flex h-full w-full rounded-full opacity-75", c.dot)}
            animate={{ scale: [1, 1.8, 1], opacity: [0.75, 0, 0.75] }}
            transition={{ duration: 2, repeat: Infinity }}
          />
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", c.dot)} />
      </span>
      {label || c.label}
    </span>
  );
}
