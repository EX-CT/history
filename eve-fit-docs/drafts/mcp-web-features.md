# Draft: feature inventory of eve-fit-mcp and eve-fit-web (for docs/19)

> Draft by eve4, 2026-10-03 ~11:30 CST, for eve to merge into docs/19. It lists what the two front-ends **already
> have**, sorted by Pyfa feature area. Every item cites evidence: MCP tool, resource or prompt names; web files and
> components; test names; e2e check names; CI runs.
>
> **Status:** **full** = works end to end and is covered by a test or e2e check. **partial** = works but is limited, or
> has no automated check. **—** = absent. Gaps are listed per area. Neither front-end has hard-coded engine logic.
> Every number comes from the engine contract (`calc(FitRequest) → FitStats`, eve-fit-docs docs/05). The web UI's
> approximation graphs are the only exception.
>
> 中文摘要：按 Pyfa 功能区列出 MCP 与网页**已有**的功能，每项附证据（工具名、文件/组件、测试名、e2e 检查名、CI 运行）并标注 full/partial，最后列出已知缺口。

## Evidence base (as of this draft)

**eve-fit-mcp** (main `f223517`)
- 18 tools, 9 resources (3 of them templates) and 4 prompts, all in `src/server.ts`. Tests are in `src/test/`:
  `unit.test.ts`, `integration.test.ts` and `adapters.test.ts`. The integration and adapter tests spawn the real
  engine on the real dataset; they ran locally 37/37 with `EVE_FIT_DEV_ROOT`. CI runs the unit tests and a schema
  drift check.
- CI is green: https://github.com/EX-CT/eve-fit-mcp/actions/runs/37083602797
- Release v0.1.0: https://github.com/EX-CT/eve-fit-mcp/releases/tag/v0.1.0
- Engine adapters (`src/adapters`): `rpc` (serve-stdio worker pool), `cli` and `http`. Default engine: `eve-dogma` on
  `PATH` (eve-dogma-rs), unchanged.

