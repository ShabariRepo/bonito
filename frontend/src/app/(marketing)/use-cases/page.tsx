"use client";

import { motion } from "framer-motion";
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
} from "lucide-react";

const painPoints = [
  {
    icon: AlertTriangle,
    title: "Fragmented AI access",
    description: "Engineering uses Claude on AWS Bedrock for code generation, data science uses Gemini on Vertex AI for analytics, and marketing wants GPT-4o for ad copy. Three teams, three consoles, three billing dashboards, zero visibility.",
  },
  {
    icon: DollarSign,
    title: "Cost blindspots",
    description: "Nobody knows what AI is actually costing the company. Each team runs their own models with no budget controls. Finance finds out at the end of the quarter.",
  },
  {
    icon: Shield,
    title: "Compliance gaps",
    description: "First-party dealer data flows through AI models with no audit trail. The security team can't answer basic questions: which models touch customer data? Who has access? Are we logging everything?",
  },
  {
    icon: Users,
    title: "No governance",
    description: "Every team picks their own models, manages their own API keys, and builds their own wrappers. There's no standard, no oversight, and no way to enforce policies across the org.",
  },
];

const aiUseCases = [
  {
    icon: FileText,
    title: "Listing descriptions",
    description: "Auto-generate compelling vehicle and trailer listings from spec sheets and photos. What used to take dealers 15 minutes per listing now takes seconds.",
    model: "Claude 3.5 Sonnet (AWS Bedrock)",
    strategy: "Cost-optimized",
  },
  {
    icon: Target,
    title: "Ad copy & targeting",
    description: "Generate personalized ad variations using first-party dealer data. A/B test headlines, descriptions, and CTAs across campaigns at scale.",
    model: "GPT-4o Mini (via Bonito routing)",
    strategy: "Cost-optimized (high volume, lower cost model)",
  },
  {
    icon: BarChart3,
    title: "Market analytics",
    description: "Analyze pricing trends, inventory turnover, and demand signals across thousands of dealers. Surface insights that help dealers price competitively.",
    model: "Gemini 1.5 Pro (GCP Vertex AI)",
    strategy: "Balanced (accuracy matters)",
  },
  {
    icon: MessageSquare,
    title: "Dealer support chat",
    description: "AI-powered support bot that answers dealer questions about the platform, troubleshoots listing issues, and handles routine requests 24/7.",
    model: "Claude 3 Haiku → Claude 3.5 Sonnet (failover)",
    strategy: "Failover (fast model first, upgrade if complex)",
  },
  {
    icon: ImageIcon,
    title: "Image quality scoring",
    description: "Automatically score listing photos for quality, lighting, and composition. Flag low-quality images and suggest retakes before the listing goes live.",
    model: "Gemini 1.5 Flash (GCP Vertex AI)",
    strategy: "Latency-optimized (real-time feedback)",
  },
];

