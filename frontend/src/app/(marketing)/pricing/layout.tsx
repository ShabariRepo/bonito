import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing — Plans for Every Team",
  description:
    "Bonito pricing for the enterprise AI control plane: Free for individuals, Pro at $999/mo for teams, Enterprise for organizations. Includes LLM gateway, AI routing, LLM observability, and AI cost optimization. Add Bonobot governed AI agents at $349/mo per department.",
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

const faqStructuredData = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "What is Bonito?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Bonito is a unified AI control plane that connects your cloud AI providers — AWS Bedrock, Azure OpenAI, Google Cloud Vertex AI, OpenAI, Anthropic, and Groq — and lets you manage everything from a single dashboard. You get intelligent routing, automatic failover, knowledge base RAG, AI agents, cost tracking, and governance controls — all through one OpenAI-compatible API endpoint.",
      },
    },
    {
      "@type": "Question",
      name: "How does Bonito billing work?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "You are billed monthly based on your plan tier. The Free plan is invite-only and includes 3 provider connections, 25K API calls, failover routing, and 1 BonBon agent. Pro ($999/mo) adds RAG, advanced routing, 5 providers, and 5 BonBon agents. Enterprise ($10K-$20K/mo) includes unlimited everything with SSO/SAML and compliance. Your AI provider costs are billed separately by those providers through your own cloud accounts.",
      },
    },
    {
      "@type": "Question",
      name: "What is AI Context in Bonito?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "AI Context is Bonito's built-in RAG (Retrieval-Augmented Generation) pipeline. Upload documents — PDFs, text files, markdown — and Bonito automatically chunks, embeds, and indexes them using pgvector search. When you or your agents make a query, relevant context is injected automatically with source citations. Every model in your catalog gets access to the same knowledge base.",
      },
    },
    {
      "@type": "Question",
      name: "What's the difference between BonBon and Bonobot agents?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "BonBon agents are pre-built templates you deploy in minutes — pick a template (Customer Support, Knowledge Assistant, Sales Qualifier), add your content, and go live. No coding needed, starting at $49/mo per agent. Bonobot is for teams that need fully custom agents with multi-agent orchestration, delegation workflows, and complete control over agent logic. Both run on the same platform with cost tracking and governance.",
      },
    },
    {
      "@type": "Question",
      name: "What cloud AI providers does Bonito support?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Bonito supports 6 AI providers: AWS Bedrock (with auto cross-region inference), Azure AI Foundry / Azure OpenAI, Google Cloud Vertex AI (Gemini, Veo, Imagen), OpenAI (GPT-4o, DALL-E, Sora), Anthropic (Claude Sonnet, Opus, Haiku), and Groq (fast open-source inference). You connect your own cloud accounts and Bonito discovers all available models.",
      },
    },
    {
      "@type": "Question",
      name: "How does Bonito compare to Langfuse, Helicone, and Portkey?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Bonito is a full-stack AI control plane, not just observability. Unlike Langfuse and Helicone (monitoring-only), Bonito adds multi-provider routing, automatic failover, governed AI agents, and RAG knowledge bases. Unlike Portkey, Bonito adds enterprise governance (SSO, RBAC, compliance), agent orchestration, and deeper cost intelligence. Unlike LangSmith, Bonito is framework-agnostic infrastructure.",
      },
    },
    {
      "@type": "Question",
      name: "Is my data secure with Bonito?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. Bonito never stores your AI request/response data. Prompts and completions pass through the gateway but are never persisted. Credentials are stored in HashiCorp Vault with encryption at rest. Enterprise plans include compliance-ready architecture with full audit trails, RBAC, and data isolation. Agent knowledge bases use isolated vector stores per organization.",
      },
    },
    {
      "@type": "Question",
      name: "Does Bonito offer SSO and SAML?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. Enterprise customers can configure SAML SSO with any identity provider — Okta, Azure AD, Google Workspace, or custom SAML. Users are automatically provisioned on first login via JIT (Just-In-Time) provisioning. Admins can enforce SSO-only login and set up a break-glass admin account for emergencies.",
      },
    },
  ],
};

const productStructuredData = [
  {
    "@context": "https://schema.org",
    "@type": "Product",
    name: "Bonito Free",
    description: "Free AI control plane for teams evaluating multi-cloud AI management. Includes 3 providers, 25K API calls/month, automatic failover, and 1 AI agent.",
    brand: { "@type": "Brand", name: "Bonito" },
    category: "AI Infrastructure",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      availability: "https://schema.org/InStock",
      url: "https://getbonito.com/pricing",
    },
  },
  {
    "@context": "https://schema.org",
    "@type": "Product",
    name: "Bonito Pro",
    description: "Professional AI control plane for teams shipping AI products. 5 providers, 500K API calls/month, advanced routing, RAG knowledge bases, cost analytics, and 5 AI agents.",
    brand: { "@type": "Brand", name: "Bonito" },
    category: "AI Infrastructure",
    offers: {
      "@type": "Offer",
      price: "999",
      priceCurrency: "USD",
      priceValidUntil: "2027-12-31",
      availability: "https://schema.org/InStock",
      url: "https://getbonito.com/pricing",
    },
  },
  {
    "@context": "https://schema.org",
    "@type": "Product",
    name: "Bonito Enterprise",
    description: "Enterprise AI control plane with unlimited providers, SSO/SAML, RBAC, compliance logging, 99.9% SLA, and dedicated support. For organizations with complex AI governance needs.",
    brand: { "@type": "Brand", name: "Bonito" },
    category: "AI Infrastructure",
    offers: {
      "@type": "Offer",
      price: "10000",
      priceCurrency: "USD",
      priceValidUntil: "2027-12-31",
      availability: "https://schema.org/InStock",
      url: "https://getbonito.com/pricing",
    },
  },
];

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqStructuredData) }}
      />
      {productStructuredData.map((product, i) => (
        <script
          key={`product-${i}`}
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(product) }}
        />
      ))}
      {children}
    </>
  );
}
