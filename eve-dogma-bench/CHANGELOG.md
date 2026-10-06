# Bench changelog

Variants: compare scores only at the same bench version (`VERSION`, shown in results/combined.md).
Expected values always come from the Pyfa oracle (`oracle/pyfa_oracle.py`). Re-run `python3 bench.py --only <X>` after
pulling.

## 1.10.0 (2026-10-03 12:30 CST, tag v1.10.0)
- Released from branch pending-1.10. `tools/evaluate.py` stays pinned to 1.8.0 (`3da9671`). CONTRACT.md = revision
  1.4.5 plus the "Draft 1.10: stats-ext" section (proposed fields, scored only by `ext/`).
- Core corpus: 339 cases, 22 513 values (+8 `e_fz_*` cases from the differential fuzz, +9 `warp_scramble_status`
  values, below). F 4b8f5f9 339/339, eve-dogma-rs d6043a7 325/339 (README "Current results").
- New suite `effects/` (docs/20 P0-2): 2 378 Pyfa micro-fits, one per dogma effect Pyfa implements (2 266 with SDE
  modifierInfo, 112 handler-only, incl. the 37 docs/19 ENG-CORE-003 unverified ones), scored on the full modified
  attribute dump (382 231 attribute values) plus the bench metrics. `effects/README.md`.
- New suite `ext/` (docs/20 P0-3 / P0-4): 116 cases. Pyfa values for mining yield/drain, outgoing remote reps / cap
  transfer (with spool), drone and fighter HP / EHP / shield recharge, the bombing panel, heat (burn cycles,
  burnout time), keyed to the proposed FitStats fields; explicit `fleet.buffs` (now modelled by the oracle); and 6
  hand-derived, non-Pyfa `overrides` cases. `ext/README.md`.
- Oracle: `fleet.buffs` modelled through Pyfa's command bonuses (explicit id wins over bursts, booster fits and
  beacons; duplicates aggregate per the dbuff's Minimum / Maximum). Opt-in `ORACLE_EXTRA=attrs,ext` dumps; default
  output unchanged (expected values regenerate byte-identical).
- `tools/check_inventory.py` (docs/20 §5.1 gate) with `inventory/suites.yaml` (suite registry: bench, state, effects,
  ext, cap, mut, fmt-export, fmt-edge, graphs, unit, mcp, web-e2e, web-unit) and `inventory/tests.yaml` (docs/19 item
  → tests, F column).
