# Effect suite (bench 1.10, docs/20 P0-2)

One legal micro-fit per dogma effect that Pyfa implements and some dataset type carries: **2 378 cases** (2 266
effects with SDE modifierInfo + 112 handler-only), each checked on the **full modified-attribute dump** (ship,
every module and its charge, every drone, every fighter) plus the bench metrics. All 37 handler-only effects that
docs/19 ENG-CORE-003 lists as unverified (weather / AoE clouds, warfare links, mining, salvaging, hacking, tractor,
point defense, lightning weapon, doomsday AoE bubble, titan effect generator, breacher pod damage control,
useMissiles, ...) have a case (`MANIFEST.json` `unverified37: true`).

```
cases/       eff_<effectID>_<effectName>.json   FitRequests (options.include_attributes = "all")
expected/    eff_<...>.json                     Pyfa oracle attribute dump + metrics, with exclusions
MANIFEST.json                                   per case: effect id/name, Pyfa handler type, carrier type, how, affectees
tools/gen_effects.py    generator (Pyfa venv; uses Pyfa's own fitting rules, so every fit is one Pyfa builds)
tools/make_expected.py  oracle run (ORACLE_EXTRA=attrs) + exclusion rules
tools/score.py          scorer
```

Score an engine:

```
python3 effects/tools/score.py --batch-cmd "/path/to/engine batch" --name X [--out results.json]
```

## How a case is built (`how` in MANIFEST.json)

| how | carrier | fit |
|---|---|---|
| fitted-module | module / structure module | first hull (preference list, then every hull by group) where Pyfa's `Module.fits` accepts it; state from the effect (overload → overheated, active/target/area → active, else online, clamped by `isValidState`); first valid charge |
| charge | charge | loaded in the first module whose `getValidCharges` has it |
| projected-module / -drone / -fighter | module / drone / fighter whose Pyfa handler is `projected` and SDE category target | projected (1 000 m) onto the standard fit |
| drone / fighter | drone / fighter | bay of the first hull that takes it, active |
| implant / booster | implant / booster | standard fit (boosters: the effect as side effect when it is one) |
| subsystem | T3C subsystem | its hull with the first subsystem of every other slot |
| ship / mode / structure | hull / T3D-Anhinga-Skua mode / Upwell structure | that hull (T3C hulls with subsystems) |
| skill / skill-std | skill | default_level 0, that skill at V |
| environment | effect beacon, weather, cloud | `environment.effect_type_ids` on the standard fit |

Plus **affectees**: items the effect modifies, derived from its SDE modifiers (LocationGroup → an item of that
group, Location/OwnerRequiredSkill → an item requiring that skill, LocationModifier → a module with the modified
attribute), fitted when Pyfa allows it. The standard fit is bench 1.9.0 `drones_active_vexor` without
Drones-skill modules.

## What is compared (`tools/make_expected.py`)

Per item, attribute A of the Pyfa dump is expected unless:

- A is not a dataset attribute (Pyfa pseudo-attributes such as `armorRepair`);
- `data_drift`: Pyfa's base value (data build 3532181) differs from the SDE 3569502 one for that type (mostly `radius`
  of non-ships, `remoteCapacitorImpedance`, Marauder `agility`); when the hull itself drifts, the case's metrics are
  dropped too (`excluded.values`);
- `pyfa_internal`: Pyfa's nosferatu `capacitorNeed` (stored negative) and the command-burst `warfareBuffN`
  Value / Multiplier routing (the resulting buffs are scored by bench `fleet_*` and ext `fleet_buffs_*`);
- `not_in_pyfa`: A is modified only by SDE effects Pyfa does not implement (mostly the skill-multiplier effects Pyfa
  folds into its handlers) and Pyfa leaves it at base;
- `bonus_source`: A is a modifier source (SDE modifierInfo or read by a Pyfa handler) that Pyfa leaves at base, e.g.
  `shipBonusMF` stays −7.5 in Pyfa while SDE-expression engines multiply it by the skill level. The bonus is still
  checked through the attributes it modifies.

Scoring uses the bench tolerance (`max(1e-3, 1e-4·|want|)`). An attribute the engine's dump lacks is a mismatch, but
an attribute Pyfa keeps on the ship / item that the engine has on `attributes.character` (e.g. `maxActiveDrones`)
counts. `attributes.fighters[]` (`fighter_index`, `attributes`) is a 1.10 draft extension of
`options.include_attributes` (CONTRACT.md draft); `pass_core` ignores it.

## Results (2026-10-03, bench 1.10.0)

See `results-1.10/effects/` (per-case JSON, `failure-classes.txt`) and the README. F 4b8f5f9: 2 107/2 378; eve-dogma-rs d6043a7: 2 095/2 378.
