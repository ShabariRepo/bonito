/**
 * /origami — Phase 1 skeleton page.
 *
 * Hosts the OrigamiChat component full-screen. Phase 3 expands this into the
 * full split-pane workspace (chat left, resources/activity right) per
 * docs/ORIGAMI-MVP-PLAN.md "Workspace UX".
 */

import { OrigamiChat } from "@/components/origami/OrigamiChat";

export default function OrigamiPage() {
  return (
    <div className="h-screen w-screen">
      <OrigamiChat />
    </div>
  );
}
