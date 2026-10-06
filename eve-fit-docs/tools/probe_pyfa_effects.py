#!/usr/bin/env python3
"""Probe for docs/19 ENG-CORE-003: which Pyfa hand-written effect handlers (eos/effects.py, read for names only)
are used by dataset types but have no SDE modifierInfo, and whether F's source names them.
Usage: probe_pyfa_effects.py PYFA_DIR DATASET.json.gz F_VARIANT_DIR"""
import gzip, json, pathlib, re, sys

pyfa, dataset, fdir = sys.argv[1:4]
d = json.load(gzip.open(dataset))
src = (pathlib.Path(pyfa) / "eos/effects.py").read_text()
names = re.findall(r'^class Effect\d+\(BaseEffect\):\n    """\n    (\w+)\n', src, re.M)
by_name = {v["name"]: (k, v) for k, v in d["effects"].items()}
used = {str(x[0]) for t in d["types"].values() for x in (t.get("effects") or [])}
fsrc = "".join(p.read_text() for p in [*pathlib.Path(fdir, "src").glob("*.rs"), pathlib.Path(fdir, "build.rs")])
mods = hand = named = 0
unnamed = []
for n in names:
    e = by_name.get(n)
    if not e or e[0] not in used:
        continue
    if e[1]["mods"]:
        mods += 1
        continue
    hand += 1
    if n in fsrc:
        named += 1
    else:
        unnamed.append(n)
print(f"used Pyfa effect classes: {mods + hand} (with SDE modifierInfo {mods}, handler-only {hand}; "
      f"handler-only named in F src {named})")
print("not named in F src:", " ".join(unnamed))
