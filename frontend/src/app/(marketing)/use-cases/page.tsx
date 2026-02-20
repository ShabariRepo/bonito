"use client";

import { useState } from "react";
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
} from "lucide-react";

/* ─── Use Case Data ───────────────────────────────────────────────── */

interface UseCase {
  id: string;
  tab: string;
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
}

const useCases: UseCase[] = [
  {
    id: "cx-platform",
    tab: "Customer Experience SaaS",
    title: "How a Mid-Market CX Platform Cut AI Costs by 89% Across Three Clouds",
    subtitle:
      "A real-world cost analysis: a B2B customer experience platform processing 50,000 AI requests per day across AWS, GCP, and Azure. From $51K/year to $5.8K/year — with better model selection per task.",
    company: {
      industry: "B2B Customer Experience Platform (SaaS)",
      scale: "200+ business clients, 50,000+ AI requests/day, 18.25M requests/year",
      cloud: "AWS Bedrock + GCP Vertex AI + Azure OpenAI (all three)",
      teams: "Product Engineering, Data Science, Customer Success, Content",
      data: "Customer interaction data, support tickets, product catalogs, engagement analytics",
      goal: "Intelligent model routing — use the cheapest model that meets quality requirements for each task",
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
          "Simple tasks like sentiment classification and FAQ responses were burning premium tokens. 60% of requests were routine — they didn't need a frontier model, but there was no easy way to route differently.",
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
          "Auto-generate response drafts for support tickets. Agents review and send — cuts average response time from 12 minutes to 3 minutes.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized — high volume, routine text generation",
      },
      {
        icon: BarChart3,
        title: "Sentiment & intent classification",
        description:
          "Classify incoming tickets by sentiment, urgency, and intent. Routes to the right team automatically. Runs on every single ticket.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized — simple classification at massive scale",
      },
      {
        icon: Search,
        title: "Product recommendations",
        description:
          "Analyze customer behavior patterns and generate personalized product recommendations. Powers the 'suggested for you' features across client platforms.",
        model: "Gemini 2.5 Flash (GCP Vertex AI)",
        strategy: "Balanced — needs reasoning quality for good recommendations",
      },
      {
        icon: FileText,
        title: "Content personalization",
        description:
          "Generate personalized email subject lines, in-app messages, and notification copy at scale. A/B tests variations automatically.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Cost-optimized — creative text but high volume",
      },
      {
        icon: Bot,
        title: "Complex analysis & reporting",
        description:
          "Deep-dive analytics: churn prediction explanations, quarterly insight reports, and strategic recommendations for enterprise clients.",
        model: "GPT-4o (Azure OpenAI)",
        strategy: "Quality-first — low volume, high-stakes output",
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
        detail: "Each task routed to the optimal model — Nova Lite, Gemini Flash, GPT-4o Mini, and GPT-4o",
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
          detail: "Premium model for everything — great quality, terrible economics at scale",
        },
        {
          label: "All GPT-4o Mini (cost-cutting approach)",
          cost: "$3,070 / year",
          detail: "Cheapest Azure option for everything — saves money but sacrifices quality on complex tasks",
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
          "Product catalogs, merchant policies, return rules, and support docs are scattered across wikis and databases. AI models can't access any of it — support bots give generic answers instead of product-specific ones.",
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
          "AI-powered support bot that answers merchant questions using Bonito's AI Context. Product catalogs, return policies, and platform docs are indexed — so the bot gives accurate, product-specific answers instead of generic responses.",
        model: "Claude 3 Haiku → Claude 3.5 Sonnet (failover)",
        strategy: "Failover + AI Context (RAG)",
      },
      {
        icon: Search,
        title: "Product Q&A with AI Context",
        description:
          "Buyers ask natural-language questions about products. Bonito's AI Context searches indexed product catalogs and specs, then injects relevant context into any model — regardless of cloud. Answers in under 500ms with source citations.",
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
        metric: "40–70%",
        label: "lower AI spend",
        detail: "By routing routine requests to cost-efficient models instead of using premium models for everything",
      },
      {
        metric: "<500ms",
        label: "RAG search latency",
        detail: "AI Context returns relevant product docs with relevance scores >0.63 — fast enough for real-time Q&A",
      },
      {
        metric: "Every request",
        label: "logged and tracked",
        detail: "User, model, cost, and token usage captured for every request routed through Bonito",
      },
      {
        metric: "1 KB",
        label: "all models can access",
        detail: "One centralized knowledge base — every AI model on any cloud gets the same product context via AI Context",
      },
    ],
    costAnalysis: {
      headline: "The Math Behind 40–70% Savings",
      description:
        "Most enterprises pick a 'good' model and use it for everything. But 60–80% of LLM requests are routine — classification, summarization, template filling, simple Q&A. These tasks don't need a frontier model. The pricing gap between premium and economy models is 10–25x.",
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
          detail: "Route 70% of routine traffic to GPT-4o Mini, keep 30% on GPT-4o for complex tasks — 67% savings",
        },
        {
          label: "Using Claude 3.5 Sonnet for everything",
          cost: "$9.00 → $3.23 per 1K tokens",
          detail: "Route 70% to Claude 3 Haiku, keep 30% on Sonnet for nuanced work — 64% savings",
        },
        {
          label: "Cross-provider routing",
          cost: "$9.00 → $2.83 per 1K tokens",
          detail: "Sonnet for complex tasks, Gemini Flash for simple ones — best price across clouds — 69% savings",
          highlight: true,
        },
      ],
      savingsSummary: [
        { vs: "Cross-provider vs single premium model", saved: "up to 69%", pct: "69%" },
      ],
      footnote:
        "Pricing based on published rates from OpenAI, Anthropic, and Google as of early 2026. Actual savings depend on traffic mix and which models your teams currently use. Savings are highest for teams defaulting to a single premium model for all tasks. AI Context (RAG) adds <500ms latency per query with relevance scores averaging 0.63+ — validated on production infrastructure with real vector search.",
    },
  },
  {
    id: "enterprise-ai-ops",
    tab: "Enterprise AI Ops",
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
        title: "$2.7M annual AI spend — unoptimized",
        description:
          "Every team defaulted to premium models for all tasks. Classification, summarization, and template-filling all running on GPT-4o at $2.80 per 1K requests. Nobody knew which tasks could use a cheaper model.",
      },
      {
        icon: Database,
        title: "Siloed company knowledge",
        description:
          "Company policies, compliance procedures, product docs, and onboarding materials lived in wikis that AI models couldn't access. Internal copilots gave generic answers. Teams maintained separate RAG pipelines per cloud — tripling infrastructure cost.",
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
          "Support agents get AI-drafted responses enriched with company-specific context. Bonito's AI Context indexes all product docs, FAQ, and policies — so every response is accurate to internal documentation, not generic.",
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
          "Company-wide AI assistant that answers questions about internal procedures, benefits, and policies. Powered by AI Context — one knowledge base, accessible to any model on any cloud.",
        model: "Gemini 2.5 Flash (GCP Vertex AI) + AI Context",
        strategy: "Balanced + RAG",
      },
      {
        icon: FileText,
        title: "Report generation",
        description:
          "Generate quarterly business reports, compliance summaries, and executive briefings. Low volume but high quality requirements — only runs on premium models.",
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
        detail: "Full catalog from AWS, Azure, and GCP — 12 actively deployed, all managed from one console",
      },
      {
        metric: "37.5:1",
        label: "ROI",
        detail: "$2.25M annual savings vs $60K Enterprise subscription — payback in under 10 days",
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
          label: "Before Bonito — premium models for everything",
          cost: "$2,700,000 / year",
          detail: "3 separate AI platforms, 3 governance frameworks, 3 sets of credentials, no cost optimization",
        },
        {
          label: "With Bonito — smart routing across 3 clouds",
          cost: "$450,000 / year",
          detail: "60% → Nova Lite • 20% → GPT-4o Mini • 15% → Gemini Flash • 5% → GPT-4o for complex tasks",
          highlight: true,
        },
        {
          label: "Bonus: Centralized AI Context replaces 3 RAG pipelines",
          cost: "$0 extra infrastructure",
          detail: "One knowledge base indexed via pgvector — all models on all clouds access the same company docs. No per-cloud RAG infrastructure to maintain.",
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
    title: "How NovaMart Deployed 8 Autonomous AI Agents with Full Budget Controls",
    subtitle:
      "A real-world walkthrough: a product marketplace with 200K+ sellers and 5M+ monthly buyers deploys Bonobot AI agents for ad operations and seller support — cutting report cycles from 2 days to 12 minutes and deflecting 78% of support tickets.",
    company: {
      industry: "Product Marketplace with Bonobot AI Agents",
      scale: "300 employees, 200K+ sellers, 5M+ monthly buyers, 25K agent interactions/day",
      cloud: "AWS Bedrock + GCP Vertex AI (via Bonito gateway)",
      teams: "Ad Operations, Seller Support, Platform Engineering",
      data: "Campaign analytics across 15+ channels, seller documentation, product catalogs, fee schedules, policy docs",
      goal: "Deploy governed AI agents that autonomously handle research, reporting, and support — with budget controls and full audit trails",
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
        title: "Coordinator Agent — Campaign Analysis",
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
        strategy: "Balanced — escalation only",
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
        detail: "Coordinator delegates to 5 parallel analyst agents, collects results, and synthesizes — fully autonomous",
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
          label: "Before Bonobot — manual + uncontrolled AI",
          cost: "$540,000 / year",
          detail: "2 FTE analysts ($180K), support overhead ($120K), uncontrolled AI spend ($240K/year projected)",
        },
        {
          label: "With Bonobot — governed autonomous agents",
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
        "Based on 25,000 agent interactions/day. Model costs from published AWS and GCP rates as of February 2026. Bonobot pricing: $349/mo per hosted agent. Budget caps enforced in real-time via Redis — agents receive HTTP 402 before exceeding limits. FTE savings estimated from industry averages for ad operations analysts ($90K) and support specialists ($60K).",
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
      "Bonito automatically syncs every available model from your connected providers. Filter by provider, search by name, and enable models with one click — no need to visit each cloud console.",
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
      "Generate a unique API key for each team or service. Your teams swap their existing SDK endpoint to Bonito's gateway URL — same OpenAI-compatible API format, just a config change.",
    time: "5 minutes per service",
  },
];

