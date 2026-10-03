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
- Daily snapshots are published as GitHub Releases `prices-jita44-<YYYYMMDDTHHMMSSZ>` ([workflow](.github/workflows/snapshot.yml))

## Pricing rule `jita_sell_band_weighted` v1 (docs/22 §3.2)

Per type, over **sell** orders at **Jita IV - Moon 4 - Caldari Navy Assembly Plant** (`location_id` 60003760, region
The Forge 10000002). Buy orders and other stations are ignored.

1. Drop every order with `volume_remain < min_units`. This filters each order by its own unit count, not by a
   percentage of the orders.
2. `p0` = the lowest price among the remaining orders.
3. `band_max` = `p0 × (1 + band)`. The band is every remaining order with `p0 ≤ price ≤ band_max` (both edges inclusive).
4. `price` = Σ(price × volume_remain) / Σ volume_remain over the band, rounded to 0.01 ISK, half to even.
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
# every marketable type of an eve-sde-pipeline dataset (sde_build taken from the dataset); ~8 s, 273 ESI pages
node dist/src/cli.js snapshot --dataset dataset-3569502-r5.json.gz --contact you@example.com --out-dir out
# -> out/prices-jita44-20261003T063356Z.json and .json.gz
node dist/src/cli.js snapshot --types 587,2048 --sde-build 3569502 --min-units 1 --band 0.1 > p.json
node dist/src/cli.js snapshot --source fuzzwork --types 587,2048 --sde-build 3569502 > p-fw.json
node dist/src/cli.js validate out/prices-jita44-20261003T063356Z.json.gz   # schema, invariants, content_hash
node dist/src/cli.js price p.json 587 2048
```

Options: `--source esi|fuzzwork`, `--min-units`, `--band`, `--types` / `--types-file` / `--dataset` (+ `--dataset-name`),
`--sde-build`, `--contact` (or env `EVE_MARKET_PRICES_CONTACT`; it goes into the User-Agent), `--cache-dir` (keeps ETag /
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

## Snapshot format notes

- Files are UTF-8 JSON with keys sorted by code point and a 2-space indent. The `.json.gz` form has mtime 0. Both are byte-identical for the same input.
- `content_hash` = `sha256:` + SHA-256 of the canonical JSON (no whitespace, code-point key order) without `content_hash`. Numbers use the shortest round-trip form (ECMAScript), so `1240000.0` is written `1240000`. See "Gaps" below.
- `coverage` (`dataset`, `dataset_sha256`, `types_requested`) is an optional additive field. docs/22 §4.1 allows additive optional fields within v1.

### Gaps / ambiguities in docs/22 (reported to eve / F)
1. **Number form in the hash (§4.6):** "Python repr / Rust ryu" writes `1240000.0`, but "no trailing zeros" suggests `1240000`. This tool writes `1240000` (ECMAScript). Engines must use the same form, otherwise hashes differ for integral prices.
2. **Key order (§4.6):** "keys sorted" is read as code-point order (`"1000" < "34"`), like Python `sort_keys` and serde `BTreeMap`.
3. **`band_max`** is unrounded `p0 × (1 + band)`. It is computed with 12 significant digits (binary noise trimmed), and orders are compared against that value, so 4.0 × 1.05 = 4.2 includes an order at 4.2.
4. **`sde_build` is required** even for ad-hoc type lists, so the CLI needs `--dataset` or `--sde-build`.
5. **Aggregate sources:** §4.5 invariants (`price ≤ band_max`) force a clamp of Fuzzwork's percentile price; documented in `source.notes`.
6. **`market_time` for sources without `Last-Modified`** (Fuzzwork): the fetch end time is used.
7. The pipeline datasets only contain fitting-relevant types (no minerals, for example), so a `--dataset` snapshot covers those.

## Development

`npm test` runs rule, mocked-source and snapshot tests (no network). `npm run smoke` is a small live ESI + Fuzzwork run;
it is non-gating in CI.

License: MIT. EVE Online and all related names are trademarks of CCP hf.
