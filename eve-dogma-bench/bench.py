#!/usr/bin/env python3
"""Score many variants and write one combined scorecard.

  python3 bench.py [--variants variants.yaml] [--only A,C] [--no-build] [--no-fetch] [--quick]

For each variant: get source (local path, or git clone/fetch of url@branch into work/<name>), read optional
`<subdir>/<manifest>` (bench.yaml with build/cmd/batch_cmd, so each variant owns its commands), run `build`,
then run.py's evaluate(). Output: results/<name>/scorecard.{md,json}, results/combined.{md,json}."""
import argparse, json, os, pathlib, subprocess, sys, time
import yaml
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import run  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent


def sh(cmd, cwd, timeout=3600):
    print(f"$ ({cwd}) {cmd}", flush=True)
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr)[-4000:]


def fetch(v, no_fetch):
    if "path" in v:
        return pathlib.Path(v["path"]), None
    g = v["git"]
    wd = ROOT / "work" / v["name"]
    if not wd.exists():
        rc, out = sh(f"git clone -q --depth 1 -b {g['branch']} {g['url']} {wd}", ROOT)
        if rc:
            return None, f"clone failed: {out.strip()[-500:]}"
    elif not no_fetch:
        rc, out = sh(f"git fetch -q --depth 1 origin {g['branch']} && git reset -q --hard FETCH_HEAD", wd)
        if rc:
            return None, f"fetch failed: {out.strip()[-500:]}"
    return wd / g.get("subdir", ""), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default=str(ROOT / "variants.yaml"))
    ap.add_argument("--only")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--quick", action="store_true", help="fewer perf repetitions")
    ap.add_argument("--cases", default="cases/*.json")
    ap.add_argument("--fresh", action="store_true", help="do not merge with rows already in results/combined.json")
    a = ap.parse_args()
    conf = yaml.safe_load(open(a.variants))
    only = set(a.only.split(",")) if a.only else None
    rows = []
    for v in conf["variants"]:
        if only and v["name"] not in only:
            continue
        row = {"name": v["name"], "label": v.get("label", ""), "status": "ok", "bench_version": bench_version(),
               "measured_at": time.strftime("%Y-%m-%d %H:%M %Z"), "loadavg": os.getloadavg()[0]}
        d, err = fetch(v, a.no_fetch)
        if err:
            row.update(status="unavailable", detail=err); rows.append(row); continue
        mf = d / v.get("manifest", "bench.yaml")
        if "cmd" not in v and mf.exists():
            v = {**v, **yaml.safe_load(open(mf))}
        if "cmd" not in v:
            row.update(status="no-manifest", detail=f"missing {mf.relative_to(ROOT) if ROOT in mf.parents else mf}"); rows.append(row); continue
        sub = lambda s: s.format(dataset=conf["dataset"], bench=ROOT, dir=d) if s else s  # noqa: E731
        if v.get("build") and not a.no_build:
            t0 = time.time()
            rc, out = sh(sub(v["build"]), d)
            row["build_s"] = round(time.time() - t0, 1)
            if rc:
                row.update(status="build-failed", detail=out[-800:]); rows.append(row); continue
        args = run.Args(name=v["name"], cmd=sub(v["cmd"]), batch_cmd=sub(v.get("batch_cmd")), cwd=str(d), cases=a.cases,
                        batch_repeat=1 if a.quick else 5, latency_n=100 if a.quick else 500)
        try:
            row["card"] = run.evaluate(args)
        except Exception as e:  # noqa: BLE001
            row.update(status="run-failed", detail=repr(e))
        if v.get("rpc_cmd"):  # informational: EFT export vs Pyfa (contract 1.4.1), not part of accuracy
            try:
                import tools.check_eft_export as cee
                row["eft_export"] = cee.check(sub(v["rpc_cmd"]), cwd=str(d))
            except Exception as e:  # noqa: BLE001
                row["eft_export"] = {"error": repr(e)}
        if d is not None and "git" in v:
            row["variant_commit"] = subprocess.run("git rev-parse --short HEAD", shell=True, cwd=d, capture_output=True, text=True).stdout.strip()
        rows.append(row)
    if not a.fresh and (ROOT / "results/combined.json").exists():
        # --only runs update their rows and keep the others (ordered as in variants.yaml)
        try:
            old = {r["name"]: r for r in json.loads((ROOT / "results/combined.json").read_text())}
        except Exception:  # noqa: BLE001
            old = {}
        new = {r["name"]: r for r in rows}
        order = [v["name"] for v in conf["variants"]]
        merged = {**old, **new}
        rows = [merged[n] for n in order if n in merged] + [r for n, r in merged.items() if n not in order]
    write_combined(rows)


def bench_version():
    f = ROOT / "VERSION"
    v = f.read_text().strip() if f.exists() else "?"
    sha = subprocess.run("git rev-parse --short HEAD", shell=True, cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return f"{v}+{sha}" if sha else v


def fmt(x, f="{:.2f}"):
    return "–" if x is None else f.format(x)


def eft(r):
    e = r.get("eft_export")
    if not e:
        return "–"
    return f"{e['ok']}/{e['total']}" if "ok" in e else "error"


def write_combined(rows):
    groups = sorted({g for r in rows if "card" in r for g in r["card"]["groups"]})
    md = ["# Combined scorecard", "", f"Generated {time.strftime('%Y-%m-%d %H:%M %Z')} — corpus: {len(list((ROOT/'cases').glob('*.json')))} cases, "
          "expected values from Pyfa (see README).", "",
          f"Bench version {bench_version()} (see CHANGELOG.md). Rows may come from different runs: see measured_at/bench_version "
          "in combined.json; perf numbers are only comparable at similar load.", "",
          "| variant | status | cases ok | values ok | accuracy % | " + " | ".join(groups) + " | ms/fit | fits/s (batch) | cold ms | deterministic | eft export | bench | measured |",
          "|" + "---|" * (12 + len(groups))]
    for r in rows:
        c = r.get("card")
        if not c:
            md.append(f"| {r['name']} {r['label']} | {r['status']} |" + " |" * (11 + len(groups)))
            continue
        p = c["perf"]
        lat = p.get("latency_one_fit", {}).get("per_calc_ms")
        fps = p.get("batch_corpus", {}).get("fits_per_s")
        cold = p["single_process_per_case_ms"]["median"]
        gcols = " | ".join(fmt(100 * c["groups"][g]["ok"] / c["groups"][g]["total"], "{:.1f}") if g in c["groups"] else "–" for g in groups)
        md.append(f"| {r['name']} {r['label']} | {r['status']} | {c['cases_fully_correct']}/{c['cases']} | {c['values_correct']}/{c['values_total']} | "
                  f"{100*c['accuracy']:.2f} | {gcols} | {fmt(lat, '{:.3f}')} | {fmt(fps, '{:.0f}')} | {fmt(cold, '{:.0f}')} | {p.get('deterministic', '–')} | {eft(r)} | {r.get('bench_version', '?')} | {r.get('measured_at', '?')} |")
    notes = [f"- {r['name']}: {r['status']}: {r.get('detail', '')[:300]}" for r in rows if r["status"] != "ok"]
    if notes:
        md += ["", "Notes:", ""] + notes
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/combined.md").write_text("\n".join(md) + "\n")
    (ROOT / "results/combined.json").write_text(json.dumps(rows, indent=1, default=str))
    print("\n".join(md))


if __name__ == "__main__":
    main()
