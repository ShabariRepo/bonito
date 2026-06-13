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
  GitPullRequest,
  BarChart3,
  Bell,
  AlertTriangle,
  Play,
  LogOut,
  Building2,
  UsersRound,
  Server,
  BookOpen,
  Bot,
  Package,
  FileText,
  UserPlus,
  Footprints,
  HeartPulse,
  Wand2,
  TrendingUp,
  MessageSquare,
  ChevronDown,
  ChevronRight as ChevronCollapsed,
} from "lucide-react";
import { cn, API_URL } from "@/lib/utils";
import { useSidebar } from "./sidebar-context";
import { useAuth } from "@/components/auth/auth-context";

// Top-level (always visible, no section header).
// Studio is the chat-first front door (the post-auth landing); Dashboard
// is the legacy metrics view that pre-Studio users may still want to hit.
// See docs/BONITO-STUDIO-PLAN.md for the planned 7-item domain grouping
// that consolidates the sections below.
const topNavigation = [
  { name: "Studio", href: "/studio", icon: MessageSquare },
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
];

// Tier hierarchy for comparison
const TIER_RANK: Record<string, number> = { free: 0, starter: 1, pro: 2, enterprise: 3, scale: 4 };

// Domain-grouped navigation — 6 sections that preserve every existing
// route, just rolled up by what the user is actually trying to do.
// See docs/BONITO-STUDIO-PLAN.md for the rationale (Danny feedback:
// the un-grouped sidebar is too crowded for first-time users).

// Agents — everything for designing + operating agent systems.
const agentsNavigation = [
  { name: "Origami", href: "/origami/workspace", icon: Wand2, badge: "NEW" as const },
  { name: "Projects", href: "/agents", icon: Bot },
  { name: "Breadcrumbs", href: "/agents/breadcrumbs", icon: Footprints },
  { name: "BonBon", href: "/agents/bonbon", icon: Package },
];

// Knowledge — RAG / KB management.
const knowledgeNavigation = [
  { name: "Knowledge Base", href: "/knowledge-base", icon: BookOpen, requiredTier: "pro" as const },
];

// Gateway — proxy, routing, costs, observability of LLM traffic.
const gatewayNavigation = [
  { name: "API Gateway", href: "/gateway", icon: Radio },
  { name: "Models", href: "/models", icon: Box },
  { name: "Routing Policies", href: "/routing-policies", icon: GitBranch },
  { name: "Playground", href: "/playground", icon: Play },
  { name: "Costs", href: "/costs", icon: DollarSign },
  { name: "Analytics", href: "/analytics", icon: BarChart3, requiredTier: "pro" as const },
  { name: "Logs", href: "/logs", icon: FileText },
  { name: "Code Review", href: "/code-review", icon: GitPullRequest },
];

// Integrations — provider connections + deployment targets.
const integrationsNavigation = [
  { name: "Providers", href: "/providers", icon: Cloud },
  { name: "Deployments", href: "/deployments", icon: Rocket },
];

// Team — members, access control, audit, compliance.
const teamNavigation = [
  { name: "Team", href: "/team", icon: Users },
  { name: "Audit", href: "/audit", icon: ScrollText, requiredTier: "pro" as const },
  { name: "Governance", href: "/governance", icon: Shield, requiredTier: "enterprise" as const },
];

// Settings — plan, billing, notifications.
const settingsNavigation = [
  { name: "Settings", href: "/settings", icon: Settings },
  { name: "Notifications", href: "/notifications", icon: Bell, requiredTier: "pro" as const },
  { name: "Alerts", href: "/alerts", icon: AlertTriangle, requiredTier: "pro" as const },
];

// Shared between every section's render. Lives at module level so the
// NavSection helper below can use it.
const contentVariants = {
  expanded: { opacity: 1, x: 0 },
  collapsed: { opacity: 0, x: -20 },
};

type NavItem = {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  requiredTier?: "pro" | "enterprise";
  badge?: string;
};

/** Renders one labeled (or unlabeled) sidebar section with the lock /
 *  badge / active-state logic the old code repeated inline 5 times.
 *  Each labeled section is independently collapsible — the label is a
 *  toggle button, state persists to localStorage, and item rendering
 *  is suppressed while the section is collapsed. Items are always
 *  shown in icon-only sidebar mode (no labels to gate against).  */
