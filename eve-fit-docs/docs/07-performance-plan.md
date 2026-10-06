# 07 — Performance plan

## Targets

| Operation | Pyfa (measured, see below) | Target (Rust) |
|---|---|---|
| Process start + dataset load | Pyfa GUI 5–15 s; eos headless ≈ 1–2 s | ≤ 150 ms (JSON), ≤ 20 ms (binary snapshot) |
| Single fit full calc (warm) | 10–100 ms | ≤ 0.5 ms |
| Cap sim (typical) | 1–50 ms | ≤ 0.2 ms |
| 1 000 fits batch | ~1–2 min | ≤ 0.5 s single-threaded, parallel with rayon |
| DPS graph, 200 points | 0.5–2 s | ≤ 5 ms |

## Why Rust (vs Go / TS)

* No GC, flat `Vec`-indexed storage, f64 math identical across targets, WASM output small (≈ 300–600 kB).
* Go: comparable dev speed, 2–4× slower on map-heavy code, WASM weak. TS/V8: JIT good for hot loops but hash-map
  heavy dogma code and JSON dataset parse are slower; still acceptable for UI-only use.
* Decision: production core in Rust; a tiny TS kernel (stacking penalty + attribute fold) is kept in
  `eve-fit-mcp/bench/` purely as a cross-language micro-benchmark.

## Engine techniques

1. Dataset indexed once: `HashMap<TypeId, TypeIdx>` → dense arrays; effects pre-decoded into modifier structs.
2. Per calc: objects (ship, char, skills, modules, charges, drones…) in a `Vec`; per-object attribute map
   `FxHashMap<u32, AttrSlot>`; modifiers registered into target attribute lists; values computed lazily with memo.
3. Skills: only skills that have effects matter → pre-filtered list (≈ 500 of ≈ 600 skills).
4. Batch mode keeps dataset resident (`--batch`, `serve-stdio`, HTTP).

## Benchmark method vs Pyfa

* `eve-dogma-rs/oracle/pyfa_oracle.py` runs Pyfa's eos headless (wx stubbed, `db_update.py` → `eve.db`) on the
  **same FitRequest JSON**, and prints stats + timing (`time.perf_counter` around `fit.calculateModifiedAttributes()`
  + stat getters, after warm-up).
* `cargo bench` / `eve-dogma bench` measures the Rust engine on the same corpus.
* Corpus: community fits (dogma-engine test corpus) + synthetic fits per ship class; results appended to
  `PROGRESS.md` and `docs/07` tables.