**eve-fit-web** (main `4a4afd8`, live at https://ex-ct.github.io/eve-fit-web/)
- React UI: `src/ui/*.tsx`. Fit model and formats: `src/fit/*.ts`. Data: `src/data/*.ts`. Engines:
  `src/engine/adapter.ts` and `worker.ts`.
- **No unit tests.** Behaviour is covered by the headless-Chrome e2e `tools/e2e.mjs`, run on every backend in Pages CI:
  ts-worker 43/43, wasm-worker 43/43, wasm-g4-worker 50/50, wasm-j-worker 50/50, http 50/50. Plus
  `tools/smoke.mjs`, the bench 1.8.0 stats corpus in the browser (F and J both 326/326, 21051/21051 values), and the
  graphs 0.2 suite in the browser (g4 178/178, 2437/2437 values).
- CI is green: https://github.com/EX-CT/eve-fit-web/actions/runs/37092474451
- Default backend: `ts-worker` (unchanged). The F backends (`wasm-worker`, and `wasm-g4-worker` with graphs) and J
  (`wasm-j-worker`, an optional speed reference) can be selected in the header or with `?engine=`.

Below, "e2e: …" quotes a check name from `tools/e2e.mjs`, and "test: …" quotes an MCP test name.

## 1. Market / item search / show info

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Search by name, English + Chinese | `search_types` (exact > prefix > fuzzy, `name_zh`) — test: "search: exact, jargon, chinese, filters, fuzzy" | full | `ui/Market.tsx` search box, kind filters, zh names from `names_i18n` — e2e: "zh weapon names", "en weapon names restored" | full |
| Player jargon (`mwd`, `lse`, `dc`, `scram`, …) | `search_types` + resource `eve://jargon` | full | — | — |
| Filters: kind / slot / group / meta / tech / `fits_ship` | `search_types` | full | kind filter; meta level shown (`M{n}`) | partial |
| Market group tree | — (search only) | — | `ui/Market.tsx` tree from dataset market groups | partial (no e2e check of browsing) |
| Show info: attributes with units, effects, required skills, traits | `get_type`, resource `eve://type/{id}` — test: "get_type and get_ship" | full | Show-info dialog (attributes, bonus text, required skills) | full |
| Show info on a fitted item: engine-computed fitted values | `compute_fit detail:"full"` sections | partial | dialog with changed values highlighted — e2e: "show info: fitted attribute values" | full |
| Compatible charges / same-group items | `get_type` | full | charge picker filtered by group, size and capacity | partial |
| Ship layout (slots, hardpoints, rig size, resources) | `get_ship`, resources `eve://ship/{id}/layout` and `eve://ship/{id}/modules/{slot}` | full | fitting window header | full |

Gaps: no Pyfa "variations" or compare window in the web UI. The MCP has no market tree browsing.

## 2. Fitting: slots, states, charges

| feature | MCP | status | web | status |
|---|---|---|---|---|
| High/mid/low/rig/subsystem/service slots | FitRequest passthrough; `validate_fit` names slot violations — test: "validate_fit names modules and hints" | full | `ui/Fitting.tsx` with engine totals and empty slots — e2e: "no violations" | full |
| Module states offline/online/active/overheated | FitRequest `state`; `what_if` state changes — test: "what_if scenarios" | full | click / right-click cycles the state | partial (no dedicated e2e check) |
| Charges / ammo | names accepted (`"200mm AutoCannon II, EMP S"`); `suggest_charges` — test: "suggest_charges ranks ammo per weapon type" | full | charge picker — e2e: "weapon dps (charges)" | full |
| T3C subsystems, T3D modes | FitRequest `mode_type_id`, subsystems | partial (no dedicated test) | subsystem slots, mode selector | partial (no e2e check) |
| Mutated modules (abyssal) | FitRequest `mutation` (`schemas.ts`) | partial (no test) | mutaplasmid + per-attribute sliders; EFT mutated blocks — e2e: "mutated module imported", "mutated module EFT round trip" | full |
| Per-module spool-up (Triglavian, mutadaptive) | FitRequest `spool` | partial | per-module spool control — e2e: "per-module spool 0% lowers disintegrator dps" | full |
| Attribute overrides (Pyfa override editor) | FitRequest `overrides` (schema only) | partial | Show-info override editor — e2e: "attribute override raises weapon dps", "removing the override restores dps" | full |
| Validation: CPU/PG/calibration, slots, hardpoints, rig size, ship restrictions, skills | `validate_fit`; index `canFit` — test: "canFit: rig size and ship restrictions" | full | violations list in the stats panel | full |
| Undo / redo | — (stateless) | n/a | per fit, buttons + Ctrl+Z / Ctrl+Y — e2e: "undo / redo" | full |
| Fit notes | — | — | `notes` field (EFT comment export) | partial |
| Cargo | FitRequest `cargo`; DNA cargo | partial | cargo list, counted in the price | partial |

## 3. Drones and fighters

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Drones: quantity / active, bandwidth, bay, control range | FitRequest; `suggest_drones` — test: "suggest_drones respects bandwidth, bay and skills" | full | drone list — e2e: "drones dps" | full |
| Fighters: squadron size, launched, per-ability toggles | FitRequest `abilities` | partial (no fighter test) | Pyfa-default abilities — e2e: "fighter dps", "fighter abilities listed", "disabling an attack ability lowers fighter dps" | full |

## 4. Implants and boosters

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Implants (one per slot) | FitRequest; `what_if` | full | implant slots | full |
| Implant sets (pirate sets from the SDE, saved sets) | `implant_set` input; `list_presets`; resource `eve://presets` — tests: "implant sets", "damage / target profiles and implant sets apply" | full | implant-set picker (SDE sets + saved) — e2e: "implant set applied (6 Snake + kept RP-905, faster)" | full |
| Boosters with side effects (one at a time) | FitRequest `side_effects` | partial (no test) | e2e: "booster side effect lowers armor HP" | full |

## 5. Character and skills

| feature | MCP | status | web | status |
|---|---|---|---|---|
| All 5 / All 4 / All 0 and custom per-skill levels | `skills` input (`0–5`, `all_4`, `{default_level, levels}`; default all V) — test: "skills change the numbers; all_0 is weaker" | full | `ui/Character.tsx` — e2e: "custom character (all 0) lowers dps" | full |
| Required / missing skills incl. prerequisites | `skill_requirements` — tests: "skill_requirements and presets", "skill tree includes prerequisites" | full | required/missing list + "train required" — e2e: "missing skills reported" | full |
| Security status | FitRequest `character.security_status` | partial | Character page | partial |

Gap in both: no ESI/SSO character import, so skills are entered by hand.

## 6. Stats panel

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Resources (CPU, PG, calibration, bandwidth, bays, tubes, hardpoints) | `compute_fit` summary metrics — test: "compute_fit from EFT: summary with metrics" | full | `ui/Stats.tsx` | full |
| Offense: DPS / volley per weapon and damage type, vs target | `compute_fit`, metric keys in `eve://metrics` | full | per-weapon table (zh names) — e2e: "weapon dps (charges)", "drones dps" | full |
| Defense: HP, resists, EHP, raw / effective / sustained tank | `compute_fit detail:"full"` — test: "full detail with sections" | full | e2e: "armor tank" | full |
| Capacitor: stability, delta, injectors, cap sim | `compute_fit` (`cap_sim` options) | full | capacitor block | full |
| Navigation, targeting (lock time, jam chance), drones | `compute_fit` | full | blocks in `Stats.tsx` | full |
| Engine warnings / violations | `compute_fit`, `validate_fit` | full | stats panel | full |
| Options: factor reload, default spool, RAH adapt / disable | FitRequest `options` | full | options tab | partial (no e2e check) |
| Compare several fits | `compare_fits` (2–20 fits, deltas, best per metric) — test: "compare_fits builds a delta table" | full | — | — |
| What-if, suggestions, optimiser | `what_if`, `suggest_modules`, `suggest_charges`, `suggest_drones`, `optimize_fit` (with progress) — tests: "suggest_modules ranks by goal and respects constraints", "optimize_fit improves a goal within budget", "optimize_fit sends progress notifications when asked" | full | — | — |

## 7. Damage patterns and target profiles

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Built-in + NPC (SDE) damage patterns, custom | `damage_profile` input; `list_presets`; `evaluate_profiles` | full | `ui/Profiles.tsx`, SDE NPC profiles (`data/sdePresets.ts`) — e2e: "SDE NPC damage profile (Guristas) changes EHP" | full |
| Target profiles (sig, speed, radius, resists) | `target_profile` input; `evaluate_profiles` (frigate…structure) | full | target profiles feed DPS vs target and the graphs | full |

## 8. Projected, fleet and environment

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Projected modules / drones / fighters with amount + distance | FitRequest `projected` (passthrough, `fit.ts`) | partial (no dedicated test) | `ui/Fitting.tsx` "Projected" tab — e2e: "projected web slows the ship" | full |
| Projected saved fits | FitRequest `projected[kind=fit]` | partial | nested `toRequest` (`fit/model.ts`) | partial (no e2e check) |
| Fleet booster fits (command bursts) | FitRequest `fleet.booster_fits` | partial | booster-fit picker | partial (no e2e check) |
| Manual warfare buffs | FitRequest `fleet.buffs` | partial | buff editor — e2e: "manual fleet buff raises shield resist (lower resonance)" | full |
| System effects / beacons, system security | FitRequest `environment` | partial | beacon selector — e2e: "environment beacon applied" | full |

## 9. Graphs

| feature | MCP | status | web | status |
|---|---|---|---|---|
| DPS vs range, capacitor vs time, regen vs fill %, speed and distance vs time, lock time, warp time | `sweep` (metrics vs target signature / velocity / skill level / projected distance) — test: "sweep gives graph series" | partial (series from stats, not the graph contract) | `ui/Graphs.tsx`. Engine-computed on `wasm-g4-worker` (and `wasm-j-worker` through `GRAPH_FALLBACK`); UI approximations (`fit/graphs.ts`) on other backends — e2e: "graph dps (engine)" … "graph warp (engine)", "engine lock-time graph matches stats", "graph backend label" | full on g4; partial elsewhere |
| Application profile (best ammo), EWAR, remote repairs | — | — | engine-only graphs, offered when `graph_specs` lists them — e2e: "graph app/ewar/rr (engine)", "engine ewar graph has web + neut" | full on g4 |
| Graph contract 0.2 conformance in the browser | — | — | `tools/browser-rpc.mjs` + bench `run_graphs.py`: 178/178 (CI) | full |

Gaps:
- The MCP has no graph-contract tool (`graph` / `graph_specs`). An `engine_graph` tool is a small step once the
  mainline engine ships the graph RPC.
- The web graphs have no multi-fit overlay, target fits, or Pyfa's per-graph extra inputs (ecm_burst, time axis for
  damage).

