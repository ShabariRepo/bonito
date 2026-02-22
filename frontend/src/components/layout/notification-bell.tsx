"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Bell, DollarSign, Shield, AlertTriangle, BookOpen, Rocket, Zap } from "lucide-react";
import { apiRequest } from "@/lib/auth";
import { getAccessToken } from "@/lib/auth";

const TYPE_ICONS: Record<string, any> = {
  cost_alert: DollarSign,
  compliance_alert: Shield,
  model_deprecation: AlertTriangle,
  deployment_alert: Rocket,
  gateway_alert: Zap,
  digest: BookOpen,
};

export function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function load() {
      // Don't poll if not authenticated — avoids 403 spam on the backend
      if (!getAccessToken()) return;
      try {
        const [countRes, listRes] = await Promise.all([
          apiRequest("/api/notifications/unread-count"),
          apiRequest("/api/notifications/"),
        ]);
        if (!countRes.ok || !listRes.ok) return;
        const countData = await countRes.json();
        const listData = await listRes.json();
        setUnreadCount(countData.count);
        setNotifications(listData.items?.slice(0, 5) || []);
      } catch {}
    }
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <motion.span
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute -top-0.5 -right-0.5 h-4 w-4 rounded-full bg-violet-600 text-[10px] font-bold text-white flex items-center justify-center"
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </motion.span>
        )}
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-80 rounded-lg border border-border bg-card shadow-lg z-50"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <span className="text-sm font-semibold">Notifications</span>
              {unreadCount > 0 && (
                <span className="text-xs text-violet-500 font-medium">{unreadCount} unread</span>
              )}
            </div>

            <div className="max-h-80 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                  No notifications
                </div>
              ) : (
                notifications.map((n) => {
                  const Icon = TYPE_ICONS[n.type] || Bell;
                  return (
                    <div
                      key={n.id}
                      className={`px-4 py-3 border-b border-border last:border-0 hover:bg-accent/50 transition-colors ${
                        !n.read ? "bg-violet-500/5" : ""
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <Icon className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                        <div className="min-w-0">
                          <p className={`text-xs font-medium truncate ${!n.read ? "text-foreground" : "text-muted-foreground"}`}>
                            {n.title}
                          </p>
                          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{n.body}</p>
                        </div>
                        {!n.read && <span className="h-2 w-2 rounded-full bg-violet-500 flex-shrink-0 mt-1" />}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <Link
              href="/notifications"
              onClick={() => setOpen(false)}
              className="block px-4 py-3 text-center text-xs font-medium text-violet-500 hover:text-violet-400 border-t border-border transition-colors"
            >
              View all notifications
            </Link>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
