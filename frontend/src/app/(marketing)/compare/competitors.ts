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
      "Enterprise compliance-ready architecture (audit trails, RBAC, data isolation)",
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
      "Enterprise governance with full audit trails, RBAC, and compliance-ready architecture",
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
          { name: "Compliance-ready architecture (audit trails, RBAC)", bonito: true, competitor: false },
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
      "Enterprise governance with audit trails, compliance scanning, and data isolation",
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
          { name: "Compliance-ready architecture (audit trails, RBAC)", bonito: true, competitor: "Partial" },
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
          { name: "Compliance-ready architecture (audit trails, RBAC)", bonito: true, competitor: "Partial" },
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
          { name: "Compliance-ready architecture (audit trails, RBAC)", bonito: true, competitor: true },
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
  {
    slug: "litellm",
    name: "LiteLLM",
    fullName: "LiteLLM (BerriAI)",
    tagline: "Open-source proxy library vs. managed enterprise control plane",
    description:
      "LiteLLM is a strong open-source unified API proxy: one OpenAI-compatible SDK across 100+ providers, self-hosted, MIT-licensed. It is the default first-stop for developers who want a multi-provider abstraction without a vendor. Bonito is the managed enterprise control plane on top of the same problem domain: governed agents, RAG knowledge bases, audit ledger, compliance posture, SSO, and structural cloud-neutrality across the same provider surface — without the self-hosting burden.",
    metaTitle: "Bonito vs LiteLLM — Managed Control Plane vs OSS Proxy",
    metaDescription:
      "LiteLLM is an open-source LLM proxy library. Bonito is a managed enterprise AI control plane: gateway plus governed agents, RAG knowledge bases, immutable audit ledger, SSO, compliance posture (SOC-2 path, HIPAA, GDPR), and structural cloud-neutrality across OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq.",
    whatTheyDoWell: [
      "Open-source, MIT-licensed, self-hostable for full data sovereignty",
      "OpenAI-compatible SDK across 100+ providers — broadest provider surface in the OSS category",
      "Active developer community and frequent releases",
      "Strong fit for teams that want a thin abstraction and own the operational burden",
      "Free at the SDK layer (paid LiteLLM-managed tier exists for hosted observability)",
    ],
    whereBonitoGoesFurther: [
      "Managed control plane — no self-hosting, no proxy operations, no upgrade-toil",
      "Governed Bonobot agents with visual canvas, default-deny tool policy, budget stops, SSRF protection, audit trail",
      "RAG knowledge bases on pgvector HNSW with VectorBoost 3.9-8x compression (no equivalent layer in LiteLLM)",
      "Immutable audit ledger across every model call, agent run, KB query, gateway request",
      "SSO/SAML across Okta, Azure AD, Google Workspace, Custom SAML; RBAC; tier-based log retention",
      "Compliance posture: SOC-2 in flight, HIPAA, GDPR, ISO27001 governance checks built into the platform",
      "Cost intelligence: real-time aggregation, per-1K-token efficiency comparison across providers, budget enforcement",
      "Image generation and video generation on the same gateway key (Sora-2, Veo, dall-e, gpt-image-1)",
    ],
    features: [
      {
        category: "Gateway and Routing",
        features: [
          { name: "OpenAI-compatible API", bonito: true, competitor: true },
          { name: "Multi-provider proxy", bonito: true, competitor: true },
          { name: "Intelligent routing (cost/latency/balanced/failover/AB)", bonito: true, competitor: "Basic fallbacks" },
          { name: "Auto cross-region inference (Bedrock)", bonito: true, competitor: false },
          { name: "Image + video generation on same key", bonito: true, competitor: false },
        ],
      },
      {
        category: "Enterprise Governance",
        features: [
          { name: "SSO/SAML (Okta, Azure AD, Google, Custom)", bonito: true, competitor: false },
          { name: "RBAC + multi-tenant org isolation", bonito: true, competitor: false },
          { name: "Immutable audit ledger across all surfaces", bonito: true, competitor: "Partial (logs only)" },
          { name: "Compliance posture (SOC-2 path, HIPAA, GDPR)", bonito: true, competitor: false },
          { name: "Tier-based log retention with org-partitioned sink", bonito: true, competitor: false },
        ],
      },
      {
        category: "Agents + RAG",
        features: [
          { name: "Governed agent framework with visual canvas", bonito: true, competitor: false },
          { name: "Default-deny tool policy + SSRF protection", bonito: true, competitor: false },
          { name: "RAG knowledge bases (pgvector HNSW)", bonito: true, competitor: false },
          { name: "Persistent agent memory + scheduled execution", bonito: true, competitor: false },
          { name: "Approval queue / human-in-the-loop", bonito: true, competitor: false },
        ],
      },
      {
        category: "Operating Model",
        features: [
          { name: "Managed SaaS (no self-hosting required)", bonito: true, competitor: "Hosted tier exists" },
          { name: "Self-hostable / open source", bonito: false, competitor: true },
          { name: "Enterprise contracts (MSA, DPA, BAA)", bonito: true, competitor: false },
          { name: "Production deployments today", bonito: true, competitor: true },
        ],
      },
    ],
    keywords: [
      "Bonito vs LiteLLM",
      "LiteLLM alternative",
      "managed LLM gateway",
      "enterprise AI control plane",
      "LLM proxy comparison",
      "multi-provider AI gateway",
      "OpenAI-compatible enterprise gateway",
      "LiteLLM hosted alternative",
      "AI governance platform",
      "enterprise AI agents",
    ],
  },
  {
    slug: "martian",
    name: "Martian",
    fullName: "Martian (withmartian)",
    tagline: "Model router vs. full enterprise AI control plane",
    description:
      "Martian is a model-routing company focused on routing requests to the cheapest or best-performing model for a given query. It is one feature in a broader control-plane stack. Bonito treats routing as one capability among many — pairing it with a governed agent framework, RAG knowledge bases, an immutable audit ledger, and compliance posture so an enterprise team gets the entire control plane in one platform.",
    metaTitle: "Bonito vs Martian — Routing Feature vs Full Control Plane",
    metaDescription:
      "Martian focuses on LLM model routing. Bonito is the enterprise AI control plane that bundles intelligent routing with governed agents, RAG knowledge bases, immutable audit ledger, SSO, cost intelligence, and compliance posture across OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq.",
    whatTheyDoWell: [
      "Focused router with model-quality and cost-aware switching",
      "Clear positioning on a single high-value gateway problem",
      "Developer-friendly integration model",
    ],
    whereBonitoGoesFurther: [
      "Routing is one of five strategies (cost/latency/balanced/failover/AB) inside a broader gateway",
      "Adds a governed agent framework: visual canvas, default-deny tool policy, budget stops, SSRF protection, audit trail",
      "Adds a RAG knowledge-base layer on pgvector HNSW with VectorBoost 3.9-8x compression",
      "Adds an immutable audit ledger across every surface (gateway, agents, KB, admin) — needed for compliance review",
      "Adds enterprise governance: SSO/SAML across 4 IdPs, RBAC, SOC-2 path, HIPAA, GDPR",
      "Adds cost intelligence with per-1K-token efficiency comparison and budget enforcement",
      "Adds image and video generation on the same gateway key",
    ],
    features: [
      {
        category: "Gateway and Routing",
        features: [
          { name: "Model routing (cost/latency/quality)", bonito: true, competitor: true },
          { name: "OpenAI-compatible API", bonito: true, competitor: true },
          { name: "Multi-provider failover", bonito: true, competitor: "Partial" },
          { name: "Auto cross-region inference (Bedrock)", bonito: true, competitor: false },
          { name: "A/B test routing strategy", bonito: true, competitor: "Partial" },
        ],
      },
      {
        category: "Agents + RAG",
        features: [
          { name: "Governed agent framework with visual canvas", bonito: true, competitor: false },
          { name: "RAG knowledge bases (pgvector HNSW)", bonito: true, competitor: false },
          { name: "Persistent agent memory + scheduled execution", bonito: true, competitor: false },
          { name: "Approval queue / human-in-the-loop", bonito: true, competitor: false },
          { name: "Image + video generation on same key", bonito: true, competitor: false },
        ],
      },
      {
        category: "Enterprise Governance",
        features: [
          { name: "SSO/SAML", bonito: true, competitor: false },
          { name: "Immutable audit ledger", bonito: true, competitor: false },
          { name: "Compliance posture (SOC-2 path, HIPAA, GDPR)", bonito: true, competitor: false },
          { name: "RBAC + multi-tenant org isolation", bonito: true, competitor: false },
          { name: "Cost intelligence (per-1K-token efficiency)", bonito: true, competitor: "Partial" },
        ],
      },
    ],
    keywords: [
      "Bonito vs Martian",
      "Martian alternative",
      "LLM router comparison",
      "AI routing platform",
      "enterprise AI gateway",
      "AI control plane",
      "multi-provider AI gateway",
      "AI cost optimization",
      "enterprise AI governance",
      "LLM gateway with agents",
    ],
  },
  {
    slug: "kong-ai-gateway",
    name: "Kong AI Gateway",
    fullName: "Kong AI Gateway (Kong Inc, NYSE: KONG)",
    tagline: "API-gateway incumbent extending into LLM vs. purpose-built AI control plane",
    description:
      "Kong is a public API-management incumbent that has extended into LLM with Kong AI Gateway. Its real distribution advantage is that thousands of enterprises already run Kong as a TCP/HTTP API gateway — adding AI routing is a low-friction expansion sale. Bonito is purpose-built for AI workloads from day one: agent framework, RAG, model-specific cost intelligence, and structural cloud-neutrality across the six AI providers that matter. Kong is great if your buyer already lives inside a Kong contract. Bonito is the answer if your AI control plane should be designed for AI, not retrofitted to it.",
    metaTitle: "Bonito vs Kong AI Gateway — Purpose-Built AI Control Plane vs API-Gateway Extension",
    metaDescription:
      "Kong AI Gateway extends Kong's API-management product into LLM workloads. Bonito is purpose-built for AI: governed agents, RAG knowledge bases, model-specific cost intelligence, immutable audit ledger, and structural cloud-neutrality across OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq.",
    whatTheyDoWell: [
      "Public-company distribution (NYSE: KONG) with thousands of existing enterprise contracts",
      "Mature API-management capabilities: rate limiting, request transformation, authentication plugins",
      "Trusted with traffic at network-infrastructure scale",
      "Open-source core with strong commercial extensions",
    ],
    whereBonitoGoesFurther: [
      "Purpose-built for AI workloads — not a TCP/HTTP gateway retrofitted into the AI surface",
      "Governed agent framework (Bonobot): visual canvas, default-deny tool policy, budget stops, persistent memory, scheduled execution, approval queue",
      "RAG knowledge bases on pgvector HNSW with VectorBoost 3.9-8x compression",
      "Model-specific cost intelligence: per-1K-token efficiency comparison across providers, real-time budget enforcement",
      "Immutable audit ledger purpose-designed for AI compliance review (every model call + agent run + KB query)",
      "Image and video generation on the same gateway key (Sora-2, Veo, dall-e, gpt-image-1) — not in Kong's surface",
      "Structurally cloud-neutral across the six AI providers customers actually use",
    ],
    features: [
      {
        category: "Gateway and Routing",
        features: [
          { name: "LLM gateway with multi-provider routing", bonito: true, competitor: true },
          { name: "Rate limiting + authentication", bonito: true, competitor: true },
          { name: "OpenAI-compatible API", bonito: true, competitor: "Partial" },
          { name: "Auto cross-region inference (Bedrock)", bonito: true, competitor: false },
          { name: "Image + video generation on same key", bonito: true, competitor: false },
        ],
      },
      {
        category: "Agents + RAG",
        features: [
          { name: "Governed agent framework with visual canvas", bonito: true, competitor: false },
          { name: "RAG knowledge bases (pgvector HNSW)", bonito: true, competitor: false },
          { name: "Persistent agent memory + scheduled execution", bonito: true, competitor: false },
          { name: "Approval queue / human-in-the-loop", bonito: true, competitor: false },
          { name: "Default-deny tool policy + SSRF protection", bonito: true, competitor: false },
        ],
      },
      {
        category: "Cost + Audit",
        features: [
          { name: "Per-1K-token efficiency comparison across providers", bonito: true, competitor: false },
          { name: "Real-time budget enforcement", bonito: true, competitor: "Partial" },
          { name: "Immutable audit ledger across all surfaces", bonito: true, competitor: "Partial" },
          { name: "Compliance posture (SOC-2 path, HIPAA, GDPR)", bonito: true, competitor: "Partial" },
        ],
      },
      {
        category: "Operating Model",
        features: [
          { name: "Purpose-built for AI workloads", bonito: true, competitor: false },
          { name: "Existing enterprise API-mgmt contracts", bonito: false, competitor: true },
          { name: "OSS core", bonito: false, competitor: true },
          { name: "Production AI deployments today", bonito: true, competitor: true },
        ],
      },
    ],
    keywords: [
      "Bonito vs Kong AI Gateway",
      "Kong AI Gateway alternative",
      "purpose-built AI control plane",
      "enterprise AI gateway comparison",
      "AI-native vs API-gateway extension",
      "multi-provider AI gateway",
      "enterprise AI agents",
      "AI compliance platform",
      "AI cost intelligence",
      "AI governance platform",
    ],
  },
  {
    slug: "apigee",
    name: "Apigee",
    fullName: "Apigee (Google Cloud)",
    tagline: "Single-cloud API management vs. structurally cloud-neutral AI control plane",
    description:
      "Apigee is Google Cloud's mature API-management platform with deep enterprise distribution and strong governance primitives. Its structural constraint: Apigee is Google-native by design — its incentive alignment with Google Cloud makes it structurally incapable of being a neutral position above the hyperscalers. Bonito sits above AWS Bedrock, Google Vertex AI, and Azure AI — by definition, no hyperscaler-owned product can occupy that position without breaking its own lock-in business model.",
    metaTitle: "Bonito vs Apigee — Structurally Cloud-Neutral AI Control Plane vs Single-Cloud API Management",
    metaDescription:
      "Apigee is Google Cloud's API-management platform extending into LLM workloads. Bonito is structurally cloud-neutral: gateway, routing, governance, audit, agents, and RAG across OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq — the only neutral position above the hyperscalers.",
    whatTheyDoWell: [
      "Deep enterprise distribution via Google Cloud sales motion",
      "Mature API lifecycle management with strong governance primitives",
      "Tight integration with Google Cloud security, IAM, and observability stack",
      "Strong fit for teams that already standardize on Google Cloud",
    ],
    whereBonitoGoesFurther: [
      "Structurally cloud-neutral: AWS Bedrock and Azure AI routed through the same gateway as Vertex AI — Apigee structurally cannot replicate this without conflicting with its parent business model",
      "Purpose-built AI surface: governed agent framework, RAG knowledge bases, model-specific cost intelligence",
      "Image and video generation on the same gateway key across OpenAI Sora-2, Vertex AI Veo, dall-e, and gpt-image-1",
      "Immutable audit ledger purpose-designed for AI compliance review (model calls, agent runs, KB queries)",
      "Direct routing across 6 AI providers — no per-cloud handoff, no Google-Cloud-by-default constraint",
      "Compliance posture covering SOC-2, HIPAA, GDPR, ISO27001 across AWS, Google, and Azure",
    ],
    features: [
      {
        category: "Structural Position",
        features: [
          { name: "Cloud-neutral by design", bonito: true, competitor: false },
          { name: "Routes across AWS Bedrock + Azure AI + Vertex", bonito: true, competitor: "Vertex-first" },
          { name: "Hyperscaler-aligned distribution", bonito: false, competitor: true },
        ],
      },
      {
        category: "AI-Specific Surface",
        features: [
          { name: "OpenAI-compatible API across 6 providers", bonito: true, competitor: "Partial" },
          { name: "Governed agent framework", bonito: true, competitor: false },
          { name: "RAG knowledge bases (pgvector HNSW)", bonito: true, competitor: false },
          { name: "Image + video generation on same key", bonito: true, competitor: false },
          { name: "Persistent agent memory + scheduled execution", bonito: true, competitor: false },
        ],
      },
      {
        category: "Governance",
        features: [
          { name: "SSO/SAML (Okta, Azure AD, Google, Custom)", bonito: true, competitor: true },
          { name: "Immutable audit ledger across all AI surfaces", bonito: true, competitor: "Partial" },
          { name: "Compliance posture (SOC-2 path, HIPAA, GDPR)", bonito: true, competitor: true },
          { name: "Per-1K-token efficiency comparison", bonito: true, competitor: false },
        ],
      },
    ],
    keywords: [
      "Bonito vs Apigee",
      "Apigee AI alternative",
      "cloud-neutral AI control plane",
      "multi-cloud AI gateway",
      "API management vs AI control plane",
      "enterprise AI governance",
      "Google Cloud AI alternative",
      "neutral AI gateway",
      "AI compliance platform",
      "enterprise AI agents",
    ],
  },
  {
    slug: "zuplo",
    name: "Zuplo",
    fullName: "Zuplo",
    tagline: "Developer-tier programmable API gateway vs. managed enterprise AI control plane",
    description:
      "Zuplo is a developer-focused programmable API gateway with strong edge-deployment ergonomics. Its sweet spot is teams that want to script their own request handling at the edge. Bonito is a managed enterprise AI control plane: purpose-built for AI workloads, with a governed agent framework, RAG, audit ledger, SSO, and compliance posture out of the box. Different target buyers, different shape.",
    metaTitle: "Bonito vs Zuplo — Managed Enterprise AI Control Plane vs Developer Edge Gateway",
    metaDescription:
      "Zuplo is a programmable developer API gateway. Bonito is a managed enterprise AI control plane: governed agents, RAG knowledge bases, immutable audit ledger, SSO, compliance posture, and structural cloud-neutrality across OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq.",
    whatTheyDoWell: [
      "Developer-first programmable gateway with strong edge ergonomics",
      "Clean TypeScript-based handler model",
      "Fast deployment story for individual developers",
      "Good fit for teams that want to script gateway logic themselves",
    ],
    whereBonitoGoesFurther: [
      "Managed enterprise control plane — not a self-scripted edge gateway",
      "Purpose-built AI surface: governed agents, RAG, audit ledger, per-1K-token cost intelligence",
      "SSO/SAML across Okta, Azure AD, Google Workspace, Custom SAML; RBAC; tier-based log retention",
      "Compliance posture: SOC-2 in flight, HIPAA, GDPR, ISO27001 governance checks across 3 clouds",
      "Image and video generation on the same gateway key (Sora-2, Veo, dall-e, gpt-image-1)",
      "Enterprise procurement: MSA, DPA, BAA available; pricing scales to dedicated infra",
    ],
    features: [
      {
        category: "Gateway and Routing",
        features: [
          { name: "OpenAI-compatible API", bonito: true, competitor: "Configurable" },
          { name: "Multi-provider routing", bonito: true, competitor: "Scripted" },
          { name: "Intelligent routing strategies (5)", bonito: true, competitor: false },
          { name: "Auto cross-region inference (Bedrock)", bonito: true, competitor: false },
          { name: "Image + video generation on same key", bonito: true, competitor: false },
        ],
      },
      {
        category: "Enterprise Surface",
        features: [
          { name: "Governed agent framework", bonito: true, competitor: false },
          { name: "RAG knowledge bases (pgvector HNSW)", bonito: true, competitor: false },
          { name: "SSO/SAML (Okta, Azure AD, Google, Custom)", bonito: true, competitor: "Partial" },
          { name: "Immutable audit ledger across all AI surfaces", bonito: true, competitor: false },
          { name: "Compliance posture (SOC-2 path, HIPAA, GDPR)", bonito: true, competitor: false },
        ],
      },
      {
        category: "Operating Model",
        features: [
          { name: "Managed control plane (no scripting required)", bonito: true, competitor: false },
          { name: "Self-scripted edge gateway", bonito: false, competitor: true },
          { name: "Enterprise contracts (MSA, DPA, BAA)", bonito: true, competitor: "Available" },
          { name: "Production AI deployments today", bonito: true, competitor: true },
        ],
      },
    ],
    keywords: [
      "Bonito vs Zuplo",
      "Zuplo alternative",
      "enterprise AI control plane",
      "managed AI gateway",
      "programmable AI gateway",
      "AI gateway comparison",
      "multi-provider AI gateway",
      "AI governance platform",
      "AI compliance gateway",
      "enterprise AI agents",
    ],
  },
];
