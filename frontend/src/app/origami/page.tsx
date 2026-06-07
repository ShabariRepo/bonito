/**
 * /origami — Phase 3 split-pane workspace.
 *
 * Chat on the left (40%), live workspace on the right (60%):
 *  • Resources grid — every agent/KB/project/gateway-key being built
 *  • Activity log — every tool call with expandable details
 *  • Progress header — during execute_plan
 *  • Result preview — post-deploy summary
 */

import { OrigamiWorkspace } from "@/components/origami/OrigamiWorkspace";

export default function OrigamiPage() {
  return (
    <div className="h-screen w-screen">
      <OrigamiWorkspace />
    </div>
  );
}