## 10. Import / export formats

| format | MCP | status | web | status |
|---|---|---|---|---|
| EFT import (incl. mutated blocks) | `parse_fit` — test: "EFT, DNA and lenient JSON give the same numbers" | full | `ui/ImportExport.tsx`, `fit/formats.ts`, `?eft=` link — e2e: "EFT import via ?eft=, ship", "mutated module imported" | full |
| EFT export (Pyfa-exact from the engine) | `export_fit` — test: "export EFT round-trips" | full | e2e: "EFT export", "mutated module EFT round trip" | full |
| DNA import / export | `parse_fit` / `export_fit` — test: "DNA round trip with charges loaded" | full | `?dna=` link — e2e: "DNA export" | full |
| ESI fitting JSON | lenient JSON in `parse_fit`; `export_fit` JSON | partial | import + export — e2e: "ESI JSON export", "ESI JSON re-import" | full |
| Multibuy | `export_fit` | full | export — e2e: "multibuy export" | full |
| Several EFT fits at once | — | — | e2e: "multi-fit EFT import + fit browser groups" | full |
| EVE XML fittings, Pyfa database / `.pyfa` backup, clipboard watch | — | — | — | — |

## 11. Fit library

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Saved fits grouped by ship group, search | — (stateless; the client keeps fits) | n/a | `ui/FitBrowser.tsx`, `store.ts` (localStorage) — e2e: "multi-fit EFT import + fit browser groups", "fit browser search" | full |
| Duplicate / delete, JSON backup / restore of the whole library | — | n/a | FitBrowser | partial (no e2e check) |

