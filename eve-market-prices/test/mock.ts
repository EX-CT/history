// A scripted fetch for source tests: responses per URL (or URL predicate), request log, header access.
import type { FetchFn } from "../src/sources/http.js";

export interface MockResponse {
  status?: number;
  body?: unknown;
  headers?: Record<string, string | undefined>;
}

export function mockFetch(handler: (url: URL, headers: Record<string, string>, n: number) => MockResponse) {
  const calls: { url: string; headers: Record<string, string> }[] = [];
  const f: FetchFn = async (url, init) => {
    const headers = init?.headers ?? {};
    calls.push({ url, headers });
    const r = handler(new URL(url), headers, calls.length);
    const h = Object.fromEntries(Object.entries(r.headers ?? {}).filter(([, v]) => v !== undefined).map(([k, v]) => [k.toLowerCase(), v]));
    return {
      status: r.status ?? 200,
      headers: { get: (n: string) => h[n.toLowerCase()] ?? null },
      text: async () => (typeof r.body === "string" ? r.body : JSON.stringify(r.body ?? null)),
    };
  };
  return { fetch: f, calls };
}

export const JITA = 60003760;
export const AMARR = 60008494;
export const order = (order_id: number, type_id: number, price: number, volume_remain: number, location_id = JITA, is_buy_order = false) => ({
  order_id,
  type_id,
  price,
  volume_remain,
  location_id,
  is_buy_order,
  duration: 90,
  issued: "2026-10-01T00:00:00Z",
  min_volume: 1,
  range: "region",
  system_id: 30000142,
  volume_total: volume_remain,
});
