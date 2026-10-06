# 12 — Repository hygiene audit (all public EX-CT repos, full history)

> Audit date 2026-10-03, about 08:10–08:25 CST. The audit was read-only. It used fresh `git clone --mirror` copies in a
> scratch directory and did not touch any worktree. **No history was rewritten, and no branch or tag was deleted.**
> Rewrites are only *proposed* (section 5); the user decides.
>
> 中文摘要：对 EX-CT 全部 11 个公开仓库的所有分支和完整历史做了检查：许可证、Pyfa GPL 代码、大文件、密钥 / 个人路径、
> 误提交的构建产物。**没有发现密钥（无 Critical）**，也没有发现逐字复制的 Pyfa 源码。主要问题是历史中的大型构建产物：
> variant-j 约 291 MB，variant-c 约 10 MB。另外 variant-h 历史里有未标注 GPL 的 oracle 脚本，eve-fit-docs 和 variant-d
> 缺少 LICENSE 文件。改写历史只作为建议，由用户决定。

## 1. Scope and method

| Repo | Branches | Commits | Notes |
|---|---|---|---|
| eve-dogma-lab | 14 (`variant-b`…`variant-k`, `graphs-g1`…`graphs-g4`) | 448 | pack 90 MiB |
| eve-dogma-rs | 1 | 61 | |
| eve-dogma-bench | 4 (`main`, `bench-1.9.0`, `formats-suite`, `graphs-round2`) | 27 | |
| eve-sde-pipeline | 2 (`main`, `presets`) | 19 | |
| eve-fit-web, eve-fit-mcp, eve-fit-docs (2 branches), .github | | 18 / 13 / 14 / 1 | |
| Vexor (2), Shuttle, eve-incursions | | 18 / 2 / 71 | other EX-CT projects, outside the toolkit |

No tags exist in any repo. The checks below cover **every blob reachable from any branch** (`rev-list --all`):

- **Secrets:** gitleaks 8.30.1 (`git` mode, `--log-opts=--all`, redacted) and trufflehog 3.97.9 (`git`,
  `--no-verification`: credentials were never sent to any provider). A custom regex pass looked for GitHub tokens,
  AWS keys, private keys, generic `key/secret/password/token = "…"`, ESI `client_secret` / `refresh_token`, and e-mail
  addresses. It also looked for secret-like file names (`.env*`, `*.pem`, `*.key`, `.npmrc`, `.netrc`, …) and for
  `secrets.*` / `pull_request_target` in workflows.
- **Pyfa code:** every blob was hash-matched against all 5 657 files of Pyfa 1d9f72b. Every
  `.py/.rs/.ts/.go/.cs/.cpp/.h/.md/.yaml` blob was also line-matched: it is flagged when ≥ 30 % of its significant
  lines (≥ 30 chars, not comments or imports) appear verbatim in Pyfa's `.py`/`.yaml`. On top of that: GPL header
  strings, and the paths `pyfa*`, `oracle*`, `eos/`.
- **Large blobs:** every blob over 1 MB, with its path, the commit that adds it and the commit that removes it.
- **Artifacts:** `node_modules/`, `dist*/`, `target/`, `build*/`, `__pycache__/`, `*.pyc/.o/.a/.so/.exe/.wasm/.test`,
  datasets (`*.json.gz`, `dataset*.json`, `*.jsonl`, `*.sqlite`, `*.xlsx`), checked in history and at every branch tip.
- **Licences:** at every branch tip, the `LICENSE*` files plus manifest licence fields (Cargo.toml, package.json,
  csproj), compared with [LICENSING.md](../LICENSING.md).
- **Personal or machine paths:** `/workspace/exct-eve`, `/home/<user>/`, `/Users/…`, `C:\Users\…`, `/tmp/bench`, host
  names.

Secret values are never reproduced. Locations are given as repo / branch / commit / path, with a redacted fingerprint.

## 2. Summary

| Severity | Count | Items |
|---|---|---|
| **Critical** (live secret) | **0** | gitleaks, trufflehog and the regex pass found no credentials anywhere in history |
| High | 0 | no verbatim Pyfa source in any LGPL/MIT tree |
| Medium | 6 | M1 variant-h GPL oracle in history without notice · M2 variant-j build artifacts 291 MB · M3 variant-c Go test binary 10.5 MB · M4 eve-fit-docs no LICENSE · M5 variant-d no LICENSE (also bundled by eve-fit-web) · M6 eve-sde-pipeline committed generated presets (**fixed at tip**) |
| Low | 8 | machine paths, mislabelled lab READMEs, GPL base under graphs-g1, CCP data without a notice in Shuttle, Vexor/Shuttle without LICENSE, personal e-mails in eve-incursions, a small `.pyc` in variant-k (fixed) |
| Info | 7 | correct GPL oracles, transpiled variant E correctly GPL, oracle outputs > 1 MB, no node_modules/dist/datasets, workflows clean |

