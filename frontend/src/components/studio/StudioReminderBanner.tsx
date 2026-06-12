"use client";

/**
 * StudioReminderBanner — additive nudges based on the org snapshot.
 *
 * Sits above the chat scroller. Renders only when there's actionable
 * advice to give (currently: no providers connected). The chat surface
 * still works normally — this is a hint, not a block.
 *
 * Adding new rules:
 *   • Add a condition + render block here. Keep the bar compact (one
 *     short sentence, max 2 links). If a rule has no concrete next-step
 *     URL, don't render it — speculative nags burn user trust.
 *   • Mirror any rule the BDR prompt would surface in chat so the
 *     banner doesn't disagree with what the agent says.
 */

import Link from "next/link";
import { Info, Cloud } from "lucide-react";
import type { StudioSnapshot } from "./types";

export function StudioReminderBanner({
  snapshot,
}: {
  snapshot: StudioSnapshot | null;
}) {
  if (!snapshot) return null;

  // Rule 1 — no providers connected. The most consequential gap: most
  // build requests need at least one provider behind the gateway, and
  // the BDR agent will keep tripping over this until it's fixed.
  if (!snapshot.providers || snapshot.providers.length === 0) {
    return (
      <div className="border-b border-amber-500/20 bg-amber-500/[0.06] px-4 md:px-6 py-2.5 shrink-0">
        <div className="max-w-3xl mx-auto flex items-start gap-2.5">
          <Cloud
            size={14}
            className="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0"
          />
          <p className="text-xs text-amber-900 dark:text-amber-200 leading-relaxed">
            <span className="font-semibold">Heads up</span> — I work better
            once you&rsquo;ve got at least one model provider wired up. Try
            the{" "}
            <Link
              href="/onboarding"
              className="font-semibold underline decoration-amber-500/40 underline-offset-2 hover:decoration-amber-500"
            >
              Setup Wizard
            </Link>
            , or jump straight to{" "}
            <Link
              href="/providers"
              className="font-semibold underline decoration-amber-500/40 underline-offset-2 hover:decoration-amber-500"
            >
              Providers
            </Link>{" "}
            under Integrations.
          </p>
        </div>
      </div>
    );
  }

  // Rule 2 — providers connected, but none active (auth failed, broken
  // creds). Different fix than rule 1; route to the provider list so
  // they can reconnect rather than the wizard.
  const hasActiveProvider = snapshot.providers.some((p) => p.status === "active");
  if (!hasActiveProvider) {
    return (
      <div className="border-b border-amber-500/20 bg-amber-500/[0.06] px-4 md:px-6 py-2.5 shrink-0">
        <div className="max-w-3xl mx-auto flex items-start gap-2.5">
          <Info
            size={14}
            className="text-amber-600 dark:text-amber-400 mt-0.5 shrink-0"
          />
          <p className="text-xs text-amber-900 dark:text-amber-200 leading-relaxed">
            <span className="font-semibold">Provider check</span> — your
            connected providers aren&rsquo;t in an active state. Reconnect
            them from{" "}
            <Link
              href="/providers"
              className="font-semibold underline decoration-amber-500/40 underline-offset-2 hover:decoration-amber-500"
            >
              Providers
            </Link>{" "}
            so I can route real model calls.
          </p>
        </div>
      </div>
    );
  }

  return null;
}
