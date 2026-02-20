"use client";

import { useRef } from "react";
import { motion, useInView } from "framer-motion";
import Link from "next/link";
import Script from "next/script";
import {
  ArrowLeft,
  ArrowRight,
  Lightbulb,
  ImageIcon,
  TrendingUp,
} from "lucide-react";
import { blogPosts, type BlogPostImage } from "../posts";

/* ── Types ───────────────────────────────────────────────────────── */

type StatItem = { value: string; label: string };

type ContentBlock =
  | { type: "h2"; content: string }
  | { type: "h3"; content: string }
  | { type: "paragraph"; content: string }
  | { type: "list"; items: string[] }
  | { type: "stats"; stats: StatItem[] }
  | { type: "insight"; content: string }
  | { type: "blockquote"; content: string };

/* ── Inline renderer (bold + links) ──────────────────────────────── */

function renderInline(text: string) {
  const parts: (string | React.ReactElement)[] = [];
  const regex = /\*\*(.*?)\*\*|\[([^\]]+)\]\(([^)]+)\)/g;
  let lastIndex = 0;
  let match;
  let keyIdx = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[1] !== undefined) {
      parts.push(
        <strong key={keyIdx++} className="text-[#f5f0e8] font-semibold">
          {match[1]}
        </strong>
      );
    } else if (match[2] !== undefined) {
      const href = match[3];
      const isInternal = href.startsWith("/");
      if (isInternal) {
        parts.push(
          <Link
            key={keyIdx++}
            href={href}
            className="text-[#7c3aed] hover:underline"
          >
            {match[2]}
          </Link>
        );
      } else {
        parts.push(
          <a
            key={keyIdx++}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#7c3aed] hover:underline"
          >
            {match[2]}
          </a>
        );
      }
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length === 1 && typeof parts[0] === "string"
    ? parts[0]
    : <>{parts}</>;
}

/* ── Animated wrapper ────────────────────────────────────────────── */

