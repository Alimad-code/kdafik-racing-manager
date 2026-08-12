import type { ElementType, ReactNode } from "react";

type MarkdownBlock =
  | { type: "heading"; level: number; lines: string[] }
  | { type: "paragraph"; lines: string[] }
  | { type: "quote"; lines: string[] }
  | { type: "list"; lines: string[] };

function isSafeHref(href: string) {
  return href.startsWith("/") || href.startsWith("#") || /^https?:\/\//i.test(href);
}

function renderInline(source: string, keyPrefix: string): ReactNode[] {
  const tokenPattern = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|\*[^*]+\*)/g;
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let tokenIndex = 0;

  for (const match of source.matchAll(tokenPattern)) {
    const token = match[0];
    const start = match.index ?? 0;
    if (start > cursor) nodes.push(source.slice(cursor, start));

    const key = `${keyPrefix}-${tokenIndex}`;
    if (token.startsWith("**")) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("[")) {
      const linkMatch = /^\[([^\]]+)\]\(([^)]+)\)$/.exec(token);
      if (linkMatch && isSafeHref(linkMatch[2])) {
        nodes.push(
          <a
            key={key}
            href={linkMatch[2]}
            rel={/^https?:\/\//i.test(linkMatch[2]) ? "noreferrer" : undefined}
            target={/^https?:\/\//i.test(linkMatch[2]) ? "_blank" : undefined}
          >
            {linkMatch[1]}
          </a>
        );
      } else {
        nodes.push(token);
      }
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    }

    cursor = start + token.length;
    tokenIndex += 1;
  }

  if (cursor < source.length) nodes.push(source.slice(cursor));
  return nodes;
}

function renderLines(lines: string[], keyPrefix: string) {
  return lines.flatMap((line, index) => {
    const hasHardBreak = / {2}$/.test(line);
    const content = line.trimEnd();
    const result: ReactNode[] = [
      <span key={`${keyPrefix}-${index}`}>{renderInline(content, `${keyPrefix}-${index}`)}</span>
    ];

    if (index < lines.length - 1) {
      result.push(
        hasHardBreak ? (
          <br key={`${keyPrefix}-break-${index}`} />
        ) : (
          <span key={`${keyPrefix}-space-${index}`}> </span>
        )
      );
    }
    return result;
  });
}

function parseBlocks(markdown: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  let current: MarkdownBlock | null = null;

  const flush = () => {
    if (current) blocks.push(current);
    current = null;
  };

  for (const rawLine of markdown.replace(/\r\n?/g, "\n").split("\n")) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      flush();
      continue;
    }

    const headingMatch = /^(#{1,6})\s+(.+)$/.exec(line);
    if (headingMatch) {
      flush();
      blocks.push({ type: "heading", level: headingMatch[1].length, lines: [headingMatch[2]] });
      continue;
    }

    const quoteMatch = /^>\s?(.*)$/.exec(line);
    if (quoteMatch) {
      if (current?.type !== "quote") {
        flush();
        current = { type: "quote", lines: [] };
      }
      current.lines.push(quoteMatch[1]);
      continue;
    }

    const listMatch = /^[-*]\s+(.+)$/.exec(line);
    if (listMatch) {
      if (current?.type !== "list") {
        flush();
        current = { type: "list", lines: [] };
      }
      current.lines.push(listMatch[1]);
      continue;
    }

    if (current?.type !== "paragraph") {
      flush();
      current = { type: "paragraph", lines: [] };
    }
    current.lines.push(line);
  }
  flush();
  return blocks;
}

export function LegalMarkdown({ content }: { content: string }) {
  return (
    <div className="legal-markdown mt-6">
      {parseBlocks(content).map((block, index) => {
        const key = `legal-block-${index}`;
        if (block.type === "heading") {
          const Heading = `h${Math.min(block.level + 1, 6)}` as ElementType;
          return <Heading key={key}>{renderLines(block.lines, key)}</Heading>;
        }
        if (block.type === "quote") {
          return <blockquote key={key}>{renderLines(block.lines, key)}</blockquote>;
        }
        if (block.type === "list") {
          return (
            <ul key={key}>
              {block.lines.map((line, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>{renderInline(line, `${key}-${itemIndex}`)}</li>
              ))}
            </ul>
          );
        }
        return <p key={key}>{renderLines(block.lines, key)}</p>;
      })}
    </div>
  );
}
