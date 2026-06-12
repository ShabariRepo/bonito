"use client";

/**
 * StudioMarkdown — renders assistant chat messages as proper markdown.
 *
 * Studio's BDR responses are markdown-shaped (bullet lists, bold,
 * inline code) but the previous bubble used whitespace-pre-wrap which
 * showed the raw `**asterisks**` and `-` characters. This component
 * renders the markdown safely (react-markdown + remark-gfm) with
 * styles tuned to the chat-bubble context: tight spacing, inline-code
 * pill, monospace block code, no oversized headings.
 *
 * User-written messages stay as plain text — only the assistant gets
 * markdown so a stray `*` in a user prompt doesn't render formatting.
 */

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function StudioMarkdown({ text }: { text: string }) {
  return (
    <div className="space-y-2 leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Paragraphs — leading-relaxed, no big margins (bubble is tight)
          p: ({ children }) => (
            <p className="leading-relaxed [&:not(:first-child)]:mt-2">
              {children}
            </p>
          ),
          // Bold + italic — semantic emphasis
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">{children}</strong>
          ),
          em: ({ children }) => <em className="italic">{children}</em>,
          // Lists — tight, custom bullets so they read on the dark bubble
          ul: ({ children }) => (
            <ul className="list-disc pl-5 space-y-1 marker:text-muted-foreground">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 space-y-1 marker:text-muted-foreground">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed">{children}</li>
          ),
          // Inline code → small pill; block code → full mono panel
          code: ({ className, children, ...props }) => {
            const isBlock = !!className?.startsWith("language-");
            if (isBlock) {
              return (
                <code
                  className="block bg-muted/70 text-foreground rounded-md px-3 py-2 my-2 text-xs font-mono overflow-x-auto"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code
                className="rounded bg-muted/70 px-1.5 py-0.5 text-[0.85em] font-mono"
                {...props}
              >
                {children}
              </code>
            );
          },
          pre: ({ children }) => <pre className="my-2">{children}</pre>,
          // Headings stay small inside a chat bubble — H1 isn't bigger
          // than the surrounding text so the chat hierarchy reads cleanly.
          h1: ({ children }) => (
            <h1 className="text-base font-semibold mt-3 mb-1.5">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-semibold mt-3 mb-1.5">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold mt-2 mb-1">{children}</h3>
          ),
          // Links — open in same tab for in-app navigation; underline
          // by default so they read as actionable.
          a: ({ children, href }) => (
            <a
              href={href}
              className="text-violet-400 underline decoration-violet-400/40 underline-offset-2 hover:decoration-violet-400"
            >
              {children}
            </a>
          ),
          // Tables — compact and aligned. Worth supporting since BDR
          // answers about provider lists / model breakdowns may reach
          // for tables eventually.
          table: ({ children }) => (
            <div className="my-2 overflow-x-auto">
              <table className="text-xs border-collapse w-full">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-border/40 px-2 py-1 text-left font-semibold">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-border/20 px-2 py-1">{children}</td>
          ),
          // Blockquote — subtle left border so quotes stand out without
          // shouting.
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-violet-400/40 pl-3 italic text-muted-foreground">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-3 border-border/40" />,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
