"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  CheckCircle2,
  Cloud,
  Shield,
  DollarSign,
  Key,
  MessageSquare,
  Box,
  Route,
  BarChart3,
  Bell,
  Terminal,
  ArrowRight,
  ExternalLink,
  Rocket,
} from "lucide-react";

interface TestStep {
  title: string;
  description: string;
  checks: string[];
  endpoint?: string;
}

interface TestSection {
  icon: React.ElementType;
  title: string;
  id: string;
  steps: TestStep[];
}

const sections: TestSection[] = [
  {
    icon: Key,
    title: "1. Authentication",
    id: "auth",
    steps: [
      {
        title: "Register a new account",
        description: "Create a fresh account to test the full onboarding flow.",
        checks: [
          "Go to /register and create an account with a valid email + password",
          "You should be redirected to the dashboard after registration",
          "Check /auth/me returns your user profile",
        ],
        endpoint: "POST /api/auth/register",
      },
      {
        title: "Login / Logout",
        description: "Verify session management works correctly.",
        checks: [
          "Log out, then log back in with the same credentials",
          "Try logging in with a wrong password — should show 'Invalid credentials'",
          "After login, refreshing the page should keep you logged in (JWT stored)",
        ],
        endpoint: "POST /api/auth/login",
      },
    ],
  },
  {
    icon: Cloud,
    title: "2. Connect Providers",
    id: "providers",
    steps: [
      {
        title: "AWS Bedrock",
        description: "Connect your AWS account to pull Bedrock models.",
        checks: [
          "Go to Providers page → click Add Provider → select AWS",
          "Enter Access Key ID, Secret Access Key, and Region (e.g. us-east-1)",
          "Provider should validate (STS get-caller-identity) and show as 'Active'",
          "Models page should now show AWS Bedrock models (Claude, Llama, Titan, etc.)",
        ],
        endpoint: "POST /api/providers/",
      },
      {
        title: "Azure AI Foundry",
        description: "Connect your Azure subscription for OpenAI and Cognitive Services models.",
        checks: [
          "Add Provider → Azure → Enter Tenant ID, Client ID, Client Secret, Subscription ID",
          "Provider should validate (OAuth2 token acquisition) and show as 'Active'",
          "Models page should show Azure OpenAI models (GPT-4, GPT-4o, etc.)",
        ],
        endpoint: "POST /api/providers/",
      },
      {
        title: "Google Vertex AI",
        description: "Connect GCP for Gemini and other Vertex AI models.",
        checks: [
          "Add Provider → GCP → Upload or paste your Service Account JSON",
          "Provider should validate (project lookup) and show as 'Active'",
          "Models page should show Vertex AI models (Gemini, PaLM, etc.)",
        ],
        endpoint: "POST /api/providers/",
      },
    ],
  },
  {
    icon: Box,
    title: "3. Model Catalog",
    id: "models",
    steps: [
      {
        title: "View and filter models",
        description: "All synced models should appear with correct provider tabs.",
        checks: [
          "Models page shows all synced models from connected providers",
          "Filter tabs show ALL connected providers (AWS, Azure, GCP)",
          "If a provider tab shows ⚠️, click Sync to re-fetch models",
          "Search bar filters by model name or ID",
          "Click a model card to see details (pricing, capabilities, context window)",
        ],
        endpoint: "GET /api/models/",
      },
      {
        title: "Model Playground",
        description: "Test models live from the browser.",
        checks: [
          "Click a model → open the Playground tab",
          "Send a test message — response should stream back",
          "Check that token usage and cost appear after the response",
          "Try with different temperature / max token settings",
        ],
        endpoint: "POST /api/models/{id}/playground",
      },
      {
        title: "Model Comparison",
        description: "Compare responses from multiple models side-by-side.",
        checks: [
          "Select 2-4 models for comparison",
          "Send the same prompt to all — responses appear side by side",
          "Compare latency, token usage, and cost across models",
        ],
        endpoint: "POST /api/models/compare",
      },
    ],
  },
  {
    icon: Route,
    title: "4. API Gateway",
    id: "gateway",
    steps: [
      {
        title: "Generate an API key",
        description: "Create a gateway key to route requests through Bonito.",
        checks: [
          "Go to Gateway page → click 'Create Key'",
          "Copy the generated key (bn-xxx format)",
          "Key should appear in the keys list with creation date",
        ],
        endpoint: "POST /api/gateway/keys",
      },
      {
        title: "Make a request through the gateway",
        description: "Test the OpenAI-compatible proxy endpoint.",
        checks: [
          "Use curl or any OpenAI SDK pointed at your Bonito gateway URL",
          "Send a chat completion request with your bn-xxx key",
          "Response should come back in OpenAI format",
          "Check Gateway → Logs to see the request logged with cost + tokens",
        ],
        endpoint: "POST /v1/chat/completions",
      },
      {
        title: "Test from the code snippets",
        description: "The gateway page shows ready-to-use code snippets.",
        checks: [
          "Copy the Python snippet and run it locally",
          "Copy the curl snippet and run it in your terminal",
          "Both should return a valid chat completion response",
        ],
      },
    ],
  },
  {
    icon: Route,
    title: "5. Routing Policies",
    id: "routing",
    steps: [
      {
        title: "Create a routing policy",
        description: "Set up intelligent routing between models/providers.",
        checks: [
          "Go to Routing → Create Policy",
          "Select a strategy: cost-optimized, latency-optimized, balanced, failover, or A/B test",
          "Assign primary and fallback models",
          "For A/B testing: set percentage weights (must sum to 100)",
          "Save the policy — it should appear in the list",
        ],
        endpoint: "POST /api/routing-policies/",
      },
      {
        title: "Test a routing policy",
        description: "Dry-run model selection to verify routing logic.",
        checks: [
          "Click 'Test' on a policy — it should show which model would be selected",
          "For failover: verify the fallback model is picked when primary is down",
          "For A/B: run multiple tests and verify the distribution matches weights",
        ],
        endpoint: "POST /api/routing-policies/{id}/test",
      },
    ],
  },
  {
    icon: Rocket,
    title: "6. Deployments",
    id: "deployments",
    steps: [
      {
        title: "Create a deployment",
        description: "Deploy a model directly into your cloud from the Bonito UI.",
        checks: [
          "Go to Deployments page → click 'Create Deployment'",
          "Select a provider and model",
          "AWS: choose On-demand or Provisioned Throughput (PT requires commitment)",
          "Azure: set TPM capacity for the deployment (Standard or GlobalStandard tier)",
          "GCP: serverless by default — verify access",
          "Deployment should appear in the list with status updates",
        ],
        endpoint: "POST /api/deployments/",
      },
      {
        title: "Monitor deployment status",
        description: "Check that deployment lifecycle notifications work.",
        checks: [
          "Deployment status should update: Creating → Active (or Failed)",
          "In-app notification should appear for deployment status changes",
          "Deployment details page shows provider, model, capacity, and status",
        ],
        endpoint: "GET /api/deployments/{id}",
      },
    ],
  },
  {
    icon: DollarSign,
    title: "7. Cost Intelligence",
    id: "costs",
    steps: [
      {
        title: "View cost dashboard",
        description: "Check real cost data from your cloud providers.",
        checks: [
          "Costs page shows aggregated spending across all providers",
          "Breakdown by provider (AWS, Azure, GCP) with charts",
          "Cost forecast shows projected spending with confidence bounds",
        ],
        endpoint: "GET /api/costs/",
      },
      {
        title: "Cost recommendations",
        description: "Get optimization suggestions.",
        checks: [
          "Recommendations endpoint returns cheaper model alternatives",
          "Cross-provider routing recommendations appear if applicable",
        ],
        endpoint: "GET /api/costs/recommendations",
      },
    ],
  },
  {
    icon: Shield,
    title: "8. Compliance & Governance",
    id: "compliance",
    steps: [
      {
        title: "Run compliance checks",
        description: "Verify security posture across all connected providers.",
        checks: [
          "Compliance page shows check results by provider",
          "AWS: Bedrock logging, IAM permissions, EBS encryption, CloudTrail",
          "Azure: Network rules, RBAC roles, diagnostic settings",
          "GCP: SA permissions, audit logging, VPC Service Controls",
          "Framework mapping: SOC2, HIPAA, GDPR, ISO 27001",
        ],
        endpoint: "GET /api/compliance/checks",
      },
      {
        title: "View audit trail",
        description: "All sensitive actions are logged.",
        checks: [
          "Audit page shows a timeline of actions (logins, provider connects, invocations)",
          "Each entry has timestamp, user, action type, and details",
        ],
        endpoint: "GET /api/audit/",
      },
    ],
  },
  {
    icon: BarChart3,
    title: "9. Analytics & Usage",
    id: "analytics",
    steps: [
      {
        title: "Usage dashboard",
        description: "Track API usage and trends.",
        checks: [
          "Analytics page shows overview cards (requests, tokens, cost, avg latency)",
          "Usage charts show daily/weekly/monthly trends",
          "Cost breakdown by provider and model",
        ],
        endpoint: "GET /api/analytics/overview",
      },
    ],
  },
  {
    icon: Bell,
    title: "10. Notifications & Alerts",
    id: "notifications",
    steps: [
      {
        title: "Notification bell",
        description: "Check that in-app notifications work.",
        checks: [
          "Bell icon in the header shows unread count",
          "Click to see notification list with read/unread states",
          "Mark notifications as read",
        ],
        endpoint: "GET /api/notifications/",
      },
      {
        title: "Alert rules",
        description: "Set up budget and compliance alerts.",
        checks: [
          "Create an alert rule with a budget threshold",
          "Set notification preferences (email, in-app, weekly digest)",
        ],
        endpoint: "POST /api/alert-rules/",
      },
    ],
  },
  {
    icon: MessageSquare,
    title: "11. AI Copilot",
    id: "copilot",
    steps: [
      {
        title: "Chat with the copilot",
        description: "Test the Groq-powered AI assistant.",
        checks: [
          "Click the AI Copilot panel (or Cmd+K)",
          "Ask: 'What are my costs this month?'",
          "Ask: 'Which models are available?'",
          "Ask: 'Run a compliance check'",
          "Responses should be context-aware (knows your providers, models, costs)",
          "Quick action buttons should work (Cost Summary, Compliance Check, etc.)",
        ],
        endpoint: "POST /api/ai/command",
      },
    ],
  },
];

