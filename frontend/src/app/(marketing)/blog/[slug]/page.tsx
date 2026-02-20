"use client";

import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import Script from "next/script";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { blogPosts } from "../posts";

function renderContent(content: string) {
  return content.split("\n\n").map((block, i) => {
    if (block.startsWith("## ")) {
      return <h2 key={i} className="text-xl font-bold mt-10 mb-4 text-[#f5f0e8]">{block.replace("## ", "")}</h2>;
    }
    if (block.startsWith("### ")) {
      return <h3 key={i} className="text-lg font-semibold mt-8 mb-3 text-[#f5f0e8]">{block.replace("### ", "")}</h3>;
    }
    if (block.startsWith("- ")) {
      return (
        <ul key={i} className="space-y-2 my-4">
          {block.split("\n").map((line, j) => {
            const text = line.replace(/^- /, "");
            return (
              <li key={j} className="text-[#888] text-sm leading-relaxed pl-4 border-l-2 border-[#7c3aed]/30">
                {renderInline(text)}
              </li>
            );
          })}
        </ul>
      );
    }
    return <p key={i} className="text-[#888] text-sm leading-relaxed mb-4">{renderInline(block)}</p>;
  });
}

function renderInline(text: string) {
  // Handle bold, links
  const parts: (string | React.ReactElement)[] = [];
  // Combined pattern for **bold** and [text](url)
  const regex = /\*\*(.*?)\*\*|\[([^\]]+)\]\(([^)]+)\)/g;
  let lastIndex = 0;
  let match;
  let keyIdx = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[1] !== undefined) {
      parts.push(<strong key={keyIdx++} className="text-[#f5f0e8] font-semibold">{match[1]}</strong>);
    } else if (match[2] !== undefined) {
      const href = match[3];
      const isInternal = href.startsWith("/");
      if (isInternal) {
        parts.push(<Link key={keyIdx++} href={href} className="text-[#7c3aed] hover:underline">{match[2]}</Link>);
      } else {
        parts.push(<a key={keyIdx++} href={href} target="_blank" rel="noopener noreferrer" className="text-[#7c3aed] hover:underline">{match[2]}</a>);
      }
    }
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts.length === 1 && typeof parts[0] === "string" ? parts[0] : <>{parts}</>;
}

export default function BlogPostPage() {
  const params = useParams();
  const post = blogPosts.find((p) => p.slug === params.slug);

  if (!post) {
    return (
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-20 text-center">
        <h1 className="text-2xl font-bold mb-4">Post not found</h1>
        <Link href="/blog" className="text-[#7c3aed] hover:underline">Back to Blog</Link>
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
      logo: { "@type": "ImageObject", url: "https://getbonito.com/icon-512.png" },
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
        <Link href="/blog" className="inline-flex items-center gap-2 text-sm text-[#666] hover:text-[#999] transition mb-8">
          <ArrowLeft className="w-4 h-4" /> Back to Blog
        </Link>
      </section>

      <article className="pb-12">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex flex-wrap gap-2 mb-4">
            {post.tags.map((tag) => (
              <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-[#7c3aed]/10 text-[#7c3aed] font-medium">
                {tag}
              </span>
            ))}
          </div>
          <div className="text-sm text-[#666] mb-4">{post.date} · {post.readTime}{post.author ? ` · ${post.author}` : ""}</div>
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-8">{post.title}</h1>
          <div className="prose prose-invert prose-sm max-w-none">
            {renderContent(post.content)}
          </div>
        </motion.div>
      </article>

      {/* CTA */}
      <div className="border border-[#7c3aed]/20 bg-[#7c3aed]/5 rounded-xl p-8 mb-12 text-center">
        <h3 className="text-xl font-bold mb-2">Ready to manage your AI infrastructure?</h3>
        <p className="text-[#888] text-sm mb-4">Join teams using Bonito to connect, route, and optimize their AI stack.</p>
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
                <div className="text-xs text-[#666] mb-2">{r.date} · {r.readTime}</div>
                <h3 className="text-sm font-semibold group-hover:text-[#7c3aed] transition">{r.title}</h3>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
