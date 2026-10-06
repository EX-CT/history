# HANDOFF / STATUS — EVE fitting project (EX-CT)

Anyone resuming work starts here. **Rule: commit + push after every small step; unfinished work goes to a `wip/*` branch. Update your own section below after each push.** Coordinator: eve. Last full update: 2026-10-03 14:25 CST.

## Standing decisions (user, 2026-10-03)
- Mainline engine: Rust, EX-CT/eve-dogma (built on variant F). J (C++) kept only as backup/speed reference (eve-dogma branch `j-backup`, lab tags `j-backup-2026-10-03`, `j-graphs-wip-2026-10-03`). All other engine lines stopped.
- **Feature completeness and correct calculation first; coverage may only grow, never shrink; optimization after.** Must cover ALL Pyfa features (docs/19); extras (beyond Pyfa) counted separately.
- Pyfa parity wins: Pyfa special behaviours are implemented as observed (documented, no copied code). Only proven Pyfa-bundled-data vs SDE drift goes to eve-sde-pipeline docs/pyfa-data-drift.json (eve approves).
- Engine/server/MCP never call ESI. ESI login/skills sync is web-client only (later). Engine defines character/skills input.
- Formats (EFT/DNA/XML/ESI/EFS/HTML/Pyfa saved fits) live in crate `crates/eve-fit-formats` inside the eve-dogma workspace (no separate repo); engine takes structured JSON only.
- Optimizer: v1 exists (eve-dogma 20aa425) but is **deprioritized** — keep as is, no regressions, no further work (AI will optimize via MCP).
- No-regression gate: bench pending-1.11 `tools/check_no_regress.py` + `baselines/f.json` (baseline 2da8150); pass counts, passed case ids and docs/19 have-counts may never drop.

## New core requirements (2026-10-03 14:14–14:23) — see docs/20, docs/21, docs/22
1. **Batch API (extra, high priority):** many fits, or base fit + variant patches (modules, ammo, states, skills, implants, boosters, fleet boosts, projected, targets), cartesian product and parameter sweeps (with a combination cap); shared data/caches, deterministic; output `fields` selection, delta vs baseline (abs/%), `sort_by`, `filter`, top-N, per-variant id/label, per-item errors. Entry points: Rust lib, RPC/CLI `eve-fit batch`, WASM, MCP `compute_batch`. Test: batch == one-by-one, in gate.
2. **Prices are engine core:** request input `price_overrides` by type_id / market_group_id (incl. children) / group_id / category_id; value fixed (0 for self-made/stock), or multiplier. Precedence: request override (type > market group, most specific first > group > category) > injected prices (`prices` / `--prices`) > embedded release Jita snapshot. Output total + per-item breakdown with `source` per price and missing-price list. Batch variants may carry their own overrides; sort/filter by price.
3. **Embedded SDE:** each release embeds its SDE build (no external download); report sde_build + hash; optional update switch `--sde` / `sde_override`. Engine never goes online.
4. **Frozen prices:** each release embeds a price snapshot. Rule: Jita 4-4 (60003760) sell orders only; drop orders with fewer than `min_units` units (filter by unit count, not by a percentage of orders); p0 = lowest remaining; price = unit-weighted average of orders within [p0, p0×1.05]; both parameters configurable.
5. **Market price updater:** separate tool, repo EX-CT/eve-market-prices (MIT), pluggable sources (ESI orders, Fuzzwork, more later), emits versioned snapshot files (schema in docs/22).

## Owners and queues
### F bot — EX-CT/eve-dogma (main 20aa425 at 13:56, CI green)
Queue: (1) eve-fit-formats unit tests + CI; (2) remaining 26 effects/ failures, Pyfa behaviour; (3) batch API + price overrides/breakdown (docs/20/21/22 contract first); (4) embedded SDE + price snapshot + injection; (5) close docs/19 F-column missing (26) and partial (24) items incl. alpha clones; wire no-regress gate into CI.
Scores 20aa425: core 1.10 339/339, effects 2352/2378, ext 116/116 (pending-1.11 ext 187/187+ fehp 15/15), cap 150, mutated 93, formats 4779, graphs 178 (0.3: 192).
_Status:_ see per-bot section "variant F / eve-dogma" below.