Gaps: no cloud or ESI sync of fits. No tags or folders beyond ship groups.

## 12. Prices

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Fit value (ship, modules incl. charges and mutaplasmids, drones / fighters, implants / boosters, cargo) | — | — | `data/prices.ts` (public ESI market prices, opt-in, 6 h cache), `ui/PriceBox.tsx` — e2e: "fit price from ESI" | full |

Gap: there are no prices in the MCP. Only the ESI average price is used (no Jita buy/sell split).

## 13. Language (i18n)

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Chinese item names | search and results carry `name_zh` | full | dataset `names_i18n`; the zh switch covers item names and main UI labels (`src/i18n.ts`) — e2e: "zh weapon names" | partial (not every UI string is translated) |

## 14. Engine, platform and other

| feature | MCP | status | web | status |
|---|---|---|---|---|
| Swappable engine | `rpc` / `cli` / `http` adapters, `EVE_DOGMA_BIN`, `engine_info` — tests: "cli adapter (spawn per call) gives identical numbers", "worker pool (EVE_FIT_WORKERS=3)", "variant C (Go) serve-stdio through EVE_FIT_RPC_CMD", "http adapter against variant C serve-http", "bad engine binary gives an actionable error, not a hang" | full | `src/engine/adapter.ts`: `ts-worker`, `wasm-worker` (F), `wasm-g4-worker` (F + graphs), `wasm-j-worker` (J, optional), `http` (`tools/engine-bridge.mjs`); pinned in `engines.lock` | full |
| Transports / hosting | stdio + Streamable HTTP (`--http`, DNS-rebinding protection) — test: "Streamable HTTP transport" | full | static GitHub Pages; the About tab shows engine, dataset and build commits — e2e: "about page: backend, engine, dataset, links", "about page: graph engine" | full |
| Agent workflow aids | prompts `fit_for_role`, `review_fit`, `explain_stat`, `compare_options`; resource `eve://guide/fitting` — test: "resources and prompts" | full | — | n/a |
| Dataset / schema resources | `eve://dataset/meta`, `eve://schema/fit-request`, `eve://schema/fit-stats` | full | dataset from the eve-sde-pipeline release, shown on About | full |

## Known gaps (summary for docs/19)

1. **The MCP has no graph-contract tool** (see §9). It also has no prices and no market tree.
2. **Web:**
   - no compare window, variations window, what-if or optimiser (those exist only in the MCP)
   - no multi-fit graph overlay or graph target fits
   - partial zh UI
   - no unit tests (e2e only)
   - no e2e checks for module-state cycling, T3D modes or subsystems, fleet booster fits, projected saved fits, library
     backup / restore, or options
3. **Both:**
   - no ESI SSO (characters, skills, fits)
   - no EVE XML or Pyfa-database import
   - several FitRequest features (mutations, overrides, projected, fleet, environment, fighters) have no dedicated MCP
     integration test; they are covered only by the web e2e checks on the same engines.
4. **Engine choice:** both front-ends still default to their current engines (web `ts-worker`, MCP `eve-dogma` =
   eve-dogma-rs). The switch to the Rust mainline based on F waits for the mainline repo. In the web UI, F
   (`wasm-worker`, `wasm-g4-worker`) can already be selected.
