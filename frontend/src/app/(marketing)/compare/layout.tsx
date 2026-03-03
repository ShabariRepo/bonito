import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Compare Bonito - AI Control Plane vs Alternatives",
  description:
    "See how Bonito compares to Langfuse, Helicone, Portkey, LangSmith, and Arize. Compare features across LLM observability, AI routing, governed agents, multi-cloud management, and AI cost optimization.",
  keywords: [
    "Bonito comparison",
    "Bonito vs Langfuse",
    "Bonito vs Helicone",
    "Bonito vs Portkey",
    "Bonito vs LangSmith",
    "Bonito vs Arize",
    "LLM observability comparison",
    "AI gateway comparison",
    "AI routing platform",
    "LLM gateway alternative",
    "enterprise AI platform comparison",
    "agentic AI platform",
    "multi-cloud AI",
    "AI cost optimization",
    "AI governance",
    "Humanloop alternative",
    "CGAI alternative",
  ],
  openGraph: {
    title: "Compare Bonito vs AI Platform Alternatives",
    description:
      "Feature-by-feature comparisons of Bonito against Langfuse, Helicone, Portkey, LangSmith, and Arize across observability, routing, agents, and governance.",
    url: "https://getbonito.com/compare",
  },
  alternates: { canonical: "https://getbonito.com/compare" },
};

export default function CompareLayout({ children }: { children: React.ReactNode }) {
  return children;
}
