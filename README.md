# eve-market-prices

Builds **price snapshots** for EVE Online fitting engines. It takes Jita 4-4 sell orders and prices each type with a
fixed, documented rule. The output is one self-contained, deterministic file per snapshot, in the
**`eve-price-snapshot` v1** format defined in
[EX-CT/eve-fit-docs docs/22 §4](https://github.com/EX-CT/eve-fit-docs/blob/main/docs/22-embedded-sde-and-prices.md).

This tool only produces snapshots. Engines never go online. Each engine release embeds one snapshot, accepts a newer
snapshot injected at run time (`--prices FILE` / RPC), and applies request price overrides itself (docs/22 §3). No
pricing math happens in engines, MCP or web clients: they read `types[id].price`.

- TypeScript library (Node ≥ 20 and browsers, no runtime dependencies) + CLI `eve-market-prices`
- Pluggable sources: **ESI** market orders (exact rule) and **Fuzzwork** aggregates (approximation, `rule.exact: false`); add your own with `registerSource`
- JSON Schema: [`schema/eve-price-snapshot.v1.schema.json`](schema/eve-price-snapshot.v1.schema.json); sample: [`examples/prices-jita44-sample.json`](examples/prices-jita44-sample.json)
- Daily snapshots are published as GitHub Releases `prices-jita44-<YYYYMMDDTHHMMSSZ>` ([workflow](.github/workflows/snapshot.yml)), covering every published marketable type of the latest CCP SDE

## Pricing rule `jita_sell_band_weighted` v1 (docs/22 §3.2)

Per type, over **sell** orders at **Jita IV - Moon 4 - Caldari Navy Assembly Plant** (`location_id` 60003760, region
The Forge 10000002). Buy orders and other stations are ignored.

1. Drop every order with `volume_remain < min_units`. This filters each order by its own unit count, not by a
   percentage of the orders.
2. `p0` = the lowest price among the remaining orders.
3. `band_max` = `p0 × (1 + band)`. The band is every remaining order with `p0 ≤ price ≤ band_max` (both edges inclusive).
4. `price` = Σ(price × volume_remain) / Σ volume_remain over the band, rounded to 0.01 ISK half to even **on the
   mean's 12-significant-digit decimal value** (exact decimal arithmetic: 100.335 → 100.34, 2.675 → 2.68, 4.085 → 4.08),
   then clamped into [p0, band_max]. Orders priced ≤ 0 or non-finite are dropped with the min_units filter.
5. If no order survives step 1, the type has no price and is listed in `missing`.

| parameter | default | CLI | |
|---|---|---|---|
| `min_units` | **10** | `--min-units N` | docs/22 proposal (open point 1); use `--min-units 1` to keep every order |
| `band` | **0.05** | `--band X` | 5 % above p0 |

Each type entry records `price`, `p0`, `band_max`, `units` and `orders` (the band), `units_considered` and
`orders_considered` (after the min_units filter), and `orders_total` (sell orders at the station before filtering).

## CLI

```sh
npm ci && npm run build
# every published marketable type of CCP's SDE (sde_build from the zip); ~10 s, 273 ESI pages
curl -sSLO https://developers.eveonline.com/static-data/tranquility/eve-online-static-data-3569502-jsonl.zip
node dist/src/cli.js snapshot --ccp-sde eve-online-static-data-3569502-jsonl.zip --contact you@example.com --out-dir out
# or only an eve-sde-pipeline dataset's types: --dataset dataset-3569502-r5.json.gz
# -> out/prices-jita44-20261003T063356Z.json and .json.gz
node dist/src/cli.js snapshot --types 587,2048 --sde-build 3569502 --min-units 1 --band 0.1 > p.json
node dist/src/cli.js snapshot --source fuzzwork --types 587,2048 --sde-build 3569502 > p-fw.json
node dist/src/cli.js validate out/prices-jita44-20261003T063356Z.json.gz   # schema, invariants, content_hash
node dist/src/cli.js price p.json 587 2048
# the rule alone on one type's ESI order book (stdin {"rule": {...}, "orders": [...]}) -> §4.5 entry or null
echo '{"rule":{"name":"jita_sell_band_weighted","version":1,"location_id":60003760,"min_units":10,"band":0.05},"orders":[{"type_id":34,"price":5,"volume_remain":100,"location_id":60003760,"is_buy_order":false}]}' | node dist/src/cli.js rule
```

`rule` is the `PRICE_RULE_CMD` of eve3's bench suite `d22/price_rule` (EX-CT/eve-dogma-bench pending-1.11); CI runs
it at a pinned bench commit and requires every case to pass. Buy orders and orders at another `location_id` are
ignored; a rule with another `name` / `version` / `order_side` / `weighting` is an error.

Options: `--source esi|fuzzwork`, `--min-units`, `--band`, `--types` / `--types-file` / `--dataset` (+ `--dataset-name`),
`--ccp-sde`, `--sde-build`, `--contact` (or env `EVE_MARKET_PRICES_CONTACT`; it goes into the User-Agent), `--cache-dir` (keeps ETag /
Expires between runs), `--generated-at`, `--region` / `--location` (ESI), `--station` (Fuzzwork), `--out` / `--out-dir`, `--quiet`.

## Library

```ts
import { parseSnapshot, priceOf, priceOrders, buildSnapshot, EsiSource } from "eve-market-prices";
import { makeSnapshot, writeSnapshotFiles, readSnapshotFile } from "eve-market-prices/node";

const snap = await makeSnapshot({ source: "esi", types: [587, 2048], sde_build: 3569502, contact: "you@example.com" });
writeSnapshotFiles(snap, "out");
const s = parseSnapshot(text);      // throws SnapshotError PRICE_SNAPSHOT_VERSION / PRICE_SNAPSHOT_INVALID (docs/22 §5)
priceOf(s, 587);                    // -> ISK or null
```

`parseSnapshot`, `canonicalJson` and `sha256Hex` are pure and run in the browser. A web client can check an injected
snapshot the same way the engine does.

## Sources

| source | data | rule | notes |
|---|---|---|---|
| `esi` | `GET /markets/10000002/orders/?order_type=sell`: all `X-Pages` pages, or `?type_id=` per type for ≤ 20 types | exact | Keeps only `location_id` 60003760. Honours `Expires` (fresh pages are not requested again) and `ETag` (`If-None-Match` → 304). Pauses when `X-ESI-Error-Limit-Remain` < 20 until the reset. Retries 5xx / 420 / 429 with backoff. Pages with a different `Last-Modified` are fetched again so the book is consistent. `market_time` = newest `Last-Modified`. |
| `fuzzwork` | `market.fuzzwork.co.uk/aggregates/?station=60003760&types=…` | `exact: false` | Fields: `p0` = sell.min, `price` = sell.percentile clamped to [p0, band_max], `units` = sell.volume, `orders` = sell.orderCount. min_units cannot be applied. `market_time` = fetch time. |

To add a source, implement `Source` (`src/sources/types.ts`: `descriptor` + `fetchPrices` → §4.5 entries, `missing`,
`market_time`, fetch window, `exact`) and register it with `registerSource("name", factory)`.

## Type coverage (docs/22, decision 2026-10-03 14:56)

A snapshot prices **every published type with a market group** in CCP's SDE of `sde_build` (fits carry cargo such
as minerals, fuel and ammo stacks), not only the pipeline dataset's fitting-relevant types. `--ccp-sde FILE` takes
CCP's JSONL SDE zip (`https://developers.eveonline.com/static-data/eve-online-static-data-latest-jsonl.zip`, which
redirects to `…-<build>-jsonl.zip`; `sde_build` is read from its `_sde.jsonl`) or a bare `types.jsonl` (then pass
`--sde-build`). The zip is read in-process (no unzip tool needed). `coverage` records the list used:
`{"dataset": "CCP SDE 3569502 (eve-online-static-data-3569502-jsonl.zip)", "dataset_sha256": <sha256 of that file>,
"types_requested": 19566}`. Types without a qualifying Jita sell order are in `missing`. The daily workflow uses the
latest CCP SDE. `--dataset` (an eve-sde-pipeline dataset, a subset) still works.

