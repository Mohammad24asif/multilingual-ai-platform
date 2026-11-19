import type { ReactNode } from "react";
import type { Readiness } from "../api/types";
import type { Route } from "../hooks/useHashRoute";
import { Badge } from "./Badge";
import { ThemeToggle } from "./ThemeToggle";

const LINKS: { route: Route; label: string }[] = [
  { route: "translate", label: "Translate" },
  { route: "models", label: "Models and languages" },
  { route: "status", label: "Status" },
];

export function Shell({ route, readiness, children }: { route: Route; readiness: Readiness | null; children: ReactNode }) {
  return (
    <div className="min-h-screen md:grid md:grid-cols-[15rem_1fr]">
      <aside className="border-b border-rule bg-panel md:min-h-screen md:border-b-0 md:border-r">
        <div className="flex items-start justify-between gap-3 px-5 py-4">
          <div>
            <p className="font-serif text-lg font-semibold leading-tight">Multilingual AI Platform</p>
            <p className="mt-1 text-xs text-soft">English and Indian languages</p>
          </div>
          <ThemeToggle />
        </div>
        <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:pb-0">
          {LINKS.map((link) => (
            <a
              key={link.route}
              href={`#/${link.route}`}
              aria-current={route === link.route ? "page" : undefined}
              className={`whitespace-nowrap rounded-md px-3 py-2 text-sm ${
                route === link.route ? "bg-panel2 font-semibold text-ink" : "text-soft hover:bg-panel2 hover:text-ink"
              }`}
            >
              {link.label}
            </a>
          ))}
        </nav>
        <div className="hidden px-5 py-4 text-xs text-soft md:block">
          {readiness ? (
            <Badge tone={readiness.ready ? "ok" : "warn"}>{readiness.ready ? "Ready to translate" : "Not ready yet"}</Badge>
          ) : (
            <Badge>Checking server…</Badge>
          )}
        </div>
      </aside>
      <main className="max-w-6xl px-4 py-6 md:px-10 md:py-8">{children}</main>
    </div>
  );
}
