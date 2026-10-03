// Canonical JSON (docs/22 §4.6): object keys sorted by code point (like Python sort_keys / Rust BTreeMap<String>,
// so "1000" < "34"), UTF-8, numbers as the shortest round-trip representation (ECMAScript Number -> String: integers
// without exponent or ".0"). `canonicalJson` (no whitespace) is what content_hash covers; `stableStringify` is the
// same order with a 2-space indent and a trailing newline, used for the files (stable, diffable).
// JSON.stringify cannot be used for objects: it always emits integer-like keys first, in numeric order.

const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

function emit(v: unknown, indent: string, depth: number): string {
  if (v === null) return "null";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) throw new Error(`non-finite number in snapshot: ${v}`);
    return JSON.stringify(v);
  }
  if (typeof v === "string" || typeof v === "boolean") return JSON.stringify(v);
  const nl = indent ? "\n" + indent.repeat(depth + 1) : "";
  const end = indent ? "\n" + indent.repeat(depth) : "";
  const sep = indent ? ": " : ":";
  if (Array.isArray(v)) {
    if (!v.length) return "[]";
    return "[" + v.map((x) => nl + emit(x === undefined ? null : x, indent, depth + 1)).join(",") + end + "]";
  }
  if (typeof v === "object") {
    const o = v as Record<string, unknown>;
    const keys = Object.keys(o).filter((k) => o[k] !== undefined).sort(cmp);
    if (!keys.length) return "{}";
    return "{" + keys.map((k) => nl + JSON.stringify(k) + sep + emit(o[k], indent, depth + 1)).join(",") + end + "}";
  }
  throw new Error(`cannot serialise ${typeof v}`);
}

/** docs/22 §4.6 canonical form: sorted keys, no insignificant whitespace. */
export const canonicalJson = (v: unknown): string => emit(v, "", 0);

/** Same order, 2-space indent, trailing newline: the on-disk form. */
export const stableStringify = (v: unknown): string => emit(v, "  ", 0) + "\n";
