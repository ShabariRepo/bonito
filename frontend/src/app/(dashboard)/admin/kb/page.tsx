"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/ui/page-header";
import { LoadingDots } from "@/components/ui/loading-dots";
import { ErrorBanner } from "@/components/ui/error-banner";
import { apiRequest } from "@/lib/auth";
import {
  BookOpen,
  ArrowLeft,
  Layers,
  Settings,
  FileText,
} from "lucide-react";

interface KBArticleSummary {
  slug: string;
  title: string;
  description: string;
  category: string;
  updated_at: string;
}

interface KBArticle extends KBArticleSummary {
  content: string;
}

const categoryConfig: Record<string, { icon: typeof BookOpen; color: string; bg: string }> = {
  Architecture: { icon: Layers, color: "text-violet-500", bg: "bg-violet-500/15" },
  Operations: { icon: Settings, color: "text-amber-500", bg: "bg-amber-500/15" },
  Reference: { icon: FileText, color: "text-cyan-500", bg: "bg-cyan-500/15" },
};

function renderMarkdown(content: string) {
  // Simple markdown renderer — handles headings, code blocks, tables, lists, bold, inline code
  const lines = content.split("\n");
  const elements: JSX.Element[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code blocks
    if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      elements.push(
        <pre
          key={key++}
          className="my-4 rounded-lg bg-[#0a0a0a] border border-border p-4 overflow-x-auto text-sm"
        >
          <code className="text-emerald-400">{codeLines.join("\n")}</code>
        </pre>
      );
      continue;
    }

    // Tables
    if (line.includes("|") && line.trim().startsWith("|")) {
      const tableRows: string[] = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim().startsWith("|")) {
        tableRows.push(lines[i]);
        i++;
      }
      // Parse table
      const parsedRows = tableRows
        .filter((r) => !r.match(/^\|[\s-:|]+\|$/)) // skip separator rows
        .map((r) =>
          r
            .split("|")
            .slice(1, -1)
            .map((cell) => cell.trim())
        );

      if (parsedRows.length > 0) {
        const header = parsedRows[0];
        const body = parsedRows.slice(1);
        elements.push(
          <div key={key++} className="my-4 overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-accent/30">
                  {header.map((cell, ci) => (
                    <th key={ci} className="px-4 py-2 text-left font-medium text-muted-foreground">
                      {cell}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {body.map((row, ri) => (
                  <tr key={ri} className="border-b border-border last:border-0">
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-4 py-2">
                        {renderInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // Headings
    if (line.startsWith("# ")) {
      elements.push(
        <h1 key={key++} className="text-2xl font-bold mt-8 mb-4 first:mt-0">
          {line.slice(2)}
        </h1>
      );
      i++;
      continue;
    }
    if (line.startsWith("## ")) {
      elements.push(
        <h2 key={key++} className="text-xl font-semibold mt-6 mb-3 text-violet-400">
          {line.slice(3)}
        </h2>
      );
      i++;
      continue;
    }
    if (line.startsWith("### ")) {
      elements.push(
        <h3 key={key++} className="text-lg font-medium mt-5 mb-2">
          {line.slice(4)}
        </h3>
      );
      i++;
      continue;
    }

    // Horizontal rule
    if (line.match(/^---+$/)) {
      elements.push(<hr key={key++} className="my-6 border-border" />);
      i++;
      continue;
    }

    // Unordered list
    if (line.match(/^[-*] /)) {
      const listItems: string[] = [];
      while (i < lines.length && lines[i].match(/^[-*] /)) {
        listItems.push(lines[i].replace(/^[-*] /, ""));
        i++;
      }
      elements.push(
        <ul key={key++} className="my-3 space-y-1.5 pl-5 list-disc text-sm">
          {listItems.map((item, li) => (
            <li key={li} className="text-muted-foreground">
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Ordered list
    if (line.match(/^\d+\. /)) {
      const listItems: string[] = [];
      while (i < lines.length && lines[i].match(/^\d+\. /)) {
        listItems.push(lines[i].replace(/^\d+\. /, ""));
        i++;
      }
      elements.push(
        <ol key={key++} className="my-3 space-y-1.5 pl-5 list-decimal text-sm">
          {listItems.map((item, li) => (
            <li key={li} className="text-muted-foreground">
              {renderInline(item)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Empty line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Paragraph
    elements.push(
      <p key={key++} className="my-2 text-sm text-muted-foreground leading-relaxed">
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return elements;
}

function renderInline(text: string): React.ReactNode {
  // Handle inline code, bold, and plain text
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let partKey = 0;

  while (remaining.length > 0) {
    // Inline code
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`(.*)/s);
    if (codeMatch) {
      if (codeMatch[1]) {
        parts.push(<span key={partKey++}>{renderBold(codeMatch[1])}</span>);
      }
      parts.push(
        <code
          key={partKey++}
          className="px-1.5 py-0.5 rounded bg-accent text-violet-400 text-xs font-mono"
        >
          {codeMatch[2]}
        </code>
      );
      remaining = codeMatch[3];
      continue;
    }

    // No more inline code — render bold and return
    parts.push(<span key={partKey++}>{renderBold(remaining)}</span>);
    break;
  }

  return parts.length === 1 ? parts[0] : <>{parts}</>;
}

function renderBold(text: string): React.ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g);
  if (parts.length === 1) return text;
  return (
    <>
      {parts.map((part, i) =>
        i % 2 === 1 ? (
          <strong key={i} className="font-semibold text-foreground">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  );
}

export default function AdminKBPage() {
  const [articles, setArticles] = useState<KBArticleSummary[]>([]);
  const [selectedArticle, setSelectedArticle] = useState<KBArticle | null>(null);
  const [loading, setLoading] = useState(true);
  const [articleLoading, setArticleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchArticles = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiRequest("/api/admin/kb");
      if (!res.ok) throw new Error("Failed to load knowledge base");
      const data = await res.json();
      setArticles(data);
    } catch (e: any) {
      setError(e.message || "Failed to load knowledge base");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchArticles();
  }, []);

  const openArticle = async (slug: string) => {
    setArticleLoading(true);
    try {
      const res = await apiRequest(`/api/admin/kb/${slug}`);
      if (!res.ok) throw new Error("Failed to load article");
      const data = await res.json();
      setSelectedArticle(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setArticleLoading(false);
    }
  };

  const categories = Array.from(new Set(articles.map((a) => a.category)));

  return (
    <div className="space-y-6">
      <PageHeader
        title={selectedArticle ? selectedArticle.title : "Knowledge Base"}
        description={
          selectedArticle
            ? selectedArticle.description
            : "Internal documentation and guides for the Bonito platform"
        }
        breadcrumbs={
          selectedArticle
            ? [
                { label: "Admin", href: "/admin/system" },
                { label: "Knowledge Base", href: "/admin/kb" },
                { label: selectedArticle.title },
              ]
            : [
                { label: "Admin", href: "/admin/system" },
                { label: "Knowledge Base" },
              ]
        }
        actions={
          selectedArticle ? (
            <button
              onClick={() => setSelectedArticle(null)}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md border border-border hover:bg-accent transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Articles
            </button>
          ) : undefined
        }
      />

      {error && <ErrorBanner message={error} onRetry={fetchArticles} />}

      {loading ? (
        <div className="flex justify-center py-20">
          <LoadingDots />
        </div>
      ) : selectedArticle ? (
        /* Article content */
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card>
            <CardContent className="py-6">
              <div className="flex items-center gap-3 mb-6">
                {(() => {
                  const cfg = categoryConfig[selectedArticle.category] || categoryConfig.Reference;
                  const Icon = cfg.icon;
                  return (
                    <div className={`h-8 w-8 rounded-lg ${cfg.bg} flex items-center justify-center`}>
                      <Icon className={`h-4 w-4 ${cfg.color}`} />
                    </div>
                  );
                })()}
                <Badge
                  variant="secondary"
                  className="text-xs"
                >
                  {selectedArticle.category}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  Updated {selectedArticle.updated_at}
                </span>
              </div>
              {articleLoading ? (
                <div className="flex justify-center py-12">
                  <LoadingDots />
                </div>
              ) : (
                <div className="max-w-none">{renderMarkdown(selectedArticle.content)}</div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      ) : (
        /* Article list */
        <div className="space-y-6">
          {categories.map((category) => {
            const cfg = categoryConfig[category] || categoryConfig.Reference;
            const Icon = cfg.icon;
            const categoryArticles = articles.filter((a) => a.category === category);

            return (
              <motion.div
                key={category}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                  <Icon className={`h-4 w-4 ${cfg.color}`} />
                  {category}
                </h2>
                <div className="grid gap-3 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                  {categoryArticles.map((article, i) => (
                    <motion.div
                      key={article.slug}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                    >
                      <Card
                        className="cursor-pointer hover:border-violet-500/30 transition-colors h-full"
                        onClick={() => openArticle(article.slug)}
                      >
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between">
                            <CardTitle className="text-base">{article.title}</CardTitle>
                            <Badge variant="secondary" className="text-[10px] shrink-0">
                              {article.category}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground">{article.description}</p>
                          <p className="text-xs text-muted-foreground/60 mt-3">
                            Updated {article.updated_at}
                          </p>
                        </CardContent>
                      </Card>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
