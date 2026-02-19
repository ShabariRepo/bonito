"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface SheetContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const SheetContext = createContext<SheetContextValue>({
  open: false,
  setOpen: () => {},
});

interface SheetProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: ReactNode;
}

export function Sheet({ open: controlledOpen, onOpenChange, children }: SheetProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setOpen = onOpenChange || setInternalOpen;

  return (
    <SheetContext.Provider value={{ open, setOpen }}>
      {children}
    </SheetContext.Provider>
  );
}

export function SheetTrigger({ children, asChild }: { children: ReactNode; asChild?: boolean }) {
  const { setOpen } = useContext(SheetContext);
  
  if (asChild && typeof children === "object" && children !== null && "props" in children) {
    return {
      ...children,
      props: {
        ...children.props,
        onClick: () => setOpen(true),
      },
    } as ReactNode;
  }
  
  return (
    <button onClick={() => setOpen(true)}>
      {children}
    </button>
  );
}

interface SheetContentProps {
  children: ReactNode;
  className?: string;
  side?: "left" | "right" | "top" | "bottom";
  onClose?: () => void;
}

export function SheetContent({ 
  children, 
  className,
  side = "right",
  onClose 
}: SheetContentProps) {
  const { open, setOpen } = useContext(SheetContext);

  const handleClose = () => {
    setOpen(false);
    onClose?.();
  };

  const slideVariants = {
    left: { x: "-100%" },
    right: { x: "100%" },
    top: { y: "-100%" },
    bottom: { y: "100%" }
  };

  const sizeClasses = {
    left: "left-0 top-0 h-full",
    right: "right-0 top-0 h-full",
    top: "top-0 left-0 w-full",
    bottom: "bottom-0 left-0 w-full"
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80"
            onClick={handleClose}
          />
          
          {/* Sheet */}
          <motion.div
            initial={slideVariants[side]}
            animate={{ x: 0, y: 0 }}
            exit={slideVariants[side]}
            transition={{ type: "spring", damping: 30, stiffness: 300 }}
            className={cn(
              "fixed z-50 bg-white dark:bg-[#1a1a2e] border border-gray-200 dark:border-gray-800 shadow-lg",
              sizeClasses[side],
              side === "left" || side === "right" ? "w-96" : "h-96",
              className
            )}
          >
            {children}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export function SheetHeader({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("p-6 pb-4 border-b border-gray-200 dark:border-gray-800", className)}>
      {children}
    </div>
  );
}

export function SheetTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <h2 className={cn("text-lg font-semibold text-gray-900 dark:text-white", className)}>
      {children}
    </h2>
  );
}

export function SheetDescription({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn("text-sm text-gray-600 dark:text-gray-400 mt-1", className)}>
      {children}
    </p>
  );
}