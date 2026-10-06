# PROGRESS (eve-sde-pipeline)

## Done
- `sdepipe latest|download|build`, deterministic gzip JSON dataset v1, invariants validator, unit tests.
- GitHub Actions workflow (`.github/workflows/sde.yml`): every 6 h, release `sde-<build>` if new.
- Built locally for TQ build 3569502: 10 745 types, 3 422 effects, 2 871 attrs, 276 dbuffs, 417 mutaplasmids;
  7.27 MB JSON / 0.70 MB gz; ~2.7 s.

## Next
- Engines: apply `environment.effect_beacons[*].dbuffs` and review `patches/proposed/` (promote to `patches/`).
- Patches for Pyfa custom effects (system beacons), damage/target profile presets, implant-set metadata,
  jargon/search aliases, old-name conversions.
- Optional binary snapshot (postcard) for faster engine load.

## State 2026-10-03 03:51 (Asia/Shanghai) — paused
- Release `sde-3569502` exists (dataset + manifest + LICENSE.EVE); workflow run 37056544532 succeeded (skip path).
- Reviewed eve-dogma-rs loader: requires `format_version == 1`, ignores unknown keys → new sections can be
  added additively without a version bump. Patches that add `mods` change engine parity; verify against the
  oracle before adding.
- Planned (not started): marketGroups/metaGroups/typeBonus/icons/units/required skills/system effects sections,
  Pyfa custom-effect inventory, diff report, CBOR/xz variants, fixture-based CI tests, `data` branch pointer.
- Work paused: user switched workers to the dogma-engine architecture bake-off (eve-dogma-lab).

## State 2026-10-03 06:10 (Asia/Shanghai): production pipeline
- Revision 3 released: https://github.com/EX-CT/eve-sde-pipeline/releases/tag/sde-3569502-r3 (run 37069656363,
  success; the CI dataset is byte-identical to the local build, sha256 500b0038…).
- Added market/meta groups, units, traits, required skills, clone grades, environment, zh names (see CHANGELOG.md).
- `sdepipe diff` tested on real builds 3552227/3561556 → 3569502. There are no engine-relevant changes: the CCP
  changes touched NPC types only, and those are filtered out.
- Pyfa coverage: 2270 sde-modifiers, 70 engine-special, 6 engine-generic (bursts), 8 data-provided (weather/cloud
  beacons), 10 gaps → 3 proposed patches (8 effects) + 3 engine-only (powerBooster, AOE ECM, AOE neut),
  18 Pyfa no-ops, 4 Pyfa custom, 15 not in SDE.
- Engines A and K give the same output on all 297 bench cases with r1 and r3.
- Not included: icons/graphics, damage/target profile presets, implant-set metadata, search aliases.
