# 18 — F vs J: dedicated engine evaluation (Rust codegen + WASM vs C++20)

> **Status: CANCELLED 2026-10-03 11:09 CST (Rust mainline based on F). Method kept as a record.** Placeholders `⟨…⟩` are filled in by later commits. Nothing in this
> document merges anything. The final section is a **recommendation only**, pending the user's confirmation.
>
> 中文摘要：用户把范围收窄到两个方案：F（Rust，构建期把 SDE 生成为代码，原生 + WASM）和 J（C++20，运行时加载二进制数据镜像，原生 + Emscripten WASM）。
> 本文先固定评测方法（本节），再逐项执行：图表、正确性与健壮性、速度（含 WASM 体积）、可维护性、可扩展性（两个引擎各做同样的三个实际改动练习）、
> 可迁移性、J 的提速手法能否移植进 F。每项单独 0–10 分并写明依据，最后只给合并建议，不做合并。

**Requested by** the user via eve (coordinator), 2026-10-03 ~11:00 CST. **Executed by** eve3.
**Conflict of interest:** eve3 is the author of J. To limit bias: every score below follows the rubric fixed in this
section *before* any measurement; the extensibility exercise in F is done by F's own author (the "EVE 方案F" bot) so
each engine is changed by the person who knows it best; numbers come from scripts whose commands are listed.

## 0. Subjects (pinned)

| | F | J |
|---|---|---|
| Repo / branch | `EX-CT/eve-dogma-lab` `variant-f` | `EX-CT/eve-dogma-lab` `variant-j` |
| Evaluated commit (round 1) | `bc84e2b` (2026-10-03 07:34 CST) | `3ab992d` (2026-10-03 09:07 CST) |
| Later heads (informational) | `af1c04b` (formats work, 09:18) | — (frozen) |
| Graph layer | `graphs-g4` (G4 = F + graphs, `f73ff1c` 10:55) | `graphs-j` (being written by another bot on top of `3ab992d`) |
| Language / build | Rust 2021, `build.rs` code generator, cargo | C++20, CMake + Ninja |
| Data | SDE compiled into the binary at build time | SDE converted at first run to an mmapped binary image |
| WASM | `wasm32-unknown-unknown` (C ABI) and `wasm32-wasip1` | Emscripten (`src/wasm.cpp`) |

Unless stated otherwise, all measurements use `dataset-3569502.json.gz` and fresh clones under
`/workspace/exct-eve/fvj-work/`. No timing run overlaps an official `evaluate*.py` run on the shared box
(`pgrep -af 'evaluate_graphs|tools/evaluate.py'` must be empty before any compile or benchmark).

## 1. Method

**已取消—2026-10-03 11:09 用户定 Rust 主线（以 F 为基础）**

> Cancelled 2026-10-03 11:09 CST: the user chose a Rust mainline based on F; J is no longer a candidate and the
> graphs-j port was stopped. The method below is kept as a record; no exercise, J WASM or J correctness runs were
> executed, and no exercise branches were created. F's correctness coverage is tracked in
> `eve-dogma-bench` `results/F-coverage/`.

Seven dimensions, each scored **0–10** on its own. There is deliberately **no single weighted total**: correctness
is a gate, and the recommendation (§9) argues from the per-dimension table. (For reference only, the round-1 weights
were speed 40 / maintainability 35 / features 15 / portability 10.)

### D1 Graphs (Pyfa graph families, contract 0.2 @ `0397d95`, 178 cases)
Source: the round-2 official run (`eve-dogma-bench@graphs-round2`, `tools/evaluate_graphs.py`,
`results/evaluation-graphs.{md,json}`) — F = G4; J = `graphs-j` once it exists.
Rubric: 10 × (cases passed / 178) through **every** interface offered (native and WASM), rounded down; −2 if there is
no WASM interface; capped at 5 if the underlying stats engine fails bench 1.8.0. **Pending** (not 0) for an engine
whose graph layer has not reached the gate yet.

### D2 Correctness and robustness (beyond the frozen round-1 bench)
Run by eve3 against **both** engines (F `bc84e2b`, J `3ab992d`; native builds):
1. eve-dogma-bench tag **`v1.9.0`** (331 cases, contract 1.4.4) — `bench.py` with the tag checked out.
2. **cap-suite** at `d80cc38` (150 cases) — `cap/run_cap.py --batch-cmd …`.
3. **pending-1.10**: the 8 `e_fz_*` minimal-repro cases (branch `pending-1.10`) and the **200 legal fuzz fits**
   (`gen_legal.py fits 200 10`, `/workspace/exct-eve/fz-e/work/fits`), compared against the stored Pyfa oracle
   output (`fz-e/work/out/oracle.jsonl`) with the bench-1.9.0 `metrics.py` tolerances. The Pyfa oracle is not re-run.
