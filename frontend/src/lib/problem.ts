import type { Problem } from "../api/types";

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === "string") : [];
}

export function problemCandidates(p: Problem): string[] {
  return strings(p.candidates);
}

export function problemSuggested(p: Problem): string | null {
  return typeof p.suggested === "string" ? p.suggested : null;
}

export function problemPivotVia(p: Problem): string | null {
  return typeof p.pivot_available_via === "string" ? p.pivot_available_via : null;
}

export function problemHint(p: Problem): string | null {
  return typeof p.hint === "string" ? p.hint : null;
}

export function problemUnlisted(p: Problem): string[] {
  return strings(p.unlisted_candidates);
}
