# 09 — Engine round 1 evaluation (variants A–K)

> **Status: RESULTS IN, DECISION PENDING.** Filled in from the official run (started 10:16, finished 10:46:56 CST,
> 2026-10-03; bench 1.8.0 pinned @ `3da9671`, = `0969967` cases) in `eve-dogma-bench/results/evaluation.{md,json}`
> (commit `579a21a`). §6 Decision is left for eve (coordinator); §7–§8 are drafts.
>
> 中文摘要：第一轮 11 个 dogma 引擎方案（A–K）的统一评测。正确性（bench 1.8.0 全部 326 个 case 与 Pyfa 一致）是门槛，
> 过门槛后按 速度 40%、可维护性 35%、功能覆盖 15%、可移植性 10% 计分。本文记录方法、规则、结果、决定与合并计划。

## 1. Goal

Eleven teams built the same stateless engine contract (`FitRequest` JSON → `FitStats` JSON, CONTRACT.md revision 1.4.3,
same dataset `dataset-3569502.json.gz`) with different languages and architectures. Round 1 decides which design (or
which combination of ideas) becomes the core of the EXCT toolkit (CLI, MCP server, web UI, WASM).

## 2. Method

All measurements come from one command in [EX-CT/eve-dogma-bench](https://github.com/EX-CT/eve-dogma-bench):

```bash
python3 tools/evaluate.py --as-of 2026-10-03T10:15:00+08:00 --runs 3 --fresh-clones   # results/evaluation.{md,json}
```

0. **Version rule:** every variant is evaluated at its branch HEAD as of **2026-10-03 10:15 CST** (last commit at or
   before the cutoff). Self-reported "final" versions are reference only. A commit that fails the correctness gate is
   **disqualified** for the round; there is no fallback to an older commit.
1. **Fetch** the head as of the cutoff for each variant: A = `EX-CT/eve-dogma-rs@main`; B–K = `EX-CT/eve-dogma-lab@variant-<x>`
   (directory `variant-<x>/`, commands from its `bench.yaml`). Full commit SHAs are recorded.
2. **Build** with the variant's own `build` command (time recorded; fresh clone ⇒ fresh build).
3. **Correctness + speed** with the official scorer (`run.py`, the same code `bench.py` uses) **pinned to bench 1.8.0
   (`3da9671`, 326 cases)** regardless of upstream main, 3 runs per variant,
   after one untimed warm-up batch; median of perf numbers, `loadavg` before/after every run. **Latency** is measured
   separately: batch command pinned to one CPU, (t_N − t_1)/(N − 1), ≥ 5 independent samples, median, with sanity
   checks (≤ 0, below a 2 µs floor, above t_N/N → invalid; spread > 50 % → re-measure, then flag). Variants run one at a time. Every child run has a hard
   timeout, so one broken variant cannot stall the evaluation.
4. **Features** through the variant's `serve-stdio` RPC: EFT export (Pyfa byte-exact check), `eft_parse` round-trip,
   `calc` over RPC equal to the CLI, `meta`, unknown-method error, `search` (interim spec) and `type` probes.
5. **Maintainability** from the source tree: LOC per language (core / test / tooling / generated / vendored), own test
   suite run and result, direct dependencies, docs (README / DESIGN / LICENSE), license, and a heuristic count of
   effects special-cased by name in hand-written code (per-effect hard-coding vs data-driven).
6. **Portability**: evidence of a WASM / browser build in code (1), only documented (0.5), none (0).

Caveat: the box is a shared 8-CPU machine that was under load (1-min loadavg 1.0–2.8 during the run; per-variant range in the last column of §5). Perf numbers are only
comparable within the same run; the log scale in the speed formula softens noise.

## 3. Scoring rules

- **Version:** branch HEAD as of 10:15 CST; failing head ⇒ disqualified (no fallback).
- **Gate:** a variant is ranked only if it builds, runs and passes **all 326 cases** (21 051 values) in every run.
- **Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability** (each sub-score in [0, 1]).
- `L(x, best, span) = clamp(1 − log10(x / best) / log10(span), 0, 1)` for lower-is-better `x`.
- **Bench pin:** 1.8.0 @ `3da9671` (326 cases, 21 051 values); bench SHA and case count recorded in the output.
- **Speed** = 0.5·L(single-CPU latency ms/calc, 100) + 0.3·L(1 / batch fits·s⁻¹, 100) + 0.2·L(cold start ms, 100).
- **Maintainability** = 0.25·Tests + 0.20·DataDriven + 0.20·Size + 0.15·Docs + 0.10·Deps + 0.10·Build
  (Tests: passing suite 0.6 + 0.4·min(1, log10(1+n)/2), failing 0.2, timeout 0.3, none 0; DataDriven: L(h+10, h_min+10, 10)
  with h = effects special-cased by name; Size: L(core LOC, min, 10); Docs: 0.4 README + 0.4 DESIGN + 0.2 LICENSE;
  Deps: 1/(1+n/5); Build: L(build s, best, 100), only when all builds are fresh, else dropped and weights renormalised).
- **Features** = mean(EFT, RPC, search, type).
- **Portability** = WASM/browser build in code 1 · documented only 0.5 · none 0.

The authoritative text is the docstring of `tools/evaluate.py`; if this section and the tool disagree, the tool wins.

## 4. Variants

| | Variant | Language | Core idea | Branch / commit | License | Mergeable into LGPL-3.0-or-later mainline |
|---|---|---|---|---|---|---|
| A | eve-dogma-rs (reference) | Rust | lazy memoised modifier graph | `main` @ 659737b | LGPL-3.0-or-later | yes (confirmed) |
| B | data-oriented | Rust | compile a flat CSR modifier graph, then evaluate | `variant-b` @ f56dd59 | LGPL-3.0-or-later | yes (confirmed) |
| C | Go | Go | pull-based modifier registry with selectors | `variant-c` @ d12ff1a | LGPL-3.0-or-later | yes (confirmed) |
| D | TypeScript | TypeScript | pull-based attribute graph + typed modifier pipeline | `variant-d` @ 5218e0d | LGPL-3.0-or-later | yes (confirmed) |
| E | Pyfa-faithful | Rust | Pyfa eos transpiled to Rust | `variant-e` @ 5867d53 | GPL-3.0-or-later | **no** (GPL LICENSE text, derived from Pyfa) (confirmed) |
| F | codegen | Rust (+WASM) | SDE compiled into Rust code at build time | `variant-f` @ bc84e2b | LGPL-3.0-or-later | yes (confirmed) |
| G | batch | Python + NumPy | vectorised dogma over many fits | `variant-g` @ a07402e | LGPL-3.0-or-later | yes (confirmed) |
| H | ECS | Rust (hecs) | entities/components/systems | `variant-h` @ b1c7852 | LGPL-3.0-or-later | yes (confirmed) |
| I | incremental | Rust (salsa) | memoised demand-driven query graph | `variant-i` @ ad9f73e | LGPL-3.0-or-later | yes (confirmed) |
| J | C++20 | C++20 | mmapped POD dataset image, flat attribute tables | `variant-j` @ 3ab992d | LGPL-3.0-or-later | yes (confirmed) |
| K | .NET | C# (Native AOT) | typed rule book + binary dataset cache | `variant-k` @ ce381f1 | LGPL-3.0-or-later | yes (confirmed) |

Licenses were **confirmed by the official run at the evaluated (10:15) commits**: all LGPL-3.0-or-later (LGPL v3 LICENSE + GPL companion text) and mergeable, except E (GPL-3.0-or-later, GPL-3 LICENSE text only ⇒ not mergeable). First detected 2026-10-03 08:47 CST on current heads from the actual LICENSE texts in the variant
dir and branch root; SPDX metadata / README only refine -only vs -or-later) and are re-detected by the evaluation run (`results/evaluation.md`, "Licensing" table). Mergeable =
the code can be merged into the LGPL-3.0-or-later mainline (`eve-dogma-rs`): LGPL-3 / permissive → yes, GPL → no,
nothing found → unknown (the authors must add a license before any merge). Licensing is informational, not scored,
but it constrains the merge plan (§7).

