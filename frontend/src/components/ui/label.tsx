import { cn } from "@/lib/utils";

interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

export function Label({ className, ...props }: LabelProps) {
  return (
    <label
      className={cn(
        "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70",
        "text-gray-700 dark:text-gray-300",
        className
      )}
      {...props}
    />
  );
}