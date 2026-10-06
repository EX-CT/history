# 21 — eve-optimizer and the character / skills input format (interface draft)

**中文摘要**：本文定义优化器组件 `eve-optimizer` 的接口草案，以及引擎的角色 / 技能输入格式。

- **角色输入**：一个 JSON 对象（`eve-character` v1），包括：
  - 技能等级（按 type_id）；
  - 克隆状态（alpha / omega；alpha 计划在 1.0 实现（待办，低优先级），需要 SDE 管线提供技能上限）；
  - 角色植入体；
  - 安全等级。
  它兼容现有 `FitRequest.character`。ESI、EVEMon 和手工输入都映射到这个格式（ESI 登录由网页端负责，以后做）。
- **优化器**：RPC 方法 `optimize`，CLI 命令 `eve-fit optimize`，WASM 通过 `rpc` 调用。
  - **v1 目标**：DPS、EHP、坦度、速度、电容稳定，以及在价格上限内最小化价格。
  - **约束**：CPU / PG / 校准值 / 槽位 / 硬点（始终是硬约束）、角色技能、元等级、属性下限、价格上限。
  - **搜索空间**：模块、弹药、改装件、无人机。
  - 每个候选装配都由引擎真实计算并校验。结果按目标排名，附带与原装配的差值。
- **格式**：EFT 等装配格式不属于引擎，由独立的 `eve-fit-formats` 处理（CLI / MCP 层转换）；优化器只接收结构化输入。
- **算法**：候选过滤 → 贪心构造 → 局部搜索（单 / 双替换）+ 束搜索。在给定种子和评估预算下结果确定。

**Status update 2026-10-03 14:30 CST: optimizer DEMOTED.** v1 is implemented (eve-dogma `crates/eve-optimizer`,
RPC/CLI/WASM `optimize`) and stays as is: tests must keep passing, no further work until the user re-prioritises (AI
will optimise through MCP `compute_batch`, see [docs/23](23-batch-api-and-prices.md)). Prices for `constraints.price`
and the price objective follow docs/23 §5 (`price_overrides`, `prices`) and docs/22 (snapshot). The character input
format (§1) is unaffected and current.

**Status: DRAFT, 2026-10-03 (CST).** Implements docs/20 P0-5 (optimizer) and the input-format part of P0-6
(character). The user approved docs/19/20 at 11:32. This document is the interface for review. Implementation starts
in `EX-CT/eve-dogma`, crate `crates/eve-optimizer`. Pyfa has no stat optimizer (only *Optimize Fit Price*, PRC-004).
Where Pyfa has an equivalent (skill requirements, alpha caps, price), behaviour follows Pyfa; no Pyfa code.

## 1. Character / skills input format (`eve-character` v1)

One JSON object. It is used in two ways:
- inline as `FitRequest.character`, which keeps today's fields valid;
- as a standalone file or RPC value, with `format`/`version` added.

```json
{
  "format": "eve-character", "version": 1,
  "name": "Pilot A", "source": "esi",
  "skills": { "default_level": 0, "levels": { "3300": 5, "3301": 4, "12441": 3 } },
  "clone": "omega",
  "implants": [10228, 13219],
  "security_status": -1.2,
  "skill_points": { "3300": 256000 }
}
```

