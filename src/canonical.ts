// Canonical JSON = RFC 8785 JCS (docs/22 §4.6, eve ruling 2026-10-03 14:56): object keys sorted by UTF-16 code units
// (JS string comparison; "1000" < "34", U+1F600 before U+FB33), no insignificant whitespace, UTF-8, strings escaped
// like ECMAScript JSON.stringify (\b \t \n \f \r, other controls as lowercase \u00xx, nothing else), numbers in
// ECMAScript Number -> String form (shortest round trip, no ".0": 1240000, 4988.83, 1e+21, -0 -> 0), so integers and
// integral floats hash the same. Lone surrogates are rejected (JCS needs I-JSON). `canonicalJson` is what content_hash
// covers (cross-checked against the Python `jcs` package in test/canonical.test.ts vectors); `stableStringify` is the
// same order with a 2-space indent and a trailing newline, used for the files (stable, diffable).
// JSON.stringify cannot be used for objects: it always emits integer-like keys first, in numeric order.

const LONE = /[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]/;
const str = (v: string) => {
  if (LONE.test(v)) throw new Error(`lone surrogate in string (not I-JSON, RFC 8785 §3.1): ${JSON.stringify(v)}`);
  return JSON.stringify(v);
};

const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

function emit(v: unknown, indent: string, depth: number): string {
  if (v === null) return "null";
  if (typeof v === "number") {
    if (!Number.isFinite(v)) throw new Error(`non-finite number in snapshot: ${v}`);
    return JSON.stringify(v);
  }
  if (typeof v === "string") return str(v);
  if (typeof v === "boolean") return JSON.stringify(v);
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
    return "{" + keys.map((k) => nl + str(k) + sep + emit(o[k], indent, depth + 1)).join(",") + end + "}";
  }
  throw new Error(`cannot serialise ${typeof v}`);
}

/** docs/22 §4.6 canonical form: RFC 8785 JCS. */
export const canonicalJson = (v: unknown): string => emit(v, "", 0);

/** Same order, 2-space indent, trailing newline: the on-disk form. */
export const stableStringify = (v: unknown): string => emit(v, "  ", 0) + "\n";
