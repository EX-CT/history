# 20 — Rust mainline: architecture plan (proposal)

**Status: PROPOSAL, 2026-10-03 (CST).** Nothing here is implemented as part of this document. Large-scale work starts
only after the user approves.

**Inputs:**
- [docs/19](19-pyfa-feature-inventory.md), the Pyfa v2.69.0 inventory: 200 items. Its YAML is the scope baseline.
- The decision of 2026-10-03: mainline = **Rust, based on F** (eve-dogma-lab `variant-f` / `variant-f-perf`, SDE
  codegen + WASM). J (C++) stays a speed reference only.
- The rule: **cover all of Pyfa, never less**. The bench corpus does not define scope.

**Update 2026-10-03 14:30 CST (priorities).** Order is now: feature completeness and correct calculation first
(docs/19 F column), then the **batch API + prices** ([docs/23](23-batch-api-and-prices.md), engine core), embedded SDE
and price snapshot ([docs/22](22-embedded-sde-and-prices.md)); the optimizer (P0-5, docs/21) is **demoted**: v1 stays
as is, no further work. The no-regression gate (bench pending-1.11 `check_no_regress.py`) is blocking in eve-dogma CI.

## 1. Where F stands

| | F today (`variant-f-perf` f5b709f + open branches) |
|---|---|
| crate | one crate `eve-dogma-f` (lib + bin + cdylib) |
| codegen | `build.rs` compiles the SDE dataset into Rust (5.4 MB generated). The Pyfa parity layer is generated `sp_*` specials plus hand-written code in `engine.rs`. |
| modules | `engine.rs`, `data.rs`, `stats.rs`, `capsim.rs`, `formats.rs`, `eft.rs`, `request.rs`, `j.rs` (JSON writer), `wasm.rs`, `main.rs`; ≈7 k lines of hand-written code |
| surface | CLI `calc/batch/serve-stdio/eft/search/type/meta/bench`; RPC `calc, search, type, meta, eft_parse, eft_export, format_export, format_import`; WASM wasip1 + wasm32-unknown-unknown C ABI (`calc`, `rpc`) |
| quality | bench 1.9.0 330/331; cap 147/150; mutated 86/93; formats 4779/4779; e_fz 8/8 (docs/19 §Method). The open fixes on `variant-f-features` (breacher 7878a41, slot rule 2046757, void bomb be35345) bring bench to 331/331 and cap to 150/150. |
| graphs | separate branch `graphs-g4`: F + `src/graphs/{dmg,app,rr,cycles,kernels,expr}.rs`, GR2 178/178 native+wasm |
| speed | ≈1131 k instr/fit corpus average vs J ≈1069 k. F has already taken J1 (in-place capsim reschedule) and J2 (exp memo). |
| docs/19 coverage (F column) | 78 have / 52 partial / 37 missing / 33 n/a |

## 2. Target crate layout

The mainline repo is one Cargo workspace. Proposed name: `EX-CT/eve-fit-core`. Reusing `EX-CT/eve-dogma` (frozen at
`dd97e12`) as a new major version is also possible; **the user decides**. (Decided 2026-10-03: `EX-CT/eve-dogma`; the C++ engine J is kept on its branch `j-backup`.) Licence: LGPL-3.0-or-later. Pyfa is used
only as a black-box oracle and behaviour reference, never as code.