| field | type | meaning | today |
|---|---|---|---|
| `skills.levels` | map of skill type_id (string) → 0..5 | trained level; ESI `active_skill_level` | have (`request.rs` `Skills`) |
| `skills.default_level` | 0..5 or null | level of every skill not listed. Null/absent = 0, both for a profile from ESI/EVEMon and in a bare `FitRequest` (today's engine and Pyfa oracle: absent = all skills 0). | have |
| `clone` | `"omega"` (default) or `"alpha"` | alpha: each skill capped at the alpha clone limit, and modules that need an omega-only skill level are invalid (ENG-CORE-009) | **Planned for 1.0 (TODO, low priority)**: Pyfa supports alpha clones and they are in 1.0 scope. Needs the alpha-clone skill caps from eve-sde-pipeline (eve4). Until it is implemented the engine answers `"alpha"` with a runtime `UNSUPPORTED` error (never guessed); `"omega"` works now. |
| `implants` | type_id list | character implants. They apply to every fit for this character unless the fit lists its own implants for that slot (Pyfa `implantSource`, ENG-IMP-002 / CHR-006). | new |
| `security_status` | number | as today | have |
| `skill_points` | map type_id → SP | optional; used only for train-time / plan output (CHR-009). Never changes stats. | new (optional) |
| `name`, `source` | string | informational: `esi`, `evemon`, `manual`, or `preset:all0|all4|all5` | new |

Rules:
- Unknown skill ids are ignored with a warning.
- A level above 5 is clamped, with a warning.
- Presets are named profiles: `{"preset": "all5"}` expands to `default_level: 5`.

Source mappings (the engine owns only the format; the web/MCP side does the fetching):
- **ESI:** `GET /characters/{id}/skills` gives `skills[].skill_id` and `active_skill_level`, plus `skillpoints_in_skill` → `skill_points`. `GET /characters/{id}/implants` → `implants`. Clone state comes from the client (ESI has no direct alpha flag); default omega.
- **EVEMon / CCP XML character sheet:** `<skill typeID level>` → `levels` (CHR-004, later).
- **Pyfa saved character:** per-skill levels → `levels` (eve-store migration, later).

RPC helpers (small, in `eve-rpc`):
- `character_validate {character}` → the normalised character plus warnings.
- `character_requirements {fit, character}` → missing skills: `[{skill_id, required, have}]`, and the plan (CHR-005).

## 2. Optimizer API

### 2.1 Request (`optimize`)

```json
{
  "base": { "...": "FitRequest: ship, any fixed modules, character, damage_pattern, target_profile, options" },
  "objective": { "metric": "dps", "direction": "max" },
  "constraints": {
    "skills": "character",
    "meta": { "max_meta_level": 5, "meta_groups": ["tech1", "tech2", "faction", "storyline"] },
    "cap_stable": true,
    "min": { "ehp": 25000, "max_velocity": 1500 },
    "price": { "max_isk": 150000000, "prices": { "2889": 1250000 } }
  },
  "search": {
    "slots": ["high", "mid", "low", "rig"],
    "charges": true, "drones": true,
    "keep": [0, 1],
    "candidates": "variations",
    "include_type_ids": [], "exclude_type_ids": [], "include_groups": [], "exclude_groups": []
  },
  "limits": { "max_evaluations": 20000, "time_ms": 3000, "results": 5, "seed": 0, "beam": 4 }
}
```

**Objective metrics (v1).** Every metric is read from the normal `calc` output, so the optimizer never has its own
formulas:

| metric | stat path | default direction |
|---|---|---|
| `dps` | `offense.total.dps.total` (weapons + drones + fighters). Variants: `weapon_dps`, `drone_dps`; `applied_dps` = `offense.vs_target_profile.dps` | max |
| `volley` | `offense.total.volley.total` | max |
| `ehp` | `defense.ehp.total` (under `base.damage_pattern`) | max |
| `tank` | sustained effective tank, `max(defense.tank.sustained_effective.*)` in EHP/s (active or passive, whichever is larger) | max |
| `speed` | `navigation.max_velocity`; `align_time` = `navigation.align_time_s` (min) | max |
| `cap_stable` | `capacitor.stable_percent` if stable, else `capacitor.depletes_in_s − 1e9` (any stable fit beats any unstable one) | max |
| `price` | sum of `constraints.price.prices` over ship + modules + charges + drones; an unpriced item is an error unless `price.missing: "zero"` | min |

`objective` may also be a weighted list `[{metric, weight, scale}]`, normalised by `scale` (v1 implements it, but
documents only a single metric as stable).

**Constraints:**
- **Always hard:**
  - CPU, PG, calibration;
  - high/mid/low/rig/subsystem/service slots, turret/launcher hardpoints;
  - drone bandwidth, drone bay;
  - fitting restrictions: `canFitShipType*` / `canFitShipGroup*`, `maxGroupFitted`, `maxTypeFitted`, `maxGroupActive`, rig size.
  These are checked by the engine's own validation: a candidate fit is accepted only if `calc` reports no
  violation. Today's codes:
  - `CPU_OVERLOAD`, `POWER_OVERLOAD`, `CALIBRATION_OVERLOAD`;
  - `SLOTS_EXCEEDED`, `RIG_SIZE`, `DRONE_BANDWIDTH`;
  - `MAX_GROUP_FITTED` / `ONLINE` / `ACTIVE`;
  - `MISSING_SKILL`.

  Not checked by validation yet (the candidate filter enforces them meanwhile):
  - turret/launcher hardpoints;
  - `canFitShipType*` / `canFitShipGroup*`;
  - `maxTypeFitted`.

  These become new validation codes as part of this work (`HARDPOINTS_EXCEEDED`, `SHIP_RESTRICTION`,
  `MAX_TYPE_FITTED`, matching Pyfa's fit restrictions).
- **`skills`:**
  - `"character"` (default when `base.character` has `levels`): only items whose required skills the character has (the engine's MISSING_SKILL check, same rule as Pyfa's `requiredSkills`). Alpha caps apply when `clone` = alpha.
  - `"ignore"`: anything goes. Each result then lists `missing_skills`.
- **`meta`:**
  - `max_meta_level`: SDE `meta_level`, which is in the dataset.
  - `meta_groups`: SDE `meta_group` (1 tech1, 2 tech2, 3 storyline, 4 faction, 5 officer, 6 deadspace, 14 tech3, 15 abyssal, 17 premium, 52/53 structure) by name.
- **`cap_stable`:** `true` means stable at any level. `{"min_percent": p}` means `stable_percent ≥ p`.
- **`min` / `max`:** floors and ceilings on any metric above, or on any numeric stat path given as `/a/b/c`.
- **`price.max_isk`:** total price ceiling. Prices come from the caller (the engine is offline). `eve-prices` (P1-5) will fill `prices` later.

**Search space:**
- **`slots`:** the racks the optimizer may change. Modules listed in `base` at indices in `keep` stay fixed. Every other `base` module is a starting point that may be replaced.
- **`candidates`:**
  - `"variations"` (default): the items that share each base module's variation family (SDE `variation_parent`), filtered by meta.
  - `"group"`: the same inventory group.
  - `"all_fittable"`: every published module that fits the slot, the ship and the constraints. Larger; needs a bigger budget.
  - Empty slots always draw from `"all_fittable"` for that slot, pruned as in §3.
- **`charges`:** for each weapon, every compatible charge (`chargeGroup*`, `chargeSize`), filtered by meta. Picked per weapon for the objective.
- **`drones`:** the drone bay and bandwidth are filled from drones the character can use. Active drones are capped by `maxActiveDrones`.
- **`rigs`:** included through `slots`; rig size and calibration are enforced.

**Limits:**
- `max_evaluations`: the number of engine `calc` calls. This is the only budget on wasm32-unknown-unknown, which has no clock.
- `time_ms`: native only.
- `results`: how many distinct ranked fits to return.
- `seed`: tie-breaking and local-search order. The result is deterministic for a fixed `(request, seed, max_evaluations)`; `time_ms` can make it vary.
- `beam`: number of partial fits kept per construction step.

### 2.2 Response

```json
{
  "results": [
    {
      "rank": 1,
      "fit": { "...": "FitRequest, ready for calc (and for format_export in eve-fit-formats)" },
      "objective": 412.7,
      "metrics": { "dps": 412.7, "ehp": 26120.4, "max_velocity": 1612.0, "cap_stable": true, "price_isk": 98400000 },
      "delta": { "dps": 61.3, "ehp": -1880.0 },
      "changes": [ { "slot": "low", "index": 3, "from": 519, "to": 13939 } ],
      "missing_skills": [],
      "eft": "[Rifter, optimized #1] ..."
    }
  ],
  "base_metrics": { "dps": 351.4 },
  "evaluated": 8412,
  "stopped_by": "converged",
  "warnings": []
}
```

- `stopped_by` is one of `converged`, `evaluations` or `time`.
- `eft` is optional text added by surfaces that link `eve-fit-formats` (the `eve-fit` CLI / `serve-stdio`, MCP). Formats
  are not part of the engine (ruling 2026-10-03): `eve_optimizer` itself and the engine WASM return `fit` only; a
  frontend converts with the `eve-fit-formats` WASM module.
- `delta` is relative to the base fit (which is evaluated first; if it is invalid its metrics are reported and `delta` is null).
- **Errors:** contract error codes, plus:
  - `OPT_NO_FEASIBLE` (no fit meets the constraints; returns the closest one with the violated constraints);
  - `OPT_BAD_METRIC`;
  - `OPT_MISSING_PRICE`.

### 2.3 Surfaces

| surface | form |
|---|---|
| Rust | `eve_optimizer::optimize(&OptimizeRequest) -> Result<OptimizeResult, OptError>`; `eve_optimizer::Evaluator` trait (default: `eve_dogma::calc`) so tests can stub it |
| RPC | `{"method":"optimize","params":OptimizeRequest}` in `serve-stdio`, the engine WASM (`eve-wasm`) `rpc` export, and later HTTP; structured input only |
| CLI | `eve-fit optimize < optimize_request.json`; `--eft FILE` to start from an EFT fit (the CLI converts it with `eve-fit-formats` before calling the optimizer); `--character FILE` |
| MCP | `optimize_fit` (eve4) calls `optimize`; `suggest_*` may use `search.candidates` with a small budget |

## 3. Algorithm (v1)

1. **Candidate sets** per changeable slot:
   - filter by slot, hardpoint type, ship restrictions, skills, alpha caps, meta, price, include/exclude;
   - drop items with no effect on any metric in the objective or the constraints. An item counts as having an effect if it modifies an attribute that one of those stats reads, using the per-effect modifier tables the codegen already emits;
   - drop items dominated on (objective contribution, CPU, PG, calibration, price) within the same slot family, based on a single-module probe on the base hull;
   - keep at most N per slot (default 40).
2. **Greedy construction with a beam:**
   - fill slots in order rig → high → low → mid, choosing at each step the candidate with the best objective gain per unit of resource slack used;
   - keep the `beam` best partial fits;
   - choose charges and drones after each rack (charges per weapon by objective; drones by bandwidth/bay knapsack on drone DPS or the objective).
3. **Local search:**
   - single swaps, then pair swaps (to trade CPU/PG between modules), on the best fits until no swap improves or the budget runs out;
   - stacking penalties and set bonuses are handled implicitly, because every step is a real `calc`.
4. **Feasibility:**
   - every scored fit is a real `calc` with validation on;
   - floors (`min`, `cap_stable`, price) are hard: an infeasible fit scores below any feasible one, ordered by total constraint violation, so the search can pass through it;
   - batches of candidate fits are evaluated in parallel on native (the batch worker pool) and serially on wasm.
5. **Results:** distinct fits (by module multiset), best first, re-verified by `calc`.

Expected cost: about 0.06 ms per `calc`, so 20 000 evaluations take ≈1.2 s single-thread native and ≈2–3 s in WASM.

## 4. Crates and data

- `crates/eve-optimizer` depends on `eve-dogma` and `eve-fit-model` only, never on `eve-fit-formats` (formats are not
  part of the engine; EFT in/out is done by the CLI/MCP layer).
- `crates/eve-character` holds the input format, validation, alpha caps, the requirements/plan helpers and the
  presets. Until it exists, the types live in `eve-fit-model` (`Character`, `Skills`; re-exported as `eve_dogma::request`).
- Data the dataset already has:
  - `meta_level`, `meta_group`, `variation_parent`, `market_group`;
  - required skills;
  - fitting restriction attributes.
- Needed from `eve-sde-pipeline` (eve4, docs/20 §2): alpha-clone skill caps; skill rank/SP for train time.
  **Alpha clones: planned for 1.0 (TODO, low priority).** Until implemented, `clone: "alpha"` gets a runtime
  `UNSUPPORTED` error rather than guessed caps.

## 5. Tests (docs/20 §5.4)

- **Property tests** (fixed seeds): every returned fit
  - re-calcs with no violation;
  - needs no skill the character lacks (`skills: character`);
  - meets every floor and the price cap;
  - leaves `keep` modules unchanged.
- **Skill monotonicity:** All 0 ≤ custom ≤ All V on the best objective, for fixed search settings.
- **Regression corpus** `optimizer-suite` (eve-dogma-bench branch): about 30 requests (frigate to battleship, each objective,
  with and without price caps). The CI gate is "objective ≥ last recorded best", plus determinism (same seed gives
  byte-identical results).
- **Oracle:** Pyfa has no optimizer. Pyfa checks the *metrics* of returned fits through the usual oracle (any
  result fit can be scored like a bench case). Price optimisation (PRC-004) is checked against Pyfa's Optimize Fit
  Price where the inputs coincide.

## 6. Open questions for the user

1. Is the default objective set right (dps, ehp, tank, speed, cap_stable, price), and should `applied_dps` vs a
   target profile be in v1?
2. Default candidates: `variations` (fast, predictable) or `all_fittable` (wider, slower)?
3. ~~Alpha clones in v1?~~ Ruled 2026-10-03: in scope for 1.0, low priority (planned/TODO); the optimizer v1 may ship
   before them, with the runtime `UNSUPPORTED` error for `clone: "alpha"` meanwhile.
4. Price source for v1: caller-supplied map only (offline engine), with `eve-prices` later. Is that OK?
