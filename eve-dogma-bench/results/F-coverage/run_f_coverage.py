#!/usr/bin/env python3
"""F coverage: run six correctness suites against F binaries at several refs; write normalized JSON per suite x ref."""
import json, os, subprocess, sys, pathlib, time
W = pathlib.Path(__file__).resolve().parent
D = "/workspace/exct-eve/data/dataset-3569502.json.gz"
OUT = W / "cov"; OUT.mkdir(exist_ok=True)
REFS = sys.argv[1].split(",")
ONLY = sys.argv[2].split(",") if len(sys.argv) > 2 else None
def sh(cmd, cwd, timeout=1800):
    t = time.time()
    r = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    return r, round(time.time() - t, 1)
def save(suite, ref, rec):
    rec.update(suite=suite, f_ref=ref)
    (OUT / f"{suite}__{ref}.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    print(suite, ref, rec["passed"], "/", rec["total"], "fail", len(rec["failing"]), "crash", len(rec["crashes"]), "timeout", len(rec["timeouts"]), flush=True)

def stats_run(suite, ref, cwd, suite_ref, extra=""):
    B = W / "bin" / f"F-{ref}"
    name = f"F-{ref}"
    r, s = sh(f"python3 run.py --name {name} --cmd '{B} calc --dataset {D}' --batch-cmd '{B} batch --dataset {D}' "
              f"--batch-repeat 1 --latency-n 5 --timeout 10 {extra}", cwd)
    sc = json.load(open(cwd / "results" / name / "scorecard.json"))
    fl = json.load(open(cwd / "results" / name / "failures.json"))
    failing, crashes, timeouts = [], [], []
    for cid, f in sorted(fl.items()):
        err = f.get("error")
        if err:
            (timeouts if "timeout" in str(err).lower() else crashes).append({"id": cid, "error": str(err)[:300]})
        failing.append({"id": cid, "mismatches": f.get("mismatches"), "error": err})
    return dict(suite_ref=suite_ref, passed=sc["cases_fully_correct"], total=sc["cases"],
                values=f'{sc["values_correct"]}/{sc["values_total"]}', failing=failing, crashes=crashes,
                timeouts=timeouts, wall_s=s, rc=r.returncode)

for ref in REFS:
    B = W / "bin" / f"F-{ref}"
    if not ONLY or "bench-1.9.0" in ONLY:
        save("bench-1.9.0", ref, stats_run("bench-1.9.0", ref, W / "s-b19", "v1.9.0 (d2edf98), 331 cases"))
    if not ONLY or "cap-suite" in ONLY:
        cwd = W / "s-cap"; name = f"F-{ref}"
        r, s = sh(f"python3 cap/run_cap.py --name {name} --batch-cmd '{B} batch --dataset {D}'", cwd)
        sc = json.load(open(cwd / "cap/results" / f"{name}.json"))
        failing = [{"id": x["case"], "category": x.get("category"), "fails": x.get("fails"), "error": x.get("error")}
                   for x in sc["rows"] if not x.get("ok")]
        crashes = [{"id": x["case"], "error": str(x["error"])[:300]} for x in sc["rows"] if x.get("error")]
        save("cap-suite", ref, dict(suite_ref="cap-suite d80cc38, 150 cases", passed=sc["cases_ok"], total=sc["cases"],
             per_metric=sc["per_metric"], failing=failing, crashes=crashes, timeouts=[], wall_s=s, rc=r.returncode))
    if not ONLY or "mutated-suite" in ONLY:
        cwd = W / "s-mut"; name = f"F-{ref}"
        r, s = sh(f"python3 mutated/run_mutated.py --name {name} --cmd '{B} calc --dataset {D}' --batch-cmd '{B} batch --dataset {D}'", cwd)
        sc = json.load(open(cwd / "mutated/results" / name / "scorecard.json"))
        fl = json.load(open(cwd / "mutated/results" / name / "failures.json"))
        r2, s2 = sh(f"python3 mutated/tools/check_eft.py --rpc-cmd '{B} serve-stdio --dataset {D}' --dataset {D}", cwd)
        eft = json.loads(r2.stdout)
        failing = [{"id": c, "mismatches": f.get("mismatches"), "error": f.get("error")} for c, f in sorted(fl.items())]
        crashes = [{"id": c, "error": str(f["error"])[:300]} for c, f in fl.items() if f.get("error")]
        save("mutated-suite", ref, dict(suite_ref="mutated-suite 2ac7c00, 93 stats cases + EFT export/import",
             passed=sc["cases_fully_correct"], total=sc["cases"], values=f'{sc["values_correct"]}/{sc["values_total"]}',
             eft_export=eft.get("export"), eft_import=eft.get("import"), eft_export_failed=eft.get("export_failed"),
             eft_import_failed=eft.get("import_failed"), failing=failing, crashes=crashes, timeouts=[], wall_s=s + s2, rc=r.returncode))
    if not ONLY or "formats-suite" in ONLY:
        cwd = W / "s-fmt"; od = W / "tmp" / f"fmt-{ref}"
        r, s = sh(f"python3 tools/evaluate_formats.py --rpc '{B} serve-stdio --dataset {D}' --name F-{ref} --out {od}", cwd)
        sc = json.load(open(od / "scorecard.json")); fl = json.load(open(od / "failures.json"))
        scored = [f for f in fl if f.get("scored", True)]
        crashes = [f for f in scored if "crash" in json.dumps(f).lower() or "timeout" in json.dumps(f).lower()]
        save("formats-suite", ref, dict(suite_ref="formats-suite 7c716e7, FORMATS 0.1, 4779 scored rows",
             passed=sc["rows_passed"], total=sc["rows"], score_pct=sc["score_pct"], gate=sc["gate"],
             groups=sc["groups"], failing=[{"id": f["id"], "category": f.get("category"), "detail": {k: v for k, v in f.items() if k not in ("id", "category")}} for f in scored],
             report_only_disagreeing=[f["id"] for f in fl if not f.get("scored", True) and not f.get("agrees_with_pyfa", False)],
             crashes=crashes, timeouts=[], wall_s=s, rc=r.returncode))
    for gs, gdir, gref in (("graphs-0.2", "s-gr", "graphs-round2 84f7c2e, contract 0.2, 178 cases"),
                           ("graphs-0.3", "s-gr3", "graphs-round2 db81b8c = tag graphs-v0.3, contract 0.3, 192 cases")):
        if ONLY and gs not in ONLY: continue
        cwd = W / gdir; ifaces = {}
        for iface, flag in (("rpc", f"--rpc-cmd '{B} serve-stdio --dataset {D}'"), ("batch", f"--batch-cmd '{B} graph-batch --dataset {D}'")):
            name = f"F-{ref}-{iface}"
            r, s = sh(f"python3 graphs/run_graphs.py --name {name} {flag} --timeout 10", cwd)
            sc = json.load(open(cwd / "results" / f"graphs-{name}" / "scorecard.json"))
            fl = json.load(open(cwd / "results" / f"graphs-{name}" / "failures.json"))
            ifaces[iface] = dict(passed=sc["cases_fully_correct"], total=sc["cases"], values=f'{sc["values_correct"]}/{sc["values_total"]}',
                                 info_charge_ids=sc.get("info_charge_ids"),
                                 distinct_errors=sorted({json.dumps(f.get("error"), sort_keys=True) for f in fl.values() if f.get("error")}),
                                 failing=[{"id": c, "error": f.get("error"), "mismatches": f.get("mismatches")} for c, f in sorted(fl.items())],
                                 timeouts=[c for c, f in fl.items() if "timeout" in json.dumps(f).lower()])
        best = ifaces["rpc"]
        save(gs, ref, dict(suite_ref=gref + " (interfaces: rpc method graph; graph-batch)", interfaces=ifaces,
             passed=min(v["passed"] for v in ifaces.values()), total=best["total"], values=best["values"],
             failing=sorted({x["id"]: x for v in ifaces.values() for x in v["failing"]}.values(), key=lambda x: x["id"]),
             crashes=[], timeouts=sorted({t for v in ifaces.values() for t in v["timeouts"]}), wall_s=None, rc=0))
    if not ONLY or "pending-1.10-head" in ONLY:
        rec = stats_run("pending-1.10-head", ref, W / "s-p110h", "pending-1.10 head 6b10d26 (11:38 CST), full corpus 339 cases (= ed8deaa's 334 + 5 from the 1.9.0 merge)")
        r, s = sh(f"python3 tools/check_module_state.py --batch-cmd '{B} batch --dataset {D}'", W / "s-p110h")
        rec["module_state_1_4_5"] = dict(rc=r.returncode, summary=r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:], output=r.stdout[-3000:])
        save("pending-1.10-head", ref, rec)
    if not ONLY or "pending-1.10" in ONLY:
        rec = stats_run("pending-1.10", ref, W / "s-p110x", "pending-1.10 3193689 e_fz_* (8 cases, scored with bench-1.9.0 run.py/metrics)")
        # 200 legal fuzz fits vs stored Pyfa oracle output
        sys.path.insert(0, str(W / "s-b19" / "tools"))
        from metrics import from_pyfa, METRICS, extract, close
        fits = sorted(pathlib.Path("/workspace/exct-eve/fz-e/work/fits").glob("*.json"))
        orc = {json.loads(l)["file"][:-5]: json.loads(l) for l in open("/workspace/exct-eve/fz-e/work/out/oracle.jsonl")}
        fz_fail, fz_crash, fz_to, nvals = [], [], [], 0
        for f in fits:
            try:
                p = subprocess.run([str(B), "calc", str(f), "--dataset", D], capture_output=True, text=True, timeout=10)
                out = json.loads(p.stdout)
                if p.returncode not in (0, 2): fz_crash.append({"id": f.stem, "rc": p.returncode, "stderr": p.stderr[-200:]})
            except subprocess.TimeoutExpired:
                fz_to.append(f.stem); continue
            except Exception as e:
                fz_crash.append({"id": f.stem, "error": str(e)[:200]}); continue
            want = from_pyfa(orc[f.stem]["stats"]); d = {}
            for k, w in sorted(want.items()):
                if k not in METRICS: continue
                nvals += 1
                g = extract(out, METRICS[k][0]) if "error" not in out else "ERR"
                if not close(g, w): d[k] = {"pyfa": w, "got": g}
            if d: fz_fail.append({"id": f.stem, "mismatches": d})
        rec["fuzz200"] = dict(source="fz-e/work/fits (gen_legal.py fits 200 10) vs stored Pyfa oracle fz-e/work/out/oracle.jsonl; bench-1.9.0 metrics",
                              passed=len(fits) - len(fz_fail) - len(fz_crash) - len(fz_to), total=len(fits), values=nvals,
                              failing=fz_fail, crashes=fz_crash, timeouts=fz_to)
        rec["suite_ref"] += " + 200 legal fuzz fits"
        print("fuzz200", ref, rec["fuzz200"]["passed"], "/", len(fits), flush=True)
        save("pending-1.10", ref, rec)
