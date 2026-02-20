import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { blogPosts } from "../posts";
import BlogPostClient from "./BlogPostClient";

/* ── Static params (pre-render all blog posts at build time) ───── */

export function generateStaticParams() {
  return blogPosts.map((post) => ({ slug: post.slug }));
}

/* ── Per-post SEO metadata ───────────────────────────────────────── */

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = blogPosts.find((p) => p.slug === slug);
  if (!post) return {};

  const url = `https://getbonito.com/blog/${post.slug}`;

  return {
    title: post.title,
    description: post.metaDescription,
    keywords: post.tags,
    alternates: { canonical: url },
    openGraph: {
      title: post.title,
      description: post.metaDescription,
      url,
      type: "article",
      publishedTime: post.dateISO,
    },
    twitter: {
      card: "summary_large_image",
      title: post.title,
      description: post.metaDescription,
    },
  };
}

/* ── Server page ─────────────────────────────────────────────────── */

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = blogPosts.find((p) => p.slug === slug);
  if (!post) notFound();

  return <BlogPostClient slug={slug} />;
}
