# 13 — Engine round 2 evaluation (graphs, variants G1–G4)

> **Status: DRAFT SKELETON.** Placeholders (`⟨…⟩`) are filled from `eve-dogma-bench@graphs-round2`
> `results/evaluation-graphs.{md,json}` after the round-2 run (cutoff 11:00 CST, 2026-10-03). The plan is in
> [10-round-2-graphs-plan.md](10-round-2-graphs-plan.md); round 1 is in [09](09-engine-round-1-evaluation.md).
>
> 中文摘要：第二轮评测 Pyfa 图表（graphs）子系统的 4 个方案 G1–G4。门槛：图表合同 0.2 全部 178 个 case 正确（各接口一致），
> 且该分支的引擎仍通过 bench 1.8.0 的 326 个属性 case。过门槛后按 速度 40%、可维护性 35%、功能 15%、可移植性 10% 计分。
> 许可证按评测提交中的实际 LICENSE 文件判定；G1 基于 GPL 的方案 E，不能并入 LGPL 主线。

**Confirmed round-2 rules (eve, 2026-10-03):**
1. Cutoff `--as-of 2026-10-03T11:00:00+08:00` (Asia/Shanghai).
2. Graph contract **0.2** pinned @ `0397d95` (178 cases); the 0.3 draft is not used.
3. Gate = **all 178** contract-0.2 cases pass through every interface offered — including `ecm_burst` and the error
   cases, not only the nine Pyfa graphs — **and** the branch's underlying stats engine passes bench **1.8.0 326/326**.
   Weights: speed 40 / maintainability 35 / features 15 / portability 10.
4. **No fresh clones; build time is not measured for scoring** (recorded for information only). Unlike round 1,
   the command has no `--fresh-clones`.

