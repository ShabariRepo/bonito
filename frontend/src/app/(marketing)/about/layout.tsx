import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About Bonito — The Enterprise AI Control Plane",
  description:
    "Bonito is building the operating system for enterprise AI. Unified governance, routing, and cost management across AWS, Azure, and GCP. Founded by Shabari, software architect at FIS Global.",
  openGraph: {
    title: "About Bonito",
    description:
      "The enterprise AI control plane. Unified multi-cloud AI management with governed agents, smart routing, and 84% cost savings.",
    url: "https://getbonito.com/about",
  },
  alternates: { canonical: "https://getbonito.com/about" },
};

export default function AboutLayout({ children }: { children: React.ReactNode }) {
  return children;
}