```
crates/
  eve-sde           static data compiled in (codegen tables.rs): types, attributes, groups, names (en/zh),
                    mutaplasmids; later the runtime dataset loader for non-hot data (market groups, meta
                    variations, jargon, conversions, i18n), search. No engine code.            [exists]
  eve-dogma-codegen build-time generator (today's build.rs): SDE → tables.rs (eve-sde) + effects.rs (eve-dogma,
                    effect code + specials); emits the per-effect coverage manifest (§5.2)     [exists]
  eve-dogma         engine core: fit graph, modifiers, stacking, skills, specials, projected/fleet/env, RAH,
                    overrides; feature `trace` records modifier sources (Affected-by / dependants); no I/O.
                    Structured input only (FitRequest + skills): no fit formats.               [exists]
  eve-capsim        capacitor simulator (F capsim.rs + J techniques), used by stats and graphs
  eve-stats         every Pyfa stats panel: resources, defense/tank, offense (+breacher, spool min/max), mining,
                    outgoing RR/cap, drones/fighters (+EHP/regen), navigation, targeting (+lock-time table, holds),
                    bombing, heat; validation
  eve-graphs        the 10 Pyfa graphs + options (port of graphs-g4 src/graphs/*)
  eve-fit-model     FitRequest / FitStats schema (serde), fit editing ops (add/remove/state/charge/variation),
                    incremental edit + undo-friendly API, multi-fit context (projected/command fits by id)
                                                                              [exists: FitRequest types]
  eve-fit-formats   NOT part of the engine (ruling 2026-10-03). EFT (+cfg, mutated), DNA (+alt, link), ESI JSON,
                    EVE XML, multibuy, shipstats (stats supplied by the caller), EFS, muta text, HTML, additions
                    lists, auto-detect, multi-fit buffers, file/folder import, Pyfa saved-fit import. Depends on
                    eve-fit-model + eve-sde only, never on eve-dogma.                          [exists]
  eve-fit-formats-wasm  C ABI (alloc/dealloc/rpc) of eve-fit-formats for the frontend          [exists]
  eve-character     skill profiles (All 0/4/5, custom), alpha clone caps, character implants, EVEMon/XML import,
                    skill-plan export, SP/train-time; the character/skill INPUT FORMAT that ESI clients fill in
  eve-profiles      built-in damage patterns, target profiles, implant sets (from the presets pipeline), user libraries
  eve-optimizer     skill-based optimizer (§4 P0-5): goals × constraints × the character's skills → ranked fits
  eve-prices        price-source trait (ESI, fuzzwork, evetycoon, …), cache, totals, Optimize Fit Price; network
                    behind a feature, and a host-supplied fetch callback on wasm
  eve-store         persistence for CLI/desktop/server: fit library (folders/tags), profiles, characters, backup /
                    restore (JSON + EVE XML), Pyfa saveddata import (migration path: more than Pyfa)
  eve-rpc           JSON-RPC method tables shared by stdio, HTTP and WASM, with contract error codes: engine table
                    (calc, batch, graph, search, type, market, character_*, optimize, price, …) and formats table
                    (eft_parse, eft_export, format_import, format_export); hosts that link both serve both
  eve-cli           binary `eve-fit` (convenience tool linking engine + formats): calc, batch, graph,
                    graph-batch, format, eft, search, type, meta, optimize, serve-stdio, serve-http, bench  [exists]
  eve-http          thin HTTP server over eve-rpc (feature-gated deps)
  eve-wasm          engine only: wasm-bindgen typed JS/TS bindings (+ .d.ts generated from the schema) and the
                    existing C ABI (calc, rpc); batch/streaming calls; built for the web worker   [exists: C ABI]
```

Dependency graph as built in `EX-CT/eve-dogma` (2026-10-03, commit 597b7fc; details in its
`docs/FORMATS-SPLIT.md`):

```
eve-fit-model ──┬──────────────► eve-fit-formats ──► eve-fit-formats-wasm
eve-sde ────────┤                        │
                └──► eve-dogma ──┬───────┴──► eve-cli (eve-fit)
eve-capsim ──────────►┘          └──► eve-wasm
eve-dogma-codegen (build-time) ──► eve-sde, eve-dogma
```

**Formats are not part of the engine** (user ruling, 2026-10-03). The engine takes the structured fit plus skills
input and only calculates; text formats are converted before (import) or after (export) by `eve-fit-formats`, in the
CLI/MCP/web layer. CI enforces the boundary with `cargo tree`.

**MCP.** Keep `EX-CT/eve-fit-mcp` (TypeScript, eve4). It talks to `eve-cli serve-stdio` through its existing `rpc`
adapter, and it gains `graph`, `price` and `market` tools once `eve-rpc` exposes them. A Rust MCP crate is not
needed now. Revisit it only if the TS layer becomes a bottleneck.

**Web.** `EX-CT/eve-fit-web` switches its default backend from `ts-worker` to `eve-wasm`. ESI login and ESI fittings
are web-frontend features, owned by eve4 and scheduled later (ruling of 2026-10-03). The web passes the fetched skills
and fits into the engine's own input format (`eve-character`, `eve-fit-model`).

**SDE pipeline.** `eve-sde-pipeline` (eve4) stays the single source of datasets and presets. New outputs it needs:
- alpha-clone skill caps
- skill SP and rank, and character attributes, for train time
- item conversions (renames)
- the full market-group tree
- localized names for all Pyfa languages

