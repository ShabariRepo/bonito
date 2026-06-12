"use client";

/**
 * StudioOpener — the snapshot-aware empty state.
 *
 * Shown when the chat has no messages yet. Reads the org snapshot from
 * useStudioSession and renders a specific opener based on what the org
 * looks like — empty / mid-build / active gateway / etc. This is the
 * Claude-Code-like first impression Danny was asking for: the agent
 * already knows the room.
 *
 * The opener text mirrors STUDIO_SYSTEM_PROMPT's opener templates on
 * the backend — if you change one, change the other so the empty state
 * matches what the model will actually say.
 */

import { Sparkles, Cloud, Bot, BookOpen, Activity } from "lucide-react";
import type { StudioSnapshot } from "./types";

type OpenerPattern = {
  headline: string;
  subline: string;
  chips: { label: string; prompt: string; icon: React.ReactNode }[];
  accent: React.ReactNode;
};

function buildPattern(snapshot: StudioSnapshot | null): OpenerPattern {
  if (!snapshot) {
    return {
      headline: "Welcome to Bonito Studio.",
      subline: "Tell me what you want to build.",
      chips: [
        {
          label: "Connect a provider",
          prompt: "Help me connect a model provider.",
          icon: <Cloud size={13} />,
        },
        {
          label: "Build my first agent",
          prompt: "Help me build my first agent.",
          icon: <Bot size={13} />,
        },
        {
          label: "Set up a knowledge base",
          prompt: "Help me set up a knowledge base.",
          icon: <BookOpen size={13} />,
        },
      ],
      accent: <Sparkles size={28} />,
    };
  }

  const providerCount = snapshot.providers?.length ?? 0;
  const activeProvider = snapshot.providers?.find((p) => p.status === "active");
  const agentCount = snapshot.agent_count ?? 0;
  const gateway7d = snapshot.gateway?.requests_7d ?? 0;
  const topModel = snapshot.gateway?.top_models?.[0]?.model;
  const firstName = snapshot.org_name?.split(" ")[0];
  const greeting = firstName ? `${firstName}` : "there";

  // Pattern A — empty org
  if (providerCount === 0) {
    return {
      headline: `Hey ${greeting} — welcome to Bonito Studio.`,
      subline: "Let's start by connecting your first model provider.",
      chips: [
        {
          label: "Connect AWS Bedrock",
          prompt: "I want to connect AWS Bedrock.",
          icon: <Cloud size={13} />,
        },
        {
          label: "Connect OpenAI",
          prompt: "I want to connect OpenAI.",
          icon: <Cloud size={13} />,
        },
        {
          label: "Connect Anthropic",
          prompt: "I want to connect Anthropic.",
          icon: <Cloud size={13} />,
        },
      ],
      accent: <Cloud size={28} />,
    };
  }

  // Pattern B — 1+ providers, 0 agents → invite first agent build
  if (agentCount === 0) {
    const providerName = activeProvider?.provider_type ?? snapshot.providers[0]?.provider_type;
    return {
      headline: `Hey ${greeting} — ${providerName ?? "your provider"} is connected.`,
      subline: "Want to spin up your first agent?",
      chips: [
        {
          label: "Build a support bot",
          prompt: "Build me a customer support agent with a knowledge base.",
          icon: <Bot size={13} />,
        },
        {
          label: "Build a data hub + spokes",
          prompt:
            "Build me a wheel-pattern team: one hub agent that routes to three specialist spokes.",
          icon: <Bot size={13} />,
        },
        {
          label: "Set up a knowledge base",
          prompt: "Help me set up a knowledge base.",
          icon: <BookOpen size={13} />,
        },
      ],
      accent: <Bot size={28} />,
    };
  }

  // Pattern C — active gateway → reference yesterday's usage
  if (gateway7d > 0) {
    const usageLine = topModel
      ? `${gateway7d.toLocaleString()} gateway requests this past week, mostly on ${topModel}.`
      : `${gateway7d.toLocaleString()} gateway requests this past week.`;
    return {
      headline: `Welcome back, ${greeting}.`,
      subline: usageLine + " Want to dig in, work on agents, or something else?",
      chips: [
        {
          label: "Show me usage",
          prompt: "Show me a breakdown of last 7 days gateway usage.",
          icon: <Activity size={13} />,
        },
        {
          label: "Work on agents",
          prompt: "What agents do I have, and which are most active?",
          icon: <Bot size={13} />,
        },
        {
          label: "Mint a gateway key",
          prompt: "Mint me a new gateway key.",
          icon: <Sparkles size={13} />,
        },
      ],
      accent: <Activity size={28} />,
    };
  }

  // Pattern D — providers + agents but no recent gateway → keep building
  return {
    headline: `Welcome back, ${greeting}.`,
    subline: `You have ${agentCount} agent${agentCount === 1 ? "" : "s"} ready. What's next?`,
    chips: [
      {
        label: "Add a knowledge base",
        prompt: "Help me add a new knowledge base.",
        icon: <BookOpen size={13} />,
      },
      {
        label: "Build another agent",
        prompt: "Build me another agent.",
        icon: <Bot size={13} />,
      },
      {
        label: "Mint a gateway key",
        prompt: "Mint me a new gateway key.",
        icon: <Sparkles size={13} />,
      },
    ],
    accent: <Sparkles size={28} />,
  };
}

export function StudioOpener({
  snapshot,
  onChipClick,
}: {
  snapshot: StudioSnapshot | null;
  onChipClick: (prompt: string) => void;
}) {
  const pattern = buildPattern(snapshot);

  return (
    <div className="max-w-2xl mx-auto pt-12 pb-6 px-2">
      <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary mb-5">
        {pattern.accent}
      </div>
      <h1 className="text-2xl font-medium tracking-tight text-foreground">
        {pattern.headline}
      </h1>
      <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
        {pattern.subline}
      </p>

      <div className="mt-7 flex flex-wrap gap-2">
        {pattern.chips.map((chip) => (
          <button
            key={chip.label}
            onClick={() => onChipClick(chip.prompt)}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card hover:bg-accent hover:border-accent-foreground/20 text-foreground/90 text-xs font-medium px-3 py-1.5 transition-colors"
          >
            <span className="text-muted-foreground">{chip.icon}</span>
            {chip.label}
          </button>
        ))}
      </div>

      {snapshot && (
        <p className="mt-6 text-[11px] text-muted-foreground/70">
          On the {snapshot.billing?.tier ?? "free"} plan
          {snapshot.providers?.length
            ? ` · ${snapshot.providers.length} provider${
                snapshot.providers.length === 1 ? "" : "s"
              } connected`
            : ""}
          {snapshot.kb_count > 0
            ? ` · ${snapshot.kb_count} knowledge base${
                snapshot.kb_count === 1 ? "" : "s"
              }`
            : ""}
        </p>
      )}
    </div>
  );
}
