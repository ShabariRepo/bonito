"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import Script from "next/script";
import { ArrowRight } from "lucide-react";
import { blogPosts, blogTags } from "./posts";

export default function BlogPage() {
  const [activeTag, setActiveTag] = useState<string | null>(null);

  const filtered = activeTag
    ? blogPosts.filter((p) => p.tags.includes(activeTag))
    : blogPosts;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Blog",
    name: "Bonito Blog",
    description: "Insights on multi-cloud AI management, cost optimization, and building scalable AI infrastructure.",
    url: "https://getbonito.com/blog",
    publisher: {
      "@type": "Organization",
      name: "Bonito",
      url: "https://getbonito.com",
      logo: { "@type": "ImageObject", url: "https://getbonito.com/icon-512.png" },
    },
    blogPost: blogPosts.map((post) => ({
      "@type": "BlogPosting",
      headline: post.title,
      description: post.metaDescription,
      datePublished: post.dateISO,
      url: `https://getbonito.com/blog/${post.slug}`,
    })),
  };

  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12">
      <Script
        id="json-ld-blog"
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <section className="pt-20 pb-10">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-4xl md:text-6xl font-bold tracking-tight"
        >
          Blog
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mt-4 text-lg text-[#888] max-w-2xl"
        >
          Insights on multi-cloud AI management, cost optimization, and building scalable AI infrastructure.
        </motion.p>
      </section>

      {/* Tags */}
      <section className="pb-8 flex flex-wrap gap-2">
        <button
          onClick={() => setActiveTag(null)}
          className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${
            activeTag === null
              ? "bg-[#7c3aed] text-white"
              : "bg-[#1a1a1a] text-[#888] hover:text-[#f5f0e8]"
          }`}
        >
          All
        </button>
        {blogTags.map((tag) => (
          <button
            key={tag}
            onClick={() => setActiveTag(activeTag === tag ? null : tag)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium transition ${
              activeTag === tag
                ? "bg-[#7c3aed] text-white"
                : "bg-[#1a1a1a] text-[#888] hover:text-[#f5f0e8]"
            }`}
          >
            {tag}
          </button>
        ))}
      </section>

      <section className="pb-24 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map((post, i) => (
          <motion.article
            key={post.slug}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Link
              href={`/blog/${post.slug}`}
              className="block bg-[#111] border border-[#1a1a1a] rounded-xl p-8 hover:border-[#7c3aed]/30 transition group h-full"
            >
              <div className="flex flex-wrap gap-2 mb-3">
                {post.tags.map((tag) => (
                  <span key={tag} className="text-[10px] px-2 py-0.5 rounded-full bg-[#7c3aed]/10 text-[#7c3aed] font-medium">
                    {tag}
                  </span>
                ))}
              </div>
              <div className="text-xs text-[#666] mb-3">{post.date} · {post.readTime}</div>
              <h2 className="text-lg font-semibold mb-3 group-hover:text-[#7c3aed] transition">{post.title}</h2>
              <p className="text-sm text-[#888] leading-relaxed mb-4">{post.excerpt}</p>
              <span className="text-sm text-[#7c3aed] flex items-center gap-1 group-hover:gap-2 transition-all">
                Read more <ArrowRight className="w-4 h-4" />
              </span>
            </Link>
          </motion.article>
        ))}
      </section>
    </div>
  );
}
