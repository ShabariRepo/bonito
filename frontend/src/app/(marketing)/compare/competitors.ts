export interface FeatureComparison {
  category: string;
  features: {
    name: string;
    bonito: string | boolean;
    competitor: string | boolean;
  }[];
}

export interface Competitor {
  slug: string;
  name: string;
  fullName: string;
  tagline: string;
  description: string;
  metaTitle: string;
  metaDescription: string;
  whatTheyDoWell: string[];
  whereBonitoGoesFurther: string[];
  features: FeatureComparison[];
  keywords: string[];
}

export const competitors: Competitor[] = [
  {
    slug: "langfuse",
    name: "Langfuse",
    fullName: "Langfuse",
    tagline: "Open-source LLM observability vs. full AI control plane",
    description:
      "Langfuse is an excellent open-source platform for LLM tracing and observability. It helps teams debug, analyze, and monitor their LLM applications with detailed trace views and prompt management. Bonito includes observability as part of a broader AI control plane that also covers routing, agent deployment, governance, and multi-cloud management.",
    metaTitle: "Bonito vs Langfuse - LLM Observability and Beyond",
    metaDescription:
      "Compare Bonito and Langfuse for LLM observability. Langfuse offers open-source tracing. Bonito provides observability plus AI routing, governed agents, multi-cloud management, and AI cost optimization in one platform.",
    whatTheyDoWell: [
      "Open-source with self-hosting option for full data control",
      "Deep LLM tracing with detailed span and generation views",
      "Prompt management and versioning system",
      "Evaluation framework for scoring LLM outputs",
      "Active community and frequent releases",
    ],
    whereBonitoGoesFurther: [
      "Full AI gateway with intelligent routing (cost-optimized, failover, A/B testing)",
      "Governed AI agents (BonBon and Bonobot) with default-deny security",
      "Multi-cloud provider management across AWS, Azure, and GCP from one dashboard",
      "One-click model deployment and activation across all providers",
      "AI cost analytics with per-model, per-provider breakdowns and budget alerts",
      "Knowledge bases with RAG for agent-powered retrieval",
      "MCP (Model Context Protocol) integration for tool-using agents",
      "Enterprise compliance features (SOC 2, HIPAA-ready audit trails)",
    ],
    features: [
      {
        category: "Observability",
        features: [
          { name: "LLM request tracing", bonito: true, competitor: true },
          { name: "Prompt management", bonito: true, competitor: true },
          { name: "Cost tracking per request", bonito: true, competitor: true },
          { name: "Evaluation scoring", bonito: true, competitor: true },
          { name: "Multi-cloud cost aggregation", bonito: true, competitor: false },
        ],
      },
      {
        category: "Gateway and Routing",
        features: [
          { name: "LLM gateway / proxy", bonito: true, competitor: false },
          { name: "Cost-optimized routing", bonito: true, competitor: false },
          { name: "Failover chains", bonito: true, competitor: false },
          { name: "A/B testing across models", bonito: true, competitor: false },
          { name: "OpenAI-compatible API", bonito: true, competitor: false },
        ],
      },
      {
        category: "AI Agents",
        features: [
          { name: "Managed AI agents", bonito: true, competitor: false },
          { name: "Multi-agent orchestration", bonito: true, competitor: false },
          { name: "Agent audit trails", bonito: true, competitor: false },
          { name: "Per-agent budget controls", bonito: true, competitor: false },
          { name: "Embeddable chat widget", bonito: true, competitor: false },
        ],
      },
      {
        category: "Infrastructure",
        features: [
          { name: "Multi-cloud provider management", bonito: true, competitor: false },
          { name: "One-click model deployment", bonito: true, competitor: false },
          { name: "Knowledge bases / RAG", bonito: true, competitor: false },
          { name: "MCP tool integration", bonito: true, competitor: false },
          { name: "Open-source / self-hosted", bonito: false, competitor: true },
        ],
      },
    ],
    keywords: [
      "Bonito vs Langfuse",
      "Langfuse alternative",
      "LLM observability comparison",
      "LLM tracing platform",
      "AI observability",
      "open source LLM observability",
      "LLM gateway",
      "AI routing",
      "enterprise AI agents",
      "agentic AI platform",
    ],
  },
  {
    slug: "helicone",
    name: "Helicone",
    fullName: "Helicone",
    tagline: "LLM observability proxy vs. unified AI control plane",
    description:
      "Helicone provides LLM observability through a lightweight proxy layer. It is easy to integrate and offers request logging, cost tracking, and caching. Bonito goes beyond observability into active routing, governed agent deployment, and full multi-cloud infrastructure management.",
    metaTitle: "Bonito vs Helicone - LLM Proxy and Observability Compared",
    metaDescription:
      "Compare Bonito and Helicone for LLM observability and proxying. Helicone offers logging and caching via proxy. Bonito provides AI routing, governed agents, multi-cloud management, and AI cost optimization in a unified control plane.",
    whatTheyDoWell: [
      "Simple one-line proxy integration for instant observability",
      "Request caching to reduce costs on repeated queries",
      "Clean dashboard for cost tracking and request analytics",
      "Rate limiting and threat detection features",
      "Quick setup with minimal code changes",
    ],
    whereBonitoGoesFurther: [
      "Intelligent routing policies, not just proxying (cost-optimized, failover, A/B)",
      "Governed AI agents (BonBon and Bonobot) with per-agent security and budget controls",
      "Full cloud provider management: connect AWS, Azure, and GCP accounts directly",
      "Model deployment and activation across all providers from one dashboard",
      "Knowledge bases with RAG for retrieval-augmented agent workflows",
      "MCP integration for agents that use external tools",
      "Enterprise governance with SOC 2 and HIPAA-ready compliance",
      "Multi-agent orchestration with async fan-out patterns",
    ],
    features: [
      {
        category: "Observability",
        features: [
          { name: "Request logging and analytics", bonito: true, competitor: true },
          { name: "Cost tracking", bonito: true, competitor: true },
          { name: "Request caching", bonito: "Planned", competitor: true },
          { name: "Rate limiting", bonito: true, competitor: true },
          { name: "Multi-cloud cost aggregation", bonito: true, competitor: false },
        ],
      },
      {
        category: "Gateway and Routing",
        features: [
          { name: "LLM proxy layer", bonito: true, competitor: true },
          { name: "Cost-optimized routing", bonito: true, competitor: false },
          { name: "Failover chains", bonito: true, competitor: false },
          { name: "A/B testing across models", bonito: true, competitor: false },
          { name: "Provider-agnostic API", bonito: true, competitor: "Partial" },
        ],
      },
      {
        category: "AI Agents",
        features: [
          { name: "Managed AI agents", bonito: true, competitor: false },
          { name: "Multi-agent orchestration", bonito: true, competitor: false },
          { name: "Default-deny agent security", bonito: true, competitor: false },
          { name: "Per-agent budget controls", bonito: true, competitor: false },
          { name: "Knowledge bases / RAG", bonito: true, competitor: false },
        ],
      },
      {
        category: "Infrastructure",
        features: [
          { name: "Cloud provider account management", bonito: true, competitor: false },
          { name: "One-click model deployment", bonito: true, competitor: false },
          { name: "MCP tool integration", bonito: true, competitor: false },
          { name: "Threat detection", bonito: true, competitor: true },
          { name: "Enterprise compliance (SOC 2, HIPAA)", bonito: true, competitor: false },
        ],
      },
    ],
    keywords: [
      "Bonito vs Helicone",
      "Helicone alternative",
      "LLM observability proxy",
      "LLM logging platform",
      "AI observability",
      "LLM gateway comparison",
      "AI routing",
      "enterprise AI platform",
      "AI cost optimization",
      "agentic AI",
    ],
  },
  {
    slug: "portkey",
    name: "Portkey",
    fullName: "Portkey",
    tagline: "AI gateway vs. full enterprise AI control plane",
    description:
      "Portkey is a capable AI gateway focused on routing, load balancing, and reliability for LLM applications. It is one of the closest competitors to Bonito on gateway features. Bonito extends beyond the gateway layer with governed AI agents (BonBon and Bonobot), full cloud provider account management, and enterprise compliance features.",
    metaTitle: "Bonito vs Portkey - AI Gateway and Routing Compared",
    metaDescription:
      "Compare Bonito and Portkey for AI gateway and LLM routing. Portkey offers gateway routing and observability. Bonito adds governed AI agents, multi-cloud provider management, knowledge bases, and enterprise AI governance on top of a full AI gateway.",
    whatTheyDoWell: [
      "Robust AI gateway with routing, load balancing, and fallbacks",
      "Good provider coverage across major LLM APIs",
      "Guardrails for content moderation and safety",
      "Prompt management and versioning",
      "Solid developer experience with clear documentation",
    ],
    whereBonitoGoesFurther: [
      "Direct cloud provider account connections (AWS, Azure, GCP) with IAM management",
      "Governed AI agents (BonBon and Bonobot) with default-deny security architecture",
      "Multi-agent orchestration with coordinator-specialist fan-out patterns",
      "Knowledge bases with RAG for retrieval-augmented workflows",
      "One-click model deployment and activation across all three cloud providers",
      "AI cost analytics with cross-cloud aggregation and budget alerts",
      "MCP integration for tool-using agents",
      "Enterprise governance with audit trails, compliance scanning, and HIPAA readiness",
    ],
    features: [
      {
        category: "Gateway and Routing",
        features: [
          { name: "LLM gateway / proxy", bonito: true, competitor: true },
          { name: "Cost-optimized routing", bonito: true, competitor: true },
          { name: "Failover and retries", bonito: true, competitor: true },
          { name: "Load balancing", bonito: true, competitor: true },
          { name: "A/B testing", bonito: true, competitor: true },
        ],
      },
      {
        category: "Observability",
        features: [
          { name: "Request logging", bonito: true, competitor: true },
          { name: "Cost tracking", bonito: true, competitor: true },
          { name: "Prompt management", bonito: true, competitor: true },
          { name: "Guardrails / safety", bonito: true, competitor: true },
          { name: "Multi-cloud cost aggregation", bonito: true, competitor: false },
        ],
      },
      {
        category: "AI Agents",
        features: [
          { name: "Managed AI agents", bonito: true, competitor: false },
          { name: "Multi-agent orchestration", bonito: true, competitor: false },
          { name: "Default-deny agent security", bonito: true, competitor: false },
          { name: "Agent audit trails", bonito: true, competitor: false },
          { name: "Embeddable chat widget", bonito: true, competitor: false },
        ],
      },
      {
        category: "Infrastructure",
        features: [
          { name: "Cloud provider account management", bonito: true, competitor: false },
          { name: "One-click model deployment", bonito: true, competitor: false },
          { name: "Knowledge bases / RAG", bonito: true, competitor: false },
          { name: "MCP tool integration", bonito: true, competitor: false },
          { name: "Enterprise compliance (SOC 2, HIPAA)", bonito: true, competitor: "Partial" },
        ],
      },
    ],
    keywords: [
      "Bonito vs Portkey",
      "Portkey alternative",
      "AI gateway comparison",
      "LLM routing platform",
      "AI routing",
      "LLM gateway",
      "enterprise AI agents",
      "AI orchestration",
      "multi-cloud AI management",
      "agentic AI platform",
    ],
  },
  {
    slug: "langsmith",
    name: "LangSmith",
    fullName: "LangSmith (by LangChain)",
    tagline: "LangChain ecosystem platform vs. framework-agnostic AI control plane",
    description:
      "LangSmith is LangChain's platform for LLM observability, testing, and evaluation. It is deeply integrated with the LangChain framework and provides excellent tooling for teams already in that ecosystem. Bonito is framework-agnostic and combines observability with routing, agent deployment, and multi-cloud infrastructure management.",
    metaTitle: "Bonito vs LangSmith - LLM Platform Comparison",
    metaDescription:
      "Compare Bonito and LangSmith for LLM observability and management. LangSmith is tied to the LangChain ecosystem. Bonito is framework-agnostic with AI routing, governed agents, multi-cloud management, and AI cost optimization built in.",
    whatTheyDoWell: [
      "Deep integration with LangChain and LangGraph frameworks",
      "Comprehensive tracing for complex chain and agent executions",
      "Evaluation and testing datasets for systematic LLM quality checks",
      "Prompt hub for sharing and versioning prompts",
      "Strong developer tooling for debugging LangChain applications",
    ],
    whereBonitoGoesFurther: [
      "Framework-agnostic: works with any OpenAI-compatible SDK, not just LangChain",
      "Full AI gateway with cost-optimized routing, failover, and A/B testing",
      "Governed AI agents (BonBon and Bonobot) with enterprise security",
      "Direct cloud provider management across AWS Bedrock, Azure OpenAI, and GCP Vertex",
      "One-click model deployment instead of manual provider console setup",
      "Knowledge bases with RAG that work independently of any framework",
      "Multi-cloud cost aggregation with budget alerts and optimization suggestions",
      "MCP tool integration for agent workflows",
    ],
    features: [
      {
        category: "Observability",
        features: [
          { name: "LLM request tracing", bonito: true, competitor: true },
          { name: "Chain / agent execution tracing", bonito: true, competitor: true },
          { name: "Evaluation datasets", bonito: "Planned", competitor: true },
          { name: "Prompt management", bonito: true, competitor: true },
          { name: "Framework-agnostic", bonito: true, competitor: false },
        ],
      },
      {
        category: "Gateway and Routing",
        features: [
          { name: "LLM gateway / proxy", bonito: true, competitor: false },
          { name: "Cost-optimized routing", bonito: true, competitor: false },
          { name: "Failover chains", bonito: true, competitor: false },
          { name: "A/B testing across models", bonito: true, competitor: false },
          { name: "OpenAI-compatible API", bonito: true, competitor: false },
        ],
      },
      {
        category: "AI Agents",
        features: [
          { name: "Managed agent deployment", bonito: true, competitor: false },
          { name: "Multi-agent orchestration", bonito: true, competitor: "Via LangGraph" },
          { name: "Default-deny security", bonito: true, competitor: false },
          { name: "Per-agent budget controls", bonito: true, competitor: false },
          { name: "Knowledge bases / RAG", bonito: true, competitor: "Via LangChain" },
        ],
      },
      {
        category: "Infrastructure",
        features: [
          { name: "Cloud provider account management", bonito: true, competitor: false },
          { name: "One-click model deployment", bonito: true, competitor: false },
          { name: "MCP tool integration", bonito: true, competitor: false },
          { name: "Multi-cloud cost aggregation", bonito: true, competitor: false },
          { name: "Enterprise compliance (SOC 2, HIPAA)", bonito: true, competitor: "Partial" },
        ],
      },
    ],
    keywords: [
      "Bonito vs LangSmith",
      "LangSmith alternative",
      "LangChain platform comparison",
      "LLM observability",
      "framework-agnostic AI platform",
      "AI routing",
      "LLM gateway",
      "enterprise AI agents",
      "AI orchestration platform",
      "multi-cloud AI",
    ],
  },
  {
    slug: "arize",
    name: "Arize",
    fullName: "Arize AI",
    tagline: "ML observability platform vs. AI-native control plane",
    description:
      "Arize is a well-established ML observability platform that has expanded into LLM monitoring and evaluation. It brings deep expertise in model performance monitoring, drift detection, and data quality from the traditional ML world. Bonito is built AI-native from day one, focusing on the full lifecycle of LLM operations: routing, agents, governance, and multi-cloud infrastructure.",
    metaTitle: "Bonito vs Arize - AI Observability Platform Comparison",
    metaDescription:
      "Compare Bonito and Arize for AI observability. Arize offers deep ML and LLM monitoring with drift detection. Bonito is AI-native with LLM routing, governed agents, multi-cloud management, and AI cost optimization as a unified control plane.",
    whatTheyDoWell: [
      "Deep ML observability with drift detection and data quality monitoring",
      "LLM tracing with Phoenix (open-source) and Arize platform",
      "Evaluation and benchmarking tools for model performance",
      "Enterprise-grade infrastructure and reliability",
      "Strong integration with traditional ML pipelines and tools",
    ],
    whereBonitoGoesFurther: [
      "Built for LLM-first workflows, not adapted from traditional ML monitoring",
      "Full AI gateway with intelligent routing (cost-optimized, failover, A/B testing)",
      "Governed AI agents (BonBon and Bonobot) with enterprise security architecture",
      "Direct cloud provider management for AWS Bedrock, Azure OpenAI, and GCP Vertex AI",
      "One-click model deployment and activation across all providers",
      "Knowledge bases with RAG for retrieval-augmented agent workflows",
      "MCP integration for tool-using agents",
      "Multi-cloud cost aggregation with budget alerts and optimization recommendations",
    ],
    features: [
      {
        category: "Observability",
        features: [
          { name: "LLM request tracing", bonito: true, competitor: true },
          { name: "Traditional ML monitoring", bonito: false, competitor: true },
          { name: "Drift detection", bonito: false, competitor: true },
          { name: "Evaluation and benchmarking", bonito: true, competitor: true },
          { name: "Multi-cloud cost aggregation", bonito: true, competitor: false },
        ],
      },
      {
        category: "Gateway and Routing",
        features: [
          { name: "LLM gateway / proxy", bonito: true, competitor: false },
          { name: "Cost-optimized routing", bonito: true, competitor: false },
          { name: "Failover chains", bonito: true, competitor: false },
          { name: "A/B testing across models", bonito: true, competitor: false },
          { name: "OpenAI-compatible API", bonito: true, competitor: false },
        ],
      },
      {
        category: "AI Agents",
        features: [
          { name: "Managed AI agents", bonito: true, competitor: false },
          { name: "Multi-agent orchestration", bonito: true, competitor: false },
          { name: "Default-deny agent security", bonito: true, competitor: false },
          { name: "Per-agent budget controls", bonito: true, competitor: false },
          { name: "Knowledge bases / RAG", bonito: true, competitor: false },
        ],
      },
      {
        category: "Infrastructure",
        features: [
          { name: "Cloud provider account management", bonito: true, competitor: false },
          { name: "One-click model deployment", bonito: true, competitor: false },
          { name: "MCP tool integration", bonito: true, competitor: false },
          { name: "Traditional ML pipeline integration", bonito: false, competitor: true },
          { name: "Enterprise compliance (SOC 2, HIPAA)", bonito: true, competitor: true },
        ],
      },
    ],
    keywords: [
      "Bonito vs Arize",
      "Arize alternative",
      "AI observability comparison",
      "LLM monitoring platform",
      "ML observability",
      "AI-native platform",
      "LLM gateway",
      "AI routing",
      "enterprise AI agents",
      "multi-cloud AI management",
    ],
  },
];
