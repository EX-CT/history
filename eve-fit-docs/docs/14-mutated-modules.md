# 14 — Mutated modules (mutaplasmids) and implant/booster combinations: plan

**中文摘要**：本文是变异装备（突变质体 / 深渊装备、变异无人机）以及植入体/增效剂组合的计划。

- **请求格式**：沿用 1.x 合约中的 `mutation {base_type_id, mutaplasmid_type_id, attributes}`。属性值为绝对值。这正是 Pyfa
  导入 EFT `[Mutated]` 写法后得到的结果。
- **语义（Pyfa 规则）**：
  - 变异属性从基础物品的数值开始；
  - 范围按四舍五入到 3 位小数的倍数校验，超出范围则截断；基础值为 0 时结果为 0；
  - 突变质体未列出的属性一律忽略；
  - 植入体/增效剂按槽位"先到先得"，后来者完全无效；
  - 效果 2791 的技能过滤以 Pyfa 为准（导弹发射器操作，而非 SDE 中的 3452）。
- **测试集**：位于 eve-dogma-bench 分支 `mutated-suite`（`mutated/`）。共 93 个用例、6184 个数值，另有 EFT 导出 93 条、
  导入 99 条（含 8 条手写边界文本）。期望值全部由 Pyfa 作为黑盒 oracle 生成，测试集中不含任何 Pyfa 代码。
- **现状**：参考实现 Variant I（349c6fd）全部通过，且 1.8.0 保持 326/326、输出逐字节一致。A–K 普遍缺少槽位规则和
  校验后的 EFT 导出数值。
- 第 4 节列出各引擎需要的改动，第 5 节给出计分方法。

Status: **DRAFT**, 2026-10-03 (09:20 CST; §3/§5 updated ~10:00 CST).

- **Contract:** `CONTRACT-MUTATED.md` draft 0.1 on the `EX-CT/eve-dogma-bench` branch **`mutated-suite`**, under
  `mutated/`. It is additive to bench contract 1.4.x.
- **Relation to scoring:** the suite is not part of the frozen 1.8.0 scoring.
- **Reference implementation:** Variant I `variant-i` @ 349c6fd.

## 1. What Pyfa does (black-box observations and the semantics they pin down)

| topic | Pyfa behaviour | where it shows up |
|---|---|---|
| Mutated item | Built as `Module(resultingItem, baseItem, mutaplasmid)`. The resulting (abyssal) type's attributes are laid over the base type's: `{**base, **resulting}` | every `mm_*` case |
| Start value | A mutated attribute starts from the **base** type's value, even when the resulting type lists its own value | `empty_attrs_*`, `partial_*` |
| Validation | `v/base` is checked against `[round(min,3), round(max,3)]`. Out of range, the value is clamped to `[lo·base, hi·base]`; base 0 gives 0 | `mwd_decayed_over/under`, `edge_*_over` |
| Foreign attributes | Attributes the mutaplasmid does not list are never applied | `foreign_attr_*` |
| Override precedence | A mutated value beats an `overrides[]` entry for the same attribute (`mutator > override > base`) | not tested in 0.1 |
| Implant/booster slots | `HandledImplantList`/`HandledBoosterList.append`: an entry whose `implantness`/`boosterness` slot is taken is dropped. **The first entry wins**, and the later one has no effects and no side effects | `slot_*`, `combo_two_boosters_*` |
| Effect 2791 | `boosterMissileExplosionCloudPenaltyFixed` (Exile/Mindflood side effect): the SDE filters on skill 3452 (Acceleration Control), but Pyfa's handler uses Missile Launcher Operation, so missile explosion radius grows | `combo_nomad_ab_mwd_exct_damnation` |
| EFT export | The base name is written with ` [N]` after the charge and `/offline`. The `[N]` blocks list sorted attribute names with `floatUnerr` of the **validated** values. Drones are sorted by `DRONE_ORDER`, then unmutated before mutated, then by `fullName` = `<mutaplasmid short name> <base>`. Dropped implants and boosters are not written | `expected_extra/eft_export.jsonl` |
| EFT import | The item line's base wins over the block header. A missing block gives a plain item. Unknown or foreign attribute names are dropped. A missing attribute line means base values. A shared reference mutates both modules. `xQ [N]` mutates the whole drone stack | `mutated/eft/eftedge_*` |

