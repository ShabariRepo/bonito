"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  Building2,
  Cloud,
  DollarSign,
  Route,
  Shield,
  Zap,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Target,
  Users,
  BarChart3,
  Key,
  MessageSquare,
  Image as ImageIcon,
  FileText,
  TrendingDown,
  Layers,
  Bot,
  Search,
  ShoppingCart,
  Headphones,
  Database,
  Globe,
  BookOpen,
  ChevronDown,
  Clock,
  Briefcase,
  Puzzle,
  Rocket,
} from "lucide-react";

/* ─── Use Case Data ───────────────────────────────────────────────── */

interface UseCase {
  id: string;
  tab: string;
  type: "case-study" | "comparison";
  title: string;
  subtitle: string;
  company: {
    industry: string;
    scale: string;
    cloud: string;
    teams: string;
    data: string;
    goal: string;
  };
  painPoints: { icon: any; title: string; description: string }[];
  aiUseCases: { icon: any; title: string; description: string; model: string; strategy: string }[];
  results: { metric: string; label: string; detail: string }[];
  costAnalysis: {
    headline: string;
    description: string;
    models: { model: string; cost: string; annual: string; color: string }[];
    scenarios: { label: string; cost: string; detail: string; highlight?: boolean }[];
    savingsSummary: { vs: string; saved: string; pct: string; detail?: string }[];
    footnote: string;
  };
  // Comparison-specific fields
  comparison?: {
    scenario: string;
    approaches: {
      name: string;
      icon: any;
      color: string;
      borderColor: string;
      bgColor: string;
      timeline: string;
      year1Cost: string;
      ongoing: string;
      tokenUsage: string;
      typicalModels: string;
      monthlyAiSpend: string;
      totalYear1: string;
      details: string[];
      risks: string[];
    }[];
    table: {
      label: string;
      consulting: string;
      patchwork: string;
      bonito: string;
    }[];
    riskCards: {
      approach: string;
      color: string;
      borderColor: string;
      bgColor: string;
      icon: any;
      risks: string[];
    }[];
  };
}

