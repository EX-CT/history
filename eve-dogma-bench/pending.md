# pending-1.10 (staged, not released)

Branch from main (32295d5, bench 1.8.0). Holds minimal repro cases for **real engine bugs** found by the
legal-fit differential fuzz (A = eve-dogma-rs vs the Pyfa oracle, E 5867d53 for reference), 2026-10-03.

## Tools (GPL, Pyfa used as a library, same as `oracle/pyfa_oracle.py`)
- `oracle/fuzz/gen_legal.py OUTDIR N SEED`: random **legal** ship fits. Ship group stratified; modules are added
  only if Pyfa's `Module.fits` accepts them (slot counts after T3C subsystems, turret/launcher hardpoints, rig size,
  canFitShipGroup/Type, fitsToShipType, maxGroupFitted, no capital modules on subcaps) plus maxTypeFitted;
  charges from `Module.getValidCharges`; states respect isValidState + maxGroupOnline/maxGroupActive;
  T3D/Anhinga get a mode; drones within bay/bandwidth/5 active; fighters within tubes/class slots/bay;
  implants/boosters in distinct slots. CPU/PG/calibration not enforced. Structures excluded.
- `oracle/fuzz/check_legal.py REQ...`: the same rules as a checker (one JSON line per request). Rigs must be online
  (EVE can't offline a rig; Pyfa can). "state above the module's max" is only a note, because the contract clamps it.
- `oracle/fuzz/compare.py FITS OUT`: oracle (bench-1.9.0 `pyfa_oracle.py` + `metrics.py`) vs A and E on every fit.
  `minimize.py FIT METRIC OUT`: greedy delta minimiser (drop modules/drones/implants/boosters/charges while the
  A-vs-Pyfa gap on METRIC stays). `drift.py`: per-type attribute/effect drift, Pyfa eve.db vs dataset 3569502.
  The paths in these three are hard-coded to the EXCT box.

## Sweep (2026-10-03 10:50–11:00 CST)
`gen_legal.py fits 200 10` → 200 fits, all `check_legal` OK; 46 ship groups (4 T3C, 5 T3D, 12 with fighters,
74 with drones, 117 with implants, 51 with boosters). 12 057 compared values. A = eve-dogma-rs e4c42db, E = variant-e 5867d53.

| | fits | values | class |
|---|---|---|---|
| A = Pyfa on every value | 190 | | |
| Paladin (28659) agility: Pyfa eve.db build 3532181 has 0.858 vs SDE 3569502 0.0858 (A = E) | 2 | 2 | (a) oracle data drift (already known) |
| A ≠ Pyfa, **E = Pyfa** | 8 | 8 | (c) A bugs below |

A first pass with the same seed had 26 more diffs, all `calibration_used` (A counted offline rigs, Pyfa and E don't).
Every one of them was an offline rig. EVE can't offline a rig, so these were (b) illegal fits. The generator now
keeps rigs online; that changed exactly those 26 fits. If the bench does want offline rigs, A should count
`upgradeCost` only for rigs that are online, like Pyfa `getItemAttrOnlineSum`.

## Expected differences: Pyfa data drift (`oracle/fuzz/expected_diffs.json`)
Data-driven allowlist (eve ruling 2026-10-03), copied from EX-CT/eve-sde-pipeline `docs/pyfa-data-drift.json`.
Pyfa's `eve.db` is client build 3532181. The engines' dataset follows SDE 3569502.
- `paladin-agility` (28659, attr 70: Pyfa 0.858 vs SDE/ESI 0.0858) and `golem-agility` (28710, 0.963 vs 0.0963):
  CCP fixed both after 3532181, by 3552227. `align_time_s` diffs on these hulls are class (a), like the 2 Paladin
  fits in the sweep above.
- `remote-capacitor-impedance`: the SDE added attrs 6463/6464 and switched effect 6184's resistance from 2116 to
  6463. A remote cap transmitter projected onto one of the 47 listed capitals, or onto a ship running
  Siege/Triage/Bastion/Industrial Core, gives class (a) diffs on `cap_stable` / `cap_stable_percent`.
- `t3c-max-subsystems` (1367: Pyfa forces 4, SDE 5): decision is no pipeline patch, informational only (no metric).

`compare.py` reads it (default: next to the script, or `--expected-diffs FILE`): a diff whose metric is listed by an
`expected_difference` entry whose `match` holds for the fit goes to `expected_drift.json` and `summary.expected_drift`
(fits, values, by_entry, per-engine fits) instead of `diffs.json` / `*_diff_fits`. New `--no-engines` reuses saved
`<engine>.jsonl`. Test 2026-10-03 11:26 CST on the saved 200 fits (`fz-e/work/out`, m19 metrics): before A 10 / E 2 / J 10
diff fits; now A 8 / E 0 / J 8 real + expected_drift 2 fits / 2 values (`paladin-agility`, lf10_123/197). The
`remote-capacitor-impedance` matcher (transmitter projected onto a listed capital, or onto a ship with an active
Siege/Triage/Bastion/Industrial Core) was checked on 3 synthetic fits (Revelation, Revelation + Siege → drift;
Cyclone control → real). `drift.py` does not read it yet. No
scored case is affected. The only corpus case on these hulls is `esf_projection_18`, already in
`expected/known_divergences.json`.

## (c) A bugs, with minimal repro cases (`cases/e_fz_*.json`, `expected/e_fz_*.json`, 1.9.0 format)
Each case is legal by `check_legal.py`. **A fails exactly one value on each one and E passes all of them.**

| Case | Bug | A | Pyfa = E |
|---|---|---|---|
| `e_fz_drone_speed_orbweaver_dagon` (Dagon, 3× Orbweaver SW-300-I active) | **E1** Drones with both `targetAttack` and an EWAR effect (group 5239: SW-300 / TD-900 …): A uses the EWAR effect's `duration` (73, 5000 ms) as the damage cycle. Pyfa and the SDE `targetAttack.duration_attr` use `speed` (51, 4000 ms). Gap is −20 % drone dps, at any skill level | drone_dps 38.81 | 48.52 |
| `e_fz_drone_speed_torafugu_odysseus` (Odysseus, Torafugu TD-900-I ×5, 1 active) | E1, same bug on the TD drone | 58.22 | 72.77 |
| `e_fz_offline_cloak_hulk` (Hulk, Dread Guristas Cloaking Device **offline**) | **E2** Pyfa `type = 'offline'` effects apply even when the module is offline: 854 cloak scanResolution, 3046 Expanded Cargohold maxVelocity, 6737 command-burst charge, 11714 Disruptive Lance cloak block. A applies none of them to an offline module | scan_resolution 825 | 536.25 |
| `e_fz_offline_expanded_cargohold_rifter` (Rifter, Expanded Cargohold II offline) | E2 control on 3046 | max_velocity 456.25 | 374.125 |
| `e_fz_cloak_wcs_penalty_group_ninazu` (Ninazu, Estamel's cloak active + 'Halcyon' Core Equalizer I) | **E3** Pyfa puts the cloak scanResolution multiplier in its own stacking-penalty group (`penaltyGroup='cloakingScanResolutionMultiplier'`). A stacks it together with the WCS `scanResolutionMultiplier` | 35.18 | 33.93 |
| `e_fz_capsim_overheat_cycle_zarmazd` (Zarmazd, 2× Small Inefficient Hull Repair Unit, one overheated) | **E4** Cap sim: A uses the overheated cycle time 15300.0 ms. Pyfa (and E) use the float 15299.999999999998, so the sim period differs (A 111 iterations, E 2612) | cap_stable_percent 91.049 | 91.020 |
| `e_fz_capsim_overheat_cycle_revelation_ni` (Revelation Navy Issue, smartbomb + small armor rep, both overheated) | E4, same (A 3825.0 vs 3824.9999999999995 ms) | 81.966 | 81.954 |
| `e_fz_cpu_round_tie_gold_magnate` (Gold Magnate, 125mm Carbide Railgun I + Small Algid Hybrid Administrations Unit I) | **E5** Multiplication order at a `round(v, 2)` tie: A computes 11 × 0.75 × 0.9 = 7.42499999… → 7.42. Pyfa computes rig then skill, 11 × 0.9 × 0.75 = 7.4250000000000007 → 7.43 | cpu_used 7.42 | 7.43 |

Notes for adjudication:
- E1 is unambiguous: Pyfa and the SDE `duration_attr` of `targetAttack` agree.
- E2 and E3 come from Pyfa hand-written effect modelling, not SDE modifiers: effect 854 has SDE category 0 and
  plain PostMul. The bench scores Pyfa parity, so they are listed as A bugs. If eve rules SDE semantics instead,
  move them to `known_divergences` (a).
- E4 and E5 are float-order artefacts, at most 0.03 percentage points of cap and 0.01 tf of CPU. They are real A ≠ Pyfa values at the bench tolerance.

## Module-state ruling reversed (eve, 2026-10-03 11:19 CST; contract draft 1.4.5)
Principle (user): align with Pyfa; engines may do more than Pyfa, never less. Adopts Variant F's behaviour, which
already equals the Pyfa oracle: an impossible requested `active`/`overheated` state is corrected to `online`, the
response reports the corrected `modules[].state`, and `warnings[]` gets
`/modules/N: state '<requested>' not possible for this module, using online` (CONTRACT.md "Module state correction").
- Scored values are unchanged (the oracle always corrected the state); A/J/E-style engines that echoed the requested
  state now differ only in `modules[].state` / `warnings[]`.
- Check (informational, not scored): `python3 tools/check_module_state.py --batch-cmd "<engine> batch"` on
  `pending/state/state_rifter_*.json` (expected states from Pyfa `isValidState` via `oracle/state_oracle.py`).
  2026-10-03 11:22 CST: F bc84e2b 3/3, eve-dogma-rs d6043a7 1/3 (echoes the requested state, no warnings).
- **Not on this branch, still encodes the old "keeps requested value" ruling:** eve-dogma-bench `graphs-round2`
  `graphs/draft-0.3` (fd4e8c8: contract section + case `dmg_dist_vargur_bastion_overheated_state`, whose expected
  values were made with the Bastion *active*; under the reversed ruling Pyfa corrects `overheated` Bastion to
  `online`), and `graphs/pending` notes on fz0157 / fz0038 / fz0518 (eda48f2). The graphs owner must regenerate that
  case from the plain oracle (`rulings/make_ruling_cases.py` no longer applies) and update the notes there.

## `warp_scramble_status`: follow Pyfa (eve, 2026-10-03 11:19 CST)
The 9 `known_divergences` entries "SDE: Networked Sensor Array ModAdd warpScrambleStatus += warpScrambleStrength (+100);
Pyfa's hand-written moduleBonusNetworkedSensorArray omits it" are removed (exct_hel, exct_nidhoggur,
fighters_mwd_nidhoggur, skills{0,2,4}_{hel,nidhoggur}). Their expected files were regenerated from the Pyfa oracle
(`tools/make_expected.py`): the only change per file is the added `warp_scramble_status` value (e.g. exct_hel −25.0) and
an empty `excluded`. 9 more values scored. Check 2026-10-03 11:24 CST (pending-1.10 corpus, bench-1.9.0 metrics.py):
F bc84e2b 334/334 cases; eve-dogma-rs d6043a7 320/334 (fails the 9 NSA cases + 5 `e_fz_*`).

## F/A-vs-Pyfa root-cause triage on valid fits (2026-10-03 11:26–11:32 CST)
Question: the metrics where both Variant F (bc84e2b) and A disagreed with Pyfa in the random-fit arbitration
(`cap_stable_percent`, `max_velocity`, `scan_resolution`, `ehp.{shield,armor,hull}`, `stank.armor`). Pool: every fit that
passes `oracle/fuzz/check_legal.py` from J's random generator (51 of 4 000) and F's module sweeps (13 398 of 20 312), plus 900
new `gen_legal.py` fits (seeds 31–33, 300 each), then CPU / PG / calibration within limits per the oracle → **13 347 valid
fits** (194 oracle errors: types missing from Pyfa's eve.db; 808 over CPU/PG/calibration). Also the 200 fz-e fits above.
Engines: F bc84e2b, A = eve-dogma-rs d6043a7. Oracle: this branch's `pyfa_oracle.py`, metrics = this branch's `tools/metrics.py`.

| metric | F and A ≠ Pyfa on valid fits | F ≠ Pyfa only | cause of the earlier F-and-A disagreements | F bug? |
|---|---|---|---|---|
| cap_stable_percent | 0 | 0 | all 5 were illegal fits (wrong-class modules, T3D without mode, …) | no |
| max_velocity | 0 | 0 | all 3 illegal fits | no |
| scan_resolution | 0 | 0 | all 3 illegal fits | no |
| ehp.shield / armor / hull | 0 / 0 / 0 | 0 | all illegal fits (2 / 3 / 3) | no |
| stank.armor | 0 | 0 | all 2 illegal fits | no |
| (other) align_time_s | 6 | 0 | Paladin 28659 / Golem 28710 agility: Pyfa data drift (`expected_diffs.json`) | no |
| (other) signature_radius | 1 (jrand00544) | 0 | request uses explicit `fleet.buffs`; the oracle doesn't model them (contract does more than Pyfa) | no |
| (other) cap_capacity | 1 (jrand03574) | 0 | request uses `overrides`; the oracle ignores them | no |

The 14 sampled fits behind the 21 earlier "neither" values were all rejected by `check_legal.py`. On every valid fit
F matches Pyfa on all scored metrics (F-only mismatches: 0; on the 200 fz-e fits F has 0 diff fits). A-only mismatches
on the pool: cap_stable_percent 75, drone_dps 24, max_velocity 20, scan_resolution 14, warp_scramble_status 9,
signature_radius 7, scan_strength 6, tank/stank.armor 1 each (the E1–E5 classes above and the NSA ruling).
No F repro case is needed. Fuzz note: requests with `fleet.buffs` or `overrides` are outside the oracle's model and
should be excluded from oracle triage (or the oracle extended).
