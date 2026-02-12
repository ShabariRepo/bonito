"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { SidebarProvider, useSidebar } from "@/components/layout/sidebar-context";
import { MobileTopBar } from "@/components/layout/mobile-topbar";
import { CommandBar } from "@/components/ai/command-bar";
import { ChatPanel } from "@/components/ai/chat-panel";
import { NotificationBell } from "@/components/layout/notification-bell";
import { useAuth } from "@/components/auth/auth-context";

function SidebarToggle() {
  const { isCollapsed, isMobile, toggle } = useSidebar();

  if (isMobile) return null;

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={toggle}
      className="fixed left-4 top-4 z-30 p-2 rounded-md bg-card border border-border hover:bg-accent text-muted-foreground hover:text-foreground transition-colors shadow-sm min-h-[44px] min-w-[44px] flex items-center justify-center"
      aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
    >
      {isCollapsed ? (
        <ChevronRight className="h-4 w-4" />
      ) : (
        <ChevronLeft className="h-4 w-4" />
      )}
    </motion.button>
  );
}

function DashboardContent({ children }: { children: React.ReactNode }) {
  const { isCollapsed, isMobile } = useSidebar();

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      
      <main className="flex-1 overflow-y-auto">
        <MobileTopBar />
        
        {/* Desktop notification bell */}
        <div className="hidden lg:flex justify-end px-4 md:px-8 pt-4">
          <NotificationBell />
        </div>
        
        {/* Main content with responsive padding */}
        <div className="p-4 md:p-8 pt-2">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {children}
          </motion.div>
        </div>
      </main>

      <SidebarToggle />
      <CommandBar />
      <ChatPanel />
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0a0a0a]">
        <div className="w-8 h-8 border-2 border-[#7c3aed] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <SidebarProvider>
      <DashboardContent>{children}</DashboardContent>
    </SidebarProvider>
  );
}