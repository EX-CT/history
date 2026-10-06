# EX-CT History

Consolidated archive of the pre-migration `eve-*` repositories. Each project is
merged into this repository as a top-level directory **with its full git
history preserved** — `git log --follow <dir>/` walks back into the original
project's commits.

These repositories were archived after the EXFA migration. Their successors:

| Directory | Successor | Notes |
|---|---|---|
| `eve-dogma-rs/` | [EXFA-Engine](https://github.com/EX-CT/EXFA-Engine) | Rust fitting engine |
| `eve-sde-pipeline/` | [EXFA-Data](https://github.com/EX-CT/EXFA-Data) | SDE dataset + prices pipeline |
| `eve-dogma-bench/` | [EXFA-Bench](https://github.com/EX-CT/EXFA-Bench) | Test suites + Pyfa oracle |
| `eve-fit-docs/` | [EXFA-Docs](https://github.com/EX-CT/EXFA-Docs) | Architecture + process docs |
| `eve-fit-web/` | [EXFA-App](https://github.com/EX-CT/EXFA-App) `apps/web` | Web fitting UI |
| `eve-fit-mcp/` | [EXFA-App](https://github.com/EX-CT/EXFA-App) `packages/mcp` | MCP server + CLI |
| `eve-dogma/` | superseded by `eve-dogma-rs` → EXFA-Engine | Earlier Python dogma prototype |
| `eve-dogma-lab/` | not migrated | Experimental lab work (engines/, lab-g1) |
| `eve-market-prices/` | superseded by EXFA-Data prices workflow | Old market-price fetcher |
| `eve-incursions/` | standalone, archived as-is | Incursions fits tool |

The original repositories are **archived** (read-only) on GitHub — this
repository is a consolidated, browsable copy, not the only record.

Tags from the source repositories are preserved under their original names.