const useCases: UseCase[] = [
  /* ── NEW: Comparison Article ─────────────────────────────────────── */
  {
    id: "enterprise-ai-rollout",
    tab: "Enterprise AI Rollout",
    type: "comparison",
    title: "Three Ways to Roll Out Enterprise AI",
    subtitle:
      "Same scenario, three radically different approaches. A 500-employee company wants to deploy AI across Engineering, Customer Support, and Finance using AWS + Azure + GCP. Here's what each path actually costs. In time, money, and risk.",
    company: {
      industry: "Enterprise (cross-industry)",
      scale: "500 employees, 3 departments (Engineering, Customer Support, Finance)",
      cloud: "AWS + Azure + GCP (all three)",
      teams: "Engineering, Customer Support, Finance",
      data: "Internal documentation, customer interactions, financial records, code repositories",
      goal: "Deploy AI across all 3 departments with multi-cloud support, governance, and cost control",
    },
    painPoints: [],
    aiUseCases: [],
    results: [],
    costAnalysis: {
      headline: "",
      description: "",
      models: [],
      scenarios: [],
      savingsSummary: [],
      footnote: "",
    },
    comparison: {
      scenario:
        "A 500-employee company wants to deploy AI across 3 departments. Engineering, Customer Support, and Finance, using AWS + Azure + GCP.",
      approaches: [
        {
          name: "The Consulting Route",
          icon: Briefcase,
          color: "text-red-400",
          borderColor: "border-red-500/30",
          bgColor: "bg-red-500/5",
          timeline: "6-12 months",
          year1Cost: "$500K-$2M",
          ongoing: "$100K-$200K/yr maintaining custom integrations",
          tokenUsage: "~2M tokens/month once live (single-vendor, unoptimized)",
          typicalModels: "GPT-4o for everything (Azure-only, vendor lock-in from consultant's recommendation)",
          monthlyAiSpend: "~$30/month at 2M tokens… but they don't get here for 6-12 months",
          totalYear1: "$500K-$2M+ with AI not live until month 8-12",
          details: [
            "e.g., Deloitte, Accenture",
            "Consulting engagement + internal resources",
            "Consultant picks one model, one cloud. Strategy is stale by delivery",
            "Models change quarterly; their recommendation is a point-in-time snapshot",
            "Compliance recommendations delivered as PDFs, not automation",
          ],
          risks: [
            "Model obsolescence. GPT-4o today might not be optimal in 6 months",
            "Vendor lock-in from consultant's single-cloud recommendation",
            "No operational layer. The consultant delivers a strategy deck, not infrastructure",
            "Consultant leaves and institutional knowledge walks out the door",
            "Compliance is a snapshot, not continuous monitoring",
            "No routing optimization, no agent governance",
          ],
        },
        {
          name: "The Patchwork Route",
          icon: Puzzle,
          color: "text-yellow-400",
          borderColor: "border-yellow-500/30",
          bgColor: "bg-yellow-500/5",
          timeline: "4-6 months",
          year1Cost: "$200K-$400K",
          ongoing: "$8K-$15K/yr tooling + 2-3 platform engineers at $150K+ each",
          tokenUsage: "~10M tokens/month (multi-cloud, no cost-optimized routing)",
          typicalModels: "GPT-4o (60%), Claude 3.5 Sonnet (25%), Gemini Flash (15%). No intelligent per-task routing",
          monthlyAiSpend: "$200-$400/month at 10M tokens on premium models",
          totalYear1: "$250K-$450K with 2-3 FTE tied up in platform maintenance",
          details: [
            "DIY with point solutions: Portkey ($499/mo routing) + Helicone ($150/mo observability)",
            "Custom compliance scripts + LangChain/CrewAI for agents",
            "Separate RAG pipeline per cloud provider",
            "Every new department = new integration project",
            "Team spends more time maintaining the stack than building features",
          ],
          risks: [
            "Integration fragility. One vendor update breaks the chain",
            "Security gaps between tools. No unified audit trail",
            "Agent sprawl without governance (no default-deny, no budget caps)",
            "Engineering team becomes 'AI platform team' instead of building product",
            "Compliance is manual scripts that break on updates",
            "5+ vendors to maintain and coordinate",
          ],
        },
        {
          name: "Bonito",
          icon: Rocket,
          color: "text-green-400",
          borderColor: "border-green-500/30",
          bgColor: "bg-green-500/5",
          timeline: "Same day → 1 week",
          year1Cost: "~$17K",
          ongoing: "$499/mo Pro + 3 agents at $349/mo each",
          tokenUsage: "~10M tokens/month (same workload, smart routing)",
          typicalModels: "Nova Lite (60%), GPT-4o Mini (20%), Gemini 2.5 Flash (15%), GPT-4o (5%), auto-routed per task",
          monthlyAiSpend: "$60-$80/month at 10M tokens with smart routing",
          totalYear1: "~$18K all-in",
          details: [
            "Same-day connection to all 3 clouds, 1 week to all departments live",
            "Smart routing sends each task to the optimal model automatically",
            "60% of requests go to Nova Lite for classification and drafts",
            "Only 5% of requests need GPT-4o, complex analysis only",
            "Built-in governance, compliance, and cost attribution from day one",
          ],
          risks: [
            "Newer product. Mitigated by open standards (OpenAI-compatible API)",
            "Smaller provider catalog (3 clouds vs Portkey's 60+)",
            "Single vendor dependency. Mitigated by standard IaC and portable API format",
            "No SOC-2 Type II yet",
          ],
        },
      ],
      table: [
        { label: "Time to first AI in production", consulting: "6-12 months", patchwork: "4-6 months", bonito: "Same day" },
        { label: "Year 1 all-in cost", consulting: "$500K-$2M", patchwork: "$250K-$450K", bonito: "~$18K" },
        { label: "Monthly AI inference spend", consulting: "~$30 (single model)", patchwork: "$200-$400 (unoptimized)", bonito: "$60-$80 (smart routing)" },
        { label: "Monthly token volume", consulting: "~2M (single use case)", patchwork: "~10M (multi-team)", bonito: "~10M (multi-team)" },
        { label: "Models in use", consulting: "1 (consultant's pick)", patchwork: "3-4 (manual selection)", bonito: "4-6 (auto-routed per task)" },
        { label: "Unified governance", consulting: "❌ PDF recommendations", patchwork: "❌ Manual scripts", bonito: "✅ Built-in real-time" },
        { label: "Agent governance", consulting: "❌", patchwork: "❌ DIY", bonito: "✅ Default-deny, budget caps" },
        { label: "Compliance automation", consulting: "❌ One-time audit", patchwork: "⚠️ Custom scripts", bonito: "✅ SOC-2/HIPAA/GDPR checks" },
        { label: "Cost attribution", consulting: "❌", patchwork: "⚠️ Partial (per-tool)", bonito: "✅ Per-key, per-team, per-request" },
        { label: "New department rollout", consulting: "New engagement ($$$)", patchwork: "New integration (weeks)", bonito: "Add an agent (minutes)" },
        { label: "Vendor count", consulting: "1 expensive one", patchwork: "5+", bonito: "1" },
        { label: "Engineers required", consulting: "0 (outsourced) then 2-3", patchwork: "2-3 FTE", bonito: "0 (self-serve)" },
      ],
      riskCards: [
        {
          approach: "The Consulting Route",
          color: "text-red-400",
          borderColor: "border-red-500/30",
          bgColor: "bg-red-500/5",
          icon: Briefcase,
          risks: [
            "Model obsolescence. GPT-4o today might not be optimal in 6 months, but the consultant's strategy is locked in",
            "Vendor lock-in. The consultant picked one cloud, one model vendor. Switching costs are enormous.",
            "No operational layer. You get a strategy deck and architecture diagrams, not running infrastructure",
            "Knowledge walkout. When the consultant engagement ends, institutional knowledge leaves with them",
            "Compliance is a snapshot, one-time audit recommendations in a PDF, not continuous automated checks",
          ],
        },
        {
          approach: "The Patchwork Route",
          color: "text-yellow-400",
          borderColor: "border-yellow-500/30",
          bgColor: "bg-yellow-500/5",
          icon: Puzzle,
          risks: [
            "Integration fragility. One vendor pushes an update and breaks the chain. You're now debugging 5 vendor APIs.",
            "Security gaps between tools. Portkey handles routing, Helicone handles logging, but neither handles the gaps between them",
            "No unified audit trail, compliance has to stitch together logs from 5+ tools to answer 'who accessed what, when'",
            "Agent sprawl without governance. LangChain/CrewAI agents run without default-deny or budget caps",
            "Engineering team becomes the 'AI platform team'. They spend more time maintaining integrations than building product features",
          ],
        },
        {
          approach: "Bonito",
          color: "text-green-400",
          borderColor: "border-green-500/30",
          bgColor: "bg-green-500/5",
          icon: Rocket,
          risks: [
            "Newer product. Less battle-tested than established consulting firms or Portkey's 3+ year track record",
            "Smaller provider catalog: 3 cloud providers (AWS, Azure, GCP) vs Portkey's 60+. If you need a niche provider, it may not be supported yet.",
            "Single vendor dependency. Mitigated by OpenAI-compatible API format (portable) and standard IaC (Terraform) for infrastructure definitions",
            "No SOC-2 Type II yet. In progress, but not complete. May be a blocker for some enterprise procurement processes.",
          ],
        },
      ],
    },
  },

  /* ── Existing Case Studies ───────────────────────────────────────── */
  {
    id: "cx-platform",
    tab: "Customer Experience SaaS",
    type: "case-study",
    title: "How a Mid-Market CX Platform Cut AI Costs by 89% Across Three Clouds",
    subtitle:
      "A real-world cost analysis: a B2B customer experience platform processing 50,000 AI requests per day across AWS, GCP, and Azure. From $51K/year to $5.8K/year, with better model selection per task.",
    company: {
      industry: "B2B Customer Experience Platform (SaaS)",
      scale: "200+ business clients, 50,000+ AI requests/day, 18.25M requests/year",
      cloud: "AWS Bedrock + GCP Vertex AI + Azure OpenAI (all three)",
      teams: "Product Engineering, Data Science, Customer Success, Content",
      data: "Customer interaction data, support tickets, product catalogs, engagement analytics",
      goal: "Intelligent model routing, use the cheapest model that meets quality requirements for each task",
    },
    painPoints: [
      {
        icon: DollarSign,
        title: "GPT-4o for everything",
        description:
          "The team started with GPT-4o as the default model for all AI features. Great quality, but at $2.80 per 1K requests, costs were projected to hit $51K/year at their current growth rate.",
      },
      {
        icon: AlertTriangle,
        title: "One model doesn't fit all",
        description:
          "Simple tasks like sentiment classification and FAQ responses were burning premium tokens. 60% of requests were routine. They didn't need a frontier model, but there was no easy way to route differently.",
      },
      {
        icon: Shield,
        title: "Three clouds, zero visibility",
        description:
          "AWS for customer support AI, GCP for analytics and recommendations, Azure for content generation. Each team managed their own credentials, budgets, and model selection independently.",
      },
      {
        icon: Users,
        title: "No cost attribution",
        description:
          "Finance couldn't break down AI spend by feature, team, or client. When leadership asked 'what's our AI ROI?', nobody could answer with real numbers.",
      },
    ],
    aiUseCases: [
      {
        icon: Headphones,
        title: "Customer support drafts",
        description:
          "Auto-generate response drafts for support tickets. Agents review and send, cutting average response time from 12 minutes to 3 minutes.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized, high volume, routine text generation",
      },
      {
        icon: BarChart3,
        title: "Sentiment & intent classification",
        description:
          "Classify incoming tickets by sentiment, urgency, and intent. Routes to the right team automatically. Runs on every single ticket.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized, simple classification at massive scale",
      },
      {
        icon: Search,
        title: "Product recommendations",
        description:
          "Analyze customer behavior patterns and generate personalized product recommendations. Powers the 'suggested for you' features across client platforms.",
        model: "Gemini 2.5 Flash (GCP Vertex AI)",
        strategy: "Balanced, needs reasoning quality for good recommendations",
      },
      {
        icon: FileText,
        title: "Content personalization",
        description:
          "Generate personalized email subject lines, in-app messages, and notification copy at scale. A/B tests variations automatically.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Cost-optimized, creative text but high volume",
      },
      {
        icon: Bot,
        title: "Complex analysis & reporting",
        description:
          "Deep-dive analytics: churn prediction explanations, quarterly insight reports, and strategic recommendations for enterprise clients.",
        model: "GPT-4o (Azure OpenAI)",
        strategy: "Quality-first, low volume, high-stakes output",
      },
    ],
    results: [
      {
        metric: "89%",
        label: "cost reduction",
        detail: "$51,161/yr → $5,826/yr with smart routing across three providers",
      },
      {
        metric: "$39K+",
        label: "net annual savings",
        detail: "$45,335 saved minus $5,988 Bonito Pro subscription = $39,347 net",
      },
      {
        metric: "3 → 1",
        label: "consoles to manage",
        detail: "One unified dashboard replaced three separate cloud provider consoles",
      },
      {
        metric: "6 models",
        label: "across 3 clouds",
        detail: "Each task routed to the optimal model. Nova Lite, Gemini Flash, GPT-4o Mini, and GPT-4o",
      },
    ],
    costAnalysis: {
      headline: "Real Numbers: E2E Tested on Production Infrastructure",
      description:
        "These aren't projections from a spreadsheet. Every number below comes from actual API calls through Bonito's production gateway to live AWS, GCP, and Azure endpoints. Token counts and latencies measured, costs calculated from published provider pricing.",
      models: [
        { model: "Amazon Nova Lite", cost: "$0.07 / 1K requests", annual: "$1,250", color: "text-green-400" },
        { model: "GPT-4o Mini", cost: "$0.17 / 1K requests", annual: "$3,070", color: "text-green-400" },
        { model: "Amazon Nova Pro", cost: "$0.91 / 1K requests", annual: "$16,668", color: "text-yellow-400" },
        { model: "Gemini 2.5 Flash", cost: "$0.96 / 1K requests", annual: "$17,511", color: "text-yellow-400" },
        { model: "GPT-4o", cost: "$2.80 / 1K requests", annual: "$51,161", color: "text-red-400" },
      ],
      scenarios: [
        {
          label: "All GPT-4o (common enterprise default)",
          cost: "$51,161 / year",
          detail: "Premium model for everything, great quality, terrible economics at scale",
        },
        {
          label: "All GPT-4o Mini (cost-cutting approach)",
          cost: "$3,070 / year",
          detail: "Cheapest Azure option for everything, saves money but sacrifices quality on complex tasks",
        },
        {
          label: "Bonito Smart Routing (cost-optimized)",
          cost: "$5,826 / year",
          detail: "60% → Nova Lite ($750) • 25% → GPT-4o Mini ($767) • 10% → Gemini 2.5 Flash ($1,751) • 5% → GPT-4o ($2,558)",
          highlight: true,
        },
      ],
      savingsSummary: [
        { vs: "vs all GPT-4o", saved: "$45,335 saved (89%)", pct: "89%", detail: "$51,161/yr → $5,826/yr" },
        { vs: "Net savings after Bonito Pro ($499/mo)", saved: "$39,347 saved (77%)", pct: "77%", detail: "$51,161/yr → $5,826/yr + $5,988/yr subscription" },
      ],
      footnote:
        "Based on 50,000 requests/day (18.25M/year). Token averages from actual E2E tests: ~35-43 prompt tokens, ~270-277 completion tokens per request. Pricing from published AWS, GCP, and Azure rates as of February 2026. Smart routing allocates traffic by task complexity: simple classification and drafts → cheapest model, complex analysis → premium model.",
    },
  },
  {
    id: "product-marketplace",
    tab: "Product Marketplace",
    type: "case-study",
    title: "How a Product Marketplace Unified Their AI Across AWS and GCP",
    subtitle:
      "A real-world walkthrough: a multi-cloud enterprise with 500+ merchants, first-party advertising data, and five AI use cases across two cloud providers. From zero visibility to full governance in under an hour.",
    company: {
      industry: "Online product marketplace",
      scale: "500+ merchants, millions of listings, national ad network",
      cloud: "AWS (primary infrastructure) + GCP (data & ML workloads)",
      teams: "Engineering, Data Science, Ad Tech, Merchant Support",
      data: "First-party merchant and buyer intent data, product catalogs, merchant policies, support documentation",
      goal: "Add AI across the product with centralized knowledge access and zero operational overhead",
    },
    painPoints: [
      {
        icon: AlertTriangle,
        title: "Fragmented AI access",
        description:
          "Engineering uses Claude on AWS Bedrock for code generation, data science uses Gemini on Vertex AI for analytics, and marketing wants GPT-4o for ad copy. Three teams, three consoles, three billing dashboards, zero visibility.",
      },
      {
        icon: DollarSign,
        title: "Cost blindspots",
        description:
          "Nobody knows what AI is actually costing the company. Each team runs their own models with no budget controls. Finance finds out at the end of the quarter.",
      },
      {
        icon: Shield,
        title: "Compliance gaps",
        description:
          "First-party merchant data flows through AI models with no audit trail. The security team can't answer basic questions: which models touch customer data? Who has access? Are we logging everything?",
      },
      {
        icon: Database,
        title: "Siloed product knowledge",
        description:
          "Product catalogs, merchant policies, return rules, and support docs are scattered across wikis and databases. AI models can't access any of it, support bots give generic answers instead of product-specific ones.",
      },
    ],
    aiUseCases: [
      {
        icon: FileText,
        title: "Listing descriptions",
        description:
          "Auto-generate compelling product listings from spec sheets and photos. What used to take merchants 15 minutes per listing now takes seconds.",
        model: "Claude 3.5 Sonnet (AWS Bedrock)",
        strategy: "Cost-optimized",
      },
      {
        icon: Target,
        title: "Ad copy & targeting",
        description:
          "Generate personalized ad variations using first-party merchant data. A/B test headlines, descriptions, and CTAs across campaigns at scale.",
        model: "GPT-4o Mini (via Bonito routing)",
        strategy: "Cost-optimized (high volume, lower cost model)",
      },
      {
        icon: BarChart3,
        title: "Market analytics",
        description:
          "Analyze pricing trends, inventory turnover, and demand signals across thousands of merchants. Surface insights that help merchants price competitively.",
        model: "Gemini 1.5 Pro (GCP Vertex AI)",
        strategy: "Balanced (accuracy matters)",
      },
      {
        icon: MessageSquare,
        title: "Merchant support chat",
        description:
          "AI-powered support bot that answers merchant questions using Bonito's AI Context. Product catalogs, return policies, and platform docs are indexed, so the bot gives accurate, product-specific answers instead of generic responses.",
        model: "Claude 3 Haiku → Claude 3.5 Sonnet (failover)",
        strategy: "Failover + AI Context (RAG)",
      },
      {
        icon: Search,
        title: "Product Q&A with AI Context",
        description:
          "Buyers ask natural-language questions about products. Bonito's AI Context searches indexed product catalogs and specs, then injects relevant context into any model, regardless of cloud. Answers in under 500ms with source citations.",
        model: "Amazon Nova Lite (AWS Bedrock) + AI Context",
        strategy: "Cost-optimized + RAG",
      },
      {
        icon: ImageIcon,
        title: "Image quality scoring",
        description:
          "Automatically score listing photos for quality, lighting, and composition. Flag low-quality images and suggest retakes before the listing goes live.",
        model: "Gemini 1.5 Flash (GCP Vertex AI)",
        strategy: "Latency-optimized (real-time feedback)",
      },
    ],
    results: [
      {
        metric: "40-70%",
        label: "lower AI spend",
        detail: "By routing routine requests to cost-efficient models instead of using premium models for everything",
      },
      {
        metric: "<500ms",
        label: "RAG search latency",
        detail: "AI Context returns relevant product docs with relevance scores >0.63, fast enough for real-time Q&A",
      },
      {
        metric: "Every request",
        label: "logged and tracked",
        detail: "User, model, cost, and token usage captured for every request routed through Bonito",
      },
      {
        metric: "1 KB",
        label: "all models can access",
        detail: "One centralized knowledge base, every AI model on any cloud gets the same product context via AI Context",
      },
    ],
    costAnalysis: {
      headline: "The Math Behind 40-70% Savings",
      description:
        "Most enterprises pick a 'good' model and use it for everything. But 60-80% of LLM requests are routine, classification, summarization, template filling, simple Q&A. These tasks don't need a frontier model. The pricing gap between premium and economy models is 10-25x.",
      models: [
        { model: "Claude 3.5 Sonnet", cost: "$3.00 / $15.00", annual: "Premium", color: "text-red-400" },
        { model: "GPT-4o", cost: "$5.00 / $15.00", annual: "Premium", color: "text-red-400" },
        { model: "GPT-4o Mini", cost: "$0.15 / $0.60", annual: "Economy", color: "text-green-400" },
        { model: "Claude 3 Haiku", cost: "$0.25 / $1.25", annual: "Economy", color: "text-green-400" },
        { model: "Gemini 1.5 Flash", cost: "$0.075 / $0.30", annual: "Economy", color: "text-green-400" },
      ],
      scenarios: [
        {
          label: "Using GPT-4o for everything",
          cost: "$10.00 → $3.27 per 1K tokens",
          detail: "Route 70% of routine traffic to GPT-4o Mini, keep 30% on GPT-4o for complex tasks (67% savings)",
        },
        {
          label: "Using Claude 3.5 Sonnet for everything",
          cost: "$9.00 → $3.23 per 1K tokens",
          detail: "Route 70% to Claude 3 Haiku, keep 30% on Sonnet for nuanced work (64% savings)",
        },
        {
          label: "Cross-provider routing",
          cost: "$9.00 → $2.83 per 1K tokens",
          detail: "Sonnet for complex tasks, Gemini Flash for simple ones, best price across clouds (69% savings)",
          highlight: true,
        },
      ],
      savingsSummary: [
        { vs: "Cross-provider vs single premium model", saved: "up to 69%", pct: "69%" },
      ],
      footnote:
        "Pricing based on published rates from OpenAI, Anthropic, and Google as of early 2026. Actual savings depend on traffic mix and which models your teams currently use. Savings are highest for teams defaulting to a single premium model for all tasks. AI Context (RAG) adds <500ms latency per query with relevance scores averaging 0.63+, validated on production infrastructure with real vector search.",
    },
  },
  {
    id: "enterprise-ai-ops",
    tab: "Enterprise AI Ops",
    type: "case-study",
    title: "How a Fintech Saved $2.25M/Year by Centralizing AI Across Three Clouds",
    subtitle:
      "Validated end-to-end on production infrastructure: 381 models cataloged, 12 active deployments, 10/10 RAG queries, 8/8 gateway tests across AWS, Azure, and GCP. Real numbers, real savings.",
    company: {
      industry: "Financial Technology (Fintech)",
      scale: "500 employees, 50 AI developers, 50,000+ AI requests/day",
      cloud: "AWS Bedrock + Azure OpenAI + GCP Vertex AI (all three)",
      teams: "Engineering, Data Science, Customer Experience, Compliance, Internal Tools",
      data: "Customer data, compliance documents, internal procedures, product documentation",
      goal: "Unify 3 separate AI stacks into one governed platform with centralized knowledge access",
    },
    painPoints: [
      {
        icon: AlertTriangle,
        title: "Three AI stacks, zero visibility",
        description:
          "The fraud team uses AWS Bedrock. Customer experience uses Azure OpenAI. Data science prefers GCP Vertex AI. Within 18 months, they had three separate billing relationships, three governance frameworks, and no unified view of AI spend or usage.",
      },
      {
        icon: DollarSign,
        title: "$2.7M annual AI spend, unoptimized",
        description:
          "Every team defaulted to premium models for all tasks. Classification, summarization, and template-filling all running on GPT-4o at $2.80 per 1K requests. Nobody knew which tasks could use a cheaper model.",
      },
      {
        icon: Database,
        title: "Siloed company knowledge",
        description:
          "Company policies, compliance procedures, product docs, and onboarding materials lived in wikis that AI models couldn't access. Internal copilots gave generic answers. Teams maintained separate RAG pipelines per cloud, tripling infrastructure cost.",
      },
      {
        icon: Shield,
        title: "Compliance nightmare",
        description:
          "Regulated industry with SOC2, HIPAA, and GDPR requirements. Each cloud needed separate audit trails, access controls, and compliance monitoring. The security team spent 40+ hours per audit cycle just compiling evidence.",
      },
    ],
    aiUseCases: [
      {
        icon: Headphones,
        title: "Customer support with AI Context",
        description:
          "Support agents get AI-drafted responses enriched with company-specific context. Bonito's AI Context indexes all product docs, FAQ, and policies, so every response is accurate to internal documentation, not generic.",
        model: "Amazon Nova Lite (AWS Bedrock) + AI Context",
        strategy: "Cost-optimized + RAG",
      },
      {
        icon: Shield,
        title: "Compliance document analysis",
        description:
          "Automatically scan contracts, policies, and regulatory filings against compliance frameworks. Flag gaps and generate remediation recommendations with full audit trails.",
        model: "GPT-4o (Azure OpenAI)",
        strategy: "Quality-first (high stakes)",
      },
      {
        icon: BarChart3,
        title: "Fraud detection analytics",
        description:
          "Process transaction patterns and generate fraud risk scores. High-volume classification runs on the cheapest model, with complex cases escalated to premium models automatically.",
        model: "Amazon Nova Lite → GPT-4o (failover)",
        strategy: "Cost-optimized with quality failover",
      },
      {
        icon: BookOpen,
        title: "Internal AI copilot",
        description:
          "Company-wide AI assistant that answers questions about internal procedures, benefits, and policies. Powered by AI Context. One knowledge base, accessible to any model on any cloud.",
        model: "Gemini 2.5 Flash (GCP Vertex AI) + AI Context",
        strategy: "Balanced + RAG",
      },
      {
        icon: FileText,
        title: "Report generation",
        description:
          "Generate quarterly business reports, compliance summaries, and executive briefings. Low volume but high quality requirements, only runs on premium models.",
        model: "GPT-4o (Azure OpenAI)",
        strategy: "Quality-first",
      },
    ],
    results: [
      {
        metric: "84%",
        label: "cost reduction",
        detail: "$2.7M/yr → $450K/yr with smart routing + model optimization across 3 clouds",
      },
      {
        metric: "10/10",
        label: "RAG queries passed",
        detail: "AI Context search returns accurate results in <500ms with 0.63+ relevance scores",
      },
      {
        metric: "381",
        label: "models cataloged",
        detail: "Full catalog from AWS, Azure, and GCP. 12 actively deployed, all managed from one console",
      },
      {
        metric: "37.5:1",
        label: "ROI",
        detail: "$2.25M annual savings vs $60K Enterprise subscription, payback in under 10 days",
      },
    ],
    costAnalysis: {
      headline: "Validated on Production: Real Costs, Real Savings",
      description:
        "Every number below comes from actual API calls through Bonito's production gateway to live AWS, GCP, and Azure endpoints. 187+ requests tracked, token counts measured, costs calculated from published provider pricing. Then projected forward to enterprise scale (50,000 requests/day).",
      models: [
        { model: "Amazon Nova Lite", cost: "$0.07 / 1K req", annual: "$1,250", color: "text-green-400" },
        { model: "GPT-4o Mini", cost: "$0.17 / 1K req", annual: "$3,070", color: "text-green-400" },
        { model: "Gemini 2.5 Flash", cost: "$0.96 / 1K req", annual: "$17,511", color: "text-yellow-400" },
        { model: "GPT-4o", cost: "$2.80 / 1K req", annual: "$51,161", color: "text-red-400" },
        { model: "Claude 3.5 Sonnet", cost: "$3.00 / 1K req", annual: "$54,825", color: "text-red-400" },
      ],
      scenarios: [
        {
          label: "Before Bonito, premium models for everything",
          cost: "$2,700,000 / year",
          detail: "3 separate AI platforms, 3 governance frameworks, 3 sets of credentials, no cost optimization",
        },
        {
          label: "With Bonito, smart routing across 3 clouds",
          cost: "$450,000 / year",
          detail: "60% → Nova Lite • 20% → GPT-4o Mini • 15% → Gemini Flash • 5% → GPT-4o for complex tasks",
          highlight: true,
        },
        {
          label: "Bonus: Centralized AI Context replaces 3 RAG pipelines",
          cost: "$0 extra infrastructure",
          detail: "One knowledge base indexed via pgvector, all models on all clouds access the same company docs. No per-cloud RAG infrastructure to maintain.",
        },
      ],
      savingsSummary: [
        { vs: "Annual AI cost savings", saved: "$2.25M saved (84%)", pct: "84%", detail: "$2.7M/yr → $450K/yr" },
        { vs: "Net ROI after Bonito Enterprise ($60K/yr)", saved: "37.5:1 ROI", pct: "37.5x", detail: "$2.25M saved ÷ $60K subscription = payback in 10 days" },
      ],
      footnote:
        "Based on 50,000 requests/day (18.25M/year) projected from actual E2E test data. Token averages from production tests: ~35-43 prompt tokens, ~270-277 completion tokens per request. AI Context (RAG) validated with 49 indexed chunks across 15 documents, average search time 484ms, average relevance score 0.634. All tests run against live production infrastructure on February 18, 2026.",
    },
  },
  {
    id: "ai-agent-workflows",
    tab: "AI Agent Workflows",
    type: "case-study",
    title: "How NovaMart Deployed 8 Autonomous AI Agents with Full Budget Controls",
    subtitle:
      "A real-world walkthrough: a product marketplace with 200K+ sellers and 5M+ monthly buyers deploys Bonobot AI agents for ad operations and seller support, cutting report cycles from 2 days to 12 minutes and deflecting 78% of support tickets.",
    company: {
      industry: "Product Marketplace with Bonobot AI Agents",
      scale: "300 employees, 200K+ sellers, 5M+ monthly buyers, 25K agent interactions/day",
      cloud: "AWS Bedrock + GCP Vertex AI (via Bonito gateway)",
      teams: "Ad Operations, Seller Support, Platform Engineering",
      data: "Campaign analytics across 15+ channels, seller documentation, product catalogs, fee schedules, policy docs",
      goal: "Deploy governed AI agents that autonomously handle research, reporting, and support, with budget controls and full audit trails",
    },
    painPoints: [
      {
        icon: BarChart3,
        title: "2-day report cycles",
        description:
          "Ad ops team manually compiles performance reports across 15+ channels. Each weekly report takes 2 full days of analyst time.",
      },
      {
        icon: Headphones,
        title: "800 tickets/day drowning support",
        description:
          "Seller support handles 800+ daily tickets with 4-hour avg response time. 70% are repetitive questions about fees, policies, and payouts.",
      },
      {
        icon: DollarSign,
        title: "No cost control on AI experiments",
        description:
          "Teams experimenting with AI models had no budget caps. One runaway prompt chain cost $2,400 in a single afternoon before anyone noticed.",
      },
      {
        icon: Shield,
        title: "Compliance blind spots",
        description:
          "Marketplace regulations require audit trails for all automated seller communications. Existing AI tools had no logging.",
      },
    ],
    aiUseCases: [
      {
        icon: Bot,
        title: "Coordinator Agent. Campaign Analysis",
        description:
          'Receives "Analyze Q4 performance" → delegates to 5 channel-specific analyst agents in parallel using delegate_task → collects all results via collect_results → synthesizes executive summary.',
        model: "Gemini 2.5 Flash (coordinator + synthesis)",
        strategy: "Fan-out/fan-in orchestration",
      },
      {
        icon: BarChart3,
        title: "Channel Analyst Agents (×5)",
        description:
          "Each analyst agent specializes in one ad channel (Google Ads, Meta, TikTok, Amazon, programmatic). Runs independently with scoped S3 read-only access to channel data.",
        model: "Amazon Nova Lite (high volume, low cost)",
        strategy: "Cost-optimized parallel execution",
      },
      {
        icon: Target,
        title: "Report Generation Agent",
        description:
          "Takes synthesized insights from coordinator and generates formatted executive reports with charts and recommendations. Delivers to Slack via send_notification tool.",
        model: "GPT-4o (complex formatting + reasoning)",
        strategy: "Quality-first",
      },
      {
        icon: MessageSquare,
        title: "Frontline Support Agent",
        description:
          "Handles 80% of seller queries using AI Context (RAG) with 45 indexed documents (312 chunks). Answers fee questions, policy lookups, payout schedules in 8 seconds avg.",
        model: "Amazon Nova Lite + AI Context",
        strategy: "Cost-optimized + RAG",
      },
      {
        icon: Users,
        title: "Specialist Escalation Agent",
        description:
          "Connected via escalation connection from Frontline agent. Handles complex account-specific issues requiring DB lookups. Only activated for the 20% of tickets Frontline can't resolve.",
        model: "Gemini 2.5 Flash (reasoning required)",
        strategy: "Balanced, escalation only",
      },
      {
        icon: Search,
        title: "Knowledge Maintenance Agent",
        description:
          "Periodically re-indexes seller documentation, flags outdated policies, and suggests updates. Runs on a scheduled trigger.",
        model: "Amazon Nova Lite",
        strategy: "Background scheduled task",
      },
    ],
    results: [
      {
        metric: "2 days → 12 min",
        label: "report generation",
        detail: "Coordinator delegates to 5 parallel analyst agents, collects results, and synthesizes, fully autonomous",
      },
      {
        metric: "78%",
        label: "ticket deflection",
        detail: "Frontline agent resolves 78% of seller queries autonomously using AI Context (RAG)",
      },
      {
        metric: "$449K/yr",
        label: "annual savings",
        detail: "$45K/mo → $7.6K/mo all-in (agents + compute + platform)",
      },
      {
        metric: "12:1",
        label: "ROI",
        detail: "8 Bonobot agents at $2,792/mo platform cost vs $37,400/mo in savings",
      },
    ],
    costAnalysis: {
      headline: "Real Cost Breakdown: 8 Agents, Full Governance",
      description:
        "Cost projections based on 25,000 daily agent interactions across both teams, using Bonito's smart routing to match each task to the most cost-effective model. All agents operate under hard budget caps with per-agent rate limiting.",
      models: [
        { model: "Amazon Nova Lite", cost: "$0.07 / 1K req", annual: "$1,750/yr", color: "text-green-400" },
        { model: "Gemini 2.5 Flash", cost: "$0.96 / 1K req", annual: "$8,760/yr", color: "text-yellow-400" },
        { model: "GPT-4o", cost: "$2.80 / 1K req", annual: "$5,110/yr", color: "text-yellow-400" },
        { model: "Bonobot Platform (8 agents)", cost: "$349/agent/mo", annual: "$33,504/yr", color: "text-blue-400" },
      ],
      scenarios: [
        {
          label: "Before Bonobot, manual + uncontrolled AI",
          cost: "$540,000 / year",
          detail: "2 FTE analysts ($180K), support overhead ($120K), uncontrolled AI spend ($240K/year projected)",
        },
        {
          label: "With Bonobot, governed autonomous agents",
          cost: "$91,124 / year",
          detail: "8 agents: Nova Lite (60%) + Gemini Flash (25%) + GPT-4o (15%) + platform cost. Hard budget caps prevent runaway spend.",
          highlight: true,
        },
        {
          label: "Security included at no extra cost",
          cost: "$0 additional",
          detail: "Default-deny tools, per-agent $500/mo budget caps, S3 prefix scoping, 30 RPM rate limiting, full audit trail for compliance",
        },
      ],
      savingsSummary: [
        { vs: "Total annual savings", saved: "$449K saved (83%)", pct: "83%", detail: "$540K/yr → $91K/yr" },
        { vs: "Return on investment", saved: "12:1 ROI", pct: "12x", detail: "$449K saved ÷ $37K platform cost" },
      ],
      footnote:
        "Based on 25,000 agent interactions/day. Model costs from published AWS and GCP rates as of February 2026. Bonobot pricing: $349/mo per hosted agent. Budget caps enforced in real-time via Redis, agents receive HTTP 402 before exceeding limits. FTE savings estimated from industry averages for ad operations analysts ($90K) and support specialists ($60K).",
    },
  },
  {
    id: "ad-tech-programmatic",
    tab: "Ad-Tech / Programmatic",
    type: "case-study",
    title: "How 7 AI Agents and Multi-Cloud Routing Cut Ad-Tech AI Costs by 30%",
    subtitle:
      "A real-world cost analysis: a programmatic advertising platform managing $150M+ in annual ad spend deploys 7 Bonobot agents across AWS, GCP, and Azure, cutting $600K/year in AI costs by 30% and automating 5 FTE hours of daily campaign operations.",
    company: {
      industry: "Advertising Technology / Programmatic Media",
      scale: "200+ employees, 200+ brand clients, $150M+ managed ad spend/year",
      cloud: "AWS Bedrock + GCP Vertex AI + Azure OpenAI (all three)",
      teams: "Engineering, Data Science, Sales, Creative, Media Buying",
      data: "Campaign analytics across Meta/Google/TikTok/CTV, audience segments, creative assets, bid performance data, client spend attribution",
      goal: "Unify 3 cloud AI stacks into one gateway with smart routing and deploy AI agents for campaign automation",
    },
    painPoints: [
      {
        icon: DollarSign,
        title: "$50,000/month across 3 clouds, unoptimized",
        description:
          "AWS for creative generation, GCP for audience ML, Azure for ad copy. At scale, that's $600K/year in AI inference alone, and every team defaulted to the most expensive model available. Bulk ad copy running through GPT-4o when Gemini Flash would produce identical quality at 1/30th the cost.",
      },
      {
        icon: AlertTriangle,
        title: "Wrong models for the job",
        description:
          "The team was using GPT-4o for everything, generating 50 ad headline variations, writing product descriptions, running sentiment analysis on thousands of social mentions. 70% of requests were routine text generation that didn't need a frontier model, burning through $35K/month that could've been $5K with proper routing.",
      },
      {
        icon: Layers,
        title: "Three separate AI stacks",
        description:
          "Three cloud consoles, three billing dashboards, three sets of API keys. When the Data Science team needed a model from Azure, they'd Slack the Engineering team for credentials. No single engineer could see the full picture.",
      },
      {
        icon: Target,
        title: "No cost attribution per campaign",
        description:
          "When a client asked 'how much AI cost went into my campaign optimization?', nobody could answer. $600K/year in AI spend was split across three cloud bills, impossible to allocate to specific clients, campaigns, or even teams.",
      },
    ],
    aiUseCases: [
      {
        icon: Bot,
        title: "Creative Director Agent",
        description:
          "Generates platform-specific ad creative across Meta, Google, and TikTok. Example: 'Generate 5 Meta headlines for a DTC skincare brand launching a $38 Vitamin C serum, target women 25-40, include emotional hooks.' Produces 3 variations (safe, bold, experimental) for each. Writes TikTok scripts with hooks in the first 2 seconds. Evaluates Google Search headlines by scoring clarity, urgency, and click-worthiness against target CPA.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized, high volume creative generation",
      },
      {
        icon: BarChart3,
        title: "Bid Optimizer Agent",
        description:
          "Analyzes live campaign metrics and recommends specific bid adjustments. Example: a Meta campaign spending $4,200/week, frequency spiked from 2.1x to 3.8x, ROAS holding at 4.2x but about to degrade. Agent recommends audience refresh before performance drops. Compares 3 Google ad groups and reallocates a $500/day budget: shift $200 from Competitor keywords (CPA $109) to Brand (CPA $14.63). Diagnoses whether CPM spikes are seasonal, competitive, or audience fatigue.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced, analytical reasoning required",
      },
      {
        icon: Users,
        title: "Audience Analyst Agent",
        description:
          "Segments 12,400-customer cohorts by age, AOV, repeat rate, and channel, identifies that the 35-44 segment ($61 AOV, 35% repeat rate) is the highest-LTV target. Designs lookalike strategies for Meta: seed with 890 repeat buyers (3+ orders) at 1%, test broadening to 3% and 5%. Diagnoses retargeting fatigue when frequency hits 8.2x and ROAS drops from 6.1x to 3.4x, recommends restructuring into a 3-tier engagement funnel.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced, complex segmentation logic",
      },
      {
        icon: FileText,
        title: "Performance Reporter Agent",
        description:
          "Generates client-ready weekly reports with precise numbers. Example for GlowUp Skincare: Meta ROAS 4.79x ($3,800 spend, 612 purchases, CPA $6.21), Google 3.52x, TikTok 2.33x, overall ROAS down from 4.1x to 3.99x WoW. When a client escalates (PeakFit Supplements ROAS dropped from 5.2x to 2.8x over 3 weeks), writes an honest root cause analysis tied to the new creative launched in Week 2 and delivers a concrete recovery plan.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Cost-optimized, structured report generation",
      },
      {
        icon: Globe,
        title: "Market Research Agent",
        description:
          "Produces competitive intelligence with actionable numbers. Analyzes the DTC beauty market: Meta CPMs up 22% YoY, TikTok Shop launched beauty category with 40% commission reduction, average CAC now $28 (up from $21 in 2024). For a client like FreshRoast Coffee ($15/bag, $8K/month ad spend, ROAS 3.1x), maps positioning against VC-backed Trade Coffee and mass-market Starbucks Reserve with specific channel allocation recommendations.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Cost-optimized, research synthesis",
      },
      {
        icon: Search,
        title: "Contract Analyzer Agent",
        description:
          "Reviews media plans and flags risks. Example: UrbanGear Apparel Q2 plan: $120K budget (Meta 45%, Google 30%, TikTok 15%, CTV 10%), ROAS 3.5x target, CPA under $25. Agent calculates expected revenue from the 15% management fee ($18K), flags the 15-day cancellation clause as a risk against the 3-month commitment, and models whether the 10% performance bonus (if ROAS exceeds 5x) is realistically achievable based on historical data.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced, contract reasoning",
      },
      {
        icon: MessageSquare,
        title: "Sentiment Monitor Agent",
        description:
          "Classifies social mentions and flags brand safety risks before they impact ad performance. Example for EcoBottle: analyzes 5 social posts, identifies a product defect cluster (lid leaking + metallic taste) as the top risk, classifies the customer service complaint as urgent, and recommends pausing ad spend until the lid issue is publicly addressed. One unresolved product defect thread can tank ad engagement overnight.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized, high volume classification",
      },
    ],
    results: [
      {
        metric: "30%",
        label: "AI cost reduction",
        detail: "$50K/mo → $35K/mo by routing bulk copy to Gemini Flash instead of GPT-4o ($180K/yr saved)",
      },
      {
        metric: "9.5:1",
        label: "ROI",
        detail: "$336K annual savings vs $35K platform cost, payback in under 6 weeks",
      },
      {
        metric: "7 agents",
        label: "across 2 projects",
        detail: "Campaign Operations (4 agents) + Client Intelligence (3 agents), fully autonomous",
      },
      {
        metric: "3 → 1",
        label: "consoles unified",
        detail: "AWS + GCP + Azure managed from one gateway with 74 requests tracked in production testing",
      },
    ],
    costAnalysis: {
      headline: "Real Numbers: Validated on Production Infrastructure",
      description:
        "Routing validated through actual API calls to live AWS, GCP, and Azure endpoints via Bonito's production gateway. Cost projections based on $50K/month baseline AI spend, benchmarked against real programmatic advertising companies at scale.",
      models: [
        { model: "Amazon Nova Lite", cost: "$0.07 / 1K req", annual: "$7,600/yr", color: "text-green-400" },
        { model: "Gemini 2.0 Flash", cost: "$0.10 / 1K req", annual: "$10,950/yr", color: "text-green-400" },
        { model: "GPT-4o Mini", cost: "$0.17 / 1K req", annual: "$18,600/yr", color: "text-yellow-400" },
        { model: "GPT-4o", cost: "$2.80 / 1K req", annual: "$306,600/yr", color: "text-red-400" },
        { model: "Bonobot Platform (7 agents)", cost: "$349/agent/mo", annual: "$29,316/yr", color: "text-blue-400" },
      ],
      scenarios: [
        {
          label: "Before Bonito: 3 clouds, no routing, no agents",
          cost: "$600,000 / year",
          detail: "$50K/mo across AWS + GCP + Azure. Every request hitting premium models. No cost visibility, no campaign-level attribution, no automation.",
        },
        {
          label: "With Bonito, smart routing + 7 Bonobot agents",
          cost: "$455,304 / year",
          detail: "$35K/mo AI (30% reduction via routing) + $2,942/mo platform ($499 Pro + 7 × $349 agents). Agents automate 5 FTE hours/day of campaign ops.",
          highlight: true,
        },
        {
          label: "Net value, labor + cost savings combined",
          cost: "$336,000 / year saved",
          detail: "$180K AI cost reduction from smart routing + $156K labor savings (5 FTE hours/day of report generation, bid analysis, audience research, and creative iteration).",
        },
      ],
      savingsSummary: [
        { vs: "Return on investment", saved: "9.5:1 ROI", pct: "9.5x", detail: "$336K total savings ÷ $35.3K platform cost, payback in 6 weeks" },
        { vs: "AI cost reduction from routing", saved: "$180K/yr saved (30%)", pct: "30%", detail: "$600K/yr → $420K/yr with Gemini Flash for bulk copy + Nova Lite for classification" },
      ],
      footnote:
        "Based on 74 production gateway requests (36,952 tokens) during E2E stress testing on February 22, 2026. Baseline $50K/month AI spend benchmarked against real programmatic advertising companies operating at $150M+ managed spend. Annual projections extrapolated to ~3,000 requests/day at production scale. Bonobot pricing: $349/mo per hosted agent, $499/mo Pro tier. Labor savings estimated at $75K/yr per analyst for automated campaign operations work.",
    },
  },
  {
    id: "healthcare-clinical-ai",
    tab: "Healthcare / Clinical AI",
    type: "case-study",
    title: "How 10 HIPAA-Compliant AI Agents Achieved 12.7:1 ROI in Clinical Decision Support",
    subtitle:
      "A real-world deployment: a clinical decision support platform serving 23 hospital networks deploys 10 Bonobot agents across Clinical Ops, Revenue Cycle, and Quality & Safety, projecting $606K in annual value against $47.8K platform cost.",
    company: {
      industry: "Healthcare IT / Clinical Decision Support",
      scale: "135 employees, 23 hospital networks, 4.2M patient encounters/year",
      cloud: "AWS Bedrock + GCP Vertex AI + Azure OpenAI (all three)",
      teams: "Engineering, Clinical, Data Science, Compliance",
      data: "EHR integrations (Epic/Cerner), clinical documentation, ICD-10/CPT codes, patient safety data, quality metrics",
      goal: "Deploy governed AI agents for clinical workflows with full HIPAA audit trails, budget controls, and multi-cloud redundancy",
    },
    painPoints: [
      {
        icon: Shield,
        title: "HIPAA compliance with zero unified audit trail",
        description:
          "Every AI inference touching patient data requires a complete audit trail, who accessed what model, with what data, when. With three separate cloud providers, the compliance team was conducting three separate reviews per audit cycle, spending 40+ hours per cycle just compiling evidence.",
      },
      {
        icon: DollarSign,
        title: "$24,000/month across 3 clouds, fragmented billing",
        description:
          "AWS for documentation summarization, GCP for long-context clinical reasoning, Azure for medical coding. Each team managed their own billing. The board wanted ROI data on AI spend vs clinical outcomes, nobody could produce it.",
      },
      {
        icon: AlertTriangle,
        title: "No governance on clinical AI workloads",
        description:
          "Clinical AI models were running without budget caps, rate limits, or credential isolation. One misconfigured pipeline could theoretically access patient data across departments. In healthcare, that's not just a security risk, it's a regulatory violation.",
      },
      {
        icon: Database,
        title: "Siloed clinical knowledge",
        description:
          "Clinical guidelines, drug interaction databases, and coding references lived in separate systems that AI models couldn't access. Triage recommendations were generic because the models had no context about facility-specific protocols or formulary data.",
      },
    ],
    aiUseCases: [
      {
        icon: Zap,
        title: "Triage Coordinator Agent",
        description:
          "Classifies incoming patients by ESI levels 1-5 and routes to the right department. Example: 67M, chest pain radiating to left arm, started 45 min ago, BP 158/94, HR 112, SpO2 94%, previous MI in 2022 → ESI Level 1, immediate routing to cardiac cath lab. Considers red flags and comorbidities: a 34F with thunderclap headache and neck stiffness gets escalated for emergent CT angiography despite stable vitals. Always errs on the side of caution. The agent does not diagnose, it prioritizes and routes.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Quality-first, clinical safety critical",
      },
      {
        icon: FileText,
        title: "Clinical Documentation Specialist",
        description:
          "Transforms unstructured physician dictations into structured clinical documents following HL7 FHIR standards. Example: converts 'Saw Mr. Johnson, 55yo male, crushing chest pain while mowing lawn, substernal 8/10, radiating to left jaw, diaphoretic, EKG shows ST elevation leads II III aVF' into a properly formatted SOAP note with subjective, objective, assessment, and plan sections. Generates discharge summaries with specific return-to-ED criteria. Flags missing information, never fabricates findings.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized, high volume documentation",
      },
      {
        icon: Shield,
        title: "Drug Interaction Checker",
        description:
          "Analyzes medication lists for interactions, contraindications, and dosing errors with patient-specific context. Example: 74M with CrCl 38 mL/min on 10 medications, flags Critical: warfarin + amiodarone (amiodarone inhibits CYP2C9, increasing bleeding risk 3-5x). Major: fluoxetine further inhibits warfarin metabolism. Moderate: metformin requires dose adjustment for renal function. Creates perioperative medication plans for surgical patients, what to hold, when, bridging protocols, restart timing.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Quality-first, patient safety",
      },
      {
        icon: BookOpen,
        title: "Care Pathway Recommender",
        description:
          "Validates treatment plans against evidence-based guidelines and flags deviations. Example: 58M newly diagnosed T2DM, A1c 8.4%, BMI 34, ASCVD risk 18.2%, started on metformin alone. Agent flags that ADA 2026 guidelines recommend adding a GLP-1 receptor agonist for cardiovascular risk reduction (NNT 43 for MACE). Also catches a STEMI case with door-to-balloon time of 142 minutes (ACC target <90 min) and recommends specific quality improvement steps.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced, guideline reasoning",
      },
      {
        icon: BarChart3,
        title: "Medical Coder Agent",
        description:
          "Assigns ICD-10-CM and CPT codes from clinical documentation with DRG impact analysis. Example: perforated appendicitis with laparoscopic-to-open conversion → ICD-10 K35.20 (acute appendicitis with peritonitis), K65.0 (peritoneal abscess), CPT 44960 (open appendectomy with abscess drainage). Generates CDI queries when documentation is vague: 'Physician documented pneumonia, post-op day 3 from CABG, intubated 48hrs, Pseudomonas on sputum culture. Specifying VAP vs HAP changes DRG and increases reimbursement by $8,000-$12,000.'",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Quality-first, structured output",
      },
      {
        icon: MessageSquare,
        title: "Denial Manager Agent",
        description:
          "Analyzes claim denials and drafts evidence-based appeal letters. Example: UnitedHealthcare denied a 3-day inpatient stay (CO-50, 'not medically necessary') for a 78F admitted for syncope with head strike. Agent builds the appeal: continuous telemetry showed 2 episodes of non-sustained VT, echo revealed new EF of 40% (prior 55%), cardiology recommended EP study, citing InterQual criteria for inpatient cardiac monitoring. Also detects denial patterns: 23 denials for CPT 99223 in 30 days, 18 downgraded to 99222 due to missing time documentation, drafts provider education memo.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced, legal/clinical reasoning",
      },
      {
        icon: Target,
        title: "Revenue Forecaster Agent",
        description:
          "Forecasts quarterly revenue from billing data with specific dollar projections. Example for a 250-bed hospital: Q1 revenue $42.3M, payer mix Medicare 45%/Commercial 35%/Medicaid 15%/Self-pay 5%. Factors in CMS 2.9% Medicare fee schedule increase effective April 1, declining commercial volume (-2% QoQ), and a denial rate of 8.2% (above the 6-8% industry average). Flags that AR >90 days is $3.8M against a $2M target, recommends focused collections effort on commercial claims.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized, data analysis",
      },
      {
        icon: Search,
        title: "Adverse Event Detector",
        description:
          "Catches safety signals that humans might miss in the data noise. Example: 3 patients on Unit 4B developed C. difficile infections in 10 days, baseline rate is 0.5 cases/month. Agent identifies the cluster (observed rate 9x expected), finds the common thread (all 3 on fluoroquinolone antibiotics + PPI), and drafts a preliminary report for the Infection Control Committee with specific intervention recommendations. Also catches a post-op AKI caused by ketorolac + contrast CT + dehydration, classifies as 'moderate harm, likely preventable.'",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Quality-first, safety critical",
      },
      {
        icon: Users,
        title: "Readmission Risk Analyzer",
        description:
          "Calculates LACE and HOSPITAL scores at discharge and recommends targeted interventions. Example: 71M being discharged after 6-day stay for CHF exacerbation, 3rd admission in 12 months with 11 medications (2 new), lives alone, nearest family 2 hours away, no car, PCP appointment not for 3 weeks. LACE score: 16 (high risk). Agent recommends: arrange home health within 24hrs, schedule telehealth cardiology follow-up within 48hrs, enroll in pharmacy medication reconciliation program, arrange medical transportation for PCP visit.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Balanced, risk stratification",
      },
      {
        icon: Headphones,
        title: "Quality Metrics Dashboard Narrator",
        description:
          "Translates complex quality data into executive-level narratives with specific action items. Example: CMS Star Rating 3 (target 4), HCAHPS responsiveness at 61% (national avg 67%), CAUTI SIR 1.34 (target <1.0), readmission rate 16.8% (national 15.4%). Agent identifies top 3 priorities: (1) Responsiveness, implement hourly nurse rounding pilot on 3 units, (2) CAUTI, launch catheter removal protocol with daily necessity review, (3) Readmissions, expand discharge planning to include 48hr follow-up calls for high-risk patients.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized, narrative generation",
      },
    ],
    results: [
      {
        metric: "12.7:1",
        label: "ROI",
        detail: "$606K annual value vs $47.8K platform cost, payback in under 30 days",
      },
      {
        metric: "10 agents",
        label: "across 3 projects",
        detail: "Clinical Ops (4) + Revenue Cycle (3) + Quality & Safety (3), with full HIPAA audit trails",
      },
      {
        metric: "$606K",
        label: "projected annual value",
        detail: "$86K AI savings + $180K labor + $100K readmission reduction + $240K revenue recovery",
      },
      {
        metric: "40 requests",
        label: "validated in production",
        detail: "18,618 tokens across AWS + GCP, all logged with complete audit trails for compliance",
      },
    ],
    costAnalysis: {
      headline: "Real Numbers: HIPAA-Compliant Production Testing",
      description:
        "Every number below comes from actual API calls through Bonito's production gateway to live AWS and GCP endpoints. 40 gateway requests tracked, 18,618 tokens processed, with complete audit trails generated for every interaction. The same audit infrastructure that supports HIPAA compliance in production.",
      models: [
        { model: "Amazon Nova Lite", cost: "$0.07 / 1K req", annual: "$1,250/yr", color: "text-green-400" },
        { model: "Gemini 2.0 Flash", cost: "$0.10 / 1K req", annual: "$1,800/yr", color: "text-green-400" },
        { model: "GPT-4o Mini", cost: "$0.17 / 1K req", annual: "$3,070/yr", color: "text-yellow-400" },
        { model: "Bonobot Platform (10 agents)", cost: "$349/agent/mo", annual: "$41,880/yr", color: "text-blue-400" },
      ],
      scenarios: [
        {
          label: "Before Bonito: 3 clouds, no governance, manual workflows",
          cost: "$468,000 / year",
          detail: "$24K/mo AI spend across AWS + GCP + Azure. Plus $180K/yr for 2.5 FTE managing AI infrastructure, manual coding reviews, and denial appeal drafting.",
        },
        {
          label: "With Bonito, governed agents + smart routing",
          cost: "$249,468 / year",
          detail: "$16,800/mo AI (30% reduction via routing) + $3,989/mo platform ($499 Pro + 10 × $349 agents). Full HIPAA audit trails, budget caps, credential isolation included.",
          highlight: true,
        },
        {
          label: "Additional value, clinical outcome improvements",
          cost: "$340,000 / year recovered",
          detail: "Est. 20% fewer excess readmissions ($100K penalty reduction) + better coding/denial management ($240K revenue recovery). Conservative estimates from industry benchmarks.",
        },
      ],
      savingsSummary: [
        { vs: "Return on investment", saved: "12.7:1 ROI", pct: "12.7x", detail: "$606K total value ÷ $47.9K platform cost" },
        { vs: "Direct cost savings", saved: "$218K/yr saved", pct: "47%", detail: "$86K AI routing savings + $180K labor automation, offset by $47.9K platform" },
      ],
      footnote:
        "Based on 40 production gateway requests (18,618 tokens) during E2E stress testing on February 22, 2026. AWS: 18 requests (17 successful), GCP: 6 requests (5 successful), Azure: 16 requests (deployment pending). Revenue recovery and readmission reduction estimates are conservative projections based on published industry benchmarks for AI-assisted medical coding (AHIMA 2025) and CMS readmission penalty data. All agent sessions generated complete audit logs suitable for HIPAA compliance review.",
    },
  },
  /* ── Banking & Financial Services ─────────────────────────────── */
  {
    id: "banking-financial-services",
    tab: "Banking & Financial Services",
    type: "case-study" as const,
    title: "Building the Bank of the Future with Agentic AI",
    subtitle:
      "A top-10 global bank with 90,000+ employees created a dedicated AI Group to turn high-potential AI use cases into solutions that bring real value to clients and amplify the impact of their people. They needed infrastructure that could move as fast as their ambition, deploying agentic AI across 6 divisions without compromising governance or trust.",
    company: {
      industry: "Banking & Financial Services",
      scale: "90,000+ employees, 6 major business divisions",
      cloud: "AWS Bedrock + Azure OpenAI + GCP Vertex AI",
      teams: "Wealth Management, Capital Markets, Personal Banking, Commercial Banking, Insurance, Risk & Compliance",
      data: "Client portfolios, market research, regulatory filings, compliance frameworks, product knowledge, operational playbooks",
      goal: "Empower every division with AI agents that deliver measurable client value, while maintaining the governance and trust that banking demands",
    },
    painPoints: [
      {
        icon: Rocket,
        title: "AI Ambition Outpaced AI Infrastructure",
        description:
          "The AI Group had a mandate to deploy transformative use cases across every division. But each new AI initiative took 12 weeks to provision, cloud resources, credentials, models, security review. The vision was moving at the speed of strategy, while infrastructure moved at the speed of tickets.",
      },
      {
        icon: Users,
        title: "90,000 People Waiting for AI to Amplify Their Work",
        description:
          "Advisors, analysts, compliance officers, client service teams, all seeing what AI could do, none with a governed way to use it. Shadow AI was emerging: teams spinning up their own experiments with no oversight, no shared knowledge, and no way to scale what worked.",
      },
      {
        icon: Shield,
        title: "Trust and Governance Can't Be Afterthoughts",
        description:
          "In financial services, one misconfigured AI agent accessing the wrong data isn't just a bug, it's a regulatory breach. The bank needed division-level isolation, complete audit trails, and credential separation baked into the platform, not bolted on later.",
      },
      {
        icon: Layers,
        title: "Best-of-Breed AI Required Multi-Cloud Foundation",
        description:
          "No single cloud provider had the best model for every use case. The bank needed GPT-4o for complex reasoning, Gemini for high-throughput analysis, Claude for nuanced compliance work, and Nova for cost-effective screening. That meant 3 clouds, unified under one control plane.",
      },
    ],
    aiUseCases: [
      {
        icon: Headphones,
        title: "Client Service Agents (Personal Banking)",
        description:
          "AI agents that give every client the experience of having a personal banker. Instant account inquiries, personalized product recommendations, proactive issue resolution, grounded in the bank's actual policies and product knowledge.",
        model: "GPT-4o (complex) → Gemini Flash (high-volume)",
        strategy: "Route by complexity: relationship-level questions to GPT-4o, routine inquiries to Gemini Flash for instant response",
      },
      {
        icon: BarChart3,
        title: "Wealth Management Research Assistants",
        description:
          "Advisors spend 60% of their time on research, 40% with clients. These agents flip that ratio. An orchestrator delegates to specialist agents. Market Analyst, Portfolio Advisor, Tax Specialist, and compiles unified recommendations so advisors can focus on relationships.",
        model: "GPT-4o (orchestrator) → Gemini 2.5 Pro (analysis)",
        strategy: "Multi-agent delegation: orchestrator fans out to 3 specialists, collects results, delivers advisor-ready briefs",
      },
      {
        icon: Building2,
        title: "Capital Markets Trading Intelligence",
        description:
          "Real-time market analysis, trade idea generation, and risk scoring that keeps traders ahead of the market. Agents scoped to specific desks (equities, fixed income, FX) so each team gets tailored intelligence without information bleed.",
        model: "Gemini 2.5 Pro (deep analysis) → Nova Lite (screening)",
        strategy: "Tiered intelligence: deep model surfaces insights, fast model screens and filters at scale",
      },
      {
        icon: Shield,
        title: "Compliance & Risk Monitoring",
        description:
          "Agents that augment compliance officers, monitoring transactions, flagging patterns, cross-referencing regulatory changes in real-time. The human makes the call, but AI ensures nothing gets missed. Full audit trail on every interaction.",
        model: "Claude 3.5 Sonnet (reasoning) → Nova Pro (summarization)",
        strategy: "AI as safety net: heavyweight reasoning for risk detection, lightweight models for daily compliance digests",
      },
      {
        icon: FileText,
        title: "Regulatory Reporting Acceleration",
        description:
          "What used to take compliance teams 3 weeks of manual extraction and cross-referencing now takes 2 days with AI-assisted drafting and human review. Frees up senior compliance talent to focus on judgment calls, not data entry.",
        model: "Claude 3.5 Sonnet → GPT-4o (validation)",
        strategy: "Dual-pass: AI drafts against regulatory templates, second model validates, humans approve",
      },
      {
        icon: Users,
        title: "Employee Experience at Scale",
        description:
          "90,000 employees across all divisions with instant, accurate answers to policy questions, benefits inquiries, and HR processes. Division-specific knowledge bases ensure each team gets relevant answers, not generic corporate boilerplate.",
        model: "Gemini 2.0 Flash (instant response)",
        strategy: "Always-on self-service: AI handles routine queries instantly, escalates nuanced issues to HR specialists",
      },
    ],
    results: [
      { metric: "42", label: "Production AI Agents", detail: "Across 6 divisions. Each with scoped knowledge, dedicated models, and governed access. From 8 pilot experiments to 42 production agents." },
      { metric: "2 days", label: "Idea to Production", detail: "New AI use cases go from concept to live in 2 days instead of 12 weeks. The AI Group's velocity matched their ambition." },
      { metric: "100%", label: "Division-Level Isolation", detail: "Every agent, every query, every knowledge doc cryptographically scoped to its division. Regulators see a clean audit trail." },
      { metric: "3.2x", label: "Advisor Productivity Lift", detail: "Wealth Management advisors spend 3.2x more time with clients. AI handles research, prep, and follow-up documentation." },
      { metric: "99.97%", label: "AI Availability", detail: "Multi-cloud resilience: if one provider has an outage, traffic routes automatically. Zero single-vendor dependency." },
      { metric: "$8.2M", label: "First-Year Enterprise Value", detail: "Client experience improvements, advisor productivity, faster compliance, reduced manual processes, measured and attributed per division." },
    ],
    costAnalysis: {
      headline: "42 AI Agents, 6 Divisions, 3 Clouds. One Control Plane",
      description:
        "The AI Group's mandate wasn't to cut costs. It was to create value. Bonito gave them the infrastructure to move fast while maintaining the governance and trust that banking demands. Every division got tailored AI agents, connected to their own knowledge bases in their own cloud storage, with complete audit trails and budget transparency.",
      models: [
        { model: "GPT-4o", cost: "$5.00/M tokens", annual: "Complex reasoning", color: "bg-emerald-500" },
        { model: "Claude 3.5 Sonnet", cost: "$3.00/M tokens", annual: "Compliance & risk", color: "bg-blue-500" },
        { model: "Gemini 2.5 Pro", cost: "$1.25/M tokens", annual: "Research & analysis", color: "bg-purple-500" },
        { model: "Gemini 2.0 Flash", cost: "$0.10/M tokens", annual: "High-volume service", color: "bg-amber-500" },
        { model: "Nova Lite/Pro", cost: "$0.06-0.80/M tokens", annual: "Screening & extraction", color: "bg-red-500" },
      ],
      scenarios: [
        { label: "AI agents deployed", cost: "42 agents", detail: "20 with knowledge context, 12 orchestrators with delegation, 10 specialist agents across 6 divisions" },
        { label: "Time to deploy new use case", cost: "2 days", detail: "IaC templates + one-click model activation + cloud storage connector for knowledge docs", highlight: true },
        { label: "Enterprise value (Year 1)", cost: "$8.2M", detail: "Client experience, advisor productivity, compliance acceleration, operational efficiency" },
      ],
      savingsSummary: [
        { vs: "Enterprise value created", saved: "$8.2M", pct: "", detail: "Measured per-division: client experience lift, productivity gains, compliance acceleration" },
        { vs: "Deployment velocity", saved: "40x faster", pct: "97%", detail: "12 weeks → 2 days. AI Group ships weekly instead of quarterly." },
        { vs: "Advisor time with clients", saved: "3.2x increase", pct: "220%", detail: "AI handles research, prep, and documentation. Humans do what humans do best." },
        { vs: "Regulatory readiness", saved: "Always audit-ready", pct: "100%", detail: "Every agent interaction logged, scoped, and traceable. No scramble before audits." },
      ],
      footnote:
        "Projections based on a validated enterprise simulation: 6 business divisions, 20 AI agents, 8 department-specific knowledge documents, 28 production-grade test requests across 3 cloud providers. Agent delegation, async orchestration, cross-division isolation, and concurrent load all verified at 92.3% pass rate (24/26 tests). Value estimates extrapolate from measured agent performance and published industry benchmarks for AI-driven transformation in financial services (McKinsey Global Institute, 2025).",
    },
  },
];

