"use client";

import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface Step {
  title: string;
  description?: string;
}

interface StepWizardProps {
  steps: Step[];
  currentStep: number;
  children: React.ReactNode;
}

export function StepWizard({ steps, currentStep, children }: StepWizardProps) {
  return (
    <div className="space-y-8">
      {/* Step indicators */}
      <div className="flex items-center justify-center gap-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="flex items-center gap-2">
              <motion.div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full text-xs font-bold transition-colors",
                  i < currentStep && "bg-violet-600 text-white",
                  i === currentStep && "bg-violet-600 text-white ring-4 ring-violet-600/20",
                  i > currentStep && "bg-accent text-muted-foreground"
                )}
                animate={i === currentStep ? { scale: [1, 1.05, 1] } : {}}
                transition={{ duration: 2, repeat: Infinity }}
              >
                {i < currentStep ? <Check className="h-4 w-4" /> : i + 1}
              </motion.div>
              <span className={cn(
                "text-sm font-medium hidden sm:inline",
                i === currentStep ? "text-foreground" : "text-muted-foreground"
              )}>
                {step.title}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={cn(
                "h-px w-8 sm:w-12",
                i < currentStep ? "bg-violet-600" : "bg-border"
              )} />
            )}
          </div>
        ))}
      </div>

      {/* Step content with animation */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentStep}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.25 }}
        >
          {children}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