const apiTestSnippet = `# Health check
curl https://getbonito.com/api/health

# Login (replace with your credentials)
TOKEN=$(curl -s -X POST https://getbonito.com/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email":"you@example.com","password":"yourpassword"}' \\
  | jq -r '.access_token')

# List your providers
curl -s https://getbonito.com/api/providers/ \\
  -H "Authorization: Bearer $TOKEN" | jq

# List models
curl -s https://getbonito.com/api/models/ \\
  -H "Authorization: Bearer $TOKEN" | jq

# Gateway request (use your bn-xxx key)
curl -X POST https://getbonito.com/v1/chat/completions \\
  -H "Authorization: Bearer bn-your-key-here" \\
  -H "Content-Type: application/json" \\
  -d '{"model":"claude-3-haiku","messages":[{"role":"user","content":"Hello"}]}'`;

export default function TestingGuidePage() {
  return (
    <div className="max-w-5xl mx-auto px-6 md:px-12">
      {/* Hero */}
      <section className="pt-20 pb-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-[#7c3aed]" />
            </div>
            <span className="text-sm font-medium text-[#7c3aed] uppercase tracking-wider">Testing Guide</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
            How to Test Bonito
          </h1>
          <p className="mt-4 text-lg text-[#888] max-w-2xl">
            A step-by-step guide to validate every feature of the platform.
            Work through each section in order, or jump to the area you want to test.
          </p>
        </motion.div>
      </section>

      {/* Table of Contents */}
      <section className="pb-12">
        <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-[#888] mb-4">Jump to section</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {sections.map((s) => (
              <a
                key={s.id}
                href={`#${s.id}`}
                className="flex items-center gap-2 text-sm text-[#ccc] hover:text-[#7c3aed] transition-colors py-1.5"
              >
                <s.icon className="w-4 h-4 text-[#7c3aed]" />
                {s.title}
              </a>
            ))}
            <a
              href="#api-testing"
              className="flex items-center gap-2 text-sm text-[#ccc] hover:text-[#7c3aed] transition-colors py-1.5"
            >
              <Terminal className="w-4 h-4 text-[#7c3aed]" />
              API Testing (curl)
            </a>
          </div>
        </div>
      </section>

      {/* Prerequisites */}
      <section className="pb-12">
        <div className="bg-gradient-to-br from-[#7c3aed]/10 to-transparent border border-[#7c3aed]/20 rounded-xl p-6 md:p-8">
          <h2 className="text-xl font-bold mb-3">Prerequisites</h2>
          <ul className="space-y-2 text-sm text-[#ccc]">
            <li className="flex items-start gap-2">
              <ArrowRight className="w-4 h-4 text-[#7c3aed] mt-0.5 shrink-0" />
              An account on <a href="https://getbonito.com/register" className="text-[#7c3aed] hover:underline">getbonito.com</a>
            </li>
            <li className="flex items-start gap-2">
              <ArrowRight className="w-4 h-4 text-[#7c3aed] mt-0.5 shrink-0" />
              At least one cloud provider account (AWS, Azure, or GCP) with AI services enabled
            </li>
            <li className="flex items-start gap-2">
              <ArrowRight className="w-4 h-4 text-[#7c3aed] mt-0.5 shrink-0" />
              Provider credentials ready — see the <Link href="/docs" className="text-[#7c3aed] hover:underline">Docs</Link> for what&apos;s needed per provider
            </li>
            <li className="flex items-start gap-2">
              <ArrowRight className="w-4 h-4 text-[#7c3aed] mt-0.5 shrink-0" />
              <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs">curl</code> or <code className="bg-[#0a0a0a] px-1.5 py-0.5 rounded text-xs">jq</code> for API testing (optional)
            </li>
          </ul>
        </div>
      </section>

      {/* Test Sections */}
      {sections.map((section, si) => (
        <section key={section.id} id={section.id} className="pb-16 scroll-mt-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.05 }}
          >
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
                <section.icon className="w-5 h-5 text-[#7c3aed]" />
              </div>
              <h2 className="text-2xl font-bold">{section.title}</h2>
            </div>

            <div className="space-y-6">
              {section.steps.map((step, i) => (
                <div
                  key={i}
                  className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 hover:border-[#7c3aed]/20 transition"
                >
                  <div className="flex items-start justify-between gap-4 mb-3">
                    <h3 className="text-lg font-semibold">{step.title}</h3>
                    {step.endpoint && (
                      <code className="text-xs text-[#7c3aed] bg-[#7c3aed]/10 px-2 py-1 rounded shrink-0">
                        {step.endpoint}
                      </code>
                    )}
                  </div>
                  <p className="text-sm text-[#888] mb-4">{step.description}</p>
                  <ul className="space-y-2">
                    {step.checks.map((check, ci) => (
                      <li key={ci} className="flex items-start gap-3 text-sm text-[#ccc]">
                        <div className="w-5 h-5 rounded border border-[#333] flex items-center justify-center shrink-0 mt-0.5 hover:border-[#7c3aed] transition cursor-pointer">
                          <CheckCircle2 className="w-3 h-3 text-transparent hover:text-[#7c3aed]" />
                        </div>
                        {check}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </motion.div>
        </section>
      ))}

      {/* API Testing */}
      <section id="api-testing" className="pb-16 scroll-mt-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <Terminal className="w-5 h-5 text-[#7c3aed]" />
            </div>
            <h2 className="text-2xl font-bold">API Testing (curl)</h2>
          </div>
          <p className="text-sm text-[#888] mb-4">
            Test the API directly from your terminal. Copy and run these commands:
          </p>
          <div className="bg-[#0a0a0a] border border-[#1a1a1a] rounded-xl p-6 overflow-x-auto">
            <pre className="text-sm text-[#ccc] font-mono whitespace-pre">{apiTestSnippet}</pre>
          </div>
          <p className="text-sm text-[#888] mt-4">
            For automated testing, clone the repo and run:{" "}
            <code className="bg-[#111] px-2 py-1 rounded text-xs text-[#7c3aed]">./scripts/test-api.sh https://getbonito.com your@email.com yourpassword</code>
          </p>
        </motion.div>
      </section>

      {/* Reporting Issues */}
      <section className="pb-24">
        <div className="bg-[#111] border border-[#1a1a1a] rounded-xl p-6 md:p-8 text-center">
          <h2 className="text-xl font-bold mb-2">Found a bug?</h2>
          <p className="text-sm text-[#888] mb-4">
            Open an issue on GitHub or reach out to the team directly.
          </p>
          <div className="flex items-center justify-center gap-4">
            <Link
              href="/contact"
              className="px-4 py-2 rounded-lg bg-[#7c3aed] text-white text-sm font-medium hover:bg-[#6d28d9] transition"
            >
              Contact Us
            </Link>
            <a
              href="https://github.com/ShabariRepo/bonito/issues"
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-lg border border-[#333] text-sm font-medium text-[#ccc] hover:border-[#7c3aed] transition flex items-center gap-2"
            >
              GitHub Issues <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
