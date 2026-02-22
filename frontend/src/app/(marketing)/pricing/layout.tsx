import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing — Plans for Every Team",
  description:
    "Bonito pricing: Free for individuals, Pro at $499/mo for teams, Enterprise for organizations. Add Bonobot AI agents at $349/mo per department.",
  openGraph: {
    title: "Bonito Pricing — Enterprise AI Control Plane",
    description:
      "Unified multi-cloud AI management from $0. Smart routing saves up to 84% on AI costs. Add governed AI agents per department.",
    url: "https://getbonito.com/pricing",
  },
  alternates: { canonical: "https://getbonito.com/pricing" },
};

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
