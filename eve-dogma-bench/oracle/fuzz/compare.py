#!/usr/bin/env python3
"""Run the Pyfa oracle (bench-1.9.0 oracle/metrics) + engines A and E on fits/*.json; write per-fit diffs.
usage: compare.py FITSDIR OUTDIR [--no-oracle] [--no-engines] [--expected-diffs FILE]
  --no-oracle   reuse OUTDIR/oracle.jsonl;  --no-engines  reuse OUTDIR/<engine>.jsonl (any engines found there)
Diffs that match an `expected_difference` entry of expected_diffs.json (Pyfa data drift allowlist, default: next to
this script) are reported as `expected_drift` (expected_drift.json, summary["expected_drift"]) and are NOT counted as
real mismatches (diffs.json, *_diff_fits)."""
import json, os, pathlib, subprocess, sys
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
ENG = {"A": ["/workspace/exct-eve/fz-e/bin/A-e4c42db", "--dataset", "/workspace/exct-eve/data/dataset-3569502.json.gz"],
       "E": ["/workspace/exct-eve/fz-e/bin/E-5867d53", "--dataset", "/workspace/exct-eve/data/dataset-3569502.json.gz"]}
args = [a for a in sys.argv[1:] if not a.startswith("--")]
fits, out = pathlib.Path(args[0]).resolve(), pathlib.Path(args[1]).resolve()
XD = pathlib.Path(sys.argv[sys.argv.index("--expected-diffs") + 1]) if "--expected-diffs" in sys.argv else W / "expected_diffs.json"
if "--expected-diffs" in sys.argv:
    args.remove(str(XD))
DATASET = "/workspace/exct-eve/data/dataset-3569502.json.gz"


def load_drift():
    """expected_difference entries of expected_diffs.json -> list of (id, metrics, matcher(request) -> bool)."""
    if not XD.exists():
        return []
    rules, eff_types = [], None
    for e in json.load(open(XD)).get("entries", []):
        if e.get("status") != "expected_difference" or not e.get("metrics"):
            continue
        if e.get("kind") == "type_attribute":
            ids = set(e.get("type_ids", []))
            rules.append((e["id"], set(e["metrics"]), lambda r, ids=ids: (r.get("ship") or {}).get("type_id") in ids))
        elif e.get("id") == "remote-capacitor-impedance" or e.get("effect_ids"):
            if eff_types is None:  # type ids carrying each effect, for "a module with effect X is projected"
                import gzip
                ds = json.load(gzip.open(DATASET))
                eff_types = {}
                for tid, t in ds["types"].items():
                    for ef in t.get("effects", []):
                        eff_types.setdefault(ef[0], set()).add(int(tid))
            src = set().union(*(eff_types.get(x, set()) for x in e.get("effect_ids", [])))
            tgt = set(e.get("target_ship_type_ids", [])); imp = set(e.get("impedance_module_type_ids", []))

            def m(r, src=src, tgt=tgt, imp=imp):
                def projected_types(r):
                    for p in r.get("projected", []) or []:
                        for k in ("module", "drone", "fighter"):
                            if isinstance(p.get(k), dict):
                                yield p[k].get("type_id")
                        if isinstance(p.get("fit"), dict):
                            for mm in p["fit"].get("modules", []):
                                if mm.get("state") in ("active", "overheated"):
                                    yield mm.get("type_id")
                        if p.get("type_id") is not None:
                            yield p.get("type_id")
                if not any(t in src for t in projected_types(r)):
                    return False
                if (r.get("ship") or {}).get("type_id") in tgt:
                    return True
                return any(mm.get("type_id") in imp and mm.get("state") in ("active", "overheated") for mm in r.get("modules", []))
            rules.append((e["id"], set(e["metrics"]), m))
    return rules


