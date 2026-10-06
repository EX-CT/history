#!/usr/bin/env python3
"""ext/expected/<case>.json from the Pyfa oracle (ORACLE_EXTRA=ext): bench metrics (`values`, tools/metrics.py) for
every case plus the feature's Pyfa values (`ext`, keyed by JSON pointer into the proposed FitStats fields of
CONTRACT.md "Draft 1.10: stats-ext"). Hand-derived cases (overrides, oracle "hand-derived (non-Pyfa)") are left alone.
usage: python3 ext/tools/make_expected.py [ext/cases/*.json]"""
import json, os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from metrics import from_pyfa, METRICS  # noqa: E402
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
STUB = os.environ.get("WX_STUB", f"{REF}/stubs")
SUITE = ROOT / "ext"
LAYERS = ("shield", "armor", "hull")


def ext_pointers(feature, x):
    out = {}
    if "mining" in feature:
        m = x["mining"]
        out.update({"/mining/modules_m3_s": m["miner_yield"], "/mining/drones_m3_s": m["drone_yield"],
                    "/mining/total_m3_s": m["miner_yield"] + m["drone_yield"],
                    "/mining/modules_drain_m3_s": m["miner_drain"], "/mining/drones_drain_m3_s": m["drone_drain"]})
    if feature == "outgoing":
        for k, kk in (("current", "current"), ("min", "spool_min"), ("max", "spool_max")):
            for l, v in x["outgoing"][k].items():
                out[f"/outgoing/{kk}/{l}_per_s"] = v
    if feature == "drone_ehp":
        for arr, key, lst in (("drones", "drone_index", x["drones"]), ("fighters", "fighter_index", x["fighters"])):
            for d in lst:
                i = d[key]
                for l in LAYERS:
                    out[f"/{arr}/items[{key}={i}]/hp/{l}"] = d["hp"][l]
                    out[f"/{arr}/items[{key}={i}]/ehp/{l}"] = d["ehp"][l]
                if "shield_regen" in d:
                    out[f"/{arr}/items[{key}={i}]/shield_peak_recharge_hp_s"] = d["shield_regen"]
    if feature == "bombing":
        for dt, lv in x["bombing"].items():
            for L, v in lv.items():
                out[f"/bombing/{dt}/covert_ops_{L}"] = v
    if feature == "heat":
        for h in x["heat"]:
            out[f"/modules[module_index={h['module_index']}]/heat/burn_cycles"] = h["burn_cycles"]
            out[f"/modules[module_index={h['module_index']}]/heat/burnout_s"] = h["burnout_s"]
    return out


def main(files):
    files = [str(pathlib.Path(f).resolve()) for f in files] or sorted(str(p) for p in (SUITE / "cases").glob("*.json"))
    man = json.loads((SUITE / "MANIFEST.json").read_text())
    files = [f for f in files if "non-Pyfa" not in man[pathlib.Path(f).stem]["source"]]
    env = dict(os.environ, PYTHONPATH=STUB, ORACLE_REPEAT="0", PYFA=PYFA, ORACLE_EXTRA="ext")
    out = subprocess.run([PY, str(ROOT / "oracle/pyfa_oracle.py"), *files], capture_output=True, text=True, cwd=PYFA, env=env)
    if out.returncode:
        print(out.stderr[-3000:], file=sys.stderr)
    n = 0
    for line in out.stdout.splitlines():
        if not line.startswith("{"):
            continue
        r = json.loads(line)
        name = r["file"][:-5]
        if "error" in r:
            print(f"{name}: oracle error {r['error']}")
            continue
        feat = man[name]["feature"]
        exp = {"case": name, "oracle": "pyfa-eos", "feature": feat,
               "values": {k: v for k, v in sorted(from_pyfa(r["stats"]).items()) if k in METRICS},
               "ext": ext_pointers(feat, r["stats"]["ext"]), "excluded": {}}
        (SUITE / "expected" / f"{name}.json").write_text(json.dumps(exp, indent=1, sort_keys=True, default=str) + "\n")
        n += 1
    print(f"wrote {n} expected files")


if __name__ == "__main__":
    main(sys.argv[1:])
