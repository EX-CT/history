#!/usr/bin/env python3
"""Greedy delta minimizer: drop modules/drones/fighters/implants/boosters one at a time while metric M still
differs between A and Pyfa. usage: minimize.py FIT.json METRIC OUT.json"""
import copy, json, os, pathlib, subprocess, sys, tempfile
W = pathlib.Path(__file__).resolve().parent
M19 = W / "m19"  # bench-1.9.0 tools/metrics.py + oracle/pyfa_oracle.py; falls back to this checkout's
if not M19.exists():
    M19 = W.parent.parent
    sys.path.insert(0, str(M19 / "tools")); ORACLE = str(M19 / "oracle/pyfa_oracle.py")
else:
    ORACLE = str(M19 / "pyfa_oracle.py")
sys.path.insert(0, str(M19))
from metrics import from_pyfa, METRICS, extract, close  # noqa
REF = "/workspace/exct-eve/ref"
A = ["/workspace/exct-eve/fz-e/bin/A-e4c42db"]
DSA = ["--dataset", "/workspace/exct-eve/data/dataset-3569502.json.gz"]
src, metric, dst = sys.argv[1], sys.argv[2], sys.argv[3]
tmp = pathlib.Path(tempfile.mkdtemp(prefix="fzmin-"))
env = dict(os.environ, PYTHONPATH=REF + "/stubs", ORACLE_REPEAT="0", PYFA=REF + "/pyfa")


def evaluate(reqs):
    paths = []
    for i, r in enumerate(reqs):
        p = tmp / f"c{i:03d}.json"; p.write_text(json.dumps(r)); paths.append(p)
    o = subprocess.run([REF + "/pyfa-venv/bin/python", ORACLE, *map(str, paths)],
                       capture_output=True, text=True, cwd=REF + "/pyfa", env=env)
    orc = {}
    for l in o.stdout.splitlines():
        if l.startswith("{"):
            j = json.loads(l); orc[j["file"]] = j
    res = []
    for p in paths:
        j = orc.get(p.name)
        if not j or "error" in j:
            res.append(None); continue
        w = from_pyfa(j["stats"]).get(metric)
        g = extract(json.loads(subprocess.run(A + ["calc", str(p)] + DSA, capture_output=True, text=True).stdout), METRICS[metric][0])
        res.append((g, w))
    return res


def variants(r):
    for key in ("modules", "drones", "fighters", "implants", "boosters"):
        for i in range(len(r.get(key, []))):
            v = copy.deepcopy(r); x = v[key].pop(i)
            if key == "modules" and x.get("slot") == "subsystem":
                continue
            yield f"-{key}[{i}]", v
    for i, m in enumerate(r.get("modules", [])):
        if m.get("charge_type_id"):
            v = copy.deepcopy(r); v["modules"][i]["charge_type_id"] = None; yield f"-charge[{i}]", v


r = json.load(open(src))
(g, w), = evaluate([r])
print("start", metric, "A", g, "pyfa", w)
while True:
    vs = list(variants(r))
    if not vs:
        break
    res = evaluate([v for _, v in vs])
    for (lab, v), x in zip(vs, res):
        if x and not close(*x):
            r = v; print("keep", lab, x, flush=True); break
    else:
        break
json.dump(r, open(dst, "w"), indent=1, sort_keys=True)
(g, w), = evaluate([r])
print("final", metric, "A", g, "pyfa", w, "modules", [(m["type_id"], m["state"]) for m in r["modules"]], "drones", r["drones"], "imp", r["implants"], "boo", r["boosters"])
