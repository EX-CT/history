// Fuzzwork market aggregates (https://market.fuzzwork.co.uk/aggregates/?station=<id>&types=<ids>): per-type
// buy/sell statistics computed by Fuzzwork from ESI. There is no order book, so the band rule cannot run; the
// SELL side maps onto TypePrice as p0 = sell.min, price = sell.percentile (Fuzzwork's 5% volume percentile),
// units = sell.volume, orders = sell.orderCount (method "fuzzwork-sell-percentile"; min_units/band do not apply).
import type { TypePrice } from "../rule.js";
import { roundIsk } from "../rule.js";
import { HttpClient, type HttpOptions } from "./http.js";
import { JITA_4_4 } from "./esi.js";
import type { FetchOptions, Source, SourceDescriptor, SourceResult } from "./types.js";

export interface FuzzworkOptions extends HttpOptions {
  station?: number;
  base_url?: string;
  /** type ids per request (default 200) */
  batch?: number;
}

type Side = { min: string | number; percentile: string | number; volume: string | number; orderCount: string | number };

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
      id: "fuzzwork",
      kind: "aggregate",
      method: "fuzzwork-sell-percentile",
      params: { station: this.station, endpoint: `${this.base}/aggregates/`, side: "sell" },
    };
  }

  async fetchPrices(opts: FetchOptions): Promise<SourceResult> {
    if (!opts.types?.length) throw new Error("fuzzwork needs a type list (--types or --dataset)");
    const types = [...new Set(opts.types)].sort((a, b) => a - b);
    const n = Math.max(1, this.o.batch ?? 200);
    const prices = new Map<number, TypePrice>();
    const unpriced: number[] = [];
    for (let i = 0; i < types.length; i += n) {
      const chunk = types.slice(i, i + n);
      const r = await this.http.get(`${this.base}/aggregates/?station=${this.station}&types=${chunk.join(",")}`, { signal: opts.signal });
      const body = JSON.parse(r.body) as Record<string, { sell?: Side }>;
      for (const t of chunk) {
        const s = body[String(t)]?.sell;
        const orders = Number(s?.orderCount ?? 0);
        if (!s || !(orders > 0) || !(Number(s.min) > 0)) {
          unpriced.push(t);
          continue;
        }
        prices.set(t, { p0: roundIsk(Number(s.min)), price: roundIsk(Number(s.percentile)), units: Math.round(Number(s.volume)), orders });
      }
      opts.log?.(`fuzzwork: ${Math.min(i + n, types.length)}/${types.length} types`);
    }
    return { prices, unpriced, data_as_of: null, rule: null, stats: { ...this.http.stats } };
  }
}
