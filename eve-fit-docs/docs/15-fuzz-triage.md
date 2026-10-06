# 15 — Stats-engine fuzz triage: legal random fits, A vs Pyfa

**中文摘要**：用 Pyfa 的装配规则生成了 200 个**合法**随机装配，比较 A (eve-dogma-rs e4c42db) 与 Pyfa 预言机，并以 E (variant-e 5867d53) 作参照。
共比较 12 057 个数值，结果如下：
- 190 个装配完全一致；
- 2 个属于 (a) 预言机数据版本差异（Paladin 敏捷度）；
- 8 个属于 (c) A 的真实缺陷，共 5 类。E 在这 5 类上全部与 Pyfa 一致。
eve3 看到的大量差异主要来自非法装配：第一轮有 26 个差异全是离线改装件，而 EVE 中改装件无法离线，属于 (b)。
复现用例见 eve-dogma-bench 分支 `pending-1.10` 的 `cases/e_fz_*.json`。

Date: 2026-10-03 (sweep 10:50–11:00 CST). Background: eve3's 64 random fits showed 31 diffs vs Pyfa. A and J
agreed byte for byte on them, and at least one fit was illegal (a frigate with a structure rig).

## Method
- Generator `oracle/fuzz/gen_legal.py` and checker `check_legal.py` on eve-dogma-bench `pending-1.10`. Both are GPL
  and use Pyfa as a library.
  - Ships only, stratified by ship group.
  - Modules are added only when Pyfa's `Module.fits` accepts them. That covers slot counts after T3C subsystems,
    hardpoints, rig size, canFitShipGroup/Type, fitsToShipType, maxGroupFitted, and capital modules on subcaps.
    maxTypeFitted is also enforced.
  - Charges come from `getValidCharges`.
  - States follow isValidState and maxGroupOnline/Active; rigs are always online. T3D hulls get a mode.
  - Drones stay within bay, bandwidth and 5 active; fighters within tubes and class slots. Implants and boosters use
    distinct slots.
  - CPU/PG are not enforced.
  - Only types present in Pyfa's eve.db are drawn, because that data build lags dataset 3569502.
- Run: `gen_legal.py fits 200 10`. It is deterministic, and all 200 fits pass `check_legal`. They cover 46 ship
  groups: 4 T3C, 5 T3D, 12 with fighters, 74 with drones.
- Compare: bench-1.9.0 oracle + metrics, A and E (`compare.py`). Every diff was minimised with `minimize.py` (greedy
  removal) and checked for data drift with `drift.py`.

## Result
| Class | Fits | Detail |
|---|---|---|
| match | 190 | |
| (a) oracle limitation | 2 | Paladin agility: Pyfa eve.db 3532181 has 0.858, SDE 3569502 has 0.0858. A = E. Already known |
| (b) illegal / out of contract | 0 (26 in the first pass) | Offline rigs: Pyfa and E skip `upgradeCost` of offline rigs, A counts it. EVE can't offline rigs, so the generator now forbids them |
| (c) real A bug | 8 | 5 bugs, below. E = Pyfa on all of them |

| Bug | Repro case(s) | A vs Pyfa |
|---|---|---|
| E1: drones that have both `targetAttack` and an EWAR effect (SW-300 / TD-900, group 5239) take their damage cycle from `duration` (73) instead of `speed` (51) | `e_fz_drone_speed_orbweaver_dagon`, `e_fz_drone_speed_torafugu_odysseus` | drone dps −20 % |
| E2: Pyfa `type='offline'` effects (854 cloak scanRes, 3046 Expanded Cargohold velocity, 6737 burst charge, 11714 lance) are not applied to offline modules | `e_fz_offline_cloak_hulk`, `e_fz_offline_expanded_cargohold_rifter` | scan res 825 vs 536; velocity 456 vs 374 |
| E3: the cloak scanRes multiplier has its own Pyfa penalty group; A stacks it with the WCS multiplier | `e_fz_cloak_wcs_penalty_group_ninazu` | 35.18 vs 33.93 |
| E4: the cap sim uses a rounded overheated cycle time (15300.0 vs float 15299.999…) | `e_fz_capsim_overheat_cycle_zarmazd`, `…_revelation_ni` | stable % +0.01 to 0.03 pp |
| E5: multiplication order at a `round(v,2)` tie (skill then rig, vs Pyfa rig then skill) | `e_fz_cpu_round_tie_gold_magnate` | cpu 7.42 vs 7.43 |

