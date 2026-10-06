# 17 — Fuzzing, oracle adjudication, pending cases and nightly CI

**中文摘要**：本文说明差分模糊测试（fuzz）和夜间 CI。

- **模糊测试**：随机生成请求，交给多个引擎变体计算。结果不一致时，由 Pyfa 预言机（oracle）裁定谁对谁错。
- **裁定**：预言机结果就是期望值；但如果 eve 的裁定与 Pyfa 不同，以合约为准。例如：模块请求了自己无法使用的
  状态（不能超载 / 不能激活）时保持请求值，Pyfa 则把它降为 online。
- **待定用例流程**：fuzz 发现 → `pending` 文件（最小复现 + 预言机输出 + 裁定说明）→ eve 裁定 → 进入下一个合约
  版本的语料。不会自动加入计分语料。
- **夜间 CI**（eve-dogma-bench `.github/workflows/nightly.yml`）：
  - 构建 eve-dogma-rs main，跑 bench 1.8.0、1.9.0 和 graphs 语料；
  - 再跑一个不依赖 Pyfa 的自洽性 fuzz：确定性、batch == 单次、抗性在 [0,1]、技能单调等；
  - 失败时按标题去重，自动开 issue 或在已有 issue 下评论。

Status: 2026-10-03 CST. The nightly workflow is a PR to eve-dogma-bench main (bench frozen for scoring; eve merges).

## 1. Why two kinds of checks

The bench corpora (stats 1.8.0: 326 cases, 1.9.0: 331, graphs 0.2: 178 cases / 2437 values) are hand-picked and
oracle-backed, but they only cover what someone thought of. Fuzzing finds the rest. There are two layers:

| layer | needs Pyfa | where | finds |
|---|---|---|---|
| differential fuzz + oracle adjudication | yes (GPL oracle, local box) | `graphs/tools/fuzz_graphs.py` (graphs-round2), `oracle/fuzz/gen_legal.py` (pending-1.10, legal stats fits) | wrong values: one engine disagrees with another and with Pyfa |
| self-consistency fuzz | no | `tools/ci_invariants.py` (ci-nightly → main) | crashes, nondeterminism, batch/single drift, values outside physical bounds |

## 2. Differential fuzzer design (graphs)

`graphs/tools/fuzz_graphs.py --n N --seed S --variants G1,G2,G3,G4 [--contract 0.2] [--record]`

1. **Generate.** Random GraphRequests for the contract version:
   - fits drawn from the graph corpus and the 326 stats FitRequests;
   - a random graph, x axis and y series;
   - x samples that include limiter edges (optimal/falloff, web/TP ranges);
   - random params and settings;
   - targets: ideal, a random profile, or a random target fit with a resist mode;
   - 0.2 extras: `ecm_burst`, the damage %-axes, ewar/RR target fits, and out-of-range `time_s`/resist params.
   Seeded, so a run can be replayed exactly.
2. **Differ.** Every request goes through each variant's `graph-batch`. These are read-only worktrees prepared by
   `tools/evaluate_graphs.py`. A request is a *disagreement* when two variants differ on any sample value beyond the
   corpus tolerance (`tools/metrics.close`), or when one answers and another errors.
3. **Adjudicate.** Each disagreement is sent to the Pyfa graph oracle, and each answer is scored against it with
   `run_graphs.score_case`. A case is *confirmed* when the oracle answered and at least one variant is wrong.
   Confirmed cases are clustered by (graph, axis, wrong variants, request features). A wrong answer that a variant
   already fails in the scored corpus is labelled "known (corpus gap)" so it isn't counted twice.
4. **Record** (`--record`). One representative per cluster is written to `graphs/pending/cases/` + `expected/`, plus a
   section in `graphs/pending.md`. Nothing reaches `graphs/cases` automatically.

Stats-side generator (E, pending-1.10): `oracle/fuzz/gen_legal.py` builds only **legal** fits, using Pyfa's
`Module.fits` slot, hardpoint and restriction rules, valid charges, and state limits. `check_legal.py` applies the
same rules as a checker. The graphs fuzzer doesn't enforce legality, so its stats-side findings must be checked
with `check_legal.py` before they are proposed (see the Standup Cap Battery entry below).

Results on 2026-10-03 (5 seeds, 400–800 requests each):
- G2 had 135 confirmed wrong answers.
- G1 and G4 had none.
- G3's findings were fixed in graphs-g3: webs/TPs stacking with the target's own penalised multipliers,
  launcher damage multipliers in the app profile, missing target resist attributes, and a NumPy crash on drone webs.
- The rest were two non-bugs: the state convention (§3) and a stats-engine difference (Standup Cap Battery on a
  ship, §4).

## 3. Oracle adjudication rules

- **The oracle decides values, the contract decides semantics.** When Pyfa's behaviour is an artefact rather
  than game mechanics, eve rules, and the ruling wins over the oracle. The expected value is then produced by
  running the oracle on the request the ruling implies, never by hand-typing numbers.
- **Module state ruling (eve, 2026-10-03; stats contract and graphs 0.3 draft; A and H agree):** a module whose
  requested state it can't use (`overheated` without overheat effects, such as Bastion or a doomsday, or `active` on
  a passive module) **keeps the requested state**. Pyfa's `isValidState` downgrades it to `online`, which is what
  `oracle/pyfa_oracle.py` line 96 does. For such fits the expected values come from the oracle run with the state
  the ruling implies. Graphs: `graphs/draft-0.3/rulings/make_ruling_cases.py`, case
  `dmg_dist_vargur_bastion_overheated_state`. The earlier G3 normalisation to online was reverted (graphs-g3 610ea6c).
