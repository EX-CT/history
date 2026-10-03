// The pluggable source interface. A source turns "these type ids (or everything it has)" into per-type prices.
// Order-book sources (ESI) return raw orders and the shared rule (rule.ts) prices them; aggregate sources (Fuzzwork)
// only publish per-type statistics and map them onto the same TypePrice fields (documented per source).
import type { Order, RuleParams, TypePrice } from "../rule.js";

export type SourceKind = "orders" | "aggregate";

export interface SourceDescriptor {
  /** stable id used in snapshots and on the CLI, e.g. "esi", "fuzzwork" */
  id: string;
  kind: SourceKind;
  /** how TypePrice is derived, e.g. "band-weighted-sell" (rule.ts) or "fuzzwork-sell-percentile" */
  method: string;
  /** source-specific parameters recorded in the snapshot (region, location, endpoint, ...) */
  params: Record<string, string | number | boolean | null>;
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
  /** types seen or requested that got no price (no order left after the min_units filter, or no data) */
  unpriced: number[];
  /** newest Last-Modified of the data the source served (ISO 8601 UTC), when known */
  data_as_of: string | null;
  /** what the rule actually used ("rule" for order sources; null for aggregate sources) */
  rule: RuleParams | null;
  /** counters for the snapshot (pages, orders seen, orders at the location, requests, cache hits, ...) */
  stats: Record<string, number>;
}

export interface Source {
  readonly descriptor: SourceDescriptor;
  fetchPrices(opts: FetchOptions): Promise<SourceResult>;
}

/** Order sources can also hand out the raw orders (tests, other rules). */
export interface OrderSource extends Source {
  fetchOrders(opts: Omit<FetchOptions, "rule">): Promise<{ orders: Order[]; data_as_of: string | null; stats: Record<string, number> }>;
}