### Approaches (from each variant's README / DESIGN.md)

- **A — eve-dogma-rs (reference).** The baseline Rust engine. It builds an object graph with a hash map of attributes per
  item, resolves each modifier to concrete target items at registration time, and evaluates lazily with per-attribute
  memo cells. Modifiers come from SDE `modifierInfo`; effects CCP ships without it are covered by small data patches in
  the pipeline plus a few documented engine specials. Bincode dataset cache for faster cold start. Library + CLI +
  JSONL RPC (calc, EFT parse/export, search, type, meta).
- **B — data-oriented Rust.** "Compile, then evaluate": items get sorted base-attribute patches, all modifiers are
  appended to one flat list, sorted by a packed `(item, attr, op, seq)` key into a CSR graph whose sources resolve to
  node indexes or constants, then evaluated by an iterative DFS that visits each node once. Same formulas as A for the
  stats layer; adds `calc_many`.
- **C — Go.** Zero-dependency, stdlib-only Go. The dataset is loaded once (in parallel) into an immutable shared
  structure; each fit keeps a modifier registry keyed by attribute and tagged with a *selector* (ship location, group,
  required skill, owner…) instead of expanding modifiers to targets (pull, not push), with a memoised value cache and an
  explicit cycle stack. Skill modifiers for all-V characters are templated once per dataset. Library + CLI + HTTP.
