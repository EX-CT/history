# pending-1.10: EXCT fuzz findings (staged, not scored)

Separate from `pending.md` (E's legal-fit fuzz) so the two lists don't collide. Case names are prefixed `exct_fuzz_`.
Request JSONs and the Pyfa stats-oracle output are in `pending/exct/`.

Source: the graphs differential fuzz on eve-dogma-bench `graphs-round2` (`graphs/tools/fuzz_graphs.py`, seed 5, request
fz0767-81a1012d, 2026-10-03 09:40 CST). The graph-level disagreement comes from a stats-engine difference, so it's
filed here as a FitRequest case.

**Status (eve, 2026-10-03 11:00 CST): `exct_fuzz_rifter_standup_cap_battery` is OUT OF CONTRACT, not scored. A Standup
Cap Battery on a ship is an illegal in-game fit. Kept only as a record; no engine change required.**

| Candidate case | What it checks | Pyfa oracle | eve-dogma-rs 659737b / variant-g |
|---|---|---|---|
| `exct_fuzz_rifter_standup_cap_battery` (Rifter 587, 1× Standup Cap Battery I 47352, requested `active`, all skills V) | Pyfa's python effect `structureCapacitorCapacityBonus` (7027) adds the module's `capacitorBonus` (50000) to the ship's `capacitorCapacity` before the Capacitor Management skill multiplier. The SDE effect has no modifiers, so a modifier-only engine adds nothing | `cap_capacity` 62812.5 GJ, `cap_recharge_peak` 1675.0 GJ/s | **gap**: capacity 312.5, peak 8.33 (both) |

Adjudication (resolved: out of contract, see status above):
- **Illegal fit.** `oracle/fuzz/check_legal.py` says `legal: false`: a structure module on a ship
  (canFitShipGroup/Type restriction), and `active` is above the module's max state. The graphs fuzzer doesn't enforce
  fitting legality; E's generator does. If the bench only scores legal fits, drop the case or keep it as an
  unscored note. If calc must follow Pyfa on any fit, A and G need the effect 7027 handler (a single `capacitorBonus`
  → ship `capacitorCapacity` modAdd, as Pyfa does).
- State: under the reversed module-state ruling (contract draft 1.4.5, 2026-10-03 11:19 CST) the requested `active` is
  corrected to `online` with a warning, as Pyfa does. The battery has only passive and online effects, so this doesn't
  change any value.