E1 is unambiguous, because the SDE `targetAttack.duration_attr` and Pyfa agree. E2 and E3 come from Pyfa's
hand-written effect modelling; they count as bugs under the Pyfa-parity rule, and move to `known_divergences` if eve
rules SDE semantics. E4 and E5 are float-order artefacts, but they fail at the bench tolerance.

Takeaway for eve3's 31/64: random fits need a legality filter before diffs against Pyfa mean anything. With the
filter, only 4 % of fits differ in A (8/200), and each diff has a single-value minimal repro. The legality checker
also flags about half of the official 1.8.0 corpus as illegal (overfilled slots and hardpoints, drones on ships
without a bay, structure hulls), so the bench corpus is not legality-constrained. That's fine for scoring, but
worth knowing.

## Expected differences: Pyfa data drift (eve ruling, 2026-10-03)
Pyfa's `eve.db` (v2.69.0, client build **3532181**, SDE of 2026-09-22) is older than the engines' dataset (SDE
3569502). This was checked against CCP's own SDE zips for both builds, ESI on server 3569502, and Pyfa's
`staticdata`. The pipeline copies the SDE 1:1 (0 diffs), so these are oracle-side data drift, class (a), and not engine
bugs. Canonical machine-readable list: EX-CT/eve-sde-pipeline
[`docs/pyfa-data-drift.json`](https://github.com/EX-CT/eve-sde-pipeline/blob/main/docs/pyfa-data-drift.json)
(details: `docs/pyfa-data-drift.md`). The fuzz copy is eve-dogma-bench `pending-1.10:oracle/fuzz/expected_diffs.json`.

| Entry | Types | Pyfa | SDE / ESI | Metrics treated as expected difference | Ruling |
|---|---|---|---|---|---|
| `paladin-agility` | Paladin 28659, attr 70 | 0.858 | 0.0858 | `align_time_s` | Keep CCP. Pyfa outdated; CCP fixed it after 3532181, by 3552227 |
| `golem-agility` | Golem 28710, attr 70 | 0.963 | 0.0963 | `align_time_s` | Same |
| `remote-capacitor-impedance` | Remote cap transmitter (effect 6184) onto 47 capitals (carrier, FAX, dread, super, titan groups) or onto any ship running Siege/Triage/Bastion/Industrial Core | resistance attr 2116, no 6463/6464 | resistance attr 6463; modules set 6464 = −99.9999 % | target's `cap_stable`, `cap_stable_percent` (and any outgoing remote-cap value against such a target) | Keep. Pyfa outdated |
| `t3c-max-subsystems` | Tengu/Legion/Proteus/Loki, attr 1367 | 4 (Pyfa `db_update.py` override) | 5 | none; informational | No pipeline patch. Legality belongs to the engine/validation layer, which should behave like Pyfa |

Kronos and Vargur agree in every source. No other attribute value differs between `eve.db` and the dataset on
shared types.

Where these are recorded:
- **Scored corpus** (bench `expected/known_divergences.json`, case → metric): `esf_projection_18` / `align_time_s`
  (Paladin) is already excluded. No other corpus case uses Paladin, Golem, or remote cap onto an affected target, so
  nothing else was added and scoring is unchanged.
- **A's oracle** (eve-dogma-rs `oracle/compare.py`, `KNOWN` dict, case-keyed): already has `esf_projection_18`.
  Owner TODO: optionally read `pyfa-data-drift.json` instead of a hard-coded dict when new cases appear.
- **Legal-fit fuzz** (bench `pending-1.10:oracle/fuzz/`): the allowlist file is committed but not wired in yet.
  Owner TODO: in `compare.py`, classify a diff as `expected_drift` when the fit matches an entry's `match`, and
  report the count separately in `summary.json`.
- **Variant F fuzz** (`/workspace/exct-eve/f-fuzz/fuzz.py`, not in a repo): it inherits the bench's per-case
  `excluded` lists only. Owner TODO: same type-level check for perturbed cases (for example, a mutation that adds a
  Paladin or Golem hull, or projects remote cap onto a capital).
