// ESI market orders: SELL orders of one region, kept only at one location (default The Forge / Jita IV - Moon 4 -
// Caldari Navy Assembly Plant), priced with the shared rule.
//
// GET /markets/{region_id}/orders/?order_type=sell&page=N (X-Pages pages, 1000 orders each). Respects Expires (a
// fresh cached page is not requested again), ETag (If-None-Match -> 304), the error limit (X-ESI-Error-Limit-*), and
// checks that every page has the same Last-Modified (ESI refreshes the book every 5 minutes; a page served from a
// newer/older snapshot is fetched again so the book is consistent).
import { priceAll, type Order } from "../rule.js";
import { HttpClient, type HttpOptions } from "./http.js";
import { isoSecond, type FetchOptions, type OrderSource, type SourceDescriptor, type SourceResult } from "./types.js";

export const THE_FORGE = 10000002;
export const JITA_4_4 = 60003760;

export interface EsiOptions extends HttpOptions {
  region_id?: number;
  location_id?: number;
  /** market id for snapshot ids (default "jita44" for Jita 4-4, else "loc<location_id>") */
  market?: string;
  base_url?: string;
  /** parallel page requests (default 8) */
  concurrency?: number;
  /** with at most this many requested types, query ?type_id= per type instead of the whole region (default 20) */
  per_type_max?: number;
}

interface EsiOrder {
  order_id: number;
  type_id: number;
  location_id: number;
  price: number;
  volume_remain: number;
  is_buy_order: boolean;
}

export class EsiSource implements OrderSource {
  readonly descriptor: SourceDescriptor;
  readonly http: HttpClient;
  private readonly region: number;
  private readonly location: number;
  private readonly base: string;

  constructor(private readonly o: EsiOptions) {
    this.region = o.region_id ?? THE_FORGE;
    this.location = o.location_id ?? JITA_4_4;
    this.base = (o.base_url ?? "https://esi.evetech.net/latest").replace(/\/$/, "");
    this.http = new HttpClient(o);
    this.descriptor = {
      kind: "esi",
      endpoint: `${this.base}/markets/${this.region}/orders/`,
      region_id: this.region,
      location_id: this.location,
      market: o.market ?? (this.location === JITA_4_4 ? "jita44" : `loc${this.location}`),
    };
  }

  private url(page: number, type?: number) {
    return `${this.base}/markets/${this.region}/orders/?datasource=tranquility&order_type=sell&page=${page}${type !== undefined ? `&type_id=${type}` : ""}`;
  }

  /** every page of one listing, consistent on Last-Modified */
  private async listing(type: number | undefined, opts: { log?: (m: string) => void; signal?: AbortSignal }, stats: Record<string, number>) {
    const first = await this.http.get(this.url(1, type), { signal: opts.signal });
    const pages = Math.max(1, Number(first.headers["x-pages"] ?? 1) || 1);
    const res = new Array<Awaited<ReturnType<HttpClient["get"]>>>(pages);
    res[0] = first;
    const conc = Math.max(1, this.o.concurrency ?? 8);
    const fetchPages = async (idx: number[], revalidate: boolean) => {
      let next = 0;
      await Promise.all(
        Array.from({ length: Math.min(conc, idx.length) }, async () => {
          while (next < idx.length) {
            const i = idx[next++];
            res[i] = await this.http.get(this.url(i + 1, type), { revalidate, signal: opts.signal });
          }
        }),
      );
    };
    await fetchPages(Array.from({ length: pages - 1 }, (_, i) => i + 1), false);
    for (let round = 0; ; round++) {
      const lm = res.map((r) => r.last_modified);
      const newest = lm.reduce<string | null>((a, b) => (b && (!a || Date.parse(b) > Date.parse(a)) ? b : a), null);
      const stale = lm.map((v, i) => (v !== newest ? i : -1)).filter((i) => i >= 0);
      if (!stale.length || newest === null) break;
      if (round >= 3) {
        opts.log?.(`ESI pages still disagree on Last-Modified after 3 refetches (${stale.length} of ${pages}); using them as served`);
        stats.inconsistent_pages = (stats.inconsistent_pages ?? 0) + stale.length;
        break;
      }
      opts.log?.(`ESI: ${stale.length} of ${pages} pages older than ${newest}, refetching`);
      await fetchPages(stale, true);
    }
    stats.pages = (stats.pages ?? 0) + pages;
    return res;
  }

  async fetchOrders(opts: Omit<FetchOptions, "rule">) {
    const stats: Record<string, number> = {};
    const types = opts.types ? [...new Set(opts.types)].sort((a, b) => a - b) : null;
    const perType = types !== null && types.length <= (this.o.per_type_max ?? 20);
    const listings = perType ? await Promise.all(types!.map((t) => this.listing(t, opts, stats))) : [await this.listing(undefined, opts, stats)];
    const orders: Order[] = [];
    const want = types ? new Set(types) : null;
    let seen = 0;
    let newest: string | null = null;
    for (const pages of listings)
      for (const p of pages) {
        if (p.last_modified && (!newest || Date.parse(p.last_modified) > Date.parse(newest))) newest = p.last_modified;
        const rows = JSON.parse(p.body) as EsiOrder[];
        if (!Array.isArray(rows)) throw new Error(`ESI: unexpected body ${p.body.slice(0, 200)}`);
        for (const r of rows) {
          seen++;
          if (r.is_buy_order || r.location_id !== this.location) continue;
          if (want && !want.has(r.type_id)) continue;
          orders.push({ type_id: r.type_id, price: r.price, volume_remain: r.volume_remain, location_id: r.location_id, order_id: r.order_id });
        }
      }
    // the same order can show up on two pages when the book moves between requests
    const uniq = new Map<number | string, Order>();
    for (const o of orders) uniq.set(o.order_id ?? `${o.type_id}:${o.price}:${o.volume_remain}:${uniq.size}`, o);
    Object.assign(stats, { orders_seen: seen, orders_at_location: uniq.size }, this.http.stats);
    return { orders: [...uniq.values()], market_time: newest ? isoSecond(Date.parse(newest)) : null, stats };
  }

  async fetchPrices(opts: FetchOptions): Promise<SourceResult> {
    const fetched_from = isoSecond(this.http.clock());
    const { orders, market_time, stats } = await this.fetchOrders(opts);
    const fetched_to = isoSecond(this.http.clock());
    const { prices, missing } = priceAll(orders, opts.rule);
    const miss = new Set(missing);
    if (opts.types) for (const t of opts.types) if (!prices.has(t)) miss.add(t);
    return { prices, missing: [...miss].sort((a, b) => a - b), market_time, fetched_from, fetched_to, exact: true, stats };
  }
}