## 3. Findings

Times are CST. "Tip" means the current branch head. "History only" means the item is already deleted at the tip but
still in the packs.

### Medium

**M1 — GPL oracle and scratch files in variant-h history, without a GPL notice.**
`eve-dogma-lab@variant-h`. Commit `6767434` (05:49) added these at the branch root: `oracle_local/pyfa_oracle.py`,
`oracle_local/pyfa_oracle_a.py`, `oracle_local/__pycache__/*.pyc`, `oracle_local/*.jsonl|*.err` (0.9 MB of oracle
output), and root scratch scripts (`eftcmp.py`, `vs_a.py`, `quick.py`, …, `__pycache__/timeit.cpython-312.pyc`).
`467d258` (07:23) removed them; the tip is clean. `pyfa_oracle*.py` imports Pyfa, so like
`eve-dogma-bench/oracle/` it is GPL-3.0-or-later. Here it sat in an LGPL branch without the `LICENSE-GPL-NOTE` that
the bench and eve-dogma-rs ship. No Pyfa source was copied (the line match is 0 %).
*Handling:* no tip change is needed. Either add one line to `variant-h/README.md` saying the history-only
`oracle_local/` scripts are GPL-3.0-or-later test tools (same as `eve-dogma-bench/oracle`), or purge them (P3). Owner:
variant-h.

**M2 — variant-j build trees committed: 291 MB raw in history.**
`eve-dogma-lab@variant-j`. `variant-j/build-prof/` and `variant-j/build-native/`, added in `277729e` (04:27),
re-committed in `a06e2e6`, `56abe6d`, `8301b87`, `99693e8`, `75d52d2` (05:00) and `8a5b73f`, then removed in
`37802a8` (05:13), which also adds `build-*/` to `.gitignore`. That is 7 versions each of `libevej.a` (21–26 MB),
`eve-dogma-j` (10.7–16 MB) and the CMake `*.o` objects (3–5 MB each). These blobs make up most of the 90 MiB pack, so
every fresh clone of the lab downloads them. The tip is clean.
*Handling:* rewrite proposal P1 (after the round-1 evaluation). Until then, the tip ignore is enough to prevent more.

**M3 — Go test binary `variant-c/dogma.test` in history (known).**
`eve-dogma-lab@variant-c`, also reachable from `graphs-g2`. Added in `39ef85d` (04:14, 5.2 MB), modified in
`8459d9d` (04:24, 5.3 MB), deleted in `d212d9a` (04:26). `2726c7e` (04:22) carries it. Together 10.5 MB, an ELF
executable. The tip is clean.
*Handling:* rewrite proposal P2. Add `*.test` to `variant-c/.gitignore` (tip, owner variant-c).

**M4 — eve-fit-docs has no LICENSE file.**
`eve-fit-docs@main`, at the tip and in all history. LICENSING.md §4 says prose is CC-BY-4.0, and the repo table says
schemas are MIT. Without a licence file, GitHub shows "no licence", which legally means all rights reserved.
*Handling (docs owner):* add `LICENSE` with the CC-BY-4.0 legal code, and `schema/LICENSE` with MIT (or one
`LICENSE` with both sections, saying which paths each covers). EX-CT/.github now ships the CC-BY-4.0 text, which can be
copied.

**M5 — variant-d has no LICENSE file; eve-fit-web bundles it.**
`eve-dogma-lab@variant-d`, at the tip and in all history. Only `variant-d/package.json` declares
`"license": "LGPL-3.0-or-later"`. eve-fit-web's Pages build copies `variant-d/LICENSE` into
`public/engines/d/` with a `|| true` fallback, so the deployed site currently serves engine D with no licence text.
*Handling:* add `variant-d/LICENSE` (LGPL-3.0) and `variant-d/LICENSE.GPL-3.0` (eve is arranging this). The next Pages
build then picks them up automatically, with no web change needed.

**M6 — eve-sde-pipeline committed generated preset files.** *Fixed at tip.*
`eve-sde-pipeline@main`: `presets/presets.json` (2.6 MB, generated) and `presets/presets-pyfa.json` (copyleft
LGPL/GPL data in an MIT repo). Both came from G's branch (`9e656a7`) and were merged into main (`7bad5ed`, `68aa09e`).
LICENSING.md §3 says generated data ships as release assets, not in git.
*Fix:* `2107dbb` removes both from the tip, ignores them, and points `presets/README.md` at the release assets
(`presets.json`, `presets-pyfa-LGPL-GPL.json`, built by CI since `sde-3569502-r5`). The history copies are labelled per
section with licence and provenance, so no rewrite is needed. The merged `presets` branch still carries them (P4).

