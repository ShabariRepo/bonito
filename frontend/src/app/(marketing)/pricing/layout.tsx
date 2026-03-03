import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing — Plans for Every Team",
  description:
    "Bonito pricing for the enterprise AI control plane: Free for individuals, Pro at $499/mo for teams, Enterprise for organizations. Includes LLM gateway, AI routing, LLM observability, and AI cost optimization. Add Bonobot governed AI agents at $349/mo per department.",
  keywords: [
    "Bonito pricing",
    "AI gateway pricing",
    "LLM gateway cost",
    "AI cost optimization",
    "LLM cost management",
    "enterprise AI pricing",
    "AI agent pricing",
    "multi-cloud AI",
    "AI routing",
    "LLM observability",
    "agentic AI platform",
    "AI governance",
    "Langfuse pricing",
    "Helicone pricing",
    "Portkey pricing",
    "LangSmith pricing",
    "Arize pricing",
  ],
  openGraph: {
    title: "Bonito Pricing — Enterprise AI Control Plane",
    description:
      "Unified multi-cloud AI management from $0. Smart routing saves up to 84% on AI costs. Add governed AI agents per department.",
    url: "https://getbonito.com/pricing",
  },
  alternates: { canonical: "https://getbonito.com/pricing" },
};

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