**Codegen vs runtime data.** Keep F's compile-time codegen for the hot path. A new SDE means a CI rebuild that is
triggered by a pipeline release. `eve-sde` also loads the same dataset at runtime for the non-hot data: names, market,
presets. That way search, market and i18n do not bloat the generated code.

## 3. Speed: J techniques to take

These are ported behind the existing gate: byte-identical sha256 over the corpus (native + wasm), bench, EFT and
formats. All of them come from `variant-j/DESIGN.md`. Measured J gains are given where J documents them.

| # | technique (J) | F status | expected | effort |
|---|---|---|---|---|
| J1 | in-place capsim reschedule (one sift-down) | **done** 6e2ebf1 (−9.8 % Ir) | – | – |
| J2 | `exp(dt/τ)` memo | **done** f5b709f (−5.1 %) | – | – |
| J3 | stricter skill pruning: instantiate a skill only if one of its modifiers can reach another item or a fit item requires it, via an inverted relevance index | F has P5 (fold pre-filter) planned | J: −19 % rifter, −16 % corpus | 1 d |
| J4 | lazy base fill: attribute slots created without a value, filled on first read, one probe finds and inserts | F has a dense table for ship/char (P1) and a type-attr cache (P12) | −3…−6 % | 1 d |
| J5 | generation-stamped per-worker fit arena (bump the generation instead of clearing) | F has P3 thread-local scratch (partial) | J: −2.5 % | 0.5 d |
| J6 | streaming JSON writer with keys pre-sorted at build time + fast fixed-point six-decimal formatter (proven equal to shortest round-trip on 1e-5 ≤ \|v\| < 1e9) | F has P2a/P13/P14 (partial) | −5…−10 % of serialise | 1–2 d |
| J7 | batch pipeline: reader / N workers / ordered writer, a single request computed inline, flush when caught up | F batch threads (check inline path) | latency on loaded box | 0.5 d |
| J8 | static linking + no per-process precompute (cold start) | F compiles data in, so it is already near zero | small | 0.25 d |
| – | J's mmapped dataset image | not needed: F compiles the data in. Use the idea only for `eve-sde` runtime data on native. | – | – |

Target: reach parity with J (≤1069 k instr/fit corpus average) without changing a single output byte. Priority is
**below** feature completion: speed work happens only in gaps between the P0 tasks.

## 4. Gaps by priority (from docs/19), with effort

Efforts are bot-days (d) for the implementing bot, including oracle cases and tests. Every task closes the listed
docs/19 IDs and must add tests that map to them (§5).

### P0 — engine feature completion + skill-based optimizer (top priority)

