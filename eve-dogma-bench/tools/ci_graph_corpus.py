#!/usr/bin/env python3
"""Graph corpus integrity (no engine, no Pyfa): every graphs/cases/*.json has an expected file; each expected
series has one value per x (or is null-padded), finite numbers, and dps/volley/damage/hp-type series are >= 0.

  python3 tools/ci_graph_corpus.py GRAPHS_DIR"""
import json, math, pathlib, sys

g = pathlib.Path(sys.argv[1])
errs, n = [], 0
NONNEG = ("dps", "volley", "damage", "cap", "hp", "time", "speed", "range", "strength", "rps")
for c in sorted((g / "cases").glob("*.json")):
    e = g / "expected" / c.name
    if not e.exists():
        errs.append(f"{c.stem}: no expected file")
        continue
    x = json.loads(e.read_text())
    n += 1
    if "expect_error" in x:
        continue
    xs = x.get("x", [])
    for y, vals in x.get("series", {}).items():
        if y.endswith("_charge_type_id"):
            continue
        if len(vals) != len(xs):
            errs.append(f"{c.stem}.{y}: {len(vals)} values for {len(xs)} x")
        for i, v in enumerate(vals):
            if v is None:
                continue
            if not isinstance(v, (int, float)) or not math.isfinite(v):
                errs.append(f"{c.stem}.{y}[{i}]: {v!r}")
            elif v < -1e-9 and any(k in y for k in NONNEG) and "delta" not in y:
                errs.append(f"{c.stem}.{y}[{i}] = {v} < 0")
print(f"graph corpus: {n} cases checked, {len(errs)} problems")
for m in errs[:50]:
    print("  -", m)
sys.exit(1 if errs else 0)
