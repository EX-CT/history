#!/usr/bin/env python3
"""Run the eve-dogma-bench stats corpus (cases/*.json of the given bench checkout, e.g. 1.9.0 = 331 cases) through an in-browser engine of the site.

  python3 tools/browser-dogma-bench.py <bench-dir> <site-url> <engine-id> [--name N]

All requests go through one headless-Chrome session (tools/browser-rpc.mjs --batch: the page's Engine adapter, Web
Worker + WASM, i.e. the deployed build). Scoring uses the bench's own run.py (load_cases, score) and metrics.py, so
values and tolerances are the official ones. bench run.py itself starts one process per case, which for a browser
would mean one Chrome launch per case; this driver only replaces that transport. Writes <bench-dir>/results/<name>/."""
import argparse, json, pathlib, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument("bench"); ap.add_argument("url"); ap.add_argument("engine"); ap.add_argument("--name")
a = ap.parse_args()
bench = pathlib.Path(a.bench).resolve()
sys.path.insert(0, str(bench)); sys.path.insert(0, str(bench / "tools"))
import run  # noqa: E402  (bench run.py)
from metrics import METRICS  # noqa: E402

name = a.name or f"browser-{a.engine}"
cases = run.load_cases("cases/*.json")
lines = "".join(json.dumps(json.loads(r)) + "\n" for _, r, _ in cases)
t0 = time.perf_counter()
p = subprocess.run(["node", str(pathlib.Path(__file__).with_name("browser-rpc.mjs")), a.url, a.engine, "--batch"],
                   input=lines, capture_output=True, text=True, timeout=1800)
dt = time.perf_counter() - t0
outs = [l for l in p.stdout.splitlines() if l.strip()]
if p.returncode or len(outs) != len(cases):
    print(f"browser run failed: exit {p.returncode}, {len(outs)}/{len(cases)} responses\n{p.stderr[-2000:]}"); sys.exit(2)
groups, failures, ok_cases, vok, vtot = {}, {}, 0, 0, 0
for (cname, _, exp), line in zip(cases, outs):
    resp = json.loads(line)
    s = run.score(resp, exp)
    bad = {k: {"got": g, "want": w} for k, (ok, g, w) in s.items() if not ok}
    ok_cases += not bad
    if bad: failures[cname] = bad
    for k, (ok, _, _) in s.items():
        g = groups.setdefault(METRICS[k][1], [0, 0]); g[0] += ok; g[1] += 1; vok += ok; vtot += 1
out = bench / "results" / name
out.mkdir(parents=True, exist_ok=True)
card = {"variant": name, "engine": a.engine, "url": a.url, "cases": len(cases), "cases_fully_correct": ok_cases,
        "values_correct": vok, "values_total": vtot, "groups": {k: {"ok": v[0], "total": v[1]} for k, v in sorted(groups.items())},
        "wall_s_incl_browser_start": dt, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
(out / "scorecard.json").write_text(json.dumps(card, indent=1))
(out / "failures.json").write_text(json.dumps(failures, indent=1, default=str))
md = [f"# Browser dogma bench: {a.engine}", "", f"- cases fully correct: **{ok_cases}/{len(cases)}**",
      f"- values correct: **{vok}/{vtot}** ({100 * vok / vtot:.2f} %)", f"- wall time incl. browser start: {dt:.1f} s", "",
      "| group | ok | total |", "|---|---|---|"] + [f"| {k} | {v[0]} | {v[1]} |" for k, v in sorted(groups.items())]
print("\n".join(md))
sys.exit(0 if ok_cases == len(cases) else 1)
