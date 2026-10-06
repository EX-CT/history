# 23 — Batch API and prices (contract draft)

**中文摘要**：
- 引擎批量计算接口 `batch`：一次请求计算多套装配。三种形式：多套独立装配；基础装配 + 变体（JSON Patch）；笛卡尔积 / 参数扫描（有组合数上限，超出报 `BATCH_TOO_LARGE`）。
- 输出可选字段（`fields`）、相对基准的差值（绝对值和百分比）、排序（`sort_by`）、过滤（`filter`）、前 N 个（`top_n`）。每个变体有 `id` 和 `label`。单个装配出错只影响该条结果。结果确定：同样的请求和数据，输出字节相同，且等于逐个 `calc` 的结果。
- 入口：Rust 库 `eve_dogma::batch`、RPC 方法 `batch`（`eve-fit serve-stdio` 和 eve-wasm 的 `rpc` 导出）、CLI `eve-fit batch`。
- 价格是引擎核心：请求字段 `price_overrides`（按 type / 市场分组（含子分组）/ 分组 / 类别，固定价（可为 0）或倍数）、注入价格 `prices` / `--prices`、内嵌快照。优先级：变体覆盖 > 请求覆盖 > 注入价格 > 快照；同一层内越具体越优先，平局取较小 id；倍数作用于下一层解析出的价格。
- 输出 `price` 块：总价，按舰船 / 装备 / 弹药 / 无人机 / 铁骑 / 植入体 / 增效剂 / 货柜分段，细到每个物品，每个价格带来源和快照时间，无价物品单独列出。批量结果可按价格排序和过滤。

**Status: IMPLEMENTED in eve-dogma (see HANDOFF), contract v1, 2026-10-03 (CST).** Rulings by eve 14:26 / 14:36 and F's contract decisions (§11) are folded in. Decisions from the user / eve (14:14–14:26). Implemented in
`EX-CT/eve-dogma` (engine) right after this doc; eve4 wires MCP `compute_batch` as a pass-through; eve3's
`batch-suite` (bench pending-1.11 `batch/`, provisional shape `CONTRACT-BATCH.md`) maps onto this contract in its
`adapter.py` only. The shape below deliberately keeps eve3's provisional semantics (JSON Patch, `fields` projection,
6-decimal deltas, `on: "delta"` filters, stable multi-key sort); names that differ are accepted as aliases.

## 1. Entry points

| surface | how |
|---|---|
| Rust library | `eve_dogma::batch::run(&BatchRequest) -> BatchResponse` and `eve_dogma::batch_json(&str) -> String`; prices in `eve_dogma::price` (`resolve`, `PriceBlock`) |
| RPC method | **`batch`**, `params` = BatchRequest, `result` = BatchResponse (alias `calc_batch`) |
| `eve-fit serve-stdio` | serves `batch` like every other RPC method (JSONL `{"id","method":"batch","params":{…}}`) |
| eve-wasm | the C-ABI `rpc` export serves `batch` (same JSON in / out); wasm32-wasip1 CLI identical to native |
| CLI | `eve-fit batch --request FILE` (or `-` for stdin): one BatchRequest JSON → one BatchResponse JSON. Plain `eve-fit batch` keeps its JSONL stream mode (one FitRequest per line → one FitStats per line); a stream line that is a BatchRequest object (has `"batch_version"`) is answered with one BatchResponse line |
| global CLI option | `--prices FILE` (all commands): injected prices for the process (§5.3) |
| MCP | `compute_batch` (eve4) passes BatchRequest / BatchResponse through unchanged; no pricing logic in MCP |

`calc` also accepts the price inputs (§5) and emits the `price` block (§6).

## 2. BatchRequest

