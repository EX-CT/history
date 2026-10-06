# F coverage: correctness suites × F refs

Correctness only, no timing. Runner: `run_f_coverage.py` (this folder) on the EXCT box, by eve3. Native release
builds (`cargo build --release`, `EVE_DOGMA_DATASET=dataset-3569502.json.gz`) from `EX-CT/eve-dogma-lab`; 10 s per
request. **No crash or timeout in any suite × ref.** First three columns: 2026-10-03 ~11:15 CST; `4b8f5f9` column and
the graphs 0.3 / pending-1.10-head rows: 11:39 CST (load 1.7, no evaluate process running).

| F ref | what |
|---|---|
| `bc84e2b` | variant-f round-1 evaluated commit (07:34 CST) |
| `af1c04b` | variant-f head (09:18 CST, formats work) |
| `6e2ebf1` | variant-f-perf head at the 11:13 CST fetch (commit 11:09 CST) |
| `4b8f5f9` | variant-f-features head (11:31 CST): graphs-g4 merged + the three gap fixes |

| suite (pinned) | `bc84e2b` | `af1c04b` | `6e2ebf1` | `4b8f5f9` |
|---|---|---|---|---|
| bench `v1.9.0` (d2edf98), 331 cases | 330/331 | 330/331 | 330/331 | **331/331** |
| cap-suite `d80cc38`, 150 | 147/150 | 147/150 | 147/150 | **150/150** |
| mutated-suite `2ac7c00`, stats 93 (EFT export 93 / import 99) | 86/93 (EFT 85/93 / 96/99) | 86/93 (EFT 85/93 / 96/99) | 86/93 (EFT 85/93 / 96/99) | **93/93** (EFT 93/93 / 99/99) |
| formats-suite `7c716e7`, FORMATS 0.1, 4779 scored rows | 4773/4779 | 4779/4779 | 4779/4779 | **4779/4779** |
| graphs 0.2 (`84f7c2e`), 178, rpc + graph-batch | 0/178 | 0/178 | 0/178 | **178/178** |
| graphs **0.3** (tag `graphs-v0.3` = `db81b8c`), 192, rpc + graph-batch | 0/192 | 0/192 | 0/192 | **192/192** |
| pending-1.10 `3193689`: 8 `e_fz_*` + 200 legal fuzz fits | e_fz 8/8; fuzz 198/200 | e_fz 8/8; fuzz 198/200 | e_fz 8/8; fuzz 198/200 | e_fz 8/8; fuzz 198/200 |
| pending-1.10 head `6b10d26`, full corpus 339 + module-state check (1.4.5, 3 cases) | 338/339; state 3/3 | 338/339; state 3/3 | 338/339; state 3/3 | **339/339**; state 3/3 |

**`4b8f5f9` (variant-f-features) verified:** every suite passes. bench 1.9.0 331/331 (22 046/22 046 values), cap 150/150,
mutated stats 93/93 with EFT export 93/93 and import 99/99, formats 4779/4779, graphs 0.2 178/178 (2437/2437 values, both
interfaces; informational charge ids 120/120), graphs 0.3 192/192 (2694/2694, both interfaces; informational charge
ids 138/161, not scored), pending-1.10 head 339/339 (22 513/22 513 values) and module-state 1.4.5 check 3/3, e_fz 8/8.
The only non-pass is fuzz 198/200: `lf10_123_28659` and `lf10_197_28659` (Paladin `align_time_s` 10.29 vs 102.93), which
is known oracle data drift (Pyfa eve.db 3532181 agility 0.858 vs SDE 3569502 0.0858; docs/15 class (a)), so effectively
200/200.

pending-1.10: the request said 334 cases (the corpus at `ed8deaa`). The branch head at run time was `6b10d26`
(11:38 CST), after `5fa7b5a` merged main (bench 1.9.0), so it has 339 cases = those 334 + the 5 new 1.9.0 cases.

Graphs: the three `variant-f` / `variant-f-perf` refs have no graph layer (every case → `UNKNOWN_METHOD graph`), so
their 0/178 and 0/192 mean "no interface", not wrong numbers. Official round-2 result for `graphs-g4` (`f73ff1c`):
`eve-dogma-bench@graphs-round2 562a201`, 178/178 + stats 326/326.

## Failing case ids (older refs)

Identical at `bc84e2b`, `af1c04b`, `6e2ebf1` unless noted; all fixed in `4b8f5f9`.

- **bench v1.9.0 and pending-1.10 head:** `breacher_kestrel` (`weapon_pure_dps` / `weapon_pure_volley` 0 vs 250; breacher pure damage).
- **cap-suite:** `hard_three_void_bombs`, `hard_void_bomb_bs`, `in_void_bomb` (void bomb not a cap drain: `use_gj_s`, `delta_gj_s`, `depletes_in_s`).
- **mutated-suite stats:** `combo_nomad_ab_mwd_exct_damnation` (missile `explosion_radius` w9–w11), `combo_two_boosters_dda_exct_dominix`
  (armor HP/EHP, `max_velocity`), `slot_booster_slot_first_wins_exct_rifter`, `slot_booster_slot_first_wins_rev_exct_rifter`,
  `slot_booster_three_slots_exct_rifter`, `slot_implant_slot_first_wins_exct_rifter`, `slot_implant_slot_first_wins_rev_exct_rifter` (slot conflicts).
- **mutated-suite EFT** export 85/93: `combo_two_boosters_dda_exct_dominix`, `drone_bouncer_ii_drones_sentry_dominix`, `drone_ogre_ii_exct_rattlesnake`
  + the five `slot_*` above; import 96/99: `state_lse_offline_exct_nightmare`, `eftedge_header_base_mismatch`, `eftedge_missing_ref`.
- **formats-suite, `bc84e2b` only:** `edge_export/name_newline.json@import:xml`, `eft_case_names.eft.txt@auto`, `eft_header_empty_name.eft.txt@auto`,
  `xml_malformed.xml@auto`, `xml_no_fittings.xml@auto`, `auto_garbage.txt@xml`.
- **fuzz (all four refs):** `lf10_123_28659`, `lf10_197_28659`: oracle data drift, see above.

## Files
- `<suite>__<ref>.json`: pass/total, every failing case with mismatches, crashes, timeouts, suite pin (graphs: per interface;
  pending-1.10-head: module-state check output).
- `<suite>__<ref>.csv`: one row per failing case (`suite,f_ref,case_id,kind,detail`).
- `run_f_coverage.py`: the runner (box paths; needs the suite worktrees named in it).
