// Sources against a mocked ESI / Fuzzwork: pagination, location + buy filtering, ETag / Expires, error limit,
// Last-Modified consistency, retries, User-Agent.
import assert from "node:assert/strict";
import { test } from "node:test";
import { EsiSource, FuzzworkSource, MemoryCache, createSource, registerSource, SOURCES, userAgent } from "../src/index.js";
import { mockFetch, order, AMARR, JITA } from "./mock.js";

const LM = "Sat, 03 Oct 2026 06:00:00 GMT";
const LM2 = "Sat, 03 Oct 2026 06:05:00 GMT";
const UA = userAgent("0.0.0-test", "tests@example.invalid");
const rule = { min_units: 1, band: 0.05 };
const noSleep = async () => {};

// two pages; Jita sells, an Amarr sell (other location in the region), a buy order (ESI filtered order_type, but be safe)
const PAGES: Record<number, unknown[]> = {
  1: [order(1, 34, 4.0, 1000), order(2, 34, 4.1, 3000), order(3, 34, 3.0, 50, AMARR), order(4, 587, 250000, 2)],
  2: [order(5, 34, 9.0, 10), order(6, 587, 255000, 3), order(7, 587, 1, 1, JITA, true), order(4, 587, 250000, 2)],
};

function esiMock(opts: { lm?: (page: number, n: number) => string; status?: (page: number, n: number) => number | undefined; extra?: Record<string, string> } = {}) {
  return mockFetch((u, h, n) => {
    assert.equal(u.pathname, "/latest/markets/10000002/orders/");
    assert.equal(u.searchParams.get("order_type"), "sell");
    assert.equal(h["User-Agent"], UA);
    const page = Number(u.searchParams.get("page"));
    const st = opts.status?.(page, n);
    if (st) return { status: st, body: { error: "x" }, headers: { "X-ESI-Error-Limit-Remain": "99", "X-ESI-Error-Limit-Reset": "1" } };
    return {
      body: PAGES[page],
      headers: { "X-Pages": "2", "Last-Modified": opts.lm?.(page, n) ?? LM, Expires: "Sat, 03 Oct 2026 06:05:00 GMT", ETag: `"p${page}"`, "X-ESI-Error-Limit-Remain": "100", ...(opts.extra ?? {}) },
    };
  });
}

test("esi: paginates, keeps Jita 4-4 sells only, de-duplicates orders seen on two pages, prices with the rule", async () => {
  const m = esiMock();
  const s = new EsiSource({ userAgent: UA, fetch: m.fetch, sleep: noSleep });
  const r = await s.fetchPrices({ rule });
  assert.equal(m.calls.length, 2);
  // 34: 9.0 is outside the band, Amarr's 3.0 is not at Jita 4-4; 587: 255000 <= 250000 * 1.05, buy order ignored
  assert.deepEqual(Object.fromEntries(r.prices), {
    34: { p0: 4, price: 4.08, units: 4000, orders: 2 },
    587: { p0: 250000, price: 253000, units: 5, orders: 2 },
  });
  assert.equal(r.data_as_of, "2026-10-03T06:00:00Z");
  assert.equal(r.stats.pages, 2);
  assert.equal(r.stats.orders_seen, 8);
  assert.equal(r.stats.orders_at_location, 5);
  assert.deepEqual(r.unpriced, []);
  assert.deepEqual(s.descriptor.params.location_id, JITA);
});

test("esi: min_units drops small orders; a type left without orders is unpriced", async () => {
  const s = new EsiSource({ userAgent: UA, fetch: esiMock().fetch, sleep: noSleep });
  const r = await s.fetchPrices({ rule: { min_units: 5, band: 0.05 } });
  assert.deepEqual([...r.prices.keys()], [34]);
  assert.deepEqual(r.unpriced, [587]);
  assert.equal(r.prices.get(34)!.units, 4000 + 0); // 9.0 x10 is >= 5 units but outside the band
});

test("esi: Expires serves fresh pages from cache; afterwards ETag revalidates with 304", async () => {
  let now = Date.parse("Sat, 03 Oct 2026 06:01:00 GMT");
  const cache = new MemoryCache();
  const m1 = esiMock();
  await new EsiSource({ userAgent: UA, fetch: m1.fetch, cache, now: () => now, sleep: noSleep }).fetchPrices({ rule });
  const m2 = esiMock();
  const s2 = new EsiSource({ userAgent: UA, fetch: m2.fetch, cache, now: () => now, sleep: noSleep });
  const r2 = await s2.fetchPrices({ rule });
  assert.equal(m2.calls.length, 0, "not expired: no request");
  assert.equal(s2.http.stats.cache_fresh, 2);
  assert.equal(r2.prices.get(34)!.price, 4.08);
  now = Date.parse("Sat, 03 Oct 2026 06:06:00 GMT");
  const m3 = mockFetch((u, h) => {
    assert.equal(h["If-None-Match"], `"p${u.searchParams.get("page")}"`);
    return { status: 304, headers: { Expires: "Sat, 03 Oct 2026 06:10:00 GMT", "X-ESI-Error-Limit-Remain": "100" } };
  });
  const s3 = new EsiSource({ userAgent: UA, fetch: m3.fetch, cache, now: () => now, sleep: noSleep });
  const r3 = await s3.fetchPrices({ rule });
  assert.equal(m3.calls.length, 2);
  assert.equal(s3.http.stats.cache_revalidated, 2);
  assert.deepEqual(r3.prices, r2.prices);
});

