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

const definedTerms = {
  "@context": "https://schema.org",
  "@type": "DefinedTermSet",
  name: "AI Infrastructure Concepts",
  hasDefinedTerm: [
    {
      "@type": "DefinedTerm",
      name: "AI Control Plane",
      description: "A unified management layer that sits between applications and AI providers, handling routing, governance, cost tracking, and failover across multiple cloud AI services like AWS Bedrock, Azure OpenAI, and Google Vertex AI.",
    },
    {
      "@type": "DefinedTerm",
      name: "AI Gateway",
      description: "An API proxy that provides a single endpoint (typically OpenAI-compatible) to route requests to multiple AI providers. Handles authentication, load balancing, failover, and request logging.",
    },
    {
      "@type": "DefinedTerm",
      name: "LLM Observability",
      description: "Monitoring and analytics for large language model usage including token consumption, latency tracking, cost attribution, error rates, and model performance across providers.",
    },
    {
      "@type": "DefinedTerm",
      name: "Multi-Cloud AI",
      description: "Strategy of using AI services from multiple cloud providers simultaneously to avoid vendor lock-in, optimize costs, ensure redundancy, and access the best models from each provider.",
    },
    {
      "@type": "DefinedTerm",
      name: "AI Agent Orchestration",
      description: "Coordinating multiple AI agents that can communicate, delegate tasks, and work together in workflows. Includes features like agent-to-agent connections, approval queues, and budget controls.",
    },
  ],
};

export default function CompareLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(definedTerms) }}
      />
      {children}
    </>
  );
}
