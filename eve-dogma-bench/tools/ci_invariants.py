#!/usr/bin/env python3
"""Nightly fuzz self-consistency check: no Pyfa needed.

  python3 tools/ci_invariants.py --batch-cmd "eve-dogma batch" --cmd "eve-dogma calc" [--n 300] [--seed S] [--single 40]

Pyfa can't run in CI, so this doesn't compare with an oracle. (The committed oracle expectations are checked by run.py on
the corpus.) It mutates the committed corpus requests (cases/*.json) with a seeded RNG: skill levels, module states,
damage pattern, dropped modules/drones. Then it checks properties every correct engine must have:
  determinism       the same batch run twice gives byte-identical JSON (meta excluded)
  batch == single   `calc` on one request gives the same stats as that request inside `batch`
  bounds            resonances in [0,1]; hp, ehp, dps, volley, velocity, capacity >= 0; finite numbers;
                    ehp.total >= hp.total; dps/volley totals = sum of the damage types; align = ln(4)*agility*mass/1e6
  monotonic         all skills V never lowers hp.total, capacitor capacity or max_targets vs the same fit at all skills 0
Exit 1 on any violation; writes ci-invariants.json + a markdown summary (to $GITHUB_STEP_SUMMARY if set).
"""
import argparse, copy, json, math, os, pathlib, random, shlex, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DMG = ("em", "thermal", "kinetic", "explosive")


def run_batch(cmd, reqs):
    out = subprocess.run(cmd, shell=True, input="".join(json.dumps(r) + "\n" for r in reqs), capture_output=True, text=True, timeout=900)
    lines = out.stdout.splitlines()
    if len(lines) != len(reqs):
        raise SystemExit(f"batch returned {len(lines)} lines for {len(reqs)} requests (rc {out.returncode}): {out.stderr[-2000:]}")
    return [json.loads(l) for l in lines]


def strip(o):
    o = copy.deepcopy(o)
    if isinstance(o, dict):
        o.pop("meta", None)
    return o


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def mutate(rng, base, i):
    r = copy.deepcopy(base)
    kind = rng.choice(["skills", "states", "pattern", "drop", "none"])
    if kind == "skills":
        r.setdefault("character", {}).setdefault("skills", {})["default_level"] = rng.randint(0, 5)
    elif kind == "states" and r.get("modules"):
        for m in r["modules"]:
            if rng.random() < 0.4:
                m["state"] = rng.choice(["offline", "online", "active", "overheated"])
    elif kind == "pattern":
        w = [rng.randint(0, 100) for _ in DMG]
        if sum(w):
            r["damage_pattern"] = dict(zip(DMG, w))
    elif kind == "drop":
        for key in ("modules", "drones"):
            if r.get(key):
                r[key].pop(rng.randrange(len(r[key])))
    return kind, r


def check(o, errs, tag):
    def bad(msg):
        errs.append(f"{tag}: {msg}")

    if not isinstance(o, dict) or "error" in o:
        return  # an error response is fine for a mutated request (e.g. validation); determinism still checked
    stack = [("", o)]
    while stack:
        p, v = stack.pop()
        if isinstance(v, dict):
            stack += [(p + "." + k, x) for k, x in v.items()]
        elif isinstance(v, list):
            stack += [(f"{p}[{j}]", x) for j, x in enumerate(v)]
        elif isinstance(v, float) and not math.isfinite(v):
            bad(f"non-finite {p}={v}")
    d = o.get("defense", {})
    for layer, res in d.get("resonance", {}).items():
        for t, x in res.items():
            if num(x) and not (-1e-9 <= x <= 1 + 1e-9):
                bad(f"resonance {layer}.{t}={x} outside [0,1]")
    for sec in ("hp", "ehp"):
        for k, x in d.get(sec, {}).items():
            if num(x) and x < -1e-9:
                bad(f"{sec}.{k}={x} < 0")
    hp, ehp = d.get("hp", {}).get("total"), d.get("ehp", {}).get("total")
    if num(hp) and num(ehp) and ehp + 1e-6 < hp:
        bad(f"ehp.total {ehp} < hp.total {hp}")
    tot = o.get("offense", {}).get("total", {})
    for k in ("dps", "volley"):
        v = tot.get(k, {})
        if isinstance(v, dict) and num(v.get("total")):
            parts = [v.get(t, 0) or 0 for t in DMG]
            if any(x < -1e-9 for x in parts):
                bad(f"{k} negative part {parts}")
            if abs(sum(parts) - v["total"]) > 1e-3 * max(1, abs(v["total"])):
                bad(f"{k}.total {v['total']} != sum of types {sum(parts)}")
    n = o.get("navigation", {})
    if num(n.get("max_velocity")) and n["max_velocity"] < -1e-9:
        bad(f"max_velocity {n['max_velocity']} < 0")
    if all(num(n.get(k)) for k in ("align_time_s", "agility", "mass")) and n["mass"] > 0:
        want = math.log(4) * n["agility"] * n["mass"] / 1e6
        if abs(n["align_time_s"] - want) > 1e-3 * max(1, want):
            bad(f"align_time_s {n['align_time_s']} != ln4*agility*mass/1e6 {want}")
    c = o.get("capacitor", {})
    if num(c.get("capacity")) and c["capacity"] < -1e-9:
        bad(f"capacitor.capacity {c['capacity']} < 0")


