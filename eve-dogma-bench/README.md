# eve-dogma-bench

> **Bench 1.10.0** (released 2026-10-03, tag `v1.10.0`): 339 core cases, 22 513 values, contract 1.4.5; new suites
> `effects/` (2 378 per-effect Pyfa micro-fits, full attribute dump) and `ext/` (116: mining, outgoing RR, drone EHP,
> bombing, heat, fleet.buffs, overrides). The round-1 evaluation (`tools/evaluate.py`) stays pinned to the frozen
> 1.8.0 case set (`3da9671`). See CHANGELOG.md.


Shared, engine-agnostic test & benchmark harness for EVE Online fitting engines (EX-CT).
Any implementation of [CONTRACT.md](CONTRACT.md) (stateless FitRequest JSON → FitStats JSON) can be scored
on **correctness against Pyfa** (per stat, with tolerance), **speed** (cold start, per-fit latency, batch throughput)
and **determinism**.

```
cases/       FitRequest JSON files (the corpus; fully resolved type ids, no EFT needed)
expected/    expected values per case, produced by the Pyfa oracle (+ known_divergences.json)
expected_extra/ informational checks outside accuracy scoring (eft_export.jsonl: Pyfa exportEft texts)
oracle/      pyfa_oracle.py (GPL-3.0 test tool: runs Pyfa's eos engine headless as a black box)
tools/       metrics.py (metric -> JSON pointer, tolerance), make_expected.py (regenerate expected/)
run.py       the runner / scorer
effects/     per-effect suite (cases, expected, MANIFEST.json, tools/score.py), see effects/README.md
ext/         stats-ext / heat / fleet.buffs / overrides suite (draft fields), see ext/README.md
inventory/   suites.yaml + tests.yaml for tools/check_inventory.py (docs/19 item -> tests gate)
results-1.10/ release results of the 1.10 suites (tracked; results/ itself is local)
results/     scorecards (results/<variant>/scorecard.{md,json}, failures.json)
```

## Dataset (same for every variant)

