import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Use Cases — How Enterprises Use Bonito",
  description:
    "See how enterprises use Bonito as their AI orchestration platform to unify multi-cloud LLM infrastructure, cut AI costs by 84%, and deploy governed agentic AI agents per department. Real case studies with real numbers on AI routing, LLM observability, and AI governance.",
  keywords: [
    "AI use cases",
    "enterprise AI case studies",
    "AI cost optimization",
    "multi-cloud AI",
    "multi-cloud LLM",
    "AI orchestration platform",
    "agentic AI",
    "enterprise AI agents",
    "AI governance",
    "LLM routing",
    "AI routing",
    "LLM gateway",
    "AI observability",
    "LLM cost management",
    "RAG platform",
    "Langfuse alternative",
    "Portkey alternative",
    "Helicone alternative",
  ],
  openGraph: {
    title: "Bonito Use Cases — Enterprise AI in Action",
    description:
      "Real case studies: 84% cost reduction, $2.25M annual savings, unified multi-cloud AI operations.",
    url: "https://getbonito.com/use-cases",
  },
  alternates: { canonical: "https://getbonito.com/use-cases" },
};

export default function UseCasesLayout({ children }: { children: React.ReactNode }) {
  return children;
}
