// Snapshot format (docs/22 §4): build, canonical bytes, content_hash vectors, JSON Schema, engine-side checks,
// file naming, gzip determinism, makeSnapshot with a mocked source.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { Ajv2020 } from "ajv/dist/2020.js";
import { buildSnapshot, canonicalJson, contentHash, parseSnapshot, priceOf, serializeSnapshot, sha256Hex, snapshotFileName, stableStringify, SnapshotError, priceAll, type Snapshot, type SourceResult } from "../src/index.js";
import { makeSnapshot, readSnapshotFile, writeSnapshotFiles } from "../src/node.js";
import { mockFetch, order } from "./mock.js";

const schema = JSON.parse(readFileSync(new URL("../../schema/eve-price-snapshot.v1.schema.json", import.meta.url), "utf8"));
const validate = new Ajv2020({ allErrors: true, strict: false }).compile(schema);
const rule = { min_units: 10, band: 0.05 };
const desc = { kind: "esi", endpoint: "https://esi.evetech.net/latest/markets/10000002/orders/", region_id: 10000002, location_id: 60003760, market: "jita44" };

function result(): SourceResult {
  const { prices, missing } = priceAll(
    [
      { type_id: 2889, price: 1240000, volume_remain: 100 },
      { type_id: 2889, price: 1250000, volume_remain: 300 },
      { type_id: 2889, price: 1240000, volume_remain: 5 },
      { type_id: 34, price: 3.91, volume_remain: 1000000 },
      { type_id: 34, price: 4, volume_remain: 3000000 },
      { type_id: 1000, price: 9.99, volume_remain: 3 },
    ],
    rule,
  );
  return { prices, missing: [...missing, 587], market_time: "2026-10-03T06:00:00Z", fetched_from: "2026-10-03T05:58:40Z", fetched_to: "2026-10-03T06:00:00Z", exact: true, stats: {} };
}
const snap = () => buildSnapshot({ result: result(), source: desc, rule, sde_build: 3569502, generated_at: "2026-10-03T06:04:12.345Z", updater: { name: "eve-market-prices", version: "0.1.0" } });

