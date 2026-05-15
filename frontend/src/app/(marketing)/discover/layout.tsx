import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Discover — See What Bonito Can Do for Your Company",
  description:
    "Enter your company name and our AI will research your business, identify AI challenges, and show you exactly how Bonito fits. Free, instant, shareable.",
  openGraph: {
    title: "Discover — See What Bonito Can Do for Your Company",
    description:
      "AI-powered company analysis. Enter your company name and get a personalised Bonito use-case report in seconds.",
    url: "https://getbonito.com/discover",
    siteName: "Bonito",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Discover — See What Bonito Can Do for Your Company",
    description:
      "AI-powered company analysis. Enter your company name and get a personalised Bonito use-case report in seconds.",
  },
};

export default function DiscoverLayout({ children }: { children: React.ReactNode }) {
  return children;
}