## 2. Request format

```jsonc
"modules": [{"type_id": 47408, "slot": "mid", "state": "active",
             "mutation": {"base_type_id": 12076, "mutaplasmid_type_id": 47742,
                          "attributes": {"6": 172.8, "20": 515.1, "30": 160.05, "50": 49.6, "554": 446.5}}}],
"drones":  [{"type_id": 60479, "quantity": 3, "active": 3,
             "mutation": {"base_type_id": 2185, "mutaplasmid_type_id": 60473, "attributes": {"64": 2.304}}}],
"implants": [19540, 33947],                                  // order matters: first entry per slot wins
"boosters": [{"type_id": 15466, "side_effects": [2736, 2737, 2741, 2746]}]
```

This is the existing 1.x shape. It maps one-to-one to the EFT notation:

| EFT | request field |
|---|---|
| item line `Base Name [N]` | `base_type_id` |
| block line 2, the mutaplasmid name | `mutaplasmid_type_id` |
| `attrName value, …` | `attributes`, by attribute id |
| `type_id` | the mutaplasmid's resulting type (dataset `mutaplasmids[].mapping`) |

No new fields are needed.

## 3. The suite (`mutated/` on `mutated-suite`)

- **Cases:** 93 FitRequests, generated deterministically by `mutated/tools/gen_cases.py` (MIT) from main-corpus fits
  and the dataset's mutaplasmid ranges:

  | family | cases | what it covers |
  |---|---|---|
  | `mm_*` | 26 | one roll per mutable module group |
  | `mwd_*` | 10 | every mutaplasmid tier, plus min/max/over/under rolls |
  | `edge_*` | 9 | — |
  | `partial_*`, `empty_attrs_*`, `foreign_attr_*` | 6 | — |
  | `multi_*` | 4 | — |
  | `state_*` | 3 | — |
  | `drone_*` | 6 | — |
  | `combo_*` | 24 | implant sets, hardwirings, boosters with side effects, mostly combined with a mutated module |
  | `slot_*` | 5 | — |

- **Expected values:** produced by `mutated/tools/make_expected.py`, which runs `oracle/pyfa_oracle.py` as a separate
  process. They use the same metrics and tolerances as the main corpus: 6,184 values. Known SDE-vs-Pyfa divergences
  of the source fit stay excluded.
- **EFT:**
  - `expected_extra/eft_export.jsonl` holds Pyfa's `exportEft` output (93 rows);
  - `expected_extra/eft_import.jsonl` holds Pyfa's `importEft` results (99 rows): 91 exports plus 8 hand-written edge
    texts;
  - two exports are excluded: `combo_mindflood_ham_se_exct_ishtar` and `state_web_overheated_exct_tengu`. The cause
    is now known (CONTRACT-MUTATED §6.1). Pyfa's `importEft` drops every module that fails `Module.fits()`. Both
    source corpus fits are overfilled: `exct_ishtar` has 5 mid modules on 4 mid slots, and `exct_tengu` has 6 mid
    modules where Pyfa gives that subsystem set 4 at import. The last lines of the rack are dropped, and the mutated
    module is last. The plain, unmutated MWD line is dropped the same way, so this is not a mutation rule.
- **Licensing:** the oracle scripts are GPL-3.0-or-later test tools that import an unmodified Pyfa checkout. The
  generator, scorers, cases and expected files contain no Pyfa code.

## 4. What each engine needs to change

First scores are in `mutated/RESULTS.md`. They come from the binaries already built in the bench's `work/` clones, so
some are older than the branch heads.