function AnimatedBlock({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-40px" });

  return (
    <motion.div
      ref={ref}
      className={className || undefined}
      initial={{ opacity: 0, y: 16 }}
      animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

/* ── Visual components ───────────────────────────────────────────── */

function SectionDivider() {
  return (
    <div className="my-10 flex items-center justify-center">
      <div className="h-px w-full bg-gradient-to-r from-transparent via-[#7c3aed]/30 to-transparent" />
    </div>
  );
}

function StatCards({ stats }: { stats: StatItem[] }) {
  return (
    <div
      className={`grid gap-3 my-8 ${
        stats.length === 2
          ? "grid-cols-1 sm:grid-cols-2"
          : stats.length >= 3
          ? "grid-cols-1 sm:grid-cols-3"
          : "grid-cols-1"
      }`}
    >
      {stats.map((stat, i) => (
        <div
          key={i}
          className="relative overflow-hidden rounded-xl border border-[#7c3aed]/20 bg-gradient-to-br from-[#7c3aed]/[0.08] to-transparent p-5 text-center"
        >
          <div className="flex items-center justify-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-[#7c3aed]/60" />
          </div>
          <div className="text-2xl md:text-3xl font-bold text-[#f5f0e8] tracking-tight">
            {stat.value}
          </div>
          <div className="text-xs text-[#888] mt-1 font-medium uppercase tracking-wider">
            {stat.label}
          </div>
          {/* Subtle glow */}
          <div className="absolute -top-12 -right-12 w-24 h-24 bg-[#7c3aed]/10 rounded-full blur-2xl" />
        </div>
      ))}
    </div>
  );
}

function InsightBox({ content }: { content: string }) {
  return (
    <div className="my-8 rounded-xl border border-[#7c3aed]/20 bg-[#7c3aed]/[0.05] p-5 pl-12 relative overflow-hidden">
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#7c3aed] to-[#7c3aed]/30" />
      <div className="absolute left-3.5 top-5">
        <Lightbulb className="w-4 h-4 text-[#7c3aed]" />
      </div>
      <div className="text-sm text-[#c5c0b8] leading-relaxed">
        {renderInline(content)}
      </div>
    </div>
  );
}

function PullQuote({ content }: { content: string }) {
  return (
    <blockquote className="my-8 pl-6 border-l-4 border-[#7c3aed]/60 relative">
      <p className="text-base md:text-lg italic text-[#c5c0b8] leading-relaxed font-light">
        {renderInline(content)}
      </p>
      <div className="absolute -left-3 -top-2 text-[#7c3aed]/20 text-5xl font-serif leading-none select-none">
        &ldquo;
      </div>
    </blockquote>
  );
}

function FloatingImage({ image }: { image: BlogPostImage }) {
  return (
    <div className="relative overflow-hidden rounded-xl aspect-[4/3] bg-gradient-to-br from-[#7c3aed]/20 via-[#1a1a2e] to-[#7c3aed]/10 border border-[#7c3aed]/20">
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
        <div className="w-12 h-12 rounded-full bg-[#7c3aed]/10 flex items-center justify-center">
          <ImageIcon className="w-6 h-6 text-[#7c3aed]/50" />
        </div>
        <span className="text-xs text-[#7c3aed]/40 font-medium tracking-wider uppercase">
          {image.alt || "Illustration"}
        </span>
      </div>
      {/* Subtle grid pattern overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(#7c3aed 1px, transparent 1px), linear-gradient(90deg, #7c3aed 1px, transparent 1px)",
          backgroundSize: "20px 20px",
        }}
      />
    </div>
  );
}

/* ── Content parser ──────────────────────────────────────────────── */

function parseContent(content: string): ContentBlock[] {
  return content
    .split("\n\n")
    .map((raw): ContentBlock | null => {
      const block = raw.trim();
      if (!block) return null;

      // Stats block: :::stats ... :::
      if (block.startsWith(":::stats")) {
        const lines = block
          .split("\n")
          .filter(
            (l) =>
              l.trim() && l.trim() !== ":::stats" && l.trim() !== ":::"
          );
        return {
          type: "stats",
          stats: lines.map((l) => {
            const [value, ...rest] = l.split("|");
            return { value: value.trim(), label: rest.join("|").trim() };
          }),
        };
      }

      // Insight block: :::insight ... :::
      if (block.startsWith(":::insight")) {
        const inner = block
          .replace(/^:::insight\n?/, "")
          .replace(/\n?:::$/, "")
          .trim();
        return { type: "insight", content: inner };
      }

      // Blockquote / pull quote
      if (block.startsWith("> ")) {
        const inner = block
          .split("\n")
          .map((l) => l.replace(/^> /, ""))
          .join(" ");
        return { type: "blockquote", content: inner };
      }

      // Headings
      if (block.startsWith("## "))
        return { type: "h2", content: block.slice(3) };
      if (block.startsWith("### "))
        return { type: "h3", content: block.slice(4) };

      // List
      if (block.startsWith("- ")) {
        return {
          type: "list",
          items: block.split("\n").map((l) => l.replace(/^- /, "")),
        };
      }

      // Paragraph (default)
      return { type: "paragraph", content: block };
    })
    .filter((b): b is ContentBlock => b !== null);
}

/* ── Block renderer ──────────────────────────────────────────────── */

function renderContent(content: string, images?: BlogPostImage[]) {
  const blocks = parseContent(content);
  let currentSection = "";
  const usedSections = new Set<string>();
  const allElements: React.ReactElement[] = [];

  blocks.forEach((block, i) => {
    // Track current section for image insertion
    if (block.type === "h2") currentSection = block.content;

    // Insert floating image on first paragraph of a section that has one
    if (
      block.type === "paragraph" &&
      images &&
      currentSection &&
      !usedSections.has(currentSection)
    ) {
      const img = images.find((im) => im.section === currentSection);
      if (img) {
        usedSections.add(currentSection);
        const isLeft = img.position === "left";
        allElements.push(
          <AnimatedBlock
            key={`img-${i}`}
            className={[
              "w-full mb-4",
              "md:w-[280px] lg:w-[320px] md:mb-2 mt-1",
              isLeft ? "md:float-left md:mr-6" : "md:float-right md:ml-6",
            ].join(" ")}
          >
            <FloatingImage image={img} />
          </AnimatedBlock>
        );
      }
    }

    switch (block.type) {
      case "h2":
        allElements.push(
          <div key={`clear-${i}`} className="clear-both" />
        );
        allElements.push(
          <AnimatedBlock key={i}>
            <SectionDivider />
            <h2 className="text-xl font-bold mt-2 mb-4 text-[#f5f0e8]">
              {block.content}
            </h2>
          </AnimatedBlock>
        );
        break;

      case "h3":
        allElements.push(
          <AnimatedBlock key={i}>
            <h3 className="text-lg font-semibold mt-8 mb-3 text-[#f5f0e8]">
              {block.content}
            </h3>
          </AnimatedBlock>
        );
        break;

      case "paragraph":
        allElements.push(
          <AnimatedBlock key={i}>
            <p className="text-[#888] text-sm leading-relaxed mb-4">
              {renderInline(block.content)}
            </p>
          </AnimatedBlock>
        );
        break;

      case "list":
        allElements.push(
          <AnimatedBlock key={i}>
            <ul className="space-y-2 my-4">
              {block.items.map((item, j) => (
                <li
                  key={j}
                  className="text-[#888] text-sm leading-relaxed pl-4 border-l-2 border-[#7c3aed]/30"
                >
                  {renderInline(item)}
                </li>
              ))}
            </ul>
          </AnimatedBlock>
        );
        break;

      case "stats":
        allElements.push(
          <AnimatedBlock key={i}>
            <StatCards stats={block.stats} />
          </AnimatedBlock>
        );
        break;

      case "insight":
        allElements.push(
          <AnimatedBlock key={i}>
            <InsightBox content={block.content} />
          </AnimatedBlock>
        );
        break;

      case "blockquote":
        allElements.push(
          <AnimatedBlock key={i}>
            <PullQuote content={block.content} />
          </AnimatedBlock>
        );
        break;
    }
  });

  // Final clear for any trailing floats
  allElements.push(<div key="clear-end" className="clear-both" />);

  return allElements;
}

/* ── Client component ────────────────────────────────────────────── */

export default function BlogPostClient({ slug }: { slug: string }) {
  const post = blogPosts.find((p) => p.slug === slug);

  if (!post) {
    return (
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-20 text-center">
        <h1 className="text-2xl font-bold mb-4">Post not found</h1>
        <Link href="/blog" className="text-[#7c3aed] hover:underline">
          Back to Blog
        </Link>
      </div>
    );
  }

  const related = blogPosts.filter((p) => p.slug !== post.slug).slice(0, 2);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.metaDescription,
    datePublished: post.dateISO,
    dateModified: post.dateISO,
    author: { "@type": "Organization", name: "Bonito" },
    publisher: {
      "@type": "Organization",
      name: "Bonito",
      url: "https://getbonito.com",
      logo: {
        "@type": "ImageObject",
        url: "https://getbonito.com/icon-512.png",
      },
    },
    image: "https://getbonito.com/og-blog.png",
    url: `https://getbonito.com/blog/${post.slug}`,
    mainEntityOfPage: `https://getbonito.com/blog/${post.slug}`,
  };

  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12">
      <Script
        id="json-ld-article"
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <section className="pt-12 pb-4">
        <Link
          href="/blog"
          className="inline-flex items-center gap-2 text-sm text-[#666] hover:text-[#999] transition mb-8"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Blog
        </Link>
      </section>

      <article className="pb-12">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex flex-wrap gap-2 mb-4">
            {post.tags.map((tag) => (
              <span
                key={tag}
                className="text-[10px] px-2 py-0.5 rounded-full bg-[#7c3aed]/10 text-[#7c3aed] font-medium"
              >
                {tag}
              </span>
            ))}
          </div>
          <div className="text-sm text-[#666] mb-4">
            {post.date} · {post.readTime}
            {post.author ? ` · ${post.author}` : ""}
          </div>
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-8">
            {post.title}
          </h1>
          <div className="prose prose-invert prose-sm max-w-none">
            {renderContent(post.content, post.images)}
          </div>
        </motion.div>
      </article>

      {/* CTA */}
      <div className="border border-[#7c3aed]/20 bg-[#7c3aed]/5 rounded-xl p-8 mb-12 text-center">
        <h3 className="text-xl font-bold mb-2">
          Ready to manage your AI infrastructure?
        </h3>
        <p className="text-[#888] text-sm mb-4">
          Join teams using Bonito to connect, route, and optimize their AI
          stack.
        </p>
        <Link
          href="/register"
          className="inline-flex items-center gap-2 px-6 py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white font-semibold rounded-lg transition"
        >
          Get started free <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Related Articles */}
      {related.length > 0 && (
        <section className="pb-24">
          <h2 className="text-xl font-bold mb-6">Related Articles</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {related.map((r) => (
              <Link
                key={r.slug}
                href={`/blog/${r.slug}`}
                className="block bg-[#111] border border-[#1a1a1a] rounded-xl p-6 hover:border-[#7c3aed]/30 transition group"
              >
                <div className="text-xs text-[#666] mb-2">
                  {r.date} · {r.readTime}
                </div>
                <h3 className="text-sm font-semibold group-hover:text-[#7c3aed] transition">
                  {r.title}
                </h3>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
