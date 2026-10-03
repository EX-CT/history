// Price snapshot `eve-price-snapshot` v1 (eve-fit-docs docs/22 §4): the self-contained, deterministic file engines
// embed at release and accept at run time. Engines read types[*].price only (and apply their own overrides).
// JSON Schema: schema/eve-price-snapshot.v1.schema.json. Pure module (Node + browser).
import { canonicalJson, stableStringify } from "./canonical.js";
import { RULE_NAME, RULE_VERSION, type RuleParams, type TypePrice } from "./rule.js";
import { sha256Hex } from "./sha256.js";
import { isoSecond, type SourceDescriptor, type SourceResult } from "./sources/types.js";

export const SCHEMA_ID = "eve-price-snapshot";
export const SCHEMA_VERSION = 1;

export interface SnapshotSource {
  kind: string;
  endpoint: string;
  region_id: number;
  location_id: number;
  fetched_from: string;
  fetched_to: string;
  notes?: string;
}

export interface SnapshotRule {
  name: string;
  version: number;
  order_side: "sell";
  location_id: number;
  min_units: number;
  band: number;
  weighting: "units";
  exact: boolean;
}

/** Optional, additive (docs/22 §4.1 allows additive optional fields in v1): what universe was priced. */
export interface SnapshotCoverage {
  /** dataset file name or label the type list came from */
  dataset: string | null;
  /** sha256 of that dataset file */
  dataset_sha256: string | null;
  /** number of distinct types requested (null = every type the source had) */
  types_requested: number | null;
}

export interface Snapshot {
  schema: typeof SCHEMA_ID;
  schema_version: number;
  snapshot_id: string;
  market: string;
  market_time: string;
  generated_at: string;
  source: SnapshotSource;
  rule: SnapshotRule;
  currency: "ISK";
  sde_build: number;
  type_count: number;
  types: Record<string, TypePrice>;
  missing: number[];
  updater: { name: string; version: string };
  coverage?: SnapshotCoverage;
  content_hash: string;
}

const compactTime = (iso: string) => iso.replace(/[-:]/g, "");
/** `<market>-<YYYYMMDDTHHMMSSZ>` of market_time (§4.1) */
export const snapshotId = (market: string, market_time: string) => `${market}-${compactTime(market_time)}`;
/** `prices-<market>-<YYYYMMDDTHHMMSSZ>.json` (add `.gz` for the gzip form) */
export const snapshotFileName = (s: Pick<Snapshot, "market" | "market_time">) => `prices-${snapshotId(s.market, s.market_time)}.json`;

/** "sha256:<hex>" over the canonical JSON of the object without content_hash (§4.6). */
export function contentHash(s: Omit<Snapshot, "content_hash"> | Snapshot): string {
  const { content_hash: _drop, ...rest } = s as Snapshot;
  return `sha256:${sha256Hex(canonicalJson(rest))}`;
}

export function buildSnapshot(a: {
  result: SourceResult;
  source: SourceDescriptor;
  rule: RuleParams;
  sde_build: number;
  generated_at: Date | string | number;
  updater: { name: string; version: string };
  coverage?: SnapshotCoverage | null;
}): Snapshot {
  if (!Number.isInteger(a.sde_build) || a.sde_build <= 0) throw new Error(`sde_build must be a positive integer (got ${a.sde_build})`);
  const types: Record<string, TypePrice> = {};
  for (const [t, p] of [...a.result.prices].sort((x, y) => x[0] - y[0]))
    types[String(t)] = {
      price: p.price,
      p0: p.p0,
      band_max: p.band_max,
      units: p.units,
      orders: p.orders,
      units_considered: p.units_considered,
      orders_considered: p.orders_considered,
      orders_total: p.orders_total,
    };
  const market_time = a.result.market_time ?? a.result.fetched_to;
  const source: SnapshotSource = {
    kind: a.source.kind,
    endpoint: a.source.endpoint,
    region_id: a.source.region_id,
    location_id: a.source.location_id,
    fetched_from: a.result.fetched_from,
    fetched_to: a.result.fetched_to,
  };
  if (a.result.notes) source.notes = a.result.notes;
  const body: Omit<Snapshot, "content_hash"> = {
    schema: SCHEMA_ID,
    schema_version: SCHEMA_VERSION,
    snapshot_id: snapshotId(a.source.market, market_time),
    market: a.source.market,
    market_time,
    generated_at: isoSecond(a.generated_at),
    source,
    rule: {
      name: RULE_NAME,
      version: RULE_VERSION,
      order_side: "sell",
      location_id: a.source.location_id,
      min_units: a.rule.min_units,
      band: a.rule.band,
      weighting: "units",
      exact: a.result.exact,
    },
    currency: "ISK",
    sde_build: a.sde_build,
    type_count: Object.keys(types).length,
    types,
    missing: [...new Set(a.result.missing)].filter((t) => !a.result.prices.has(t)).sort((x, y) => x - y),
    updater: { name: a.updater.name, version: a.updater.version },
  };
  if (a.coverage) body.coverage = a.coverage;
  return { ...body, content_hash: contentHash(body) };
}

