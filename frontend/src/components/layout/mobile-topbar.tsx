"use client";

import { motion } from "framer-motion";
import { Menu, Zap } from "lucide-react";
import { useSidebar } from "./sidebar-context";
import { NotificationBell } from "./notification-bell";

export function MobileTopBar() {
  const { isMobile, toggle } = useSidebar();

  if (!isMobile) return null;

  return (
    <div className="lg:hidden sticky top-0 z-30 flex h-16 items-center justify-between bg-card border-b border-border px-4">
      {/* Left: Hamburger + Branding */}
      <div className="flex items-center gap-3">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={toggle}
          className="p-2 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Open sidebar"
        >
          <Menu className="h-5 w-5" />
        </motion.button>
        
        <div className="flex items-center gap-2">
          <motion.div
            animate={{ rotate: [0, 10, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity, repeatDelay: 5 }}
          >
            <Zap className="h-6 w-6 text-violet-500" />
          </motion.div>
          <span className="text-xl font-bold tracking-tight">Bonito</span>
        </div>
      </div>

      {/* Right: Notification Bell */}
      <NotificationBell />
    </div>
  );
}