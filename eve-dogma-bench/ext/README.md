# ext suite: stats-ext, heat, fleet.buffs, overrides (bench 1.10, docs/20 P0-3 / P0-4)

116 cases. Values are keyed by JSON pointer into the **proposed** FitStats fields of CONTRACT.md "Draft 1.10:
stats-ext" (no engine implements them yet, so a missing pointer is reported as `not_implemented`), plus the bench
metrics (`values`) for every case.

| feature | cases | Pyfa source of the expected values |
|---|---|---|
| mining | 12 (1 with mining fleet buffs) | `fit.minerYield / minerDrain / droneYield / droneDrain` (m³/s; drain = volume removed incl. residue) |
| outgoing | 25 | `fit.getRemoteReps(spoolOptions)` shield / armor / hull HP/s and capacitor GJ/s, at the default spool and spool 0 / 1 (mutadaptive) |
| drone_ehp | 16 | `drone.hp`, `drone.ehp` (fit damage pattern), `calculateShieldRecharge()` per drone, same for fighters |
| bombing | 15 | `gui/builtinStatsViews/bombingViewFull.py` arithmetic: bombs to kill per bomb type (27920 / 27916 / 27912 / 27918), Covert Ops 0–5, red giant `smartbombDamageMultiplier`, signature factor, ceil to 0.1 |
| heat | 30 | `gui/builtinViewColumns/heat.py` `Thermodynamics` (loaded from Pyfa's source): `calcBurnCycles` and burnout time per overheated module |
| fleet.buffs | 12 | explicit `fleet.buffs` through Pyfa command bonuses (oracle `explicit_buffs`), incl. duplicate ids (Minimum / Maximum aggregate), titan generator buffs, a Claymore booster fit with and without an explicit override |
| overrides | 6 | **hand-derived, not Pyfa** (see below) |

Fits: hand-built reference fits (Venture, Hulk, Covetor, Procurer, Porpoise, Guardian, Basilisk, Oneiros, Scimitar,
Zarmazd, maintenance-bot Vexor / Dominix, ...) and random legal fits from the `oracle/fuzz/gen_legal.py` pool
(`pool_*`, first fit per distinct hull with the feature). 115/116 pass `oracle/fuzz/check_legal.py`; all are Pyfa
buildable.

**overrides is our own request feature** and is kept out of Pyfa comparisons (ruling 2026-10-03). Its 6 cases have
hand-derived expected values written by `tools/gen_ext.py`, each with a `derivation` text (oracle
`"hand-derived (non-Pyfa)"`): base-value override of ship maxVelocity / shieldCapacity at skills 0 and V, a module
attribute override applied to every module of that type, and charge damage overrides through a turret's
damageMultiplier.

```
python3 ext/tools/gen_ext.py [POOL_LIST LEGAL_JSONL]   # cases (+ hand-derived expected for overrides)
python3 ext/tools/make_expected.py                       # Pyfa oracle (ORACLE_EXTRA=ext) for the rest
python3 ext/tools/score.py --batch-cmd "ENGINE batch" --name X [--out r.json]
```
