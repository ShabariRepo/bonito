"use client";

import Link from "next/link";
import { History, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { OrigamiWorkspace } from "@/components/origami/OrigamiWorkspace";

export default function OrigamiPage() {
  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Origami"
        description="Plan and deploy Bonito infrastructure in plain English — projects, knowledge bases, agents, and gateway keys."
        actions={
          <div className="flex items-center gap-2">
            <Link href="/origami/history">
              <Button variant="outline" size="sm" className="gap-1.5">
                <History className="h-3.5 w-3.5" />
                History
              </Button>
            </Link>
            <Link href="/origami/usage">
              <Button variant="outline" size="sm" className="gap-1.5">
                <BarChart3 className="h-3.5 w-3.5" />
                Usage
              </Button>
            </Link>
          </div>
        }
      />
      <OrigamiWorkspace />
    </div>
  );
}
