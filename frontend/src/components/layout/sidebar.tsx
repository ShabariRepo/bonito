"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import {
  LayoutDashboard,
  Box,
  Rocket,
  Settings,
  Cloud,
  DollarSign,
  Users,
  Shield,
  ScrollText,
  Sparkles,
  Radio,
  GitBranch,
  BarChart3,
  Bell,
  AlertTriangle,
  Play,
  LogOut,
} from "lucide-react";
import { cn, API_URL } from "@/lib/utils";
import { useSidebar } from "./sidebar-context";
import { useAuth } from "@/components/auth/auth-context";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Models", href: "/models", icon: Box },
  { name: "Playground", href: "/playground", icon: Play },
  { name: "Deployments", href: "/deployments", icon: Rocket },
  { name: "Providers", href: "/providers", icon: Cloud },
  { name: "Costs", href: "/costs", icon: DollarSign },
  { name: "Team", href: "/team", icon: Users },
  { name: "Governance", href: "/governance", icon: Shield },
  { name: "API Gateway", href: "/gateway", icon: Radio },
  { name: "Routing Policies", href: "/routing-policies", icon: GitBranch },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Audit", href: "/audit", icon: ScrollText },
  { name: "Notifications", href: "/notifications", icon: Bell },
  { name: "Alerts", href: "/alerts", icon: AlertTriangle },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { isCollapsed, isMobile, isOpen, setOpen } = useSidebar();
  const { user, logout } = useAuth();
  const [setupIncomplete, setSetupIncomplete] = useState(false);

  const handleLogout = async () => {
    await logout();
    router.push("/login");
  };

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

  // Close mobile sidebar when route changes
  useEffect(() => {
    if (isMobile) {
      setOpen(false);
    }
  }, [pathname, isMobile, setOpen]);

  const sidebarVariants = {
    expanded: { width: 256 },
    collapsed: { width: 64 },
  };

  const contentVariants = {
    expanded: { opacity: 1, x: 0 },
    collapsed: { opacity: 0, x: -20 },
  };

  const SidebarContent = () => (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex h-16 items-center border-b border-border px-4 shrink-0">
        <AnimatePresence mode="wait">
          {(!isCollapsed || isMobile) ? (
            <motion.div
              key="full"
              variants={contentVariants}
              initial="collapsed"
              animate="expanded"
              exit="collapsed"
              transition={{ duration: 0.2 }}
            >
              <Image src="/logo-text-dark.png" alt="Bonito" width={120} height={40} className="shrink-0" priority />
            </motion.div>
          ) : (
            <motion.div
              key="icon"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="mx-auto"
            >
              <Image src="/logo.png" alt="Bonito" width={32} height={21} className="shrink-0" priority />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
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
          <div
            className={cn(
              "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors min-h-[44px]",
              pathname === "/onboarding" || pathname?.startsWith("/onboarding/")
                ? "text-accent-foreground"
                : "text-muted-foreground hover:text-foreground",
              isCollapsed && !isMobile && "justify-center"
            )}
          >
            <Sparkles className="h-4 w-4 shrink-0" />
            <AnimatePresence>
              {(!isCollapsed || isMobile) && (
                <motion.span
                  variants={contentVariants}
                  initial="collapsed"
                  animate="expanded"
                  exit="collapsed"
                  transition={{ duration: 0.2 }}
                  className="flex items-center justify-between flex-1"
                >
                  Setup Wizard
                  {setupIncomplete && (
                    <span className="flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-violet-400 opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-violet-500" />
                    </span>
                  )}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
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
              <div
                className={cn(
                  "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors min-h-[44px]",
                  isActive ? "text-accent-foreground" : "text-muted-foreground hover:text-foreground",
                  isCollapsed && !isMobile && "justify-center"
                )}
              >
                <item.icon className="h-4 w-4 shrink-0" />
                <AnimatePresence>
                  {(!isCollapsed || isMobile) && (
                    <motion.span
                      variants={contentVariants}
                      initial="collapsed"
                      animate="expanded"
                      exit="collapsed"
                      transition={{ duration: 0.2 }}
                    >
                      {item.name}
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-border p-4 shrink-0">
        <div className={cn("flex items-center gap-3", isCollapsed && !isMobile && "justify-center")}>
          <div className="h-8 w-8 rounded-full bg-violet-600 flex items-center justify-center text-xs font-bold shrink-0">
            {user?.name?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || "B"}
          </div>
          <AnimatePresence>
            {(!isCollapsed || isMobile) && (
              <motion.div
                variants={contentVariants}
                initial="collapsed"
                animate="expanded"
                exit="collapsed"
                transition={{ duration: 0.2 }}
                className="flex-1 min-w-0"
              >
                <p className="text-sm font-medium truncate">{user?.name || "User"}</p>
                <p className="text-xs text-muted-foreground truncate">{user?.email || ""}</p>
              </motion.div>
            )}
          </AnimatePresence>
          <AnimatePresence>
            {(!isCollapsed || isMobile) && (
              <motion.button
                variants={contentVariants}
                initial="collapsed"
                animate="expanded"
                exit="collapsed"
                transition={{ duration: 0.2 }}
                onClick={handleLogout}
                className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors min-h-[36px] min-w-[36px] flex items-center justify-center"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
              </motion.button>
            )}
          </AnimatePresence>
        </div>
        {isCollapsed && !isMobile && (
          <button
            onClick={handleLogout}
            className="mt-2 w-full p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors flex items-center justify-center"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );

  if (isMobile) {
    // Render mobile sidebar via portal to avoid overflow-hidden clipping on iOS
    if (typeof document === "undefined") return null;
    return createPortal(
      <AnimatePresence>
        {isOpen && (
          <div key="mobile-sidebar-overlay">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
              onClick={() => setOpen(false)}
            />

            {/* Mobile Sidebar */}
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className="fixed left-0 top-0 z-50 h-full w-64 border-r border-border bg-card shadow-2xl lg:hidden"
            >
              <SidebarContent />
            </motion.aside>
          </div>
        )}
      </AnimatePresence>,
      document.body,
    );
  }

  // Desktop sidebar
  return (
    <motion.aside
      variants={sidebarVariants}
      animate={isCollapsed ? "collapsed" : "expanded"}
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className="hidden lg:flex h-screen flex-col border-r border-border bg-card"
    >
      <SidebarContent />
    </motion.aside>
  );
}