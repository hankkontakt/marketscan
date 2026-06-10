"use client";

import React from "react";

/**
 * MarkdownLite — renderar lättviktig markdown från LLM-text utan externa libs.
 * Stödjer: **fet**, punktlistor (- / * / •), numrerade punkter och stycken.
 * Tar bort kvarvarande markdown-tecken (#, `, lösa *) så inget läcker som råtext.
 */
function renderInline(s: string, keyBase: string): React.ReactNode[] {
  // Dela på **fet** och rendera resten som ren text (stripa lösa *)
  const parts = s.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    const m = p.match(/^\*\*([^*]+)\*\*$/);
    if (m) return <strong key={`${keyBase}-${i}`}>{m[1]}</strong>;
    return <React.Fragment key={`${keyBase}-${i}`}>{p.replace(/\*/g, "")}</React.Fragment>;
  });
}

export function MarkdownLite({ text, className }: { text: string; className?: string }) {
  const cleaned = (text ?? "")
    .replace(/^#{1,6}\s+/gm, "") // rubrik-markörer
    .replace(/`+/g, "")          // kod-backticks
    .trim();

  if (!cleaned) return null;

  const lines = cleaned.split(/\n/);
  const blocks: React.ReactNode[] = [];
  let bullets: string[] = [];

  const flush = () => {
    if (bullets.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="list-disc pl-4 space-y-1 my-1.5">
          {bullets.map((b, i) => (
            <li key={i}>{renderInline(b, `li-${blocks.length}-${i}`)}</li>
          ))}
        </ul>,
      );
      bullets = [];
    }
  };

  lines.forEach((raw, idx) => {
    const t = raw.trim();
    const bullet = t.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/);
    if (bullet) {
      bullets.push(bullet[1]);
      return;
    }
    flush();
    if (t) {
      blocks.push(
        <p key={`p-${idx}`} className="my-1.5 first:mt-0 last:mb-0">
          {renderInline(t, `p-${idx}`)}
        </p>,
      );
    }
  });
  flush();

  return <div className={className}>{blocks}</div>;
}
