# EX-CT History

Consolidated archive of the deleted pre-migration `eve-*` repositories. Each
project was merged into this repository as a top-level directory **with its
full git history preserved** — `git log --follow <dir>/` walks back into the
original project's commits. Source tags were kept under their original names.

The original repositories have been **deleted**; this repository is the
canonical record.

## Projects / 项目

| Directory | Successor | Notes |
|---|---|---|
| `eve-dogma-rs/` | [EXFA-Engine](https://github.com/EX-CT/EXFA-Engine) | Rust fitting engine |
| `eve-sde-pipeline/` | [EXFA-Data](https://github.com/EX-CT/EXFA-Data) | SDE dataset + prices pipeline |
| `eve-dogma-bench/` | [EXFA-Bench](https://github.com/EX-CT/EXFA-Bench) | Test suites + Pyfa oracle |
| `eve-fit-docs/` | [EXFA-Docs](https://github.com/EX-CT/EXFA-Docs) | Architecture + process docs |
| `eve-fit-web/` | [EXFA-App](https://github.com/EX-CT/EXFA-App) `apps/web` | Web fitting UI |
| `eve-fit-mcp/` | [EXFA-App](https://github.com/EX-CT/EXFA-App) `packages/mcp` | MCP server + CLI |
| `eve-dogma/` | superseded by `eve-dogma-rs` → EXFA-Engine | Earlier Python dogma prototype |
| `eve-dogma-lab/` | not migrated | Engine architecture bake-off (engines/, lab-g1) |
| `eve-market-prices/` | superseded by EXFA-Data prices workflow | Old market-price fetcher |
| `eve-incursions/` | no successor | Incursions fits tool, retired |

## Release assets / Release 资产

Release assets are not part of git history, so the deleted repositories'
release files are preserved as archive releases on this repository:

- [`archive-eve-sde-pipeline`](https://github.com/EX-CT/history/releases/tag/archive-eve-sde-pipeline) —
  historical SDE dataset builds (32 assets)
- [`archive-eve-fit-mcp`](https://github.com/EX-CT/history/releases/tag/archive-eve-fit-mcp) —
  eve-fit-mcp release tarballs (27 assets)
- [`archive-eve-market-prices`](https://github.com/EX-CT/history/releases/tag/archive-eve-market-prices) —
  daily jita4 price snapshots (15 assets)

Asset names are prefixed with their original release tag, e.g.
`sde-3569502-r5__dataset-3569502-r5.json.gz`.
