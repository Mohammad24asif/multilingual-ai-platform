import type { ReactNode } from "react";

export type Tone = "ok" | "warn" | "bad" | "neutral";

const TONES: Record<Tone, string> = {
  ok: "bg-okbg text-ok",
  warn: "bg-warnbg text-warn",
  bad: "bg-badbg text-bad",
  neutral: "bg-panel2 text-soft",
};

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}