const onboardingSteps = [
  {
    step: "1",
    title: "Create your Bonito account",
    description: "Sign up at getbonito.com. One account covers the entire organization. You'll get an org workspace where you can invite team members later.",
    time: "2 minutes",
  },
  {
    step: "2",
    title: "Connect AWS Bedrock",
    description: "Go to Providers → Add Provider → AWS. Enter your IAM Access Key ID and Secret Access Key. Bonito validates the credentials against STS and checks Bedrock permissions automatically. Choose Quick Start (managed role) for evaluation, or Enterprise mode for least-privilege IAM policies scoped per capability.",
    time: "3 minutes",
    detail: "Core permissions: bedrock:ListFoundationModels, GetFoundationModel, InvokeModel, InvokeModelWithResponseStream, sts:GetCallerIdentity. Add Provisioning, Model Activation, or Cost Tracking policies only as needed.",
  },
  {
    step: "3",
    title: "Connect GCP Vertex AI",
    description: "Add Provider → GCP. Paste your Service Account JSON key file and enter the Project ID. Bonito validates access to Vertex AI APIs. Use Quick Start (aiplatform.user role) or Enterprise mode with a custom role containing only the exact permissions Bonito needs.",
    time: "3 minutes",
    detail: "Core permissions: aiplatform.publishers.get, publisherModels.get, endpoints.predict, resourcemanager.projects.get. Add endpoint management and billing permissions only as needed.",
  },
  {
    step: "4",
    title: "See all your models in one place",
    description: "Bonito automatically syncs every available model from your connected providers: Claude, Llama, Titan from AWS Bedrock and Gemini from GCP Vertex. Filter by provider, search by name, and enable models with one click — no need to visit each cloud console. Bulk-activate up to 20 models at once.",
    time: "1 minute",
  },
  {
    step: "5",
    title: "Test models in the playground",
    description: "Click any model to open the playground. Send test prompts, compare responses from different models side by side (up to 4 at once), and see real token usage and cost per request. Try your actual use cases here before committing.",
    time: "10 minutes",
  },
  {
    step: "6",
    title: "Set up routing policies",
    description: "Create routing policies for each use case. Cost-optimized routing for ad copy (auto-selects cheapest model). Failover chain for dealer support (Haiku → Sonnet fallback). A/B testing for analytics (90% Gemini Pro / 10% new model). Each policy is testable with dry-run before going live.",
    time: "10 minutes",
  },
  {
    step: "7",
    title: "Generate API keys for each team",
    description: "Go to Gateway → Create Key. Generate a unique API key for each team or service. The ad tech team gets their key, engineering gets theirs, data science gets theirs. Each key routes through the policies you defined.",
    time: "5 minutes",
  },
  {
    step: "8",
    title: "Integrate with one line of code",
    description: "Your teams swap their existing SDK endpoint to Bonito's gateway URL (gateway.getbonito.com/v1). Same OpenAI-compatible API format they already use. No code rewrite, just a config change. Bonito handles routing, failover, and logging transparently.",
    time: "5 minutes per service",
    detail: "Works with any OpenAI-compatible SDK: Python, Node.js, Go, curl. Also available via bonito-cli for terminal workflows.",
  },
  {
    step: "9",
    title: "Monitor costs and compliance",
    description: "The Costs dashboard shows real-time spending across all providers, broken down by team, model, and use case. Set budget alerts and get in-app + email notifications so finance never gets surprised. The Compliance page runs automated checks against SOC2 and HIPAA frameworks.",
    time: "Ongoing",
  },
];

const results = [
  { metric: "40–70%", label: "lower AI spend", detail: "By routing routine requests to cost-efficient models instead of using premium models for everything" },
  { metric: "Minutes", label: "to connect a provider", detail: "Paste your service account credentials, Bonito validates and syncs models automatically" },
  { metric: "Every request", label: "logged and tracked", detail: "User, model, cost, and token usage captured for every request routed through Bonito" },
  { metric: "3→1", label: "consoles to manage", detail: "One dashboard instead of juggling AWS, GCP, and Azure consoles separately" },
];

const pricingComparisons = [
  { model: "Claude 3.5 Sonnet", tier: "Premium", input: "$3.00", output: "$15.00", color: "text-red-400" },
  { model: "GPT-4o", tier: "Premium", input: "$5.00", output: "$15.00", color: "text-red-400" },
  { model: "GPT-4o Mini", tier: "Economy", input: "$0.15", output: "$0.60", color: "text-green-400" },
  { model: "Claude 3 Haiku", tier: "Economy", input: "$0.25", output: "$1.25", color: "text-green-400" },
  { model: "Gemini 1.5 Flash", tier: "Economy", input: "$0.075", output: "$0.30", color: "text-green-400" },
];

const routingScenarios = [
  {
    label: "Using GPT-4o for everything",
    before: "$10.00",
    after: "$3.27",
    savings: "67%",
    detail: "Route 70% of routine traffic to GPT-4o Mini, keep 30% on GPT-4o for complex tasks",
  },
  {
    label: "Using Claude 3.5 Sonnet for everything",
    before: "$9.00",
    after: "$3.23",
    savings: "64%",
    detail: "Route 70% to Claude 3 Haiku, keep 30% on Sonnet for nuanced work",
  },
  {
    label: "Cross-provider routing",
    before: "$9.00",
    after: "$2.83",
    savings: "69%",
    detail: "Sonnet for complex tasks, Gemini Flash for simple ones — best price across clouds",
  },
];

