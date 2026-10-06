# 03 — Pyfa feature parity checklist

Status legend — **Core**: engine (`eve-dogma-rs`); **API**: exposed in request/response schema; **MCP**: tool in `eve-fit-mcp`;
**UI**: future web UI. Values: ✅ done · 🟡 partial · ⬜ todo · ➖ not applicable (client-side concern).
Pyfa source references in parentheses. This file is updated as work lands (see each repo's PROGRESS.md).

## A. Dogma / attribute engine

| # | Feature (Pyfa ref) | Core | API | MCP | Notes |
|---|---|---|---|---|---|
| A1 | Base attributes from SDE incl. type fields (mass, volume, capacity, radius) | ✅ | ✅ | ✅ | type-level fields injected as attrs 4/161/38/162 |
| A2 | All CCP operators in order (PreAssign…PostAssign) (`modifiedAttributeDict.py`) | ✅ | ✅ | ✅ | |
| A3 | Stacking penalties, sign-split, sorted, `exp(-i²/7.1289)` | ✅ | ✅ | ✅ | |
| A4 | Penalty exemption by source category (ship/charge/skill/implant/subsystem/structure) | ✅ | | | |
| A5 | min/maxAttributeID clamp | ✅ | | | |
| A6 | Modifier funcs: Item/Location/LocationGroup/LocationRequiredSkill/OwnerRequiredSkill | ✅ | | | |
| A7 | Domains: shipID, charID, itemID, otherID (charge↔module), structureID, target | ✅ | | | target via projected |
| A8 | Skill levels drive bonuses (attr 280) | ✅ | ✅ | ✅ | |
| A9 | Effect categories gate by module state (passive/online/active/overload) | ✅ | ✅ | | |
| A10 | Overheat effects & heat attributes (`overheat` type effects) | 🟡 | ✅ | | data-driven part only; heat damage sim ⬜ |
| A11 | Remote resistance (`remoteResistanceID`, `<prefix>ResistanceID`) | ⬜ | | | |
| A12 | Attribute overrides (`saveddata/override.py`) | ✅ | ✅ | | request `overrides` |
| A13 | Mutated modules & drones (`mutator.py`, `mutatedMixin.py`) incl. range clamp | ✅ | ✅ | | base attrs + rolled values |
| A14 | cpu/power round to 2dp | ✅ | | | |
| A15 | "Affected by" provenance (`getAfflictions`) | ⬜ | ⬜ | | `options.sources` |
| A16 | Extended recompute (extra multipliers / ignore afflictors) for graphs (`getExtended`) | ⬜ | | | |

## B. Special effects (no/insufficient modifierInfo)

| # | Feature | Core | Notes |
|---|---|---|---|
| B1 | Propulsion: AB/MWD speed (`speedFactor·speedBoostFactor/mass`), mass add, MWD sig bloom | ✅ | |
| B2 | MicroJumpDrive / MJFG sig | ⬜ | |
| B3 | Local shield boost / armor rep / hull rep → `tank` | ✅ | |
| B4 | Ancillary boosters/reps with charges (paste multiplier) | ✅ | |
| B5 | Cap boosters (injectors) | 🟡 | in cap sim |
| B6 | Energy neut / nos out & in, neut sig-resolution reduction (`fit.addDrain`) | ⬜ | |
| B7 | Remote reps / RCT out (`getRemoteReps`), received RR | ⬜ | |
| B8 | Damage control / bastion / siege / triage / industrial core | 🟡 | data-driven parts |
| B9 | Reactive Armor Hardener adaptation (Effect4928) | ⬜ | |
| B10 | Spool-up weapons (Entropic, mutadaptive RR) – 4 spool modes (`spoolSupport.py`) | ✅ | |
| B11 | Breacher pods DoT | ⬜ | |
| B12 | Doomsday / lances / superweapons subcycles & delays | ⬜ | |
| B13 | Smartbombs, bombs, guided bombs | 🟡 | DPS only |
| B14 | Vorton projectors (chain) | 🟡 | DPS only |
| B15 | ECM projected (`addProjectedEcm`), jam chance | ⬜ | |
| B16 | Webs, TPs, damps, tracking/guidance disruptors, sensor boosters projected | ⬜ | via `projected` |
| B17 | Command bursts / warfare buffs (dbuffCollections, max-aggregate) | ✅ | buffs by id/value |
| B18 | Booster fits (fleet command from another fit) | ⬜ | |
| B19 | Generic command links (`commandLink.py`) | ✅ | = buffs |
| B20 | System effects: wormhole classes (C1–C6, Thera, drifter), abyssal weather/filaments, incursion, sov, insurgency, trig | ⬜ | `environment.effects` |
| B21 | T3D ship modes | ✅ | |
| B22 | T3C subsystems: slots/hardpoints added | ✅ | |
| B23 | Drone control range, max active drones, bandwidth | 🟡 | |
| B24 | Fighters: squadron size, abilities (attack, missiles, bombs, MWD, MJD, ECM…), tubes by class | 🟡 | |
| B25 | Structures (citadels): services, structure fighters, rigs, Upwell modules | 🟡 | |
| B26 | Boosters (drugs) & side effects selection | ✅ | |
| B27 | Implant sets bonuses (pirate sets multiply each other) | ✅ | data-driven |
| B28 | Security status-dependent bonuses (CONCORD ships/insurgency) | 🟡 | attr 2610 |
| B29 | Pyfa custom effects 100000+ (insurgency tackle range, sov/trig system buffs) | ⬜ | |
| B30 | Mining modules, drones, residue/waste, crystals (`calculatemining`) | ⬜ | |
| B31 | Cloaks, covert, warp core stabs (warp scramble status) | ✅ | attrs |

## C. Fit statistics (Pyfa stats panels: `gui/builtinStatsViews/*`)

| # | Stat | Core | Notes |
|---|---|---|---|
| C1 | Resources: CPU, PG, calibration, drone bandwidth/bay, fighter bay/tubes, cargo | ✅ | |
| C2 | Slots & hardpoints used/total (high/mid/low/rig/subsystem/service/turret/launcher) | ✅ | |
| C3 | Weapon volley & DPS per damage type, per module and total, reload factor | ✅ | |
| C4 | Drone volley/DPS | ✅ | |
| C5 | Fighter DPS | 🟡 | |
| C6 | DPS vs target profile resists | ✅ | |
| C7 | HP, resonances per layer, EHP vs damage pattern | ✅ | |
| C8 | Active tank (passive shield regen, shield/armor/hull reps, pre/full spool) raw & effective | ✅ | |
| C9 | Sustainable tank (cap-limited) | ⬜ | |
| C10 | Capacitor: capacity, recharge time, peak recharge, use, delta, stable % / time-to-empty (capSim) | ✅ | |
| C11 | Navigation: max speed (speedLimit cap), align time, warp speed, max warp distance, mass, agility, sig | ✅ | |
| C12 | Targeting: max targets (min of ship and character), range, scan res, sensor strength/type, lock time vs sig, probe size, jam chance | ✅ | |
| C13 | Drones: active count, control range | ✅ | |
| C14 | Mining yield/drain | ⬜ | |
| C15 | Remote reps output (outgoing view) | ⬜ | |
| C16 | Bombing view (bomb EHP needed etc. `bombingViewFull.py`) | ⬜ | |
| C17 | Price view (ship/fittings/drones/cargo totals) | ➖ | MCP/UI with market sources |
| C18 | Per-module columns: cap use, range/falloff, tracking, explosion stats, heat, ammo, price, misc (`builtinViewColumns/*`) | 🟡 | per-module attrs output |

## D. Validation (`module.fits/canHaveState/isValidState`, `fit.canFit`)

| # | Rule | Core |
|---|---|---|
| D1 | Slot counts, hardpoints | ✅ |
| D2 | CPU/PG/calibration overuse | ✅ |
| D3 | canFitShipGroup01..20 / canFitShipType01..11 | ✅ |
| D4 | maxGroupFitted / maxTypeFitted / maxGroupOnline / maxGroupActive | ✅ |
| D5 | rigSize match | ✅ |
| D6 | Capital module on subcap (`maxShipVolume`?/`isCapitalSize`) | 🟡 |
| D7 | Charge fits module (chargeGroup1..5, chargeSize, capacity) | ✅ |
| D8 | Skill requirements vs character | ✅ |
| D9 | Drone bandwidth / bay, fighter tubes per class | ✅ |
| D10 | Hisec restrictions (`disallowInHighSec`), structure-only modules | 🟡 |
| D11 | Subsystem slot uniqueness (1 per type) | ✅ |
| D12 | Boosters slot uniqueness, implant slot uniqueness | ✅ |

## E. Graphs (`graphs/data/*`)

| # | Graph | Core |
|---|---|---|
| E1 | Damage stats vs distance/time/target speed/sig (turret/missile/drone/fighter/bomb/smartbomb/doomsday/breacher/vorton application) | ⬜ |
| E2 | Application profile (best ammo per distance) | ⬜ |
| E3 | Capacitor amount vs time; regen vs cap % | ⬜ |
| E4 | Shield regen vs % | ⬜ |
| E5 | Mobility: speed & distance vs time | ⬜ |
| E6 | Warp time vs distance | ⬜ |
| E7 | Lock time vs target sig | ⬜ |
| E8 | Remote reps vs distance/time | ⬜ |
| E9 | Ewar stats vs distance | ⬜ |
| E10 | ECM burst / scanres damps | ⬜ |

## F. Import / export (`service/port/*`)

| # | Format | Core/lib |
|---|---|---|
| F1 | EFT text import/export (incl. mutated `[1]` refs, `/OFFLINE`, empty slots, `xN`, implants/boosters/cargo sections) | ⬜ |
| F2 | DNA (`shipID:mod;qty:...::`) & `fitting:` links | ⬜ |
| F3 | EVE XML fittings | ⬜ |
| F4 | ESI fittings JSON (flags) | ⬜ |
| F5 | EFS JSON export | ⬜ |
| F6 | Multibuy | ⬜ |
| F7 | Mutated module text (`muta.py`) | ⬜ |
| F8 | Ship stats text export | ⬜ |
| F9 | Killmail import | ⬜ |
| F10 | Clipboard / file (UI) | ➖ |
| F11 | Item rename conversions (`service/conversions/*`) | ⬜ (dataset) |

## G. Profiles & services (client side, provided by MCP/UI, not core)

| # | Feature | Where |
|---|---|---|
| G1 | Characters: All 0/All 5 presets, custom levels, save/load | MCP local store ⬜ |
| G2 | ESI SSO: import skills, implants, fittings; save fitting to EVE | MCP ⬜ |
| G3 | Damage pattern library (built-ins: uniform, EM/therm/kin/exp, NPC factions, ammo-to-pattern) | dataset presets ⬜ |
| G4 | Target profile library (resists + sig/speed/radius, NPC presets, "ideal") | dataset presets ⬜ |
| G5 | Implant sets (built-in pirate sets + user) | dataset ⬜ |
| G6 | Prices (Fuzzwork, EVE Tycoon, EveMarketData, ceve-market), caching | MCP ⬜ |
| G7 | Market browser tree, meta variations, search with jargon (`service/jargon`) | MCP/dataset ⬜ |
| G8 | Item stats/compare/"show info", traits | dataset + MCP ⬜ |
| G9 | Fit browser (ship tree), tags, notes, fit booster/projected management | UI ➖ |
| G10 | Settings: factor reload, spool default, RAH mode, compact skills | API `options` ✅ |
| G11 | Skill affectors view, "required skills" check, skill plan export | MCP ⬜ |
| G12 | Localisation (ja, zh, ru, …) | dataset names (SDE has 8 langs) ⬜ |
| G13 | Update check, db migrations | ➖ |
