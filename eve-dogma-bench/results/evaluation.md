# Engine round 1 evaluation

Generated 2026-10-03 10:46:56 CST (Asia/Shanghai) by `tools/evaluate.py` (`32295d5`); bench pinned to 1.8.0 @ `3da9671` (326 cases); commits: 2026-10-03T10:15:00+08:00; runs = 3; host 8 CPUs; total wall time 23.1 min. Perf numbers were measured on a shared, loaded machine: compare with the loadavg column.

## Ranking

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

## Maintainability and features

| variant | core LOC (languages) | test LOC | tests (own suite) | runtime deps | build s | README/DESIGN/LICENSE | license | hard-coded effects (h) | data-driven ratio | EFT exp | EFT parse | RPC | search | type | portability |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| J | 7251 (C++ 7155, CMake 96) | 199 | passed (123✓/0✗, ctest, 1.8 s) | 2 | 7.3 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 94 | 0.971 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | code |
| F | 5204 (Rust 5204) | 0 | passed (0✓/0✗, cargo, 63.7 s) | 4 | 78.8 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 92 | 0.971 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | code |
| B | 6220 (Rust 6220) | 672 | passed (51✓/0✗, cargo, 80.4 s) | 6 | 79.5 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 96 | 0.970 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | docs-only |
| A | 5478 (Rust 5456, JavaScript 22) | 157 | passed (10✓/0✗, cargo, 41.4 s) | 8 | 72.4 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 98 | 0.970 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | code |
| H | 5139 (Rust 5139) | 190 | passed (35✓/0✗, cargo, 93.8 s) | 10 | 83.5 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 94 | 0.971 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | code |
| C | 7702 (Go 7702) | 661 | passed (361✓/0✗, go, 3.6 s) | 0 | 0.8 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 93 | 0.971 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | none |
| E | 4742 (Rust 4742) | 0 | passed (1✓/0✗, cargo, 34.4 s) | 7 | 105.1 (fresh) | ✓✓✓ | GPL-3.0-or-later | 26 | 0.992 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | none |
| I | 5372 (Rust 5372) | 0 | passed (0✓/0✗, cargo, 34.6 s) | 7 | 104.5 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 97 | 0.970 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | none |
| D | 7216 (TypeScript 3642, JavaScript 3574) | 57 | passed (None✓/None✗, npm, 7.4 s) | 0 | 7.6 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 96 | 0.970 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | code |
| G | 3845 (Python 3845) | 232 | passed (None✓/None✗, script, 6.8 s) | 1 | 0.3 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 93 | 0.971 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | none |
| K | 4054 (C# 4041, Shell 13) | 0 | none found | 0 | 13.9 (fresh) | ✓✓✓ | LGPL-3.0-or-later | 96 | 0.970 | 326/326 | 20/20 | 1.00 | 1.00 | 1.00 | none |

## Licensing (mainline eve-dogma-rs is LGPL-3.0-or-later)

| variant | license | -only/-or-later from | LICENSE files (kind) | mergeable into LGPL-3.0-or-later mainline | reason |
|---|---|---|---|---|---|
| J | LGPL-3.0-or-later | README | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| F | LGPL-3.0-or-later | package metadata | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| B | LGPL-3.0-or-later | package metadata | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3); <branch root>/LICENSE (LGPL-3); <branch root>/LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| A | LGPL-3.0-or-later | package metadata | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| H | LGPL-3.0-or-later | package metadata | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3); <branch root>/COPYING (GPL-3); <branch root>/LICENSE (LGPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| C | LGPL-3.0-or-later | README | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3); <branch root>/LICENSE (LGPL-3); <branch root>/LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| E | GPL-3.0-or-later | package metadata | LICENSE (GPL-3) | **no** | GPL-3.0-or-later (LICENSE text, no LGPL) is stronger copyleft; cannot be relicensed into LGPL-3.0-or-later |
| I | LGPL-3.0-or-later | package metadata | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| D | LGPL-3.0-or-later | package metadata | <branch root>/LICENSE (LGPL-3); <branch root>/LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| G | LGPL-3.0-or-later | README | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |
| K | LGPL-3.0-or-later | package metadata | LICENSE (LGPL-3); LICENSE.GPL-3.0 (GPL-3) | **yes** | LGPL v3 LICENSE text + GPL companion text |

## Latency measurement (single CPU, own measurement)

