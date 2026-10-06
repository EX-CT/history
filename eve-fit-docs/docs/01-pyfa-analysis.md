# 01 — Pyfa analysis (how it actually computes things)

Reference snapshot: `pyfa-org/Pyfa` master (shallow clone, Oct 2026). Paths relative to repo root.
Sizes: `eos/effects.py` 43 803 lines / **2 402 effect classes**; `eos/saveddata/fit.py` 2 004; `module.py` 1 138;
`eos/modifiedAttributeDict.py` 610; `eos/capSim.py` 309; total Python ≈ 133 k lines.

> 中文要点：Pyfa 的 eos 不读取 SDE 的 modifierInfo，而是 2402 个手写 Python 效果处理器；属性计算顺序为
> preAssign → preIncrease → multiplier → 叠加惩罚乘数（按组、正负分开、按幅度排序，exp(-i²/7.1289)）→ postIncrease → min/max 截断。
> 计算分 early/normal/late 三个 runTime，command / projected 递归计算。我们的新引擎用数据驱动 + 少量特殊效果复现。

## 1. Layering

| Layer | Path | Role |
|---|---|---|
| Static data | `staticdata/fsd_built/*.json`, `fsd_lite`, `phobos/` | JSON dumped by **Phobos** from client FSD; **no `modifierInfo`** kept (see `dogmaeffects.0.json`: only flags/attr IDs) |
| DB build | `db_update.py` (947 l.) | Loads JSON into SQLite `eve.db` (SQLAlchemy), adds custom pyfa effects/attributes |
| Gamedata ORM | `eos/gamedata.py`, `eos/db/gamedata/*` | `Item`, `Attribute`, `Effect` (handler proxied by effect name → `eos/effects.py` class) |
| Saved data | `eos/saveddata/*` | Stateful `Fit`, `Module`, `Drone`, `Fighter`, `Character`, `Skill`, `Implant`, `Booster`, `Mode`, `Cargo`, `DamagePattern`, `TargetProfile`, `ImplantSet`, `Mutator`, `Override`, `CommandLink`, `Citadel` |
| Attribute math | `eos/modifiedAttributeDict.py` | Per-item lazy modified attribute dict with operator buckets |
| Calc helpers | `eos/calc.py`, `eos/utils/{spoolSupport,cycles,stats}.py`, `eos/capSim.py` | penalties, range factor, lock time, spool, cycles, cap sim |
| Services | `service/*` | fit/market/character/price/ESI/port (import/export)/settings/jargon search |
| Graphs | `graphs/data/*` | 10 graph families with own calc code |
| GUI | `gui/*` (wxPython) | views, stats panels, context menus |

## 2. Attribute calculation — `eos/modifiedAttributeDict.py`

Each item has `itemModifiedAttributes` (and `chargeModifiedAttributes`). Effects call:

* `preAssign(attr, v)` → base override; `increase(attr, v, position="pre"|"post")`;
  `multiply(attr, m, stackingPenalties, penaltyGroup)`; `boost(attr, pct)` = `multiply(1+pct/100)`; `force(attr, v)`.
* Optional `skill=` multiplies the amount by skill level (`__handleSkill`); projected effects pass `effect=` and get
  **remote resistance** applied: `m' = (m-1)*resist + 1` where resist attr comes from `effect.resistanceID` or
  `<prefix>ResistanceID` / `remoteResistanceID` attribute of the source (`getResistanceAttrID`, l.65).

`__calculateValue` (l.323) order:

1. If forced → clamp to min/max attr and return.
2. `val = intermediary or preAssign or original(mutator > override > base) or attribute default`.
3. `val += preIncrease`; `val *= multiplier` (product of all unpenalised multipliers).
4. For **each penalty group** independently: split `>1` and `<1` multipliers, sort by `|m-1|` descending,
   `val *= 1 + (m-1) * exp(-(i^2)/7.1289)` for i = 0,1,2…  (7.1289 = 2.67², i.e. factor 0.8691^(i²)).
5. `val += postIncrease`; clamp by `minAttributeID`/`maxAttributeID` of the attribute (values read off *same item*).
6. `cpu`, `power`, `cpuOutput`, `powerOutput` rounded to 2 dp.