- Fuzz: `oracle/fuzz/gen_legal.py` / `check_legal.py` (legal random fits by Pyfa's fitting rules), `compare.py`
  `expected_diffs.json` → `expected_drift` category.
- Contract revision 1.4.5: module state correction (ruling reversed 2026-10-03 11:19 CST): impossible requested
  `active`/`overheated` → `online`, corrected state reported in `modules[].state`, one `warnings[]` entry per
  correction (`/modules/N: state '<requested>' not possible for this module, using online`). No scored value changes;
  informational check `tools/check_module_state.py` (`pending/state/`).
- `warp_scramble_status` follows Pyfa: the 9 Networked Sensor Array known divergences (SDE +100, Pyfa omits) are
  removed and their expected values regenerated from the oracle (+9 scored values).

## 1.9.0 (2026-10-03 11:00 CST, tag v1.9.0)
- Released after the round-1 unified evaluation, which used 1.8.0 (`tools/evaluate.py` keeps pinning `3da9671`).
- CONTRACT.md = contract revision 1.4.4: additive `pure` damage key (breacher pods) and `weapons[].kind = "breacher"`;
  "Semantics" defines breacher pods and overheat order.
- Scorer: new metrics `weapon_pure_dps` / `weapon_pure_volley` (`/offense/total/{dps,volley}/pure`, an absent key
  counts as 0), expected from Pyfa `getWeaponDps().pure` / `getWeaponVolley().pure` (oracle extended). Every case
  gains these two values; the other expected values are unchanged.
- +5 cases (331 cases, 22 046 values), from Variant F's Pyfa sweep, all Pyfa-verified:
  - `overheat_order_tengu`, `overheat_order_rev_tengu`: every active module overheated, EFT order and reversed. Pyfa
    runs effects module by module, so a hardener's overheat reads `overloadHardeningBonus` before a Defensive
    subsystem listed after it has boosted it (shield EM resonance 0.1967 vs 0.1769 with the full bonus).
  - `breacher_kestrel`: 2 × Small Breacher Pod Launcher with SCARAB Breacher Pod S. Volley = DPS = one tick
    (`dotMaxDamagePerTick`) as `pure` damage, strongest pod only: 250, not 500.
  - `neut_nos_vs_mwd_rifter`: projected neutralisers read the target signature before the 'late' MWD bloom,
    nosferatu after it.
  - `ewar_drones_rifter`: ECM and target-painter drones projected (EWAR drone cycle time).
- EFT export expected texts added for the 5 cases (331 lines).
  Scores at 1.8.0 are not comparable with 1.9.0.

## 1.8.0 (2026-10-03 06:10 CST)
- CONTRACT.md = contract revision 1.4.3. No field changes; "Semantics" now also defines weather/cloud beacons,
  incursion system effects and burst projectors (below).
- +20 cases (326 cases, 21 051 values), all Pyfa-verified:
  - Abyssal weather / AoE clouds (`weather_*`, `cloud_*`; environment type ids 47380–47392, 47436, 47441, 47472, 47620):
    the beacon's `warfareBuff1/2` join the fleet-buff pool (strongest |value| per id). Pyfa also applies buffs 79,
    90 and 93–99 to drones requiring Drones. Weather resist/HP/velocity buffs are unpenalised.
  - Incursion system effects (`incursion_*`; Sansha HQ/Vanguard, Drifter defeat): Pyfa `OffensiveDefensiveReduction`.
  - Burst projectors (`aoe_*`): web / paint / damp / weapon disruption (turrets and missiles) at full strength
    regardless of distance; neutralization burst as a cap drain; ECM burst as a jam source.
  - Standup weapon disruptors with range factor, and the Standup web/WD bursts (`standup_*`).
- EFT export expected texts added for the 20 cases (326 lines).
- Dataset: sde-3569502-r3 gives the same results as r1 for every case (only `meta.dataset_sha256` differs).
  Scores at 1.7.0 are not comparable with 1.8.0.

## 1.7.0 (2026-10-03 06:00 CST)
- +9 cases (306 cases), found by sweeping every published module and implant on an empty Hyperion against Pyfa:
  - `exct_avatar_lance`, `exct_hyperion_bosonic`: lance / Bosonic Field doomsdays deal their volley every
    `doomsdayDamageCycleTime` for `doomsdayDamageDuration` (Pyfa `getVolleyParameters` subcycles; not the Reaper
    slash), so DPS = subcycles × volley / cycle and volley = one tick; active superweapons also apply their
    `speedFactor` to the ship's maxVelocity and the `siegeModeWarpStatus` to warpScrambleStatus.
  - `exct_broadsword_bubble`: an active uncharged Warp Disruption Field Generator: unpenalised mass / signature
    radius / propulsion-module speed boost on the HIC, `disallowAssistance` = 1.
  - `exct_moros_ehe` (Capital Emergency Hull Energizer: hull resonances), `exct_hurricane_entosis` (Entosis Link:
    disallowAssistance, scan strengths), `exct_hyperion_mjfg` (Micro Jump Field Generator: signature radius).
  - `exct_hyperion_smartbomb`: `cpu_used` / `pg_used` are Python `round(v, 2)` (correct rounding of the binary value,
    e.g. 28.125000000000004 → 28.13 but 28.12499… → 28.12), not round-half-up of v×100.
  - `proj_td_drones_rifter`, `proj_td_drones_out_of_range_rifter`: tracking-disruptor drones
    (`npcEntityWeaponDisruptor`): full strength inside the drone's maxRange, nothing beyond it.
- EFT export expected texts added for the 9 cases (`expected_extra/eft_export.jsonl`, 306 lines).
  Scores at 1.6.0 are not comparable with 1.7.0.

## 1.6.0 (2026-10-03 05:50 CST)
- +2 cases (297 cases, 19 103 values): `projfit_scythe_rtc_x2_on_rifter` (two Scythes with scripted Remote Tracking
  Computers at 12 km: Pyfa `shipModuleRemoteTrackingComputer` boosts the target's Gunnery modules' trackingSpeed /
  maxRange / falloff, postPercent × range factor, stacking-penalised, blocked by `disallowAssistance`) and its source
  fit `exct_scythe_rtc`. Scores at 1.5.x are not comparable with 1.6.0.

## 1.5.1 (2026-10-03 05:40 CST)
- Harness only (corpus and scoring unchanged): `results/` is no longer tracked at all (combined.md/json were tracked
  and modified by every run, so `git pull` in the shared checkout failed with "Please commit or stash").
  The shared box keeps its local results/combined.*; the README table holds published numbers.

## 1.5.0 (2026-10-03 05:30 CST)
- CONTRACT.md = contract revision 1.4.2: precise definitions (section "Semantics") of `capacitor.use_gj_s` /
  `injected_gj_s` / `delta_gj_s`, of `projected[].amount` (projected fits: computed once on their own; every active
  module / active drone / active fighter squadron is projected `amount` times, each copy a separate stacking-penalised
  modifier), and fleet-buff precedence (an explicit `fleet.buffs` entry overrides own bursts and booster fits for its
  buff id; otherwise the strongest |value| wins).
- +6 cases (295 cases, 18 978 values), amount > 1 projected fits: `projfit_curse_x3_on_ishtar` (3 neut/nos Curses at
  10 km: cap drains ×3), `projfit_curse_x2_falloff_on_rifter` (neuts + tracking disruptors in falloff at 20 km),
  `projfit_crucifier_x2_on_cerberus` (scripted guidance disruptors ×2 vs missiles), `projfit_crucifier_x3_falloff_on_rifter`
  (TD/GD/neut ×3 at 30 km), and the source fits `exct_curse`, `exct_crucifier` on their own.
  These need projected **Tracking Disruptor / Guidance Disruptor** effects (Pyfa Effect6424 / Effect6423: modify the
  target's Gunnery modules' trackingSpeed/maxRange/falloff and Missile Launcher Operation charges'
  aoeCloudSize/aoeVelocity/maxVelocity/explosionDelay, postPercent × range factor, stacking-penalised, remote resistance).
- Scores at 1.4.x are not comparable with 1.5.0 (new cases). `expected_extra/eft_export.jsonl` also covers the new cases.

## 1.4.1 (2026-10-03 05:40 CST)
- CONTRACT.md = eve-dogma contract revision 1.4.1 (coordinator rulings): (1) a calc error exits 2 and still prints
  the `{"error":…}` JSON on stdout; (2) `options` missing entirely → `validate` defaults to true; (3) `search` is out
  of dogma scoring, interim spec only (limit 20; kinds ship/module/charge/drone/fighter/implant/booster/subsystem/skill;
  exact > prefix > substring; ties by typeID ascending); (4) `eft_export` must match Pyfa's exporter byte for byte
  (Pyfa writes no T3D mode line); (5) duplicate changelog heading removed.
- Corpus and accuracy scoring unchanged (289 cases, 18 591 values): scores from 1.4.0 remain comparable.
- New informational check (not in accuracy): EFT export vs Pyfa `exportEft` (all options on, after GUI `fill()`),
  `expected_extra/eft_export.jsonl` (289 fits; `oracle/pyfa_eft_export.py` generates it). Run
  `python3 tools/check_eft_export.py --rpc-cmd "<engine serve-stdio>"`, or add `rpc_cmd:` to bench.yaml and bench.py
  shows an "eft export" column. RPC: JSONL `{"id","method":"eft_export","params":{"fit","name"}}` →
  `{"id","result":{"text"}}`. Accepted data divergence: T3C maxSubSystems 5 (SDE) vs 4 (Pyfa eve.db).

## 1.4.0 (2026-10-03 04:50 CST)
- +40 cases (289): sustainable tank (factor_reload / neuted fits), ECM (racial/multispectral modules, falloff, EC drones,
  burst jammer), projected fighters (`projected[].kind = "fighter"`, `fighter`: FighterReq; web / point / neut / ECM),
  active drones (light/medium/heavy/sentry), local fighter abilities (MWD / evasive / MJD via `fighters[].abilities`),
  booster side effects (`boosters[].side_effects` = effect IDs).
- New metrics (18 591 values): `stank.{armor,shield,hull}` → `/defense/tank/sustained/*` (Pyfa `sustainableTank`),
  `jam_chance` → `/targeting/jam_chance_percent` (Pyfa `jamChance`, 0 when no ECM), `warp_scramble_status` →
  `/navigation/warp_scramble_status`, `drone_control_range` → `/drones/control_range_m`, per active damaging drone
  `d<drone_index>.{optimal_m,falloff_m,tracking,max_velocity,signature_radius}` → `/offense/drones[drone_index=N]/…`,
  per damaging fighter `f<fighter_index>.{max_velocity,signature_radius}` → `/offense/fighters[fighter_index=N]/…`.
- Known divergence: Networked Sensor Array `warpScrambleStatus` (SDE +100, Pyfa omits) for Hel/Nidhoggur cases.
- Note: `capacitor.use_gj_s` semantics (contract v1.4) not scored.

## 1.3.0 (2026-10-03 04:20 CST, b687270)
- New metric group `application`: per weapon `w<module_index>.{optimal_m,falloff_m,tracking,range_m,explosion_radius,
  explosion_velocity}` at `/offense/weapons[module_index=N]/<field>` (array-selector pointer, see tools/metrics.py).
  Missile `range_m` = Pyfa `missileMaxRangeData` (ship radius flight-time bonus, acceleration, floor/ceil blend).
  13 812 values.

## 1.2.0 (2026-10-03 04:10 CST, 6533a02)
- +23 cases: projected whole fits (`projected[].kind = "fit"`), projected module charges/scripts, incoming remote
  reps (Pyfa diminishing-returns formula into `/defense/tank/raw/*`), neuts/nos/cap transfers (extra cap-sim drains).
  249 cases.

## 1.1.0 (2026-10-03 04:00 CST, be77fa7)
- +19 cases: `fleet.booster_fits`, wormhole environments (`environment.effect_type_ids`), implant sets, boosters.
  226 cases.

## 1.0.0 (2026-10-03 03:45 CST, a834277)
- 207 cases, 9 827 values; runner, variants.yaml, combined scorecard.

## Harness
- results/: only `combined.{md,json}` are tracked; `--only X` merges into combined (use `--fresh` to reset).
