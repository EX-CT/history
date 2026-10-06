# Fitting presets (`presets/`)

Static preset data that fitting tools bundle but CCP's SDE does not ship as such: damage profiles, target profiles,
NPC damage types, implant sets, character skill presets, search aliases. Generated, not hand-copied:

```bash
python tools/make_presets.py --sde SDE_JSONL_DIR [--pyfa PYFA_CHECKOUT] --out presets
python -m unittest tests.test_presets
```

Pure stdlib and deterministic: the same inputs give byte-identical files. The generated files are **not committed**
(LICENSING.md: generated data ships as release assets). CI builds them for every release: `presets.json` and, as a
separately labelled asset, `presets-pyfa-LGPL-GPL.json`. Download them with
`gh release download -R EX-CT/eve-sde-pipeline -p 'presets*.json'`. The counts below are from SDE build 3569502
(2026-10-02) and Pyfa commit 1d9f72b.

## Two files, two licence regimes

| file | content | licence |
|---|---|---|
| `presets.json` | derived from the SDE by the rules in `tools/make_presets.py`, plus EX-CT hand-written tables (classification keywords, alias list, generic profiles) | data: CCP third-party developer licence (`LICENSE.EVE`); rules and hand-written tables: MIT (`LICENSE`) |
| `presets-pyfa.json` | Pyfa's built-in damage patterns and target profiles, and its jargon (search abbreviation) table, extracted as **data only** (`ast` literal evaluation of the `BUILTINS` tables; a minimal YAML list reader) | damage patterns / target profiles: **LGPL-2.1-or-later** (eos file headers); jargon: **GPL-3.0-or-later** (Pyfa LICENSE) |

`presets.json` contains no Pyfa data. `presets-pyfa.json` is optional, so keep it separate from the MIT/CCP outputs
and follow LGPL/GPL when you redistribute it. No Pyfa code is used or copied: the generator only reads Pyfa's data
literals. Every section carries a `provenance` object with: source, SDE build and files, method, generator, and
`license`.

Licence note: the eos headers say "GNU Lesser General Public License ... version 2 of the License, or (at your
option) any later version". LGPL version 2 was the *Library* GPL 2.0, so the literal reading is LGPL-2.0-or-later.
We label it `LGPL-2.1-or-later`, which that grant permits. In releases the file ships as a separately named asset
(`presets-pyfa-LGPL-GPL.json`), never inside the CCP/MIT default set.

## Sections of `presets.json` (SDE 3569502)

| section | count | what / how |
|---|---|---|
| `damage_profiles.generic` | 5 | Uniform, and pure EM / Thermal / Kinetic / Explosive (definition) |
| `damage_profiles.ammo` | 823 | every published charge (category 8) with damage. Base damage and ratio, no skills or launcher bonuses |
| `damage_profiles.npc` | 69 | per NPC faction (19) and per faction × context (asteroid belt, deadspace, mission, FW, incursion, …). `ratio` is weighted by DPS; `ratio_type_mean` is the mean of the per-type ratios |
| `target_profiles.generic` | 5 | ideal target, and uniform 25 / 50 / 75 / 90 % |
| `target_profiles.npc` | 106 | median over the NPC types of a (faction, hull class): resists per layer and HP-weighted, signature radius, max velocity, radius, HP |
| `npc_damage_types.factions` | 19 | damage share per faction, primary damage type, and secondary (share > 5 %) |
| `npc_damage_types.types` | 5185 | every armed NPC type: DPS by damage type, share, primary types |
| `implant_sets` | 47 | published implants carrying an `implantSet*` set-bonus attribute (multiplier; per-slot `...Modifier` and `...FAKE` display attributes excluded), grouped by attribute and Low/Mid/High grade. Members with slot (`implantness`) and multiplier; `complete` means all 6 slots are present |
| `character_skill_presets` | 10 | All 0 … All 5 (every published skill, 512) and the SDE clone grades (alpha clone caps) |
| `search_aliases` | 108 | EX-CT abbreviation table (mwd, scram, lse, bcs, haml, rf, …) resolved to type ids by whole-word match on English names. 6 aliases with no match are listed in `dropped_no_match` |

NPC rules: NPCs are SDE category 11. The faction comes from `factionID` when the type has one, otherwise from
keywords in the group name. Context comes from the group-name prefix and hull class from a word in the group name.
A weapon counts only when the type has the matching weapon effect: turret `targetAttack` / `projectileFired` /
`targetDisintegratorAttack`, or missile `missileLaunchingForEntity`. Many NPCs carry leftover weapon attributes
with no effect. Turret DPS = damage × `damageMultiplier` / `speed`. Missile DPS = the damage of the
`entityMissileTypeID` charge × `missileDamageMultiplier` / `missileLaunchDuration`.

## Sections of `presets-pyfa.json` (Pyfa 1d9f72b)

| section | count | source |
|---|---|---|
| `damage_patterns` | 118 | `eos/saveddata/damagePattern.py` `BUILTINS` (name, amounts, ratio) |
| `target_profiles` | 195 | `eos/saveddata/targetProfile.py` `BUILTINS` (resists, optional velocity / signature / radius / hp) |
| `jargon` | 309 | `service/jargon/defaults.yaml` (key → patterns) |

## Gaps / known limits

- NPC profiles are not weighted by spawn frequency or site composition, because the SDE has no spawn tables. Pyfa's
  curated mission and abyssal profiles, e.g. Abyssal per weather/tier, cannot be derived from the SDE. They are only
  in `presets-pyfa.json`.
- Abyssal, Irregular, Homefront and similar NPC groups without a faction keyword or factionID are left out of the
  faction aggregates. They are still in `npc_damage_types.types` with `faction: null`.
- NPC DPS uses base attributes. It ignores NPC behaviour (orbit range, target switching), and it ignores fighters,
  drones and EWAR, plus anything not modelled as entity turret or missile attributes.
- The search aliases are English only and hand-curated (108). Pyfa's 309-entry jargon is available only under GPL in
  `presets-pyfa.json`.
- Not included: Pyfa market overrides (force-published or regrouped items), price data, and saved user fits and
  characters. ESI was not needed: everything above comes from the SDE.
