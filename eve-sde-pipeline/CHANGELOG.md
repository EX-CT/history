# CHANGELOG

Dataset `format_version` stays **1**: all changes below only add data, and the eve-dogma-rs loader ignores keys it
doesn't know. `dataset_revision` counts content revisions of the pipeline output. For revision > 1, files and
tags carry a suffix (`dataset-<build>-r<rev>.json.gz`, release `sde-<build>-r<rev>`), so published files are never
overwritten.

## Unreleased
- Docs only, no dataset change: `docs/pyfa-data-drift.{md,json}` records the known differences between Pyfa's
  `eve.db` (client 3532181) and the dataset, with eve's rulings. Paladin/Golem agility and remote capacitor impedance
  are expected differences. For T3C maxSubSystems the decision is to keep CCP's 5, with no patch. Added
  `tools/pyfa_drift.py` (re-check tool) and `tests/test_pyfa_drift.py`.

## Revision 5 (pipeline 0.5.0, 2026-10-03)
- New release asset `presets.json` (fitting presets from the SDE, generated in CI by `tools/make_presets.py`, merged
  from variant G's `presets` branch). It holds damage profiles (generic / per ammo / per NPC faction and context),
  target profiles (generic / NPC faction × hull), NPC damage types, implant sets, character skill presets and search
  aliases. Licences: data under CCP's third-party licence (`LICENSE.EVE`); rules and hand-written tables under MIT.
  It contains no Pyfa data. See `presets/README.md`.
- Pyfa's built-in damage patterns and target profiles (LGPL, from the eos headers) and jargon (GPL-3.0) are published
  only as the separately named asset `presets-pyfa-LGPL-GPL.json`. That file is extracted as data literals with
  per-section licence and commit provenance. It is not part of the default asset set.
- Review fix: implant sets now come only from real set-bonus attributes, so 51 sets became 47. The per-slot
  `implantSetHackingVirusCoherenceModifier` and the `...OmegaSetBonusFAKE` display attribute had produced bogus
  partial "Wedge" sets. `wedge.low-grade` / `wedge.mid-grade` now name the real Omega set.
- Dataset content is unchanged vs r4 apart from `dataset_revision` and `generator`. The release is
  `sde-3569502-r5`, file `dataset-3569502-r5.json.gz`. Earlier files are unchanged.

## Revision 4 (pipeline 0.4.0, 2026-10-03)
- Promoted the three reviewed patches from `patches/proposed/` to `patches/` (applied by default). Engine owner A
  approved all three (eve-dogma-rs `docs/review-sde-proposed-patches.md`):
  - `0101-aoe-burst-projectors`: modifiers for doomsdayAOEWeb/Paint/Damp/Track and
    structureModuleEffectWeaponDisruption. Engine notes: the burst effects have no `range_attr`, so use range factor 1
    (as Pyfa does). The Standup WD keeps range 54 / falloff 2044. `disallowOffensiveModifiers` still blocks all of them.
  - `0102-incursion-system-effects`: modifiers for OffensiveDefensiveReduction (effect 4728). The effect now carries
    a new key, `"stacking_exempt": true`, because Pyfa applies incursion effects **without stacking penalty**.
    Engines must not stacking-penalise modifiers from effects with this flag. The key is additive; loaders that
    ignore unknown keys still work, but they will stacking-penalise these modifiers.
  - `0103-breacher-pod-damage-control`: the moduleBonusBreacherPodDamageControl ship modifier.
- `dataset_revision` 4, release `sde-3569502-r4`, file `dataset-3569502-r4.json.gz`. Earlier files are unchanged.
- Changed sections vs r3: `effects` (7 effects gain `mods`; 4728 also gains `stacking_exempt`), `patches`,
  `dataset_revision`, `generator`. Everything else is byte-identical.
- Verified: engine A (eve-dogma-rs) gives identical output on all 326 bench 1.8.0 cases with r3 and r4, because A
  handles these effects engine-side.
- CI: the coverage job clones the public EX-CT/eve-dogma-rs and Pyfa master on every run to refresh
  `tools/engine-effect-names.json`. The committed list is kept as a fallback.

## Revision 3 (pipeline 0.3.0, 2026-10-03)
- `environment.effect_beacons[*].dbuffs`: the warfare buffs `{buffID: value}` that each environment beacon emits
  (abyssal weather, clouds, …). Engines can apply them the way they apply fleet command bursts.
- Proposed patches (`patches/proposed/`, opt-in with `--with-proposed`, not in releases) for the Pyfa effects
  that have no modifierInfo.
- `sdepipe diff` (Markdown + JSON, with an optional CCP `changes/<build>.jsonl` summary), and `sdepipe names`.
- CI: releases `sde-<build>-r<rev>` with CHANGELOG-<build>.md, diff JSON, Pyfa coverage report, manifest.
- Verified: with r1 and r3, engine A (eve-dogma-rs) and variant K give identical output on all 297 bench cases.

## Revision 2 (pipeline 0.2.0, 2026-10-03; local only, never released)
- New top-level sections:
  - `market_groups`, `meta_groups`, `units`
  - `traits` (ship bonus text: role/misc/per-skill, en + zh)
  - `required_skills`, `clone_grades`
  - `environment` (wormhole classes, systems with a WH class or effect beacon, effect beacons classified by kind,
    system-wide effects, type lists)
  - `names_i18n.zh` for groups/categories/market groups/meta groups/attributes/units
  - `dataset_revision`
- Every section that existed in r1 is byte-identical to r1.

## Revision 1 (pipeline 0.1.0)
- First dataset: types/groups/categories/attributes/effects (compressed modifierInfo), dbuffs, mutaplasmids,
  fighter abilities, zh type names. Release `sde-3569502`.
