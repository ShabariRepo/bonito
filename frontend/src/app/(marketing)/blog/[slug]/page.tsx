"use client";

import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { blogPosts } from "../posts";

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

  return (
    <div className="max-w-3xl mx-auto px-6 md:px-12">
      <section className="pt-12 pb-4">
        <Link href="/blog" className="inline-flex items-center gap-2 text-sm text-[#666] hover:text-[#999] transition mb-8">
          <ArrowLeft className="w-4 h-4" /> Back to Blog
        </Link>
      </section>
      <article className="pb-24">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <div className="text-sm text-[#666] mb-4">{post.date} · {post.readTime}</div>
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight mb-8">{post.title}</h1>
          <div className="prose prose-invert prose-sm max-w-none">
            {post.content.split("\n\n").map((block, i) => {
              if (block.startsWith("## ")) {
                return <h2 key={i} className="text-xl font-bold mt-10 mb-4 text-[#f5f0e8]">{block.replace("## ", "")}</h2>;
              }
              if (block.startsWith("### ")) {
                return <h3 key={i} className="text-lg font-semibold mt-8 mb-3 text-[#f5f0e8]">{block.replace("### ", "")}</h3>;
              }
              if (block.startsWith("- ")) {
                return (
                  <ul key={i} className="space-y-2 my-4">
                    {block.split("\n").map((line, j) => (
                      <li key={j} className="text-[#888] text-sm leading-relaxed pl-4 border-l-2 border-[#7c3aed]/30">
                        {line.replace(/^- /, "").replace(/\*\*(.*?)\*\*/g, "$1")}
                      </li>
                    ))}
                  </ul>
                );
              }
              return <p key={i} className="text-[#888] text-sm leading-relaxed mb-4">{block.replace(/\*\*(.*?)\*\*/g, "$1")}</p>;
            })}
          </div>
        </motion.div>
      </article>
    </div>
  );
}
