# Known Pyfa data drift

Pyfa is the bench oracle, but its bundled game data (`eve.db`, Pyfa v2.69.0 `1d9f72b`) is from CCP client build
**3532181** (SDE released 2026-09-22). The pipeline dataset follows CCP's current SDE (3569502). Where they disagree,
the pipeline keeps CCP's data and the difference is recorded here. Machine-readable list:
[`pyfa-data-drift.json`](pyfa-data-drift.json). Oracle comparisons and fuzzers should load that file (or copy its
entries) and treat matching diffs as expected, not as engine bugs.

## How it was checked (2026-10-03)
- Re-downloaded CCP SDE zips 3532181 and 3569502 from developers.eveonline.com and compared every
  `typeDogma` value with Pyfa `eve.db`, Pyfa `staticdata/fsd_built` and dataset 3569502.
- Pipeline fidelity: raw SDE 3569502 vs `dataset-3569502.json.gz`: 0 value diffs, 0 dropped, 0 extra attributes
  over all 10 746 types.
- Pyfa vs dataset over all shared types: 6 attribute values differ (below), all explained. Ship mass, capacity,
  volume and radius match on every ship. About 140 unpublished / special-edition / NPC ships are missing in
  `eve.db` (Pyfa filters them).
- Third reference: ESI `/universe/types/{id}` on server 3569502.
- Re-run: `python3 tools/pyfa_drift.py --eve-db PATH/eve.db --dataset dist/dataset-*.json.gz`.

## Entries

| id | Types | Attribute | Pyfa | SDE 3569502 / ESI | Metrics | Decision |
|---|---|---|---|---|---|---|
| `paladin-agility` | Paladin 28659 | 70 agility | 0.858 | 0.0858 | `align_time_s` | Expected difference. CCP fixed it after 3532181, by 3552227 |
| `golem-agility` | Golem 28710 | 70 agility | 0.963 | 0.0963 | `align_time_s` | Expected difference, same CCP fix |
| `remote-capacitor-impedance` | 47 capitals; Siege/Triage/Bastion/Industrial Core users | 6463 / 6464, effect 6184 | resistance attr 2116, no 6463/6464 | resistance attr 6463 | `cap_stable`, `cap_stable_percent` of a target receiving remote cap | Expected difference |
| `t3c-max-subsystems` | Tengu, Legion, Proteus, Loki | 1367 maxSubSystems | 4 | 5 | none today | Keep CCP's 5, no patch |

Kronos (0.0925) and Vargur (0.0888) agree in every source.

### 1. Paladin and Golem agility (decided by eve, 2026-10-03)
CCP's SDE 3532181 had Paladin 0.858 and Golem 0.963. By 3552227 (2026-09-28) they are 0.0858 and 0.0963, and
the live server (ESI) agrees. With mass 128 000 000 the Paladin aligns in about 7.6 s with 0.0858. With 0.858 it
would take about 76 s. The pipeline keeps CCP's value. Any Pyfa-oracle comparison of `align_time_s` on these hulls
is an expected difference until Pyfa ships newer data.

### 2. T3C subsystem slots, attribute 1367 (decided by eve, 2026-10-03)
This is not CCP drift. Pyfa's `db_update.py` overwrites `maxSubSystems` with 4 in post-processing, because only 4
subsystem slots are usable. **No pipeline patch**: the dataset keeps CCP's 5. Fit legality (exactly one subsystem
per slot type, 4 in total) is the engine / validation layer's job, and it should behave like Pyfa. No bench metric
reads 1367 today.

### 3. Remote capacitor impedance, attributes 6463/6464 (decided by eve, 2026-10-03)
After 3532181 CCP added `remoteCapacitorImpedance` (6463, default 1.0) and `remoteCapacitorImpedanceBonus`
(6464). Effect 6184 `shipModuleRemoteCapacitorTransmitter` now resists with 6463 instead of 2116
`remoteRepairImpedance`. Capitals carry 6463 = 1.0. Siege, Triage and Bastion modules and Industrial Cores
(effects 6582, 6581, 6658, 4575, 8119) multiply the ship's 6463 by (1 − 0.999999). Pyfa's data has neither
attribute. **Keep**. Cases where a remote capacitor transmitter is projected onto one of the listed capitals,
or onto any ship running one of those modules, are expected differences in the target's capacitor results.
Other targets resolve to 1.0 on both sides and are unaffected. Fighters (6463 = 0) and Upwell structures
(1e-05 or 0) also carry 6463. They are outside the bench and fuzz scope, and `tools/pyfa_drift.py` lists them as
`only-dataset 6463` on 111 types.

## Maintenance
When Pyfa ships a newer `eve.db`, re-run `tools/pyfa_drift.py`, drop the entries that disappear, and update
`pyfa.client_build`. When CCP changes a listed value again, `tests/test_pyfa_drift.py` fails for that SDE build,
which is the signal to review this list.
