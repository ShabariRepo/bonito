import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
      // Explicitly allow AI search engine crawlers
      {
        userAgent: "GPTBot",
        allow: ["/", "/llms.txt", "/llms-full.txt"],
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
      {
        userAgent: "ChatGPT-User",
        allow: ["/", "/llms.txt", "/llms-full.txt"],
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
      {
        userAgent: "Anthropic-AI",
        allow: ["/", "/llms.txt", "/llms-full.txt"],
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
      {
        userAgent: "Claude-Web",
        allow: ["/", "/llms.txt", "/llms-full.txt"],
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
      {
        userAgent: "PerplexityBot",
        allow: ["/", "/llms.txt", "/llms-full.txt"],
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
      {
        userAgent: "Google-Extended",
        allow: ["/", "/llms.txt", "/llms-full.txt"],
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
      {
        userAgent: "Amazonbot",
        allow: ["/", "/llms.txt", "/llms-full.txt"],
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
      {
        userAgent: "YouBot",
        allow: ["/", "/llms.txt", "/llms-full.txt"],
        disallow: ["/api/", "/auth/", "/dashboard/"],
      },
    ],
    sitemap: "https://getbonito.com/sitemap.xml",
  };
}
