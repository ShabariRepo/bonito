import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Use Cases — How Enterprises Use Bonito",
  description:
    "See how enterprises use Bonito to unify multi-cloud AI, cut costs by 84%, and deploy governed AI agents per department. Real case studies with real numbers.",
  openGraph: {
    title: "Bonito Use Cases — Enterprise AI in Action",
    description:
      "Real case studies: 84% cost reduction, $2.25M annual savings, unified multi-cloud AI operations.",
    url: "https://getbonito.com/use-cases",
  },
  alternates: { canonical: "https://getbonito.com/use-cases" },
};

export default function UseCasesLayout({ children }: { children: React.ReactNode }) {
  return children;
}
