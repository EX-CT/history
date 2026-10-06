# Licensing decisions

| Upstream | License | Notes |
|---|---|---|
| Pyfa application (`gui/`, `service/`, `graphs/`, root) | **GPL-3.0-or-later** | file headers "This file is part of pyfa … GPL v3" |
| Pyfa `eos/` (engine) | **LGPL-2.0-or-later** (headers) — `eos/lgpl.txt`; `eos/calc.py` is GPLv3 (header "part of pyfa") | |
| EVEShipFit dogma-engine / data | **MIT** (+ CCP licence for EVE data) | |
| EVE data (SDE, icons) | CCP Games "Developer License Agreement" / EVE content licence | not open source; redistribution of derived data allowed for third-party tools, with CCP copyright notice |

## Our policy

1. **eve-dogma-rs** (engine): **LGPL-3.0-or-later**. Rationale: the engine reproduces eos behaviour; if we ever
   translate specific eos handler logic (LGPL-2.0-or-later), LGPL-3.0-or-later is a valid upgrade path, while still
   letting proprietary or MIT front-ends/bots *link* to it (dynamic link / WASM module / process boundary).
   MIT code from dogma-engine may be incorporated (MIT → LGPL compatible; keep MIT notices).
2. **No direct translation of GPL-only Pyfa files** (`service/port/*`, `graphs/*`, `eos/calc.py`, `gui/*`) into
   the LGPL/MIT repos. Behaviour is re-implemented clean-room from: CCP data, public formulas (EVE University wiki,
   CCP dev blogs), file-format specs (EFT/DNA/XML/ESI are public formats), and Pyfa used **only as a black-box
   test oracle** (comparing numeric outputs is not copying). Formulas/mathematical facts are not copyrightable;
   code expression is. Contributors who have read GPL code should write from the doc in `eve-fit-docs`, not from
   the Python source side-by-side. If a feature cannot practically be done this way, it goes into a separate
   **GPL-3.0** crate (`eve-fit-gpl-extras`) that is optional.
3. **eve-sde-pipeline**, **eve-fit-mcp**, schemas: **MIT**. Generated datasets carry `LICENSE.EVE` (CCP notice) and
   are published as release assets, not committed to git.
4. **eve-fit-docs**: CC-BY-4.0 for prose. The analysis documents quote short excerpts/paths of Pyfa for
   commentary (fair use / quotation right); no wholesale code reproduction.

> 中文：引擎用 LGPL-3.0+（兼容 eos 的 LGPL-2.0+，又不强迫上层闭源/开源），其它仓库 MIT；不直接翻译 Pyfa 的 GPL 部分，
> 只把 Pyfa 当“黑盒对照”验证数值；EVE 数据遵循 CCP 授权，只作为 Release 资源分发。
