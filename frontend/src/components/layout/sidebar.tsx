"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  Box,
  Rocket,
  Settings,
  Cloud,
  Zap,
  DollarSign,
  Users,
  Shield,
  ScrollText,
  Sparkles,
  Radio,
  BarChart3,
  Bell,
  AlertTriangle,
} from "lucide-react";
import { cn, API_URL } from "@/lib/utils";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Models", href: "/models", icon: Box },
  { name: "Deployments", href: "/deployments", icon: Rocket },
  { name: "Providers", href: "/providers", icon: Cloud },
  { name: "Costs", href: "/costs", icon: DollarSign },
  { name: "Team", href: "/team", icon: Users },
  { name: "Governance", href: "/governance", icon: Shield },
  { name: "API Gateway", href: "/gateway", icon: Radio },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Audit", href: "/audit", icon: ScrollText },
  { name: "Notifications", href: "/notifications", icon: Bell },
  { name: "Alerts", href: "/alerts", icon: AlertTriangle },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [setupIncomplete, setSetupIncomplete] = useState(false);

  useEffect(() => {
    async function checkSetup() {
      try {
        const res = await fetch(`${API_URL}/api/providers/`);
        if (res.ok) {
          const providers = await res.json();
          setSetupIncomplete(providers.length === 0);
        }
      } catch {
        setSetupIncomplete(true);
      }
    }
    checkSetup();
  }, []);

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border bg-card">
      <div className="flex h-16 items-center gap-2 border-b border-border px-6">
        <motion.div
          animate={{ rotate: [0, 10, -10, 0] }}
          transition={{ duration: 2, repeat: Infinity, repeatDelay: 5 }}
        >
          <Zap className="h-6 w-6 text-violet-500" />
        </motion.div>
        <span className="text-xl font-bold tracking-tight">Bonito</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto">
        {/* Onboarding link */}
        <Link href="/onboarding" className="relative block mb-2">
          {(pathname === "/onboarding" || pathname?.startsWith("/onboarding/")) && (
            <motion.div
              layoutId="sidebar-active"
              className="absolute inset-0 rounded-md bg-accent"
              transition={{ type: "spring", stiffness: 350, damping: 30 }}
            />
          )}
          <span
            className={cn(
              "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
              pathname === "/onboarding" || pathname?.startsWith("/onboarding/")
                ? "text-accent-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Sparkles className="h-4 w-4" />
            Setup Wizard
            {setupIncomplete && (
              <span className="ml-auto flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-violet-400 opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-violet-500" />
              </span>
            )}
          </span>
        </Link>

        <div className="border-b border-border mb-2" />

        {navigation.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(item.href + "/");
          return (
            <Link key={item.name} href={item.href} className="relative block">
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-md bg-accent"
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              <span
                className={cn(
                  "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive ? "text-accent-foreground" : "text-muted-foreground hover:text-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.name}
              </span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border p-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold">
            B
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">Bonito Org</p>
            <p className="text-xs text-muted-foreground truncate">Enterprise</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
