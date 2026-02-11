import { useToast as useToastBase } from "@/components/ui/toast";

/**
 * Wrapper around useToast that accepts both:
 * - toast("message", "error")                          — original API
 * - toast({ title, description, variant })             — shadcn-style API
 */
export function useToast() {
  const { toast: baseToast } = useToastBase();

  function toast(input: string | { title?: string; description?: string; variant?: string }, type?: "success" | "error" | "info") {
    if (typeof input === "string") {
      baseToast(input, type);
    } else {
      const msg = [input.title, input.description].filter(Boolean).join(": ");
      const toastType = input.variant === "destructive" ? "error" : input.variant === "success" ? "success" : "info";
      baseToast(msg, toastType as any);
    }
  }

  return { toast };
}
