"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingDots } from "@/components/ui/loading-dots";
import {
  Bell,
  DollarSign,
  Shield,
  AlertTriangle,
  BookOpen,
  Check,
  Filter,
} from "lucide-react";
import { apiRequest } from "@/lib/auth";

const TYPE_CONFIG: Record<string, { icon: any; color: string; label: string }> = {
  cost_alert: { icon: DollarSign, color: "text-amber-500", label: "Cost Alert" },
  compliance_alert: { icon: Shield, color: "text-red-400", label: "Compliance" },
  model_deprecation: { icon: AlertTriangle, color: "text-orange-500", label: "Model Update" },
  digest: { icon: BookOpen, color: "text-blue-500", label: "Digest" },
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filter, setFilter] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [featureGated, setFeatureGated] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const url = filter
        ? `/api/notifications/?type=${filter}`
        : `/api/notifications/`;
      const res = await apiRequest(url);
      if (res.status === 403) {
        setFeatureGated(true);
        return;
      }
      const data = await res.json();
      setNotifications(data.items);
      setTotal(data.total);
      setUnreadCount(data.unread_count);
    } catch (e) {
      console.error("Failed to load notifications", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filter]);

  async function markRead(id: string) {
    try {
      await apiRequest(`/api/notifications/${id}/read`, { method: "PUT" });
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
    } catch (e) {
      console.error("Failed to mark as read", e);
    }
  }

  const filters = [
    { value: null, label: "All" },
    { value: "cost_alert", label: "Cost Alerts" },
    { value: "compliance_alert", label: "Compliance" },
    { value: "model_deprecation", label: "Model Updates" },
    { value: "digest", label: "Digests" },
  ];

  if (featureGated) {
    return (
      <div className="space-y-8">
        <PageHeader
          title="Notifications"
          description="Stay informed about cost alerts, compliance changes, and model updates"
        />
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="p-4 rounded-full bg-violet-500/10 mb-4">
            <Bell className="h-8 w-8 text-violet-500" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Notifications require a Pro plan</h3>
          <p className="text-sm text-muted-foreground max-w-md mb-6">
            Get real-time cost alerts, compliance notifications, model deprecation warnings, and usage digests with a Pro or Enterprise plan.
          </p>
          <a
            href="/pricing"
            className="px-6 py-2.5 rounded-lg bg-violet-600 text-white text-sm font-medium hover:bg-violet-700 transition-colors"
          >
            View Plans
          </a>
        </div>
      </div>
    );
  }

  if (loading) {
    return <div className="flex items-center justify-center h-96"><LoadingDots size="lg" /></div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Notifications"
        description={`${unreadCount} unread notification${unreadCount !== 1 ? "s" : ""}`}
      />

      {/* Filters */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        {filters.map((f) => (
          <button
            key={f.label}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full transition-colors ${
              filter === f.value
                ? "bg-violet-600 text-white"
                : "bg-accent text-muted-foreground hover:text-foreground"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Notification list */}
      <div className="space-y-3">
        <AnimatePresence>
          {notifications.map((n, i) => {
            const config = TYPE_CONFIG[n.type] || TYPE_CONFIG.digest;
            const Icon = config.icon;
            return (
              <motion.div
                key={n.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ delay: i * 0.05 }}
              >
                <Card className={`transition-colors ${!n.read ? "border-violet-500/40 bg-violet-500/5" : ""}`}>
                  <CardContent className="flex items-start gap-4 py-4">
                    <div className={`mt-0.5 p-2 rounded-lg bg-accent/50 ${config.color}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className={`text-sm font-medium ${!n.read ? "text-foreground" : "text-muted-foreground"}`}>
                          {n.title}
                        </h3>
                        <Badge variant={n.read ? "secondary" : "default"} className="text-[10px]">
                          {config.label}
                        </Badge>
                        {!n.read && (
                          <span className="h-2 w-2 rounded-full bg-violet-500 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">{n.body}</p>
                      <p className="text-xs text-muted-foreground mt-2">
                        {new Date(n.created_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          hour: "numeric",
                          minute: "2-digit",
                        })}
                      </p>
                    </div>
                    {!n.read && (
                      <motion.button
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={() => markRead(n.id)}
                        className="p-2 rounded-lg hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                        title="Mark as read"
                      >
                        <Check className="h-4 w-4" />
                      </motion.button>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {notifications.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <Bell className="h-8 w-8 mx-auto mb-3 opacity-50" />
            <p>No notifications</p>
          </div>
        )}
      </div>
    </div>
  );
}