```jsonc
{
  "batch_version": 1,
  // exactly ONE fit source:
  "fits":     [ { "id": "a", "label": "Rifter AC", "fit": FitRequest, "price_overrides": [...] } ],   // form 1
  "base":     FitRequest,                                                                              // forms 2, 3
  "variants": [ { "id": "v1", "label": "T2 guns", "patch": [JSONPatchOp], "price_overrides": [...] } ], // form 2
  "product":  { "axes": [ Axis, ... ] },                                                               // form 3
  "sweep":    Sweep,                                                                                   // form 3 (1-D)

  "max_combinations": 2000,       // cap for expansion (default 2000, hard ceiling 100000)
  "price_overrides": [ ... ],     // batch-wide request overrides (§5)
  "prices": { ... },              // injected prices for the whole batch (§5.3)
  "price": true,                  // force the price block on every result (default: auto, §6.1)

  "fields":  ["offense.total.dps.total", "defense.ehp.total", "price.total_isk"],
  "deltas":  true,                // needs base (forms 2/3) or "delta_ref" (form 1)
  "delta_ref": "a",               // form 1 only: id of the reference fit
  "filter":  [ { "field": "price.total_isk", "op": "<=", "value": 50000000 } ],
  "sort_by": [ { "field": "offense.total.dps.total", "order": "desc" } ],
  "top_n":   10,
  "include_errors": true          // keep errored results in "results" (default true; they never pass a filter)
}
```

### 2.1 Form 1 — many fits
`fits` is a list of independent FitRequests. Each entry: `fit` (required), `id` (string, default = its index as a
string), `label` (string, default = `id`), `price_overrides` (optional, §5).

### 2.2 Form 2 — base fit + variants
`base` is a FitRequest. Each variant = `base` with its `patch` applied; `id` default `"v<k>"`, `label` default = `id`.
The base itself is computed once and returned in `base` (not in `results`) when `deltas` is on or `include_base: true`.

**Patch** = RFC 6902 JSON Patch on the FitRequest JSON, ops `add`, `remove`, `replace` (paths are JSON Pointers,
`/modules/-` appends). This covers every variant kind: modules, charges, states, skills, implants, boosters, fleet
buffs / booster fits, projected fits, target profile, environment, options. Examples:
`{"op":"replace","path":"/modules/0/type_id","value":2873}`, `{"op":"replace","path":"/modules/2/state","value":"overheated"}`,
`{"op":"add","path":"/character/skills/levels/3300","value":4}`, `{"op":"add","path":"/implants/-","value":13203}`,
`{"op":"remove","path":"/drones/0"}`. Convenience op (engine extension): `{"op":"swap_type","from":484,"to":2873}`
replaces `type_id` of every module whose `type_id` is `from` (keeps state / charge).

### 2.3 Form 3 — cartesian product and sweeps
```jsonc
"product": { "axes": [
  { "name": "guns", "options": [ { "id": "t1", "label": "T1", "patch": [...] }, { "id": "t2", "label": "T2", "patch": [...] } ] },
  { "name": "ammo", "sweep": { "path": "/modules/0/charge_type_id", "values": [12608, 12614, 12625] } },
  { "name": "skill", "sweep": { "path": "/character/skills/default_level", "from": 0, "to": 5, "step": 1 } }
]}
"sweep": { "path": "/target_profile/signature_radius", "from": 40, "to": 400, "step": 40 }   // = product with one sweep axis
```
- An axis is either `options` (each a patch with `id`/`label`, optional `price_overrides`) or `sweep`.
- A sweep is `{path, values:[...]}` or numeric `{path, from, to, step}` (`step` > 0; values `from + k·step` for
  k = 0.. while value ≤ `to` + 1e-9·|step|, computed by multiplication, never by accumulation; integers stay integers
  when from/to/step are all integers). Each value becomes `{"op":"add","path":path,"value":v}`. Sweep option id/label:
  `path=<json value>`, where `<json value>` is **compact JSON with object keys sorted** (no spaces; Python:
  `json.dumps(v, separators=(",", ":"), sort_keys=True)`), e.g. `/damage_pattern={"em":10,"explosive":0,"kinetic":45,"thermal":45}`.
- Patch paths that do not exist in the base as given are retried on the **normalized** base (the FitRequest with all
  defaults present, e.g. `/character/skills/levels/3300`, `/character/skills/default_level`); stats are the same.