DRIFT = load_drift()
out.mkdir(parents=True, exist_ok=True)
files = sorted(fits.glob("*.json"))
names = [f.stem for f in files]
if "--no-oracle" not in sys.argv:
    env = dict(os.environ, PYTHONPATH=REF + "/stubs", ORACLE_REPEAT="0", PYFA=REF + "/pyfa")
    with open(out / "oracle.jsonl", "w") as fo:
        for i in range(0, len(files), 25):
            r = subprocess.run([REF + "/pyfa-venv/bin/python", ORACLE, *map(str, files[i:i + 25])],
                               capture_output=True, text=True, cwd=REF + "/pyfa", env=env)
            fo.write("".join(l + "\n" for l in r.stdout.splitlines() if l.startswith("{")))
            if r.returncode:
                print("oracle rc", r.returncode, r.stderr[-500:], file=sys.stderr)
            print("oracle", i + 25, flush=True)
orc = {}
for l in open(out / "oracle.jsonl"):
    j = json.loads(l)
    orc[j["file"][:-5]] = j
res = {}
if "--no-engines" in sys.argv:
    for p in sorted(out.glob("*.jsonl")):
        if p.stem == "oracle":
            continue
        res[p.stem] = {j["file"]: j["out"] for j in map(json.loads, open(p))}
for e, cmd in ({} if "--no-engines" in sys.argv else ENG).items():
    if not os.path.exists(cmd[0]):
        continue
    for f in files:
        r = subprocess.run(cmd[:1] + ["calc", str(f)] + cmd[1:], capture_output=True, text=True)
        try:
            res.setdefault(e, {})[f.stem] = json.loads(r.stdout)
        except Exception:
            res.setdefault(e, {})[f.stem] = {"error": r.stdout[:300] + r.stderr[:300]}
    with open(out / f"{e}.jsonl", "w") as fo:
        for n in names:
            fo.write(json.dumps({"file": n, "out": res[e][n]}) + "\n")
rep, drift = {}, {}
summary = {"fits": len(names), "oracle_errors": [], **{f"{e}_diff_fits": 0 for e in res}, "AE_disagree_fits": 0, "values": 0,
           "expected_drift": {"fits": 0, "values": 0, "by_entry": {}, **{f"{e}_fits": 0 for e in res}},
           "expected_diffs_file": str(XD) if XD.exists() else None}
for n in names:
    o = orc.get(n)
    if o is None or "error" in o:
        summary["oracle_errors"].append([n, (o or {}).get("error", "missing")]); continue
    want = from_pyfa(o["stats"])
    d = {}
    for k, w in sorted(want.items()):
        if k not in METRICS:
            continue
        summary["values"] += 1
        g = {e: extract(res[e][n], METRICS[k][0]) if "error" not in res[e][n] else "ERR" for e in res}
        if any(not close(g[e], w) for e in g):
            d[k] = {"pyfa": w, **g}
    req = json.load(open(fits / f"{n}.json"))
    hit = {}
    for k in list(d):
        ids = [rid for rid, ms, m in DRIFT if k in ms and m(req)]
        if ids:
            hit[k] = {**d.pop(k), "expected_diff": ids}
    if hit:
        drift[n] = hit
        x = summary["expected_drift"]; x["fits"] += 1; x["values"] += len(hit)
        for v in hit.values():
            for rid in v["expected_diff"]:
                x["by_entry"][rid] = x["by_entry"].get(rid, 0) + 1
        for e in res:
            x[f"{e}_fits"] += any(not close(v.get(e), v["pyfa"]) for v in hit.values())
    if d:
        rep[n] = d
        for e in res:
            summary[f"{e}_diff_fits"] += any(e in v and not close(v.get(e), v["pyfa"]) for v in d.values())
    if "E" in res and "A" in res:
        for k in want:
            if k in METRICS and not close(extract(res["A"][n], METRICS[k][0]), extract(res["E"][n], METRICS[k][0])):
                summary["AE_disagree_fits"] += 1; break
json.dump(rep, open(out / "diffs.json", "w"), indent=1, default=str)
json.dump(drift, open(out / "expected_drift.json", "w"), indent=1, default=str)
json.dump(summary, open(out / "summary.json", "w"), indent=1)
print(json.dumps(summary)[:2000])