function NavSection({
  label,
  items,
  pathname,
  isCollapsed,
  isMobile,
  isFeatureLocked,
  defaultCollapsed = true,
}: {
  label?: string;
  items: ReadonlyArray<NavItem>;
  pathname: string | null;
  isCollapsed: boolean;
  isMobile: boolean;
  isFeatureLocked: (tier?: string) => boolean;
  defaultCollapsed?: boolean;
}) {
  const storageKey = label
    ? `bonito:sidebar:section:${label.toLowerCase()}`
    : null;
  const [sectionCollapsed, setSectionCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined" || !storageKey) return defaultCollapsed;
    const saved = window.localStorage.getItem(storageKey);
    if (saved === null) return defaultCollapsed;
    return saved === "true";
  });

  const sidebarShowsLabels = !isCollapsed || isMobile;
  // In icon-only sidebar mode there's no per-section label to click,
  // so per-section collapse is meaningless — always render items.
  const showItems = !label || !sidebarShowsLabels || !sectionCollapsed;

  function toggleSection() {
    setSectionCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined" && storageKey) {
        window.localStorage.setItem(storageKey, String(next));
      }
      return next;
    });
  }

  return (
    <>
      {label !== undefined && (
        <>
          <div className="border-b border-border my-2" />
          <AnimatePresence>
            {sidebarShowsLabels && (
              <motion.button
                key={`section-${label}`}
                onClick={toggleSection}
                variants={contentVariants}
                initial="collapsed"
                animate="expanded"
                exit="collapsed"
                transition={{ duration: 0.2 }}
                className="w-full px-3 py-1 flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-muted-foreground/60 hover:text-foreground transition-colors group"
                aria-expanded={!sectionCollapsed}
                aria-label={
                  sectionCollapsed
                    ? `Expand ${label} section`
                    : `Collapse ${label} section`
                }
              >
                <span>{label}</span>
                {sectionCollapsed ? (
                  <ChevronCollapsed
                    className="h-3 w-3 opacity-60 group-hover:opacity-100 transition-opacity"
                  />
                ) : (
                  <ChevronDown
                    className="h-3 w-3 opacity-60 group-hover:opacity-100 transition-opacity"
                  />
                )}
              </motion.button>
            )}
          </AnimatePresence>
        </>
      )}
      {showItems && items.map((item) => {
        const matchesPath =
          pathname === item.href || pathname?.startsWith(item.href + "/");
        const hasMoreSpecificMatch = items.some(
          (other) =>
            other.href !== item.href &&
            other.href.startsWith(item.href + "/") &&
            (pathname === other.href ||
              pathname?.startsWith(other.href + "/")),
        );
        const isActive = matchesPath && !hasMoreSpecificMatch;
        const locked = isFeatureLocked(item.requiredTier);

        return (
          <Link
            key={item.name}
            href={locked ? "/settings" : item.href}
            className="relative block"
            title={
              locked
                ? `Requires ${item.requiredTier === "pro" ? "Pro" : "Enterprise"} plan`
                : undefined
            }
          >
            {isActive && !locked && (
              <motion.div
                layoutId="sidebar-active"
                className="absolute inset-0 rounded-md bg-accent"
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
              />
            )}
            <div
              className={cn(
                "relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors min-h-[44px]",
                locked
                  ? "text-muted-foreground/40 cursor-not-allowed"
                  : isActive
                    ? "text-accent-foreground"
                    : "text-muted-foreground hover:text-foreground",
                isCollapsed && !isMobile && "justify-center",
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
                    className="flex items-center justify-between flex-1"
                  >
                    {item.name}
                    {locked && (
                      <span
                        className={cn(
                          "ml-auto text-[10px] font-semibold px-1.5 py-0.5 rounded-full",
                          item.requiredTier === "pro"
                            ? "bg-violet-500/10 text-violet-400"
                            : "bg-amber-500/10 text-amber-400",
                        )}
                      >
                        {item.requiredTier === "pro" ? "Pro" : "Ent"}
                      </span>
                    )}
                    {!locked && item.badge && (
                      <span className="ml-auto text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400">
                        {item.badge}
                      </span>
                    )}
                  </motion.span>
                )}
              </AnimatePresence>
            </div>
          </Link>
        );
      })}
    </>
  );
}

