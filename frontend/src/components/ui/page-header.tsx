"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Breadcrumb {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  description?: string;
  breadcrumbs?: Breadcrumb[];
  actions?: React.ReactNode;
}

export function PageHeader({ title, description, breadcrumbs, actions }: PageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <div className="mb-2 flex items-center gap-1 text-sm text-muted-foreground">
            {breadcrumbs.map((bc, i) => (
              <span key={i} className="flex items-center gap-1">
                {bc.href ? (
                  <Link href={bc.href} className="hover:text-foreground transition-colors">{bc.label}</Link>
                ) : (
                  <span className="text-foreground">{bc.label}</span>
                )}
                {i < breadcrumbs.length - 1 && <ChevronRight className="h-3 w-3" />}
              </span>
            ))}
          </div>
        )}
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground mt-1">{description}</p>}
      </div>
      {actions && <div className="mt-4 sm:mt-0 flex gap-2">{actions}</div>}
    </motion.div>
  );
}
