# Bench 1.9.0: released 2026-10-03 (tag v1.9.0; see CHANGELOG.md 1.9.0). Kept as the record of the freeze-time candidates.

Candidate cases and harness changes found during the freeze. Nothing here is scored yet.

Source: Variant F's Pyfa sweep (eve-dogma-lab `variant-f/RESULTS.md`), re-checked against Variant A and the Pyfa
oracle on 2026-10-03. The request JSONs are in eve-dogma-rs `tests/cases/` and `tests/fits/` (A at 0fa98c3 matches Pyfa
on all of them).

| Candidate case | What it checks | A before 0fa98c3 |
|---|---|---|
| `overheat_order_tengu` (exct_tengu, every active module overheated, EFT order) | Pyfa runs effects module by module, so the shield hardeners' overheat reads `overloadHardeningBonus` before the Defensive subsystem listed after them has boosted it | **gap**: shield resists 0.1769 vs Pyfa 0.1967 (EM), shield EHP 63,535 vs 60,836 |
| `overheat_order_rev_tengu` (same fit, module list reversed) | Control: the subsystem runs first and the full bonus applies | matched |
| `breacher_kestrel` (Kestrel, 2× Small Breacher Pod Launcher + SCARAB Breacher Pod S) | Breacher pod DoT is Pyfa `pure` damage (no resists), with volley = dps = one tick (`dotMaxDamagePerTick`). Only the strongest pod counts in fit totals, so 2 pods = 250, not 500 | **gap**: weapon_dps/volley 0 vs 250 |
| `neut_nos_vs_mwd_rifter` (Rifter with MWD on; small neut ×2 + heavy nos projected) | Projected neutralisers read the target signature before the late MWD bloom; nosferatu read it after | matched |
| `ewar_drones_rifter` (ECM / TP drones projected) | EWAR drone cycle time (speed before duration) | matched |

Contract consequence: a scored breacher case needs the additive `pure` damage key and `weapons[].kind = "breacher"`
(eve-dogma-rs `docs/contract.md`) in the bench contract and in the scorer's damage comparison.

Also checked with no gap in A, so no case is proposed for these:
- Python `round()`: A now uses correctly rounded, ties-to-even `round(cap, 1)` for the capsim wrap. This had no visible
  effect on any corpus; it could only matter on an exact .x5 tie.
- Command bursts: only the strongest buff applies (already covered at 1.8.0).
- The 14 effects Pyfa never applies (Domination barrage mutators, `ammoInfluenceEntityFlyRange`, the WDFG/focused
  script hidden effects, `leadershipCpuBonus`, the Impairor rookie disruption bonus, Snake `smugglingModifier`/
  `setBonusSerpentis2`, the industrial invulnerability core, the recloner, `online`). Probes on a Domination AC Rifter,
  Gleam Punisher, WDFG Heretic (with and without the focused script), Talos, Impairor TD, full Snake set, and a Rorqual
  with the Nexus core or the recloner all match Pyfa.
- Known data-version divergence, not a case: Paladin/Golem agility (Pyfa eve.db build 3532181 vs SDE 3569502).