- **D — TypeScript.** Zero runtime dependencies, pure ESM, runs in Node and in the browser (dataset decompressed with
  `DecompressionStream`). A pull-based attribute graph with lazily materialised cells, an operator table as data, target
  resolution through prebuilt indexes, and a registry of special effects keyed by effect name ("adding a special effect
  is one registry entry"). Goal: the most maintainable and web-friendly engine, within ~2–3× of Rust.
- **E — Pyfa-faithful Rust port.** Matches Pyfa by not re-deriving dogma: a Python-AST transpiler (`tools/pyfa2rs.py`)
  turns Pyfa's `eos/effects.py` handlers (2 359 of 2 402) into Rust in their original order, with names resolved to ids
  at transpile time; Pyfa's quirks (stacking sort order, `round(x, 2)`, cap-sim heap order) are kept on purpose. A few
  hand ports (RAH, remote reps/neuts…). GPL-3.0 because it is derived from Pyfa.
- **F — codegen Rust/WASM.** `build.rs` compiles the SDE into ~5 MB of generated Rust: every effect becomes a match arm
  of straight-line modifier calls, domains/operators/stacking decisions resolved at build time, skill effects
  precomputed for levels 0–5, dense attribute tables. No dataset parsing at runtime (dataset baked into the binary),
  so cold start is ~2 ms; also builds to WASM.
- **G — Python + NumPy batch.** The readability and batch-throughput baseline: fits are parsed per fit in Python, then
  modifier registration (gather/filter/equi-join on CSR template tables) and evaluation (levelised dependency graph,
  per-stage aggregation with stacking penalties via lexsort, caps, rounding) run as NumPy array operations over the
  whole batch. Special effects (propulsion, projected EWAR, RAH, fleet buffs) in a small per-fit Python layer.
- **H — Rust ECS.** Dogma as an Entity-Component-System on `hecs`: one entity per ship/character/skill/module/charge/…,
  attributes and modifiers as components, effect application and attribute calculation as systems run in an explicit,
  documented order (`Fit::run`) on a fresh world per request; derived dataset cache for start-up.
- **I — Rust salsa incremental.** Dogma as a demand-driven memoised query graph (salsa 0.28): inputs per item identity,
  derived queries for structure index, outgoing/incoming modifiers and attribute values, with backdating so a
  persistent session only recomputes what an edit touched. The CLI stays stateless and byte-identical (checked forward
  + reverse vs fresh database). Aimed at interactive fitting UIs.
- **J — C++20.** Performance-first: the gz JSON dataset is converted once (libdeflate + simdjson) into a relocatable POD
  image with flat index arrays and precomputed relevance tables, cached and `mmap`ped read-only (cold start ~2 ms);
  requests are parsed with simdjson, evaluated on flat attribute tables and written with a streaming JSON writer;
  `batch` spreads the JSONL across all cores in order. Byte-level fidelity to A's output.
- **K — C# / .NET 8 Native AOT.** "Rules that read like a rulebook": strong typed ids (`readonly record struct`),
  exhaustive switches, a `RuleBook` layer holding all dogma special cases separate from the attribute graph, a
  reflection-free deterministic JSON writer, binary dataset cache; Native AOT gives a single native executable with
  millisecond-scale start-up.

## 5. Results

Source: `eve-dogma-bench/results/evaluation.md` (commit `579a21a`), measured 10:16–10:46:56 CST 2026-10-03, 3 runs
per variant + warm-up, fresh clones (build time scored), total wall time 23.1 min. Commits are the branch heads as of
10:15 CST (checked against the GitHub push log: no variant pushed between the cutoff and its fetch; variant-i got a
later push at 10:53 CST, `1dba15e`, a bench-1.9.0 failures.json refresh, after its evaluation — not part of round 1).
Latency: all 11 variants 5/5 valid samples, spread ≤ 40 %, no flags.

| rank | variant | commit (CST) | cases | values | ms/calc | fits/s | cold ms | speed | maint | features | port | **total** | load (1m) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | J C++20 | `3ab992d` 10-03 09:07 | 326/326 | 21051/21051 | 0.076 | 28641 | 2.2 | 0.99 | 0.75 | 1.00 | 1.00 | **0.911** | 2.8–2.8 |
| 2 | F codegen Rust/WASM | `bc84e2b` 10-03 07:34 | 326/326 | 21051/21051 | 0.101 | 21783 | 1.8 | 0.95 | 0.64 | 1.00 | 1.00 | **0.854** | 1.3–1.6 |
| 3 | B data-oriented Rust | `f56dd59` 10-03 09:45 | 326/326 | 21051/21051 | 0.099 | 19268 | 4.7 | 0.90 | 0.70 | 1.00 | 0.50 | **0.805** | 1.6–1.7 |
| 4 | A eve-dogma-rs (Rust ref) | `659737b` 10-03 09:31 | 326/326 | 21051/21051 | 0.120 | 4847 | 8.0 | 0.77 | 0.66 | 1.00 | 1.00 | **0.790** | 1.0–1.2 |
| 5 | H Rust ECS | `b1c7852` 10-03 08:46 | 326/326 | 21051/21051 | 0.231 | 3240 | 5.2 | 0.69 | 0.69 | 1.00 | 1.00 | **0.770** | 1.2–1.2 |
| 6 | C Go | `d12ff1a` 10-03 07:27 | 326/326 | 21051/21051 | 0.234 | 12794 | 27.1 | 0.71 | 0.83 | 1.00 | 0.00 | **0.723** | 2.1–2.7 |
| 7 | E Pyfa-faithful Rust | `5867d53` 10-03 07:34 | 326/326 | 21051/21051 | 0.120 | 4377 | 8.8 | 0.76 | 0.74 | 1.00 | 0.00 | **0.712** | 1.2–1.3 |
| 8 | I Rust salsa | `ad9f73e` 10-03 09:18 | 326/326 | 21051/21051 | 0.124 | 2031 | 17.8 | 0.68 | 0.68 | 1.00 | 0.00 | **0.659** | 1.5–1.6 |
| 9 | D TypeScript | `5218e0d` 10-03 08:13 | 326/326 | 21051/21051 | 1.827 | 1168 | 109.3 | 0.27 | 0.68 | 1.00 | 1.00 | **0.596** | 1.3–1.8 |
| 10 | G Python+NumPy | `a07402e` 10-03 06:51 | 326/326 | 21051/21051 | 2.288 | 382 | 104.2 | 0.17 | 0.79 | 1.00 | 0.00 | **0.496** | 1.3–1.8 |
| 11 | K C#/.NET AOT | `ce381f1` 10-03 08:18 | 326/326 | 21051/21051 | 1.139 | 1017 | 59.9 | 0.34 | 0.57 | 1.00 | 0.00 | **0.484** | 2.1–2.8 |

All 11 variants passed the gate (326/326 cases, 21 051/21 051 values in every run, deterministic). Gaps in the
total come from speed (log scale, 100× span) and maintainability; features are 1.00 for everyone (EFT export
byte-exact 326/326, `eft_parse` 20/20, RPC/search/type probes all pass).

### Per-variant notes

- **J (C++20) — 1st, 0.911.** Fastest latency (0.076 ms/calc) and batch (28.6 k fits/s), cold start 2.2 ms (mmapped
  POD image), WASM build in code. Maintainability 0.75: 7 251 core LOC, 123 ctest tests passing, 2 deps, 7.3 s build.
- **F (codegen Rust/WASM) — 2nd, 0.854.** Best cold start (1.8 ms, dataset baked in), 0.101 ms/calc, 21.8 k fits/s,
  WASM in code. Maintainability 0.64 is the weak spot: no own tests (0 tests found), 78.8 s build, generated code.
- **B (data-oriented Rust) — 3rd, 0.805.** 0.099 ms/calc (≈ F), 19.3 k fits/s; 51 tests; WASM only documented (0.5).
- **A (eve-dogma-rs reference) — 4th, 0.790.** 0.120 ms/calc but low batch (4.8 k fits/s) and 8 ms cold start; 10 tests,
  8 deps; WASM in code. The incumbent; good merge target.
- **H (Rust ECS) — 5th, 0.770.** 0.231 ms/calc, 3.2 k fits/s; 35 tests, 10 deps (most); WASM in code.
- **C (Go) — 6th, 0.723.** Highest maintainability (0.83: 361 tests, 0 deps, 0.8 s build) and good batch (12.8 k fits/s),
  but 27 ms cold start and no WASM/browser path (portability 0).
- **E (Pyfa-faithful Rust) — 7th, 0.712.** Most data-driven (26 hard-coded effect names vs 92–98 elsewhere, ratio 0.992,
  transpiled Pyfa handlers), 0.120 ms/calc; only 1 test, no WASM. **GPL-3.0-or-later ⇒ not mergeable** into the
  LGPL mainline; valuable as an independent Pyfa oracle.
- **I (Rust salsa) — 8th, 0.659.** 0.124 ms/calc single-shot, 2.0 k fits/s, 17.8 ms cold; incremental-session strengths
  are not exercised by the stateless bench. 0 tests found, no WASM.
- **D (TypeScript) — 9th, 0.596.** 1.83 ms/calc, 109 ms cold start (Node), but zero deps and runs in browser (port. 1.0);
  test count not parsed (npm suite passed).
- **G (Python + NumPy) — 10th, 0.496.** Slowest single-fit (2.29 ms/calc, 382 fits/s); smallest core (3 845 LOC), 0.3 s
  build, maint 0.79. Batch design does not pay off on 326 fits.
- **K (C#/.NET AOT) — 11th, 0.484.** 1.14 ms/calc, 60 ms cold start; no own test suite found (Tests 0), no WASM.

Maintainability detail (core LOC per language, tests, deps, build time, docs, license, hard-coded effects) and the
per-run table with loadavg: see `results/evaluation.md`.

Not ranked (failed the gate): none.

## 6. Decision

**Round 1 result: J first (0.911), F second (0.854). No engine is adopted yet.** The user narrowed the choice to F and
J on 2026-10-03 at about 11:00 CST, and the adoption decision is deferred to an F-vs-J head-to-head evaluation
(docs/18, eve3). An earlier plan to promote J straight to mainline (a new repo `EX-CT/eve-dogma`, with MCP/web switching
to J) is **paused** until docs/18 is decided.

**Engine lines stopped.** On 2026-10-03 at about 11:05 CST the user stopped every other engine line: A, B, C, D, E, G,
H, I and K. Only F and J continue. `eve-dogma-rs` (A) is **frozen as an archived reference**. Its last merged state is
`d6043a7` (H's capacitor-simulation PR #1 on top of the round-1 commit `659737b`), and it gets no further engine
work. Open A findings, such as the 5 bug classes in docs/15, are recorded there and not fixed.

### Why J ranks first, and why it is not yet decisive

| | weight | J | F | J − F (weighted) |
|---|---|---|---|---|
| Speed | 0.40 | 0.99 | 0.95 | +0.016 |
| Maintainability | 0.35 | 0.75 | 0.64 | +0.039 |
| Features | 0.15 | 1.00 | 1.00 | 0 |
| Portability | 0.10 | 1.00 | 1.00 | 0 |
| **Total** | | **0.911** | **0.854** | **+0.057** |

- **Correctness is equal.** Both pass 326/326 cases and 21 051/21 051 values in every run, are deterministic, give
  byte-exact EFT export, and pass every RPC probe.
- **Speed is close.**
  - J: 0.076 ms/calc, 28.6 k fits/s, 2.2 ms cold start.
  - F: 0.101 ms/calc, 21.8 k fits/s, 1.8 ms cold start (the best cold start).
  - J's lead is about 0.016 of the total.
- **Most of the margin is maintainability**, about 0.039 of the total.
  - J has 123 passing ctest tests, 2 dependencies and a 7.3 s build.
  - F had no tests of its own found, a 78.8 s build, and generated code.
  - This gap can be closed with ordinary engineering work. It is not an architectural difference.
- **License.** Both ship LGPL v3 LICENSE texts and are mergeable into an LGPL-3.0-or-later mainline (§4, licensing
  table). Neither has the GPL problem of E.
- **Noise caveat.** The run used a shared, loaded host: 1-minute loadavg was 2.8 during J and 1.3–1.6 during F.
  Latency spreads were up to 40 % on the single-CPU measurement, and every speed sub-score is log-scaled. J's speed lead
  is within what the load difference could explain. The 0.057 total margin is real but mostly maintainability. A
  head-to-head on an idle, pinned host with the current heads (docs/18) is the right basis for adoption.

### Adoption plan (applies to whichever of F / J wins docs/18)

1. **Mainline repo.** The winner moves to a new repo `EX-CT/eve-dogma`, created from its variant branch with filtered
   history and no build directories. Preparation for J was started and is paused.
2. **eve-dogma-rs (A)** is archived as a frozen reference. It can still serve as a second implementation for
   differential testing, and the round-2 setup decides whether that cross-check runs against A, the docs/18 runner-up,
   or E.
3. **MCP / web UI** (eve-fit-mcp, eve-fit-web) switch their default engine to the winner after docs/18 (eve4). Until
   then they keep their current engine.
4. **P1 (docs/12, history rewrite of `variant-j/build-prof/` and `build-native/` in eve-dogma-lab).** If J wins, P1
   is unnecessary for the new repo, because `EX-CT/eve-dogma` is created from filtered history without build
   directories. P1 then only matters if the eve-dogma-lab pack itself has to shrink. If F wins, P1 stays as written in
   docs/12.
5. **Bench.** 1.9.0 is released (`v1.9.0`, 331 cases). The winner must pass 1.9.0 331/331 and the capacitor suite
   (`cap-suite`, 150 cases) before the switch.

### What the other variants contribute (ideas, not code merges)

- **F (codegen):** build-time specialisation of effects and the baked dataset (cold start, WASM size). If J wins, these
  are the main ideas to port.
- **J (C++20):** precomputed relevance tables, the mmapped POD dataset image and the streaming writer. If F wins, these
  are the main ideas to port.
- **B (data-oriented Rust):** CSR flat modifier graph and data layout, with latency close to F in Rust.
- **H (Rust ECS):** capacitor-simulation fidelity. Its Pyfa multiplier fold and incoming void-bomb drains (merged into A
  as PR #1) score 150/150 on the cap suite, and its cap-suite fixtures are acceptance material for the winner.
- **E (Pyfa-faithful Rust, GPL-3.0-or-later):** the most data-driven design (transpiled Pyfa handlers). It is not
  mergeable into the LGPL mainline and stays a separate **GPL fidelity reference / differential oracle** (docs/15 fuzz
  triage).
- **C (Go):** the selector-tagged pull registry, and its 361-test suite as test material.
- **A (eve-dogma-rs):** the incumbent contract, the oracle tooling, the documentation (DESIGN.md, contract) and the
  WASI build path. It stays as the archived reference.

### 6.x Update 2026-10-03 11:09–11:11 CST (user decision)

- **Mainline is Rust, built on F** (`variant-f` / `variant-f-perf` in EX-CT/eve-dogma-lab). This supersedes the F-vs-J head-to-head above; docs/18 is cancelled.
- **J (C++20) is kept as the backup engine and must not be deleted.** Locations:
  - Tag `j-backup-2026-10-03` → `3ab992d` (variant-j exactly as scored in round 1, 0.911), branch `variant-j` in EX-CT/eve-dogma-lab.
  - Tag `j-graphs-wip-2026-10-03` → `bc46ef9`, branch `graphs-j`: unfinished graph port, stopped at 11:09.
  - EX-CT/eve-dogma `dd97e12`: empty repo created for the promotion, left untouched.
- J's speed techniques serve as a reference for F. Priority is now feature completeness against Pyfa (docs/19 inventory, docs/20 Rust architecture plan); performance work comes after.

## 7. Merge plan

**DRAFT (depends on §6).** Template, with first proposals from the results:
1. Ideas to port into the chosen core (per idea: source variant, expected gain, owner, acceptance = bench 326/326 + no
   perf regression). Candidates: J's precomputed relevance tables / mmapped POD dataset image and streaming writer
   (latency, cold start); F's build-time specialisation of effects and baked dataset (cold start, WASM size); B's CSR
   flat modifier graph (Rust-native, near-F latency); C's selector-tagged pull registry and its 361-test suite as test
   material; E's transpiled Pyfa handlers only as a GPL oracle for differential testing (not merged).
2. Repository moves (which branch becomes which repo / crate). Licensing gate: only code marked *mergeable = yes*
   enters the LGPL-3.0-or-later core; E (GPL-3.0-or-later, derived from Pyfa) can only contribute ideas or stay a
   separate GPL cross-check tool. All other variants currently ship LGPL v3 LICENSE texts (re-checked at the 10:15 commit).
3. Variants archived (branch kept, README pointer to this document).
4. Bench: unfreeze, apply `pending-1.9.0.md`, re-run the evaluation for the merged engine.

## 8. Lessons learned

**DRAFT.** First observations from the run (to be extended by the teams):
- Correctness converged: all 11 designs reached 326/326 on the frozen 1.8.0 bench, so the ranking is decided by
  speed and maintainability — the shared bench/oracle and frozen versions worked.
- Dataset loading dominates cold start (1.8–2.2 ms for baked/mmapped images vs 8–110 ms for parse-at-start).
- Several variants report no own tests (F, I, K) or unparsed counts (D, G); require a machine-readable test summary.
- Per-effect hard-coding is similar (92–98 names) except E (26): transpiling Pyfa is the data-driven outlier.
- Measurement: shared loaded machine (loadavg up to 2.8); own single-CPU latency kept spreads ≤ 40 %; next time run on
  an idle host. Freeze the cutoff by **push time** (GitHub push log), not commit time — variant-i had commits dated
  09:52–09:53 that were only pushed at 10:53.

Prompts:
- Correctness: which Pyfa quirks were hardest, and how did the shared oracle/bench shape the work?
- Performance: what actually mattered (dataset loading/caching, allocation, skill pruning, batch parallelism)?
- Process: 11 parallel bots, frozen bench versions (1.5 → 1.8), contract rulings; what to change for round 2?
- Measurement: shared loaded machine; next time pin CPUs or run the evaluation on an idle host.