Notable: Pyfa merges CCP operators into 4 buckets (pre-assign, pre-inc, multiply, post-inc). CCP dogma
`modifierInfo.operation` codes (verified against SDE build 3569502): **-1 PreAssign, 0 PreMul, 1 PreDiv, 2 ModAdd,
3 ModSub, 4 PostMul, 5 PostDiv, 6 PostPercent, 7 PostAssign, 9 SkillLevel (SP→level, ignore)**. CCP's evaluation
order is PreAssign → PreMul → PreDiv → ModAdd → ModSub → PostMul → PostDiv → PostPercent → PostAssign. Pyfa's
collapse gives the same results for real data because adds and multiplies on the same attribute are rare and
ordered consistently. Our engine implements the full CCP order (as dogma-engine does) and tests vs Pyfa.

Skill levels are *data-driven* in the SDE: every skill has `skillEffect` and effects such as
`gunnerySkillBoostTurretSpeeBonus` = `ItemModifier(itemID) PreMul attr441 by skillLevel(280)`, so setting
attribute 280 on the skill item to the trained level is enough. Pyfa instead multiplies by `skill.level` in each
handler (`level = container.level if 'skill' in context else 1`).

Stacking-penalty rule: penalised iff the *modified attribute* is not `stackable` (SDE `dogmaAttributes.stackable=false`)
**and** the source item category is not exempt (Ship, Skill, Implant, Subsystem, Charge in some cases, Booster) —
in Pyfa this is encoded per handler (`stackingPenalties=True`); in data-driven engines it's derived from
`stackable` + source category (dogma-engine `pass_2.rs`). Penalty groups: Pyfa uses `"default"` plus custom ones
(e.g. `postMul`, `postDiv`, `preMul` for some, and separate groups for e.g. *heat* & *command* bonuses).

`getExtended(...)` re-computes with extra multipliers / ignored afflictors — used by graphs to apply webs/TPs
at distance without re-running the fit.

## 3. Fit calculation — `eos/saveddata/fit.py::calculateModifiedAttributes` (l.993)

* Recursive with `CalcType` LOCAL / PROJECTED / COMMAND (`eos/const.py`).
* Command fits are calculated first (their modules call `fit.addCommandBonus(warfareBuffID, value, …)`), the
  strongest value per buff ID is kept, then `__runCommandBoosts(runTime)` (l.613) applies a **hard-coded table of
  warfare buff IDs 10–~90** (shield/armor/info/skirmish/mining bursts, titan/structure/sov/insurgency buffs).
  The SDE now ships `dbuffCollections` describing these declaratively (`aggregateMode`, `operationName`,
  `itemModifiers`, `locationGroupModifiers`, `locationRequiredSkillModifiers`, …) → data-driven in our engine.
* Three **runTime** passes: `early`, `normal`, `late` (`gamedata.Effect.runTime`). Items iterated in order:
  character+ship, drones, fighters, boosters, implants, modules, then restricted: mode, projected drones/fighters/
  modules (system effects are projected modules with `FittingSlot.SYSTEM`). Structures have a restricted set.
* Projected fits: `__runProjectionEffects` applies source modules/drones/fighters onto target `amount` times with
  `projectionRange` (distance) → range factor via `calculateRangeFactor` (`eos/calc.py`).
* Effect `type` tags: `passive` 2 129, `('projected','passive')` 99, `active` 94, `projected` 33, `overheat` 19,
  `('projected','passive','gang')` 12, `offline` 4. A module's state (offline/online/active/overheated,
  `FittingModuleState` −1/0/1/2) gates which effects run.

## 4. Effect handlers — `eos/effects.py`

* One class per effect ID (`Effect<ID>`), docstring = effect name + "Used by". Typical handler:
  `fit.modules.filteredItemBoost(lambda mod: mod.item.requiresSkill('Small Projectile Turret'), 'damageMultiplier', container.getModifiedItemAttr('damageMultiplierBonus') * level)`.
  These are 1:1 translations of CCP `modifierInfo` (`LocationRequiredSkillModifier` on `shipID` etc.).