export default function UseCasesPage() {
  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12">
      {/* Hero */}
      <section className="pt-20 pb-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-[#7c3aed]" />
            </div>
            <span className="text-sm font-medium text-[#7c3aed] uppercase tracking-wider">Use Case</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            How a Vehicle Marketplace Unified Their AI Across AWS and GCP
          </h1>
          <p className="mt-4 text-lg text-[#888] max-w-3xl">
            A real-world walkthrough: a multi-cloud enterprise with 500+ dealers, first-party advertising data,
            and five AI use cases across two cloud providers. From zero visibility to full governance in under an hour.
          </p>
        </motion.div>
      </section>

      {/* Company Profile */}
      <section className="pb-12">
        <div className="bg-gradient-to-br from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-xl p-6 md:p-8">
          <h2 className="text-xl font-bold mb-4">The Company</h2>
          <div className="grid sm:grid-cols-2 gap-6 text-sm text-[#ccc]">
            <div className="space-y-3">
              <div><span className="text-[#888]">Industry:</span> Online vehicle & trailer marketplace</div>
              <div><span className="text-[#888]">Scale:</span> 500+ dealers, millions of listings, national ad network</div>
              <div><span className="text-[#888]">Cloud:</span> AWS (primary infrastructure) + GCP (data & ML workloads)</div>
            </div>
            <div className="space-y-3">
              <div><span className="text-[#888]">Teams using AI:</span> Engineering, Data Science, Ad Tech, Dealer Support</div>
              <div><span className="text-[#888]">Data:</span> First-party dealer and buyer intent data used for targeted advertising</div>
              <div><span className="text-[#888]">Goal:</span> Add AI across the product without the operational overhead</div>
            </div>
          </div>
        </div>
      </section>

      {/* The Problem */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-8">The Problem</h2>
        <p className="text-[#888] mb-8 max-w-3xl">
          The company wants to use AI everywhere — listing generation, ad copy, analytics, dealer support, image scoring.
          But with two cloud providers and four teams, they&apos;re heading toward the same mess every enterprise hits:
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          {painPoints.map((point, i) => (
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
        <p className="text-[#888] mb-8">Five AI-powered features, each with different requirements for cost, latency, and model quality.</p>
        <div className="space-y-4">
          {aiUseCases.map((uc, i) => (
            <motion.div
              key={uc.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.05 }}
              className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 hover:border-[#7c3aed]/20 transition"
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center shrink-0">
                  <uc.icon className="w-5 h-5 text-[#7c3aed]" />
                </div>
                <div className="flex-1">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <h3 className="font-semibold">{uc.title}</h3>
                    <span className="text-xs text-[#7c3aed] bg-[#7c3aed]/10 px-2 py-1 rounded shrink-0">{uc.strategy}</span>
                  </div>
                  <p className="text-sm text-[#888] mb-2">{uc.description}</p>
                  <p className="text-xs text-[#666]">
                    <span className="text-[#888]">Model:</span> {uc.model}
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
          Instead of each team building their own AI integration, managing their own credentials, and tracking their own costs,
          the platform team sets up Bonito once. Every team gets a single API endpoint, governed routing, and full visibility.
        </p>

        <div className="grid sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
            <Cloud className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
            <h3 className="font-semibold mb-1">Connect once</h3>
            <p className="text-sm text-[#888]">Plug in your AWS and GCP service accounts. Bonito handles the rest.</p>
          </div>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
            <Route className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
            <h3 className="font-semibold mb-1">Route intelligently</h3>
            <p className="text-sm text-[#888]">Each use case gets the right model at the right price with automatic failover.</p>
          </div>
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 text-center">
            <Shield className="w-8 h-8 text-[#7c3aed] mx-auto mb-3" />
            <h3 className="font-semibold mb-1">Govern everything</h3>
            <p className="text-sm text-[#888]">Costs, compliance, audit trails, and access controls from one dashboard.</p>
          </div>
        </div>
      </section>

      {/* Step by Step */}
      <section className="pb-16">
        <h2 className="text-3xl font-bold mb-3">Step-by-Step Onboarding</h2>
        <p className="text-[#888] mb-8">
          From &quot;we have service account credentials&quot; to &quot;all teams are using AI through one gateway&quot; in under an hour.
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
                    <span className="text-xs text-[#888] bg-[#1a1a1a] px-2 py-1 rounded shrink-0">{step.time}</span>
                  </div>
                  <p className="text-sm text-[#888] leading-relaxed">{step.description}</p>
                  {step.detail && (
                    <p className="text-xs text-[#666] mt-2 bg-[#0a0a0a] rounded px-3 py-2 font-mono">{step.detail}</p>
                  )}
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
          {results.map((r, i) => (
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
        <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-[#7c3aed]" />
            </div>
            <h2 className="text-3xl font-bold">The Math Behind 40–70% Savings</h2>
          </div>
          <p className="text-[#888] mb-8 max-w-3xl">
            Most enterprises pick a &quot;good&quot; model and use it for everything. But 60–80% of LLM requests are routine — 
            classification, summarization, template filling, simple Q&amp;A. These tasks don&apos;t need a frontier model. 
            The pricing gap between premium and economy models is 10–25x.
          </p>

          {/* Pricing Table */}
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl overflow-hidden mb-8">
            <div className="px-6 py-4 border-b border-[#1a1a1a]">
              <h3 className="font-semibold">Model Pricing per 1M Tokens (actual provider pricing)</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-[#888] border-b border-[#1a1a1a]">
                    <th className="text-left px-6 py-3 font-medium">Model</th>
                    <th className="text-left px-6 py-3 font-medium">Tier</th>
                    <th className="text-right px-6 py-3 font-medium">Input</th>
                    <th className="text-right px-6 py-3 font-medium">Output</th>
                  </tr>
                </thead>
                <tbody>
                  {pricingComparisons.map((p) => (
                    <tr key={p.model} className="border-b border-[#1a1a1a]/50 hover:bg-[#1a1a1a]/30">
                      <td className="px-6 py-3 font-medium">{p.model}</td>
                      <td className={`px-6 py-3 ${p.color}`}>{p.tier}</td>
                      <td className="px-6 py-3 text-right font-mono">{p.input}</td>
                      <td className="px-6 py-3 text-right font-mono">{p.output}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Routing Scenarios */}
          <div className="bg-[#111] border border-[#1a1a1a] rounded-xl overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-[#1a1a1a]">
              <h3 className="font-semibold">What Intelligent Routing Actually Saves</h3>
              <p className="text-xs text-[#888] mt-1">Blended cost per 1K tokens, assuming 70% of traffic is routine</p>
            </div>
            <div className="divide-y divide-[#1a1a1a]/50">
              {routingScenarios.map((s) => (
                <div key={s.label} className="px-6 py-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium">{s.label}</span>
                    <span className="text-lg font-bold text-green-400">{s.savings} savings</span>
                  </div>
                  <div className="flex items-center gap-4 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-[#888]">Before:</span>
                      <span className="text-sm font-mono text-red-400">{s.before}</span>
                    </div>
                    <ArrowRight className="w-4 h-4 text-[#888]" />
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-[#888]">After:</span>
                      <span className="text-sm font-mono text-green-400">{s.after}</span>
                    </div>
                    <span className="text-xs text-[#888]">per 1K tokens</span>
                  </div>
                  <p className="text-xs text-[#666]">{s.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-[#666] italic">
            Pricing based on published rates from OpenAI, Anthropic, and Google as of early 2026. 
            Actual savings depend on traffic mix and which models your teams currently use. 
            Savings are highest for teams defaulting to a single premium model for all tasks.
          </p>
        </motion.div>
      </section>

      {/* CTA */}
      <section className="pb-24">
        <div className="bg-gradient-to-br from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-xl p-8 md:p-12 text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-3">Sound like your team?</h2>
          <p className="text-[#888] mb-6 max-w-xl mx-auto">
            If you&apos;re running AI workloads across multiple cloud providers and want unified control without the infrastructure overhead, Bonito was built for you.
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