- Patches of one combination are applied in axis order. The first axis varies slowest. Combination `id` = option ids
  joined with `|` (e.g. `t2|12614|3`), `label` = option labels joined with ` × `.
- Option-level `price_overrides` of all axes are concatenated in axis order (later axes do not override earlier ones;
  they are one layer, §5.2).
- **Combination cap.** Before computing anything, the engine counts the expansion (product of axis sizes; forms 1/2:
  number of entries). If it exceeds `max_combinations` (default 2000) or the hard ceiling 100000, the whole request
  fails with `BATCH_TOO_LARGE` `{"count": N, "limit": L}`; nothing is computed.

## 3. Determinism
- Same request + same engine build + same data (SDE pack, price inputs) → byte-identical BatchResponse.
- Every result's `stats` is byte-identical to `calc` of the same expanded FitRequest run on its own (eve3's gate).
- Expansion order is fixed (§2); `index` = position in the expansion (0-based). Thread count never changes output.
- Sort is stable: ties keep expansion order. Deltas use the emitted values (§4.2). No randomness anywhere.

## 4. Output selection

### 4.1 `fields`
Paths into the result object `{stats…, price}`: dotted (`offense.total.dps.total`, numeric segments index lists:
`modules.0.cpu`) or JSON Pointer (`/defense/ehp/total`). With `fields`, a result's `stats` becomes `{field: value}`
(`null` for a missing path, plus one warning per missing field). Without `fields`, `stats` is the full FitStats.
`price.*` paths read the result's price block (§6).

### 4.2 Deltas
`deltas: true` adds `delta` and `delta_pct` to each result for every selected numeric field:
`delta = round6(value) − round6(ref)`, rounded to 6 decimals; `delta_pct = delta / |ref| × 100` rounded to 6 decimals,
`null` when ref is 0. Non-numeric or missing on either side → `null`. Reference: `base` (forms 2/3) or the fit with
`id == delta_ref` (form 1; error `BATCH_BAD_REQUEST` if absent). Requires `fields`.

### 4.3 `filter`, `sort_by`, `top_n`
- `filter`: list of `{field, op, value, on?}`, all must hold (AND). `op`: `<` `<=` `>` `>=` `==` `!=` `in` (value is a
  list) `not_null`. `on`: `value` (default), `delta` or `delta_pct`. A result with an error, or a `null` /
  non-numeric value for a numeric comparison, fails. Booleans compare as 0/1.
- `sort_by` (alias `sort`): list of `{field, order: "asc"|"desc", on?}`, multi-key, stable; `null`, non-numeric and
  errored results go last regardless of order.
- `top_n` (alias `limit`): applied after filter and sort.
- Order of operations: expand → compute all → filter → sort → top_n. `total` counts the expansion; `matched` counts
  results after filter.

## 5. Prices: inputs and precedence

### 5.1 `price_overrides`
A list on the FitRequest (same level as `ship`, `modules`, `character`), on the BatchRequest (batch-wide), and on each
batch fit / variant / axis option:
```jsonc
"price_overrides": [
  { "type_id": 2873, "price": 0 },                    // self-built: free
  { "market_group_id": 9, "multiplier": 0.9 },        // Ship Equipment and all child market groups: 90 %
  { "group_id": 55, "price": 250000 },                // every type of group 55
  { "category_id": 8, "multiplier": 1.1 }             // all charges +10 %
]
```
Each entry has exactly one target (`type_id` | `market_group_id` | `group_id` | `category_id`) and exactly one of
`price` (ISK per unit, finite, ≥ 0; 0 allowed) or `multiplier` (finite, ≥ 0). A `market_group_id` matches every type
whose market group is that group or any descendant. Two entries with the same target in one layer, or a malformed
entry, fail the request (`BAD_PRICE_OVERRIDE`; in a batch the whole batch fails, since it is input validation).

### 5.2 Layers and resolution (deterministic)
Layers, highest first:
1. **L1 variant overrides**: a batch fit's / variant's `price_overrides`, plus its axis options' (form 3).
2. **L2 request overrides**: the BatchRequest's `price_overrides` and the base / fit FitRequest's own `price_overrides`
   (a FitRequest computed alone with `calc` has only this layer).