### eve3 — EX-CT/eve-dogma-bench (pending-1.11), docs/19 owner
Queue: (1) Pyfa-generated cases for the 26 missing + full cases for partial items; (2) batch-suite incl. price-override cases; (3) docs/22 cases (embedded SDE version/hash, price rule pure-function cases, injection precedence); docs/19 extras ENG-BATCH-001, ENG-PRICE-001. optimizer-bench parked as WIP (13cb0d9..d48bbab).
_Status:_ eve3: add a section "eve3 / bench" below.

### eve4 — eve-fit-web, eve-fit-mcp, eve-sde-pipeline, eve-market-prices
Queue: web fit library + Pyfa saved-fit import (with engine bump to latest and showing new outputs) ‖ eve-market-prices; then MCP `compute_batch` + price_overrides pass-through (right after F's contract); web "my prices" setting; then mcp/web test gaps (inventory/mcp-web-gaps.md). MCP has no optimize tool. ESI login last.
_Status:_ see per-bot section "eve4 / eve-fit-web" below.

## docs/19 counts (have/partial/missing/n/a), 200 items
- f (2da8150): 104/24/26/46 · mcp: see latest docs/19 (07341e3 upgraded 51 engine-backed items) · web (40e6044): 84/81/29/6 · formats: 10/1/2/1 · extras: UI-CMP-001 (+ENG-BATCH-001, ENG-PRICE-001 pending)

---
# Per-bot status sections (each bot updates only its own)

## variant F / eve-dogma (executor bot; updated 2026-10-03 15:10 CST)

### Current commits
- EX-CT/eve-dogma main: **8bde0ba** provenance + embedded price snapshot + JCS + global --sde/--prices + SDE_LOAD_FAILED (CI run 37105439110 green); 197223f batch API + prices (green); d55fadb SDE dataset r5 (green).
- EX-CT/eve-fit-docs main: **eccf455** docs/22 + docs/23 eve 14:56 rulings + answers to eve4 B1–B8; 399b839, 6baea45, 8b1e6cf earlier.
- EX-CT/eve-sde-pipeline main: 83ba879 pyfa-data-drift.json.
- EX-CT/eve-dogma-bench: only parked **wip/stats-ext-suite** = 07beb42 (reference only).

### Done
- docs/23 batch + prices (lib `eve_dogma::batch`, `eve_dogma::price`; RPC `batch`/`calc_batch`, `prices_load`; CLI `batch --request`, JSONL BatchRequest lines). Batch response: top-level `provenance` + per-result `provenance`; all price-override lists validated up front (whole-batch BAD_PRICE_OVERRIDE); BATCH_TOO_LARGE count computed analytically.
- docs/22: `provenance` on every calc/batch result (`crates/eve-dogma/src/prov.rs`); price_source request>file>snapshot>none; `version` CLI command + RPC; global `--sde FILE` / RPC `sde_override` → `SDE_LOAD_FAILED` with reason not_found/corrupt/hash_mismatch/incompatible_version (valid packs currently refused as incompatible_version: no runtime pack interpreter yet); embedded snapshot = eve-market-prices `prices-jita44-20261003T063856Z` (`crates/eve-dogma/data/`, hash sha256:3dd62f6c…, JCS-verified); `--prices`/`prices_load` read .json/.json.gz snapshots (JCS hash + invariant checks) or plain tables.
- Scores (8bde0ba, pending-1.11 d151cb3, data/ generated locally): batch **78/92**, d22 sde **7/17** (5 pending), price_inject **17/32** (1 pending). no-regress gate: no regression. All remaining failures are bench-side vs the 14:56 rulings (see eve3 list below).
- For eve3: SDE_PACK_INVALID → SDE_LOAD_FAILED+reason; price_source embedded/request+embedded/request+file → snapshot/request/file; price_time → snapshot_time; bench snapshot files' content_hash must use JCS (RFC 8785); sweep labels compact sorted JSON; price_missing_list / price_multiplier_without_base / calcprice_request_table / price_variants_sort_filter assume no embedded snapshot (use `prices.use_snapshot:false` or update expectations); `batch/data` + `d22/data` are gitignored (generate or commit).

### Next steps
1. docs/19 missing items with eve3 cases: ext brdc, cimp, alpha, dpb, tpb, src, dep; ext/rpc 54; type RPC fields; CONTRACT.md "Draft 1.11: missing-f".
2. docs/22 embedded edp pack + runtime pack interpreter (then sde_hash_of = "pack").
- Pending external: eve3 1.11 tag → switch CI bench tag, inventory step blocking.

### Key context for a successor
- Paths: eve-dogma `/workspace/exct-eve/eve-dogma-main`, docs `/workspace/exct-eve/fit-docs-main`, pending-1.11 clone `/tmp/nrg/bench`, Pyfa reference `/workspace/exct-eve/ref/pyfa`.
- Build: `export EVE_DOGMA_DATASET=/workspace/exct-eve/data/dataset-3569502-r5.json.gz; cargo build --release --locked -p eve-cli`. Gate: `BENCH=/tmp/nrg/bench SUITES_DIR=/tmp/ci-suites ci/run_suites.sh native $PWD/target/release/eve-fit`; no-regress: `/tmp/nrg/bench/tools/run_all_suites.sh target/release/eve-fit out && python3 /tmp/nrg/bench/tools/check_no_regress.py --baseline /tmp/nrg/bench/baselines/f.json --run-dir out`; batch `python3 batch/run_batch.py --cmd ENGINE --out X`; d22 `python3 d22/run_d22.py --suite sde|price_inject --cmd ENGINE --out X`.
- New output keys → `ci/round1-new-keys.txt` + `ci/round1.sha256`; existing-field changes must be intended and re-baselined in `ci/round1-base.sha256`.
- Embedded snapshot update: replace file in crates/eve-dogma/data + EMBEDDED_ID/TIME/HASH in price.rs (test `embedded_snapshot_identity_and_jcs` checks them).
- Commit identity `-c user.name=EXCT-Bot -c user.email=bot@exct.invalid`; never force-push; unfinished work → `wip/*`.

## eve4 / eve-fit-web (executor bot; updated 2026-10-03 16:10 CST)

### Current commits
- EX-CT/eve-fit-web main: **c07e9d9**. All work is pushed; there are no wip branches.
- Run 37108036168 (0608315) was green and deployed. Unit tests passed. e2e: ts-worker 73/73, wasm-worker 87/87, J 83/83, http 87/87.
  - Bench pending-1.11 @7192f66: core 339/339, ext 208/239, ext_rpc 0/54, batch 93/93, effects 2378/2378, graphs 192/192, cap 150/150, mutated 93/93, formats 4779/4779, sde 16/18, price_inject 32/32. No regression.
  - Gate baseline is f.json without sde version_cli_fields / version_rpc_fields (browser-inherent: version.target = wasm32).
- Run 37108520615 (c07e9d9) green and deployed: e2e ts 78/78, wasm 92/92, J 88/88, http 92/92; bench same as above, no regression. Live e2e wasm-worker 92/92, ts-worker 78/78; data/presets-pyfa-LGPL-GPL.json served (118 patterns, 195 profiles).
- Live build-info: engine_f 8bde0ba, prices_snapshot prices-jita44-20261003T070857Z.

### Done this round
- 2308bf3: F pin set to eve-dogma 8bde0ba (effects 2378/2378).
- bc10926 / e240b23 / 0608315: browser-rpc and browser-engine pass any RPC through (batch, prices_load, sde_override; --prices). The response text is kept exactly as the engine wrote it. Compare makes one engine `batch` call.
- 5e290d9 + a9ee592: prices come from the engine price block.
  - Price box shows source, missing items, and provenance.
  - "My prices" overrides and self-made = 0 (localStorage eve-fit-web-my-prices).
  - Optional "update prices" uses prices_load with the site's own copy of the latest eve-market-prices release. CI downloads and checks it, and the 6-hourly schedule refreshes it.
- 0cd6084, PRF-DMG-001:
  - Built-in damage patterns are now only Uniform and pure EM/Thermal/Kinetic/Explosive. The invented NPC/ammo values are removed.
  - Pyfa's built-in patterns and target profiles are opt-in (Profiles tab) from the pipeline's separate asset presets-pyfa-LGPL-GPL.json (GPL data).
  - CI deploys that file beside the site with its notice and attribution, slimmed by tools/slim-presets-pyfa.mjs. It is not in the MIT repo, and the browser fetches it only when the option is on.
- 0cd6084, ENG-CORE-006: e2e show-info-engine-values (every fitted value = engine attribute) and show-info-skill-formula (HNB II all-V formula).
- c07e9d9: docs/test-ids.md and README.

### Next steps
1. User/parent: confirm that deploying the Pyfa GPL data file next to the site (opt-in, attributed, not vendored) is acceptable. If not, remove the CI step.
2. Bench owners may add a web baseline (sde version fields: target wasm32).
3. pyfadb built-in pattern ids are not yet mapped to the Pyfa preset ids (a warning on import).
4. Deferred (C): the remaining docs/19 partial-test items.

### Key context
- Repo: /workspace/exct-eve/eve-fit-web. Local preview: `npm run build && npx vite preview --port 4180`, then `node tools/e2e.mjs http://127.0.0.1:4180/eve-fit-web/ wasm-worker|ts-worker`. For http: `node tools/engine-bridge.mjs --stdio "<eve-fit> serve-stdio" --port <free port>`. Other agents' bridges hold 8787 to 8799.
- The F build for 8bde0ba is in /tmp/ed19: wasm in target/wasm32-unknown-unknown/release-small, native eve-fit in target/release. It has been copied to public/engines/f.
- The Pyfa fixture generator (GPL, outside the repo) is in /workspace/pyfa-db-fixture.
- The formats layer drops what Pyfa would not fit (capital modules, extra slots, wrong charges), so illegal-fit tests add those items through the market.

## eve4 / eve-fit-mcp / eve-market-prices (executor bot; updated 2026-10-03 16:24 CST)

### Current commits
- EX-CT/eve-fit-mcp main: **249bf39** = release **v0.4.2** (release run 37109345277, published 16:20 CST; CI 37109258068 green; npm test 98 pass/1 todo/0 fail on 8bde0ba; mcp-bench core 339/339, ext 202/202, effects 2378/2378, cap 150/150). Fixes eve3's mcp-batch 71/93 (results-1.11/mcp-v0.4.1.md): engine error fields kept (BATCH_TOO_LARGE count/limit) in text + `structuredContent.error`; compute_fit `detail:"full"` = engine calc output verbatim (request_hash/notes/engine in `_meta["eve-fit-mcp"]`); compute_batch fits[i] the MCP cannot normalise go to the engine unchanged (error in place); compute_fit accepts builtin `damage_pattern`/`target_profile`; injected price file: tool `load_prices` {source: path|URL|"latest", clear}, env `EVE_FIT_PRICES` (+ `EVE_FIT_PRICES_REPO`), engine `--prices FILE` / RPC `prices_load` (overrides > request prices > file > embedded). Commits c1a45c1, 6638472, 68306ce, 7f77720 (9 new test ids -> ENG-BATCH-001 / ENG-PRICE-001; 99 ids). **Batch suite via MCP at bench 01e6724: 80/93 with the stock tools/mcp_batch.py, 93/93 with a 2-change adapter patch** (eve3: map `--prices FILE` to env EVE_FIT_PRICES=<abspath> instead of UNSUPPORTED; on isError use `structuredContent.error`). Before: **447420f** = release **v0.4.1** (release run 37106390778, published 15:27 CST; CI 37106278784 green): engines.lock eve-dogma **8bde0ba**, `provenance` surfaced by compute_fit (summary + full section), compute_batch (top level, per result, table header), price_fit; price_fit `use_snapshot` (engine snapshot fills items without a market price); new test mcp.features.provenance -> ENG-PRICE-001 (90 ids). mcp-bench on 8bde0ba: core 339/339, ext 202/202, effects 2378/2378, cap 150/150. d3707e7 pin+provenance. Before: d3786eb = release **v0.4.0** (release run 37105109044 success, published 15:04 CST; assets eve-fit-mcp-0.4.0.tgz, eve-fit-mcp.tgz, SHA256SUMS; CI 37104953313 green: npm test 85 pass/1 todo/0 fail, mcp-bench ext 202/202, effects 2378/2378, cap 150/150). 462c759 engines.lock -> eve-dogma **197223f** (docs/23 batch + prices); CI must run the docs/23 checks (TODO fallback fails CI). Before it: 583a197 price_fit engine path (include_* toggles as a view over engine sections), e309e7e README, 73eb2b7 module /online|/active|/overheated, 7e8fa6b docs/test-ids (tools/test-ids.py), c1626ef price_fit via engine, aeb7b7e compute_batch, 1665e11 compute_fit price inputs. Previous release v0.3.1 (e7b794a). No wip branches.
- EX-CT/eve-market-prices main: **8d65963** price-rule-bench pin bench **01e6724** (42/42 locally; CI green). Before: **364b96d** (0.2.1; CI green, price-rule-bench **41/41** at bench b638e8a): roundIsk = spec exactly (half-even on the 12-significant-digit decimal value, BigInt, Python Decimal vectors), Fuzzwork clamp test + rule.exact false. 5c7a860 README rule details settled (eve3 ruling 15:11). a7ec353 (0.2.0; CI 37105405374 green incl. price-rule-bench 21/21 at bench d151cb3): docs/22 rulings eccf455 — coverage = all published marketable types from CCP's JSONL SDE (`--ccp-sde`), content_hash = RFC 8785 JCS (RFC + Python `jcs` vectors). Earlier e9781a5 CLI `rule` + band-edge fix. Snapshot run 37105434259 published **`prices-jita44-20261003T070857Z`**: 9178 priced, 10388 missing of 19566 requested (CCP SDE 3569502), sha256:279683dd…; hash re-verified with Python jcs. wip/docs22-schema kept.

### Done
- docs/23 MCP pass-through, checked against eve-dogma 197223f: compute_fit `price_overrides` / `prices` / `price` (names -> ids, engine block verbatim), compute_batch (fit sources normalised, engine `batch`), price_fit (market table + own isk injected as `prices.isk`, engine block; legacy sum only for old engines). npm test on 197223f: 88 pass, 1 todo (security-status effect 6871, engine). mcp-bench on 197223f: core 339/339, ext 202/202, effects 2378/2378 (0 lost through MCP), cap 150/150.
- Step 2 test gaps (inventory/mcp-web-gaps.md): mcp-bench in CI, silent skips hard-fail, stats/validation value assertions, get_ship traits, utility module states; docs/test-ids.{md,json} (89 ids with inventory item refs).
- eve-market-prices: d22/price_rule found a real bug (order prices were trimmed to 12 digits before the band compare, so an order one ulp above band_max counted); fixed per docs/22 §4.5.
- Earlier: mcp_batch fixes (error codes, graph passthrough), v0.3.1; eve-market-prices v1 updater + snapshot workflow.

### Next steps
1. eve3: apply the 2-change adapter patch to bench tools/mcp_batch.py (diff in the eve4 report) to get 93/93; the remaining 13 stock-adapter failures are all adapter-side (10 `--prices` cases, 3 BATCH_TOO_LARGE count/limit read from text only).
2. docs/22 b577db9 / f6fca5f checked: no MCP change needed.

## eve3 / bench (executor bot; updated 2026-10-03 15:15 CST)

### batch-suite, no-regress gate, optimizer-bench (shelved at d48bbab, score.py not started) — updated 2026-10-03 15:22 CST
**Current commits** (everything pushed)
- eve-dogma-bench pending-1.11:
  - Gate + baseline: `98419df`, `b3a0957`, `07245e8`, `c2229b2`, `88ed590`, `32981f5`, `d151cb3` (d22 suites), `01f39e1` (totals after the rulings), `05ae5a1` (raised to 8bde0ba).
    - `baselines/f.json` = eve-dogma 8bde0ba (CI green): core 339, ext 208/239, ext_rpc 0/54, batch 93/93,
      effects 2378, graphs 192, cap 150, mutated 93, formats 4779, sde 18/18, price_inject 32/32; docs/19 f 106,
      mcp 102, web 84, formats 10. price_rule runs only with `PRICE_RULE_CMD` (eve4 5c7a860: 41/41); `SDE_PACK`
      enables 6 pending d22 cases (F refuses valid packs with incompatible_version until the pack interpreter lands).
  - batch-suite: `a00620f`, `97dc60f` (docs/23 shape), `89f5853`, `30a47bb`, `93853b0` (14 price_* cases), `d4ed730` (eve's docs/23 price rulings applied).
    `dfb4f49`: 34 gap cases (gap 15, gap_error 12, calc_price 6, calc_price_embedded 1) + `batch/data/` price files.
    92 cases; self-test 92/92; d990818 0/92 (no `batch` method; calc has no price block / no `--prices`).
  - `48b1cb6`: embedded-snapshot batch case sets options.price.
  - d22 suites `04f9ba5` (docs/22; provisional adapter `d22/adapter.py`): sde 22, price_inject 33, price_rule 21.
    d990818: sde 0/17 (+5 pending, need `SDE_PACK`), price_inject 0/32 (+1 pending); price_rule targets the
    updater (eve4), not F, and runs only with `PRICE_RULE_CMD`.
  - optimizer-bench WIP: `13cb0d9`..`d48bbab`.
- wip branches: `wip/eve3-batch-prices` (already merged).

- eve's rulings `ef17210` (unified provenance; price_source = base table only, request > file > snapshot > none;
  SDE_LOAD_FAILED + reason). price_rule `b638e8a` adopts eve4's rule (eve-market-prices e9781a5) as the reference:
  41 cases (the 21 existing ones unchanged), eve4 41/41. The spec is in d22/README.md.

- F 8bde0ba (batch + prices, CI green) and the contract in eve-fit-docs eccf455. Bench fixes: `df587f0` (JCS
  content_hash; batch/data and d22/data committed via `.gitignore` `/data/`) and `4783eab` (contract §11 decisions,
  compact sweep labels, use_snapshot:false on 4 cases). 8bde0ba: batch 93/93, sde 18/18 (+5 pending),
  price_inject 32/32 (+1 pending).

**In progress:** none. 8bde0ba has no real F bug in any suite; every failure was a bench bug and is fixed.

**Next step:** when F has the edp interpreter and the pipeline publishes a pack, run with `SDE_PACK`.

### docs/19 + missing/partial cases (updated 2026-10-03 15:54 CST)
**Current commits:** eve-dogma-bench pending-1.11: 443ee69, 5b6051c, d7ba4d9, 113415b, 5dc739d, a319f0f, 11993f5, 583f912, b34ebb9, 455aa53, 1fd7e37, e3e3895, 1fdcf61, 2738960, 6f3e985, 8683e48, 5efa174, 90f8f56, f212bcd, 89e3805, 7192f66, 26e3833, 5c1ff1f, 4a80c84, 01e6724 (tip 01e6724). eve-fit-docs: ef6cdb6, 07341e3, eccb194, b6b8a6d, 295694a, c35c162, 8c25b2d, 3f86ebb, e817900, 9bc28f7, bccc5b8. Nothing uncommitted; **no wip branches**.

**Progress**
- 26 f-missing items: 16 Pyfa-generatable with 68 cases. `ext:` brdc_ (ENG-MISC-004), cimp_ (ENG-IMP-002, CHR-006), alpha_ (ENG-CORE-009), dpb_ (PRF-DMG-001), tpb_ (PRF-TGT-001), src_ (ENG-CORE-007), dep_ (ENG-CORE-008). `ext-rpc:` var_, cmp_, mkt_, srch_, isets_, evemon_, names_, backup_ (ENG-MOD-013, MKT-004, MKT-001, MKT-002, ENG-IMP-005, CHR-004, SVC-005, DB-003). Not generatable: CHR-009, PRC-001..005, UI-STAT-PRC, UI-PREF-MKT, DB-001, DB-008. Oracle opt-in `ORACLE_EXTRA=drafts,sources` + `oracle/pyfa_lookup.py` (default output byte-identical). Draft fields: CONTRACT.md "Draft 1.11: missing-f".
- F d990818 (binary /workspace/exct-eve/bin/eve-fit-d990818): ext 208/239 (breacher_dc 4/4, char_implants 2/6, others 0), rpc 0/54, effects 2378/2378. Flipped f: ENG-MISC-004 missing -> have, ENG-CORE-003 partial -> have. Results: bench results-1.11/ED-d990818.md.
- f partial: `ext-rpc:type_*` (23) for MKT-003 / ENG-SHIP-006 / CHR-008 (F 0/23); other f partials are implementation gaps.
- mcp partial: `tools/mcp_batch.py` (bench suites through compute_fit / compute_graph), suites mcp-bench/-ext/-ext-unit/-cap/-mut/-graphs; 59 mcp items partial -> have (eve-fit-mcp 8c6b93d + F 2da8150). MCP bugs: nested empty `booster_fits: []` rejected (fit.ts:209), projected fighter quantity defaults to 1 (fit.ts:202).
- eve-fit-mcp v0.3.1 (e7b794a) re-run (bench results-1.11/mcp-v0.3.1.md): engine d990818 core 339/339, ext 208/239, effects 2378/2378, cap 150/150, mut 93/93, graphs 189/192; engine 2da8150 the same except ext 205/239, effects 2352/2378. MCP = engine on every Pyfa case. Graph failures (both engines): err_missing_x, err_missing_x_values, err_missing_y (MCP fills defaults; n/a for MCP is eve's call, left as is). mcp partial -> have: ENG-FTR-002, ENG-PROJ-002/003/004, ENG-FLT-002. ENG-MISC-004 (brdc 4/4) and ENG-CORE-003 (new suite mcp-effects) pass only with engine d990818, so they stay partial until the MCP pins it. New ids mapped (partial): mcp.unit.empty-nested-arrays -> ENG-FLT-002/ENG-PROJ-003, mcp.unit.projected-fighter-default-quantity -> ENG-PROJ-002. mcp.features.contract-error-codes is unmapped (no docs/19 item). mcp column: have 102 / partial 32 / missing 40 / n/a 26 (+3 extras).
- mcp-graphs n/a (eve ruling): err_missing_x / err_missing_x_values / err_missing_y via suites.yaml `na:` (check_inventory excludes them and rejects citing them; tools/apply_na.py rescored results: 189/189).
- eve-fit-mcp v0.4.0 (d3786eb, pinned engine 197223f, contains d990818; bench results-1.11/mcp-v0.4.0.md): core 339, ext 208, effects 2378, cap 150, mut 93, graphs 189/189 + 3 n/a; batch via compute_batch (tools/mcp_batch.py --tool compute_batch) 52/92 before the provenance rulings (engine 62/92), 8/93 after. Test-id map imported (36 ids with refs; security-status-value is todo, not mapped). mcp flips: ENG-MISC-004, ENG-CORE-003/006, ENG-MOD-007, ENG-SHIP-006, ENG-DRN-003, ENG-FTR-004, ENG-OFF-006/007, ENG-PROJ-006, PRC-003, UI-STAT-OUT/MIN/BMB, GRF-OPT-001..008 -> have; ENG-BATCH-001 missing -> partial; ENG-PRICE-001 stays partial (mcp-batch price_* 0/14).
- F 8bde0ba on bench 05ae5a1 (binary eve-fit-8bde0ba-r5, dataset r5): batch 93/93, sde 18/18 (+5 pending), price_inject 32/32 (+1 pending). The earlier 77/93 / 21/32 came from my r1-dataset build, not from F; this is corrected in results-1.11/mcp-v0.4.0.md and results-1.11/F-8bde0ba/. ENG-BATCH-001 / ENG-PRICE-001 f: partial -> have, pending-bench note removed.
- eve-fit-mcp v0.4.1 (447420f, engine 8bde0ba, 90 ids, 37 with refs; --root mcp = v0.4.1). mcp-batch 71/93 on 26e3833. MCP-only failures for eve4 are listed in results-1.11/mcp-v0.4.1.md:
  - 10 --prices FILE: no MCP equivalent; n/a is eve's call
  - 3 BATCH_TOO_LARGE without count/limit
  - 7 full results with extra engine/notes/request_hash
  - multi_error_in_place rejected up front
  - multi_ext_mix: compute_fit rejects builtin target_profile/damage_pattern ("Invalid input at fit.ship") while compute_batch computes them
- Bench 26e3833: batch identity compares JSON numbers canonically, so the 14 price_* "1 vs 1.0" failures are gone. MCP CI features+unit run locally: 38 pass / 0 fail (+1 todo, 1 skip).
- mcp column: ENG-PRICE-001 partial -> have; ENG-BATCH-001 stays partial. mcp.features.provenance -> ENG-PRICE-001 (partial).
- web strict gate: ENG-CORE-006 and PRF-DMG-001 have -> partial.
  - ENG-CORE-006: the site test checks presence only.
  - PRF-DMG-001: src/data/presets.ts has 15 hand-made patterns, not Pyfa's builtins (e.g. Guristas 0/18/82/0 vs Pyfa 19.8/80.2), and dpb_* fail in the browser.
  - ENG-CORE-001 stays have: its site tests pass, and the 25 effects failures are only the stale wasm 20aa425, which needs bumping. baselines/web.json is now web have 104.
- d22 price_rule: + round_11_integer_digits (55174443703.65 -> 55174443703.7, Decimal-verified), 42 cases, bench 7192f66; eve-market-prices 364b96d passes 42/42 (read-only build).
- web: eve-fit-web run 37104154159 (F wasm 20aa425 in Chrome, bench c2229b2) verified per case (results-1.11/web-fdbb014.md); suites web-ext/-ext-unit/-effects/-cap/-mut; 22 web items partial -> have; baselines/web.json added (f.json unchanged).
- Counts (parity 200): f 106/23/25/46, mcp 124/28/22/26, web 104/61/29/6, formats 10/1/2/1 (have/partial/missing/n/a).
- check_inventory: 0 problems.

**Next step:**
1. eve: rule whether the 10 `--prices FILE` batch cases are n/a for MCP.
2. eve4: MCP compute_batch gaps (results-1.11/mcp-v0.4.1.md). When they are fixed, re-run mcp-batch; ENG-BATCH-001 mcp can become have.
3. web: when the site bumps F wasm past 20aa425, refresh baselines/web.json (effects 2353 -> 2378). Re-check PRF-DMG-001 once the site ships Pyfa's builtin patterns.
4. Re-score new F commits with ext/tools/score.py + score_rpc.py.
5. Build worktrees /workspace/exct-eve/ed-197223f and ed-8bde0ba are left in place for re-use.
**wip branches:** none.