const adminNavigation = [
  { name: "Organizations", href: "/admin/organizations", icon: Building2 },
  { name: "All Users", href: "/admin/users", icon: UsersRound },
  { name: "Access Requests", href: "/admin/access-requests", icon: UserPlus },
  { name: "Agent Health", href: "/admin/agent-health", icon: HeartPulse },
  { name: "Tier Utilization", href: "/admin/tier-utilization", icon: TrendingUp },
  { name: "Origami Metrics", href: "/admin/origami-metrics", icon: Wand2 },
  { name: "Studio Billing", href: "/admin/studio-billing", icon: DollarSign },
  { name: "Discover Logs", href: "/admin/discover-logs", icon: Sparkles },
  { name: "System", href: "/admin/system", icon: Server },
  { name: "Knowledge Base", href: "/admin/kb", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { isCollapsed, isMobile, isOpen, setOpen } = useSidebar();
  const { user, logout } = useAuth();
  const [setupIncomplete, setSetupIncomplete] = useState(false);

  const userTier = user?.subscription_tier || "free";

  const isFeatureLocked = (requiredTier?: string) => {
    if (!requiredTier) return false;
    return (TIER_RANK[userTier] ?? 0) < (TIER_RANK[requiredTier] ?? 0);
  };

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
  // `contentVariants` is now module-level so NavSection can use it too.

  const SidebarContent = () => (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex h-16 items-center border-b border-border px-4 shrink-0">
        <Link href="/studio" className="flex items-center gap-2.5">
          <Image src="/bonito-icon.png" alt="Bonito" width={36} height={18} className="shrink-0" priority />
          <AnimatePresence>
            {(!isCollapsed || isMobile) && (
              <motion.span
                key="brand-text"
                variants={contentVariants}
                initial="collapsed"
                animate="expanded"
                exit="collapsed"
                transition={{ duration: 0.2 }}
                className="text-lg font-bold text-white"
              >
                Bonito
              </motion.span>
            )}
          </AnimatePresence>
        </Link>
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

        {/* Dashboard */}
        {topNavigation.map((item) => {
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

        {/* Domain-grouped sections — 6 buckets that cover all 23+ pages
            without overwhelming first-time users. Lock/badge handling is
            in NavSection (see top of file). Each section header is a
            toggle button — Agents stays expanded by default so the
            most-used surface is one click away; the others collapse on
            first paint and the user's preference persists per section. */}
        <NavSection
          label="Agents"
          items={agentsNavigation}
          pathname={pathname}
          isCollapsed={isCollapsed}
          isMobile={isMobile}
          isFeatureLocked={isFeatureLocked}
          defaultCollapsed={false}
        />
        <NavSection
          label="Knowledge"
          items={knowledgeNavigation}
          pathname={pathname}
          isCollapsed={isCollapsed}
          isMobile={isMobile}
          isFeatureLocked={isFeatureLocked}
        />
        <NavSection
          label="Gateway"
          items={gatewayNavigation}
          pathname={pathname}
          isCollapsed={isCollapsed}
          isMobile={isMobile}
          isFeatureLocked={isFeatureLocked}
        />
        <NavSection
          label="Integrations"
          items={integrationsNavigation}
          pathname={pathname}
          isCollapsed={isCollapsed}
          isMobile={isMobile}
          isFeatureLocked={isFeatureLocked}
        />
        <NavSection
          label="Team"
          items={teamNavigation}
          pathname={pathname}
          isCollapsed={isCollapsed}
          isMobile={isMobile}
          isFeatureLocked={isFeatureLocked}
        />
        <NavSection
          label="Settings"
          items={settingsNavigation}
          pathname={pathname}
          isCollapsed={isCollapsed}
          isMobile={isMobile}
          isFeatureLocked={isFeatureLocked}
        />

        {/* Platform admin section — only visible to platform superadmins */}
        {user?.is_platform_admin && (
          <NavSection
            label="Platform"
            items={adminNavigation}
            pathname={pathname}
            isCollapsed={isCollapsed}
            isMobile={isMobile}
            isFeatureLocked={isFeatureLocked}
          />
        )}
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