### Low

**L1 — Machine-specific paths at branch tips.** These are paths of the shared build box (`/workspace/exct-eve/...`,
`/home/box`, `/tmp/bench`), not personal names. They break defaults on other machines:
- eve-dogma-lab:
  - variant-h `src/main.rs` (`SHARED_DATASET`) and `tests/common.rs` (default dataset constant)
  - variant-c / graphs-g2: `dogma/*_test.go`, `tools/*.py`
  - variant-g / graphs-g3: `tests/*.py`
  - variant-j: `tools/*_ref.py`
  - scorecards and READMEs on every branch
- eve-fit-mcp `src/test/helpers.ts` and `src/tools/dump-schemas.ts`. These are fallbacks behind env vars, so they are
  acceptable.
- eve-dogma-bench `README.md`, `variants.yaml`, `oracle/pyfa_oracle.py`, `tools/make_expected.py`. These are
  intentional for the shared box.
- eve-dogma-rs `oracle/compare.py`, `oracle/pyfa_oracle.py`.

variant-k: fixed in `6e1f95d`, which switched to env vars.
*Handling:* source code should take paths from env or CLI with relative defaults. Scorecards and logs can stay.

**L2 — Wrong root README on lab branches.** The root `README.md` of `variant-g`, `graphs-g2` and `graphs-g3` says
"This branch: **variant-c** (Go)". `variant-g` and `graphs-g3` also carry a full copy of `variant-c/`, because they
branched from variant-c. *Handling:* fix the one-line README per branch, and drop the stray `variant-c/` copy from
`variant-g` if it is unused (owners G and graphs-g3).

**L3 — graphs-g1 builds on the GPL variant E.** `eve-dogma-lab@graphs-g1` contains `variant-e/` (GPL-3.0-or-later,
transpiled from Pyfa eos) and has no root LICENSE. Graph code added there is GPL as a derivative. That is fine as
labelled, but it **cannot be merged into the LGPL engine** without a clean-room rewrite (LICENSING.md §2).
*Handling:* add a root LICENSE (GPL-3.0) and a README note. Take this into account when choosing a round-2 winner.

**L4 — Shuttle: CCP SDE data and generated spreadsheets committed, no LICENSE, no CCP notice.**
`Shuttle@main` `e415513`: `sde/mapSolarSystems.jsonl` (5.1 MB), `sde/mapStargates.jsonl` (2.9 MB),
`sde/mapConstellations.jsonl` and more (9 MB of CCP data), plus 9 `.xlsx` outputs (4.4 MB). *Handling:* add a LICENSE
and a CCP notice (`LICENSE.EVE`, as in eve-sde-pipeline), or download the SDE at run time and release the outputs.

**L5 — Vexor: no LICENSE; `.env.production` committed.** `Vexor@main` (`ea016a3`, `d2e931d`): `.env.production`
holds only `VITE_BASE_PATH` (fingerprint `VITE_BASE_PATH=/Ve…`), which is not a secret. `gh-pages` is a build-output
branch on purpose (`assets/index-*.js`, 1.2 MB). *Handling:* add a LICENSE. Keep `.env*` in `.gitignore` as a guard.

**L6 — eve-incursions: personal e-mail addresses.** The author's personal addresses appear in commit metadata and in
the source as the ESI `User-Agent` contact (`packages/server/src/lib/esi.ts`, `commands/updateRats.ts`, …; 47
occurrences in history). They are intentional (CCP asks for a contact in the User-Agent) and published by the author.
The repo is marked retired. `seed/eve-incursions-seed.sql.gz` (3.8 MB, `ff7cefe`) was decompressed and scanned: it
holds incursion, map and station data and an empty Laravel migrations list, with no e-mails, tokens or passwords.
*Handling:* none required. Optionally use a role address in the User-Agent.

**L7 — variant-k: 5.8 KB `.pyc` committed by this audit's own fix.** It was added in `6e1f95d` and removed in
`ce381f1`, and `*.pyc` is now ignored. History-only, no action.

**L8 — EX-CT/.github had no LICENSE.** Fixed in `fe98e09`: CC-BY-4.0, matching the docs policy.

### Info (compliant)

- **I1** eve-dogma-bench `oracle/` and eve-dogma-rs `oracle/` are GPL-3.0-or-later test tools (they import Pyfa).
  Both ship `LICENSE-GPL-NOTE` and the GPL text, and the tool is never linked into the engine. This matches
  LICENSING.md.
