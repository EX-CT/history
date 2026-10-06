# 11 — Import / export format parity with Pyfa

**中文摘要**：本文列出 Pyfa `service/port/` 的全部导入/导出格式（EFT、EFT 配置文件、DNA/聊天链接、XML、ESI JSON、
Multibuy、舰船属性文本、变异装备文本、附加列表、自动识别、EFS），说明用 Pyfa 自身代码生成的往返测试集
（eve-dogma-bench 分支 `formats-suite`：3260 条导出、1304 条往返导入、16 条边界用例），并给出 Pyfa 的实际行为
与 variant F 的实现/未实现对照表。第 3 轮（导入/导出格式）以 FORMATS 合约 0.1 草案计分（第 5 节）：
共 4793 行（4779 行计分，四组各占 25%；Pyfa 自身崩溃、多舰合并粘贴、旧物品名、依赖主基准已排除属性的 3 行舰船属性文本等
14 行仅报告），以 Pyfa 实际行为为准；variant F（bc84e2b）得分 98.46%（4773/4779），graphs-g4（22dbeb7）与
variant-f-formats（af1c04b）100%（4779/4779），原生与 WASM 相同。
草案尚未冻结，等第 1 轮归档后再定稿。

Status: 2026-10-03, Pyfa client db 3532181, bench cases 1.8.0 (326 fits). Suite: `EX-CT/eve-dogma-bench`
branch **`formats-suite`** (`formats/`, `oracle/pyfa_formats.py`, `tools/make_formats.py`, `tools/check_formats.py`).
The suite is not part of the frozen 1.8.0 scoring. **Round 3** scores it as the FORMATS contract 0.1 draft
(`formats/CONTRACT-FORMATS.md`, `tools/evaluate_formats.py`). Section 5 has the scoring rules. The draft is not
frozen until the round-1 archive.

## 1. Pyfa's formats (`service/port/`)

| # | Format | Pyfa entry points | Direction | Notes on Pyfa behaviour (from the generated cases) |
|---|---|---|---|---|
| F1 | **EFT text** | `eft.py exportEft`, `importEft` | export + import | Export options: implants, mutations, loaded charges, boosters, cargo (each switchable). It writes `[Empty X slot]` lines and `/offline` (import also accepts `/OFFLINE`). Mutated modules get a `[n]` reference plus a trailing block (base type, mutaplasmid, `attr value, …`). T3D: **no mode line is written**, and on import a mode line is not read: the fit gets the hull's *first* mode. |
| F1a | EFT, multi-fit paste | `importEft` (via `importAuto`) | import | Two `[ship, name]` blocks in one paste are **merged into one fit** (the first header wins). The second header is treated as a stub line. |
| F1b | **EFT config file** (`<Ship>.cfg`) | `eft.py importEftCfg` | import (multi-fit) | The ship comes from the file stem, and each `[name]` header starts a fit. It reads `Drones_Active=` / `Drones_Inactive=` (active count), `Implant_*=`, `Booster_*=`, `Cargohold=` and `Description=`, and `module,charge` with no space. |
| F2 | **DNA** | `dna.py exportDna`, `importDna` | export + import | `ship:sub;1…:mod;n…:drone;n:fighter;n:charge;n::`. Subsystems are sorted by `subSystemSlot`. Modules are grouped by type, and loaded charges are summed (`numCharges`, scripts count 1) and appended with cargo charges. Implants and boosters are never exported, and module state is lost. Import: charges go to **cargo** (not loaded), every module is set to its highest allowed state (`activeStateLimit`), and the name is `"<Ship> - DNA Imported"`. An unknown type id aborts the import. |
| F2a | DNA chat link | `exportDna` with FORMATTING, `importAuto` | export + import | `<url=fitting:DNA::>name</url>`. On import the link text becomes the fit name. |
| F2b | DNA alt (`DNA:ship:id*n`) | `importDnaAlt` | import | Same as DNA, with `*` as the amount separator. |
| F3 | **XML** (EVE client fittings) | `xml.py exportXml`, `importXml` | export + import (multi-fit) | It writes `<hardware slot="low slot 0">`, drone bay and cargo `qty`, and mutated `base_type` / `mutaplasmid` / `mutated_attrs`. Loaded charges are exported as cargo, the description is limited to 400 chars and newlines become `<br>`. Import: charges stay in cargo, implants and boosters are not supported, and every `<fitting>` becomes a fit. |
| F4 | **ESI fitting JSON** | `esi.py exportESI`, `importESI` | export + import | The name is cut to 50 chars (47 plus `...`). Flags: low 11+, mid 19+, high 27+, rig 92+, subsystem = `subSystemSlot`, service 164+, cargo 5, drone bay 87, fighter 158. Charges (as an option) go to cargo, and so do implants and boosters. A fit with no items raises an error. Import: items are sorted by flag, unpublished types are skipped, fighters take the **default squadron size**, and a drone sent with the fighter flag is dropped. |
| F5 | **Multibuy** | `multibuy.py exportMultiBuy` | export | The ship line comes first, then items sorted by (category, group, name) with ` xN` when N > 1. Options: loaded charges, cargo, implants, boosters, and price optimisation (needs the market service, not generated). **Mutated modules are omitted.** |
| F6 | **Ship stats text** | `shipstats.py exportFitStats` | export | `name (ship)`, then DPS/volley, EHP plus per-layer resists, reps, and misc (speed, sig, cap, targeting). It uses Pyfa's `formatAmount` (3 significant digits, `k`/`M` suffixes). |
| F7 | Mutated item text | `muta.py parseMutant` (via `importAuto` with an active fit) | import | 3 lines: base type, mutaplasmid, attributes. The result is an item, not a fit. |
| F8 | Additions lists | `eft.py isValid{Drone,Fighter,Implant,Booster,Cargo}Import` | import | `Name xN` lists pasted into an open fit. The result is a list, not a fit. |
| F9 | Format auto-detection | `port.py Port.importAuto` | import | The order is: XML header, then `{` → ESI, then `[...]` plus a file path → EFT config, then `[a, b]` → EFT, then DNA, then DNA link, then `DNA:` alt. After that it tries the dynamic-item ESI link (needs the network), then the mutant text, then the additions lists. |
| F10 | EFS (Eve Fitting Simulator JSON) | `efs.py EfsPort.exportEfs` | export | This needs Pyfa's GUI fit commands and stats tables, so it is not generated. |
| F11 | Killmail / ESI fittings fetch | `service/esi.py` | import | This needs the network and SSO, so it is out of scope for an offline engine. |