- **Data-version gaps are not bugs.** Pyfa's eve.db build lags the SDE dataset (3532181 vs 3569502). Values that
  differ only because of that (e.g. Paladin/Golem agility) are noted, not proposed. E's generator draws only types
  that exist in the oracle DB.
- **Sampling artefacts are informational.** Pyfa's grid step and interpolation in the application profile are
  documented, not scored. Sample points are kept off edges (`tools/edge_check.py`).

## 4. Pending-case flow

```
fuzz finding ─▶ minimal repro (request JSON) ─▶ oracle output ─▶ pending entry ─▶ eve ruling ─▶ next corpus version
```

| corpus | pending location | released as |
|---|---|---|
| graphs | `graphs/pending.md` + `graphs/pending/{cases,expected}` (graphs-round2) | `graphs/draft-0.3/` (unreleased, 192 cases / 2694 values) |
| stats | `pending-1.9.0.md` (main), `pending-1.10` branch: `pending.md` (E), `pending-1.10-exct.md` + `pending/exct/` (EXCT) | bench 1.9.0 (staged, 331 cases), 1.10 |

Each entry lists:
- the candidate case name (team-prefixed, e.g. `exct_fuzz_…`, so parallel contributors don't collide);
- what it checks;
- the oracle value;
- each engine's value;
- what needs adjudication.

Contributors add their own files and never edit another team's pending file. Example (pending-1.10):
`exct_fuzz_rifter_standup_cap_battery`. Pyfa's python effect `structureCapacitorCapacityBonus` gives a Rifter with a
Standup Cap Battery 62812.5 GJ; eve-dogma-rs and variant-g give 312.5. The fit is illegal (a structure module on a
ship), so eve decides whether it's scored.

## 5. Nightly CI (eve-dogma-bench)

`.github/workflows/nightly.yml` runs on `schedule` (18:00 UTC = 02:00 CST) and `workflow_dispatch` (inputs:
`engine_ref`, `sde_tag`, `fuzz_seed`). Permissions are `contents: read, issues: write`. Steps:

1. Check out the bench and eve-dogma-rs at `engine_ref` (default `main`), then `cargo build --release --locked`.
2. Download the pinned dataset from EX-CT/eve-sde-pipeline release `sde-3569502`. The bench expectations are tied to
   that build; "latest" could move.
3. **Bench 1.8.0** (`run.py`) on the checked-out branch, **bench 1.9.0** from `origin/bench-1.9.0`, and **graphs** from
   `origin/graphs-round2`. Each one is skipped with a notice if its branch is gone. `tools/ci_gate.py` fails the step
   unless every case is fully correct, there are 0 engine errors and the engine is deterministic.
4. **Graphs:**
   - corpus integrity (`tools/ci_graph_corpus.py`, on 0.2 and the 0.3 draft);
   - `run_graphs.py --self-test`;
   - engine scoring once eve-dogma-rs implements `graph-batch`. eve-dogma-rs main has no graph command yet, and the
     step says so in the summary.
5. **Fuzz self-consistency** (`tools/ci_invariants.py`, 400 mutated requests plus 40 skill-pair fits, seed = run number).
6. Artifacts: scorecards, `failures.json`, `ci-invariants.json`.
7. **On failure:** `actions/github-script` comments on the open issue titled **"Nightly bench failure"**, or opens one
   (deduped by exact title). This only happens for scheduled runs or runs on main, so test runs on branches don't
   file issues.

Scheduled workflows only run from the default branch, and the bench is frozen for scoring. The workflow therefore
lives on branch `ci-nightly` and is proposed by PR. eve decides when to merge it.

## 6. Invariants (Pyfa-free)

`ci_invariants.py` mutates committed corpus requests with a seeded RNG:
- skill default level 0–5;
- random module states (offline/online/active/overheated);
- random damage pattern;
- one dropped module or drone.

It checks:

| invariant | rule |
|---|---|
| determinism | the same batch twice → byte-identical JSON (excluding `meta`) |
| batch == single | `calc` on a request = its line in `batch` (40 random requests) |
| finite | no NaN/±inf anywhere in the response |
| resists | every resonance in [0, 1] |
| non-negative | hp, ehp, dps/volley parts, max velocity, capacitor capacity ≥ 0 |
| EHP bound | `ehp.total ≥ hp.total` |
| sums | dps/volley `total` = em + thermal + kinetic + explosive |
| align | `align_time_s = ln 4 · agility · mass / 10⁶` |
| monotonic | all skills V vs all skills 0 on the same fit: hp.total, capacitor capacity and max_targets never drop |

Error responses are allowed for mutated requests. They must still be deterministic and the same in single and batch
mode. A fault-injection run (a wrapped `batch` that sets a resonance to 1.2 and jitters align time) is caught: exit 1.
eve-dogma-rs 659737b passes on seeds 1–3 (1580 requests each) and on the default seed.

Out of scope for the nightly run: comparing against Pyfa, and timing. Single-core timing belongs to the official
evaluation; CI runners are noisy.
