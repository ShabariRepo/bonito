"use client";

import type { Resource } from "./useOrigamiSession";
import { ResourceCard } from "./ResourceCard";

export function ResourcesGrid({ resources }: { resources: Resource[] }) {
  if (resources.length === 0) {
    return (
      <div className="text-sm text-muted-foreground italic py-8 text-center border border-dashed border-border rounded-md">
        Resources you build will appear here.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {resources.map((r) => (
        <ResourceCard key={r.id} resource={r} />
      ))}
    </div>
  );
}