| variant | ms/calc (median) | min | max | spread | valid/samples | N per sample | startup ms | flags |
|---|---|---|---|---|---|---|---|---|
| J | 0.0763 | 0.0761 | 0.0887 | 17% | 5/5 | 4032 | 7.91 | ok |
| F | 0.1005 | 0.0992 | 0.1262 | 27% | 5/5 | 4102 | 7.66 | ok |
| B | 0.0988 | 0.0981 | 0.0988 | 1% | 5/5 | 4122 | 7.8 | ok |
| A | 0.1204 | 0.1204 | 0.1204 | 0% | 5/5 | 2066 | 16.01 | ok |
| H | 0.2306 | 0.2261 | 0.3112 | 37% | 5/5 | 1766 | 7.93 | ok |
| C | 0.2339 | 0.2074 | 0.2341 | 11% | 5/5 | 1209 | 32.13 | ok |
| E | 0.1199 | 0.1198 | 0.1681 | 40% | 5/5 | 2076 | 16.14 | ok |
| I | 0.1245 | 0.1243 | 0.1406 | 13% | 5/5 | 3081 | 32.06 | ok |
| D | 1.8266 | 1.6239 | 2.0297 | 22% | 5/5 | 248 | 164.56 | ok |
| G | 2.2885 | 2.2878 | 2.7465 | 20% | 5/5 | 220 | 114.32 | ok |
| K | 1.1393 | 1.0124 | 1.2652 | 22% | 5/5 | 397 | 64.63 | ok |

## Per-run measurements

| variant | run | wall s | cases ok | run.py ms/calc (info only) | fits/s | cold ms | loadavg before | loadavg after |
|---|---|---|---|---|---|---|---|---|
| J | 1 | 1.1 | 326 | 0.027 | 18921 | 2.3 | [2.77, 1.92, 1.58] | [2.77, 1.92, 1.58] |
| J | 2 | 1.0 | 326 | 0.024 | 29311 | 2.2 | [2.77, 1.92, 1.58] | [2.77, 1.92, 1.58] |
| J | 3 | 1.0 | 326 | 0.026 | 28641 | 2.2 | [2.77, 1.92, 1.58] | [2.77, 1.92, 1.58] |
| F | 1 | 0.9 | 326 | 0.032 | 22589 | 1.8 | [1.27, 1.4, 1.31] | [1.56, 1.46, 1.33] |
| F | 2 | 0.9 | 326 | 0.034 | 21783 | 1.8 | [1.56, 1.46, 1.33] | [1.56, 1.46, 1.33] |
| F | 3 | 0.9 | 326 | 0.032 | 20379 | 1.8 | [1.56, 1.46, 1.33] | [1.56, 1.46, 1.33] |
| B | 1 | 1.9 | 326 | 0.031 | 19268 | 4.7 | [1.66, 1.14, 1.14] | [1.66, 1.14, 1.14] |
| B | 2 | 1.9 | 326 | 0.029 | 19053 | 4.6 | [1.66, 1.14, 1.14] | [1.61, 1.13, 1.14] |
| B | 3 | 1.9 | 326 | 0.033 | 20168 | 4.7 | [1.61, 1.13, 1.14] | [1.61, 1.13, 1.14] |
| A | 1 | 3.4 | 326 | 0.141 | 4360 | 7.9 | [1.02, 0.55, 0.97] | [1.18, 0.59, 0.98] |
| A | 2 | 3.3 | 326 | 0.134 | 4973 | 8.0 | [1.18, 0.59, 0.98] | [1.24, 0.61, 0.98] |
| A | 3 | 3.5 | 326 | 0.159 | 4847 | 8.4 | [1.24, 0.61, 0.98] | [1.24, 0.61, 0.98] |
| H | 1 | 2.6 | 326 | 0.266 | 3222 | 5.1 | [1.25, 1.44, 1.36] | [1.23, 1.44, 1.36] |
| H | 2 | 2.6 | 326 | 0.235 | 3240 | 5.2 | [1.23, 1.44, 1.36] | [1.23, 1.44, 1.36] |
| H | 3 | 2.7 | 326 | 0.242 | 3335 | 5.5 | [1.23, 1.44, 1.36] | [1.21, 1.43, 1.36] |
| C | 1 | 9.7 | 326 | 0.049 | 12794 | 27.5 | [2.74, 1.62, 1.31] | [2.47, 1.6, 1.31] |
| C | 2 | 9.7 | 326 | 0.046 | 13037 | 27.1 | [2.47, 1.6, 1.31] | [2.24, 1.58, 1.3] |
| C | 3 | 9.6 | 326 | 0.042 | 11937 | 27.1 | [2.24, 1.58, 1.3] | [2.06, 1.56, 1.3] |
| E | 1 | 4.2 | 326 | 0.178 | 4169 | 9.4 | [1.34, 1.47, 1.32] | [1.24, 1.44, 1.31] |
| E | 2 | 3.8 | 326 | 0.127 | 4377 | 8.7 | [1.24, 1.44, 1.31] | [1.24, 1.44, 1.31] |
| E | 3 | 3.7 | 326 | 0.122 | 4538 | 8.8 | [1.24, 1.44, 1.31] | [1.22, 1.44, 1.31] |
| I | 1 | 7.1 | 326 | 0.131 | 2108 | 17.8 | [1.64, 1.69, 1.49] | [1.61, 1.68, 1.49] |
| I | 2 | 7.0 | 326 | 0.129 | 2031 | 17.5 | [1.61, 1.68, 1.49] | [1.56, 1.67, 1.49] |
| I | 3 | 7.5 | 326 | 0.156 | 1956 | 18.8 | [1.56, 1.67, 1.49] | [1.48, 1.65, 1.48] |
| D | 1 | 38.6 | 326 | 0.526 | 1199 | 109.6 | [1.84, 1.53, 1.29] | [1.51, 1.48, 1.28] |
| D | 2 | 38.5 | 326 | 0.858 | 1168 | 109.3 | [1.51, 1.48, 1.28] | [1.26, 1.42, 1.27] |
| D | 3 | 38.5 | 326 | 0.603 | 1160 | 107.8 | [1.26, 1.42, 1.27] | [1.41, 1.43, 1.28] |
| G | 1 | 41.3 | 326 | 2.056 | 382 | 104.2 | [1.81, 1.59, 1.39] | [1.46, 1.53, 1.37] |
| G | 2 | 41.5 | 326 | 1.949 | 309 | 104.5 | [1.46, 1.53, 1.37] | [1.4, 1.51, 1.37] |
| G | 3 | 40.4 | 326 | 2.257 | 387 | 103.3 | [1.4, 1.51, 1.37] | [1.26, 1.46, 1.36] |
| K | 1 | 22.7 | 326 | 1.199 | 969 | 59.9 | [2.82, 1.98, 1.6] | [2.4, 1.94, 1.6] |
| K | 2 | 22.8 | 326 | 1.249 | 1067 | 60.0 | [2.4, 1.94, 1.6] | [2.27, 1.95, 1.61] |
| K | 3 | 22.6 | 326 | 0.985 | 1017 | 59.8 | [2.27, 1.95, 1.61] | [2.14, 1.95, 1.62] |