/** The on-disk bytes (sorted keys, 2-space indent, trailing newline). */
export const serializeSnapshot = (s: Snapshot): string => stableStringify(s);

export class SnapshotError extends Error {
  constructor(
    readonly code: "PRICE_SNAPSHOT_VERSION" | "PRICE_SNAPSHOT_INVALID",
    msg: string,
  ) {
    super(`${code}: ${msg}`);
  }
}

const RFC3339_UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/;

/** Parse and check a snapshot like engines do on load (§4.5 invariants, §4.6 hash, §5 error codes). */
export function parseSnapshot(input: string | unknown): Snapshot {
  const s = (typeof input === "string" ? JSON.parse(input) : input) as Snapshot;
  const bad = (m: string): never => {
    throw new SnapshotError("PRICE_SNAPSHOT_INVALID", m);
  };
  if (!s || typeof s !== "object") bad("not an object");
  if (s.schema !== SCHEMA_ID || s.schema_version !== SCHEMA_VERSION)
    throw new SnapshotError("PRICE_SNAPSHOT_VERSION", `${JSON.stringify(s.schema)} v${s.schema_version} (this reader: ${SCHEMA_ID} v${SCHEMA_VERSION})`);
  for (const k of ["market_time", "generated_at"] as const) if (typeof s[k] !== "string" || !RFC3339_UTC.test(s[k])) bad(`${k} is not RFC 3339 UTC seconds`);
  if (!s.types || typeof s.types !== "object") bad("types");
  if (!Array.isArray(s.missing)) bad("missing");
  const keys = Object.keys(s.types);
  if (s.type_count !== keys.length) bad(`type_count ${s.type_count} != ${keys.length} entries`);
  const fin = (v: unknown) => typeof v === "number" && Number.isFinite(v);
  for (const k of keys) {
    const p = s.types[k];
    if (!/^[1-9]\d*$/.test(k)) bad(`type key ${k} is not a type id`);
    if (![p.price, p.p0, p.band_max, p.units, p.orders, p.units_considered, p.orders_considered, p.orders_total].every(fin)) bad(`type ${k}: non-finite or missing field`);
    if (!(p.p0 <= p.price && p.price <= p.band_max)) bad(`type ${k}: p0 <= price <= band_max broken`);
    if (!(0 < p.units && p.units <= p.units_considered)) bad(`type ${k}: 0 < units <= units_considered broken`);
    if (!(0 < p.orders && p.orders <= p.orders_considered && p.orders_considered <= p.orders_total)) bad(`type ${k}: order counts broken`);
  }
  const h = contentHash(s);
  if (s.content_hash !== h) bad(`content_hash ${s.content_hash} != ${h}`);
  return s;
}

/** Price of one type, or null. (Engines apply overrides themselves; this is a convenience for tools.) */
export const priceOf = (s: Snapshot, typeId: number): number | null => s.types[String(typeId)]?.price ?? null;