test("esi: pages from different book versions are refetched until Last-Modified agrees", async () => {
  // page 2 is first served from the older book
  const m = esiMock({ lm: (page, n) => (page === 2 && n === 2 ? "Sat, 03 Oct 2026 05:55:00 GMT" : LM) });
  const s = new EsiSource({ userAgent: UA, fetch: m.fetch, sleep: noSleep });
  const r = await s.fetchPrices({ rule });
  assert.equal(m.calls.length, 3);
  assert.equal(r.data_as_of, "2026-10-03T06:00:00Z");
  assert.equal(r.stats.inconsistent_pages, undefined);
});

test("esi: low error limit pauses until the reset; 5xx and 420 are retried with backoff", async () => {
  const sleeps: number[] = [];
  let t = 0;
  const m = mockFetch((u, _h, n) => {
    if (n === 1) return { status: 502, headers: { "X-ESI-Error-Limit-Remain": "5", "X-ESI-Error-Limit-Reset": "7" } };
    if (n === 2) return { status: 420, headers: { "X-ESI-Error-Limit-Remain": "0", "X-ESI-Error-Limit-Reset": "3" } };
    return { body: PAGES[Number(u.searchParams.get("page"))], headers: { "X-Pages": "2", "Last-Modified": LM, "X-ESI-Error-Limit-Remain": "100" } };
  });
  const s = new EsiSource({ userAgent: UA, fetch: m.fetch, now: () => t, sleep: async (ms) => { sleeps.push(ms); t += ms; } });
  const r = await s.fetchPrices({ rule });
  assert.equal(r.prices.size, 2);
  assert.equal(s.http.stats.retries, 2);
  assert.ok(s.http.stats.error_limit_waits >= 1, JSON.stringify(s.http.stats));
  assert.ok(sleeps.some((ms) => ms >= 7000), `waited for the error-limit reset: ${sleeps}`);
});

test("esi: non-retryable errors fail with the URL and status; a User-Agent is mandatory", async () => {
  const m = mockFetch(() => ({ status: 404, body: { error: "not found" } }));
  await assert.rejects(new EsiSource({ userAgent: UA, fetch: m.fetch, sleep: noSleep }).fetchPrices({ rule }), /HTTP 404/);
  assert.throws(() => new EsiSource({ userAgent: " " }), /User-Agent/);
  assert.match(UA, /^eve-market-prices\/0\.0\.0-test \(tests@example\.invalid; \+https:\/\/github\.com\/EX-CT\/eve-market-prices\)$/);
});

test("esi: a short type list is queried per type (?type_id=), other types are ignored", async () => {
  const m = mockFetch((u) => {
    const t = Number(u.searchParams.get("type_id"));
    assert.ok(t === 587 || t === 999);
    return { body: t === 587 ? [order(6, 587, 255000, 3), order(8, 34, 1, 1)] : [], headers: { "X-Pages": "1", "Last-Modified": LM2 } };
  });
  const r = await new EsiSource({ userAgent: UA, fetch: m.fetch, sleep: noSleep }).fetchPrices({ rule, types: [587, 999] });
  assert.equal(m.calls.length, 2);
  assert.deepEqual([...r.prices.keys()], [587]);
  assert.deepEqual(r.unpriced, [999]);
  assert.equal(r.data_as_of, "2026-10-03T06:05:00Z");
});

test("fuzzwork: aggregates map onto p0 / price / units / orders; empty types unpriced; batches", async () => {
  const m = mockFetch((u) => {
    assert.equal(u.pathname, "/aggregates/");
    assert.equal(u.searchParams.get("station"), String(JITA));
    const ids = u.searchParams.get("types")!.split(",");
    assert.ok(ids.length <= 2);
    const side = (min: string, pct: string, vol: string, n: string) => ({ weightedAverage: "0", max: "0", min, stddev: "0", median: "0", volume: vol, orderCount: n, percentile: pct });
    const all: Record<string, unknown> = {
      "34": { buy: side("1", "1", "1", "1"), sell: side("3.91", "3.9100000000000006", "7605818556.0", "26") },
      "587": { buy: side("1", "1", "1", "1"), sell: side("249800.0", "249800.0", "2603.0", "50") },
      "999": { buy: side("0", "0", "0", "0"), sell: { weightedAverage: 0, max: 0, min: 0, stddev: 0, median: 0, volume: 0, orderCount: 0, percentile: 0 } },
    };
    return { body: Object.fromEntries(ids.map((i) => [i, all[i]])) };
  });
  const s = new FuzzworkSource({ userAgent: UA, fetch: m.fetch, batch: 2, sleep: noSleep });
  const r = await s.fetchPrices({ rule, types: [999, 34, 587] });
  assert.equal(m.calls.length, 2);
  assert.deepEqual(Object.fromEntries(r.prices), { 34: { p0: 3.91, price: 3.91, units: 7605818556, orders: 26 }, 587: { p0: 249800, price: 249800, units: 2603, orders: 50 } });
  assert.deepEqual(r.unpriced, [999]);
  assert.equal(r.rule, null);
  await assert.rejects(s.fetchPrices({ rule }), /type list/);
});

test("sources: registry is pluggable", async () => {
  assert.deepEqual(Object.keys(SOURCES).sort(), ["esi", "fuzzwork"]);
  registerSource("fixed", () => ({
    descriptor: { id: "fixed", kind: "aggregate", method: "fixed", params: {} },
    fetchPrices: async () => ({ prices: new Map([[34, { p0: 1, price: 1, units: 1, orders: 1 }]]), unpriced: [], data_as_of: null, rule: null, stats: {} }),
  }));
  const r = await createSource("fixed", { userAgent: UA }).fetchPrices({ rule });
  assert.equal(r.prices.get(34)!.price, 1);
  assert.throws(() => createSource("nope", { userAgent: UA }), /unknown source 'nope'/);
  assert.throws(() => registerSource("esi", () => null as never), /already registered/);
});
