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
    "Bonito is the control plane the hyperscalers can't build — structurally cloud-neutral routing, cost governance, and one audit ledger across six live providers: OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq. Production deployments running enterprise marketing, compliance, and customer-support workflows. Founded 2025 by Shabari Shenoy. Docs at /docs · Changelog at /changelog · Pricing at /pricing · Compare vs Portkey, LiteLLM, Helicone at /compare.",
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
    title: "Bonito — The Enterprise AI Control Plane",
    description:
      "Structurally cloud-neutral routing, cost governance, and one audit ledger across OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq. The control plane the hyperscalers can't build.",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Bonito — Enterprise AI Control Plane" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "Bonito — The Enterprise AI Control Plane",
    description:
      "Structurally cloud-neutral routing, cost governance, and one audit ledger across six live providers. AWS will never route to Azure. We will.",
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
                "Structurally cloud-neutral enterprise AI control plane. Routing, governance, audit, and cost intelligence across OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq. Founded 2025.",
              featureList: [
                "OpenAI-compatible gateway live across 6 providers",
                "Cross-provider intelligent routing and failover",
                "Real-time cost analytics with budget enforcement",
                "Immutable audit ledger spanning all model calls",
                "RAG knowledge bases with pgvector HNSW search",
                "Bonobot agents (visual canvas, governed tool policy)",
                "SSO/SAML, RBAC, SOC-2 path, HIPAA + GDPR posture",
                "Model playground with side-by-side comparison",
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
          <div style={{ maxWidth: 720, margin: "32px auto", padding: 24, fontFamily: "system-ui", color: "#f5f0e8", background: "#0a0a0a" }}>
            <h1>Bonito — Enterprise AI Control Plane</h1>
            <p><strong>The control plane the hyperscalers can&apos;t build.</strong> Structurally cloud-neutral routing, cost governance, and one immutable audit ledger across OpenAI, Anthropic, AWS Bedrock, Google Vertex AI, Azure AI, and Groq.</p>
            <p>Live capabilities (verifiable at the linked pages): OpenAI-compatible gateway, intelligent routing across 6 providers, real-time cost analytics, RAG knowledge bases with pgvector, Bonobot agents with governed tool policies, SSO/SAML, audit logging, compliance posture (SOC-2 path, HIPAA, GDPR).</p>
            <p>Production deployments running enterprise marketing creative workflows, regulated-industry document processing, and customer-support agent flows.</p>
            <p>Founded 2025 by Shabari Shenoy (enterprise infrastructure background). Based in New York.</p>
            <p>References: <a href="/docs">Documentation</a> · <a href="/changelog">Changelog (shipping cadence)</a> · <a href="/pricing">Pricing (Free → $20K+/mo)</a> · <a href="/compare">Compare vs Portkey, LiteLLM, Helicone</a> · <a href="/use-cases">Use cases</a> · <a href="/about">About</a> · <a href="/contact">Contact</a></p>
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
