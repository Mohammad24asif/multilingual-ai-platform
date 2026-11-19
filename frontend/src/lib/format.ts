export function formatMs(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${Math.round(ms)} ms`;
}

export function formatCount(n: number): string {
  return n.toLocaleString("en-US");
}

export function formatMb(mb: number | null | undefined): string {
  if (mb === null || mb === undefined) return "unknown";
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb} MB`;
}
