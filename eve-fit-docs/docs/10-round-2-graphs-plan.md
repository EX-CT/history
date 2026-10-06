# 10 — Round 2 plan: graphs (four implementation approaches)

> **Status: DRAFT.** Contract and corpus live on the bench branch
> [`EX-CT/eve-dogma-bench@graphs-round2`](https://github.com/EX-CT/eve-dogma-bench/tree/graphs-round2/graphs):
> `graphs/CONTRACT-GRAPHS.md` (revision 0.1), 100 Pyfa-verified graph cases with 1 649 scored sample values,
> scorer `graphs/run_graphs.py`. Round 1 (stats, bench 1.8.0) is unaffected.
>
> 中文摘要：第二轮实现 Pyfa 的全部 9 种图表（伤害/应用/电战/遥修/电容/护盾回充/机动/跃迁时间/锁定时间）。
> 契约采用「显式采样点 + SI 单位 + 每点独立」，期望值由 Pyfa 自身的 graph getter 生成。本文给出四种可由不同 worker
> 独立实现的架构方案（Pyfa 忠实移植、两阶段「图元导出 + 可移植求值器」、向量化网格引擎、声明式图表 DSL），
> 说明各自取舍、如何接入契约与基准测试，以及评测方式。

## 1. Scope

Pyfa's graph window (`graphs/data/*`) offers nine public graphs. All nine are in the contract draft:

| graph | x axes | y series | Pyfa package |
|---|---|---|---|
| `damage` | distance, time, target speed, target signature | dps, volley, damage inflicted | `fitDamageStats` |
| `application_profile` | distance | best-ammo dps / volley (+ chosen charge) | `fitApplicationProfile` |
| `ewar` | distance | neut GJ/s, web %, ECM strength, damp %, TD %, GD %, TP % | `fitEwarStats` |
| `remote_reps` | distance, time | rep/s, total repaired | `fitRemoteReps` |
| `capacitor` | time, cap % | cap GJ (capsim), regen GJ/s | `fitCapacitor` |
| `shield_regen` | time, shield % | shield HP/EHP, regen | `fitShieldRegen` |
| `mobility` | time | speed, distance, momentum, bump speed/distance | `fitMobility` |
| `warp_time` | distance | warp time | `fitWarpTime` |
| `lock_time` | target signature | lock time | `fitLockTime` |

Contract essentials (details in CONTRACT-GRAPHS.md):
- `GraphRequest = {graph, fit: FitRequest, target?, x: {axis, values[]}, y[], params?, settings?}` →
  `GraphResult = {graph, x_axis, x[], series: {y: [values]}}`; CLI `graph` / `graph-batch`, RPC method `graph`.
- **Explicit sample points** (Pyfa `getPoint`), not Pyfa's adaptive plot sampling; **SI units**; **points are
  independent**; `null` outside a graph's valid range or where Pyfa returns None.
- The hard parts are not the closed-form curves (cap/shield regen, mobility, warp, lock time are a few lines each)
  but: the **damage time cache** (cycle-by-cycle schedule with spool-by-cycles, forced reloads, breacher offsets),
  **turret/drone/missile application** with transversal geometry and drone movement modes, **projected
  webs/TPs re-applied to target fits** through stacking-penalised "extended" attributes, **capsim history** for the
  capacitor-vs-time curve, and **valid-charge enumeration** for the application profile.

## 2. Common rules for all four approaches

- Same dataset (`dataset-3569502.json.gz`), same FitRequest semantics as round 1 (a graph's source fit must give the
  round-1 stats first), GPL-compatible licensing as in round 1.
- Plug-in: a variant's `bench.yaml` adds `graph_batch_cmd:` (preferred, JSONL) and/or `graph_cmd:`, or implements
  method `graph` on `rpc_cmd`. Scoring: `python3 graphs/run_graphs.py --name X --batch-cmd …` (tolerance
  max(1e-3, 1e-4·|v|), `null` must match).
- Correctness gate: 100 % of scored sample values (1 649) plus the 1.8.0 stats corpus still at 100 %.
- Perf metrics for graphs (proposal): (a) **points/s** over the whole graph corpus in batch mode, (b) latency of one
  dense interactive request (`damage`, distance axis, 500 points), (c) cold start + one request.
- Each worker writes `DESIGN.md` (architecture, Pyfa mapping) and keeps a scorecard in its own `bench/` dir.

## 3. Approach G1 — Pyfa-faithful graph port inside the engine

**Architecture.** Port Pyfa's `graphs/data/*` one-to-one into the Rust engine next to the stats code: a `graphs/`
module with one file per graph, getter structs mirroring Pyfa's mixins (`XDistanceMixin` × `YDpsMixin`, …), a port
of `TimeCache` (damage/RR schedules), `ProjectedDataCache`, `SubwarpSpeedCache`, and an extended-attribute API
(`get_modified_extended(attr, extra_multipliers, ignore_afflictors)`) on the existing modified-attribute map. A graph
request runs one `calc` of the source (and target) fit, then evaluates every x with the same getter code path.

**Trade-offs.** + Highest chance of exact parity (same control flow, same `floatUnerr` points); + reviewable
line-by-line against Pyfa; + reuses the round-1 engine (any variant that ported Pyfa's stats closely). − Inherits
Pyfa's per-point recomputation (e.g. web/TP application per x); − some code duplication across getters; − the
extended-attribute API touches the engine core (stacking-penalised re-evaluation with extra multipliers).

**Contract/bench.** `graph` / `graph-batch` subcommands and the `graph` RPC method of the same binary; scored
directly with `run_graphs.py --batch-cmd`. Natural owner: a worker who built a Pyfa-faithful round-1 variant.

**Risks.** Time-cache edge cases (breachers, fighters' per-ability cycles, doomsday sub-cycles), capsim history
(the simulator must record every event, not only the summary), charge enumeration for the application profile
(needs market-group and meta data in the dataset).

## 4. Approach G2 — two-stage: graph primitives + portable evaluator

**Architecture.** Split the work at a clean boundary:
1. The engine (any round-1 engine) emits **graph primitives** once per fit: per damage dealer
   `{kind, dps, volley, optimal, falloff, tracking, optimalSigRadius, eR, eV, drf, missile range data, cycle
   schedule (list of (t, volley) events up to t_max), needs_lock, needs_dcr}`, the source's webs/TPs with
   resistance attribute ids, capsim event history, warp/subwarp/agility/scan figures, RR modules, EWAR sources.
2. A small, dependency-free **evaluator library** (Rust core compiled to native + WASM, optionally a TypeScript twin)
   computes any graph point from the primitives: application formulas, transversal geometry, range factors,
   cumulative damage, closed-form curves. Target-fit re-application of webs/TPs needs the target's stacking
   inputs, which the engine also exports (`speed_inputs`: base value + modifier list per stacking group).

**Trade-offs.** + Interactive UIs re-evaluate thousands of points in the browser without the engine (sliders for
distance/speed/angle are instant); + primitives are cacheable and diffable (great for MCP "why is my DPS low at
30 km?" explanations); + the evaluator is tiny and testable in isolation. − A second schema (primitives) to
version; − parity bugs can hide in the split (e.g. when Pyfa recomputes the fit, as for subwarp speed); − target-fit
stacking needs exporting modifier lists, which is more invasive than it looks.

**Contract/bench.** The public contract stays `GraphRequest → GraphResult`; the variant's `graph-batch` command
internally runs engine → primitives → evaluator. Additional (informational) bench output: the primitives JSON size
and an evaluator-only points/s figure (`--eval-only` replay of cached primitives).

**Risks.** Keeping primitives complete enough for all nine graphs; WASM/TS twin drift (mitigation: the TS twin is
scored by the same corpus through a Node `graph-batch` shim).

## 5. Approach G3 — vectorised grid engine (throughput first)

**Architecture.** Treat every graph as a function over a grid. After one `calc`, the engine builds
struct-of-arrays tables (one row per damage dealer / EWAR source / RR module) and evaluates all x values of a request
in tight loops (SIMD-friendly: `exp`, `powf`, `asinh` vectorised; branch-free range factors). Fit results are
memoised by a canonical hash of the FitRequest so that changing only the graph axis or target re-uses the fit
(batch requests over the same fit become nearly free). Optional extension beyond Pyfa: 2-D grids
(distance × target speed heat-maps) using the same kernels, exposed as an extra `x2` axis that the scorer ignores.

**Trade-offs.** + Highest points/s (targets: ≥ 10 M points/s for closed-form graphs, ≥ 1 M for damage vs distance);
+ cache-by-fit-hash fits the MCP/HTTP use case (many what-if queries per fit); − vectorised math must reproduce
Python's libm results within tolerance (fine for the 1e-4 tolerance, but not bit-exact); − time-axis damage and
capsim are inherently sequential, so the speed-up concentrates on distance/speed/signature axes; − more complex
code than G1.

**Contract/bench.** `graph-batch` with an in-process fit cache; perf measured by the proposed points/s and dense
interactive request metrics. The memo must be keyed by the full FitRequest + dataset so determinism holds.

**Risks.** Precision drift in vectorised transcendental functions; cache invalidation bugs (mitigation: canonical
JSON hashing, cache disabled under `--no-cache` and a bench run in both modes must give identical output).

## 6. Approach G4 — declarative graph specs (data-driven graphs)

**Architecture.** Graphs are data, not code: a versioned spec file (`graphs.yaml`) declares each graph's axes,
units, limiters, parameters, defaults and its formula as an expression tree over named **engine observables**
(e.g. `ship.maxVelocity`, `module[i].trackingSpeed`, `dealer[*].volley`, `capsim.history`) plus a small library of
named kernels (`range_factor`, `turret_cth`, `missile_factor`, `stack_penalised`, `time_schedule`). A generic
interpreter in the engine evaluates a spec for a GraphRequest; the same spec renders documentation tables and the
GUI's axis/param pickers, and MCP tools can list graphs and their parameters from it.

**Trade-offs.** + Adding a graph (or a Pyfa change) is a spec edit; + self-describing API (the MCP server can offer
"plot X vs Y" for any declared pair); + contract docs generated from the same source cannot drift; − an interpreter
is slower than G1/G3 code (mitigate with compile-once expression bytecode); − the hard parts (time cache, capsim,
charge enumeration, webs re-applied to target fits) still end up as hand-written kernels, so the DSL covers the
"easy 60 %" elegantly and the rest via escape hatches; − more design work up front.

**Contract/bench.** Same `graph` / `graph-batch` interface; additionally `graph-specs` (RPC `graph_specs`) returning
the spec catalogue, which the bench can check for consistency with CONTRACT-GRAPHS.md (axes/series names, units).

**Risks.** Over-engineering; kernel boundaries chosen badly. Mitigation: start from G1-style kernels for the hard
parts and keep the DSL to composition and units.

## 7. Comparison

| | G1 Pyfa port | G2 primitives + evaluator | G3 vectorised grid | G4 declarative specs |
|---|---|---|---|---|
| Parity risk | lowest | medium (split) | medium (math precision) | medium (kernels) |
| Points/s | baseline | high in evaluator | highest | lowest (interpreted) |
| Browser / WASM | via engine WASM | **native fit** (tiny evaluator) | via engine WASM | via engine WASM |
| AI / MCP fit | good | **best explanations** | good for what-if loops | **best discoverability** |
| New graph cost | code per graph | code in evaluator | code + kernels | spec edit (+kernel) |
| Engine invasiveness | extended attrs | primitives export | fit cache | observables registry |

Recommended assignment: one worker per approach, all starting from the round-1 winner's engine (or from their own
round-1 variant if the winner is not ready), each on its own branch of `EX-CT/eve-dogma-lab` (`graphs-g1` …
`graphs-g4`, directory `graphs-gN/`), scored with the same corpus. Expected outcome: G1 or G3 as the shipped
engine path, G2's evaluator for the web UI, and G4's spec catalogue as the source of the MCP/GUI graph menus.

## 8. Evaluation for round 2

1. Gate (confirmed 2026-10-03, see [13](13-engine-round-2-evaluation.md)): 0.2 全部用例 — all 178 cases of graph
   contract 0.2 @ `0397d95` (incl. `ecm_burst` and the error cases) — plus the 1.8.0 stats corpus 326/326.
2. Score (proposal, same spirit as round 1): speed 40 % (points/s batch, dense interactive latency, cold start),
   maintainability 35 %, feature coverage 15 % (0.2 全部用例 / all contract 0.2 cases, optional extras such as 2-D grids or spec
   catalogue), portability 10 % (WASM/browser evaluator).
3. Corpus growth before scoring: more fighter / bomb / breacher / vorton cases, target fits with MWD + source scram,
   drone movement modes, ECM bursts, Standup weapons, and `%`-axis convenience checks.

## 9. Open questions for the coordinator

- Freeze CONTRACT-GRAPHS.md at revision 1.0 before workers start (names of axes/series, SI units, null rules).
- Should `%`-of-target axes (Pyfa's default x for target speed/signature) be part of the contract, or GUI-only?
- Application profile: accept any charge among exact-DPS ties (needs the oracle to export the tie set), or keep
  charge ids informational as in the draft?
- Do we want Pyfa's adaptive `getRange` curves as an optional, unscored `sampling: "pyfa"` mode for GUI parity?
