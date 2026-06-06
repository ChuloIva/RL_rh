"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renders model output as markdown, themed to sit inside a transcript bubble.
// Element styling is kept compact (headings only modestly larger than body) so a
// model emphasising or formatting a passage reads naturally rather than shouting.
export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        h1: ({ children }) => (
          <h1 className="mb-2 mt-4 font-semibold text-[1.18em] leading-snug text-ink first:mt-0">
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className="mb-2 mt-4 font-semibold text-[1.1em] leading-snug text-ink first:mt-0">
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className="mb-1.5 mt-3 font-semibold text-[1.03em] leading-snug text-ink first:mt-0">
            {children}
          </h3>
        ),
        strong: ({ children }) => (
          <strong className="font-semibold text-ink">{children}</strong>
        ),
        em: ({ children }) => <em className="italic">{children}</em>,
        a: ({ children, href }) => (
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="text-gold underline decoration-gold/40 underline-offset-2 hover:decoration-gold"
          >
            {children}
          </a>
        ),
        ul: ({ children }) => (
          <ul className="mb-3 ml-5 list-disc space-y-1 last:mb-0 marker:text-gold/60">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-3 ml-5 list-decimal space-y-1 last:mb-0 marker:text-gold/60">
            {children}
          </ol>
        ),
        li: ({ children }) => <li className="leading-[1.6]">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="my-3 border-l-2 border-gold/40 pl-4 italic text-ink/75">
            {children}
          </blockquote>
        ),
        code: ({ className, children }) => {
          const isBlock = (className ?? "").includes("language-");
          if (isBlock) {
            return (
              <code className="font-mono text-[0.82em] leading-relaxed">{children}</code>
            );
          }
          return (
            <code className="rounded-sm bg-gold/10 px-1 py-0.5 font-mono text-[0.85em] text-ink">
              {children}
            </code>
          );
        },
        pre: ({ children }) => (
          <pre className="my-3 overflow-x-auto rounded-sm border border-line bg-void/50 p-3 last:mb-0">
            {children}
          </pre>
        ),
        hr: () => <hr className="my-4 border-line" />,
        table: ({ children }) => (
          <div className="my-3 overflow-x-auto">
            <table className="w-full border-collapse text-[0.92em]">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-line px-2 py-1 text-left font-semibold">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-line px-2 py-1 align-top">{children}</td>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
