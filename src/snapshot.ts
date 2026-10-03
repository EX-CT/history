// Price snapshots: the self-contained, deterministic file engines embed at release and accept at run time.
// Schema: schema/snapshot.v1.schema.json (DRAFT, pending eve-fit-docs docs/22). Pure module (Node + browser).
import { stableStringify } from "./canonical.js";
import type { RuleParams, TypePrice } from "./rule.js";
import type { SourceDescriptor, SourceResult } from "./sources/types.js";

export const SCHEMA_ID = "eve-market-prices/snapshot";
export const SCHEMA_VERSION = 1;
export const SCHEMA_STATUS = "draft";

export interface DatasetRef {
  /** e.g. "eve-sde-pipeline sde-3569502-r5" */
  name: string | null;
  sde_build: number | null;
  /** sha256 of the dataset file as given */
  sha256: string | null;
}

export interface Snapshot {
  schema: typeof SCHEMA_ID;
  schema_version: number;
  /** "draft" until eve-fit-docs docs/22 fixes the format */
  schema_status: string;
  /** when the snapshot was made, ISO 8601 UTC, second precision */
  generated_at: string;
  /** newest Last-Modified of the source data, when the source reports it */
  data_as_of: string | null;
  generator: { name: string; version: string };
  source: SourceDescriptor;
  currency: "ISK";
  /** band rule parameters (order sources); null when the source publishes aggregates (see source.method) */
  rule: RuleParams | null;
  coverage: {
    /** the type universe the snapshot was made for (eve-sde-pipeline dataset), or null = every type the source had */
    dataset: DatasetRef | null;
    types_requested: number | null;
    types_priced: number;
    /** requested / seen types that got no price, ascending */
    types_unpriced: number[];
  };
  /** data-derived source counters (pages, orders seen, orders at the location) */
  stats: Record<string, number>;
  /** type id -> price; ISK rounded to 0.01 */
  prices: Record<string, TypePrice>;
}

/** Source counters that depend only on the data (not on caching / retries), so they keep the snapshot deterministic. */
const STABLE_STATS = ["pages", "orders_seen", "orders_at_location", "inconsistent_pages"];

export const isoSecond = (d: Date | number | string) => new Date(d).toISOString().replace(/\.\d{3}Z$/, "Z");

export function buildSnapshot(a: {
  result: SourceResult;
  source: SourceDescriptor;
  generated_at: Date | string | number;
  generator: { name: string; version: string };
  dataset?: DatasetRef | null;
  types_requested?: number | null;
}): Snapshot {
  const prices: Record<string, TypePrice> = {};
  for (const [t, p] of [...a.result.prices].sort((x, y) => x[0] - y[0])) prices[String(t)] = { p0: p.p0, price: p.price, units: p.units, orders: p.orders };
  const stats: Record<string, number> = {};
  for (const k of STABLE_STATS) if (typeof a.result.stats[k] === "number") stats[k] = a.result.stats[k];
  return {
    schema: SCHEMA_ID,
    schema_version: SCHEMA_VERSION,
    schema_status: SCHEMA_STATUS,
    generated_at: isoSecond(a.generated_at),
    data_as_of: a.result.data_as_of,
    generator: a.generator,
    source: a.source,
    currency: "ISK",
    rule: a.result.rule ? { min_units: a.result.rule.min_units, band: a.result.rule.band } : null,
    coverage: {
      dataset: a.dataset ?? null,
      types_requested: a.types_requested ?? null,
      types_priced: a.result.prices.size,
      types_unpriced: [...new Set(a.result.unpriced)].sort((x, y) => x - y),
    },
    stats,
    prices,
  };
}

/** The canonical bytes of a snapshot (sorted keys, 2-space indent, trailing newline). */
export function serializeSnapshot(s: Snapshot): string {
  return stableStringify(s);
}

/** Parse + validate the parts consumers rely on (no JSON-Schema dependency; full schema in schema/). */
export function parseSnapshot(input: string | unknown): Snapshot {
  const s = (typeof input === "string" ? JSON.parse(input) : input) as Snapshot;
  const fail = (m: string): never => {
    throw new Error(`not a price snapshot: ${m}`);
  };
  if (!s || typeof s !== "object") fail("not an object");
  if (s.schema !== SCHEMA_ID) fail(`schema is ${JSON.stringify(s.schema)}, want ${SCHEMA_ID}`);
  if (s.schema_version !== SCHEMA_VERSION) fail(`schema_version ${s.schema_version} is not supported (this reader: ${SCHEMA_VERSION})`);
  if (typeof s.generated_at !== "string" || Number.isNaN(Date.parse(s.generated_at))) fail("generated_at");
  if (!s.source || typeof s.source.id !== "string") fail("source.id");
  if (!s.prices || typeof s.prices !== "object") fail("prices");
  for (const [k, p] of Object.entries(s.prices)) {
    if (!/^[1-9]\d*$/.test(k)) fail(`price key ${k} is not a type id`);
    if (!(p.price > 0) || !(p.p0 > 0) || !(p.units > 0) || !(p.orders > 0)) fail(`price of type ${k}`);
  }
  return s;
}

/** Price of one type (the band-weighted sell price), or null. */
export function priceOf(s: Snapshot, typeId: number): number | null {
  return s.prices[String(typeId)]?.price ?? null;
}

/** Pick the snapshot to use: a runtime-injected one wins over the embedded one when it parses and is newer. */
export function chooseSnapshot(embedded: Snapshot, injected?: Snapshot | null): Snapshot {
  if (!injected) return embedded;
  return Date.parse(injected.generated_at) >= Date.parse(embedded.generated_at) ? injected : embedded;
}
