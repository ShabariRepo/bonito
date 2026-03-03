import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Documentation — Bonito AI Control Plane",
  description:
    "Complete documentation for Bonito, the enterprise AI control plane. Learn how to set up your LLM gateway, configure AI routing policies, deploy governed AI agents with Bonobot, connect knowledge bases for RAG, and integrate MCP tools across multi-cloud infrastructure.",
  keywords: [
    "Bonito documentation",
    "AI control plane docs",
    "LLM gateway setup",
    "AI gateway documentation",
    "AI routing configuration",
    "LLM observability",
    "AI agent framework",
    "enterprise AI agents",
    "Bonobot documentation",
    "model context protocol",
    "MCP integration",
    "RAG platform",
    "knowledge base AI",
    "multi-cloud AI",
    "AI cost optimization",
    "AI governance",
    "agentic AI platform",
    "Langfuse alternative",
    "Portkey alternative",
    "Helicone alternative",
  ],
  openGraph: {
    title: "Bonito Documentation — Enterprise AI Control Plane",
    description:
      "Complete docs for setting up your LLM gateway, AI routing, governed agents, and multi-cloud AI management with Bonito.",
    url: "https://getbonito.com/docs",
  },
  alternates: { canonical: "https://getbonito.com/docs" },
};

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
