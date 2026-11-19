import type { ReactNode } from "react";

type NoticeTone = "info" | "warn" | "bad" | "ok";

const STYLES: Record<NoticeTone, string> = {
  info: "border-accent bg-panel2",
  warn: "border-warn bg-warnbg text-warn",
  bad: "border-bad bg-badbg text-bad",
  ok: "border-ok bg-okbg text-ok",
};

export function Notice({ tone = "info", title, children }: { tone?: NoticeTone; title?: string; children?: ReactNode }) {
  return (
    <div role={tone === "bad" ? "alert" : "status"} className={`rounded-md border-l-4 px-4 py-3 text-sm ${STYLES[tone]}`}>
      {title && <p className="font-semibold">{title}</p>}
      {children}
    </div>
  );
}