/* ─── Page Component ──────────────────────────────────────────────── */

export default function UseCasesPage() {
  const [activeCase, setActiveCase] = useState(0);
  const uc = useCases[activeCase];

  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12">
      {/* Page Hero */}
      <section className="pt-24 pb-12">
        <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight max-w-4xl">
          AI Shouldn&apos;t Be Your Biggest Expense.{" "}
          <span className="text-[#7c3aed]">It Should Be Your Biggest Edge.</span>
        </h1>
        <p className="mt-6 text-lg text-[#888] max-w-2xl leading-relaxed">
          Most enterprises burn 60–80% of their AI budget running premium models on tasks that
          don&apos;t need them. The ones who fix this first don&apos;t just save money — they move
          faster, ship smarter, and leave competitors scrambling to catch up.
        </p>
      </section>

      {/* Tab Navigation */}
      <section className="pb-2 sticky top-0 z-20 bg-[#09090b]/95 backdrop-blur-sm pt-4">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-8 h-8 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
            <Building2 className="w-4 h-4 text-[#7c3aed]" />
          </div>
          <span className="text-sm font-medium text-[#7c3aed] uppercase tracking-wider">
            Real Results
          </span>
        </div>
        <div className="flex gap-2 border-b border-[#1a1a1a] pb-0">
          {useCases.map((c, i) => (
            <button
              key={c.id}
              onClick={() => setActiveCase(i)}
              className={`px-4 py-3 text-sm font-medium transition-all relative ${
                activeCase === i
                  ? "text-white"
                  : "text-[#666] hover:text-[#999]"
              }`}
            >
              {c.tab}
              {activeCase === i && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#7c3aed]"
                />
              )}
            </button>
          ))}
        </div>
      </section>

      <AnimatePresence mode="wait">
        <motion.div
          key={uc.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
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
            <h2 className="text-3xl font-bold mb-8">Where Most Companies Lose Their Edge</h2>
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
            <h2 className="text-3xl font-bold mb-3">The AI Advantage</h2>
            <p className="text-[#888] mb-8">
              The competitive edge comes from matching each task to the right model at the right
              price — not throwing a premium model at everything and hoping for the best.
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
              <h2 className="text-3xl font-bold">How Bonito Gets You There</h2>
            </div>
            <p className="text-[#888] mb-8 max-w-3xl">
              One setup. Every team gets a single API endpoint with intelligent routing, cost
              controls, and full visibility — while your competitors are still juggling three cloud
              consoles.
            </p>

            <div className="grid sm:grid-cols-3 gap-4 mb-8">
              <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
                <Cloud className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
                <h3 className="font-semibold mb-1">Connect once</h3>
                <p className="text-sm text-[#888]">
                  Plug in your cloud accounts. Bonito syncs every model automatically — no more
                  juggling consoles.
                </p>
              </div>
              <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
                <Route className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
                <h3 className="font-semibold mb-1">Route intelligently</h3>
                <p className="text-sm text-[#888]">
                  Right model, right price, every request. Automatic failover means zero downtime
                  when it matters.
                </p>
              </div>
              <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
                <Shield className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
                <h3 className="font-semibold mb-1">Govern everything</h3>
                <p className="text-sm text-[#888]">
                  Budget caps, audit trails, and access controls — the visibility your CFO and CISO
                  have been asking for.
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
            <h2 className="text-3xl font-bold mb-8">The Competitive Edge</h2>
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
        </motion.div>
      </AnimatePresence>

      {/* CTA */}
      <section className="pb-24">
        <div className="bg-gradient-to-br from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-xl p-8 md:p-12 text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-3">
            Your Competitors Aren&apos;t Waiting.
          </h2>
          <p className="text-[#888] mb-6 max-w-xl mx-auto">
            Every month you overspend on AI or manage three separate cloud consoles is a month your
            competitors use to pull ahead. Bonito gets you unified, optimized, and shipping — in
            under an hour.
          </p>
          <div className="flex items-center justify-center gap-4 flex-wrap">
            <Link
              href="/register"
              className="px-6 py-3 rounded-lg bg-[#7c3aed] text-white font-semibold hover:bg-[#6d28d9] transition"
            >
              Start Your Edge
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
    </div>
  );
}