def get(o, *path):
    for k in path:
        if not isinstance(o, dict):
            return None
        o = o.get(k)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch-cmd", required=True)
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--single", type=int, default=40)
    ap.add_argument("--seed", type=int, default=int(os.environ.get("FUZZ_SEED", "20261003")))
    ap.add_argument("--cases", default=str(ROOT / "cases"))
    a = ap.parse_args()
    rng = random.Random(a.seed)
    bases = [json.loads(p.read_text()) for p in sorted(pathlib.Path(a.cases).glob("*.json"))]
    reqs, kinds = [], []
    for i in range(a.n):
        k, r = mutate(rng, rng.choice(bases), i)
        reqs.append(r)
        kinds.append(k)
    # skill monotonicity pairs: the same corpus fit at all skills 0 and all skills V
    pairs = []
    for b in rng.sample(bases, min(40, len(bases))):
        lo, hi = copy.deepcopy(b), copy.deepcopy(b)
        for r, lvl in ((lo, 0), (hi, 5)):
            s = r.setdefault("character", {}).setdefault("skills", {})
            s["default_level"], s["levels"] = lvl, {}
        pairs.append((len(reqs), len(reqs) + 1))
        reqs += [lo, hi]
        kinds += ["skills0", "skills5"]
    errs = []
    r1 = run_batch(a.batch_cmd, reqs)
    r2 = run_batch(a.batch_cmd, reqs)
    for i, (x, y) in enumerate(zip(r1, r2)):
        if json.dumps(strip(x), sort_keys=True) != json.dumps(strip(y), sort_keys=True):
            errs.append(f"req {i} ({kinds[i]}): nondeterministic batch output")
    for i in rng.sample(range(len(reqs)), min(a.single, len(reqs))):
        out = subprocess.run(a.cmd, shell=True, input=json.dumps(reqs[i]), capture_output=True, text=True, timeout=120)
        try:
            s = json.loads(out.stdout)
        except ValueError:
            s = {"error": {"code": "NO_JSON", "message": out.stderr[-300:]}}
        if ("error" in s) != ("error" in r1[i]) or ("error" not in s and json.dumps(strip(s), sort_keys=True) != json.dumps(strip(r1[i]), sort_keys=True)):
            errs.append(f"req {i} ({kinds[i]}): single calc != batch")
    for i, o in enumerate(r1):
        check(o, errs, f"req {i} ({kinds[i]})")
    for lo, hi in pairs:
        for path in (("defense", "hp", "total"), ("capacitor", "capacity"), ("targeting", "max_targets")):
            x, y = get(r1[lo], *path), get(r1[hi], *path)
            if num(x) and num(y) and y + 1e-6 < x:
                errs.append(f"req {lo}/{hi}: {'.'.join(path)} drops with skills V ({x} -> {y})")
    n_err = sum(1 for o in r1 if isinstance(o, dict) and "error" in o)
    summary = {"seed": a.seed, "requests": len(reqs), "error_responses": n_err, "violations": len(errs), "first": errs[:50]}
    pathlib.Path("ci-invariants.json").write_text(json.dumps(summary, indent=1))
    md = [f"### Fuzz self-consistency (seed {a.seed})", "", f"- requests: {len(reqs)} ({n_err} error responses)",
          f"- violations: **{len(errs)}**"] + [f"  - {e}" for e in errs[:50]]
    print("\n".join(md))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write("\n".join(md) + "\n")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