3. **L3 injected prices**: the request's `prices.isk` table (FitRequest or BatchRequest; a FitRequest's own table
   wins per type over the batch-wide one).
4. **L4 market snapshot**: the `--prices FILE` snapshot / RPC `prices_load` session snapshot if given (it replaces the
   embedded one completely, docs/22 §3.3; its lines are labelled `injected`), else the embedded Jita snapshot
   (docs/22; labelled `snapshot`). Not in the first implementation: no embedded snapshot yet, so without `--prices`
   L4 is empty and an otherwise unpriced item is *missing*.

Within an override layer (L1, L2) the one entry that applies to a type is the **most specific**:
`type_id` > `market_group_id` (deepest matching group first) > `group_id` > `category_id`. A tie between two entries of
the same kind and specificity (possible only when L2 combines the batch-wide list with the fit's own list) goes to the
**lower id**, then to the entry listed first.

Ties: entries of the same kind and specificity can only collide when the same target appears in both L2 lists; the
FitRequest's own list is listed first, so its entry wins (a duplicate target inside one list is `BAD_PRICE_OVERRIDE`).

Resolving type T from layer k:
- no entry for T in layer k → resolve from layer k+1;
- the entry has `price` → that is the price (lower layers are not consulted);
- the entry has `multiplier` m → resolve T from layer k+1; if that gives price p, the price is m·p; if it gives
  nothing, T is missing (reason `multiplier_without_base`).
- L3 / L4 give a price or nothing.
So multipliers stack across layers (an L1 ×0.9 over an L2 ×0.5 over an injected 100 gives 45), and a fixed price stops
the chain.

**Line attribution (eve ruling 14:36):**
- `source` / `layer` = the highest layer that had an entry for the type (the top override; `injected` / `snapshot`
  when no override applied).
- `multiplier` = the product of all multipliers in the chain; omitted when no multiplier applied.
- `base_source` = what finally supplied the base price: `injected`, `snapshot`, or the fixed-price override's source
  (`override:type` …). Without a multiplier, `base_source` = `source`.

### 5.3 Injected prices (`prices`, `--prices`)
`prices` on the FitRequest / BatchRequest:
```jsonc
"prices": { "isk": { "587": 350000.0, "2873": 1250000.0 }, "use_snapshot": true }
```
- `isk`: type id (string key) → ISK per unit, finite, ≥ 0 (layer L3).
- `use_snapshot` (default true): `false` disables L4 for this request (the request table is the only market source).
- `--prices FILE`: an `eve-price-snapshot` v1 file (docs/22 §4) or a plain `{"<type_id>": isk}` map, validated on load
  (`PRICE_SNAPSHOT_INVALID` / `BAD_PRICES`); RPC sessions: `{"method":"prices_load","params":{"path"|"snapshot"|"isk"}}`.
  It replaces the embedded snapshot (L4).
This replaces docs/22 §3.4's earlier `prices {mode, isk}` draft: `mode: "override"` = `use_snapshot: true`,
`mode: "replace"` = `use_snapshot: false` (`mode` stays accepted as an alias); partial overrides by group / category /
market group or multipliers are `price_overrides`.

## 6. Price output

### 6.1 When
The `price` block is emitted when the request (or batch) has `price_overrides` or `prices`, when `options.price` /
batch `price` is true, when `--prices` is set, or when a batch `fields` / `filter` / `sort_by` refers to `price.*`.
Otherwise it is absent, so existing outputs stay unchanged.

### 6.2 Shape
```jsonc
"price": {
  "total_isk": 98400000.0,          // sum of priced lines only
  "complete": false,                 // true when "missing" is empty
  "sections": {
    "ship":     { "total_isk": 350000.0,  "items": [ Line ] },
    "modules":  { "total_isk": …, "items": [ … ] },
    "charges":  { … }, "drones": { … }, "fighters": { … },
    "implants": { … }, "boosters": { … }, "cargo": { … }
  },
  "missing": [ { "section": "modules", "index": 3, "type_id": 2048, "name": "Damage Control II",
                 "quantity": 1, "reason": "no_price" } ],
  "sources": { "override:type": 2, "injected": 11, … }   // line count per source
}
Line = { "kind": "module", "index": 0, "type_id": 2873, "name": "125mm Gatling AutoCannon II", "quantity": 3,
         "unit_isk": 1250000.0, "total_isk": 3750000.0,
         "source": "override:type",      // override:type | override:market_group | override:group | override:category | injected | snapshot
         "layer": "variant",             // variant | request | injected | snapshot
         "multiplier": 0.45,             // product of the multipliers applied; key omitted when none
         "base_source": "injected",      // supplier of the base price; = source when no multiplier
         "snapshot_time": null }
```
- `kind` per line: `ship` | `module` | `charge` | `drone` | `fighter` | `implant` | `booster` | `cargo` (the ship row
  is `kind: "ship"`, `index` 0). All eight `sections` are always present (empty: `{"total_isk": 0, "items": []}`).
- One line per fitted item: ship; each module (`index` = module index; a mutated module is priced as its base type);
  each loaded charge stack (`index` = module index, `quantity` = floor(module type's base capacity / charge volume),
  Pyfa's rule, eve ruling 14:36; 0 if it does not fit — the line is then priced at 0); each drone /
  fighter stack (quantity; a fighter without `quantity` counts its squadron max size); implants; boosters; cargo
  entries at their actual quantity.
- `missing` reasons: `no_price`, `multiplier_without_base`. Missing lines are not in `sections.*.items` and not in
  totals.
- Projected and fleet booster fits are not priced (they are not part of the fit).

### 6.3 Price in batch
Each result's calc output includes its own `price` block (computed with that variant's layers) whenever the batch
has price inputs, `price: true`, or a `price.*` path in `fields` / `filter` / `sort_by`; `fields` read it as
`price.…`. With `price: true` the full block is also returned as the result's `price` (and `base.price`). `fields`, `filter`, `sort_by` and
`deltas` can use `price.total_isk`, `price.complete`, `price.sections.modules.total_isk`, etc.

## 7. BatchResponse
```jsonc
{
  "batch_version": 1,
  "form": "variants",                // fits | variants | product
  "total": 12,                       // expanded fits
  "computed": 12, "errors": 1,
  "matched": 7,                      // after filter
  "base": { "id": "base", "label": "base", "stats": {...}, "price": {...} },   // forms 2/3 with deltas or include_base
  "results": [
    { "index": 4, "id": "v5", "label": "T2 + Hail",
      "stats": { "offense.total.dps.total": 211.3, "price.total_isk": 4100000.0 },
      "delta": { "offense.total.dps.total": 12.4, "price.total_isk": 650000.0 },
      "delta_pct": { "offense.total.dps.total": 6.233041, "price.total_isk": 18.84058 },
      "price": { ... } },                                     // full price block when not projected by fields
    { "index": 7, "id": "v8", "label": "bad", "error": { "code": "PATCH_FAILED", "message": "/modules/9: no such index" } }
  ],
  "warnings": [ "field 'offense.foo' not found" ],
  "provenance": { "engine": "eve-dogma 0.1.0", "sde_build": 3569502, "sde_hash": "sha256:…", "price_source": "request",
                  "snapshot_time": null, … }   // docs/22 §2.3 form; the batch base table
}
```
- `results` holds the selected results in final order (after filter, sort, top_n); errored results stay in
  expansion position relative to each other at the end when sorting, and only when `include_errors` is true and no
  filter is given.
- With `fields`, the price block is not repeated unless a `price` path is requested or `price: true`.

- **Provenance (eve ruling 14:56):** every `calc` output and every batch result (inside its calc output, so it is
  visible as `stats.provenance` without `fields` and as the result's `provenance` key) carries the docs/22 §2.3
  `provenance` object. The BatchResponse carries the batch-level one at top level. A variant whose price inputs give a
  different base table (its FitRequest has its own `prices`) carries its own `price_source`.
- `provenance.price_source` names only where the **base price table** came from, by precedence: `request` (a
  `prices.isk` table in the request, FitRequest or BatchRequest) > `file` (`--prices` / `prices_load`) > `snapshot`
  (embedded) > `none`. Overrides never change it (overrides + `--prices` is still `file`); they show in each line's
  `source`. `snapshot_time` = the `market_time` of the file / embedded snapshot in use, null for `request` / `none`.
  The price block has no separate `snapshot_time` / price-source list; lines keep their own `snapshot_time`.

## 8. Errors
Per fit (in place, the rest of the batch continues): every `calc` error code (`BAD_REQUEST`, `UNKNOWN_TYPE`, …) and
`PATCH_FAILED` (bad pointer / op). Whole request: `BATCH_BAD_REQUEST` (no or several fit sources, unknown option,
`deltas` without reference), `BATCH_TOO_LARGE {count, limit}`, `BAD_PRICE_OVERRIDE`, `BAD_PRICES`.
Market-group overrides need the SDE dataset with the market-group tree (pipeline r5+); with an older dataset a
`market_group_id` override is ignored with the warning `market_group overrides unsupported until SDE dataset r5`.

## 8a. Interface (fixed, for adapters)
- `--sde FILE` and `--prices FILE` are **global CLI flags placed before the subcommand**:
  `eve-fit --sde x.edp --prices p.json.gz calc fit.json`.
- RPC `calc` `params` **is the FitRequest itself** (no wrapper). RPC `batch` `params` is the BatchRequest.
- RPC session methods: `version` `{}`, `sde_override` `{"path"}` / `{"pack_b64"}` / `{"reset": true}`, `prices_load`
  `{"path"}` / `{"snapshot"}` / `{"isk"}` / `{"clear": true}`.

## 9. Examples (copyable)

**E1 — compare three fits, sorted by DPS, with a price column**
```json
{"batch_version":1,
 "fits":[{"id":"rifter","fit":{"ship":{"type_id":587},"modules":[{"type_id":2873,"state":"active","charge_type_id":12608}]}},
         {"id":"slasher","fit":{"ship":{"type_id":585},"modules":[{"type_id":2873,"state":"active","charge_type_id":12608}]}},
         {"id":"breacher","fit":{"ship":{"type_id":598}}}],
 "prices":{"isk":{"587":350000,"585":300000,"598":320000,"2873":1250000,"12608":20}},
 "fields":["offense.total.dps.total","defense.ehp.total","price.total_isk"],
 "sort_by":[{"field":"offense.total.dps.total","order":"desc"}]}
```
**E2 — base + variants with deltas (gun swap, overheat, extra skill)**
```json
{"batch_version":1,
 "base":{"ship":{"type_id":587},"character":{"skills":{"default_level":4}},
         "modules":[{"type_id":484,"state":"active","charge_type_id":12608},{"type_id":484,"state":"active","charge_type_id":12608}]},
 "variants":[{"id":"t2","label":"T2 guns","patch":[{"op":"swap_type","from":484,"to":2873}]},
             {"id":"heat","label":"overheat gun 0","patch":[{"op":"replace","path":"/modules/0/state","value":"overheated"}]},
             {"id":"gunnery5","label":"Gunnery V","patch":[{"op":"add","path":"/character/skills/levels/3300","value":5}]}],
 "fields":["offense.total.dps.total","capacitor.stable"],"deltas":true}
```
**E3 — ammo × skill level product, top 5 by DPS under a price cap**
```json
{"batch_version":1,
 "base":{"ship":{"type_id":587},"modules":[{"type_id":2873,"state":"active","charge_type_id":12608}]},
 "product":{"axes":[
   {"name":"ammo","sweep":{"path":"/modules/0/charge_type_id","values":[12608,12614,12625]}},
   {"name":"skills","sweep":{"path":"/character/skills/default_level","from":3,"to":5,"step":1}}]},
 "prices":{"isk":{"587":350000,"2873":1250000,"12608":20,"12614":25,"12625":400}},
 "fields":["offense.total.dps.total","price.total_isk"],
 "filter":[{"field":"price.total_isk","op":"<=","value":2000000}],
 "sort_by":[{"field":"offense.total.dps.total","order":"desc"}],"top_n":5}
```
**E4 — signature-radius sweep of applied DPS against a target profile**
```json
{"batch_version":1,
 "base":{"ship":{"type_id":587},"modules":[{"type_id":2873,"state":"active","charge_type_id":12608}],
         "target_profile":{"signature_radius":40,"velocity":0}},
 "sweep":{"path":"/target_profile/signature_radius","from":40,"to":400,"step":40},
 "fields":["offense.vs_target_profile.dps"]}
```
**E5 — price overrides: own-built modules free, ships at 90 %, one variant with its own overrides**
```json
{"batch_version":1,
 "base":{"ship":{"type_id":587},"modules":[{"type_id":2873,"state":"active"},{"type_id":2048,"state":"active"}]},
 "prices":{"isk":{"587":350000,"2873":1250000,"2048":900000}},
 "price_overrides":[{"type_id":2048,"price":0},{"category_id":6,"multiplier":0.9}],
 "variants":[{"id":"jita","label":"no overrides for guns"},
             {"id":"stock","label":"guns from stock","price_overrides":[{"type_id":2873,"price":0}]}],
 "fields":["price.total_isk","price.complete"],"sort_by":[{"field":"price.total_isk","order":"asc"}]}
```
**E6 — single fit with price breakdown via `calc`**
```json
{"ship":{"type_id":587},"modules":[{"type_id":2873,"state":"active","charge_type_id":12608}],
 "drones":[],"prices":{"isk":{"587":350000,"2873":1250000}},
 "price_overrides":[{"category_id":8,"multiplier":1.0}],"options":{"price":true}}
```
(→ `price.missing` lists the charge 12608: the category multiplier has no base price.)

**E7 — RPC framing (serve-stdio / eve-wasm `rpc`)**
```json
{"id":1,"method":"batch","params":{"batch_version":1,"fits":[{"fit":{"ship":{"type_id":587}}}],"fields":["navigation.max_velocity"]}}
```

## 10. Implementation notes (eve-dogma)
- Implemented: `crates/eve-dogma/src/batch.rs`, `src/price.rs`, tests `crates/eve-dogma/tests/batch_prices.rs`; CLI
  `eve-fit batch --request`, JSONL BatchRequest lines, `--prices FILE`; RPC `batch` (alias `calc_batch`) and
  `prices_load` (`{"clear":true}` clears). SDE dataset r5 (market-group tree) since eve-dogma d55fadb, so
  `market_group_id` overrides are supported; with a pre-r2 dataset they are ignored with the warning in §8.
- Module `eve_dogma::batch` expands, computes with the existing parallel batch workers (data and caches shared,
  output order fixed), then projects / filters / sorts. `eve_dogma::price` resolves layers per type and builds the
  block; the market-group tree comes from the SDE tables (dataset r5+).
- Tests: batch == one-by-one `calc` (byte-identical) on all forms; cap error; determinism (two runs, 1 vs N threads);
  every precedence rule and the multiplier chain; eve3 batch-suite through its adapter.

## 11. Contract decisions by F (2026-10-03 14:50 CST; differences from bench batch/ prices.py at 93853b0)
1. `base_source` without a multiplier = `source` (eve ruling); bench reference currently emits `null`.
2. All eight `sections` always present, empty ones as `{"total_isk": 0, "items": []}`, so `price.sections.charges.total_isk`
   is `0`, not `null`, for a fit without charges (bench reference omits empty sections).
3. Sweep ids/labels use compact JSON with sorted keys (§2.3); the bench uses Python's default `json.dumps` (`", "`, `": "`).
4. L2 tie on the same target: the FitRequest's own entry wins over the batch-wide one (bench lists batch-wide first).
5. Fighter lines without `quantity` use the squadron max size (bench: 1). Mutated drones are priced as their base type.
