// The pluggable source interface. A source turns "these type ids (or everything it has)" into docs/22 §4.5 per-type
// entries. Order-book sources (ESI) hand raw orders to the shared rule (rule.ts); aggregate sources (Fuzzwork) can
// only approximate it, say so (`exact: false`, `notes`) and still fill every §4.5 field.
import type { Order, RuleParams, TypePrice } from "../rule.js";

/** docs/22 §4.3 static part of `source` (the fetch window is per run, see SourceResult) */
export interface SourceDescriptor {
  /** `source.kind`: "esi" | "fuzzwork" | other registered plug-in names; also the CLI name */
  kind: string;
  /** base URL or dataset name used */
  endpoint: string;
  region_id: number;
  location_id: number;
  /** `market` id used in snapshot ids and file names, e.g. "jita44" */
  market: string;
}

export interface FetchOptions {
  /** price only these types; null/undefined = every type the source has (order sources only) */
  types?: readonly number[] | null;
  rule: RuleParams;
  log?: (msg: string) => void;
  signal?: AbortSignal;
}

export interface SourceResult {
  prices: Map<number, TypePrice>;
  /** requested (or seen) types without a qualifying order, ascending */
  missing: number[];
  /** market state the prices describe: max Last-Modified over pages/types (ISO UTC, seconds); null if unknown */
  market_time: string | null;
  /** fetch window, ISO UTC seconds */
  fetched_from: string;
  fetched_to: string;
  /** false when the source can only approximate the rule (`rule.exact`) */
  exact: boolean;
  /** free text for `source.notes` (e.g. aggregate limitations) */
  notes?: string;
  /** run counters (pages, orders seen, requests, cache hits, ...); logged, not part of the snapshot */
  stats: Record<string, number>;
}

export interface Source {
  readonly descriptor: SourceDescriptor;
  fetchPrices(opts: FetchOptions): Promise<SourceResult>;
}

/** Order sources can also hand out the raw orders (tests, other rules). */
export interface OrderSource extends Source {
  fetchOrders(opts: Omit<FetchOptions, "rule">): Promise<{ orders: Order[]; market_time: string | null; stats: Record<string, number> }>;
}

export const isoSecond = (d: Date | number | string) => new Date(d).toISOString().replace(/\.\d{3}Z$/, "Z");