4. **Graphs contract 0.2** (178 cases) — taken from D1 (F: G4; J: pending until `graphs-j` passes).

For each: passed/total, every mismatching case id with metric and values (engine vs Pyfa), crashes, timeouts
(10 s per request) and non-determinism.
Rubric: start at 10; −1 per **distinct root cause** of a Pyfa mismatch in suites 1–3 (a bug class shared by many
cases counts once; mismatches ruled out of contract or caused by oracle data drift do not count); −3 per crash,
hang or non-JSON output; −1 if suites cannot be run at all (missing interface). Floor 0.

### D3 Speed
Inputs: round-1 official numbers (`eve-dogma-bench@579a21a` `results/evaluation.json`: single-CPU pinned latency
median, batch fits/s, cold start), plus WASM:
* artifact size of each engine's browser WASM build: raw / gzip -9 / brotli -q 11 bytes (plus JS glue);
* quick Node (v20+) numbers measured by eve3: module load + instantiate + dataset init (ms, median of 5 cold
  processes) and per-fit `calc` time (median over the 326 bench-1.8.0 requests, 3 passes after 1 warm-up pass);
* real-browser numbers (headless Chrome, page load to first result, per-fit in a Worker) are measured by **eve4**
  and merged into §4.3 when available; eve3 does not duplicate them.

Rubric: per metric, score_m = 10 × (best of the two / own) (lower-is-better metrics; inverted for fits/s). Weighted:
native latency 0.35, native throughput 0.20, native cold start 0.10, WASM per-fit 0.20, WASM transfer size (brotli,
including any data file the engine must fetch) 0.15. One decimal.

### D4 Maintainability
A 10-point checklist, one point each (half points allowed where stated), evidence from the evaluated commit:
1. A discoverable, passing automated test suite with > 0 tests (round-1 `evaluate.py` discovery) — 1.
2. That test suite checks outputs, not only that it runs (golden / parity tests) — 1.
3. Clean release build ≤ 30 s on the box (round-1 `build_s`) — 1 (½ if ≤ 60 s).
4. ≤ 3 runtime dependencies — 1.
5. README + DESIGN that explain architecture and trade-offs — 1.
6. Core hand-written LOC ≤ 6 000 — 1 (½ if ≤ 8 000).
7. Data-driven: ≤ 100 effects handled by hand-written code (round-1 `hardcoded_effects`) — 1.
8. Readability: no hand-written source file > 2 000 lines and no function > 300 lines — 1 (½ if one exception).
9. What a reviewer has to read for a data update is small (no regenerated multi-MB source in diffs/builds, or the
   generated code is never committed) — 1.
10. A new SDE can be used without rebuilding the engine — 1.

### D5 Extensibility — the same three real changes in both engines
Done on throwaway branches `fvj-exercise-f` / `fvj-exercise-j` in `EX-CT/eve-dogma-lab` (never merged; `variant-*`
untouched). F is changed by F's author, J by J's author (eve3). Each task is timed from the first look at the code
to "bench 1.8.0 still 326/326 and the task's acceptance check passes". Recorded per task: lines added + removed in
non-test source (`git diff --numstat`, tests/fixtures counted separately), files touched, minutes, bench result.

* **X1 — new attribute output.** Add `navigation.warp_capacitor_need` to FitStats: the ship's *modified*
  `warpCapacitorNeed` (attribute 153; Warp Drive Operation −10 %/level). Acceptance: present in every calc output;
  Rifter (587) with all skills V = 2.24e-06 × 0.5 = 1.12e-06; F and J agree on all 326 bench-1.8.0 requests.