## 2. Test suite (EX-CT/eve-dogma-bench `formats-suite`)

`oracle/pyfa_formats.py` loads Pyfa's own `service/port/*.py` **unmodified**. The only stand-ins are for GUI-only
imports: the Market singleton (it uses Pyfa's `conversions` and `ITEMS_FORCEPUBLISHED` read from Pyfa's source),
`service.fit` recalc/fill, and `activeStateLimit` (executed from Pyfa's `helpers.py` source). For every bench case
the oracle builds the fit, exports it in every format, imports each importable export back, and re-exports.
Hand-written edge inputs go through Pyfa's `Port.importAuto`.

| Set | Rows | Content |
|---|---|---|
| Export | **3260** | 326 cases × {eft, eft_min, dna, dna_formatted, esi, esi_min, xml, multibuy, multibuy_min, shipstats}. 2 rows are expected errors (esi_min on an empty fit). |
| Round-trip import | **1304** | 326 × {eft, dna, esi, xml}. The input is Pyfa's export and the expected result is Pyfa's imported fit (FitRequest-shaped). Of the 326 cases, 132 are over-fitted validation cases (more modules than slots or hardpoints), and Pyfa's importers drop the excess modules there. The other 194 are legal fits. |
| Edge | **16** | `/offline` and `/OFFLINE`; mutated blocks; all EFT sections and drone-stack merging; CRLF, an unknown item and a charge on a module that takes none; T3D mode line; T3C subsystems; structure with services; multi-fit EFT paste; `.cfg` multi-fit; XML with 2 fits and a mutation; DNA link, alt and unknown id; ESI with wrong flags; additions list; single mutant. |

Checker: `python3 tools/check_formats.py --rpc "<variant> serve-stdio" --name X`. It sends `format_export` and
`format_import` RPC calls (proposed contract extension), falling back to `eft_export` and `eft_parse`.

### Pyfa's own round-trip stability (194 legal fits)

| Format | Pyfa re-export identical | Import identical to the source fit | What the format loses (count of fits) |
|---|---|---|---|
| EFT | 190/194 | 133/194 | drone active count 48, active→online by `activeStateLimit` 15 (MJD, cloak, WCS, …), T3D mode set to the first 5, invalid charge dropped 3, drone stacks merged 1 |
| DNA | 183/194 | 0/194 | name 193, loaded charges → cargo 121, active counts 47, state 15, subsystem/module order 5, implants and boosters 6, fighters 1 (plus one unknown-type crash) |
| ESI | 181/194 | 52/194 | charges → cargo 121 (cargo 125), active counts 48, state 15, fighter squadron size 6, implants and boosters 6 |
| XML | 185/194 | 54/194 | charges → cargo 121, active counts 48, state 15, implants and boosters 6 |

## 3. Parity table — variant F (`EX-CT/eve-dogma-lab` `variant-f`, commit 02257b7)

Status: ✅ implemented and matching Pyfa · 🟡 implemented with differences · ⬜ not implemented.
F exposes RPC `format_export {fit, name, format, options}` and `format_import {text, format, path?}` (plus the 1.8.0
`eft_export` / `eft_parse`). Scorecard: `variant-f/bench/formats/scorecard.md` in the lab repo.

| Format | Direction | F status | Suite result | Differences vs Pyfa |
|---|---|---|---|---|
| EFT (all options) | export | ✅ | 326/326 | Only the known data divergence: T3 cruisers get `maxSubSystems` 5 in SDE 3569502 and 4 in Pyfa's db, so there is one extra `[Empty Subsystem slot]` (21 cases, accepted by the checker). |
| EFT (options off) | export | ✅ | 326/326 | Same subsystem-slot note. |
| EFT | import (`format_import eft`) | ✅ | 326/326 (legal 194/194) | Pyfa semantics: `activeStateLimit`, drone-stack merge, invalid charges dropped, over-fit dropped, first T3D mode, drones inactive. (The 1.8.0 `eft_parse` keeps its contract behaviour.) |
| EFT config (`.cfg`) | import | ✅ | edge 1/1 | |
| DNA / DNA link / DNA alt | export, import | ✅ | export 326/326 ×2, import 326/326 (legal 194/194) | Includes Pyfa's crash on a mutated drone type (reported as an import error). |
| XML | export, import | ✅ | 326/326, 326/326 (legal 194/194) | |
| ESI JSON | export, import | ✅ | 326/326 ×2, 326/326 (legal 194/194) | Item publicity follows Pyfa's database (Civilian modules public, abyssal/mutated types not). |
| Multibuy | export | ✅ | 326/326 ×2 | Price optimisation not implemented (needs market data; not in the suite). |
| Ship stats text | export | 🟡 | 324/326 | `esf_structure_bonus_1` (known structure-bonus exclusion, also excluded from the main bench) and `esf_items_7` (odd item; Pyfa capacitor 62.8k vs F 312 GJ, a capacitor value the main bench does not score). Uses no spool-up, like Pyfa's copy. |
| Mutant text / additions lists / auto-detect | import | ✅ | edge 16/16 | Additions lists: `[n]` mutation references on drones are not resolved (not in the suite). |
| EFS | export | ⬜ (not in suite) | – | |

Other variants can be scored with the same checker. As of this writing only EFT export and import exist in the
1.8.0 contract.

## 4. Recommendations for the contract (proposed, not yet agreed)

1. Add `format_export {fit, name, format, options}` and `format_import {text, format|auto, path?}` RPC methods.
   Pyfa's option names are in `formats/expected/export.jsonl`.
2. Decide whether `eft_parse` should copy Pyfa's import-time normalisation: `activeStateLimit`, merging drone
   stacks, dropping invalid charges and over-fitted modules. An alternative is to keep the request faithful and
   report violations, with a `pyfa_import: true` option for strict parity.
3. Treat T3D modes explicitly: Pyfa neither writes nor reads a mode line in EFT. DNA, ESI and XML carry no mode
   either.

## 5. Round 3 scoring rules (FORMATS contract 0.1, DRAFT, with eve's rulings of 2026-10-03)

Contract: eve-dogma-bench `formats-suite`, `formats/CONTRACT-FORMATS.md` (revision 0.1, draft; not frozen, not
merged to bench main; freeze after the round-1 archive). Ground truth is Pyfa's actual behaviour, recorded
black-box by `oracle/pyfa_formats.py`. Variants re-implement it from the contract text and cases, and no Pyfa (GPL)
code may be copied.

**Interface (ruling 6).**
- `serve-stdio` RPC is mandatory. A `format-batch` CLI is optional.
- `format_export {fit, name, format, options}` returns `{"text"}`.
- `format_import {text, format, path?}` returns `{"kind","fits"}` or `{"kind","items"}`.
- Recommended error codes: `UNRECOGNIZED_INPUT` (auto-detect found nothing, including blank input), `IMPORT_ERROR`
  (format detected or forced, but no fit), `EXPORT_ERROR` and `BAD_REQUEST`. `UNSUPPORTED_FORMAT` /
  `UNKNOWN_METHOD` mean not implemented.

**Rows: 4793, of which 4779 are scored.**

| group | weight (ruling 5) | rows | source |
|---|---|---|---|
| `export` | 25 % | 3260 (3257 scored) | 326 bench fits × 10 export variants |
| `import` | 25 % | 1304 | Pyfa's import of its own export: eft, dna, esi, xml |
| `edge_export` | 25 % | 125 | 9 hand-written fits (special/unicode/newline/long/empty names, ship-only, cargo-only, drone stacks, implants + boosters) × 10 exports, plus 35 round trips |
| `edge` | 25 % | 104 (93 scored) | 87 inputs imported with `auto`, plus 17 forced-format rows: eft, dna, esi, xml, eftcfg, multi-fit, mutated, items lists, autodetect |

**Report-only rows (14, never scored).**
- 8 rows where Pyfa itself crashes (ruling 1: the oracle is invalid there).
- 2 pasted multi-fit EFT texts, which Pyfa merges into one fit (ruling 3: a known divergence; engines may merge
  or reject).
- 1 legacy item name (`Drone Control Unit I`), which only Pyfa's rename table resolves. Item names follow the
  current SDE (3569502: `Fighter Support Unit I`), and a scored control row uses that name.
- 3 `shipstats` export rows that print a stat the main bench excludes for that case (`expected/known_divergences.json`).
  The list is fixed in `formats/edge/MANIFEST.json` → `export_unscored` (eve, 2026-10-03):

  | case | excluded stat | shipstats lines |
  |---|---|---|
  | `esf_items_4` | `max_velocity` (two prop mods active at once) | Speed |
  | `esf_items_7` | `cap_capacity` (structure module on a ship) | Capacitor |
  | `esf_structure_bonus_1` | `hp.armor`, `ehp.armor` (unpowered structure plating bonus) | EHP, Armor |

**Pass rules.**
- **Export:** byte-exact text, names included. The only accepted difference is one extra `[Empty Subsystem slot]`
  on T3 cruisers (SDE vs Pyfa db).
- **Import:** same fit count and order, and the same `kind`. Per fit, these must match:
  - ship
  - mode (null = first mode, accepted)
  - modules per rack in order: type, state, charge, mutation (attributes to 6 decimals)
  - multisets of drones, fighters, implants, boosters and cargo
  - **name** (ruling 4). An XML name with a newline follows Pyfa's result: the newline becomes a space.

  Drone active counts and notes are reported only.
- **Items payloads:** `kind` plus the ordered (type, amount, mutation) list.
- **Error rows (ruling 2):** only reject-vs-accept agreement with Pyfa is scored. Codes are reported only.

**Score (ruling 5).** The mean of the four group pass rates (25 % each, per row within a group). Total scored rows
are reported too. **Correctness gate: 100 % of scored rows.**

Run it with `python3 tools/evaluate_formats.py --rpc "<variant> serve-stdio" --name X`. The output goes to
`results/formats/X/`.

**Scores (native = WASM, wasm32-wasip1; suite `formats-suite` 7c716e7):**

| build | score | scored rows | export | import | edge_export | edge | report-only rows agreeing |
|---|---|---|---|---|---|---|---|
| variant-f bc84e2b (first entrant, unchanged for the 10:20 scoring) | 98.46 % | 4773/4779 | 3257/3257 | 1304/1304 | 124/125 | 88/93 | 9/14 |
| graphs-g4 22dbeb7 / `variant-f-formats` af1c04b (F + formats parity fixes) | **100 %** | **4779/4779** (gate passed) | 3257/3257 | 1304/1304 | 125/125 | 93/93 | 11/14 |

`variant-f-formats` is a fast-forward of variant-f (bc84e2b → af1c04b), and its calc output is byte-identical. It
becomes variant-f once the round-1 run is confirmed finished.

Scorecards: eve-dogma-lab `graphs-g4` `graphs-g4/bench/formats-contract-0.1/`.
