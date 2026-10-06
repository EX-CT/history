#!/usr/bin/env python3
"""eve-dogma-bench runner: scores any engine that implements CONTRACT.md.

  python3 run.py --name variant-a --cmd "eve-dogma calc" [--batch-cmd "eve-dogma batch"] [--cwd DIR]

--cmd        single mode: `<cmd> < request.json > response.json` (one process per case => includes cold start)
--batch-cmd  optional batch mode: JSONL requests on stdin -> JSONL responses on stdout, same order
Writes results/<name>/scorecard.{json,md} and per-case diffs (results/<name>/failures.json)."""
import argparse, json, os, pathlib, shlex, statistics, subprocess, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).parent / "tools"))
from metrics import METRICS, extract, close  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent


def load_cases(pattern):
    cases = []
    for p in sorted(ROOT.glob(pattern)):
        e = ROOT / "expected" / p.name
        if e.exists():
            cases.append((p.stem, p.read_text(), json.loads(e.read_text())))
    return cases


def run_one(cmd, req, cwd, timeout):
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, input=req, capture_output=True, text=True, cwd=cwd, timeout=timeout, shell=True)
    except subprocess.TimeoutExpired:
        return None, timeout * 1000, "timeout"
    dt = (time.perf_counter() - t0) * 1000
    if r.returncode != 0:
        return None, dt, f"exit {r.returncode}: {r.stderr.strip()[-300:]}"
    try:
        return json.loads(r.stdout), dt, None
    except json.JSONDecodeError as e:
        return None, dt, f"bad json: {e}: {r.stdout[:200]}"


def score(resp, exp):
    res = {}
    if resp is None or "error" in resp and len(resp) == 1:
        return {k: (False, None, v) for k, v in exp["values"].items()}
    for k, want in exp["values"].items():
        got = extract(resp, METRICS[k][0])
        res[k] = (close(got, want), got, want)
    return res


def batch_time(cmd, lines, cwd, timeout):
    data = "".join(l + "\n" for l in lines)
    t0 = time.perf_counter()
    r = subprocess.run(cmd, input=data, capture_output=True, text=True, cwd=cwd, timeout=timeout, shell=True)
    dt = time.perf_counter() - t0
    outs = [l for l in r.stdout.splitlines() if l.strip()]
    return dt, outs, r.returncode


