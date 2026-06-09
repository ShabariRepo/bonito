"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  Terminal,
  Workflow,
  Database,
  KeyRound,
  Check,
  Cloud,
  Cpu,
  ShieldCheck,
  Zap,
  ListChecks,
  CircleDot,
  PlayCircle,
  Lock,
} from "lucide-react";

// ─── FadeIn helper (matches other marketing pages) ───
function FadeIn({
  children,
  className = "",
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// ─── Demo chat lines (typed out in the hero) ───
const heroPrompt =
  "Spin up a customer support agent that searches our policy KB and escalates billing questions to a human.";

const heroPlanCard = [
  { icon: Database, label: "Create knowledge base", detail: "policy-kb" },
  { icon: Cpu, label: "Create agent", detail: "support-bot (gpt-4o-mini)" },
  { icon: Workflow, label: "Wire escalation route", detail: "billing intent to human queue" },
  { icon: KeyRound, label: "Mint gateway key", detail: "for your app" },
];

const tiers = [
  { name: "Free", turns: "50", overage: "no overage", footnote: "Trial only" },
  { name: "Builder", turns: "100", overage: "$0.12 / turn" },
  { name: "Growth", turns: "300", overage: "$0.12 / turn" },
  { name: "Pro", turns: "1,000", overage: "$0.12 / turn" },
  { name: "Enterprise", turns: "5,000+", overage: "$0.10 / turn" },
];

const useCases = [
  {
    title: "First agent in 90 seconds",
    body:
      "New to Bonito? Origami walks you through connecting a provider, syncing your model catalog, and shipping your first agent without ever opening a settings page.",
    icon: PlayCircle,
  },
  {
    title: "Bolt on knowledge bases",
    body:
      "Already have agents but want them grounded in your docs? Tell Origami where the files live. It creates the KB, ingests, embeds, and re-wires the agent.",
    icon: Database,
  },
  {
    title: "Tier-aware orchestration",
    body:
      "Origami knows what your plan can and can't do. If a build needs Enterprise features, it tells you up front, with the cost, and a single button to upgrade in place.",
    icon: ShieldCheck,
  },
  {
    title: "Multi-cloud from one prompt",
    body:
      "Say the word and Origami spreads your workload across Bedrock, Azure, Vertex, OpenAI, Anthropic, and Groq. Failover, cost tracking, and audit are already wired in.",
    icon: Cloud,
  },
];

// ─── Typing animation hook ───
function useTypingDemo(text: string, started: boolean, speed = 28) {
  const [shown, setShown] = useState("");
  useEffect(() => {
    if (!started) return;
    let i = 0;
    const id = setInterval(() => {
      i += 1;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, started, speed]);
  return shown;
}

// ─── Hero workspace mock (split-pane) ───
function WorkspaceMock() {
  const [stage, setStage] = useState(0);
  const typed = useTypingDemo(heroPrompt, stage >= 1);

  useEffect(() => {
    const t1 = setTimeout(() => setStage(1), 600);
    const t2 = setTimeout(() => setStage(2), 4400);
    const t3 = setTimeout(() => setStage(3), 5800);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  return (
    <div className="relative w-full overflow-hidden rounded-2xl border border-[#1a1a1a] bg-[#0f0f0f] shadow-2xl shadow-[#7c3aed]/10">
      {/* Window chrome */}
      <div className="flex items-center gap-2 border-b border-[#1a1a1a] bg-[#0a0a0a] px-4 py-2.5">
        <div className="flex gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-[#333]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#333]" />
          <span className="h-2.5 w-2.5 rounded-full bg-[#333]" />
        </div>
        <span className="ml-3 text-xs text-[#555]">getbonito.com / origami</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 min-h-[420px]">
        {/* Chat pane */}
        <div className="flex flex-col gap-3 border-b border-[#1a1a1a] p-5 md:border-b-0 md:border-r">
          <div className="flex items-center gap-2 text-xs text-[#666] uppercase tracking-wider">
            <Sparkles className="h-3.5 w-3.5 text-[#7c3aed]" />
            <span>Conversation</span>
          </div>
          <div className="flex-1 space-y-3 text-sm">
            <div className="flex justify-end">
              <div className="max-w-[90%] rounded-lg rounded-tr-sm bg-[#7c3aed] px-3 py-2 text-white">
                {typed || <span className="text-white/60">Type to begin&hellip;</span>}
                {stage === 1 && typed.length < heroPrompt.length && (
                  <span className="inline-block w-[1ch] animate-pulse">|</span>
                )}
              </div>
            </div>
            {stage >= 2 && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
                className="flex justify-start"
              >
                <div className="max-w-[92%] rounded-lg rounded-tl-sm border border-[#1a1a1a] bg-[#111] px-3 py-2 text-[#ccc]">
                  Plan ready. Four steps, all within your Builder tier. Hit Deploy when you&apos;re good.
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Workspace pane */}
        <div className="flex flex-col gap-3 p-5">
          <div className="flex items-center gap-2 text-xs text-[#666] uppercase tracking-wider">
            <Workflow className="h-3.5 w-3.5 text-[#7c3aed]" />
            <span>Workspace</span>
          </div>

          {stage < 2 && (
            <div className="flex flex-1 items-center justify-center text-xs text-[#555]">
              The plan card will appear here as Origami thinks.
            </div>
          )}

          {stage >= 2 && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className="rounded-xl border border-[#1a1a1a] bg-[#0a0a0a] p-4"
            >
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#a78bfa]">
                  <ListChecks className="h-3.5 w-3.5" />
                  Plan card
                </div>
                <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
                  Within tier
                </span>
              </div>

              <ul className="space-y-2.5">
                {heroPlanCard.map((step, i) => (
                  <motion.li
                    key={step.label}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.15 * i + 0.2 }}
                    className="flex items-start gap-3 rounded-lg border border-transparent bg-[#111] p-2.5"
                  >
                    <span className="mt-0.5 grid h-7 w-7 place-items-center rounded-md bg-[#7c3aed]/10 text-[#7c3aed]">
                      <step.icon className="h-3.5 w-3.5" />
                    </span>
                    <div className="flex-1">
                      <p className="text-sm text-[#eee]">{step.label}</p>
                      <p className="text-xs text-[#777]">{step.detail}</p>
                    </div>
                    {stage >= 3 ? (
                      <Check className="mt-1 h-4 w-4 text-emerald-400" />
                    ) : (
                      <CircleDot className="mt-1 h-4 w-4 animate-pulse text-[#444]" />
                    )}
                  </motion.li>
                ))}
              </ul>

              <div className="mt-4 flex items-center justify-between gap-2">
                <span className="text-xs text-[#666]">
                  {stage >= 3 ? "Deployed in 8.2s" : "Awaiting confirmation"}
                </span>
                <button
                  disabled
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-semibold transition ${
                    stage >= 3
                      ? "bg-emerald-500/15 text-emerald-300"
                      : "bg-[#7c3aed] text-white"
                  }`}
                >
                  {stage >= 3 ? "Deployed" : "Deploy"}
                  {stage < 3 && <ArrowRight className="h-3 w-3" />}
                </button>
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main page ───
export default function OrigamiPage() {
  const router = useRouter();

  // Logged-in visitors who land here get bounced into the actual workspace.
  // Token lives in localStorage so this has to run client-side.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = window.localStorage.getItem("bonito_access_token");
    if (token) router.replace("/origami/workspace");
  }, [router]);

  return (
    <div className="relative z-10">
      {/* ─── Hero ─── */}
      <section className="mx-auto max-w-6xl px-6 pb-12 pt-20 md:px-12 md:pt-32">
        <FadeIn className="text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#7c3aed]/20 bg-[#7c3aed]/10 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-[#a78bfa]">
            <Sparkles className="h-3.5 w-3.5" />
            Now in early access
          </div>
          <h1 className="text-4xl font-bold tracking-tight md:text-6xl">
            Build infra by talking.{" "}
            <span className="text-[#7c3aed]">Watch it ship.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-lg text-[#888]">
            Origami is Bonito&apos;s conversational build workspace. Tell it what
            you want. It plans. You hit Deploy. Real agents, real KBs, real
            gateway keys, end to end, all on your existing Bonito org.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/register"
              className="group inline-flex items-center gap-2 rounded-lg bg-[#7c3aed] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#6d28d9]"
            >
              Start with 50 free turns
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
            <Link
              href="#how-it-works"
              className="inline-flex items-center gap-2 rounded-lg border border-[#333] px-6 py-3 text-sm text-[#aaa] transition hover:border-[#7c3aed]/40 hover:text-[#f5f0e8]"
            >
              See how it works
            </Link>
          </div>
        </FadeIn>

        <FadeIn delay={0.15} className="mt-16">
          <WorkspaceMock />
        </FadeIn>
      </section>

      {/* ─── Three feature pillars ─── */}
      <section id="how-it-works" className="mx-auto max-w-6xl px-6 py-16 md:px-12">
        <FadeIn className="text-center">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Three things make Origami feel different.
          </h2>
          <p className="mt-3 text-[#888]">
            It is not a chatbot. It is a build surface.
          </p>
        </FadeIn>

        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {[
            {
              icon: Terminal,
              title: "Talk it",
              body:
                "Plain English. No YAML, no clicking. Origami understands provider connections, agent topology, KB ingestion, gateway keys, and tier limits as first-class concepts.",
            },
            {
              icon: ListChecks,
              title: "Watch it",
              body:
                "Every plan is a card you can read line by line. Origami shows what it is about to change, why, and what it will cost on your current tier. You stay in control.",
            },
            {
              icon: Zap,
              title: "Ship it",
              body:
                "Hit Deploy and the plan runs through Bonito's API, the same one your code uses. Every action is audited in the immutable Origami log. No black box.",
            },
          ].map((pillar, i) => (
            <FadeIn key={pillar.title} delay={0.1 * i}>
              <div className="h-full rounded-xl border border-[#1a1a1a] bg-[#111] p-6 transition hover:border-[#7c3aed]/30">
                <div className="mb-4 grid h-10 w-10 place-items-center rounded-lg bg-[#7c3aed]/10 text-[#a78bfa]">
                  <pillar.icon className="h-5 w-5" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-[#f5f0e8]">
                  {pillar.title}
                </h3>
                <p className="text-sm leading-relaxed text-[#999]">{pillar.body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* ─── Tier table ─── */}
      <section className="mx-auto max-w-6xl px-6 py-16 md:px-12">
        <FadeIn className="text-center">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Pricing follows your existing plan.
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-[#888]">
            Origami turns are included on every Bonito tier. A turn is one
            round-trip: your message in, plan card or response out. Overage is
            usage-based, no surprises.
          </p>
        </FadeIn>

        <FadeIn delay={0.1} className="mt-10">
          <div className="overflow-hidden rounded-xl border border-[#1a1a1a]">
            <table className="w-full text-sm">
              <thead className="bg-[#111] text-xs uppercase tracking-wider text-[#888]">
                <tr>
                  <th className="px-5 py-3 text-left font-semibold">Tier</th>
                  <th className="px-5 py-3 text-left font-semibold">Turns / month</th>
                  <th className="px-5 py-3 text-left font-semibold">Overage</th>
                  <th className="px-5 py-3 text-left font-semibold">Note</th>
                </tr>
              </thead>
              <tbody>
                {tiers.map((tier, i) => (
                  <tr
                    key={tier.name}
                    className={`border-t border-[#1a1a1a] transition hover:bg-[#0e0e0e] ${
                      i === tiers.length - 1 ? "bg-[#7c3aed]/5" : ""
                    }`}
                  >
                    <td className="px-5 py-4 font-semibold text-[#f5f0e8]">
                      {tier.name}
                    </td>
                    <td className="px-5 py-4 text-[#ccc]">{tier.turns}</td>
                    <td className="px-5 py-4 text-[#999]">{tier.overage}</td>
                    <td className="px-5 py-4 text-xs text-[#777]">
                      {tier.footnote || "Included"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-center text-xs text-[#666]">
            Need more headroom? Pro and Enterprise tiers add seat-level
            allowances. See <Link href="/pricing" className="text-[#a78bfa] hover:underline">full pricing</Link>.
          </p>
        </FadeIn>
      </section>

      {/* ─── How it is different ─── */}
      <section className="mx-auto max-w-6xl px-6 py-16 md:px-12">
        <FadeIn className="text-center">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Already using a coding agent? Origami is the layer below it.
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-[#888]">
            Other agent frameworks help you write code. Origami stands up the
            infrastructure your code talks to.
          </p>
        </FadeIn>

        <FadeIn delay={0.1} className="mt-10">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              {
                title: "Routes through Bonito gateway",
                body:
                  "Every model call gets cost tracking, failover, and audit out of the box. Coding agents call providers directly. You lose those rails.",
              },
              {
                title: "Tier-aware planning",
                body:
                  "Origami reads your subscription before it plans. It will not propose Enterprise features if you are on Builder. It will offer to upgrade in place.",
              },
              {
                title: "Org-scoped by construction",
                body:
                  "Origami uses a dedicated og- token bound to one (user, org) pair at the auth layer. Tools cannot escape your org even if the model tries.",
              },
              {
                title: "Immutable audit trail",
                body:
                  "Every intent, plan card, tier check, and tool call is logged to the origami_audit_log table. Compliance teams see exactly what was changed and why.",
              },
            ].map((row, i) => (
              <div
                key={row.title}
                className="rounded-xl border border-[#1a1a1a] bg-[#111] p-5 transition hover:border-[#7c3aed]/30"
              >
                <div className="mb-2 flex items-center gap-2">
                  <Lock className="h-4 w-4 text-[#a78bfa]" />
                  <h3 className="text-sm font-semibold text-[#f5f0e8]">{row.title}</h3>
                </div>
                <p className="text-sm leading-relaxed text-[#999]">{row.body}</p>
              </div>
            ))}
          </div>
        </FadeIn>
      </section>

      {/* ─── Use cases ─── */}
      <section className="mx-auto max-w-6xl px-6 py-16 md:px-12">
        <FadeIn className="text-center">
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            What people build with it
          </h2>
        </FadeIn>

        <div className="mt-10 grid gap-5 md:grid-cols-2">
          {useCases.map((uc, i) => (
            <FadeIn key={uc.title} delay={0.1 * (i % 2)}>
              <div className="h-full rounded-xl border border-[#1a1a1a] bg-[#111] p-6 transition hover:border-[#7c3aed]/30">
                <div className="mb-4 grid h-10 w-10 place-items-center rounded-lg bg-[#7c3aed]/10 text-[#a78bfa]">
                  <uc.icon className="h-5 w-5" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-[#f5f0e8]">{uc.title}</h3>
                <p className="text-sm leading-relaxed text-[#999]">{uc.body}</p>
              </div>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* ─── Closing CTA ─── */}
      <section className="mx-auto max-w-4xl px-6 py-20 md:px-12">
        <FadeIn>
          <div className="relative overflow-hidden rounded-2xl border border-[#7c3aed]/30 bg-gradient-to-br from-[#7c3aed]/20 via-[#111] to-[#111] p-10 text-center">
            <div className="absolute right-0 top-0 h-64 w-64 rounded-full bg-[#7c3aed]/10 blur-3xl" />
            <div className="relative">
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
                The fastest way into Bonito is to ask for it.
              </h2>
              <p className="mx-auto mt-3 max-w-xl text-[#aaa]">
                Sign up free, open Origami, type what you want. The plan card
                appears. You hit Deploy. Your first agent is live before your
                coffee gets cold.
              </p>
              <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Link
                  href="/register"
                  className="group inline-flex items-center gap-2 rounded-lg bg-[#7c3aed] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#6d28d9]"
                >
                  Get 50 turns free
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center gap-2 rounded-lg border border-[#333] px-6 py-3 text-sm text-[#aaa] transition hover:border-[#7c3aed]/40 hover:text-[#f5f0e8]"
                >
                  Compare plans
                </Link>
              </div>
            </div>
          </div>
        </FadeIn>
      </section>
    </div>
  );
}