All variants must load the **same SDE build**: `dataset-3569502.json.gz` (CCP SDE build 3569502, 2026-10-02),
published as a release asset of [EX-CT/eve-sde-pipeline](https://github.com/EX-CT/eve-sde-pipeline/releases/tag/sde-3569502):

```bash
gh release download sde-3569502 -R EX-CT/eve-sde-pipeline -D data/
# on the shared EXCT box it already exists at /workspace/exct-eve/data/dataset-3569502.json.gz
```

Format: gzip JSON documented in eve-sde-pipeline (`types`, `attributes`, `effects` with compact modifier tuples
`[func, domain, modified_attr, modifying_attr, operation, group_or_skill]`, `dbuffs`, `mutaplasmids`, …).
A variant may convert it to any internal format, but must not use other data.

## Scoring all variants (A–K)

```bash
python3 bench.py                 # all variants in variants.yaml -> results/combined.md + per-variant scorecards
# results/ is local to the checkout (not tracked), so `git pull` never conflicts with scorecards written by other runs
python3 bench.py --only A,C --quick --no-build
```

Each lab variant (branch `variant-x` of EX-CT/eve-dogma-lab, directory `variant-x/`) ships a **`bench.yaml`**:

```yaml
build: cargo build --release                      # run in variant-x/ (optional)
cmd: ./target/release/engine calc --dataset {dataset}        # one request on stdin -> one response on stdout
batch_cmd: ./target/release/engine batch --dataset {dataset} # JSONL in -> JSONL out (optional but scored)
```

Optional `rpc_cmd:` (a JSONL RPC process, see CONTRACT.md) enables the informational EFT-export check
(`tools/check_eft_export.py`, Pyfa byte-exact, shown as "eft export" in combined.md; not part of accuracy).

Contract rulings in force (CONTRACT.md revision 1.4.2; precise use_gj_s / projected amount / fleet-buff precedence in its "Semantics" section): calc error → exit 2 with the JSON error on stdout;
`options` omitted → `validate` true; `search` not scored (interim spec in CONTRACT.md); EFT export = Pyfa's exporter
exactly (no T3D mode line, as Pyfa).

Placeholders: `{dataset}` (shared dataset path from variants.yaml), `{bench}` (bench checkout), `{dir}` (variant dir).
bench.py clones/fetches the branch into `work/<letter>/`, builds, runs, and records status
(`unavailable`, `no-manifest`, `build-failed`, `run-failed`, `ok`) in the combined table.

## Round-1 evaluation (all variants, scored)

```bash
python3 tools/evaluate.py --as-of 2026-10-03T10:15:00+08:00 --runs 3 --fresh-clones   # results/evaluation.{md,json}; heads as of the cutoff, no fallback
python3 tools/evaluate.py --dry-run --runs 2 --quick --only A,J                          # results/dryrun/ (labelled DRY RUN)
```

Fetches A (eve-dogma-rs main) and B–K (eve-dogma-lab variant-x) at the cutoff, builds, runs the official scorer
`--runs` times (median, loadavg per run, hard timeouts), probes EFT/RPC/search/type, collects maintainability metrics
and the variants' own tests, and ranks variants that pass every case. Always scores against the frozen 1.8.0 case set (bench `3da9671`, 326 cases, extracted with `git archive`, independent of upstream main); latency is its own single-CPU measurement (median of ≥5 samples with sanity checks); a licensing table shows whether each variant can merge into the LGPL-3.0-or-later mainline. Rules and formulas: docstring of
[tools/evaluate.py](tools/evaluate.py) (also printed in the md output).

## Plugging a variant in (single run)

Provide one command that reads one FitRequest on stdin and prints one FitStats JSON on stdout, and (strongly
recommended) a batch command that reads JSONL requests and prints JSONL responses in order:

```bash
python3 run.py --name variant-x \
  --cmd       "/path/to/engine calc  --dataset /workspace/exct-eve/data/dataset-3569502.json.gz" \
  --batch-cmd "/path/to/engine batch --dataset /workspace/exct-eve/data/dataset-3569502.json.gz" \
  [--cwd DIR] [--cases 'cases/esf_*.json'] [--batch-repeat 5] [--latency-n 500]
```

The response only needs the fields listed in [tools/metrics.py](tools/metrics.py) (JSON pointers into FitStats,
e.g. `/defense/ehp/armor`, `/capacitor/stable_percent`; `a+b` = sum; `name[key=value]` selects an array element, e.g. `/offense/weapons[module_index=3]/tracking`). Missing fields count as wrong.
Tolerance: `|got-want| <= max(1e-3, 1e-4*|want|)`; booleans exact.

Scorecard (`results/<name>/scorecard.md`): cases fully correct, values correct per group (fitting, defense,
tank, offense, capacitor, navigation, targeting), one-process-per-case median wall time (≈ cold start),
batch throughput (fits/s over the whole corpus × N), per-calc latency for one fit (N repetitions in one process),
determinism (identical output for identical input), plus `failures.json` with every mismatch.

## Corpus

339 cases (331 of 1.9.0 + 8 `e_fz_*` from the differential fuzz): 101 dogma-engine (EVE Ship Fit) community/regression fits, 35 hand-written fits (frigates, destroyers,
T3D modes, cruisers, HACs, T3C subsystems, battleships, marauders in bastion, logistics, command ships, interdictor,
mining, carriers/supercarrier with fighters, structures with rigs/service modules, titan lance, HIC bubble, emergency hull energizer, entosis, micro jump field generator, breacher pods), 195 variations (fleet command booster fits, projected whole fits, incoming remote reps/neuts/nos/cap transfers, scripted projected modules, wormhole environments C1–C6, abyssal weather / AoE clouds, incursion system effects, burst projectors and Standup weapon disruptors, implant sets, combat boosters, overheat module order, EWAR drones, skills 0/2/3/4,
damage patterns incl. Reactive Armor Hardener adaptation, reload, projected webs/target painters/damps/web drones/TD drones,
mutated modules and drones). See `cases/`.

Expected values come from Pyfa (eos, Pyfa client data build 3532181) via `oracle/pyfa_oracle.py`; regenerate with
`python3 tools/make_expected.py`. Pyfa is the reference, not the truth: `expected/known_divergences.json` lists
metrics excluded because Pyfa's data is older than the SDE or because Pyfa disagrees with CCP's own modifiers.

## Current results

Bench 1.10.0, 2026-10-03 12:05 CST, shared box (load average 0.5–1.6 during the runs). Core = `run.py` on `cases/`
(339 cases, 22 513 values); effects = `effects/tools/score.py`; ext = `ext/tools/score.py`.

| engine | core cases | core values | effects | ext | batch fits/s | latency/fit | cold start + calc |
|---|---|---|---|---|---|---|---|
| F: eve-dogma-lab variant-f-features 4b8f5f9 | 339/339 | 22 513/22 513 | 2 107/2 378 | 18/116 | 20 683 | 0.036 ms | 4.6 ms |
| eve-dogma-rs d6043a7 | 325/339 | 22 499/22 513 | 2 095/2 378 | 18/116 | 5 338 | 0.128 ms | 9.2 ms |
| Pyfa (reference, Python) | – | – | – | – | – | 10–31 ms | ~390 ms first calc + startup |

- eve-dogma-rs core failures: `e_fz_cloak_wcs_penalty_group_ninazu e_fz_drone_speed_orbweaver_dagon
  e_fz_drone_speed_torafugu_odysseus e_fz_offline_cloak_hulk e_fz_offline_expanded_cargohold_rifter exct_hel
  exct_nidhoggur fighters_mwd_nidhoggur skills0_hel skills0_nidhoggur skills2_hel skills2_nidhoggur skills4_hel
  skills4_nidhoggur` (mostly warp_scramble_status, +drone_dps / scan_resolution / max_velocity).
- ext: both engines pass fleet.buffs 12/12 and overrides 6/6; mining, outgoing, drone_ehp, bombing and heat are not
  implemented by either (0/98, proposed fields).
- effects: failure classes per engine in `results-1.10/effects/failure-classes.txt`. F's largest:
  `moduleRepairRate` on subsystems/modules (150 cases), `isBlackOpsJump{Conduit,Portal}Passenger` on subsystems (139),
  `ship.conduitJumpPassengerCount` 30 vs Pyfa 130 (91), no `attributes.fighters` dump (38), then 5 or fewer each
  (gateScrambleStatus, miningScannerUpgrade, drone miningDroneAmountPercent / shieldCapacity, structure armor HP and
  scan resolution rigs, missile damage with a launcher-speed effect, triage drone damage, breacher pod resistance).
- Per-case JSON: `results-1.10/{core,effects,ext}/`.

## License

Runner, metrics and corpus: MIT. `oracle/` is GPL-3.0-or-later (imports Pyfa). EVE Online data © CCP hf.