**Scope change (user, via the main bot, 2026-10-03 ≈ 11:00):** round 2 evaluates only **F and J**: G4 (`graphs-g4`,
on variant-f) and GJ (`graphs-j`, J's graph port on variant-j `3ab992d`, in progress). G1–G3 are no longer evaluated
(their descriptions below are kept for reference). F baseline done (§5); side-by-side rerun when `graphs-j` exists:

```bash
python3 tools/evaluate_graphs.py --as-of 2026-10-03T11:00:00+08:00 --runs 3 --only G4,GJ
```

**Push-time check (added for round 2):** the `--as-of` pick (last first-parent commit with committer date ≤ cutoff) is
verified against the GitHub branch activity log (`GET /repos/{o}/{r}/activity?ref=refs/heads/<branch>`). A commit
dated before the cutoff but pushed after it was not available at the cutoff, so the last head pushed at or before the
cutoff is evaluated instead; commit date, push time, chosen SHA and verdict are in the json (`git.push_check`) and the
md ("Commit selection"). Reason: in round 1, variant-i had commits dated 09:52–09:53 that were pushed only at 10:53
(the evaluated `ad9f73e` was the head pushed before 10:15, so round 1 was unaffected). From round 3, cutoffs are
defined by push time (TODO in `tools/evaluate.py`).

## 1. Goal

Pick the graph implementation (or the ideas from several) that becomes the graph layer of the EXCT toolkit (CLI, MCP
`graph` tool, web UI), with Pyfa's ten graph families: `damage`, `application_profile`, `mobility`, `lock_time`,
`warp_time`, `shield_regen`, `capacitor`, `ewar`, `remote_reps`, `ecm_burst`.

## 2. Method

One command in `EX-CT/eve-dogma-bench`, branch `graphs-round2`:

```bash
python3 tools/evaluate_graphs.py --as-of 2026-10-03T11:00:00+08:00 --runs 3      # results/evaluation-graphs.{md,json}
```

1. **Version rule:** each variant (`EX-CT/eve-dogma-lab` branches `graphs-g1..g4`) at its branch HEAD as of the cutoff
   (last first-parent commit at or before it), checked out read-only. SHA and commit time recorded.
2. **Pins:** graph corpus, expected values, `run_graphs.py` and `CONTRACT-GRAPHS.md` from `0397d95` (contract
   revision 0.2, 178 graph cases / 2 437 values); stats gate from bench 1.8.0 `3da9671` (326 cases). Both extracted with
   `git archive`, independent of the branch head (the unreleased 0.3 draft is not used).
3. **Build** with the variant's own command (`bench.yaml`, or inferred from its `score*.sh`, flagged). No fresh
   clones; build time is informational only and not part of the score.
4. **Correctness** with the official scorer over every interface the variant offers (graph-batch, RPC `graph`,
   single `graph`); the interfaces must agree. Stats gate: `run.py` on the branch's round-1 engine commands.
5. **Perf** (medians over runs, loadavg per run): batch points/s (start-up excluded), cold start; **dense latency**
   measured with the round-1 rules (below).
6. **Maintainability, features, portability, licensing** (helpers shared with the round-1 `tools/evaluate.py`).

## 3. Scoring rules (as implemented in `tools/evaluate_graphs.py`)

- **Gate:** all 178/178 contract-0.2 cases (incl. `ecm_burst` and error cases) fully correct through every interface
  offered, and 326/326 bench-1.8.0 stats cases. Both are required; a run with `--no-stats-gate` is marked unofficial.
- **Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability**,
  `L(x, best, span) = clamp(1 − log10(x/best)/log10(span), 0, 1)`.
- **Speed** = 0.4·L(1/points·s⁻¹, 100) + 0.4·L(dense latency ms, 100) + 0.2·L(cold ms, 100).
  - points/s = corpus points / (wall(corpus) − wall(1 small request)); if that difference is < 5 % of the corpus wall
    time the raw value is used and flagged.
  - **Dense latency** = every distance-axis damage case re-sampled at 500 points (distinct fits): graph-batch pinned
    to **one CPU** (taskset), (T_N − T_1)/(N − 1), N sized for ≈0.5 s, **≥ 5 independent samples, median**; samples ≤ 0,
    < 0.002 ms, > T_N/N or with missing responses are invalid; spread > 50 % ⇒ up to 3 extra samples, then flagged.
    RPC warm-process latency is reported for information.
  - cold = fresh process answering one small request, median of 5.
- **Maintainability** = 0.30·Tests + 0.30·Size + 0.20·Docs + 0.20·Deps (Size = L(round-2 core lines added since the
  merge-base with the round-1 branch, min, 10); Tests/Docs/Deps as round 1; skipped tests don't count as passed).
- **Features** = 0.6·(graphs with all cases correct / 10) + 0.3·(interfaces passing / 3) + 0.1·(empty `x.values` →
  empty series).
- **Portability** = 1 WASM/browser build in code, 0.5 documented only, 0 none.
- **Licensing** (not scored): actual LICENSE files at the evaluated commit (variant dir + branch root) plus the
  license of the round-1 variant the branch is built on.

## 4. Variants

| | Approach | Built on (round 1) | Branch / commit | License | Mergeable into LGPL-3.0-or-later mainline |
|---|---|---|---|---|---|
| G1 | Pyfa-faithful graph port (Rust) | E (Pyfa-faithful Rust, GPL) | `graphs-g1` @ ⟨sha⟩ | GPL-3.0-or-later | **no**: derived from E/Pyfa (GPL) ⟨confirm⟩ |
| G2 | engine primitives (Go) + portable TS evaluator | C (Go) | `graphs-g2` @ ⟨sha⟩ | LGPL-3.0-or-later | yes ⟨confirm⟩ |
| G3 | vectorised NumPy grid + per-fit cache | G (Python + NumPy) | `graphs-g3` @ ⟨sha⟩ | LGPL-3.0 (text; qualifier not stated in the graph dir) | yes ⟨confirm⟩ |
| G4 | declarative graph spec (Rust, expression catalogue) | F (codegen Rust/WASM) | `graphs-g4` @ `f73ff1c` | LGPL-3.0-or-later | **yes** (confirmed at the evaluated commit) |

GJ: F/J side-by-side cancelled: on 2026-10-03 at 11:09 CST the user set the Rust mainline based on F (J and the `graphs-j` port stopped).

Provisional licenses: detected 2026-10-03 09:10 CST on current heads with the evaluation tool's detection. G4 confirmed by the F baseline run.

### Approaches (from each branch's README / DESIGN / GRAPHS.md)

- **G1 — Pyfa-faithful graph port.** Extends variant E (Pyfa transpiled to Rust) with `src/graphs/`: all ten graph
  types as ports of Pyfa's `graphs/data/*` getters, exposed as `graph`, `graph-batch` and RPC `graph`. Inherits E's
  GPL-3.0-or-later license (derivative of Pyfa).
- **G2 — engine primitives + portable evaluator.** Two stages: the Go engine (variant C) emits per-fit graph
  *primitives* (`graph-primitives`, JSONL), and a dependency-free TypeScript evaluator turns them into the
  GraphResult; the Go stage also compiles to WebAssembly, so the whole pipeline runs in the browser.
- **G3 — vectorised grid engine.** On variant G's Python dogma engine: request validation and dispatch, a `Ctx`
  wrapper with a per-fit cache, and NumPy kernels evaluating whole x grids at once (range factors, stacking
  penalties, regen curves, application kernels per weapon kind).
- **G4 — declarative graph spec.** On variant F: a compiled-in catalogue (`graphs.json`) with constants, graph
  definitions and EWAR source tables, evaluated by a small expression language (`src/graphs/expr.rs`); graphs are
  data, the Rust side provides context (fit, raw stats, params) and builtins.

## 5. Results

### F baseline (G4 only)

Source: `eve-dogma-bench@graphs-round2` `results/evaluation-graphs-F-baseline.{md,json}` (also
`results/evaluation-graphs.{md,json}`; commit `562a201`, tool `ed54676`). Command
`python3 tools/evaluate_graphs.py --as-of 2026-10-03T11:00:00+08:00 --runs 3 --only G4` (official settings, no
`--quick`, no `--no-stats-gate`, no fresh clones). Run **11:05:42 – 11:09:00 CST** 2026-10-03, 3 runs, 1-min loadavg
2.8–4.7 (other agents' builds running on the shared box). A first attempt (11:04:24 – 11:05:04) was aborted because the
build was killed by an external SIGTERM after 38 s; it is not a variant failure.

| rank | variant | commit (CST) | graph cases | values | stats 1.8.0 | points/s | dense ms (1 CPU) | spread / flags | cold ms | speed | maint. | features | port. | **total** | mergeable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| (1) | G4 (on F) | `f73ff1c` 10:55 | **178/178** | 2 437/2 437 | **326/326** | 1 790 | 35.79 ⚠ | 0/8 valid; upper bound T_N/N used | 2 | 1.00* | 0.79 | 1.00 | 1.00 | 0.927* | yes |

- **Gate: pass.** 178/178 through all three interfaces (graph-batch, RPC `graph`, single `graph`), including
  `ecm_burst` 218/218 values and the error cases 20/20; stats engine 326/326 (21 051/21 051 values).
- **Commit selection:** commit-date pick `f73ff1c` (committed 10:55:17, pushed 10:55:18 CST) = head pushed before the
  11:00 cutoff ⇒ verdict ok.
- **Dense latency flag:** all 8 differencing samples were invalid (above T_N/N) under load, so the tool fell back to
  the upper bound T_N/N = 35.8 ms. For comparison, the warm "dense repeat" is 8.1–11.5 ms and the RPC warm request
  9.6 ms. Treat the dense value as unreliable; it must be re-measured in the side-by-side run.
- *Speed and total are relative to the best ranked variant. With G4 alone, speed = 1.00 by construction, so 0.927 is
  **not** a comparable score. Only the side-by-side `--only G4,GJ` run ranks F vs J.
- Maintainability 0.79: 2 773 round-2 core lines (Rust), own cargo suite passed but reports 0 counted tests, 4 deps,
  README/DESIGN/LICENSE present. Portability 1 (WASM build in code). Features 1.00 (all graphs, all 3 interfaces,
  empty `x` → empty series 154/154).

### F vs J (side by side)

F/J side-by-side cancelled: on 2026-10-03 at 11:09 CST the user set the Rust mainline based on F (J and the `graphs-j` port stopped).

## 6. Decision

⟨Left for eve (coordinator).⟩ Questions:
- Which graph layer goes into the mainline (CLI + MCP `graph` tool)? G1 can only contribute as a GPL oracle/cross-check.
- Is the browser path (G2 WASM + TS, or G4 via F's WASM build) a requirement for the web UI?
- Keep a second implementation for differential fuzzing (`graphs/tools/fuzz_graphs.py`)?

## 7. Merge plan

⟨To be written.⟩ Template:
1. Port the winning graph layer onto the round-1 mainline engine (or keep its engine if that also won round 1).
2. Licensing gate: only *mergeable = yes* code enters the LGPL-3.0-or-later mainline; G1/E stay GPL (separate repo
   or test-only tool).
3. Contract: release graph contract 0.3 (`graphs/draft-0.3`) after the decision; re-run the evaluation on the merged code.
4. Archive the other branches with a pointer to this document.

## 8. Lessons learned

⟨To be written.⟩ Prompts: Pyfa graph quirks that cost most time; value of the differential fuzzer and pending-case
workflow; single-CPU latency vs multi-threaded batch; corpus growth during the round (0.1 → 0.2 → 0.3 draft).
