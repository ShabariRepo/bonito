import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Blog — Enterprise AI Insights",
  description:
    "Insights on enterprise AI operations, multi-cloud management, AI cost optimization, and governed AI agents. From the team building Bonito.",
  openGraph: {
    title: "Bonito Blog — Enterprise AI Insights",
    description:
      "Insights on enterprise AI operations, multi-cloud management, cost optimization, and governed AI agents.",
    url: "https://getbonito.com/blog",
  },
  alternates: { canonical: "https://getbonito.com/blog" },
};

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return children;
}
