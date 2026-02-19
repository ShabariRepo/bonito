"use client";

import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface ScrollAreaProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function ScrollArea({ children, className, style, ...props }: ScrollAreaProps) {
  return (
    <div
      className={cn(
        "overflow-auto scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-gray-100 dark:scrollbar-thumb-gray-600 dark:scrollbar-track-gray-800",
        className
      )}
      style={style}
      {...props}
    >
      {children}
    </div>
  );
}