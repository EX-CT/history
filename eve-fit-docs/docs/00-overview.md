# 00 — Overview: vision, alternatives, recommendation

> 中文结论：推荐 **方案 A —— Rust 核心（数据驱动 dogma + 少量手写特殊效果）**，同一份核心编译为原生 CLI、HTTP 服务和 WASM；
> SDE 单独处理成紧凑版本化数据包；MCP 服务器（TypeScript）通过 CLI/HTTP（后续 WASM）调用核心；前端完全解耦。

## 1. Vision

A modern, open-source, AI-friendly replacement for [Pyfa](https://github.com/pyfa-org/Pyfa):

* **Every Pyfa feature** (stats, graphs, import/export, profiles, projected/command, mutated modules, environment…).
* **A pure function at the bottom**: `stats = compute(dataset_version, request)`. The request contains *everything*
  (skills, fit, module states, charges, mutations, implants, boosters, drones, fighters, fleet boosts, projected
  fits/modules, environment/system effects, target profile, damage pattern, options). No DB, no session, no hidden
  global state → reproducible, cacheable, trivially parallel, perfect for AI agents and external tooling.
* **Data pipeline separate from code**: CCP's official SDE (JSONL, build-numbered) → a compact, versioned
  `engine dataset` published as GitHub Release assets by GitHub Actions.
* **Faster than Pyfa by 2–3 orders of magnitude** for a single fit (target: < 1 ms warm, Pyfa ≈ 50–500 ms).
* **MCP server** so an LLM can search items, validate, compute, compare and iteratively optimise fits.
* **Frontend decoupled**: a web UI (WASM in-browser, or HTTP) is a client like any other.

## 2. Requirements recap (from owner)

| # | Requirement | Where addressed |
|---|---|---|
| R1 | Reproduce *all* Pyfa features | 01, 03 (checklist) |
| R2 | SDE processed separately, GitHub based | 04, `eve-sde-pipeline` |
| R3 | Faster than Pyfa; evaluate Rust/Go/TS | 07 |
| R4 | Stateless CLI/API, full input → deterministic output | 05, `eve-dogma-rs` |
| R5 | Comprehensive MCP | 06, `eve-fit-mcp` |
| R6 | Core decoupled from frontend; web OK | 00 §4 |

## 3. Key technical insight that drives the design

Pyfa (eos) **does not interpret the SDE's `modifierInfo`**. It ships ~2 400 hand-maintained Python effect handlers
(`eos/effects.py`, 43 803 lines, `class EffectNNNN` with `handler(fit, item, context, projectionRange)`), originally
generated from the old `expression` trees and patched by hand ever since. That is the main reason it is slow and
hard to maintain, and it means every game patch needs code changes.

The modern SDE (2025+ rework, JSONL) contains `modifierInfo` for the vast majority of effects
(domain/func/modifiedAttributeID/modifyingAttributeID/operation, plus group/skill filters). CCP's own server uses
this. EVEShipFit's dogma-engine is data-driven on top of it, needing only a small set of hand-written extras.

So the new engine is **data-driven first**, with a **registry of "special effects"** (≈ 60–120 effects with no
`modifierInfo`: weapon damage, local/remote reps, propulsion speed boost, cap boosters/neuts/nos, ECM/ewar
projection, command burst buff dispatch, RAH adaptation, spool-up, breacher DoT, doomsday, fighter abilities,
structure services, …). Each special effect is a small, unit-tested Rust function referenced by effect ID/name.

## 4. Architecture alternatives

### A. Rust core, multi-target (RECOMMENDED)

```
CCP SDE (JSONL zip) ─▶ eve-sde-pipeline (Python/Rust, GitHub Actions) ─▶ dataset-<build>.json.zst / .bin (Release)
                                                                          │
                     ┌─────────────────────── eve-dogma-rs ───────────────▼──────────────────────┐
                     │ dogma-data (load, index)  dogma-core (attrs/modifiers/stacking/special fx) │
                     │ fit-stats (DPS, tank, cap sim, nav, targeting, mining, remote, graphs)     │
                     │ fit-formats (EFT, DNA, XML, ESI JSON, multibuy, killmail)                  │
                     └──┬─────────────┬────────────────┬──────────────────┬─────────────────────┘
                        │ CLI (stdin  │ HTTP (axum,    │ WASM (wasm-bindgen│ napi / pyo3 (opt.)
                        │ JSON→JSON)  │ stateless)     │ for web UI)       │
                        ▼             ▼                ▼                   ▼
                     eve-fit-mcp (TS, MCP stdio/HTTP)   web UI (any framework)  scripts/bots
```

* + Fastest (native, no GC), deterministic f64 math, one codebase for native + browser (WASM) + Node + Python.
* + Matches dogma-engine's language: can learn from (MIT) code and interoperate.
* − Steeper contributor curve than TS/Python; compile times.

### B. Go core + Go MCP single binary

* Core in Go, `net/http` API, MCP via `mark3labs/mcp-go`; one static binary.
* + Simple, fast enough (≈ 2–5× slower than Rust, still ≫ Pyfa), great for servers.
* − WASM output large (TinyGo limits); no sharing with browser; GC pauses irrelevant here but bigger memory.

### C. TypeScript everywhere

* Core in TS, runs in browser/Node/Deno/Bun; MCP via official TS SDK; UI in same repo.
* + Lowest friction for web UI and MCP; huge ecosystem.
* − 3–10× slower than Rust for cap sim / graph sweeps; floating-point identical but perf-sensitive graph sampling
  (thousands of points × fits) suffers; dataset loading heavier.

### D. Keep Python: port eos + Rust accelerator (rejected)

* Reuse Pyfa's 2 400 handlers, accelerate attribute math with PyO3.
* − Inherits the slow handler model, GPL/LGPL entanglement, Python startup (≈ 1 s with data load); doesn't meet R3.

### Comparison

| Criterion | A Rust | B Go | C TS | D Py+Rust |
|---|---|---|---|---|
| Single-fit latency (warm) | ★★★★★ ~0.1–1 ms | ★★★★ ~0.5–3 ms | ★★★ ~2–10 ms | ★ 20–200 ms |
| Browser (offline) | WASM ★★★★★ | ★★ | native ★★★★★ | ✗ |
| MCP ecosystem | via TS wrapper ★★★★ | ★★★★ | ★★★★★ | ★★★ |
| Maintainability of effects | data-driven ★★★★ | ★★★★ | ★★★★ | ★★ |
| Contributor friendliness | ★★★ | ★★★★ | ★★★★★ | ★★★★ |

## 5. Recommendation

**A**: Rust core (`eve-dogma-rs`) with CLI + HTTP now and WASM next; MCP in TypeScript (`eve-fit-mcp`) calling
the core through the CLI/HTTP today and the WASM build later (zero native deps). A Go or TS port of the *core*
is not needed for production; a minimal TS prototype of the stacking-penalty/attribute kernel may be kept only as
a benchmark baseline (see 07).

## 6. Statelessness contract (R4)

* Input fully determines output; dataset is addressed by `sde_build` (e.g. `3569502`) and dataset hash.
* No clocks, no RNG, no network in the core. Prices are *not* core — they're an optional enrichment service.
* Output is versioned (`schema_version`), keys stable, numbers as f64 (rounding is a presentation concern; Pyfa
  only rounds cpu/power to 2 dp internally, we mirror that for parity).
* Characters/fits/profiles persistence is a client concern (UI/MCP may keep a local store), never the core's.