## Snapshot format notes

- Files are UTF-8 JSON with keys in JCS order (UTF-16 code units; all keys are ASCII, so this is also code-point
  order) and a 2-space indent. The `.json.gz` form has mtime 0. Both are byte-identical for the same input.
- `content_hash` = `sha256:` + SHA-256 of the **RFC 8785 (JCS)** canonical JSON of the snapshot without
  `content_hash` (docs/22 §4.6 as ruled 14:56): no whitespace, keys by UTF-16 code units (`"1000"` before `"34"`),
  ECMAScript number form (`1240000`, not `1240000.0`; `1e+21`), JSON.stringify string escapes; lone surrogates are
  rejected. `src/canonical.ts`; vectors from RFC 8785 and the Python `jcs` package in `test/canonical.test.ts`. The
  published snapshots `prices-jita44-20261003T063856Z` and later and the committed sample hash identically with
  Python `jcs`.
- `coverage` (`dataset`, `dataset_sha256`, `types_requested`) is an optional field (accepted in docs/22 §4.2).

### docs/22 points (status after the 2026-10-03 rulings: eve 14:56, eve3 15:11)
1. Hash: RFC 8785 JCS (decided; implemented, see above). Integers and integral floats hash the same.
2. `band_max` = p0 × (1 + band) rounded to 12 significant digits (decided); order prices are compared to it as
   given, so 4.0 × 1.05 = 4.2 includes an order at 4.2 but an order one ulp above 1050 (p0 1000) is out. Invariants
   use `tol = max(0.005, 1e-9 × band_max)`.