- **I2** `variant-e` (and `graphs-g1`): eos handlers transpiled to Rust (`variant-e/src/generated/effects.rs`,
  1.4 MB) are correctly licensed GPL-3.0-or-later (LICENSE + Cargo.toml). GitHub's repo-level badge for
  eve-dogma-lab shows LGPL-3.0, because it reads the default branch (`variant-c`). *Suggestion:* add a per-branch
  licence table to the lab's root README.
- **I3** No verbatim Pyfa source anywhere. The blob hash match against Pyfa 1d9f72b and the ≥ 30 % line match found
  nothing (the only hit was the empty file). eve-sde-pipeline `tools/pyfa_effects.py` reads Pyfa with `ast` and
  emits behaviour summaries only.
- **I4** Pyfa oracle **outputs** (numeric expectations, not code) over 1 MB: `tests/oracle/pyfa_expected.json`
  (eve-dogma-rs, 1.1 MB), `variant-b/tests/oracle/pyfa_expected.json` (1.1 MB), `variant-c/testdata/oracle/pyfa_expected.json`
  (1.0–1.1 MB), and eve-dogma-bench `formats/expected/{import,export}.jsonl` (2.8 / 2.1 MB, branch `formats-suite`).
  These are test fixtures, so no action.
- **I5** No `node_modules/`, `dist/`, `target/` or `*.json.gz` dataset is committed in any toolkit repo, at any tip or
  in history. The only exceptions are the build trees in M2 and M3.
- **I6** Workflows: no `secrets.*` usage, no `pull_request_target`, and no token echo. Releases use the built-in
  `github.token`.
- **I7** All branch tips across the 11 repos are free of binaries and build directories.

## 4. Tip fixes made during the audit (owned repos only)

| Repo / branch | Commit | Change |
|---|---|---|
| eve-dogma-lab / variant-k | `6e1f95d` | add `variant-k/LICENSE.GPL-3.0` (LGPLv3 is a set of permissions on top of GPLv3); `<PackageLicenseExpression>LGPL-3.0-or-later`; README / `tools/compare_ref.py` use env vars instead of box paths |
| eve-dogma-lab / variant-k | `ce381f1` | drop the accidentally added `.pyc`, ignore `__pycache__/` and `*.pyc` |
| eve-sde-pipeline / main | `2107dbb` | stop committing generated `presets/presets.json` / `presets-pyfa.json` (now release assets only); README |
| EX-CT/.github / main | `fe98e09` | LICENSE (CC-BY-4.0) |

eve-fit-web and eve-fit-mcp (release workflow) needed no change. Other owners' items have their recommended
handling in section 3.

## 5. History-rewrite proposals (for the user to decide; none done)

All of these force-push rewritten branches. Commit SHAs change, existing clones must re-clone or hard-reset, and
evaluation records that pin SHAs (docs/09 records full SHAs as of the 10:15 cutoff) would then point at commits that
are no longer on the branch. **Do them only after round 1 is announced and archived**, one branch at a time, with the
branch owner. Before each one, create a backup bundle (`git bundle create`). GitHub may keep unreachable objects in
cached views or forks until garbage collection, which is acceptable here because no secrets are involved.

| # | Branch(es) | Purge | Gain | Command sketch |
|---|---|---|---|---|
| P1 | eve-dogma-lab `variant-j` | `variant-j/build-prof/`, `variant-j/build-native/` | ~291 MB raw, most of the 90 MiB pack | `git filter-repo --refs variant-j --path variant-j/build-prof --path variant-j/build-native --invert-paths` |
| P2 | eve-dogma-lab `variant-c`, `graphs-g2` | `variant-c/dogma.test` | 10.5 MB | `git filter-repo --refs variant-c graphs-g2 --path variant-c/dogma.test --invert-paths` |
| P3 (optional) | eve-dogma-lab `variant-h` | `oracle_local/`, root scratch `*.py`, `__pycache__/` from `6767434` | 1 MB; removes unlabelled GPL tool copies | `git filter-repo --refs variant-h --path oracle_local --path __pycache__ --invert-paths` (plus the root scratch scripts by name). The no-rewrite alternative is the M1 README note |
| P4 (branch deletion) | eve-sde-pipeline `presets` | delete the branch (fully merged in `7bad5ed`) | tidiness | `git push origin --delete presets`. The commits stay reachable from main |

Not proposed: rewriting eve-sde-pipeline main (copyleft presets in history are labelled), the variant-k `.pyc`
(trivial), eve-incursions e-mails (intentional), or Shuttle/Vexor data (owner decision).