* Pyfa custom effects `Effect100000+` (`pyfaCustom*`): insurgency/sov/trig system buffs, etc.
* Truly special logic lives in a few dozen handlers: `adaptiveArmorHardener` (Effect4928, RAH simulation, `runTime='late'`),
  propulsion (`moduleBonusAfterburner/Microwarpdrive`: speed = speedFactor·thrust/mass), cap boosters,
  neut/nos (`fit.addDrain`), ECM (`fit.addProjectedEcm`), local reps (`fit.extraAttributes.increase('armorRepair', …)`),
  `maxTargetsLockedFromSkills`, damage-control, spool weapons (Entropic/vorton/mutadaptive), breacher pods, doomsday,
  fighter abilities, structure services, ship modes (T3D), subsystems (slot/hardpoint modifiers), drone control.

## 5. Module stats — `eos/saveddata/module.py`

* `rawCycleTime` (l.1026) = max(speed, duration, durationHighisGood, burst-projector durations).
* `getCycleParameters` (l.968): `CycleInfo(active, inactive, quantity, isInactivityReload)` / `CycleSequence`;
  takes reload into account when `fit.factorReload` (numShots from charges/capacity, `reloadTime`, `moduleReactivationDelay`).
* `getVolleyParameters` (l.477): damage per volley by time offset; charge damage × `damageMultiplier`; doomsday
  delays/subcycles; breacher DoT (absolute `dotMaxDamagePerTick`, relative `dotMaxHPPercentagePerTick`); spool
  multiplier via `calculateSpoolup` (`eos/utils/spoolSupport.py`: SPOOL_SCALE / CYCLE_SCALE / TIME / CYCLES).
* `getDps` = Σ volleys / (averageCycleTime/1000). Target profile resists applied in `DmgTypes`.
* `getRepAmountParameters`/`getRemoteReps` (l.580/606) for RR/RAR/RCT incl. ancillary paste multiplier.
* `maxRange` (l.305) / `falloff` (l.374): turrets optimal/falloff; missiles = velocity × flightTime (with
  ship-radius & 'missile range' nuance), smartbombs `empFieldRange`, bombs, etc.
* `fits`/`canHaveState`/`isValidState` (l.661/755/732): slot, hardpoints, `canFitShipGroup/Type` attrs,
  `maxGroupFitted`, `maxGroupActive`, `maxGroupOnline`, `maxTypeFitted`, rig size, capital-size restriction,
  system/structure restrictions, `disallowInEmpireSpace`/hisec, projected-only states.
* `capUse` = capNeed / cycle.

## 6. Fit-level stats — `fit.py`

| Stat | Code | Formula |
|---|---|---|
| align time | `alignTime` l.455 | `-ln(0.25) · agility · mass / 1e6` |
| max speed | `maxSpeed` l.447 | `maxVelocity` capped by `speedLimit` |
| warp speed | `warpSpeed` l.1382 | `baseWarpSpeed · warpSpeedMultiplier` AU/s |
| max warp distance | l.1388 | `capacitorCapacity / (mass · warpCapacitorNeed)` |
| probe size | `probeSize` l.1367 | `max(sig/scanStrength, 1.08)` |
| scan strength/type | l.420/425 | max of 4 sensor strengths |
| jam chance | `jamChance` l.439 | `1-Π(1-min(1, jam/sensor))` |
| lock time | `eos/calc.py::calculateLockTime` | `min(40000/scanRes/asinh(sig)², 1800)` s |
| peak cap/shield recharge | l.1434/1441 | `10/τ · √p(1-√p) · C`, p=0.25 |
| HP / EHP | `hp`, `ehp` l.1575/1583; `damagePattern.calculateEhp` | `HP / Σ(w_i · resonance_i)` per layer |
| tank (active) | `tank` l.1594 | passive shield + local reps (`extraAttributes`) + applied RR, armour pre/full spool |
| sustainable tank | `calculateSustainableTank` l.1634 | reps limited by cap stability (iteratively disables reps by cap efficiency) |
| cap sim | `simulateCap` l.1508 → `eos/capSim.py` | see §7 |
| weapon/drone DPS & volley | l.347–372, `calculateWeaponDmgStats` l.1786 | per module/drone/fighter, spool options |
| mining yield/drain (residue) | `calculatemining` l.1768 | m³/s, residue/waste |
| remote reps out | `getRemoteReps` l.1560 | per type, spool aware |
| resources | `cpuUsed`, `pgUsed`, `calibrationUsed`, `droneBandwidthUsed`, `droneBayUsed`, `fighterBayUsed`, `fighterTubesUsed`, `cargoBayUsed`, slots, hardpoints | sums of online items |
| active drones limit | `activeDrones`, `getReleaseLimitForDrone` | `maxActiveDrones` + bandwidth |
| security | `getSystemSecurity`, `getPilotSecurity` | affects e.g. Concord/Insurgency bonuses |