* **X2 — new effects.** Use the patched dataset from
  [`tools/fvj/make_exercise_dataset.py`](../tools/fvj/make_exercise_dataset.py)
  (`python3 tools/fvj/make_exercise_dataset.py dataset-3569502.json.gz dataset-3569502-fvj.json.gz`), which adds:
  * **X2a (data-driven effect):** attribute 990001 `fvjExerciseVelocityBonus`, effect 990001
    `fvjExerciseVelocityBonusOnline` (online, one modifier: ItemModifier → ship `maxVelocity`, PostPercent from 990001),
    type 990001 "FVJ Exercise Injector" (low slot, value 10). Expected: the engine needs **no code change**, only
    whatever it takes to use a new dataset.
  * **X2b (hand-written effect, like a Pyfa python-only handler):** attribute 990002 `fvjExerciseSigBonus`,
    effect 990002 `fvjExerciseSigReductionOnline` with **no modifiers**, type 990002 "FVJ Exercise Sig Suppressor"
    (low slot, value −5). The engine must implement: while the module is online or active, ship `signatureRadius`
    (552) PostPercent by the module's 990002, stacking-penalised.
  Acceptance (patched dataset, all skills V): Rifter + 1 injector online → `max_velocity` = (unpatched Rifter
  value) × 1.10; Rifter + 2 suppressors online → `signature_radius` = (unpatched Rifter value) × (1 − 0.05) × (1 − 0.05 × 0.8691199806) (penalised second module); offline modules change nothing; F and J agree; bench 1.8.0 on the
  *unpatched* dataset still 326/326.
* **X3 — small RPC feature.** New `serve-stdio` method `attr`, params `{"fit": FitRequest, "attrs": [names]}` →
  `{"ship": {name: modified value, …}}`; an unknown attribute name → error code `UNKNOWN_ATTRIBUTE`; an invalid fit →
  the same error code as `calc`. Acceptance: Rifter all-V `{"attrs":["maxVelocity","warpCapacitorNeed"]}` equals
  `navigation.max_velocity` and the X1 value; F and J agree; existing RPC checks still pass.

Rubric per task: 10, then −2 if > 15 min (−4 if > 30 min), −2 if > 30 changed lines (−4 if > 100), −1 if > 2 files
(−2 if > 4); 0 if not completed or the bench regresses. X2 = mean of X2a and X2b. D5 = mean of X1, X2, X3.

### D6 Portability
10-point checklist:
1. Linux x86_64 native build from a clean clone (2).
2. Linux arm64: cross-compiled on the box if a toolchain is available, otherwise judged by inspection (no x86-only
   intrinsics without fallback) (1).
3. macOS and Windows: by inspection (POSIX-only calls such as `mmap`, `fork`; path handling; compiler flags) and by
   existing CI/release workflows (2).
4. Browser WASM build reproduced from a clean clone with a pinned toolchain, output identical to native on the 326
   bench-1.8.0 requests (2).
5. WASM usable without a WASI runtime or special server headers (1).
6. A new SDE in the browser without recompiling the engine (1).
7. Ease of porting the engine to another language/runtime (e.g. a TypeScript/Python/Kotlin port or FFI binding):
   judged from how much of the semantics lives in data vs code and in which language (1).

