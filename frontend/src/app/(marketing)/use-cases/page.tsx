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
  {
    id: "ad-tech-programmatic",
    tab: "Ad-Tech / Programmatic",
    title: "How an Ad-Tech Platform Cut Cloud AI Costs by 30% with Multi-Cloud Routing",
    subtitle:
      "A real-world cost analysis: a programmatic advertising platform managing $40M+ in annual ad spend deploys 7 Bonobot agents across AWS, GCP, and Azure — cutting AI costs by 30% and automating 3 FTE hours of daily campaign operations.",
    company: {
      industry: "Advertising Technology / Programmatic Media",
      scale: "48 employees, 85+ brand clients, $40M+ managed ad spend/year",
      cloud: "AWS Bedrock + GCP Vertex AI + Azure OpenAI (all three)",
      teams: "Engineering, Data Science, Sales, Creative",
      data: "Campaign analytics across Meta/Google/TikTok/CTV, audience segments, creative assets, bid performance data",
      goal: "Unify 3 cloud AI stacks into one gateway with smart routing and deploy AI agents for campaign automation",
    },
    painPoints: [
      {
        icon: DollarSign,
        title: "$8,200/month across 3 clouds — unoptimized",
        description:
          "AWS for creative generation, GCP for audience ML, Azure for ad copy. Every team defaulted to the most expensive model available. Bulk ad copy running through GPT-4o when Gemini Flash would produce identical quality at a fraction of the cost.",
      },
      {
        icon: AlertTriangle,
        title: "Wrong models for the job",
        description:
          "The team was using GPT-4o for everything — generating 50 ad headline variations, writing product descriptions, running sentiment analysis. 70% of requests were routine text generation that didn't need a frontier model, but there was no routing layer to differentiate.",
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
          "When a client asked 'how much AI cost went into my campaign optimization?', nobody could answer. AI spend was a single line item buried in cloud bills — impossible to allocate to specific clients or campaigns.",
      },
    ],
    aiUseCases: [
      {
        icon: Bot,
        title: "Creative Director Agent",
        description:
          "Generates ad creative briefs, headlines, and copy variations for DTC brands across Meta, Google, and TikTok formats. Produces 3 variations per request: safe, bold, and experimental. Handles character limits and platform-specific best practices automatically.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized — high volume creative generation",
      },
      {
        icon: BarChart3,
        title: "Bid Optimizer Agent",
        description:
          "Analyzes campaign metrics (CPM, CPC, CPA, ROAS, frequency) and recommends bid adjustments, budget reallocations, and audience changes. Flags anomalies like frequency spikes and CPM inflation with data-driven reasoning.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced — analytical reasoning required",
      },
      {
        icon: Users,
        title: "Audience Analyst Agent",
        description:
          "Segments customer cohorts by demographics, channel, and LTV. Designs lookalike audience strategies and diagnoses retargeting fatigue. Recommends seed audiences and testing sequences for Meta Custom Audiences and Google Customer Match.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced — complex segmentation logic",
      },
      {
        icon: FileText,
        title: "Performance Reporter Agent",
        description:
          "Generates client-facing weekly performance reports with executive summaries, WoW/MoM trends, channel breakdowns, and recommended next steps. Handles escalation reports when ROAS drops with honest analysis and recovery plans.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Cost-optimized — structured report generation",
      },
      {
        icon: Globe,
        title: "Market Research Agent",
        description:
          "Analyzes competitive landscapes, market trends, and industry benchmarks for DTC verticals. Provides actionable insights on CAC trends, channel dynamics, and positioning strategies for client campaigns.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Cost-optimized — research synthesis",
      },
      {
        icon: Search,
        title: "Contract Analyzer Agent",
        description:
          "Reviews media plans, insertion orders, and client agreements. Calculates effective rates, verifies budget allocations against campaign objectives, and flags unusual terms or performance bonus structures.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced — contract reasoning",
      },
      {
        icon: MessageSquare,
        title: "Sentiment Monitor Agent",
        description:
          "Analyzes social media mentions and reviews for brand clients. Classifies sentiment, detects urgency, and recommends whether to pause ad campaigns when brand safety risks emerge.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized — high volume classification",
      },
    ],
    results: [
      {
        metric: "30%",
        label: "AI cost reduction",
        detail: "$8,200/mo → $5,800/mo by routing bulk copy to Gemini Flash instead of GPT-4o",
      },
      {
        metric: "3.5:1",
        label: "ROI",
        detail: "$122K annual savings vs $35K platform cost — payback in under 4 months",
      },
      {
        metric: "7 agents",
        label: "across 2 projects",
        detail: "Campaign Operations (4 agents) + Client Intelligence (3 agents) — fully autonomous",
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
        "Every number below comes from actual API calls through Bonito's production gateway to live AWS, GCP, and Azure endpoints. 74 gateway requests tracked, 36,952 tokens processed, costs calculated from published provider pricing. Then projected forward to production scale.",
      models: [
        { model: "Amazon Nova Lite", cost: "$0.07 / 1K req", annual: "$1,250/yr", color: "text-green-400" },
        { model: "Gemini 2.0 Flash", cost: "$0.10 / 1K req", annual: "$1,800/yr", color: "text-green-400" },
        { model: "GPT-4o Mini", cost: "$0.17 / 1K req", annual: "$3,070/yr", color: "text-yellow-400" },
        { model: "Bonobot Platform (7 agents)", cost: "$349/agent/mo", annual: "$29,316/yr", color: "text-blue-400" },
      ],
      scenarios: [
        {
          label: "Before Bonito — 3 clouds, no routing, no agents",
          cost: "$98,400 / year",
          detail: "$8,200/mo across AWS + GCP + Azure. Every request hitting premium models. No cost visibility, no campaign-level attribution, no automation.",
        },
        {
          label: "With Bonito — smart routing + 7 Bonobot agents",
          cost: "$104,904 / year",
          detail: "$5,800/mo AI (30% reduction via routing) + $2,942/mo platform ($499 Pro + 7 × $349 agents). Slightly higher total, but agents automate 3 FTE hours/day.",
          highlight: true,
        },
        {
          label: "Net value — labor + cost savings combined",
          cost: "$122,800 / year saved",
          detail: "$94K labor savings (3 FTE hours/day of report generation, bid analysis, audience research) + $28.8K AI cost reduction from smart routing.",
        },
      ],
      savingsSummary: [
        { vs: "Return on investment", saved: "3.5:1 ROI", pct: "3.5x", detail: "$122.8K total savings ÷ $35.3K platform cost" },
        { vs: "AI cost reduction from routing", saved: "$28,800/yr saved (30%)", pct: "30%", detail: "$98.4K/yr → $69.6K/yr with Gemini Flash for bulk copy" },
      ],
      footnote:
        "Based on 74 production gateway requests (36,952 tokens) during E2E stress testing on February 22, 2026. AWS: 36 requests (34 successful), GCP: 21 requests (21 successful), Azure: 17 requests (model deployment pending). Annual projections extrapolated to ~500 requests/day at production scale. Bonobot pricing: $349/mo per hosted agent, $499/mo Pro tier. Labor savings estimated at $75K/yr per analyst for automated campaign operations work.",
    },
  },
  {
    id: "healthcare-clinical-ai",
    tab: "Healthcare / Clinical AI",
    title: "How a Healthcare IT Company Achieved 12.7:1 ROI with HIPAA-Compliant AI Agents",
    subtitle:
      "A real-world deployment: a clinical decision support platform serving 23 hospital networks deploys 10 Bonobot agents across Clinical Ops, Revenue Cycle, and Quality & Safety — projecting $606K in annual value against $47.8K platform cost.",
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
          "Every AI inference touching patient data requires a complete audit trail — who accessed what model, with what data, when. With three separate cloud providers, the compliance team was conducting three separate reviews per audit cycle, spending 40+ hours per cycle just compiling evidence.",
      },
      {
        icon: DollarSign,
        title: "$24,000/month across 3 clouds — fragmented billing",
        description:
          "AWS for documentation summarization, GCP for long-context clinical reasoning, Azure for medical coding. Each team managed their own billing. The board wanted ROI data on AI spend vs clinical outcomes — nobody could produce it.",
      },
      {
        icon: AlertTriangle,
        title: "No governance on clinical AI workloads",
        description:
          "Clinical AI models were running without budget caps, rate limits, or credential isolation. One misconfigured pipeline could theoretically access patient data across departments. In healthcare, that's not just a security risk — it's a regulatory violation.",
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
          "Classifies incoming patient cases by ESI (Emergency Severity Index) levels 1-5 based on chief complaint, vitals, and history. Routes to appropriate department. Considers red flags and comorbidities — always errs on the side of caution.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Quality-first — clinical safety critical",
      },
      {
        icon: FileText,
        title: "Clinical Documentation Specialist",
        description:
          "Transforms unstructured physician dictations into structured SOAP notes, discharge summaries, and consultation reports following HL7 FHIR standards. Flags missing critical information. Never fabricates clinical findings.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized — high volume documentation",
      },
      {
        icon: Shield,
        title: "Drug Interaction Checker",
        description:
          "Analyzes medication lists for drug-drug interactions, contraindications, and dosing errors. Classifies by severity (Critical/Major/Moderate/Minor). Considers patient-specific factors including renal function, age, and pregnancy status.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Quality-first — patient safety",
      },
      {
        icon: BookOpen,
        title: "Care Pathway Recommender",
        description:
          "Analyzes patient cases against AHA/ACC, NCCN, ADA, and GOLD clinical guidelines. Identifies deviations from evidence-based care pathways and suggests interventions with NNT/NNH data. Cites specific guideline versions.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced — guideline reasoning",
      },
      {
        icon: BarChart3,
        title: "Medical Coder Agent",
        description:
          "Assigns ICD-10-CM diagnosis codes and CPT procedure codes from clinical documentation. Follows CMS sequencing rules, considers laterality and severity specificity. Generates CDI queries when documentation gaps prevent optimal coding.",
        model: "GPT-4o Mini (Azure OpenAI)",
        strategy: "Quality-first — structured output",
      },
      {
        icon: MessageSquare,
        title: "Denial Manager Agent",
        description:
          "Analyzes insurance claim denials, assesses appeal viability, and drafts appeal letters with supporting clinical evidence. References InterQual and Milliman criteria for medical necessity arguments. Tracks denial patterns for root cause analysis.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Balanced — legal/clinical reasoning",
      },
      {
        icon: Target,
        title: "Revenue Forecaster Agent",
        description:
          "Analyzes billing data, reimbursement trends, payer mix, and AR aging to forecast quarterly revenue. Factors in CMS fee schedule updates, seasonal patterns, and denial rate trends. Flags optimization opportunities with dollar impact.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized — data analysis",
      },
      {
        icon: Search,
        title: "Adverse Event Detector",
        description:
          "Monitors clinical data for medication errors, falls, hospital-acquired infections, and unexpected deterioration. Classifies by severity and preventability. Generates structured incident reports per Joint Commission requirements.",
        model: "Gemini 2.0 Flash (GCP Vertex AI)",
        strategy: "Quality-first — safety critical",
      },
      {
        icon: Users,
        title: "Readmission Risk Analyzer",
        description:
          "Calculates LACE and HOSPITAL scores for discharge patients. Identifies high-risk patients based on comorbidity burden, medication complexity, and social determinants. Recommends targeted interventions to reduce 30-day readmission risk.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Balanced — risk stratification",
      },
      {
        icon: Headphones,
        title: "Quality Metrics Dashboard Narrator",
        description:
          "Interprets CMS Star ratings, HCAHPS scores, PSI/HAC rates, and core measures. Generates executive-level quality summaries comparing against national benchmarks and peer hospitals. Identifies top 3 improvement priorities with action plans.",
        model: "Amazon Nova Lite (AWS Bedrock)",
        strategy: "Cost-optimized — narrative generation",
      },
    ],
    results: [
      {
        metric: "12.7:1",
        label: "ROI",
        detail: "$606K annual value vs $47.8K platform cost — payback in under 30 days",
      },
      {
        metric: "10 agents",
        label: "across 3 projects",
        detail: "Clinical Ops (4) + Revenue Cycle (3) + Quality & Safety (3) — with full HIPAA audit trails",
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
        "Every number below comes from actual API calls through Bonito's production gateway to live AWS and GCP endpoints. 40 gateway requests tracked, 18,618 tokens processed, with complete audit trails generated for every interaction — the same audit infrastructure that supports HIPAA compliance in production.",
      models: [
        { model: "Amazon Nova Lite", cost: "$0.07 / 1K req", annual: "$1,250/yr", color: "text-green-400" },
        { model: "Gemini 2.0 Flash", cost: "$0.10 / 1K req", annual: "$1,800/yr", color: "text-green-400" },
        { model: "GPT-4o Mini", cost: "$0.17 / 1K req", annual: "$3,070/yr", color: "text-yellow-400" },
        { model: "Bonobot Platform (10 agents)", cost: "$349/agent/mo", annual: "$41,880/yr", color: "text-blue-400" },
      ],
      scenarios: [
        {
          label: "Before Bonito — 3 clouds, no governance, manual workflows",
          cost: "$468,000 / year",
          detail: "$24K/mo AI spend across AWS + GCP + Azure. Plus $180K/yr for 2.5 FTE managing AI infrastructure, manual coding reviews, and denial appeal drafting.",
        },
        {
          label: "With Bonito — governed agents + smart routing",
          cost: "$249,468 / year",
          detail: "$16,800/mo AI (30% reduction via routing) + $3,989/mo platform ($499 Pro + 10 × $349 agents). Full HIPAA audit trails, budget caps, credential isolation included.",
          highlight: true,
        },
        {
          label: "Additional value — clinical outcome improvements",
          cost: "$340,000 / year recovered",
          detail: "Est. 20% fewer excess readmissions ($100K penalty reduction) + better coding/denial management ($240K revenue recovery). Conservative estimates from industry benchmarks.",
        },
      ],
      savingsSummary: [
        { vs: "Return on investment", saved: "12.7:1 ROI", pct: "12.7x", detail: "$606K total value ÷ $47.9K platform cost" },
        { vs: "Direct cost savings", saved: "$218K/yr saved", pct: "47%", detail: "$86K AI routing savings + $180K labor automation — offset by $47.9K platform" },
      ],
      footnote:
        "Based on 40 production gateway requests (18,618 tokens) during E2E stress testing on February 22, 2026. AWS: 18 requests (17 successful), GCP: 6 requests (5 successful), Azure: 16 requests (deployment pending). Revenue recovery and readmission reduction estimates are conservative projections based on published industry benchmarks for AI-assisted medical coding (AHIMA 2025) and CMS readmission penalty data. All agent sessions generated complete audit logs suitable for HIPAA compliance review.",
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
      {/* Tab Navigation */}
      <section className="pt-20 pb-2 sticky top-0 z-20 bg-[#09090b]/95 backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-8 h-8 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
            <Building2 className="w-4 h-4 text-[#7c3aed]" />
          </div>
          <span className="text-sm font-medium text-[#7c3aed] uppercase tracking-wider">
            Use Cases
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
    </div>
  );
}
