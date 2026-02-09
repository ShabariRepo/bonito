import { MetadataRoute } from "next";

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = "https://getbonito.com";

  const staticPages = [
    "",
    "/pricing",
    "/about",
    "/docs",
    "/blog",
    "/contact",
    "/changelog",
    "/terms",
    "/privacy",
    "/login",
    "/register",
  ];

  const blogSlugs = [
    "why-multi-cloud-ai-management-matters-2026",
    "introducing-bonito-your-ai-control-plane",
    "reducing-ai-costs-across-aws-azure-gcp",
  ];

  const pages: MetadataRoute.Sitemap = staticPages.map((path) => ({
    url: `${baseUrl}${path}`,
    lastModified: new Date(),
    changeFrequency: path === "" ? "weekly" : "monthly",
    priority: path === "" ? 1 : path === "/pricing" ? 0.9 : 0.7,
  }));

  const blogPages: MetadataRoute.Sitemap = blogSlugs.map((slug) => ({
    url: `${baseUrl}/blog/${slug}`,
    lastModified: new Date(),
    changeFrequency: "monthly" as const,
    priority: 0.6,
  }));

  return [...pages, ...blogPages];
}
