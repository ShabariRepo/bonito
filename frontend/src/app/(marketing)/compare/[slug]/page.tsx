import { Metadata } from "next";
import { notFound } from "next/navigation";
import { competitors } from "../competitors";
import ComparisonContent from "./ComparisonContent";

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  return competitors.map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const competitor = competitors.find((c) => c.slug === slug);
  if (!competitor) return {};

  return {
    title: competitor.metaTitle,
    description: competitor.metaDescription,
    keywords: competitor.keywords,
    openGraph: {
      title: competitor.metaTitle,
      description: competitor.metaDescription,
      url: `https://getbonito.com/compare/${competitor.slug}`,
    },
    alternates: { canonical: `https://getbonito.com/compare/${competitor.slug}` },
  };
}

export default async function ComparisonPage({ params }: Props) {
  const { slug } = await params;
  const competitor = competitors.find((c) => c.slug === slug);
  if (!competitor) notFound();

  return <ComparisonContent competitor={competitor} />;
}
