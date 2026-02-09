import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Blog — Multi-Cloud AI Management Insights",
  description:
    "Expert insights on multi-cloud AI management, cost optimization, AI governance, and platform engineering. Stay ahead of the AI infrastructure curve.",
  openGraph: {
    title: "Bonito Blog — AI Infrastructure Insights",
    description:
      "Expert insights on multi-cloud AI management, cost optimization, and building scalable AI infrastructure.",
    url: "https://getbonito.com/blog",
  },
};

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
