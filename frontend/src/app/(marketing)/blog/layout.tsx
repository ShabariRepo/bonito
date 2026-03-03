import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Blog — Enterprise AI Insights",
  description:
    "Insights on agentic AI, LLM observability, AI routing, multi-cloud LLM management, and AI cost optimization. Covering enterprise AI agents, AI governance, and the latest in AI orchestration from the Bonito team.",
  keywords: [
    "enterprise AI blog",
    "LLM observability",
    "AI observability",
    "agentic AI",
    "AI routing",
    "AI cost optimization",
    "LLM cost management",
    "multi-cloud AI",
    "AI governance",
    "enterprise AI agents",
    "AI orchestration",
    "LLM gateway",
    "RAG platform",
    "model context protocol",
    "Langfuse",
    "Helicone",
    "Portkey",
    "LangSmith",
    "Arize",
    "Humanloop",
  ],
  openGraph: {
    title: "Bonito Blog — Enterprise AI Insights",
    description:
      "Insights on agentic AI, LLM observability, AI routing, and multi-cloud management from the Bonito team.",
    url: "https://getbonito.com/blog",
  },
  alternates: { canonical: "https://getbonito.com/blog" },
};

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return children;
}
