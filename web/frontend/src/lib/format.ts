/**
 * Token formatter — direct port of `formatTokens` in
 * pi-mono-main/packages/coding-agent/src/modes/interactive/components/footer.ts
 *
 *   <1k     → "423"
 *   <10k    → "1.2k"
 *   <1M     → "12k"
 *   <10M    → "1.2M"
 *   else    → "12M"
 */
export function formatTokens(count: number): string {
  if (count < 1000) return count.toString();
  if (count < 10_000) return `${(count / 1000).toFixed(1)}k`;
  if (count < 1_000_000) return `${Math.round(count / 1000)}k`;
  if (count < 10_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  return `${Math.round(count / 1_000_000)}M`;
}

export function formatCost(usd: number): string {
  if (!usd) return "$0";
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  if (usd < 1) return `$${usd.toFixed(3)}`;
  return `$${usd.toFixed(2)}`;
}

export function shortId(id: string, n = 8): string {
  return id.length > n ? id.slice(0, n) : id;
}