| variant | stats | EFT export | EFT import | changes needed |
|---|---|---|---|---|
| I (reference, 349c6fd) | 93/93 | 93/93 | 99/99 | none |
| A eve-dogma-rs | 86/93 | 73/93 | 96/99 | the full list below (I started from A's semantics) |
| B data-oriented Rust | 84/93 | 73/93 | 96/99 | as A, plus `mm_ancillary_shield_booster_*` and `mm_propulsion_module_exct_crucifier` (cause not yet analysed) |
| C Go, G Python, J C++ | 86/93 | 73/93 | 96/99 | as A |
| D TypeScript | 86/93 | 83/93 | 96/99 | as A; EFT export is partly done |
| E Pyfa-faithful port | 87/93 | 85/93 | 0/99 | slot rule; EFT export of validated values; `eft_parse` is missing (it has the 2791 override) |
| F codegen | 86/93 | 85/93 | 96/99 | as A; EFT export is partly done |
| H ECS | 86/93 | 81/93 | 98/99 | as A |
| K Kotlin/C# | 86/93 | 73/93 | 93/99 | as A, plus three more EFT import rows |

The full list, roughly in order of score impact:

1. **Implant/booster slot rule (§3.1).** Process `implants[]` and `boosters[]` in order and skip any entry whose
   `implantness`/`boosterness` value is already taken. Every variant fails this today: 6 stats cases.
2. **Effect 2791 override (§3.3).** Add it to the engine's Pyfa-handler override table: change the charge skill
   filter from 3452 to 3319. The same overrides should go into the SDE pipeline's `patches`, so that every engine
   gets it from the dataset. The dataset is frozen for round 1, so this is done per engine for now.
3. **Mutation validation (§2.4).** Use one shared function, `mutated_values(base, mutaplasmid, given)`. It iterates
   over the **mutaplasmid's** attribute list (not the given keys), starts from the base value, and validates against
   the 3-decimal-rounded range, with base 0 giving 0. Use it both when building the item and for EFT export. Engines
   that apply the given keys directly also apply foreign attributes, and fill omitted ones from the resulting type
   instead of the base. No 0.1 stats case shows a numeric difference there, but the EFT export does.
4. **EFT export.** Print the validated values. Order drones by Pyfa `fullName`: the short-name rules keep grade only,
   or grade + kind for drone mutaplasmids, and write "Glorified" as "Gl.". Drop slot-conflicting implants and
   boosters.
5. **EFT import.**
   - Strip ` [N]` before `/offline`.
   - Take the base from the item line and ignore the block header's name.
   - Treat an undefined reference as a plain item, not an error.
   - Clamping may be done at parse time or left to calc; the checker compares effective values.
6. **Regression.** The 1.8.0 corpus must stay at 326/326 with byte-identical output. Variant I's port kept the
   output identical; its only corpus mutation case, `esf_mutations`, is in range.

For variants that share A's semantics this is a small change. The Variant I port (349c6fd) was 140 lines added and
26 removed, in the data, spec and EFT code.

## 5. Scoring

| part | tool | unit |
|---|---|---|
| stats | `python3 mutated/run_mutated.py --name X --cmd … --batch-cmd …` | cases fully correct /93 and values /6,184 (main-corpus tolerances) |
| EFT export | `python3 mutated/tools/check_eft.py --rpc-cmd … --dataset D` | byte-identical texts /93 |
| EFT import | the same tool | equal fits /99 |
| regression | `run.py` on the 1.8.0 corpus | must stay 326/326, byte-identical |

The **EFT import** check compares the ship, the mutated modules in order with their effective values, the drones,
and the implants and boosters after the slot rule. Unmutated-module import fidelity belongs to the formats suite
(docs/11).

**Pass rules** (CONTRACT-MUTATED §5.1):

| part | a row passes when |
|---|---|
| stats value | `\|got - want\| <= max(1e-3, 1e-4·\|want\|)` (main-corpus rule); a case passes when all its values pass and the engine reports no error |
| EFT export | the text is byte-identical (the T3C `[Empty Subsystem slot]` exception applies) |
| EFT import | the compared fields are equal; effective mutation values within relative 1e-6 |

**Gate:** 326/326 on the 1.8.0 corpus and no engine errors on the suite.

**Proposed weighting** (open, to be settled when the suite freezes):

| part | weight |
|---|---|
| stats cases | 60 % |
| EFT export | 20 % |
| EFT import | 20 % |

Performance is not scored. The suite is small and dominated by process start-up.

**Open questions for 0.2:**

- import drops modules that do not fit, in line order. Either make this a rule with dedicated rows (it may belong
  in the formats suite), or keep overfilled source fits out of the generator;
- an `overrides[]` × mutation case;
- mutaplasmids from another module family, where Pyfa raises an error;
- name-keyed `attributes` in requests (EFT style);
- Naiyon's Modified Stasis Webifier (15419), the one base whose effects the resulting type lacks.
