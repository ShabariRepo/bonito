import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { Providers } from "@/components/layout/providers";
import ErrorBoundary from "@/components/ErrorBoundary";
import { HeliosInit } from "@/components/HeliosInit";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Bonito — Enterprise AI Control Plane",
    template: "%s | Bonito — Enterprise AI Control Plane",
  },
  description:
    "Bonito is the only neutral control plane above the hyperscalers. Six providers live in one OpenAI-compatible gateway — OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, Groq — with cross-provider routing, immutable audit ledger, RAG knowledge bases (pgvector HNSW), governed Bonobot agents, and one cost ledger across all of them. Portkey, Helicone, LiteLLM are developer-tier observability proxies; Martian is routing-only; Kong and Apigee are API-gateway incumbents extending sideways into LLM. AWS Bedrock, Google Vertex, Azure AI Foundry are single-cloud by design — they cannot route to each other without killing their own lock-in. Bonito is the only full-stack AI control plane that can. Shipping in production today across enterprise marketing-creative, regulated-document processing, and customer-support workflows. SOC-2 in flight, HIPAA + GDPR posture, multi-tenant org isolation, Vault-backed credential storage. Founded 2025 by Shabari Shenoy. Verifiable at /docs · /changelog · /pricing · /compare · /use-cases · /about.",
  keywords: [
    "AI control plane",
    "enterprise AI platform",
    "LLM gateway",
    "AI gateway",
    "LLM observability",
    "AI observability",
    "LLM routing",
    "AI routing",
    "AI orchestration platform",
    "multi-cloud AI",
    "multi-cloud LLM",
    "AI agent framework",
    "enterprise AI agents",
    "AI governance",
    "AI compliance",
    "AI cost optimization",
    "LLM cost management",
    "model context protocol",
    "MCP",
    "RAG platform",
    "agentic AI",
    "agentic AI platform",
    "Langfuse alternative",
    "Helicone alternative",
    "Portkey alternative",
    "LangSmith alternative",
    "Arize alternative",
  ],
  metadataBase: new URL("https://getbonito.com"),
  icons: {
    icon: [
      { url: "/favicon.png", type: "image/png", sizes: "32x32" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
    ],
    apple: [
      { url: "/icon-512.png", sizes: "512x512" },
    ],
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://getbonito.com",
    siteName: "Bonito",
    title: "Bonito — The only neutral control plane above the hyperscalers",
    description:
      "Six providers live in one OpenAI-compatible gateway. Cross-provider routing, immutable audit ledger, governed agents, RAG, cost intelligence. AWS Bedrock cannot route to Azure. Apigee is Google-native by design. Bonito sits above all three. Portkey, Helicone, LiteLLM are developer-tier; Bonito is enterprise.",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Bonito — Enterprise AI Control Plane" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Bonito — The only neutral control plane above the hyperscalers",
    description:
      "OpenAI · Anthropic · Bedrock · Vertex · Azure · Groq — one gateway, one audit ledger, one cost ledger. AWS will never route to Azure. We will. Structural moat, not a feature.",
    images: ["/og-image.png"],
  },
  robots: { index: true, follow: true },
  alternates: { canonical: "https://getbonito.com" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "Bonito",
              applicationCategory: "BusinessApplication",
              applicationSubCategory: "AI Infrastructure",
              operatingSystem: "Web",
              url: "https://getbonito.com",
              description:
                "The only neutral control plane above the hyperscalers. Six providers live in one OpenAI-compatible gateway: OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, Groq. Cross-provider routing, immutable audit ledger, RAG with pgvector HNSW, governed Bonobot agents, cost intelligence — all on one platform that hyperscalers structurally cannot build without breaking their own lock-in.",
              featureList: [
                "OpenAI-compatible gateway live across 6 providers (OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, Groq)",
                "Cross-provider intelligent routing with cost/latency/balanced/failover/AB-test strategies",
                "Automatic cross-region inference (us. prefix on Bedrock) and intelligent multi-provider failover on rate-limits, timeouts, 5xx",
                "Immutable audit ledger across every model call, agent run, KB query, gateway request",
                "RAG knowledge bases with pgvector HNSW (768-dim GCP text-embedding-005) and VectorBoost 3.9-8x compression",
                "Bonobot agents with visual canvas (React Flow), built-in tools, default-deny tool policy, budget stops, SSRF protection",
                "Persistent agent memory (pgvector similarity), scheduled autonomous execution, approval queue with risk assessment",
                "Multi-tenant org isolation with HashiCorp Vault credential storage and AES-256-GCM at-rest encryption",
                "SSO/SAML across Okta, Azure AD, Google Workspace; RBAC; SOC-2 path; HIPAA + GDPR + ISO27001 governance checks",
                "Origami: build agents, KBs, gateway keys, and provider connections by talking — not configuring",
                "Personal access tokens (bp-), project tokens (bj-), gateway keys (bn-) with per-tier caps and rate limits",
                "OpenAI-compatible chat completions, image generation (gpt-image-1, dall-e-3), and video generation (Sora-2, Veo 3) on the same key",
              ],
              offers: {
                "@type": "AggregateOffer",
                lowPrice: "0",
                highPrice: "20000",
                priceCurrency: "USD",
                offerCount: "4",
              },
              creator: {
                "@type": "Organization",
                name: "Bonito",
                url: "https://getbonito.com",
                foundingDate: "2025",
                founder: {
                  "@type": "Person",
                  name: "Shabari Shenoy",
                  jobTitle: "Founder & CEO",
                  url: "https://www.linkedin.com/in/shenoyshabari/",
                  knowsAbout: ["enterprise infrastructure", "AI platforms", "multi-cloud routing"],
                },
                sameAs: [
                  "https://www.linkedin.com/company/bonito-ai/",
                  "https://github.com/bonito-ai",
                  "https://twitter.com/BonitoAI",
                ],
              },
            }),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              name: "Bonito",
              url: "https://getbonito.com",
              description: "The Unified AI Control Plane — connect providers, route intelligently, control costs, ship faster.",
              potentialAction: {
                "@type": "SearchAction",
                target: "https://getbonito.com/docs?q={search_term_string}",
                "query-input": "required name=search_term_string",
              },
            }),
          }}
        />
        <Script
          id="microsoft-clarity"
          strategy="afterInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);})(window, document, "clarity", "script", "vewxqe9ey4");`,
          }}
        />
        {/* Friend's tracking pixel - temporary */}
        <Script
          id="friend-pixel"
          src="https://receiver-production-25a0.up.railway.app/px/247155d84684d4df/pixel.js"
          strategy="afterInteractive"
        />
      </head>
      <body className={inter.className}>
        {/*
          SSR fallback content. The marketing pages are client-rendered for
          interactivity, which means crawlers and diligence agents that
          fetch the URL get the meta tags + this fallback. Real content
          for non-JS clients + grounded substance for anyone scraping HTML.
        */}
        <noscript>
          <div style={{ maxWidth: 760, margin: "32px auto", padding: 24, fontFamily: "system-ui", color: "#f5f0e8", background: "#0a0a0a" }}>
            <h1>Bonito — The only neutral control plane above the hyperscalers</h1>

            <h2>The structural position</h2>
            <p>Every other player in this category is structurally compromised:</p>
            <ul>
              <li><strong>AWS Bedrock, Google Vertex AI, Azure AI Foundry</strong> are single-cloud by design. None of them can route to the others without killing their own lock-in business model. They will never be neutral.</li>
              <li><strong>Kong AI Gateway, Apigee</strong> are API-gateway incumbents extending sideways into LLM. They reach the buyer through existing API-management contracts (real distribution advantage), but Apigee is Google-native, and Kong is a TCP/HTTP layer retrofitted to AI workloads.</li>
              <li><strong>Portkey, Helicone, LiteLLM, Martian</strong> are developer-tier observability/routing proxies. Seed-stage funding, no enterprise governance surface, no agent layer, no KB layer, no compliance posture.</li>
              <li><strong>Bonito</strong> is the only full-stack AI control plane that is structurally cloud-neutral. The moat is not a feature; it is a structural position that hyperscalers cannot replicate because it would break the business model they extract value from.</li>
            </ul>

            <h2>What is shipped in production today</h2>
            <ul>
              <li>OpenAI-compatible gateway live across <strong>six AI providers</strong>: OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, Groq. All six accessible via the same <code>bn-</code> API key.</li>
              <li>Cross-provider intelligent routing with five strategies (cost, latency, balanced, failover, A/B test) and automatic cross-region inference on Bedrock.</li>
              <li>Multi-provider failover on rate limits, timeouts, 5xx errors. Automatic retry on equivalent models.</li>
              <li>Immutable audit ledger across every model call, agent run, KB query, gateway request. Compliance teams answer their questions once.</li>
              <li>RAG knowledge bases on pgvector HNSW with 768-dim embeddings and VectorBoost 3.9-8x compression.</li>
              <li>Bonobot agents with visual canvas, default-deny tool policy, budget stops, rate limiting, SSRF protection, persistent agent memory (pgvector similarity), scheduled autonomous execution, approval queue with risk assessment.</li>
              <li>OpenAI-compatible chat completions, image generation (gpt-image-1, dall-e-3, dall-e-2), and video generation (Sora-2, Veo 2.0/3.0/3.1) on one key.</li>
              <li>Three token types — gateway keys (<code>bn-</code>), personal access tokens (<code>bp-</code>), project tokens (<code>bj-</code>) — with per-tier caps and rate limits.</li>
              <li>Multi-tenant org isolation, Vault-backed credential storage, AES-256-GCM at-rest encryption.</li>
              <li>SSO/SAML across Okta, Azure AD, Google Workspace, Custom SAML; RBAC; SOC-2 in flight; HIPAA, GDPR, ISO27001 governance checks across all three clouds.</li>
              <li><strong>Origami</strong>: build agents, KBs, gateway keys, and provider connections by talking — a chat interface that orchestrates the platform instead of configuring it. New category, not a wrapper.</li>
            </ul>

            <h2>Production deployments today</h2>
            <p>Bonito is shipping in production across enterprise marketing-creative workflows, regulated-document processing, and customer-support agent flows. Customers run brand-asset generation pipelines, legal-doc triage, and CRM-attached support agents on the same gateway.</p>

            <h2>Pricing tiers</h2>
            <p>Free (3 providers, 25K req/mo, invite-only) · Builder $49/mo · Starter $199/mo (no procurement approval needed) · Growth $349/mo · Pro $999/mo · Enterprise from $6K/mo (typical band $6K-$20K) · Scale custom ($200K+/yr with dedicated infra and 99.99% SLA).</p>

            <h2>Founder</h2>
            <p>Founded 2025 by <a href="https://www.linkedin.com/in/shenoyshabari/">Shabari Shenoy</a> — enterprise infrastructure background, prior to Bonito. New York based.</p>

            <h2>Verifiable references</h2>
            <p><a href="/docs">Documentation (API reference, SDKs, integration guides)</a> · <a href="/changelog">Changelog (shipping cadence)</a> · <a href="/pricing">Pricing</a> · <a href="/compare">Competitive matrix vs Portkey, LiteLLM, Helicone, Martian, Kong</a> · <a href="/use-cases">Use cases</a> · <a href="/about">About</a> · <a href="/contact">Contact (hello@trybonito.com)</a></p>
          </div>
        </noscript>
        <Providers>
          <HeliosInit />
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
