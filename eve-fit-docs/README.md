# eve-fit-docs — EXCT EVE Fitting Toolkit: design & analysis

**中文摘要**：本仓库是 EXCT「现代化、AI 友好的 EVE Online 配船工具」的设计文档库。目标是完整复现 Pyfa 的全部功能，
但以 *无状态核心引擎（Rust）+ 独立 SDE 数据管线 + CLI/HTTP/WASM API + MCP 服务器* 的方式重写，使其更快、可被 AI 直接调用。
所有文档英文为主，关键结论附中文。

## Repositories (GitHub org `EX-CT`)

| Repo | Purpose | License |
|---|---|---|
| [`eve-fit-docs`](https://github.com/EX-CT/eve-fit-docs) | Plans, analysis, parity checklist, JSON schemas | CC-BY-4.0 (docs), MIT (schemas) |
| [`eve-sde-pipeline`](https://github.com/EX-CT/eve-sde-pipeline) | CCP SDE (JSONL) → compact versioned engine dataset; GitHub Actions | MIT |
| [`eve-dogma-rs`](https://github.com/EX-CT/eve-dogma-rs) | Rust dogma engine + stats + stateless CLI / HTTP (+WASM later) | LGPL-3.0-or-later |
| [`eve-fit-mcp`](https://github.com/EX-CT/eve-fit-mcp) | MCP server exposing search/validate/compute/compare/suggest | MIT |

## Documents

| # | Document | Content |
|---|---|---|
| 00 | [overview](docs/00-overview.md) | Vision, requirements, 4 architecture alternatives, recommendation |
| 01 | [pyfa-analysis](docs/01-pyfa-analysis.md) | How Pyfa/eos computes everything, with file references |
| 02 | [dogma-engine-analysis](docs/02-dogma-engine-analysis.md) | EVEShipFit dogma-engine internals + gaps vs Pyfa |
| 03 | [feature-parity-checklist](docs/03-feature-parity-checklist.md) | Exhaustive Pyfa feature inventory with status columns |
| 04 | [sde-pipeline](docs/04-sde-pipeline.md) | Data sourcing, CCP JSONL SDE, dataset format, CI |
| 05 | [api-schema](docs/05-api-schema.md) | Stateless request/response contract (+ `schema/*.json`) |
| 06 | [mcp-design](docs/06-mcp-design.md) | MCP tools/resources/prompts for AI fitting |
| 07 | [performance-plan](docs/07-performance-plan.md) | Language comparison, perf targets, benchmark method vs Pyfa |
| 08 | [roadmap](docs/08-roadmap.md) | Milestones |
| 09 | [engine-round-1-evaluation](docs/09-engine-round-1-evaluation.md) | Bake-off of engine variants A–K: method, scoring, results, decision (draft) |
| 10 | [round-2-graphs-plan](docs/10-round-2-graphs-plan.md) | Round 2: Pyfa graphs — contract summary, four implementation approaches, bench plug-in (draft) |
| 12 | [repo-hygiene-audit](docs/12-repo-hygiene-audit.md) | All public repos and branches, full history: licences, Pyfa code, large blobs, secrets, artifacts; rewrite proposals |
| 13 | [engine-round-2-evaluation](docs/13-engine-round-2-evaluation.md) | Graphs bake-off G1–G4: method, scoring, licensing, results, decision (draft) |
| 14 | [mutated-modules](docs/14-mutated-modules.md) | Mutated modules (mutaplasmids) + implant/booster combos: Pyfa semantics, request format, `mutated-suite` (93 cases), per-engine changes, scoring (draft) |
| 15 | [fuzz-triage](docs/15-fuzz-triage.md) | Legal random-fit fuzz (200 fits) A vs Pyfa, E ref: class counts, 5 A bugs with `pending-1.10` repro ids |
| 17 | [fuzzing-and-ci](docs/17-fuzzing-and-ci.md) | Differential fuzz + Pyfa oracle adjudication, pending-case flow, state ruling, nightly CI and Pyfa-free invariants |
| 18 | [f-vs-j](docs/18-f-vs-j.md) | Dedicated F (Rust codegen + WASM) vs J (C++20) evaluation: method, correctness suites, speed incl. WASM, maintainability, extensibility exercise, portability, merge recommendation (draft) |
| 19 | [pyfa-feature-inventory](docs/19-pyfa-feature-inventory.md) | Complete Pyfa v2.69.0 feature inventory (scope baseline: never less than Pyfa): 200 items with stable IDs, F / MCP / web status + evidence; YAML source + CSV |
| 20 | [rust-architecture-plan](docs/20-rust-architecture-plan.md) | Proposal: Rust mainline on F — crate layout, J speed techniques, prioritized gaps with effort, inventory→test gate, bot work split |
| 21 | [optimizer-and-character-input](docs/21-optimizer-and-character-input.md) | Draft interface: `eve-optimizer` (RPC/CLI/WASM `optimize`: objectives, constraints, search space, algorithm, tests) and the `eve-character` skills/character input format (ESI/EVEMon mapping) |
| — | [LICENSING](LICENSING.md) | License decisions (Pyfa GPLv3 / eos LGPL / CCP data) |
| — | [PROGRESS](PROGRESS.md) | Done / next, for resuming work |

## License

- Documentation (everything except `schema/`): **CC-BY-4.0**. See [`LICENSE`](LICENSE).
- JSON schemas in [`schema/`](schema): **MIT**. See [`schema/LICENSE`](schema/LICENSE).
- The documents quote short excerpts and paths from Pyfa (GPL-3.0 / eos LGPL) for commentary. Those excerpts keep their
  original licence. EVE Online names and data are © CCP hf. Policy: [LICENSING.md](LICENSING.md).

中文：文档采用 CC-BY-4.0（`LICENSE`），`schema/` 下的 JSON Schema 采用 MIT（`schema/LICENSE`）。
