"use client";

import type { Resource } from "./useOrigamiSession";
import { ResourceCard } from "./ResourceCard";

export function ResourcesGrid({ resources }: { resources: Resource[] }) {
  if (resources.length === 0) {
    return (
      <div className="text-xs text-[#666] italic px-2 py-6 text-center border border-dashed border-[#1a1a1a] rounded-md">
        Resources you build will appear here.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
      {resources.map((r) => (
        <ResourceCard key={r.id} resource={r} />
      ))}
    </div>
  );
}
