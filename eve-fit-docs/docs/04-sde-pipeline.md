# 04 — SDE pipeline

> 中文：数据管线独立成仓库 `eve-sde-pipeline`。GitHub Actions 每天检查 CCP 官方 SDE 的 build 号，有新版本就下载 JSONL、
> 转换成引擎专用的紧凑数据集（只保留配船相关的类型/属性/效果），发布为 GitHub Release（`sde-<build>`），引擎按 build 号引用。

## 1. How the references source data

| Project | Source | Tooling | Output |
|---|---|---|---|
| Pyfa | Client FSD (via **Phobos**, `pyfa-org/Phobos`), committed as JSON in `staticdata/fsd_built`, `fsd_lite`, `phobos/` | `db_update.py` → SQLite `eve.db` (+ custom effects/attrs, implant sets, replacements) | ~225 MB JSON in repo; **no `modifierInfo`** (Pyfa uses hand-written effects) |
| EVEShipFit | Official SDE (YAML) or client FSD via `.pyd` loaders (Windows/Py2) | `EVEShipFit/data` `convert/` + `patches/*.yaml` (synthetic attrs/effects) | protobuf / flatbuffers `sde.dat` |
| **EXCT (us)** | **Official CCP SDE, JSONL** (2025 rework) | `eve-sde-pipeline` (Python stdlib, deterministic) | `dataset-<build>.json.gz` + manifest, GitHub Release |

## 2. CCP SDE (current, verified 2026-10-03)

* Latest pointer: `https://developers.eveonline.com/static-data/tranquility/latest.jsonl` →
  `{"_key":"sde","buildNumber":3569502,"releaseDate":"2026-10-02T11:08:57Z"}`.
* Archive: `https://developers.eveonline.com/static-data/tranquility/eve-online-static-data-<build>-jsonl.zip` (~99 MB).
  Short-hand: `.../static-data/eve-online-static-data-latest-jsonl.zip` (302 redirect).
* Changes: `.../tranquility/changes/<build>.jsonl`; schema changelog `.../tranquility/schema-changelog.yaml`.
* JSONL: one object per line; integer map keys → `_key` (and `_value` for scalars).
* Files we use: `types`, `groups`, `categories`, `marketGroups`, `metaGroups`, `dogmaAttributes`, `dogmaEffects`
  (with `modifierInfo`: 3 205 of 3 422 effects), `typeDogma` (attrs + effects with `isDefault`), `dbuffCollections`
  (warfare buffs), `dynamicItemAttributes` (mutaplasmids: `attributeIDs{min,max}`, `inputOutputMapping`),
  `fighterAbilities`, `fighterAbilitiesByType`, `typeBonus` (traits text), `dogmaUnits`, `cloneGrades` (alpha
  limits), `skinLicenses` ➖, map files only for wormhole class/system effects (`mapSolarSystems`,
  `systemWideEffects`, `mapSecondarySuns`).
* Observed modifier stats: funcs ItemModifier 1800, LocationRequiredSkillModifier 1610,
  OwnerRequiredSkillModifier 923, LocationGroupModifier 798, LocationModifier 29, EffectStopper 10; domains shipID 3595,
  charID 1065, itemID 221, structureID 177, otherID 55, targetID 47, target 10.
* Operation codes: -1 PreAssign, 0 PreMul, 1 PreDiv, 2 ModAdd, 3 ModSub, 4 PostMul, 5 PostDiv, 6 PostPercent,
  7 PostAssign, 9 skill-points→level (ignore).

## 3. Engine dataset format (v1)

`dataset.json.gz` — UTF-8 JSON, keys sorted, deterministic (same SDE → byte-identical output → stable sha256):

```jsonc
{
  "format": "exct-eve-dataset", "format_version": 1,
  "sde": {"build": 3569502, "release_date": "2026-10-02T11:08:57Z"},
  "categories": {"6": {"name": "Ship"}},
  "groups": {"25": {"name": "Frigate", "category": 6}},
  "attributes": {"9": {"name": "hp", "default": 0, "stackable": true, "high_is_good": true, "min_attr": null, "max_attr": null, "unit": 1, "display": "Structure Hitpoints"}},
  "effects": {"11": {"name": "loPower", "category": 0, "duration_attr": null, "discharge_attr": null, "range_attr": null, "falloff_attr": null, "tracking_attr": null, "resistance_attr": null, "fitting_usage_chance_attr": null, "is_offensive": false, "is_assistance": false,
                     "mods": [[func, domain, modified_attr, modifying_attr, op, group_or_skill]]}},
  "types": {"587": {"name": "Rifter", "group": 25, "category": 6, "mass": 1067000, "volume": 27289, "capacity": 140, "radius": 31, "published": true, "market_group": 391, "meta_group": null,
                    "attrs": {"9": 350.0}, "effects": [[effectID, isDefault]]}},
  "dbuffs": {"10": {"aggregate": "max", "op": "PostPercent", "item": [attr], "location": [attr], "location_group": [[attr, group]], "location_skill": [[attr, skill]]}},
  "mutaplasmids": {"47408": {"attrs": {"20": [0.8, 1.2]}, "mapping": [{"inputs": [...], "output": 47732}]}},
  "fighter_abilities": {...},
  "names": {"zh": {"587": "裂谷级"}}
}
```

Filtering: only categories relevant to fitting — Ship 6, Module 7, Charge 8, Skill 16, Drone 18, Implant 20,
Celestial 2 (effect beacons only), Subsystem 32, Fighter 87, Structure 65, Structure Module 66, Deployable 22 (some),
plus Mutaplasmid group types; removes ~85 % of `types.jsonl` (153 MB → ~6–10 MB uncompressed, ~1.5 MB gz).

Encoded `mods` tuple keeps the dataset small and quick to parse. func codes: 0 Item, 1 Location, 2 LocationGroup,
3 LocationRequiredSkill, 4 OwnerRequiredSkill, 5 EffectStopper. Domain codes: 0 itemID, 1 shipID, 2 charID,
3 otherID, 4 structureID, 5 targetID, 6 target.

**Patches** (`patches/*.json`) are applied after conversion and are themselves versioned in git: e.g. fixing
missing `mass` attribute from type field, adding pyfa-equivalent custom effects (e.g. system-effect beacons
missing modifiers). Each patch has an ID and rationale; dataset manifest lists applied patches.

## 4. GitHub Actions (`eve-sde-pipeline/.github/workflows/sde.yml`)

1. `schedule: cron '17 */6 * * *'` + `workflow_dispatch`.
2. Read `latest.jsonl`; if a release `sde-<build>` already exists → exit.
3. Download zip, verify size, unzip only needed files.
4. `python -m sdepipe build --sde <dir> --out dist/` → `dataset-<build>.json.gz`, `manifest.json`
   (build, sha256, counts, patches), `CHANGELOG-<build>.md` (types/attrs/effects added/removed/changed vs previous).
5. Run `sdepipe validate` (schema & invariants: every effect attr referenced exists, etc.).
6. Create GitHub Release `sde-<build>` with assets; update `latest.json` on the `data` branch (tiny pointer).

Consumers: `eve-dogma-rs` downloads by build (`eve-dogma dataset fetch --build latest`), caches in
`~/.cache/exct-eve/`; can also compile to a binary snapshot for faster load.
