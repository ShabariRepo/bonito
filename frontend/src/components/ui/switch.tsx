"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SwitchProps {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  id?: string;
  size?: "default" | "sm" | "lg";
}

const Switch = React.forwardRef<HTMLButtonElement, SwitchProps>(
  ({ className, checked = false, onCheckedChange, disabled, size = "default", ...props }, ref) => {
    const sizes = {
      sm: { track: "h-4 w-7", thumb: "h-3 w-3", translate: "translate-x-3" },
      default: { track: "h-5 w-9", thumb: "h-4 w-4", translate: "translate-x-4" },
      lg: { track: "h-6 w-11", thumb: "h-5 w-5", translate: "translate-x-5" },
    };
    const s = sizes[size];
    return (
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={() => onCheckedChange?.(!checked)}
        className={cn(
          "peer inline-flex shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
          s.track,
          checked ? "bg-violet-600" : "bg-accent",
          className
        )}
        ref={ref}
        {...props}
      >
        <span
          className={cn(
            "pointer-events-none block rounded-full bg-white shadow-lg ring-0 transition-transform",
            s.thumb,
            checked ? s.translate : "translate-x-0"
          )}
        />
      </button>
    );
  }
);
Switch.displayName = "Switch";

export { Switch };