3. `sde_build` required (decided): `--ccp-sde` zip, `--dataset`, or `--sde-build`.
4. Fuzzwork: clamped into [p0, band_max], `market_time` = fetch time, `rule.exact: false` (accepted). Source = `source.kind`.
5. Coverage: all published marketable types from the CCP SDE (decided; `--ccp-sde`).
6. **Rule details — settled (eve3 ruling 2026-10-03 15:11; spec = bench `d22/README.md` "Pricing rule spec" in
   EX-CT/eve-dogma-bench pending-1.11 b638e8a, reference `d22/rule.py`, 41 cases in `d22/cases/price_rule/`):**
   `price` = band mean rounded half-to-even on its 12-significant-digit decimal value
   (`Decimal(f"{mean:.12g}").quantize(Decimal("0.01"), ROUND_HALF_EVEN)`; `roundIsk` in `src/rule.ts` does the same
   with BigInt, test vectors from Python `decimal` in `test/rule.test.ts`), then clamped into [p0, band_max]; orders
   priced ≤ 0 or non-finite are dropped; `band_max` = p0 × (1 + band) at 12 significant digits, order prices compared
   to it as given; an invalid rule makes `eve-market-prices rule` exit non-zero (bench: `RULE_REJECTED`). CI runs all
   41 cases. Since 0.2.1 the rounding is exactly the spec (0.2.0 rounded `trim(v × 100)`, which differed for means with
   more than 10 integer digits, e.g. 55174443703.65 → 55174443703.6 instead of …703.7).
7. Fuzzwork entries are clamped into [p0, band_max]; such a snapshot has `rule.exact: false` and says so in
   `source.notes` (docs/22 has `exact` only on `rule`, not per type).

## Development

`npm test` runs rule, JCS, coverage, mocked-source and snapshot tests (no network). CI also runs the bench `d22/price_rule` suite
through `cli.js rule`. `npm run smoke` is a small live ESI + Fuzzwork run;
it is non-gating in CI.

License: MIT. EVE Online and all related names are trademarks of CCP hf.