### D7 Can J's speed techniques be ported into F?
F's author (EVE 方案F bot) writes a separate analysis; it is merged verbatim into §8. eve3 adds a technical list of
J's techniques (from `variant-j/DESIGN.md`) with an estimate of applicability to F's architecture. Not scored on
the 0–10 scale; it feeds the recommendation (if F could absorb J's speed, the speed gap matters less).

### Recommendation (§9)
A merge recommendation only — which engine becomes the mainline, what to port from the other, and in which order.
No merging, no changes to `EX-CT/eve-dogma` (kept at `dd97e12`), until the user confirms.

## 2. D1 Graphs
⟨pending: round-2 G4 official run; J pending `graphs-j`⟩

## 3. D2 Correctness and robustness
⟨pending⟩

## 4. D3 Speed
### 4.1 Native (round 1)
⟨pending⟩
### 4.2 WASM size and Node numbers (eve3)
⟨pending⟩
### 4.3 WASM in a real browser (eve4) — PARTIAL (stopped 11:11 CST when the comparison was cancelled)
**Partial data. Not a full D3 run:** only 7 runs, on a shared box under load, with no repeat on an idle host.
Use it as a speed reference only.

- **Builds:** the deployed eve-fit-web artifacts (web `451c43e`). F is `variant-f` @ `af1c04b` (the branch head at build
  time, not the round-1 `bc84e2b`). J is `variant-j` @ `3ab992d`, built with Emscripten 6.0.11. Dataset: sde-3569502-r5.
- **Harness:** eve-fit-web `tools/bench-engines.mjs` (commit `6a08295`), run with
  `node tools/bench-engines.mjs http://127.0.0.1:4173/eve-fit-web/ <bench 1.8.0 @3da9671> 7 20`.
  - Both engines load on the same page, one after the other, in alternating order. Each run is a fresh headless Chrome
    with an empty cache.
  - The site is served locally by `python -m http.server`, uncompressed.
  - Both engines run in the main thread (the site runs the same code in a Web Worker).
  - Latency: for each of the 326 bench-1.8.0 FitRequests, 1 warm-up call, then the mean of 20 timed calls (Chrome
    coarsens `performance.now()` to 0.1 ms).
- **Host:** shared box with 8 vCPUs (Intel Xeon). The 1-minute loadavg was 4.9–6.1 throughout, so the box was busy
  and timings are noisy.

| | F | J |
|---|---|---|
| import JS glue (ms) | — | 13 |
| fetch .wasm (ms, localhost) | 56 | 8.9 |
| compile + instantiate (ms) | 115 | 9.6 |
| dataset fetch (ms) | — (compiled in) | 17 |
| dataset init: FS write + `evej_open` (ms) | — | 255 |
| first calc (ms) | 21 | 15 |
| **load total, median of 7 (ms)** | **192** | **390** |
| load total, min–max (ms) | 58–363 | 292–734 |
| calc per fit, median / p95 over 326 fits × 7 runs (ms) | 0.23 / 1.07 | 0.20 / 0.56 |
| calc, one Rifter, 50 blocks × 20 calls × 7 runs: median / p95 (ms) | 0.21 / 0.28 | 0.18 / 0.33 |

**Sizes** (gzip -9 and brotli q11 measured with Node zlib; GitHub Pages serves gzip):

| file | raw | gzip | brotli |
|---|---|---|---|
| F `eve_dogma_f.wasm` (SDE compiled in) | 3 767 633 | 862 921 | 641 807 |
| J `evej.wasm` | 948 622 | 329 029 | 253 723 |
| J `evej.mjs` (Emscripten glue) | 73 753 | 19 188 | 17 191 |
| dataset `dataset.json.gz` (J loads it at runtime; the web UI fetches it anyway) | 892 348 | — | — |

**Reading the numbers:**
- Load: F is faster because there is no dataset init. J spends about 255 ms turning the gzipped JSON dataset into its
  image. J's download is smaller, but J also needs the dataset. In the web UI that fetch is a cache hit, because the UI
  loads the same file.
- Per-calc latency is about the same in the browser. Median: J 0.20 ms vs F 0.23 ms. J's p95 is lower (0.56 vs
  1.07 ms). Both are far below a UI frame, so neither is a bottleneck on the page.
- Correctness in the same browser build: both pass the bench 1.8.0 corpus, 326/326 cases and 21051/21051 values
  (`tools/browser-dogma-bench.py`). Source: eve-fit-web CI run 37091912616 for J; a local run for F.

**Integration code in eve-fit-web** (`src/engine/worker.ts`):
- F: `initWasm` is 27 lines, a plain C-ABI wrapper (`alloc` / `calc` / `dealloc` / `rpc`) with no imports.
- J: `initEmjs` is 15 lines, plus the 73.8 kB Emscripten JS glue that ships with J. The adapter needs one `case` line
  for each engine.
- CI build step: F needs `cargo` with the `wasm32-unknown-unknown` target. J needs emsdk 6.0.11 + CMake + Ninja, and
  FetchContent downloads simdjson and libdeflate.

## 5. D4 Maintainability
⟨pending⟩

## 6. D5 Extensibility exercise
⟨pending: J by eve3; F by the F bot⟩

## 7. D6 Portability
⟨pending: not scored (comparison cancelled)⟩. **Partial observations from the browser work (eve4)** — measurements in §4.3:
- **Checklist item 4 (browser WASM build from a clean clone, pinned toolchain, same output as native):** both engines
  were built in eve-fit-web CI from pinned commits, and both pass 326/326 of bench 1.8.0 inside headless Chrome.
- **Item 5 (no WASI runtime or special server headers):** both run on GitHub Pages with no COOP/COEP headers. F's
  `wasm32-unknown-unknown` build has zero imports; J brings its own Emscripten JS glue.
- **Item 6 (new SDE without recompiling):** J loads the dataset at runtime, so yes. F compiles the SDE in, so a new SDE
  needs a rebuild. The site rebuilds F's WASM on each dataset release anyway.
- **Size:** F's WASM is about 4× larger, because the data is inside it.

## 8. D7 J's speed techniques in F
### 8.1 F author's analysis
⟨placeholder for the F bot's analysis⟩
### 8.2 Technical notes (eve3)
⟨pending⟩

## 9. Score table and recommendation
⟨pending⟩
