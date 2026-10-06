#!/usr/bin/env python3
"""Score an engine on the ext suite (stats-ext, heat, fleet.buffs, overrides).
usage: python3 ext/tools/score.py --batch-cmd "ENGINE batch" [--name X] [--out results.json] [cases...]
A case passes when every `values` metric (tools/metrics.py pointers) and every `ext` pointer (proposed FitStats
fields, CONTRACT.md "Draft 1.10: stats-ext") matches within the bench tolerance. A pointer the engine does not
return is reported as not_implemented (a failure)."""
import argparse, collections, json, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from metrics import METRICS, extract, pointer, close  # noqa: E402
SUITE = ROOT / "ext"


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
    out = subprocess.run(a.batch_cmd, shell=True, input="".join(json.dumps(r) + "\n" for r in reqs), capture_output=True, text=True)
    lines = out.stdout.splitlines()
    if len(lines) != len(reqs):
        raise SystemExit(f"batch returned {len(lines)} lines for {len(reqs)} requests: {out.stderr[-1500:]}")
    man = json.loads((SUITE / "MANIFEST.json").read_text())
    res = {}
    for f, line in zip(files, lines):
        exp = json.loads((SUITE / "expected" / f.name).read_text())
        resp = json.loads(line)
        bad, ni = [], 0
        for k, v in exp["values"].items():
            g = extract(resp, METRICS[k][0])
            if not close(g, v):
                bad.append((k, g, v))
        for p, v in exp.get("ext", {}).items():
            g = pointer(resp, p)
            if g is None:
                ni += 1
            if not close(g, v):
                bad.append((p, g, v))
        res[f.stem] = {"pass": not bad, "feature": man[f.stem]["feature"], "source": man[f.stem]["source"],
                       "checks": len(exp["values"]) + len(exp.get("ext", {})), "mismatches": len(bad),
                       "not_implemented": ni, "first": bad[:10]}
    by = collections.defaultdict(lambda: [0, 0])
    for r in res.values():
        by[r["feature"]][0] += r["pass"]
        by[r["feature"]][1] += 1
    npass = sum(r["pass"] for r in res.values())
    print(f"{a.name}: ext suite {npass}/{len(res)} pass; " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in sorted(by.items())))
    print("  failing: " + " ".join(sorted(k for k, r in res.items() if not r["pass"])))
    if a.out:
        json.dump({"name": a.name, "pass": npass, "total": len(res), "cases": res}, open(a.out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
