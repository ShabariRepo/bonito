import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About Bonito — The Enterprise AI Control Plane",
  description:
    "Bonito is building the operating system for enterprise AI. Unified AI governance, LLM routing, and AI cost optimization across AWS, Azure, and GCP. An agentic AI platform with multi-cloud management and full observability.",
  keywords: [
    "about Bonito",
    "enterprise AI control plane",
    "agentic AI platform",
    "AI governance",
    "AI compliance",
    "multi-cloud AI management",
    "LLM routing",
    "AI cost optimization",
    "AI observability",
    "AI orchestration platform",
    "enterprise AI agents",
    "Langfuse",
    "Helicone",
    "Portkey",
    "LangSmith",
    "Arize",
  ],
  openGraph: {
    title: "About Bonito",
    description:
      "The enterprise AI control plane. Unified multi-cloud AI management with governed agents, smart routing, and 84% cost savings.",
    url: "https://getbonito.com/about",
  },
  alternates: { canonical: "https://getbonito.com/about" },
};

export default function AboutLayout({ children }: { children: React.ReactNode }) {
  return children;
}
