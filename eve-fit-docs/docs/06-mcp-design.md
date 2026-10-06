# 06 — MCP server design (`eve-fit-mcp`)

> 中文：MCP 服务器让 AI 能“搜物品 → 组装配置 → 校验 → 计算 → 比较 → 迭代优化”。所有工具都是无状态的（输入完整配置），
> 另提供可选的本地存档（角色/配置/伤害模型）。

## Runtime

* TypeScript, `@modelcontextprotocol/sdk`, transports **stdio** (desktop agents) and **Streamable HTTP**.
* Engine binding, in order of preference: (1) WASM build of `eve-dogma-rs` (in-process, no native deps),
  (2) `eve-dogma` CLI subprocess in `--serve-stdio` JSONL mode (persistent process, dataset loaded once),
  (3) remote HTTP `eve-dogma serve`. Current implementation: (2) with fallback to one-shot CLI.
* Dataset: same `dataset-<build>.json.gz`; the MCP also builds an in-memory search index (names in all SDE
  languages incl. zh, plus Pyfa-style jargon: "mwd", "ab", "lse", "dc", "rah", "sebo", "tp", "web", "scram", "point").

## Tools

| Tool | Input | Output | Notes |
|---|---|---|---|
| `search_types` | `query`, `category?` (ship/module/charge/drone/fighter/implant/booster/skill), `slot?`, `limit` | `[{type_id, name, group, category, meta_level, slot}]` | fuzzy + jargon, multilingual |
| `get_type` | `type_id` or `name` | attributes (named, with units), effects, required skills, traits, variations | "Show info" |
| `list_ship_slots` | `ship` | slots, hardpoints, resources, bonuses (traits) | |
| `parse_fit` | `text` (EFT/DNA/ESI/XML/link) | FitRequest | uses `fit-formats` |
| `export_fit` | FitRequest, `format` | text | EFT/DNA/ESI/multibuy |
| `validate_fit` | FitRequest | violations | cheap path |
| `compute_fit` | FitRequest, `sections?` | FitStats | the core call |
| `compare_fits` | `[FitRequest]`, `metrics?` | table of deltas | |
| `what_if` | FitRequest, `changes[]` (add/remove/replace module, change state/charge/skill) | stats delta per change | single batch call |
| `suggest_modules` | FitRequest, `slot`, `goal` (dps/ehp/speed/cap/…), `constraints` (cpu/pg/price/meta) | ranked candidates with stat deltas | brute-force over compatible types, batched |
| `optimize_fit` | ship, goal, constraints, `budget_iterations` | best FitRequest + stats + trace | greedy + local search (engine is fast enough) |
| `skill_requirements` | FitRequest | skills needed, missing vs character | |
| `damage_profiles` / `target_profiles` | – | built-in presets | |
| `graph` | FitRequest, `kind`, `x_range` | series | dps-vs-range, cap-vs-time, speed-vs-time… |
| `price_fit` (optional, network) | FitRequest, `source` | ISK totals | only non-deterministic tool, clearly labelled |

## Resources & prompts

* Resources: `eve://dataset/meta`, `eve://type/{id}`, `eve://ship/{id}/slots`, `eve://schema/fit-request`.
* Prompts: `fit_for_role` ("build a <ship> for <activity>, budget …"), `review_fit` (explain weaknesses),
  `explain_stat` (why is my align time X — uses `sources`).

## Design rules for AI-friendliness

1. Every tool accepts names *or* IDs; responses always return both.
2. Errors are actionable (`"Module 'Large Shield Extender II' does not fit a rig slot; did you mean slot=mid?"`).
3. Outputs are compact by default (`sections` param), with units in keys (`_m`, `_s`, `_gj_s`).
4. Deterministic & stateless → the agent can replay/compare freely; `request_hash` lets it cache.