| # | task | docs/19 ids | owner | effort |
|---|---|---|---|---|
| P0-1 | Create the workspace (§2) by splitting F into crates without changing behaviour (sha256 gate). Merge `variant-f-features` (breacher, slot rule, void bomb) and `graphs-g4` into it. | ENG-MOD-012, ENG-IMP-004, ENG-PROJ-007, ENG-CAP-005, all GRF-* (F → have) | F's bot | 2–3 d |
| P0-2 | Effect-coverage suite. eve3 generates one Pyfa-oracle micro-fit per used effect (2378: 2266 modifierInfo + 112 handler-only), checks the full modified-attribute dump, and fixes the misses. | ENG-CORE-003, ENG-MISC-002..005 | eve3 (suite 2 d), F's bot (fixes 3–5 d) | 5–7 d |
| P0-3 | Missing stats: mining yield (modules + drones, residue), outgoing RR/cap with spool, drone and fighter EHP/regen, bombing, spool min/max pair, lock-time table per class, special holds, missile range-chance pair | ENG-OFF-005/006/007, ENG-PROJ-006, ENG-DRN-002/003, ENG-FTR-004, ENG-TGT-002/006, ENG-MOD-010, UI-STAT-FP/OUT/MIN/BMB/TGT | F's bot; eve3 oracle suites | 4–5 d |
| P0-4 | Heat model (heat generation, damage, burnout estimate) | ENG-MOD-007 | F's bot | 2–3 d |
| P0-5 | **Skill-based optimizer** (`eve-optimizer`): goals (dps, ehp, cap stable, speed, applied dps vs profile, price) × hard constraints (resources, slots, restrictions, **the given character's trained skills / alpha caps**, budget) × the search space (market variations, charges, drones, rigs). It uses batched engine calls and returns ranked fits with deltas and missing-skill lists. MCP `optimize_fit` and web call it through `eve-rpc optimize`. | beyond Pyfa (Pyfa only has Optimize Fit Price, PRC-004); needs ENG-MOD-013, CHR-* | F's bot (core), eve4 (MCP/web wiring) | 4–6 d + 1–2 d |
| P0-6 | Character model: alpha clone caps, character implants vs fit implants, EVEMon/XML import, skill-plan export, SP/train time; a stable character/skill input format for ESI clients | ENG-CORE-009, ENG-IMP-002, CHR-004/005/006/009, CHR-002 | F's bot; eve4 (pipeline data) | 3 d |
| P0-7 | Modifier tracing behind feature `trace` (Affected by, dependants, skill affectors), zero cost when off | ENG-CORE-007/008 | F's bot | 2–3 d |

### P1 — data, formats, API

| # | task | docs/19 ids | owner | effort |
|---|---|---|---|---|
| P1-1 | Built-in damage/target profiles and implant sets (saved and precalculated) in `eve-profiles` | PRF-*, ENG-IMP-005, DB-008 | eve4 (pipeline), F's bot (crate) | 1 d |
| P1-2 | Formats: EFS, standalone muta text, HTML export, additions export/import, file/folder and multi-fit import, EFT export options, conversions | FMT-EFS/MUTA/HTML/ADD/AUTO/EFT-003, SVC-005 | F's bot; eve3 extends formats-suite | 3 d |
| P1-3 | `eve-sde` market: tree, variations / meta swap, jargon, item compare data, all Pyfa locales | MKT-*, ENG-MOD-013 | eve4 | 2–3 d |
| P1-4 | `eve-wasm` typed bindings + `.d.ts`, batch calls; incremental edit API and multi-fit context in `eve-fit-model` | (API) DB-004, MPF F1–F3 | F's bot; eve4 consumes | 3–4 d |
| P1-5 | `eve-prices`: sources (ESI, fuzzwork, evetycoon, …) and system choice, cache, totals, price column, Optimize Fit Price | PRC-* | eve4 | 2–3 d |
| P1-6 | `eve-store`: fit library, profiles, characters, backup/restore (JSON + XML), Pyfa saveddata import | DB-* | eve4 or F's bot | 3 d |
| P1-7 | MCP: `graph`, `price`, `market` tools; dedicated tests for passthrough features (mutations, overrides, projected, fleet, env, fighters) | MCP column partials | eve4 | 2 d |

### P2 — front-end parity and later items

| # | task | docs/19 ids | owner | effort |
|---|---|---|---|---|
| P2-1 | Web UI parity: view columns, stat-view modes, prefs, compare window, variations, multi-fit graph overlay + target fits, ECM-burst graph, full zh UI, e2e for every item | UI-*, GRF-UI-001, GRF-ECM-001, GRF-OPT-* (web) | eve4 | 5–8 d |
| P2-2 | **ESI login, skill/character fetch, ESI fittings browse/upload/delete**: web frontend, later | CHR-003, ESI-001..003, UI-PREF-ESI | eve4 (later) | 3–4 d |
| P2-3 | J speed techniques J3–J8 (§3) | – | F's bot (in gaps) | 3–5 d |

**Total, rough estimate:**
- F's bot: ≈ 25–35 d of P0/P1 engine work.
- eve4: ≈ 15–20 d.
- eve3: suites, ≈ 8–10 d (parallel).

## 5. Test strategy: no feature less than Pyfa

### 5.1 Inventory → tests (the gate)

- Each docs/19 item gets a `tests:` list in the YAML, in the form `suite:case-or-test-name` (e.g.
  `bench:breacher_kestrel`, `cap:in_void_bomb`, `web-e2e:"fleet buff …"`, `mcp:"compare_fits builds a delta table"`,
  `unit:eve-stats::mining::rorqual`).
- `tools/check_inventory.py` (new, coordinator) runs in eve-fit-docs CI and in the mainline CI. It fails when any of
  these holds:
  - an item is `have` without at least one test per column that is `have`;
  - a cited test does not exist;
  - a release candidate still has a Pyfa item `missing` or `partial` without an explicit user-approved deferral
    (`deferred: <ruling>`).
- **The release gate for "Pyfa parity 1.0" is zero `missing` in the F column** (n/a only by ruling), and zero
  `missing` in WEB for UI items not marked later.
- New Pyfa releases: on each Pyfa tag, eve3 re-walks the diff (gui/, service/, eos/, graphs/) and adds items. Removed
  Pyfa items keep their ID, marked `dropped`.

### 5.2 Oracles and suites

Pyfa v2.69.0 is run as a black box (venv + `eos` / `service/port` scripted by eve3). Existing suites stay as
regression gates:
- bench 1.9.0
- cap-suite
- mutated-suite
- formats-suite
- graphs-round2
- pending-1.10 fuzz

New suites, each generated from Pyfa outputs with deterministic seeds:

| suite | covers | size |
|---|---|---|
| effect-suite | every used effect (2378): one micro-fit each, full attribute dump | ≈2.4 k |
| stats-ext | mining, outgoing RR/cap, drone/fighter EHP/regen, bombing, lock-time table, holds, spool min/max, missile range pair | ≈150 |
| heat-suite | heat damage / burnout | ≈30 |
| character-suite | alpha caps, character implants, EVEMon/XML import, skill-plan export, train time | ≈50 |
| formats-suite v2 | EFS, muta text, HTML, additions, conversions | +≈300 |
| trace-suite | Affected-by lists vs Pyfa `itemAffectedBy` for sample fits | ≈50 |
| graph-options | every graph input/checkbox (GRF-OPT-*) | +≈100 |

**Fuzz:** the differential fuzzer (F vs Pyfa, pending-1.10 style) runs nightly. Each new mismatch becomes an
`e_fz_*` case.

### 5.3 Engineering gates per PR

- `cargo test`, then native + wasm (wasip1 and wasm-bindgen).
- Byte-identical sha256 over the corpus for pure refactors and perf work.
- Every suite at ≥ its last score; no regression is allowed.
- `check_inventory.py`.
- Web e2e on the `eve-wasm` backend.
- MCP integration tests against `eve-cli serve-stdio`.

### 5.4 Optimizer tests

- Property tests: every returned fit is valid for the given character (no untrained skills, within resources), and
  its stats are re-verified by `calc`.
- Regression goals on a fixed corpus (best dps under constraints never gets worse between releases).
- Skill sensitivity: All 0 / custom / All 5 give monotonic results.

## 6. Division of work (proposal)

| bot | role | first tasks (in order) |
|---|---|---|
| **F's bot** | mainline engine owner | P0-1 workspace split + merges → P0-3 missing stats → P0-5 optimizer core → P0-6 character → P0-7 trace → P0-4 heat → P1-2 formats → P1-4 wasm bindings/API; J techniques only in gaps |
| **eve3** | evaluation / bench / oracle | P0-2 effect-suite (first, so P0-1's fix list is known early) → stats-ext, heat, character, trace, formats v2, graph-options suites → nightly fuzz → keeps docs/19 `tests:` in sync, re-walks Pyfa on each release |
| **eve4** | web, MCP, SDE pipeline | pipeline outputs (alpha caps, SP/attributes, conversions, market tree, locales, presets) → P1-1 / P1-3 / P1-5 → MCP P1-7 + optimizer wiring → web switch to `eve-wasm` + P2-1 parity → **P2-2 ESI login (later)** |
| **coordinator (eve)** | scope + gates | owns docs/19/20, `check_inventory.py` + CI, reviews/merges, rulings on n/a / deferrals, weekly coverage counts |

**Sequencing:**
1. Week 1: P0-1, P0-2 and the pipeline outputs, in parallel.
2. Then P0-3, P0-5 and P0-6.
3. Then P0-7, P0-4 and P1.
4. P2 last.

Each milestone is published as docs/19 counts (have/partial/missing per column).

## 7. Open decisions for the user

1. Mainline repo name/location: new `EX-CT/eve-fit-core`, or a new major version in `EX-CT/eve-dogma`.
2. Release gate wording: is "zero F-column `missing`" the Pyfa-parity 1.0 bar, with web parity tracked separately?
3. Whether `eve-store` (persistence, Pyfa saveddata import) is in scope for 1.0, or follows the web library.
4. The optimizer's goal list and the default search space (market variations only, or also all fitting-compatible
   types).
