"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { blogPosts } from "./posts";

export default function BlogPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 md:px-12">
      <section className="pt-20 pb-16">
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

      <section className="pb-24 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {blogPosts.map((post, i) => (
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