class Args:
    def __init__(self, **kw):
        self.__dict__.update(dict(cwd=None, cases="cases/*.json", timeout=60, batch_repeat=5, latency_n=500,
                                  latency_case="exct_rifter", batch_cmd=None))
        self.__dict__.update(kw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--cmd", required=True)
    ap.add_argument("--batch-cmd")
    ap.add_argument("--cwd", default=None)
    ap.add_argument("--cases", default="cases/*.json")
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--batch-repeat", type=int, default=5, help="corpus repetitions for throughput")
    ap.add_argument("--latency-n", type=int, default=500, help="repetitions of one fit for latency")
    ap.add_argument("--latency-case", default="exct_rifter")
    a = ap.parse_args()
    evaluate(a)


def evaluate(a):
    cases = load_cases(a.cases)
    out_dir = ROOT / "results" / a.name
    out_dir.mkdir(parents=True, exist_ok=True)

    per_metric, per_group, failures, walls, errors = {}, {}, {}, [], {}
    passed_cases = 0
    for name, req, exp in cases:
        resp, ms, err = run_one(a.cmd, req, a.cwd, a.timeout)
        walls.append(ms)
        if err:
            errors[name] = err
        s = score(resp, exp)
        bad = {k: {"got": g, "want": w} for k, (ok, g, w) in s.items() if not ok}
        if not bad and not err:
            passed_cases += 1
        else:
            failures[name] = {"error": err, "mismatches": bad}
        for k, (ok, _, _) in s.items():
            m = per_metric.setdefault(k, [0, 0]); m[0] += ok; m[1] += 1
            g = per_group.setdefault(METRICS[k][1], [0, 0]); g[0] += ok; g[1] += 1
    total_ok = sum(v[0] for v in per_metric.values())
    total = sum(v[1] for v in per_metric.values())

    perf = {"single_process_per_case_ms": {"median": statistics.median(walls) if walls else None,
                                            "min": min(walls) if walls else None, "max": max(walls) if walls else None}}
    if a.batch_cmd:
        lines = [json.dumps(json.loads(r)) for _, r, _ in cases]
        dt, outs, rc = batch_time(a.batch_cmd, lines * a.batch_repeat, a.cwd, a.timeout * 20)
        n = len(lines) * a.batch_repeat
        perf["batch_corpus"] = {"requests": n, "total_s": dt, "fits_per_s": n / dt if dt else None,
                                "avg_ms_incl_startup": dt * 1000 / n, "responses": len(outs), "exit": rc}
        lat = next((r for nm, r, _ in cases if nm == a.latency_case), cases[0][1])
        lat = json.dumps(json.loads(lat))
        dt1, _, _ = batch_time(a.batch_cmd, [lat], a.cwd, a.timeout)
        dtn, outs_n, _ = batch_time(a.batch_cmd, [lat] * a.latency_n, a.cwd, a.timeout * 20)
        perf["latency_one_fit"] = {"case": a.latency_case, "n": a.latency_n, "startup_plus_one_ms": dt1 * 1000,
                                   "per_calc_ms": (dtn - dt1) * 1000 / max(a.latency_n - 1, 1)}
        # determinism: identical outputs for identical requests
        perf["deterministic"] = len(set(outs_n)) == 1 if outs_n else None

    card = {"variant": a.name, "cmd": a.cmd, "batch_cmd": a.batch_cmd, "cases": len(cases), "cases_fully_correct": passed_cases,
            "values_correct": total_ok, "values_total": total, "accuracy": total_ok / total if total else 0,
            "groups": {g: {"ok": v[0], "total": v[1]} for g, v in sorted(per_group.items())},
            "metrics": {k: {"ok": v[0], "total": v[1]} for k, v in sorted(per_metric.items())},
            "errors": len(errors), "perf": perf, "host": os.uname().machine, "time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    (out_dir / "scorecard.json").write_text(json.dumps(card, indent=1, default=str))
    (out_dir / "failures.json").write_text(json.dumps(failures, indent=1, default=str))
    md = [f"# Scorecard: {a.name}", "", f"- command: `{a.cmd}`" + (f", batch: `{a.batch_cmd}`" if a.batch_cmd else ""),
          f"- cases fully correct: **{passed_cases}/{len(cases)}**", f"- values correct: **{total_ok}/{total}** ({100*card['accuracy']:.2f} %)",
          f"- engine errors: {len(errors)}", "", "| group | ok | total | % |", "|---|---|---|---|"]
    for g, v in sorted(per_group.items()):
        md.append(f"| {g} | {v[0]} | {v[1]} | {100*v[0]/v[1]:.1f} |")
    md += ["", "| perf | value |", "|---|---|",
           f"| one process per case, median ms (cold start + calc) | {perf['single_process_per_case_ms']['median']:.1f} |" if walls else ""]
    if "batch_corpus" in perf:
        b, l = perf["batch_corpus"], perf["latency_one_fit"]
        md += [f"| batch throughput (corpus x{a.batch_repeat}) fits/s | {b['fits_per_s']:.0f} |",
               f"| latency one fit ({l['case']}) ms/calc | {l['per_calc_ms']:.3f} |",
               f"| startup + one calc ms | {l['startup_plus_one_ms']:.1f} |", f"| deterministic | {perf['deterministic']} |"]
    worst = sorted(((k, v) for k, v in per_metric.items() if v[0] < v[1]), key=lambda kv: kv[1][0] / kv[1][1])[:15]
    if worst:
        md += ["", "Worst metrics:", ""] + [f"- {k}: {v[0]}/{v[1]}" for k, v in worst]
    (out_dir / "scorecard.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    return card


if __name__ == "__main__":
    main()
