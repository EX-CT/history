// Deterministic JSON: object keys sorted (numeric-looking keys numerically, so type ids read in order), 2-space
// indent, "\n" line ends, trailing newline. Same input -> same bytes on every platform.

const isIndex = (k: string) => /^(0|[1-9]\d*)$/.test(k);
const cmpKeys = (a: string, b: string) => {
  const ia = isIndex(a);
  const ib = isIndex(b);
  if (ia && ib) return Number(a) - Number(b);
  if (ia !== ib) return ia ? -1 : 1;
  return a < b ? -1 : a > b ? 1 : 0;
};

export function canonicalize(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(canonicalize);
  if (v && typeof v === "object") {
    const o = v as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(o).sort(cmpKeys)) if (o[k] !== undefined) out[k] = canonicalize(o[k]);
    return out;
  }
  if (typeof v === "number" && !Number.isFinite(v)) throw new Error(`non-finite number in snapshot: ${v}`);
  return v;
}

/**
 * Stable formatting. JS engines keep integer-like keys in ascending numeric order regardless of insertion order,
 * which is exactly cmpKeys' order for those keys; the remaining keys follow in sorted insertion order.
 */
export function stableStringify(v: unknown): string {
  return JSON.stringify(canonicalize(v), null, 2) + "\n";
}
