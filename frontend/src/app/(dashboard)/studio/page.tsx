"use client";

/**
 * /studio — Bonito's chat-first front door.
 *
 * Post-auth landing page. Renders StudioChat which owns the snapshot
 * fetch + SSE turn loop. Sidebar is provided by the (dashboard) layout
 * and defaults collapsed (see sidebar-context.tsx).
 *
 * See docs/BONITO-STUDIO-PLAN.md for the full build plan.
 */

import { StudioChat } from "@/components/studio/StudioChat";

export default function StudioPage() {
  return <StudioChat />;
}
