# 08 — Roadmap

| Milestone | Scope | Exit criteria |
|---|---|---|
| **M0 Docs** | 00–08, licensing, schemas | ✅ committed |
| **M1 Data** | `eve-sde-pipeline` converter + Actions + release | dataset for current TQ build |
| **M2 Core dogma** | attributes, operators, stacking, skills, modules/charges, implants, boosters, modes, subsystems, overrides, mutations | ship attrs match Pyfa oracle on corpus (abs/rel 1e-6) |
| **M3 Stats** | resources, slots, offense (turret/missile/drone/smartbomb), defense (HP/EHP/tank), cap (+sim), nav, targeting | stats match Pyfa |
| **M4 CLI/HTTP** | `calc`, `batch`, `serve`, `types` | schema-valid output, bench numbers |
| **M5 MCP** | search/get/validate/compute/compare/what_if/suggest | usable from Claude/Cursor/Grok |
| **M6 Projected & fleet** | projected modules/fits with distance, booster fits, environment effects, neut/RR, ECM | Pyfa parity on scenarios |
| **M7 Specials** | RAH, breacher, doomsday, vorton, fighters complete, mining, structures | |
| **M8 Formats** | EFT/DNA/XML/ESI/EFS/multibuy/killmail | round-trip tests |
| **M9 Graphs** | 10 Pyfa graph families | |
| **M10 WASM + Web UI** | wasm-bindgen package, minimal web UI | |
| **M11 Services** | ESI SSO skills/fits, prices, jargon search, presets | |

Order of execution for the autonomous session: M0 → M1 → M2 → M3 → M4 → M5 (skeleton) → tests vs oracle.
