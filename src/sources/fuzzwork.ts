// Fuzzwork market aggregates (https://market.fuzzwork.co.uk/aggregates/?station=<id>&types=<ids>): per-type
// buy/sell statistics computed by Fuzzwork from ESI. There is no order book, so the rule can only be approximated
// (`rule.exact: false`): p0 = sell.min, price = sell.percentile (Fuzzwork's average of the cheapest 5% of units),
// clamped to [p0, band_max]; units = units_considered = sell.volume; orders = orders_considered = orders_total =
// sell.orderCount. min_units cannot be applied. market_time = the end of the fetch window (no Last-Modified).
import { roundIsk, trim, type TypePrice } from "../rule.js";
import { HttpClient, type HttpOptions } from "./http.js";
import { JITA_4_4, THE_FORGE } from "./esi.js";
import { isoSecond, type FetchOptions, type Source, type SourceDescriptor, type SourceResult } from "./types.js";

export interface FuzzworkOptions extends HttpOptions {
  station?: number;
  region_id?: number;
  market?: string;
  base_url?: string;
  /** type ids per request (default 200) */
  batch?: number;
}

type Side = { min: string | number; percentile: string | number; volume: string | number; orderCount: string | number };

export const FUZZWORK_NOTES =
  "Fuzzwork aggregates approximate the rule: p0 = sell.min, price = sell.percentile (average of the cheapest 5% of units) clamped to [p0, band_max], units = sell.volume, orders = sell.orderCount; min_units is not applied; market_time = fetch time.";

export class FuzzworkSource implements Source {
  readonly descriptor: SourceDescriptor;
  readonly http: HttpClient;
  private readonly station: number;
  private readonly base: string;

  constructor(private readonly o: FuzzworkOptions) {
    this.station = o.station ?? JITA_4_4;
    this.base = (o.base_url ?? "https://market.fuzzwork.co.uk").replace(/\/$/, "");
    this.http = new HttpClient(o);
    this.descriptor = {
      kind: "fuzzwork",
      endpoint: `${this.base}/aggregates/`,
      region_id: o.region_id ?? THE_FORGE,
      location_id: this.station,
      market: o.market ?? (this.station === JITA_4_4 ? "jita44" : `loc${this.station}`),
    };
  }

  async fetchPrices(opts: FetchOptions): Promise<SourceResult> {
    if (!opts.types?.length) throw new Error("fuzzwork needs a type list (--types or --dataset)");
    const fetched_from = isoSecond(this.http.clock());
    const types = [...new Set(opts.types)].sort((a, b) => a - b);
    const n = Math.max(1, this.o.batch ?? 200);
    const prices = new Map<number, TypePrice>();
    const missing: number[] = [];
    for (let i = 0; i < types.length; i += n) {
      const chunk = types.slice(i, i + n);
      const r = await this.http.get(`${this.base}/aggregates/?station=${this.station}&types=${chunk.join(",")}`, { signal: opts.signal });
      const body = JSON.parse(r.body) as Record<string, { sell?: Side }>;
      for (const t of chunk) {
        const s = body[String(t)]?.sell;
        const orders = Math.round(Number(s?.orderCount ?? 0));
        const p0 = Number(s?.min);
        const units = Math.round(Number(s?.volume ?? 0));
        if (!s || !(orders > 0) || !(p0 > 0) || !(units > 0)) {
          missing.push(t);
          continue;
        }
        const band_max = trim(p0 * (1 + opts.rule.band));
        const price = Math.min(Math.max(roundIsk(Number(s.percentile)), p0), band_max);
        prices.set(t, { price, p0, band_max, units, orders, units_considered: units, orders_considered: orders, orders_total: orders });
      }
      opts.log?.(`fuzzwork: ${Math.min(i + n, types.length)}/${types.length} types`);
    }
    const fetched_to = isoSecond(this.http.clock());
    return { prices, missing, market_time: fetched_to, fetched_from, fetched_to, exact: false, notes: FUZZWORK_NOTES, stats: { ...this.http.stats } };
  }
}
