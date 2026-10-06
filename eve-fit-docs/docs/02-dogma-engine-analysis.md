# 02 — EVEShipFit dogma-engine analysis (+ gaps vs Pyfa)

Repo: `EVEShipFit/dogma-engine` (MIT), Rust workspace, plus `EVEShipFit/data` (data conversion, MIT + CCP licence).

## 1. Crates

| Crate | Content |
|---|---|
| `esf-data` | Reader for `sde.dat` (**FlatBuffers**, zero-copy, binary-searched tables: types, dogmaAttributes, dogmaEffects, typeDogma, dbuffCollections…); generated `eve_generated.rs`, name lookup |
| `esf-dogma-engine` | `calculate/{pass_1..pass_4}.rs`, `projection.rs`, `fit.rs` (input), `validate/*` (slot/resource/skill/charge/item rules) |
| `esf-format` | EFT, ESI, killmail, link (`fitting:` DNA), "listed" parsers/serialisers, flags |
| `esf-cli` | CLI |
| `esf-python` | PyO3 bindings; also npm package via wasm (`package.json`) |
| `tests/` | `insta` snapshot regression over community fits at skills 0 and 5 (`tests/fits/community/*.rs`, `tests/snapshots/*.snap`) |

## 2. Algorithm (multi-pass, 4 175 lines of engine code)

1. **Pass 1** (`pass_1.rs`): materialise objects: ship, mode, character, skills (attribute 280 = level), items
   (+charges), mutated items (base type attrs → mutated type attrs → rolled values), environment (security, pilot
   security status attr 2610), damage profile.
2. **Pass 2** (`pass_2.rs`): collect every effect's `modifierInfo` into per-attribute effect lists. Handles
   `ItemModifier`, `LocationModifier`, `LocationGroupModifier`, `LocationRequiredSkillModifier`,
   `OwnerRequiredSkillModifier`, ignores `EffectStopper`; domains `shipID/charID/itemID/otherID/structureID`
   (target domains only for projected). Stacking penalty iff attribute `stackable=false` and source category not
   in {Ship 6, Charge 8, Skill 16, Implant 20, Subsystem 32, Structure 65}. Fighter abilities, booster side effects
   (`fittingUsageChanceAttributeID`), dbuff collections (command bursts) handled declaratively.
3. **Pass 3** (`pass_3.rs`): lazy memoised evaluation (`Cell<Option<f64>>`) of each attribute; operators in CCP
   order; penalised values split by sign, sorted by |v| desc, factor `0.8691199808003974^(i²)`; min/max attribute
   clamp; Reactive Armor Hardener simulation (`pass_3/reactive_armor.rs`).
4. **Pass 4** (`pass_4/*`): cap depletion time / stable % (simulation), fighter tubes used.

**Special effects are pushed into the data**: `EVEShipFit/data/patches/*.yaml` adds synthetic attributes and
effects (e.g. `alignTime`, `velocityBoost` for AB/MWD, `damagePerSecond`, `damageVolley`, `ehp*`, `recharge*`,
`scanStrength`, `capacitorPeak*`, `droneActive`, `chargeAmount`, `cpuPower`) so the engine itself stays generic.

## 3. Data sourcing

`EVEShipFit/data`: either official SDE (YAML) or **client FSD binaries** decoded with the client's `.pyd` loaders
(Windows + Python 2; fresher than the SDE). Converted to protobuf/flatbuffers with category IDs added and
string enums (`domain`, `func`) → ints. Since CCP's 2025 SDE rework (JSONL/YAML, per-TQ-build, includes
`dbuffCollections`, `dynamicItemAttributes`, `dogmaUnits`), the client-extraction path is largely unnecessary.

## 4. Strengths to adopt

* Data-driven modifiers; tiny special-case surface; lazy attribute evaluation; zero-copy data.
* `sources` option (per-attribute provenance) = Pyfa's "Affected by" panel.
* Incoming/outgoing effect shape makes fit-to-fit projection composable *without recursion*:
  `outgoing(A)` feeds `incoming(B)`. Stateless and cacheable — perfect fit for our API.
* Snapshot tests on community fits.

## 5. Gaps vs Pyfa (what we must add)

| Area | dogma-engine | Pyfa | Our plan |
|---|---|---|---|
| DPS/volley per weapon & total, damage types, target-profile resists | via data patches only (ship-level attrs) | full per module/drone/fighter, spool options, reload factor | first-class `stats.offense` in engine |
| Cycle model (reload, reactivation delay, charges count, `CycleSequence`) | partial | full | port semantics |
| Spool (Entropic, mutadaptive RR, vorton chain?) | `spool.multiplier_bonus` | SPOOL_SCALE/CYCLE_SCALE/TIME/CYCLES | all 4 modes |
| Breacher pods, doomsday subcycles, smartbombs, bombs | ? | yes | special effects |
| Cap sim with reloads, staggering, injectors, received neuts | simple sim | full `capSim.py` | port algorithm (clean-room from doc 01 §7) |
| Sustainable tank (cap-limited) | no | yes | yes |
| Remote reps output, received RR, neut/nos in/out | partial (incoming effects) | yes | yes |
| Projected fits with distance & range factor, `amount` | user supplies attributes | full recursive | composable `projected[]` with distance |
| Command fits/boosters, generic command links | buffs by id/value | full | both: explicit buffs or booster fits |
| System effects (wormhole classes, abyssal weather, incursion, sov, insurgency, trig) | via incoming | projected "system" modules | `environment.effects[]` by beacon typeID |
| Graphs (10 families) | no | yes | `graphs` endpoint (sampled series) |
| Mining yield/drain/residue | no | yes | yes |
| Drones: active limit, bandwidth, control range, drone DPS & EHP | partial | yes | yes |
| Fighters: squadrons, abilities, tubes, DPS incl. missile/bomb abilities | partial | yes | yes |
| Validation (slots, hardpoints, rig size, maxGroupFitted/Active/Online, canFitShip*, CPU/PG/calib, drone bw) | yes (`validate/*`) | yes | yes (machine-readable violations) |
| Character profiles, skill import (ESI/XML), implant sets, damage/target profile libraries | no (out of scope) | yes | client side (MCP/UI) + presets in dataset |
| Prices, market tree, jargon search, item compare, item stats details | no | yes | `eve-fit-mcp` / UI services |
| Import/export: EFT, DNA, ESI, XML, multibuy, EFS, killmail, muta | EFT, ESI, link, killmail | EFT, DNA, XML, ESI, EFS, multibuy, muta, shipstats | all |
| Overrides (user-edited attribute values) | no | yes | `overrides[]` in request |
| Fleet/ship modes (T3D), subsystems (T3C) | yes | yes | yes |
| Structures (citadels, services, structure fighters, rigs) | yes | yes | yes |