## Scoring rules

- **Version rule:** each variant is evaluated at its branch HEAD as of the cutoff (`--as-of`; unified scoring 2026-10-03T10:15:00+08:00). Self-reported "final" versions are reference only. A commit that fails the gate is **disqualified**; no fallback to an older commit.
- **Runs:** one untimed warm-up batch, then `--runs` official-scorer runs per variant, one variant at a time; perf = median.
- **Gate (correctness):** ranked only if the variant built, ran, and passed **all** bench cases (cases fully correct = cases, no engine errors) in every run.
- **Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability** (each in [0, 1]).
- `L(x, best, span) = clamp(1 − log10(x/best)/log10(span), 0, 1)` for lower-is-better `x` (1 = best ranked variant, 0 = `span`× worse).
- **Bench pin:** cases/expected/run.py from bench `3da9671` (1.8.0, 326 cases; = 0969967 cases), whatever upstream main is.
- **Latency** = own measurement (not run.py's): batch command pinned to one CPU (taskset), (t_N − t_1)/(N − 1) with N sized for ≈0.5 s of calcs; ≥5 independent samples, median; samples ≤0, < 0.002 ms, or > t_N/N are invalid; spread > 50 % ⇒ re-measure (≤3 extra), then flagged.
- **Licensing** (at the evaluated commit): judged by the LICENSE texts in the variant dir and branch root (LGPL header ± companion GPL text ⇒ LGPL; GPL header without LGPL ⇒ GPL); SPDX metadata/README only refine -only/-or-later. Mergeable into LGPL-3.0-or-later mainline: LGPL-3/permissive yes, GPL no, no file / conflict unknown. Informational, not scored.
- **Speed** = 0.5·L(latency ms/calc, 100) + 0.3·L(1/batch fits·s⁻¹, 100) + 0.2·L(cold-start ms, 100); medians over runs.
- **Maintainability** = 0.25·Tests + 0.20·DataDriven + 0.20·Size + 0.15·Docs + 0.10·Deps + 0.10·Build.
  Tests: passed → 0.6 + 0.4·min(1, log10(1+n)/2); failed → 0.2; timed out → 0.3; none → 0.
  DataDriven: L(h+10, h_min+10, 10), h = distinct dataset effect names (camelCase, ≥8 chars) referenced in hand-written core source (heuristic for per-effect special-casing).
  Size: L(core LOC, min, 10). Docs: 0.4 README + 0.4 DESIGN + 0.2 LICENSE. Deps: 1/(1+n/5), n = direct runtime deps. Build: L(build s, best, 100), only if every ranked build was fresh (`--fresh-clones`), else dropped and the other weights renormalised.
- **Features** = mean(EFT, RPC, search, type); EFT = ½ export (Pyfa byte-exact) + ½ eft_parse round-trip; others = share of RPC probes passing.
- **Portability** = 1 if a WASM/browser build exists in code, 0.5 if only documented, else 0.

## Reproduce

```
python3 tools/evaluate.py --as-of 2026-10-03T10:15:00+08:00 --runs 3 --fresh-clones
```