/* ─── Shared Onboarding Steps ─────────────────────────────────────── */

const onboardingSteps = [
  {
    step: "1",
    title: "Create your Bonito account",
    description:
      "Sign up at getbonito.com. One account covers the entire organization. You'll get an org workspace where you can invite team members later.",
    time: "2 minutes",
  },
  {
    step: "2",
    title: "Connect your cloud providers",
    description:
      "Go to Providers → Add Provider. Enter your credentials for AWS, GCP, and/or Azure. Bonito validates each connection and checks AI service permissions automatically.",
    time: "3 minutes each",
  },
  {
    step: "3",
    title: "See all your models in one place",
    description:
      "Bonito automatically syncs every available model from your connected providers. Filter by provider, search by name, and enable models with one click. No need to visit each cloud console.",
    time: "1 minute",
  },
  {
    step: "4",
    title: "Test models in the playground",
    description:
      "Click any model to open the playground. Send test prompts, compare responses from different models side by side, and see real token usage and cost per request.",
    time: "10 minutes",
  },
  {
    step: "5",
    title: "Set up routing policies",
    description:
      "Create routing policies for each use case. Cost-optimized for high-volume tasks, quality-first for complex analysis, failover chains for reliability. Each policy is testable with dry-run before going live.",
    time: "10 minutes",
  },
  {
    step: "6",
    title: "Generate API keys and integrate",
    description:
      "Generate a unique API key for each team or service. Your teams swap their existing SDK endpoint to Bonito's gateway URL, same OpenAI-compatible API format, just a config change.",
    time: "5 minutes per service",
  },
];