test("sha256: NIST vectors and node:crypto agree", () => {
  assert.equal(sha256Hex(""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
  assert.equal(sha256Hex("abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
  assert.equal(sha256Hex("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"), "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1");
  for (const n of [55, 56, 63, 64, 65, 1000, 100000]) {
    const s = "é€".repeat(n);
    assert.equal(sha256Hex(s), createHash("sha256").update(s, "utf8").digest("hex"), `len ${n}`);
  }
});

test("canonical JSON: code-point key order (\"1000\" < \"34\"), no whitespace, shortest numbers", () => {
  assert.equal(canonicalJson({ b: 1, a: [1.5, 2, null], "34": 0.1, "1000": 1240000.0, A: true }), '{"1000":1240000,"34":0.1,"A":true,"a":[1.5,2,null],"b":1}');
  assert.equal(stableStringify({ b: {}, a: [] }), '{\n  "a": [],\n  "b": {}\n}\n');
  assert.throws(() => canonicalJson({ x: Number.NaN }), /non-finite/);
});

test("content_hash test vector (docs/22 §4.6)", () => {
  // body = §4.7 example values; hash over canonicalJson(body without content_hash)
  const body = {
    schema: "eve-price-snapshot", schema_version: 1, snapshot_id: "jita44-20261003T060000Z", market: "jita44",
    market_time: "2026-10-03T06:00:00Z", generated_at: "2026-10-03T06:04:12Z",
    source: { kind: "esi", endpoint: "https://esi.evetech.net/latest/markets/10000002/orders/", region_id: 10000002, location_id: 60003760, fetched_from: "2026-10-03T05:58:40Z", fetched_to: "2026-10-03T06:00:00Z" },
    rule: { name: "jita_sell_band_weighted", version: 1, order_side: "sell", location_id: 60003760, min_units: 10, band: 0.05, weighting: "units", exact: true },
    currency: "ISK", sde_build: 3569502, type_count: 1,
    types: { "2889": { price: 1251234.56, p0: 1240000.0, band_max: 1302000.0, units: 412, orders: 9, units_considered: 2310, orders_considered: 31, orders_total: 37 } },
    missing: [], updater: { name: "eve-prices", version: "0.1.0" },
  };
  const canon = canonicalJson(body);
  assert.ok(canon.startsWith('{"currency":"ISK","generated_at":"2026-10-03T06:04:12Z","market":"jita44",'), canon);
  assert.ok(canon.includes('"p0":1240000,'), "integral doubles without .0");
  assert.equal(contentHash(body as never), `sha256:${createHash("sha256").update(canon).digest("hex")}`);
  assert.equal(contentHash(body as never), "sha256:" + sha256Hex(canon));
});

test("buildSnapshot: docs/22 fields, sorted types, missing, valid against the JSON Schema and engine checks", () => {
  const s = snap();
  assert.equal(s.snapshot_id, "jita44-20261003T060000Z");
  assert.equal(snapshotFileName(s), "prices-jita44-20261003T060000Z.json");
  assert.equal(s.generated_at, "2026-10-03T06:04:12Z");
  assert.deepEqual(Object.keys(s.types), ["34", "2889"]);
  assert.equal(s.type_count, 2);
  assert.deepEqual(s.missing, [587, 1000]);
  assert.deepEqual(s.types["2889"], { price: 1247500, p0: 1240000, band_max: 1302000, units: 400, orders: 2, units_considered: 400, orders_considered: 2, orders_total: 3 });
  assert.deepEqual(s.rule, { name: "jita_sell_band_weighted", version: 1, order_side: "sell", location_id: 60003760, min_units: 10, band: 0.05, weighting: "units", exact: true });
  assert.ok(validate(s), JSON.stringify(validate.errors));
  assert.deepEqual(parseSnapshot(serializeSnapshot(s)), s);
  assert.equal(priceOf(s, 34), 3.98);
  assert.equal(priceOf(s, 587), null);
  assert.throws(() => buildSnapshot({ result: result(), source: desc, rule, sde_build: 0, generated_at: 0, updater: { name: "x", version: "1" } }), /sde_build/);
});

test("determinism: same input -> byte-identical file regardless of order delivery; file is canonical", () => {
  const a = serializeSnapshot(snap());
  const r = result();
  r.prices = new Map([...r.prices].reverse());
  r.missing.reverse();
  const b = serializeSnapshot(buildSnapshot({ result: r, source: desc, rule, sde_build: 3569502, generated_at: "2026-10-03T06:04:12Z", updater: { name: "eve-market-prices", version: "0.1.0" } }));
  assert.equal(a, b);
  assert.equal(serializeSnapshot(JSON.parse(a)), a);
  assert.ok(a.indexOf('"34"') < a.indexOf('"2889"') === false, "code-point order: 2889 before 34");
});

test("parseSnapshot: engine error codes for version, hash and §4.5 invariants", () => {
  const s = snap();
  const mut = (f: (x: Snapshot) => void, fixHash = true) => {
    const x = JSON.parse(JSON.stringify(s)) as Snapshot;
    f(x);
    if (fixHash) x.content_hash = contentHash(x);
    return x;
  };
  const code = (x: unknown) => {
    try {
      parseSnapshot(x);
      return "ok";
    } catch (e) {
      return e instanceof SnapshotError ? e.code : String(e);
    }
  };
  assert.equal(code(mut(() => {})), "ok");
  assert.equal(code(mut((x) => (x.schema_version = 2))), "PRICE_SNAPSHOT_VERSION");
  assert.equal(code(mut((x) => ((x as { schema: string }).schema = "eve-market-prices/snapshot"))), "PRICE_SNAPSHOT_VERSION");
  assert.equal(code(mut((x) => (x.types["34"].price = 3.99), false)), "PRICE_SNAPSHOT_INVALID"); // hash
  assert.equal(code(mut((x) => (x.types["34"].price = 3.9))), "PRICE_SNAPSHOT_INVALID"); // below p0
  assert.equal(code(mut((x) => (x.types["34"].price = 4.2))), "PRICE_SNAPSHOT_INVALID"); // above band_max
  assert.equal(code(mut((x) => (x.types["34"].units = x.types["34"].units_considered + 1))), "PRICE_SNAPSHOT_INVALID");
  assert.equal(code(mut((x) => (x.types["34"].orders_considered = x.types["34"].orders_total + 1))), "PRICE_SNAPSHOT_INVALID");
  assert.equal(code(mut((x) => (x.type_count = 3))), "PRICE_SNAPSHOT_INVALID");
  assert.equal(code(mut((x) => (x.market_time = "2026-10-03T06:00:00.000Z"))), "PRICE_SNAPSHOT_INVALID");
});

test("makeSnapshot + files: mocked ESI end to end; .json and .json.gz deterministic; requested types only", async () => {
  const LM = "Sat, 03 Oct 2026 06:00:00 GMT";
  const m = mockFetch((u) => ({
    body: Number(u.searchParams.get("type_id")) === 34 ? [order(1, 34, 3.91, 1000000), order(2, 34, 4, 3000000), order(3, 34, 3.5, 5)] : [],
    headers: { "X-Pages": "1", "Last-Modified": LM, "X-ESI-Error-Limit-Remain": "100" },
  }));
  let t = Date.parse("2026-10-03T06:01:00Z");
  const opts = { source: "esi", types: [34, 35], sde_build: 3569502, fetch: m.fetch, now: () => (t += 1000), sleep: async () => {}, contact: "tests@example.invalid" };
  const s = await makeSnapshot(opts);
  assert.equal(m.calls[0].headers["User-Agent"], "eve-market-prices/0.1.0 (tests@example.invalid; +https://github.com/EX-CT/eve-market-prices)");
  assert.deepEqual(Object.keys(s.types), ["34"]);
  assert.deepEqual(s.missing, [35]);
  assert.equal(s.types["34"].orders_total, 3);
  assert.equal(s.rule.min_units, 10);
  assert.deepEqual(s.coverage, { dataset: null, dataset_sha256: null, types_requested: 2 });
  assert.ok(validate(s), JSON.stringify(validate.errors));
  const d1 = mkdtempSync(join(tmpdir(), "emp-"));
  const d2 = mkdtempSync(join(tmpdir(), "emp-"));
  const w1 = writeSnapshotFiles(s, d1);
  const w2 = writeSnapshotFiles(parseSnapshot(serializeSnapshot(s)), d2);
  assert.ok(w1.json.endsWith("prices-jita44-20261003T060000Z.json"));
  assert.deepEqual(readFileSync(w1.gz), readFileSync(w2.gz));
  assert.deepEqual(readSnapshotFile(w1.gz), s);
  await assert.rejects(makeSnapshot({ ...opts, sde_build: null }), /sde_build is required/);
});
