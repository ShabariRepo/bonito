import { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://getbonito.com";
  const now = new Date().toISOString();

  const blogSlugs = [
    "how-ad-tech-platform-cut-cloud-ai-costs-30-percent-multi-cloud-routing",
    "building-hipaa-compliant-ai-agents-clinical-decision-support",
    "introducing-bonobot-enterprise-ai-agent-platform",
    "ai-openpath-problem-enterprise-cost-transparency",
    "how-novamart-deployed-ai-agents-across-teams",
    "how-meridian-technologies-cut-ai-costs-84-percent",
    "openclaw-proved-ai-agents-work-enterprise-needs-them-governed",
    "the-94-billion-bet-enterprise-ai-adoption",
    "why-multi-cloud-ai-management-matters-2026",
    "introducing-bonito-your-ai-control-plane",
    "reducing-ai-costs-across-aws-azure-gcp",
  ];

  const compareSlugs = [
    "langfuse",
    "helicone",
    "portkey",
    "langsmith",
    "arize",
  ];

  return [
    {
      url: baseUrl,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 1.0,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.9,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${baseUrl}/blog`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    ...blogSlugs.map((slug) => ({
      url: `${baseUrl}/blog/${slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
    {
      url: `${baseUrl}/use-cases`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.7,
    },
    {
      url: `${baseUrl}/compare`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    ...compareSlugs.map((slug) => ({
      url: `${baseUrl}/compare/${slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
    {
      url: `${baseUrl}/docs`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.6,
    },
    {
      url: `${baseUrl}/changelog`,
      lastModified: now,
      changeFrequency: "weekly",
      priority: 0.5,
    },
    {
      url: `${baseUrl}/contact`,
      lastModified: now,
      changeFrequency: "monthly",
      priority: 0.5,
    },
    {
      url: `${baseUrl}/privacy`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
    {
      url: `${baseUrl}/terms`,
      lastModified: now,
      changeFrequency: "yearly",
      priority: 0.3,
    },
  ];
}
