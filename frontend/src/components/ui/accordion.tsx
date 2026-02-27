"use client"

import * as React from "react"

// Lightweight accordion without radix dependency

interface AccordionContextType {
  value: string | null;
  onToggle: (value: string) => void;
}

const AccordionContext = React.createContext<AccordionContextType>({
  value: null,
  onToggle: () => {},
});

interface AccordionProps {
  type?: "single" | "multiple";
  collapsible?: boolean;
  className?: string;
  children: React.ReactNode;
}

function Accordion({ className, children }: AccordionProps) {
  const [value, setValue] = React.useState<string | null>(null);

  const onToggle = React.useCallback((itemValue: string) => {
    setValue((prev) => (prev === itemValue ? null : itemValue));
  }, []);

  return (
    <AccordionContext.Provider value={{ value, onToggle }}>
      <div className={className}>{children}</div>
    </AccordionContext.Provider>
  );
}

interface AccordionItemContextType {
  value: string;
  isOpen: boolean;
}

const AccordionItemContext = React.createContext<AccordionItemContextType>({
  value: "",
  isOpen: false,
});

interface AccordionItemProps {
  value: string;
  className?: string;
  children: React.ReactNode;
}

function AccordionItem({ value, className, children }: AccordionItemProps) {
  const { value: openValue } = React.useContext(AccordionContext);
  const isOpen = openValue === value;

  return (
    <AccordionItemContext.Provider value={{ value, isOpen }}>
      <div className={`border-b ${className || ""}`}>{children}</div>
    </AccordionItemContext.Provider>
  );
}

interface AccordionTriggerProps {
  className?: string;
  children: React.ReactNode;
}

function AccordionTrigger({ className, children }: AccordionTriggerProps) {
  const { onToggle } = React.useContext(AccordionContext);
  const { value, isOpen } = React.useContext(AccordionItemContext);

  return (
    <button
      type="button"
      onClick={() => onToggle(value)}
      className={`flex w-full items-center justify-between ${className || ""}`}
      aria-expanded={isOpen}
    >
      {children}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className={`transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
      >
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    </button>
  );
}

interface AccordionContentProps {
  className?: string;
  children: React.ReactNode;
}

function AccordionContent({ className, children }: AccordionContentProps) {
  const { isOpen } = React.useContext(AccordionItemContext);

  if (!isOpen) return null;

  return (
    <div className={`overflow-hidden ${className || ""}`}>
      {children}
    </div>
  );
}

export { Accordion, AccordionItem, AccordionTrigger, AccordionContent };