## 7. Capacitor simulator — `eos/capSim.py`

Event-driven heap simulation (up to 24 h simulated): each active module = (duration, capNeed, clipSize,
disableStagger, reloadTime, isInjector). Cap regen between events uses the exact EVE curve
`C(t) = C_max·(1 + (√(c/C_max) − 1)·e^{(t0−t)/τ})²`, τ = rechargeRate/5. Identical modules are grouped
(multiplied capNeed or staggered); period optimisation via LCM of durations detects stability early
(`cap ≥ cap_at_last_wrap`). Cap boosters (injectors) postponed when they'd overshoot. Outputs: stable?,
lowest/high-water %, time to empty, `cap_stable_eve` (EVE's analytical estimate), and a time series for graphs.
Neuts/nos received (`fit.addDrain`) are included, with neut signature-resolution reduction.

## 8. Graphs — `graphs/data/*`

`fitDamageStats` (DPS/volley vs distance/time/target speed/sig; turret tracking chance-to-hit with angular speed,
missile application `(sig/er)`, `(sig·ev/er·v)^drf`, bombs, guided bombs, vorton, breacher, smartbomb, doomsday,
drones (orbit/approach modes), fighters; projected webs/TPs at distance in `calc/projected.py`),
`fitApplicationProfile`, `fitCapacitor` (cap vs time, regen vs %), `fitShieldRegen`, `fitMobility` (speed &
distance vs time: `v(t)=v_max(1−e^{−t·1e6/(m·agility)})`), `fitWarpTime` (warp acceleration/deceleration
profile), `fitLockTime` vs target sig, `fitRemoteReps` vs distance/time, `fitEwarStats` (web/TP/damp/WD/GD vs
distance), `fitEcmBurstScanresDamps`.

## 9. Services & ports

* `service/port/eft.py` (EFT text incl. mutated modules/`[Empty ... slot]`, offline `/OFFLINE`, charges, drones `xN`,
  cargo, implants/boosters sections), `dna.py` (ship DNA `shipID:mod;qty:...::`), `xml.py` (EVE client XML),
  `esi.py` (ESI fittings JSON with flags), `efs.py` (EVE Fitting Stats JSON export), `multibuy.py`, `muta.py`
  (mutated module text), `shipstats.py` (text stats).
* `service/esi.py`, `esiAccess.py`: SSO login, import skills, fetch/save fittings.
* `service/price.py` + `marketSources/{fuzzwork,evetycoon,evemarketdata,cevemarket}` — prices, cached.
* `service/character.py`: characters (All 0/All 5 built-ins), skill import from XML/ESI, implant sets.
* `service/jargon/*`: search abbreviations ("lse", "mwd", "dc").
* `service/conversions/*`: historical item renames (old fits still import).
* Settings: factor reload, spool default, RAH adaptation, compact skills, market source, etc.

## 10. Why Pyfa is slow

* Python object graph + SQLAlchemy entities; each attribute access goes through dict layers & `getAttributeInfo` DB
  queries (caches added piecemeal — see comments at l.53–61, l.337).
* 2 400 handlers iterated per runTime with Python lambdas filtering *every* module for each effect
  (`filteredItemBoost` is O(effects × items)).
* Full fit recalculation on each change; graphs re-run `getExtended` thousands of times.

Our design: precompiled modifier index (by domain/filter), flat arrays, single pass with lazy memoised attribute
evaluation (like dogma-engine), no allocation in hot loops.
