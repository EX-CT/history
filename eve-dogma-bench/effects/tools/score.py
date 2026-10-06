#!/usr/bin/env python3
"""Score an engine on the effect suite.
usage: python3 effects/tools/score.py --batch-cmd "ENGINE batch" [--name X] [--out results.json] [cases...]
A case passes when every expected attribute (effects/expected/<case>.json `attrs`: ship, modules[i].item/charge,
drones[i], fighters[i], from the engine's options.include_attributes:"all" dump; attributes.fighters[] with
fighter_index is the 1.10 draft extension, reported separately as pass_core = pass ignoring fighters) and every bench metric (`values`)
matches within the bench tolerance (tools/metrics.py close: max(1e-3, 1e-4*|want|)). An attribute the engine does
not return counts as a mismatch."""
import argparse, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from metrics import METRICS, extract, close  # noqa: E402
SUITE = ROOT / "effects"


def cmp_item(want, got, path, bad, char=None):
    """`char`: the engine's character dump. Pyfa keeps some character attributes (maxActiveDrones,
    moduleRepairRate, ...) on the ship / items; an attribute the engine has on the character instead counts."""
    n = 0
    for k, v in want.items():
        n += 1
        g = (got or {}).get(k)
        if g is None and char is not None:
            g = char.get(k)
        if g is None or not close(g, v):
            bad.append((f"{path}.{k}", g, v))
    return n


def score_one(exp, resp):
    if "error" in resp and "attributes" not in resp:
        return {"pass": False, "error": resp["error"]}
    at = resp.get("attributes") or {}
    bad, n = [], 0
    ch = at.get("character") or {}
    n += cmp_item(exp["attrs"]["ship"], at.get("ship"), "ship", bad, ch)
    gm = {m.get("module_index"): m for m in at.get("modules") or []}
    for i, m in enumerate(exp["attrs"]["modules"]):
        g = gm.get(i) or {}
        n += cmp_item(m["item"], g.get("attributes"), f"modules[{i}]", bad, ch)
        if "charge" in m:
            n += cmp_item(m["charge"], g.get("charge"), f"modules[{i}].charge", bad)
    for arr, key in (("drones", "drone_index"), ("fighters", "fighter_index")):
        ga = {x.get(key): x for x in at.get(arr) or []}
        for i, d in enumerate(exp["attrs"][arr]):
            n += cmp_item(d, (ga.get(i) or {}).get("attributes"), f"{arr}[{i}]", bad, ch)
    mbad = []
    for k, v in exp["values"].items():
        if k in METRICS:
            g = extract(resp, METRICS[k][0])
            if not close(g, v):
                mbad.append((k, g, v))
    core = [b for b in bad if not b[0].startswith("fighters[")]
    return {"pass": not bad and not mbad, "pass_core": not core and not mbad, "attrs_checked": n, "attr_mismatches": len(bad), "metric_mismatches": len(mbad),
            "first": (bad + mbad)[:12]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-cmd", required=True)
    ap.add_argument("--name", default="engine")
    ap.add_argument("--out")
    ap.add_argument("cases", nargs="*")
    a = ap.parse_args()
    files = [pathlib.Path(f) for f in a.cases] or sorted((SUITE / "cases").glob("*.json"))
    files = [f for f in files if (SUITE / "expected" / f.name).exists()]
    reqs = [json.loads(f.read_text()) for f in files]
    out = subprocess.run(a.batch_cmd, shell=True, input="".join(json.dumps(r) + "\n" for r in reqs),
                         capture_output=True, text=True)
    lines = out.stdout.splitlines()
    if len(lines) != len(reqs):
        raise SystemExit(f"batch returned {len(lines)} lines for {len(reqs)} requests: {out.stderr[-1500:]}")
    man = json.loads((SUITE / "MANIFEST.json").read_text())
    res = {}
    for f, line in zip(files, lines):
        exp = json.loads((SUITE / "expected" / f.name).read_text())
        r = score_one(exp, json.loads(line))
        r.update({k: man.get(f.stem, {}).get(k) for k in ("effect", "how", "handler_only", "unverified37")})
        res[f.stem] = r
    npass = sum(r["pass"] for r in res.values())
    ncore = sum(r.get("pass_core", False) for r in res.values())
    print(f"{a.name}: effect suite {npass}/{len(res)} pass ({ncore} without the fighter attribute dump, which bench "
          f"1.9.0's include_attributes does not define); attrs checked {sum(r.get('attrs_checked', 0) for r in res.values())}")
    by = {}
    for r in res.values():
        b = by.setdefault(r.get("how"), [0, 0])
        b[0] += r["pass"]
        b[1] += 1
    print("  by carrier kind: " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by.items(), key=lambda x: str(x[0]))))
    u = [r for r in res.values() if r.get("unverified37")]
    print(f"  docs/19 ENG-CORE-003 unverified handler-only effects: {sum(r['pass'] for r in u)}/{len(u)}")
    ho = [r for r in res.values() if r.get("handler_only")]
    print(f"  handler-only effects: {sum(r['pass'] for r in ho)}/{len(ho)}")
    if a.out:
        json.dump({"name": a.name, "pass": npass, "total": len(res), "cases": res}, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
