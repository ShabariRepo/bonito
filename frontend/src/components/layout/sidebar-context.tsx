"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

interface SidebarContextType {
  isCollapsed: boolean;
  isMobile: boolean;
  isOpen: boolean;
  toggle: () => void;
  toggleCollapse: () => void;
  setOpen: (open: boolean) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error("useSidebar must be used within SidebarProvider");
  }
  return context;
}

export function SidebarProvider({ children }: { children: ReactNode }) {
  // Default to COLLAPSED so Studio (the post-auth landing) feels clean
  // out of the gate — Danny's feedback was that the expanded sidebar
  // is overload for first-time users. Power users can pin it open via
  // toggleCollapse(); state persists in localStorage.
  const [isCollapsed, setIsCollapsed] = useState(true);
  const [isOpen, setIsOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024); // lg breakpoint
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Load collapse state from localStorage (overrides the collapsed default
  // for users who explicitly pinned the sidebar open in a prior session)
  useEffect(() => {
    const saved = localStorage.getItem("sidebar-collapsed");
    if (saved !== null) {
      setIsCollapsed(JSON.parse(saved));
    }
  }, []);

  // Save collapse state to localStorage
  const toggleCollapse = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    localStorage.setItem("sidebar-collapsed", JSON.stringify(newState));
  };

  const toggle = () => {
    if (isMobile) {
      setIsOpen(!isOpen);
    } else {
      toggleCollapse();
    }
  };

  const setOpen = useCallback((open: boolean) => {
    setIsOpen(open);
  }, []);

  return (
    <SidebarContext.Provider
      value={{
        isCollapsed,
        isMobile,
        isOpen,
        toggle,
        toggleCollapse,
        setOpen,
      }}
    >
      {children}
    </SidebarContext.Provider>
  );
}