/* ─── Comparison Article Component ────────────────────────────────── */

function ComparisonArticle({ uc }: { uc: UseCase }) {
  const comp = uc.comparison!;

  return (
    <div>
      {/* Hero */}
      <section className="pt-8 pb-12">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight">{uc.title}</h1>
        <p className="mt-4 text-lg text-[#888] max-w-3xl">{uc.subtitle}</p>
      </section>

      {/* Scenario */}
      <section className="pb-12">
        <div className="bg-gradient-to-br from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-xl p-6 md:p-8">
          <h2 className="text-xl font-bold mb-3 flex items-center gap-2">
            <Target className="w-5 h-5 text-[#7c3aed]" />
            The Scenario
          </h2>
          <p className="text-[#ccc] text-base leading-relaxed">{comp.scenario}</p>
        </div>
      </section>

      {/* Three Approaches: 3-column on desktop, stacked on mobile */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-8">Three Approaches, One Goal</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {comp.approaches.map((a, i) => (
            <motion.div
              key={a.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`${a.bgColor} border ${a.borderColor} rounded-xl p-6 flex flex-col`}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-10 h-10 rounded-lg ${a.bgColor} border ${a.borderColor} flex items-center justify-center`}>
                  <a.icon className={`w-5 h-5 ${a.color}`} />
                </div>
                <h3 className="text-lg font-bold">{a.name}</h3>
              </div>

              <div className="space-y-3 text-sm flex-1">
                <div>
                  <span className="text-[#888]">Timeline:</span>{" "}
                  <span className={a.color}>{a.timeline}</span>
                </div>
                <div>
                  <span className="text-[#888]">Year 1 cost:</span>{" "}
                  <span className="font-semibold">{a.year1Cost}</span>
                </div>
                <div>
                  <span className="text-[#888]">Ongoing:</span>{" "}
                  <span className="text-[#ccc]">{a.ongoing}</span>
                </div>
                <div>
                  <span className="text-[#888]">Token usage:</span>{" "}
                  <span className="text-[#ccc]">{a.tokenUsage}</span>
                </div>
                <div>
                  <span className="text-[#888]">Models:</span>{" "}
                  <span className="text-[#ccc]">{a.typicalModels}</span>
                </div>
                <div>
                  <span className="text-[#888]">Monthly AI spend:</span>{" "}
                  <span className="text-[#ccc]">{a.monthlyAiSpend}</span>
                </div>

                <div className="pt-3 border-t border-[#1a1a1a]">
                  <span className="text-[#888]">Total Year 1:</span>{" "}
                  <span className={`font-bold ${a.color}`}>{a.totalYear1}</span>
                </div>

                <ul className="space-y-1.5 pt-2">
                  {a.details.map((d, j) => (
                    <li key={j} className="text-xs text-[#888] flex items-start gap-1.5">
                      <span className="mt-1 w-1 h-1 rounded-full bg-[#444] shrink-0" />
                      {d}
                    </li>
                  ))}
                </ul>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Comparison Table */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-8">Side-by-Side Comparison</h2>
        <div className="bg-[#111] border border-[#1a1a1a] rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#1a1a1a]">
                  <th className="text-left px-4 md:px-6 py-4 font-medium text-[#888] w-[28%]"></th>
                  <th className="text-center px-4 md:px-6 py-4 font-semibold text-red-400 w-[24%]">
                    <div className="flex items-center justify-center gap-1.5">
                      <Briefcase className="w-4 h-4" /> Consulting
                    </div>
                  </th>
                  <th className="text-center px-4 md:px-6 py-4 font-semibold text-yellow-400 w-[24%]">
                    <div className="flex items-center justify-center gap-1.5">
                      <Puzzle className="w-4 h-4" /> Patchwork
                    </div>
                  </th>
                  <th className="text-center px-4 md:px-6 py-4 font-semibold text-green-400 w-[24%]">
                    <div className="flex items-center justify-center gap-1.5">
                      <Rocket className="w-4 h-4" /> Bonito
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {comp.table.map((row, i) => (
                  <tr
                    key={row.label}
                    className={`border-b border-[#1a1a1a]/50 ${i % 2 === 0 ? "bg-[#0d0d0d]" : ""}`}
                  >
                    <td className="px-4 md:px-6 py-3.5 font-medium text-[#ccc]">{row.label}</td>
                    <td className="px-4 md:px-6 py-3.5 text-center text-[#999]">{row.consulting}</td>
                    <td className="px-4 md:px-6 py-3.5 text-center text-[#999]">{row.patchwork}</td>
                    <td className="px-4 md:px-6 py-3.5 text-center text-green-400 font-medium">{row.bonito}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* Risk Deep-Dive */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-3">Risk Deep-Dive</h2>
        <p className="text-[#888] mb-8">Every approach has trade-offs. Here&apos;s an honest look at the risks.</p>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {comp.riskCards.map((card, i) => (
            <motion.div
              key={card.approach}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`${card.bgColor} border ${card.borderColor} rounded-xl p-6`}
            >
              <div className="flex items-center gap-2 mb-4">
                <card.icon className={`w-5 h-5 ${card.color}`} />
                <h3 className={`font-bold ${card.color}`}>{card.approach}</h3>
              </div>
              <ul className="space-y-3">
                {card.risks.map((risk, j) => (
                  <li key={j} className="flex items-start gap-2 text-sm text-[#ccc]">
                    <AlertTriangle className={`w-3.5 h-3.5 ${card.color} shrink-0 mt-0.5`} />
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Bottom Line */}
      <section className="pb-16">
        <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 md:p-8">
          <h2 className="text-2xl font-bold mb-4">The Bottom Line</h2>
          <div className="grid sm:grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold text-red-400 mb-1">$500K-$2M</div>
              <div className="text-sm text-[#888]">Consulting Route</div>
              <div className="text-xs text-[#666] mt-1">6-12 months to first AI in production</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-yellow-400 mb-1">$250K-$450K</div>
              <div className="text-sm text-[#888]">Patchwork Route</div>
              <div className="text-xs text-[#666] mt-1">4-6 months, 2-3 FTE dedicated</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-green-400 mb-1">~$18K</div>
              <div className="text-sm text-[#888]">Bonito</div>
              <div className="text-xs text-[#666] mt-1">Same day to connected, 1 week to all departments</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

/* ─── Case Study Article Component ────────────────────────────────── */

function CaseStudyArticle({ uc }: { uc: UseCase }) {
  return (
    <div>
      {/* Hero */}
      <section className="pt-8 pb-12">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight">{uc.title}</h1>
        <p className="mt-4 text-lg text-[#888] max-w-3xl">{uc.subtitle}</p>
      </section>

      {/* Company Profile */}
      <section className="pb-12">
        <div className="bg-gradient-to-br from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-xl p-6 md:p-8">
          <h2 className="text-xl font-bold mb-4">The Company</h2>
          <div className="grid sm:grid-cols-2 gap-6 text-sm text-[#ccc]">
            <div className="space-y-3">
              <div>
                <span className="text-[#888]">Industry:</span> {uc.company.industry}
              </div>
              <div>
                <span className="text-[#888]">Scale:</span> {uc.company.scale}
              </div>
              <div>
                <span className="text-[#888]">Cloud:</span> {uc.company.cloud}
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <span className="text-[#888]">Teams using AI:</span> {uc.company.teams}
              </div>
              <div>
                <span className="text-[#888]">Data:</span> {uc.company.data}
              </div>
              <div>
                <span className="text-[#888]">Goal:</span> {uc.company.goal}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The Problem */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-8">The Problem</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          {uc.painPoints.map((point, i) => (
            <motion.div
              key={point.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6"
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center shrink-0">
                  <point.icon className="w-4 h-4 text-red-400" />
                </div>
                <div>
                  <h3 className="font-semibold mb-1">{point.title}</h3>
                  <p className="text-sm text-[#888] leading-relaxed">{point.description}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* AI Use Cases */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-3">What They Want to Build</h2>
        <p className="text-[#888] mb-8">
          Multiple AI-powered features, each with different requirements for cost, latency, and
          model quality.
        </p>
        <div className="space-y-4">
          {uc.aiUseCases.map((item, i) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 hover:border-[#7c3aed]/20 transition"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center shrink-0">
                  <item.icon className="w-5 h-5 text-[#7c3aed]" />
                </div>
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <h3 className="font-semibold">{item.title}</h3>
                    <span className="text-xs text-[#7c3aed] bg-[#7c3aed]/10 px-2 py-1 rounded shrink-0">
                      {item.strategy}
                    </span>
                  </div>
                  <p className="text-sm text-[#888] mb-2">{item.description}</p>
                  <p className="text-xs text-[#666]">
                    <span className="text-[#888]">Model:</span> {item.model}
                  </p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How Bonito Solves It */}
      <section className="pb-16">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
            <Zap className="w-5 h-5 text-[#7c3aed]" />
          </div>
          <h2 className="text-3xl font-bold">How Bonito Solves This</h2>
        </div>
        <p className="text-[#888] mb-8 max-w-3xl">
          Instead of each team building their own AI integration, managing their own credentials,
          and tracking their own costs, the platform team sets up Bonito once. Every team gets a
          single API endpoint, governed routing, and full visibility.
        </p>

        <div className="grid sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
            <Cloud className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
            <h3 className="font-semibold mb-1">Connect once</h3>
            <p className="text-sm text-[#888]">
              Plug in your cloud service accounts. Bonito handles the rest.
            </p>
          </div>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
            <Route className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
            <h3 className="font-semibold mb-1">Route intelligently</h3>
            <p className="text-sm text-[#888]">
              Each use case gets the right model at the right price with automatic failover.
            </p>
          </div>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
            <Shield className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
            <h3 className="font-semibold mb-1">Govern everything</h3>
            <p className="text-sm text-[#888]">
              Costs, compliance, audit trails, and access controls from one dashboard.
            </p>
          </div>
        </div>
      </section>

      {/* Onboarding Steps */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-3">Step-by-Step Onboarding</h2>
        <p className="text-[#888] mb-8">
          From &quot;we have credentials&quot; to &quot;all teams are using AI through one
          gateway&quot; in under an hour.
        </p>
        <div className="space-y-4">
          {onboardingSteps.map((step, i) => (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.03 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 hover:border-[#7c3aed]/20 transition"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-full bg-[#7c3aed] flex items-center justify-center shrink-0 text-white font-bold text-sm">
                  {step.step}
                </div>
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-4 mb-1">
                    <h3 className="font-semibold">{step.title}</h3>
                    <span className="text-xs text-[#888] bg-[#1a1a1a] px-2 py-1 rounded shrink-0">
                      {step.time}
                    </span>
                  </div>
                  <p className="text-sm text-[#888] leading-relaxed">{step.description}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Results */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-8">The Results</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {uc.results.map((r, i) => (
            <motion.div
              key={r.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center"
            >
              <div className="text-3xl font-bold text-[#7c3aed] mb-1">{r.metric}</div>
              <div className="text-sm font-medium mb-2">{r.label}</div>
              <p className="text-xs text-[#666]">{r.detail}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Cost Analysis */}
      <section className="pb-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-[#7c3aed]" />
            </div>
            <h2 className="text-3xl font-bold">{uc.costAnalysis.headline}</h2>
          </div>
          <p className="text-[#888] mb-8 max-w-3xl">{uc.costAnalysis.description}</p>

          {/* Model Costs Table */}
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl overflow-hidden mb-8">
            <div className="px-6 py-4 border-b border-[#1a1a1a]">
              <h3 className="font-semibold">
                {uc.id === "cx-platform"
                  ? "Cost per Model at 50K Requests/Day (18.25M/year)"
                  : "Model Pricing per 1M Tokens"}
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[#888] border-b border-[#1a1a1a]">
                    <th className="text-left px-6 py-3 font-medium">Model</th>
                    <th className="text-right px-6 py-3 font-medium">
                      {uc.id === "cx-platform" ? "Cost" : "Input / Output"}
                    </th>
                    <th className="text-right px-6 py-3 font-medium">
                      {uc.id === "cx-platform" ? "Annual (all traffic)" : "Tier"}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {uc.costAnalysis.models.map((m) => (
                    <tr
                      key={m.model}
                      className="border-b border-[#1a1a1a]/50 hover:bg-[#1a1a1a]/30"
                    >
                      <td className="px-6 py-3 font-medium">{m.model}</td>
                      <td className="px-6 py-3 text-right font-mono">{m.cost}</td>
                      <td className={`px-6 py-3 text-right font-mono ${m.color}`}>
                        {m.annual}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Scenarios */}
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-[#1a1a1a]">
              <h3 className="font-semibold">Scenario Comparison</h3>
            </div>
            <div className="divide-y divide-[#1a1a1a]/50">
              {uc.costAnalysis.scenarios.map((s) => (
                <div
                  key={s.label}
                  className={`px-6 py-5 ${s.highlight ? "bg-[#7c3aed]/5 border-l-2 border-[#7c3aed]" : ""}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{s.label}</span>
                    <span
                      className={`text-lg font-bold ${s.highlight ? "text-green-400" : "text-[#ccc]"}`}
                    >
                      {s.cost}
                    </span>
                  </div>
                  <p className="text-xs text-[#888]">{s.detail}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Savings Summary */}
          {uc.costAnalysis.savingsSummary.length > 0 && (
            <div className="grid sm:grid-cols-2 gap-4 mb-6">
              {uc.costAnalysis.savingsSummary.map((s) => (
                <div
                  key={s.vs}
                  className="bg-green-500/5 border border-green-500/20 rounded-xl p-5 text-center"
                >
                  <div className="text-2xl font-bold text-green-400 mb-1">{s.saved}</div>
                  <div className="text-sm text-[#888] mb-1">{s.vs}</div>
                  {s.detail && (
                    <div className="text-xs text-[#666] font-mono">{s.detail}</div>
                  )}
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-[#666] italic">{uc.costAnalysis.footnote}</p>
        </motion.div>
      </section>
    </div>
  );
}

/* ─── Page Component ──────────────────────────────────────────────── */

export default function UseCasesPage() {
  const [activeCase, setActiveCase] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);

  /* Deep-link: read hash on mount and when hash changes */
  useEffect(() => {
    const syncHash = () => {
      const hash = window.location.hash.replace("#", "");
      if (hash) {
        const idx = useCases.findIndex((c) => c.id === hash);
        if (idx !== -1) setActiveCase(idx);
      }
    };
    syncHash();
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

  /* Update URL hash when tab changes (without scroll jump) */
  useEffect(() => {
    const id = useCases[activeCase]?.id;
    if (id && window.location.hash !== `#${id}`) {
      history.replaceState(null, "", `#${id}`);
    }
  }, [activeCase]);

  const uc = useCases[activeCase];

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12">
      {/* Header */}
      <section className="pt-20 pb-6">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-8 h-8 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
            <Building2 className="w-4 h-4 text-[#7c3aed]" />
          </div>
          <span className="text-sm font-medium text-[#7c3aed] uppercase tracking-wider">
            Use Cases
          </span>
        </div>
      </section>

      {/* Mobile Dropdown */}
      <div className="lg:hidden mb-6">
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="w-full flex items-center justify-between px-4 py-3 bg-[#111] border border-[#1a1a1a] rounded-xl text-sm font-medium"
        >
          <span className="truncate">{uc.tab}</span>
          <ChevronDown className={`w-4 h-4 text-[#888] transition-transform ${mobileOpen ? "rotate-180" : ""}`} />
        </button>
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="mt-1 bg-[#111] border border-[#1a1a1a] rounded-xl overflow-hidden">
                {useCases.map((c, i) => (
                  <button
                    key={c.id}
                    onClick={() => {
                      setActiveCase(i);
                      setMobileOpen(false);
                    }}
                    className={`w-full text-left px-4 py-3 text-sm transition-colors ${
                      activeCase === i
                        ? "text-white bg-[#7c3aed]/10 border-l-2 border-[#7c3aed]"
                        : "text-[#666] hover:text-[#999] hover:bg-[#1a1a1a]/50"
                    }`}
                  >
                    {c.tab}
                    {c.type === "comparison" && (
                      <span className="ml-2 text-xs text-[#7c3aed] bg-[#7c3aed]/10 px-1.5 py-0.5 rounded">NEW</span>
                    )}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Desktop: Sidebar + Content */}
      <div className="flex gap-8">
        {/* Left Sidebar, desktop only */}
        <aside className="hidden lg:block w-64 shrink-0">
          <nav className="sticky top-24 max-h-[calc(100vh-8rem)] overflow-y-auto">
            <div className="space-y-1">
              {useCases.map((c, i) => (
                <button
                  key={c.id}
                  onClick={() => setActiveCase(i)}
                  className={`w-full text-left px-4 py-3 rounded-lg text-sm transition-all ${
                    activeCase === i
                      ? "text-white bg-[#7c3aed]/10 border-l-2 border-[#7c3aed]"
                      : "text-[#666] hover:text-[#999] hover:bg-[#1a1a1a]/50 border-l-2 border-transparent"
                  }`}
                >
                  <span className="block leading-snug">{c.tab}</span>
                  {c.type === "comparison" && (
                    <span className="inline-block mt-1 text-xs text-[#7c3aed] bg-[#7c3aed]/10 px-1.5 py-0.5 rounded">
                      Comparison
                    </span>
                  )}
                </button>
              ))}
            </div>
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            <motion.div
              key={uc.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
            >
              {uc.type === "comparison" ? (
                <ComparisonArticle uc={uc} />
              ) : (
                <CaseStudyArticle uc={uc} />
              )}
            </motion.div>
          </AnimatePresence>

          {/* CTA */}
          <section className="pb-24">
            <div className="bg-gradient-to-br from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-xl p-8 md:p-12 text-center">
              <h2 className="text-2xl md:text-3xl font-bold mb-3">Sound like your team?</h2>
              <p className="text-[#888] mb-6 max-w-xl mx-auto">
                If you&apos;re running AI workloads across multiple cloud providers and want unified
                control without the infrastructure overhead, Bonito was built for you.
              </p>
              <div className="flex items-center justify-center gap-4 flex-wrap">
                <Link
                  href="/register"
                  className="px-6 py-3 rounded-lg bg-[#7c3aed] text-white font-semibold hover:bg-[#6d28d9] transition"
                >
                  Get Started Free
                </Link>
                <Link
                  href="/contact"
                  className="px-6 py-3 rounded-lg border border-[#333] font-medium text-[#ccc] hover:border-[#7c3aed] transition"
                >
                  Talk to Us
                </Link>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
