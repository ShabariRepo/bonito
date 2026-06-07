"use client";

import { PageHeader } from "@/components/ui/page-header";
import { OrigamiWorkspace } from "@/components/origami/OrigamiWorkspace";

export default function OrigamiPage() {
  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="Origami"
        description="Plan and deploy Bonito infrastructure in plain English — projects, knowledge bases, agents, and gateway keys."
      />
      <OrigamiWorkspace />
    </div>
  );
}
