#!/usr/bin/env python3
"""Round-1 engine evaluation for the EX-CT dogma bake-off (variants A–K): reproducible, one command.

  python3 tools/evaluate.py [--runs 3] [--only A,J] [--quick] [--dry-run] [--out results]
                            [--as-of 2026-10-03T10:15:00+08:00]
                            [--work-dir work/eval] [--fresh-clones] [--no-fetch] [--no-build] [--no-tests]
                            [--build-timeout 900] [--test-timeout 300] [--variant-timeout 1200] [--case-timeout 20]

What it does, per variant (sequentially, so variants never compete for the CPU with each other):
  1. fetch   A = EX-CT/eve-dogma-rs@main (repo root); B–K = EX-CT/eve-dogma-lab@variant-<x> (dir variant-<x>/,
             commands from its bench.yaml). Shallow clone into --work-dir/<X> (or fetch + hard reset to the remote
             head or the --as-of commit); the full commit SHA is recorded. --fresh-clones deletes the clone first
             (=> fresh build time).
             --as-of T: evaluate the last commit on the branch (first-parent) whose committer date is <= T instead of
             the current head (default: current head). The evaluated SHA + commit time, and the branch head at fetch
             time, are recorded per variant in evaluation.json and evaluation.md.
  2. build   the manifest's `build` command (timeout --build-timeout); wall time and fresh/incremental recorded.
  3. bench   the *official* scorer run.evaluate() (same code bench.py calls) --runs times, each in a child process
             with a hard timeout (--variant-timeout for all runs, --case-timeout per request) so a hung or broken
             variant cannot stall the evaluation. One untimed warm-up batch over the corpus precedes run 1 (page cache,
             dataset caches). Correctness is taken from run 1 (and checked identical in every
             run); perf numbers are the median over runs. loadavg (1/5/15 min) is recorded before and after each run.
  4. extras  EFT export check (tools/check_eft_export.py, Pyfa byte-exact) and RPC probes (eft_parse, calc via RPC,
             meta, unknown method, search, type) through the manifest's `rpc_cmd`.
  5. maint.  static metrics on the variant directory (see below) and the variant's own test suite (if discoverable).
Bench 1.8.0 (cases/, expected/, run.py, tools/metrics.py) is used unchanged; this tool only reads it.

SCORING RULES (round 1)
  Version rule: each variant is evaluated at its branch HEAD as of the cutoff (unified scoring: --as-of
        2026-10-03T10:15:00+08:00; A = eve-dogma-rs main, B–K = eve-dogma-lab variant-<x>). Self-reported "final"
        versions in variant READMEs/results are reference only. If that commit fails the correctness gate the variant
        is DISQUALIFIED for the round; there is no automatic fallback to an older commit.
  Gate: correctness. A variant is ranked only if status is ok and it passes ALL bench cases (cases fully correct
        == cases, no engine errors) in every run. Ungated variants are listed with the reason, unscored.
  Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability          (each sub-score in [0,1])
  Normalisation helper  L(x, best, span) = clamp(1 − log10(x / best) / log10(span), 0, 1)  for lower-is-better x
        (1 at the best ranked variant, 0 at `span`× worse; log scale so a 2× gap costs the same everywhere).
  Speed = 0.5·L(latency ms/calc, best, 100) + 0.3·L(1/batch fits-per-s, best, 100) + 0.2·L(cold ms, best, 100)
        latency = own measurement (see measure_latency(): batch cmd pinned to ONE cpu, (t_N − t_1)/(N − 1), ≥ 5
        independent samples, median; invalid if ≤ 0, < 0.002 ms floor, > t_N/N or wrong response count; spread
        > 50 % => up to 3 extra samples, then flagged; spread/flags in md+json). run.py's per-run latency_one_fit
        (one (500−1)/499 difference, sensitive to startup jitter, multi-threaded batch) is kept as info only.
        throughput = batch_corpus.fits_per_s, cold = median wall time
        of one process per case (single mode); medians over --runs. Only comparable at similar load: see loadavg.
  Maintainability = 0.25·Tests + 0.20·DataDriven + 0.20·Size + 0.15·Docs + 0.10·Deps + 0.10·Build
        Tests      own test command ran and passed: 0.6 + 0.4·min(1, log10(1+n)/log10(101)) (n = tests passed, or
                   static count if the runner gives no count); failed: 0.2; exists but timed out / not run: 0.3;
                   no tests found: 0.
        DataDriven L(h + 10, h_min + 10, 10) where h = number of distinct dataset effect names (camelCase, ≥ 8 chars)
                   that appear as identifiers/strings in hand-written, non-test core source, i.e. effects special-cased
                   by name (heuristic; generated code and vendored code are excluded and reported separately).
                   data_driven_ratio = 1 − h / (effects with modifierInfo in the dataset) is reported for information.
        Size       L(core LOC, min core LOC, 10); core LOC = non-blank, non-comment lines of hand-written non-test,
                   non-tooling source (simple built-in counter unless tokei/scc/cloc is installed; same for all).
        Docs       0.4·README + 0.4·DESIGN (DESIGN.md or docs/design*/architecture*) + 0.2·LICENSE file
        Deps       1 / (1 + n/5), n = direct runtime dependencies from the manifest (Cargo/go.mod/package.json/csproj/
                   CMake find_package+FetchContent+vendored third_party/Python third-party imports)
        Build      L(build s, best, 100) of this run's build. Only meaningful for fresh builds (--fresh-clones): if any
                   ranked variant's build was incremental, Build is dropped and the other weights are renormalised.
        (cold start and LOC per language are reported too; cold start is scored under Speed only.)
  Features = mean of 4 parts: EFT = 0.5·(export ok/total) + 0.5·(eft_parse round-trip ok / probes),
        RPC = share of probes ok (calc via serve-stdio equals calc CLI output; meta has sde_build; unknown method
        -> UNKNOWN_METHOD error; ids echoed), search = share of interim-spec probes ok (exact/prefix/zh/limit/kinds),
        type = share of probes ok (by id, by name, unknown id -> error).
  Portability (WASM/browser) = 1.0 if the code base has a browser/WASM build (wasm-bindgen/wasm32 target,
        emscripten, browser bundle/tsconfig, pyodide …), 0.5 if only documented as possible/planned, else 0.
Bench pin: run.py, tools/metrics.py, cases/ and expected/ come from bench commit 3da9671 (1.8.0, 326 cases, cases
  identical to 0969967), extracted with `git archive` into <work-dir>/bench-<sha>, regardless of upstream main
  (--bench-ref to override). The pinned SHA, version and case count are recorded in the output.
Licensing (informational, not scored), judged at the evaluated (--as-of) commit like the code: the actual LICENSE*/
  COPYING* texts in the variant dir AND the branch root decide (LGPL header, with or without the companion GPL text
  => LGPL; GPL header and no LGPL text => GPL; MIT/Apache/BSD/MPL by text). SPDX metadata / README "License"
  section only refine -only vs -or-later and reveal conflicts. "Mergeable into LGPL-3.0-or-later mainline" = yes
  (LGPL-3 / permissive), no (GPL), unknown (no LICENSE file, unrecognised text, or file vs metadata conflict).
Outputs: <out>/evaluation.md and <out>/evaluation.json (+ <out>/raw/<X>/ per-run scorecards and logs).
--dry-run writes to results/dryrun/ by default and marks every output DRY RUN (not final results)."""
import argparse, gzip, json, math, os, pathlib, re, shutil, signal, statistics, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BENCH_PIN = "3da9671"      # frozen bench 1.8.0 (cases/expected identical to 0969967), 326 cases
BENCH_PIN_VERSION, BENCH_PIN_CASES = "1.8.0", 326
BENCH = ROOT               # replaced in main() by the pinned snapshot (work-dir/bench-<sha>)
DATASET = "/workspace/exct-eve/data/dataset-3569502.json.gz"
LAB = "https://github.com/EX-CT/eve-dogma-lab"
REF = "https://github.com/EX-CT/eve-dogma-rs"
LETTERS = "ABCDEFGHIJK"
A_MANIFEST = {"build": "cargo build --release", "cmd": "./target/release/eve-dogma --dataset {dataset} calc",
              "batch_cmd": "./target/release/eve-dogma --dataset {dataset} batch",
              "rpc_cmd": "./target/release/eve-dogma --dataset {dataset} serve-stdio"}
W = dict(speed=0.40, maint=0.35, feat=0.15, port=0.10)
SPEED_W = dict(latency=0.5, throughput=0.3, cold=0.2)
MAINT_W = dict(tests=0.25, data=0.20, size=0.20, docs=0.15, deps=0.10, build=0.10)

ENV = dict(os.environ)
_dn = pathlib.Path.home() / ".dotnet"
if _dn.exists():
    ENV["PATH"] = f"{_dn}:{ENV['PATH']}"; ENV.setdefault("DOTNET_ROOT", str(_dn))
ENV.update(DOTNET_CLI_TELEMETRY_OPTOUT="1", DOTNET_NOLOGO="1")


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def sh(cmd, cwd, timeout, env=None, inp=None):
    """Run in its own process group; kill the whole group on timeout. -> (rc|None, seconds, output tail)."""
    t0 = time.time()
    p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         stdin=subprocess.PIPE if inp is not None else subprocess.DEVNULL, text=True,
                         start_new_session=True, env=env or ENV)
    try:
        out, _ = p.communicate(inp, timeout=timeout)
        return p.returncode, time.time() - t0, out
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out = p.communicate()[0] or ""
        return None, time.time() - t0, out + f"\n[timeout after {timeout}s]"


def load3():
    return [round(x, 2) for x in os.getloadavg()]


def L(x, best, span):
    if x is None or best is None or x <= 0 or best <= 0:
        return 0.0
    return max(0.0, min(1.0, 1 - math.log10(x / best) / math.log10(span)))


# ---------------------------------------------------------------- fetch / build
def fetch(letter, work, fresh, no_fetch, as_of=None):
    d = work / letter
    url, br, sub = (REF, "main", "") if letter == "A" else (LAB, f"variant-{letter.lower()}", f"variant-{letter.lower()}")
    if fresh and d.exists():
        shutil.rmtree(d)
    first = not d.exists()
    if first:
        rc, _, out = sh(f"git clone -q --depth 1 -b {br} {url} {d}", work, 600)
        if rc != 0:
            return None, {"url": url, "branch": br, "error": out[-500:]}
    git = lambda c: subprocess.run(c, shell=True, cwd=d, capture_output=True, text=True, env=ENV).stdout.strip()  # noqa: E731
    head = None
    if no_fetch:
        rc, out = 0, ""
    elif as_of:  # need history back to the cutoff: deepen by date (fallback: full history of this branch)
        since = time.strftime("%Y-%m-%d", time.gmtime(as_of - 7 * 86400))
        rc, _, out = sh(f"git fetch -q --shallow-since={since} origin {br} || git fetch -q --unshallow origin {br} || git fetch -q origin {br}", d, 600)
    else:
        rc, _, out = sh(f"git fetch -q --depth 1 origin {br}", d, 600)
    if rc != 0:
        return None, {"url": url, "branch": br, "error": out[-500:]}
    if not no_fetch:
        head = git("git rev-parse FETCH_HEAD")
        target = head
        if as_of:
            target = git(f"git rev-list -1 --first-parent --before={int(as_of)} FETCH_HEAD")
            if not target:
                return None, {"url": url, "branch": br, "head": head, "error": f"no commit at or before --as-of on {br}"}
        rc, _, out = sh(f"git reset -q --hard {target}", d, 120)
        if rc != 0:
            return None, {"url": url, "branch": br, "error": out[-500:]}
    sha = git("git rev-parse HEAD")
    when = git("git log -1 --format=%cI")
    return d / sub, {"url": url, "branch": br, "sha": sha, "commit_time": when, "branch_head_at_fetch": head or sha,
                     "is_branch_head": (head or sha) == sha, "fresh_clone": first}


def manifest(letter, vd):
    if letter == "A":
        return dict(A_MANIFEST)
    import yaml
    f = vd / "bench.yaml"
    return yaml.safe_load(open(f)) if f.exists() else None


# ---------------------------------------------------------------- bench runs (child process)
def child(spec):
    sys.path.insert(0, spec.pop("_bench"))
    import run
    a = run.Args(**spec)
    run.evaluate(a)


def bench_run(letter, m, vd, i, a, tag):
    name = f"_eval/{tag}/{letter}/run{i}"
    spec = dict(_bench=str(BENCH), name=name, cmd=m["cmd"], batch_cmd=m.get("batch_cmd"), cwd=str(vd), cases="cases/*.json",
                timeout=a.case_timeout, batch_repeat=1 if a.quick else 5, latency_n=100 if a.quick else 500)
    before = load3()
    rc, dt, out = sh(f"{shlex_q(sys.executable)} {shlex_q(__file__)} --_child {shlex_q(json.dumps(spec))}", ROOT,
                     a.remaining(), inp=None)
    after = load3()
    card_f = BENCH / "results" / name / "scorecard.json"
    res = {"run": i, "wall_s": round(dt, 1), "loadavg_before": before, "loadavg_after": after}
    if rc is None:
        res["error"] = "timeout"
    elif rc != 0 or not card_f.exists():
        res["error"] = f"exit {rc}: {out[-600:]}"
    else:
        c = json.loads(card_f.read_text())
        p = c["perf"]
        res.update(cases=c["cases"], cases_ok=c["cases_fully_correct"], values_ok=c["values_correct"],
                   values_total=c["values_total"], errors=c["errors"],
                   latency_ms=p.get("latency_one_fit", {}).get("per_calc_ms"),
                   fits_per_s=p.get("batch_corpus", {}).get("fits_per_s"),
                   batch_responses=p.get("batch_corpus", {}).get("responses"),
                   cold_ms=p["single_process_per_case_ms"]["median"], deterministic=p.get("deterministic"),
                   groups=c["groups"])
        shutil.copytree(BENCH / "results" / name, a.out / "raw" / letter / f"run{i}", dirs_exist_ok=True)
    return res


def shlex_q(s):
    import shlex
    return shlex.quote(str(s))


# ---------------------------------------------------------------- bench pin
def pin_bench(work, ref):
    """Extract cases/, expected/, run.py, tools/ … of bench commit `ref` into work/bench-<sha> (read-only use)."""
    git = lambda c: subprocess.run(c, shell=True, cwd=ROOT, capture_output=True, text=True)  # noqa: E731
    if git(f"git cat-file -e {ref}^{{commit}}").returncode:
        git(f"git fetch -q origin {ref} || git fetch -q --unshallow origin || git fetch -q origin")
    sha = git(f"git rev-parse {ref}^{{commit}}").stdout.strip()
    if not sha:
        sys.exit(f"bench ref {ref} not found")
    d = work / f"bench-{sha[:12]}"
    if not (d / "run.py").exists():
        tmp = work / f".bench-{sha[:12]}.tmp"
        shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
        r = subprocess.run(f"git archive {sha} | tar -x -C {shlex_q(tmp)}", shell=True, cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"git archive {sha} failed: {r.stderr}")
        tmp.rename(d)
    n = sum(1 for p in (d / "cases").glob("*.json") if (d / "expected" / p.name).exists())
    ver = (d / "VERSION").read_text().strip() if (d / "VERSION").exists() else "?"
    if ref == BENCH_PIN and (ver != BENCH_PIN_VERSION or n != BENCH_PIN_CASES):
        sys.exit(f"pinned bench mismatch: version {ver}, {n} cases (expected {BENCH_PIN_VERSION}, {BENCH_PIN_CASES})")
    return d, {"ref": ref, "sha": sha, "version": ver, "cases": n, "dir": str(d)}


# ---------------------------------------------------------------- latency (own measurement, not run.py's)
LAT_FLOOR_MS = 0.002     # 2 µs: below any real FitRequest parse + dogma + FitStats JSON; smaller = measurement artefact
LAT_SPREAD_MAX = 0.5     # (max − min) / median of valid samples above this => re-measure, then flag


def timed_batch(cmd, cwd, inp_path, timeout, cpu=None):
    """Wall time of one batch process reading inp_path; stdout streamed and only newline-counted."""
    import threading
    if cpu is not None and shutil.which("taskset"):
        cmd = f"taskset -c {cpu} sh -c {shlex_q(cmd)}"
    with open(inp_path, "rb") as f:
        t0 = time.perf_counter()
        p = subprocess.Popen(cmd, shell=True, cwd=cwd, stdin=f, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             start_new_session=True, env=ENV)
        n = [0]
        def rd():
            while True:
                b = p.stdout.read(1 << 20)
                if not b:
                    break
                n[0] += b.count(b"\n")
        th = threading.Thread(target=rd, daemon=True); th.start()
        try:
            p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL); p.wait(); th.join(5)
            return None, n[0], None
        th.join(30)
        return time.perf_counter() - t0, n[0], p.returncode


def measure_latency(batch_cmd, vd, a, work):
    """Single-core per-calc latency of one fit (case exct_rifter): run the batch command pinned to ONE cpu
    (taskset; so multi-threaded batch modes measure latency, not throughput), with 1 request (startup, median of 3)
    and with N requests (N sized so the calc part takes ≈0.5 s, 200..10000). sample = (t_N − t_1) / (N − 1).
    A sample is invalid if ≤ 0, below LAT_FLOOR_MS, above the upper bound t_N / N, or if responses != requests.
    Median of valid samples; if spread > LAT_SPREAD_MAX or < 3 valid, up to 3 extra samples, then flagged.
    No valid sample => fall back to median t_N / N (upper bound, flagged)."""
    req = json.dumps(json.loads((BENCH / "cases" / "exct_rifter.json").read_text())) + "\n"
    tmpd = work / ".lat"; tmpd.mkdir(exist_ok=True)
    def inp(n):
        f = tmpd / f"in{n}.jsonl"
        if not f.exists():
            f.write_text(req * n)
        return f
    ncpu = os.cpu_count() or 1
    to = max(60, a.case_timeout * 10)
    flags, samples = [], []
    def one(n, cpu):
        t, k, rc = timed_batch(batch_cmd, str(vd), inp(n), to, cpu)
        return (t if (t is not None and k == n and rc == 0) else None), k, rc
    # pilot
    t1s = [one(1, 0)[0] for _ in range(3)]
    t1s = [t for t in t1s if t is not None]
    tp, kp, rcp = one(200, 0)
    if not t1s or tp is None:
        return {"latency_ms": None, "flags": [f"batch failed (responses {kp}/200, rc {rcp})"], "samples": []}
    t1 = statistics.median(t1s)
    est = (tp - t1) / 199 if tp > t1 else tp / 200
    N = int(max(200, min(10000, 0.5 / max(est, 1e-7))))
    k = 0
    while k < a.latency_samples + 3:
        cpu = (k + 1) % ncpu
        t1k = [x for x in (one(1, cpu)[0] for _ in range(3)) if x is not None]
        tN, got, rc = one(N, cpu)
        smp = {"cpu": cpu, "n": N, "load1": load3()[0]}
        if not t1k or tN is None:
            smp.update(valid=False, why=f"run failed (responses {got}/{N}, rc {rc})")
        else:
            t1m = statistics.median(t1k)
            lat = (tN - t1m) / (N - 1) * 1000
            ub = tN / N * 1000
            smp.update(t1_ms=round(t1m * 1000, 2), tN_s=round(tN, 4), ms=lat, upper_ms=ub)
            if lat <= 0:
                smp.update(valid=False, why="non-positive differencing")
            elif lat < LAT_FLOOR_MS:
                smp.update(valid=False, why=f"below physical floor {LAT_FLOOR_MS} ms")
            elif lat > ub * 1.001:
                smp.update(valid=False, why="above upper bound t_N/N")
            else:
                smp["valid"] = True
        samples.append(smp); k += 1
        v = [x["ms"] for x in samples if x.get("valid")]
        if k >= a.latency_samples and len(v) >= 3 and (max(v) - min(v)) / statistics.median(v) <= LAT_SPREAD_MAX:
            break
    v = [x["ms"] for x in samples if x.get("valid")]
    bad = [x for x in samples if not x.get("valid")]
    if bad:
        flags.append(f"{len(bad)} invalid sample(s): " + "; ".join(sorted({x['why'] for x in bad})))
    if v:
        lat = statistics.median(v)
        spread = (max(v) - min(v)) / lat
        if len(v) < 3:
            flags.append(f"only {len(v)} valid sample(s)")
        if spread > LAT_SPREAD_MAX:
            flags.append(f"high spread {spread:.0%} after re-measuring")
        if len(samples) > a.latency_samples:
            flags.append(f"re-measured ({len(samples)} samples)")
    else:
        ubs = [x["upper_ms"] for x in samples if "upper_ms" in x]
        lat = statistics.median(ubs) if ubs else None; spread = None
        flags.append("no valid differencing sample: using upper bound t_N/N")
    return {"latency_ms": lat, "median_ms": lat, "min_ms": min(v) if v else None, "max_ms": max(v) if v else None,
            "spread": spread, "valid": len(v), "n_samples": len(samples), "n_per_sample": N, "startup_ms": round(t1 * 1000, 2),
            "pinned_single_cpu": bool(shutil.which("taskset")), "flags": flags, "samples": samples}


# ---------------------------------------------------------------- RPC feature probes
def rpc(cmd, cwd, reqs, timeout=120):
    inp = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in reqs)
    rc, dt, out = sh(cmd, cwd, timeout, inp=inp)
    got = {}
    for line in (out or "").splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if isinstance(o, dict) and "id" in o:
            got[o["id"]] = o
    return got, rc


def _mods(fit):
    ms = fit.get("modules") or []
    return sorted((m.get("type_id"), m.get("charge_type_id")) for m in ms if isinstance(m, dict))


def features(m, vd, a):
    res = {}
    rc_cmd = m.get("rpc_cmd")
    if not rc_cmd:
        return {"eft": 0.0, "rpc": 0.0, "search": 0.0, "type": 0.0, "detail": "no rpc_cmd in manifest"}
    # EFT export (official informational check)
    try:
        import importlib.util
        spec_ = importlib.util.spec_from_file_location("cee_pinned", BENCH / "tools" / "check_eft_export.py")
        cee = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(cee)
        ex = cee.check(rc_cmd, cwd=str(vd), timeout=a.case_timeout * 30)
        res["eft_export"] = {"ok": ex["ok"], "total": ex["total"]}
        exp_frac = ex["ok"] / ex["total"]
    except Exception as e:  # noqa: BLE001
        res["eft_export"] = {"error": repr(e)[:300]}; exp_frac = 0.0
    exp = [json.loads(l) for l in open(BENCH / "expected_extra/eft_export.jsonl")]
    step = max(1, len(exp) // 20)
    sample = exp[::step][:20]
    cases = ["exct_rifter", sorted(p.stem for p in (BENCH / "cases").glob("*.json"))[0],
             sorted(p.stem for p in (BENCH / "cases").glob("*.json"))[-1]]
    reqs = [{"id": 1000 + k, "method": "eft_parse", "params": {"text": e["text"]}} for k, e in enumerate(sample)]
    reqs += [{"id": 2000 + k, "method": "calc", "params": json.loads((BENCH / "cases" / f"{c}.json").read_text())}
             for k, c in enumerate(cases)]
    reqs += [{"id": 3000, "method": "meta", "params": {}}, {"id": 3001, "method": "no_such_method", "params": {}}]
    sq = [("Rifter", None, None), ("裂谷", None, None), ("Raven", None, None), ("Hammerhead", ["drone"], None),
          ("Shield", None, None), ("Shield", None, 5)]
    for k, (q, kinds, lim) in enumerate(sq):
        p = {"query": q}
        if kinds: p["kinds"] = kinds
        if lim: p["limit"] = lim
        reqs.append({"id": 4000 + k, "method": "search", "params": p})
    reqs += [{"id": 5000, "method": "type", "params": {"id": 587}}, {"id": 5001, "method": "type", "params": {"id": "Rifter"}},
             {"id": 5002, "method": "type", "params": {"id": 999999999}}]
    got, _ = rpc(rc_cmd, str(vd), reqs, timeout=max(60, a.case_timeout * 6))
    R = lambda i: got.get(i, {}).get("result")  # noqa: E731
    # eft_parse round-trip
    ok = 0
    for k, e in enumerate(sample):
        r = R(1000 + k)
        if isinstance(r, dict) and "error" not in r:
            ship = (r.get("ship") or {}).get("type_id") if isinstance(r.get("ship"), dict) else r.get("ship")
            if ship == e["fit"]["ship"]["type_id"] and _mods(r) == _mods(e["fit"]):
                ok += 1
    res["eft_parse"] = {"ok": ok, "total": len(sample)}
    eft = 0.5 * exp_frac + 0.5 * ok / len(sample)
    # rpc
    checks = []
    for k, c in enumerate(cases):
        cli_rc, _, cli_out = sh(m["cmd"], str(vd), a.case_timeout * 3, inp=(BENCH / "cases" / f"{c}.json").read_text())
        try:
            checks.append(json.loads(cli_out) == R(2000 + k))
        except ValueError:
            checks.append(False)
    meta = R(3000)
    checks.append(isinstance(meta, dict) and meta.get("sde_build") == 3569502)
    um = got.get(3001, {})
    err = (um.get("result") or {}).get("error") if isinstance(um.get("result"), dict) else um.get("error")
    checks.append(isinstance(err, dict) and err.get("code") == "UNKNOWN_METHOD")
    checks.append(all(i in got for i in (2000, 3000, 3001)))
    res["rpc_checks"] = checks
    rpc_s = sum(map(bool, checks)) / len(checks)
    # search (interim spec, CONTRACT.md)
    def first(i):
        r = R(i); return r[0] if isinstance(r, list) and r else {}
    s = [first(4000).get("type_id") == 587 and first(4000).get("match") == "exact",
         any(isinstance(x, dict) and x.get("type_id") == 587 for x in (R(4001) or [])),
         first(4002).get("type_id") == 638 and first(4002).get("match") == "exact",
         bool(R(4003)) and all(isinstance(x, dict) and x.get("kind") == "drone" for x in R(4003)),
         isinstance(R(4004), list) and len(R(4004)) == 20 and
         all({"type_id", "name", "name_zh", "group", "category_id", "kind", "match"} <= set(x) for x in R(4004)),
         isinstance(R(4005), list) and len(R(4005)) == 5]
    res["search_checks"] = s
    # type
    def is_rifter(r):
        return isinstance(r, dict) and "error" not in r and (r.get("type_id") == 587 or r.get("id") == 587 or r.get("name") == "Rifter")
    t3 = R(5002)
    def err_code(i):
        o = got.get(i, {}); e = (o.get("result") or {}).get("error") if isinstance(o.get("result"), dict) else o.get("error")
        return e.get("code") if isinstance(e, dict) else None
    # unknown id must give an error, but "method not implemented" does not count
    t = [is_rifter(R(5000)), is_rifter(R(5001)),
         ((isinstance(t3, dict) and "error" in t3) or (5002 in got and "error" in got[5002])) and err_code(5002) != "UNKNOWN_METHOD"]
    res["type_checks"] = t
    res.update(eft=round(eft, 4), rpc=round(rpc_s, 4), search=round(sum(s) / len(s), 4), type=round(sum(t) / len(t), 4))
    return res


# ---------------------------------------------------------------- static maintainability metrics
CODE_EXT = {".rs": "Rust", ".go": "Go", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".mjs": "JavaScript",
            ".cjs": "JavaScript", ".py": "Python", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++", ".h": "C/C++ header",
            ".cs": "C#", ".kt": "Kotlin", ".java": "Java", ".sh": "Shell", ".cmake": "CMake"}
SKIP_DIRS = {"target", "build", "node_modules", "bin", "obj", "dist", "dist-cli", ".git", ".cache", "__pycache__", "results",
             "bench-results", "scorecards", "out", ".venv"}
VENDOR_DIRS = {"vendor", "third_party", "third-party", "external", "deps"}
TOOL_DIRS = {"tools", "oracle", "bench", "scripts", "examples", "benches", "fixtures", "web"}
TEST_RE = re.compile(r"(^|/)(tests?|testdata|__tests__|spec)(/|$)|_test\.go$|(^|/)test_[^/]*\.py$|_test\.py$|\.test\.[jt]s$|\.spec\.[jt]s$|Tests?\.cs$|Tests?/|_test\.(cpp|cc)$")
TEST_PAT = {"Rust": r"#\[test\]", "Go": r"^func Test\w*\(", "TypeScript": r"^\s*(?:it|test)\(", "JavaScript": r"^\s*(?:it|test)\(",
            "Python": r"^\s*def test_\w*\(", "C++": r"\b(?:TEST|TEST_F|TEST_CASE|SCENARIO)\(", "C#": r"\[(?:Fact|Theory|Test|TestMethod)\b"}


def comment_prefix(lang):
    return ("#",) if lang in ("Python", "Shell", "CMake") else ("//", "/*", "*", "*/")


def walk(vd):
    for p in sorted(vd.rglob("*")):
        rel = p.relative_to(vd).as_posix()
        parts = rel.split("/")
        if any(x in SKIP_DIRS or (x.startswith(".") and x not in (".",)) for x in parts[:-1]):
            continue
        if p.is_file():
            yield p, rel, parts


def classify(rel, parts, head):
    if any(x in VENDOR_DIRS for x in parts[:-1]):
        return "vendored"
    if "generated" in rel or re.search(r"@generated|DO NOT EDIT|auto-?generated|generated by", head, re.I):
        return "generated"
    if TEST_RE.search(rel):
        return "test"
    if parts[0] in TOOL_DIRS or (len(parts) == 1 and parts[0].endswith(".py") and not parts[0].startswith("eve")):
        return "tooling"
    return "core"


def static_metrics(letter, vd, effect_names, n_mod_effects):
    loc, tests_static, core_text = {}, 0, []
    gen_loc = vend_loc = 0
    for p, rel, parts in walk(vd):
        lang = "CMake" if p.name == "CMakeLists.txt" else CODE_EXT.get(p.suffix)
        if not lang:
            continue
        try:
            txt = p.read_text(errors="replace")
        except OSError:
            continue
        if len(txt) > 3_000_000:  # data blobs masquerading as code
            continue
        kind = classify(rel, parts, txt[:600])
        cp = comment_prefix(lang)
        n = sum(1 for l in txt.splitlines() if l.strip() and not l.strip().startswith(cp))
        e = loc.setdefault(kind, {}); e[lang] = e.get(lang, 0) + n
        if lang in TEST_PAT:
            tests_static += len(re.findall(TEST_PAT[lang], txt, re.M))
        if kind == "core":
            core_text.append(txt)
    core = sum(loc.get("core", {}).values())
    blob = "\n".join(core_text)
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{7,}", blob))
    hard = sorted(n for n in effect_names if n in words)
    # docs / license
    docs_dir = vd / "docs"
    design = (vd / "DESIGN.md").exists() or any(docs_dir.glob("design*")) or any(docs_dir.glob("architecture*")) if docs_dir.exists() else (vd / "DESIGN.md").exists()
    lic = license_id(vd)
    lic_files = lic["files"]
    return {"loc": loc, "core_loc": core, "test_count_static": tests_static,
            "hardcoded_effects": len(hard), "hardcoded_effect_names_sample": hard[:40],
            "data_driven_ratio": round(1 - len(hard) / n_mod_effects, 4),
            "docs": {"readme": (vd / "README.md").exists(), "design": bool(design), "license_file": bool(lic_files)},
            "license": lic, "deps": deps(vd), "loc_tool": "builtin"}


SPDX_RE = re.compile(r"\b((?:L?GPL|AGPL)-[23]\.[01](?:-or-later|-only|\+)?|MIT|Apache-2\.0|BSD-[23]-Clause|MPL-2\.0|ISC|Zlib|Unlicense)\b")
PERMISSIVE = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Zlib", "Unlicense", "MPL-2.0")


def license_files(vd):
    """LICENSE*/COPYING* in the variant dir and, for lab variants, the branch root (vd's git top level)."""
    dirs = [vd]
    top = subprocess.run("git rev-parse --show-toplevel", shell=True, cwd=vd, capture_output=True, text=True).stdout.strip()
    if top and pathlib.Path(top).resolve() != vd.resolve():
        dirs.append(pathlib.Path(top))
    out = []
    for d in dirs:
        for x in sorted(list(d.glob("LICENSE*")) + list(d.glob("COPYING*"))):
            if x.is_file():
                out.append(x)
    return out


def _kind(text):
    head = text[:1500].upper()
    if "GNU LESSER GENERAL PUBLIC LICENSE" in head:
        return "LGPL-3" if "VERSION 3" in head else "LGPL-2.1" if "VERSION 2.1" in head else "LGPL"
    if "GNU AFFERO GENERAL PUBLIC LICENSE" in head:
        return "AGPL-3"
    if "GNU GENERAL PUBLIC LICENSE" in head:
        return "GPL-3" if "VERSION 3" in head else "GPL-2" if "VERSION 2" in head else "GPL"
    if "PERMISSION IS HEREBY GRANTED, FREE OF CHARGE" in text.upper():
        return "MIT"
    if "APACHE LICENSE" in head and "VERSION 2.0" in head:
        return "Apache-2.0"
    if "MOZILLA PUBLIC LICENSE" in head:
        return "MPL-2.0"
    if "REDISTRIBUTION AND USE IN SOURCE AND BINARY FORMS" in text.upper():
        return "BSD"
    return "unrecognised"


def license_id(vd, files=None):
    """Judge the license by the actual LICENSE texts (variant dir + branch root, full text): an LGPL header (+ the
    companion GPL text LGPLv3 requires) => LGPL; a GPL header without any LGPL text => GPL; MIT/Apache/... by text.
    SPDX package metadata / README "License" section are used ONLY to refine the version qualifier (-only/-or-later)
    and to detect conflicts."""
    fl = license_files(vd)
    root = vd
    kinds = {}
    for x in fl:
        try:
            rel = x.relative_to(vd).as_posix()
        except ValueError:
            rel = "<branch root>/" + x.name
        kinds[rel] = _kind(x.read_text(errors="replace"))
    ks = set(kinds.values())
    lgpl = sorted(k for k in ks if k.startswith("LGPL"))
    gpl = sorted(k for k in ks if k.startswith(("GPL", "AGPL")))
    if lgpl:
        base, companion = lgpl[0], bool(gpl)
    elif gpl:
        base, companion = gpl[0], False
    else:
        perm = sorted(k for k in ks if k != "unrecognised")
        base, companion = (perm[0] if perm else ("unrecognised" if ks else None)), False
    decl = []
    for mf, pat in (("Cargo.toml", r'^license\s*=\s*"([^"]+)"'), ("package.json", r'"license"\s*:\s*"([^"]+)"')):
        if (root / mf).exists():
            decl += re.findall(pat, (root / mf).read_text(), re.M)
    for x in root.rglob("*.csproj"):
        if not any(s in x.parts for s in SKIP_DIRS):
            decl += re.findall(r"<PackageLicenseExpression>([^<]+)<", x.read_text())
    readme = None
    if (root / "README.md").exists():
        mt = re.search(r"^#+\s*Licen[cs]e.*?$(.*?)(?=^#|\Z)", (root / "README.md").read_text(errors="replace"), re.M | re.S | re.I)
        if mt:
            rm = SPDX_RE.search(mt.group(1)); readme = rm.group(1) if rm else None
    lic = {"files": [f"{k} ({v})" for k, v in kinds.items()], "file_license": base, "gpl_companion_text": companion,
           "declared": sorted(set(decl)), "readme": readme}
    # refine qualifier
    eff, qual_src = base, None
    if base and base not in ("unrecognised",) and re.match(r"(A?L?GPL)-\d", base):
        stem = base  # e.g. LGPL-3
        for src, cands in (("package metadata", lic["declared"]), ("README", [readme] if readme else [])):
            for c in cands:
                c2 = c.replace("+", "-or-later")
                if c2.startswith(stem + ".") and c2.split(".")[0] == stem.split(".")[0]:
                    if c2.startswith(stem):
                        eff, qual_src = c2, src; break
            if qual_src:
                break
        if not qual_src:
            eff = stem + ".0" if not stem.endswith(".1") else stem
    lic["effective"], lic["qualifier_source"] = eff, qual_src
    # conflicts between files and metadata/README
    claims = [c for c in lic["declared"] + ([readme] if readme else [])]
    fam = lambda x: re.match(r"(AGPL|LGPL|GPL|MIT|Apache|BSD|MPL)", x).group(1) if x and re.match(r"(AGPL|LGPL|GPL|MIT|Apache|BSD|MPL)", x) else None  # noqa: E731
    lic["conflicts"] = sorted({c for c in claims if base and fam(c) and fam(base) and fam(c) != fam(base)})
    return mergeable(lic)


def mergeable(lic):
    """Mergeable into the LGPL-3.0-or-later mainline (eve-dogma-rs)?"""
    eff = lic["effective"]
    if not eff:
        lic["mergeable"] = "unknown"
        lic["reason"] = "no LICENSE file in variant dir or branch root" + (f" (README says {lic['readme']})" if lic.get("readme") else "")
    elif eff == "unrecognised":
        lic["mergeable"], lic["reason"] = "unknown", "LICENSE text not recognised"
    elif lic["conflicts"]:
        lic["mergeable"], lic["reason"] = "unknown", f"LICENSE file is {eff} but metadata/README claim {', '.join(lic['conflicts'])}"
    elif re.match(r"A?GPL", eff):
        lic["mergeable"], lic["reason"] = "no", f"{eff} (LICENSE text, no LGPL) is stronger copyleft; cannot be relicensed into LGPL-3.0-or-later"
    elif eff.startswith("LGPL-3"):
        q = "" if lic["qualifier_source"] else " (no -only/-or-later statement in metadata/README; treated as LGPL-3.0)"
        only = "; -only: the combined work would be LGPL-3.0-only" if eff.endswith("-only") else ""
        lic["mergeable"] = "yes"
        lic["reason"] = f"LGPL v3 LICENSE text{' + GPL companion text' if lic['gpl_companion_text'] else ''}{q}{only}"
    elif eff.startswith("LGPL-2.1"):
        lic["mergeable"], lic["reason"] = "yes", "LGPL-2.1 (or-later) can be upgraded to LGPL-3" if "later" in eff else "unknown: LGPL-2.1-only"
        if "later" not in eff:
            lic["mergeable"] = "unknown"
    elif eff in PERMISSIVE or eff == "BSD":
        lic["mergeable"], lic["reason"] = "yes", f"permissive ({eff})"
    else:
        lic["mergeable"], lic["reason"] = "unknown", f"unrecognised license {eff}"
    return lic


def deps(vd):
    out = {"runtime": [], "dev": [], "build": []}
    ct = vd / "Cargo.toml"
    if ct.exists():
        import tomllib
        t = tomllib.loads(ct.read_text())
        out["runtime"] += list(t.get("dependencies", {}))
        for tv in t.get("target", {}).values():
            out["runtime"] += list(tv.get("dependencies", {}))
        out["dev"] += list(t.get("dev-dependencies", {})); out["build"] += list(t.get("build-dependencies", {}))
    gm = vd / "go.mod"
    if gm.exists():
        txt = gm.read_text()
        blk = re.findall(r"require\s*\((.*?)\)", txt, re.S)
        lines = [l for b in blk for l in b.splitlines()] + re.findall(r"^require\s+(\S+\s+\S+.*)$", txt, re.M)
        out["runtime"] += [l.split()[0] for l in lines if l.strip() and "// indirect" not in l]
    pj = vd / "package.json"
    if pj.exists():
        j = json.loads(pj.read_text())
        out["runtime"] += list(j.get("dependencies", {})); out["dev"] += list(j.get("devDependencies", {}))
    for x in vd.rglob("*.csproj"):
        if any(s in x.parts for s in SKIP_DIRS):
            continue
        out["runtime"] += re.findall(r'<PackageReference\s+Include="([^"]+)"', x.read_text())
    cm = vd / "CMakeLists.txt"
    if cm.exists():
        txt = cm.read_text()
        fp = [n for n in re.findall(r"find_package\(\s*(\w+)", txt) if n not in ("Threads",)]
        fc = re.findall(r"FetchContent_Declare\(\s*(\w+)", txt) + re.findall(r"ExternalProject_Add\(\s*(\w+)", txt)
        out["runtime"] += sorted(set(fp + fc))
        for vdir in VENDOR_DIRS:
            if (vd / vdir).is_dir():
                out["runtime"] += [f"{vdir}/{x.name}" for x in (vd / vdir).iterdir() if x.is_dir() and x.name.lower() not in {n.lower() for n in fp + fc}]
    if not any(out.values()) and any(vd.rglob("*.py")):
        std = set(sys.stdlib_module_names)
        own = {p.name for p in vd.iterdir() if p.is_dir()} | {p.stem for p in vd.glob("*.py")}
        imps = set()
        for p, rel, parts in walk(vd):
            if p.suffix == ".py" and classify(rel, parts, "") == "core":
                imps |= set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", p.read_text(errors="replace"), re.M))
        out["runtime"] += sorted(i for i in imps if i not in std and i not in own and i != "__future__")
    if (vd / "vendor").is_dir() and ct.exists():
        out["vendored"] = sorted(x.name for x in (vd / "vendor").iterdir())
    out = {k: sorted(set(v)) for k, v in out.items()}
    out["n_runtime"] = len(out["runtime"])
    return out


# ---------------------------------------------------------------- own test suites
def test_command(m, vd):
    if m.get("test"):
        return m["test"], "manifest"
    if (vd / "Cargo.toml").exists():
        return "cargo test --release 2>&1", "cargo"
    if (vd / "go.mod").exists():
        return "go test -v ./... 2>&1", "go"
    if (vd / "package.json").exists() and "test" in json.loads((vd / "package.json").read_text()).get("scripts", {}):
        return "npm test --silent 2>&1", "npm"
    if (vd / "CMakeLists.txt").exists() and "add_test" in (vd / "CMakeLists.txt").read_text():
        return "ctest --test-dir build --output-on-failure 2>&1", "ctest"
    tp = [x for x in vd.rglob("*.csproj") if re.search(r"test", x.name, re.I) and not any(s in x.parts for s in SKIP_DIRS)]
    if tp:
        return f"dotnet test {tp[0].relative_to(vd)} --nologo 2>&1", "dotnet"
    for scr in ("tests/run_tests.py", "tests/run.py", "test/run_tests.py"):
        if (vd / scr).exists():
            return f"{sys.executable} {scr} 2>&1", "script"
    if (vd / "tests").is_dir() and any((vd / "tests").glob("test*.py")):
        try:
            import pytest  # noqa: F401
            return f"{sys.executable} -m pytest -q tests 2>&1", "pytest"
        except ImportError:
            return f"{sys.executable} -m unittest discover -s tests -v 2>&1", "unittest"
    return None, None


def parse_tests(kind, out):
    p = f = None
    if kind == "cargo":
        rs = re.findall(r"test result: \w+\. (\d+) passed; (\d+) failed", out)
        if rs: p, f = sum(int(a) for a, _ in rs), sum(int(b) for _, b in rs)
    elif kind == "go":
        p, f = len(re.findall(r"^\s*--- PASS", out, re.M)), len(re.findall(r"^\s*--- FAIL", out, re.M))
    elif kind == "ctest":
        r = re.search(r"(\d+) tests failed out of (\d+)", out)
        if r: f = int(r.group(1)); p = int(r.group(2)) - f
    elif kind in ("unittest",):
        r = re.search(r"Ran (\d+) tests?", out)
        if r:
            n = int(r.group(1)); fm = re.search(r"FAILED \((?:failures=(\d+))?(?:, )?(?:errors=(\d+))?", out)
            f = sum(int(x or 0) for x in fm.groups()) if fm else 0; p = n - f
    elif kind == "pytest":
        r1, r2 = re.search(r"(\d+) passed", out), re.search(r"(\d+) failed", out)
        p, f = int(r1.group(1)) if r1 else 0, int(r2.group(1)) if r2 else 0
    else:  # npm (node:test / jest / mocha / vitest) or manifest
        for pat_p, pat_f in ((r"^# pass (\d+)", r"^# fail (\d+)"), (r"Tests:.*?(\d+) passed", r"Tests:.*?(\d+) failed"),
                             (r"(\d+) passing", r"(\d+) failing"), (r"ℹ pass (\d+)", r"ℹ fail (\d+)"), (r"(\d+) passed", r"(\d+) failed")):
            r1 = re.search(pat_p, out, re.M)
            if r1:
                r2 = re.search(pat_f, out, re.M); p, f = int(r1.group(1)), int(r2.group(1)) if r2 else 0; break
        if kind == "dotnet":
            r = re.search(r"Passed:\s*(\d+)", out); r2 = re.search(r"Failed:\s*(\d+)", out)
            if r: p, f = int(r.group(1)), int(r2.group(1)) if r2 else 0
    return p, f


def run_tests(m, vd, timeout):
    cmd, kind = test_command(m, vd)
    if not cmd:
        return {"found": False}
    cmd = cmd.format(dataset=DATASET, bench=BENCH, dir=vd)
    env = dict(ENV, EVE_DOGMA_DATASET=DATASET)
    rc, dt, out = sh(cmd, str(vd), timeout, env=env)
    p, f = parse_tests(kind, out or "")
    st = "timeout" if rc is None else ("passed" if rc == 0 and not f else "failed")
    return {"found": True, "cmd": cmd, "runner": kind, "status": st, "rc": rc, "passed": p, "failed": f,
            "seconds": round(dt, 1), "tail": (out or "")[-600:] if st != "passed" else ""}


# ---------------------------------------------------------------- portability heuristic
WASM_CODE = re.compile(r"wasm-bindgen|wasm_bindgen|wasm32|emscripten|EMSCRIPTEN|emcmake|pyodide|DecompressionStream|tsconfig\.browser|wasm-pack|<script type=\"module\"")
WASM_DOC = re.compile(r"\bWASM\b|WebAssembly|\bbrowser\b|浏览器", re.I)


def portability(vd):
    ev = []
    for p, rel, parts in walk(vd):
        if p.suffix in (".md",) or p.stat().st_size > 2_000_000:
            continue
        if p.suffix in CODE_EXT or p.name in ("Cargo.toml", "package.json", "CMakeLists.txt", "go.mod") or p.suffix in (".json", ".toml", ".html", ".csproj", ".yaml", ".yml"):
            try:
                t = p.read_text(errors="replace")
            except OSError:
                continue
            for mt in set(WASM_CODE.findall(t)):
                ev.append(f"{rel}: {mt}")
    if ev:
        return {"score": 1.0, "level": "code", "evidence": sorted(set(ev))[:12]}
    docs = " ".join((vd / f).read_text(errors="replace") for f in ("README.md", "DESIGN.md") if (vd / f).exists())
    if WASM_DOC.search(docs):
        return {"score": 0.5, "level": "docs-only", "evidence": sorted(set(WASM_DOC.findall(docs)))[:5]}
    return {"score": 0.0, "level": "none", "evidence": []}


# ---------------------------------------------------------------- scoring + output
def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def score_all(rows):
    ranked = [r for r in rows if r.get("gate") == "pass"]
    best = lambda k: min((r[k] for r in ranked if r.get(k)), default=None)  # noqa: E731
    b_lat, b_cold, b_build = best("latency_ms"), best("cold_ms"), best("build_s")
    b_inv = min((1 / r["fits_per_s"] for r in ranked if r.get("fits_per_s")), default=None)
    b_loc = min((r["static"]["core_loc"] for r in ranked if r["static"]["core_loc"]), default=None)
    h_min = min((r["static"]["hardcoded_effects"] for r in ranked), default=0)
    all_fresh = all(r.get("build_kind") == "fresh" for r in ranked)
    for r in ranked:
        sp = {"latency": L(r.get("latency_ms"), b_lat, 100),
              "throughput": L(1 / r["fits_per_s"] if r.get("fits_per_s") else None, b_inv, 100),
              "cold": L(r.get("cold_ms"), b_cold, 100)}
        t = r["tests"]
        n = t.get("passed") or r["static"]["test_count_static"]
        ts = (0.0 if not t.get("found") else 0.6 + 0.4 * min(1, math.log10(1 + n) / math.log10(101)) if t.get("status") == "passed"
              else 0.2 if t.get("status") == "failed" else 0.3)
        d = r["static"]["docs"]
        mt = {"tests": ts, "data": L(r["static"]["hardcoded_effects"] + 10, h_min + 10, 10),
              "size": L(r["static"]["core_loc"], b_loc, 10), "docs": 0.4 * d["readme"] + 0.4 * d["design"] + 0.2 * d["license_file"],
              "deps": 1 / (1 + r["static"]["deps"]["n_runtime"] / 5), "build": L(r.get("build_s"), b_build, 100)}
        mw = dict(MAINT_W)
        if not all_fresh:
            mt["build"] = None; mw.pop("build")
        tot = sum(mw.values()); mw = {k: v / tot for k, v in mw.items()}
        f = r["features"]
        ft = {k: f.get(k, 0.0) for k in ("eft", "rpc", "search", "type")}
        s = {"speed": sum(SPEED_W[k] * v for k, v in sp.items()), "maint": sum(mw[k] * mt[k] for k in mw),
             "feat": sum(ft.values()) / 4, "port": r["portability"]["score"]}
        r["scores"] = {"speed_parts": sp, "maint_parts": mt, "maint_weights_used": mw, "feat_parts": ft, **{k: round(v, 4) for k, v in s.items()},
                       "total": round(sum(W[k] * s[k] for k in W), 4)}
    for i, r in enumerate(sorted(ranked, key=lambda r: -r["scores"]["total"])):
        r["rank"] = i + 1


RULES_MD = """## Scoring rules

- **Version rule:** each variant is evaluated at its branch HEAD as of the cutoff (`--as-of`; unified scoring 2026-10-03T10:15:00+08:00). Self-reported "final" versions are reference only. A commit that fails the gate is **disqualified**; no fallback to an older commit.
- **Runs:** one untimed warm-up batch, then `--runs` official-scorer runs per variant, one variant at a time; perf = median.
- **Gate (correctness):** ranked only if the variant built, ran, and passed **all** bench cases (cases fully correct = cases, no engine errors) in every run.
- **Total = 0.40·Speed + 0.35·Maintainability + 0.15·Features + 0.10·Portability** (each in [0, 1]).
- `L(x, best, span) = clamp(1 − log10(x/best)/log10(span), 0, 1)` for lower-is-better `x` (1 = best ranked variant, 0 = `span`× worse).
- **Bench pin:** cases/expected/run.py from bench `3da9671` (1.8.0, 326 cases; = 0969967 cases), whatever upstream main is.
- **Latency** = own measurement (not run.py's): batch command pinned to one CPU (taskset), (t_N − t_1)/(N − 1) with N sized for ≈0.5 s of calcs; ≥5 independent samples, median; samples ≤0, < 0.002 ms, or > t_N/N are invalid; spread > 50 % ⇒ re-measure (≤3 extra), then flagged.
- **Licensing** (at the evaluated commit): judged by the LICENSE texts in the variant dir and branch root (LGPL header ± companion GPL text ⇒ LGPL; GPL header without LGPL ⇒ GPL); SPDX metadata/README only refine -only/-or-later. Mergeable into LGPL-3.0-or-later mainline: LGPL-3/permissive yes, GPL no, no file / conflict unknown. Informational, not scored.
- **Speed** = 0.5·L(latency ms/calc, 100) + 0.3·L(1/batch fits·s⁻¹, 100) + 0.2·L(cold-start ms, 100); medians over runs.
- **Maintainability** = 0.25·Tests + 0.20·DataDriven + 0.20·Size + 0.15·Docs + 0.10·Deps + 0.10·Build.
  Tests: passed → 0.6 + 0.4·min(1, log10(1+n)/2); failed → 0.2; timed out → 0.3; none → 0.
  DataDriven: L(h+10, h_min+10, 10), h = distinct dataset effect names (camelCase, ≥8 chars) referenced in hand-written core source (heuristic for per-effect special-casing).
  Size: L(core LOC, min, 10). Docs: 0.4 README + 0.4 DESIGN + 0.2 LICENSE. Deps: 1/(1+n/5), n = direct runtime deps. Build: L(build s, best, 100), only if every ranked build was fresh (`--fresh-clones`), else dropped and the other weights renormalised.
- **Features** = mean(EFT, RPC, search, type); EFT = ½ export (Pyfa byte-exact) + ½ eft_parse round-trip; others = share of RPC probes passing.
- **Portability** = 1 if a WASM/browser build exists in code, 0.5 if only documented, else 0.
"""


def commit_time(r):
    g = r.get("git") or {}
    if not g.get("commit_time"):
        return ""
    import datetime
    t = datetime.datetime.fromisoformat(g["commit_time"]).astimezone(datetime.timezone(datetime.timedelta(hours=8)))
    return t.strftime("%m-%d %H:%M") + ("" if g.get("is_branch_head", True) else " (not head)")


def write(rows, a, meta):
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "evaluation.json").write_text(json.dumps({"meta": meta, "weights": {"total": W, "speed": SPEED_W, "maint": MAINT_W},
                                                         "variants": rows}, indent=1, default=str, ensure_ascii=False))
    f2 = lambda x, f="{:.2f}": "–" if x is None else f.format(x)  # noqa: E731
    dry = "**DRY RUN — not final results.** " if a.dry_run else ""
    md = [f"# Engine round 1 evaluation{' (DRY RUN)' if a.dry_run else ''}", "",
          f"{dry}Generated {meta['finished']} (Asia/Shanghai) by `tools/evaluate.py` (`{meta['evaluate_py_commit'][:7]}`); bench pinned to "
          f"{meta['bench_pin']['version']} @ `{meta['bench_pin']['sha'][:7]}` ({meta['bench_pin']['cases']} cases); "
          f"commits: {meta['as_of']}; runs = {a.runs}{' (quick)' if a.quick else ''}; host {meta['nproc']} CPUs; total wall time {meta['wall_s']/60:.1f} min. "
          "Perf numbers were measured on a shared, loaded machine: compare with the loadavg column.", "",
          "## Ranking", "",
          "| rank | variant | commit (CST) | cases | values | ms/calc | fits/s | cold ms | speed | maint | features | port | **total** | load (1m) |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted(rows, key=lambda r: (r.get("rank") or 99, r["letter"]))
    for r in order:
        s = r.get("scores", {})
        lo = "–" if not r.get("loads") else f"{min(r['loads']):.1f}–{max(r['loads']):.1f}"
        md.append(f"| {r.get('rank', '–')} | {r['letter']} {r['label']} | `{(r.get('git') or {}).get('sha', '')[:7]}` {commit_time(r)} | "
                  f"{r.get('cases_ok', '–')}/{r.get('cases', '–')} | {r.get('values_ok', '–')}/{r.get('values_total', '–')} | "
                  f"{f2(r.get('latency_ms'), '{:.3f}')} | {f2(r.get('fits_per_s'), '{:.0f}')} | {f2(r.get('cold_ms'), '{:.1f}')} | "
                  f"{f2(s.get('speed'))} | {f2(s.get('maint'))} | {f2(s.get('feat'))} | {f2(s.get('port'))} | **{f2(s.get('total'), '{:.3f}')}** | {lo} |")
    md += ["", "## Maintainability and features", "",
           "| variant | core LOC (languages) | test LOC | tests (own suite) | runtime deps | build s | README/DESIGN/LICENSE | license | hard-coded effects (h) | data-driven ratio | EFT exp | EFT parse | RPC | search | type | portability |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in order:
        st = r.get("static")
        if not st:
            md.append(f"| {r['letter']} | – |" + " – |" * 14); continue
        langs = ", ".join(f"{k} {v}" for k, v in sorted(st["loc"].get("core", {}).items(), key=lambda kv: -kv[1]))
        tl = sum(st["loc"].get("test", {}).values())
        t = r.get("tests", {})
        ts = ("none found" if not t.get("found") else "found, not run" if t.get("status") == "not run"
              else f"{t['status']} ({t.get('passed', '?')}✓/{t.get('failed', '?')}✗, {t.get('runner')}, {t.get('seconds')} s)") if t else "–"
        d = st["docs"]; fe = r.get("features", {})
        ex = fe.get("eft_export", {}); ep = fe.get("eft_parse", {})
        yn = lambda b: "✓" if b else "✗"  # noqa: E731
        lic = st["license"].get("effective") or "none"
        md.append(f"| {r['letter']} | {st['core_loc']} ({langs}) | {tl} | {ts} | {st['deps']['n_runtime']} | {f2(r.get('build_s'), '{:.1f}')} ({r.get('build_kind', '?')}) | "
                  f"{yn(d['readme'])}{yn(d['design'])}{yn(d['license_file'])} | {lic} | {st['hardcoded_effects']} | {st['data_driven_ratio']:.3f} | "
                  f"{ex.get('ok', '–')}/{ex.get('total', '–')} | {ep.get('ok', '–')}/{ep.get('total', '–')} | {f2(fe.get('rpc'))} | {f2(fe.get('search'))} | {f2(fe.get('type'))} | {r.get('portability', {}).get('level', '–')} |")
    md += ["", "## Licensing (mainline eve-dogma-rs is LGPL-3.0-or-later)", "",
           "| variant | license | -only/-or-later from | LICENSE files (kind) | mergeable into LGPL-3.0-or-later mainline | reason |", "|---|---|---|---|---|---|"]
    for r in order:
        li = (r.get("static") or {}).get("license")
        if li:
            md.append(f"| {r['letter']} | {li.get('effective') or 'none'} | {li.get('qualifier_source') or '–'} | {'; '.join(li['files']) or '–'} | "
                      f"**{li['mergeable']}** | {li['reason']} |")
    md += ["", "## Latency measurement (single CPU, own measurement)", "",
           "| variant | ms/calc (median) | min | max | spread | valid/samples | N per sample | startup ms | flags |", "|---|---|---|---|---|---|---|---|---|"]
    for r in order:
        la = r.get("latency")
        if la:
            md.append(f"| {r['letter']} | {f2(la.get('latency_ms'), '{:.4f}')} | {f2(la.get('min_ms'), '{:.4f}')} | {f2(la.get('max_ms'), '{:.4f}')} | "
                      f"{f2(la.get('spread') * 100 if la.get('spread') is not None else None, '{:.0f}%')} | {la.get('valid')}/{la.get('n_samples')} | "
                      f"{la.get('n_per_sample')} | {la.get('startup_ms')} | {'; '.join(la.get('flags') or []) or 'ok'} |")
    notes = [f"- **{r['letter']}**: {r.get('gate_reason', '')}" for r in order if r.get("gate") != "pass"]
    notes += [f"- {r['letter']} tests {r['tests']['status']}: `{r['tests'].get('tail', '')[-200:].strip()}`".replace("\n", " ")
              for r in order if r.get("tests", {}).get("status") in ("failed", "timeout")]
    if notes:
        md += ["", "## Not ranked / problems", ""] + notes
    md += ["", "## Per-run measurements", "", "| variant | run | wall s | cases ok | run.py ms/calc (info only) | fits/s | cold ms | loadavg before | loadavg after |", "|---|---|---|---|---|---|---|---|---|"]
    for r in order:
        for x in r.get("runs", []):
            md.append(f"| {r['letter']} | {x['run']} | {x['wall_s']} | {x.get('cases_ok', x.get('error', '–'))} | {f2(x.get('latency_ms'), '{:.3f}')} | "
                      f"{f2(x.get('fits_per_s'), '{:.0f}')} | {f2(x.get('cold_ms'), '{:.1f}')} | {x['loadavg_before']} | {x['loadavg_after']} |")
    md += ["", RULES_MD, "## Reproduce", "", f"```\n{meta['command']}\n```", ""]
    (a.out / "evaluation.md").write_text("\n".join(md) + "\n")
    return "\n".join(md)


LABELS = {"A": "eve-dogma-rs (Rust ref)", "B": "data-oriented Rust", "C": "Go", "D": "TypeScript", "E": "Pyfa-faithful Rust",
          "F": "codegen Rust/WASM", "G": "Python+NumPy", "H": "Rust ECS", "I": "Rust salsa", "J": "C++20", "K": "C#/.NET AOT"}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--only", help="comma-separated letters, e.g. A,J")
    ap.add_argument("--quick", action="store_true", help="fewer perf repetitions per run (batch x1, latency n=100)")
    ap.add_argument("--dry-run", action="store_true", help="label output DRY RUN; default --out results/dryrun")
    ap.add_argument("--out")
    ap.add_argument("--work-dir", default=str(ROOT / "work" / "eval"))
    ap.add_argument("--fresh-clones", action="store_true")
    ap.add_argument("--as-of", help="ISO-8601 cutoff, e.g. 2026-10-03T10:15:00+08:00: evaluate the last commit at or before it "
                    "(default: current branch head)")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--no-tests", action="store_true")
    ap.add_argument("--build-timeout", type=float, default=900)
    ap.add_argument("--test-timeout", type=float, default=300)
    ap.add_argument("--variant-timeout", type=float, default=1200, help="hard limit for all bench runs of one variant")
    ap.add_argument("--case-timeout", type=float, default=20, help="per request (single mode); batch gets 20x")
    ap.add_argument("--bench-ref", default=BENCH_PIN, help="bench commit whose cases/expected/run.py are used (default: frozen 1.8.0)")
    ap.add_argument("--latency-samples", type=int, default=5, help="independent latency measurements per variant (median)")
    ap.add_argument("--_child")
    a = ap.parse_args()
    if a._child:
        return child(json.loads(a._child))
    a.out = pathlib.Path(a.out) if a.out else ROOT / "results" / ("dryrun" if a.dry_run else "")
    a.out = a.out.resolve()
    work = pathlib.Path(a.work_dir).resolve(); work.mkdir(parents=True, exist_ok=True)
    tag = time.strftime("%Y%m%d-%H%M%S")
    import datetime
    if a.as_of and datetime.datetime.fromisoformat(a.as_of).tzinfo is None:
        ap.error("--as-of needs an explicit UTC offset, e.g. 2026-10-03T10:15:00+08:00")
    as_of = datetime.datetime.fromisoformat(a.as_of).timestamp() if a.as_of else None
    global BENCH
    BENCH, pin = pin_bench(work, a.bench_ref)
    log(f"bench pinned: {pin}")
    t_start = time.time()
    meta = {"started": time.strftime("%Y-%m-%d %H:%M:%S %Z"), "bench_version": f"{pin['version']}+{pin['sha'][:7]}", "bench_pin": pin,
            "evaluate_py_commit": subprocess.run("git rev-parse HEAD", shell=True, cwd=ROOT, capture_output=True, text=True).stdout.strip(), "nproc": os.cpu_count(),
            "command": " ".join(["python3", "tools/evaluate.py"] + [x for x in sys.argv[1:]]), "dry_run": a.dry_run, "as_of": a.as_of or "current head",
            "host_loadavg_start": load3()}
    ds = json.load(gzip.open(DATASET))
    names = {e["name"] for e in ds["effects"].values() if re.search(r"[A-Z]", e["name"]) and len(e["name"]) >= 8}
    n_mod = sum(1 for e in ds["effects"].values() if e.get("mods"))
    del ds
    letters = [x for x in (a.only.upper().split(",") if a.only else LETTERS)]
    rows = []
    for letter in letters:
        log(f"== {letter}")
        row = {"letter": letter, "label": LABELS.get(letter, ""), "gate": "fail"}
        rows.append(row)
        vd, g = fetch(letter, work, a.fresh_clones, a.no_fetch, as_of)
        row["git"] = g
        if vd is None:
            row["gate_reason"] = f"unavailable: {g.get('error', '')[:200]}"; continue
        m = manifest(letter, vd)
        if not m or "cmd" not in m:
            row["gate_reason"] = "no bench.yaml / cmd"; continue
        m = {k: (v.format(dataset=DATASET, bench=BENCH, dir=vd) if isinstance(v, str) else v) for k, v in m.items()}
        row["manifest"] = m
        if m.get("build") and not a.no_build:
            fresh_build = g.get("fresh_clone", False)
            rc, dt, out = sh(m["build"], str(vd), a.build_timeout)
            row.update(build_s=round(dt, 1), build_kind="fresh" if fresh_build else "incremental")
            log(f"{letter} build rc={rc} {dt:.1f}s")
            if rc != 0:
                row["gate_reason"] = f"build failed ({'timeout' if rc is None else rc}): {out[-300:]}"
                row["static"] = static_metrics(letter, vd, names, n_mod); continue
        deadline = time.time() + a.variant_timeout
        a.remaining = lambda: max(5, deadline - time.time())
        if m.get("batch_cmd"):  # untimed warm-up
            corpus = "".join(json.dumps(json.loads(p.read_text())) + "\n" for p in sorted((BENCH / "cases").glob("*.json")))
            sh(m["batch_cmd"], str(vd), min(300, a.case_timeout * 20), inp=corpus)
        runs = []
        for i in range(1, a.runs + 1):
            if time.time() > deadline:
                runs.append({"run": i, "error": "variant timeout", "wall_s": 0, "loadavg_before": load3(), "loadavg_after": load3()}); break
            x = bench_run(letter, m, vd, i, a, tag)
            log(f"{letter} run{i}: {x.get('cases_ok')}/{x.get('cases')} lat={x.get('latency_ms')} fps={x.get('fits_per_s')} cold={x.get('cold_ms')} load={x['loadavg_before'][0]} {x.get('error', '')[:200]}")
            runs.append(x)
            if x.get("error"):
                break
        row["runs"] = runs
        good = [x for x in runs if not x.get("error")]
        if good and m.get("batch_cmd"):
            row["latency"] = measure_latency(m["batch_cmd"], vd, a, work)
            log(f"{letter} latency {row['latency'].get('latency_ms')} ms spread={row['latency'].get('spread')} flags={row['latency'].get('flags')}")
        row["loads"] = [x["loadavg_before"][0] for x in runs] + [x["loadavg_after"][0] for x in runs]
        if good:
            r1 = good[0]
            row.update(cases=r1["cases"], cases_ok=r1["cases_ok"], values_ok=r1["values_ok"], values_total=r1["values_total"],
                       errors=r1["errors"], groups=r1["groups"],
                       latency_ms=(row.get("latency") or {}).get("latency_ms"),
                       latency_runpy_ms_info=med([x["latency_ms"] for x in good]), fits_per_s=med([x["fits_per_s"] for x in good]),
                       cold_ms=med([x["cold_ms"] for x in good]), deterministic=all(x.get("deterministic") is not False for x in good),
                       consistent=len({(x["cases_ok"], x["values_ok"]) for x in good}) == 1)
        bad = [x for x in runs if x.get("error")]
        if not good:
            row["gate_reason"] = f"run failed: {bad[0]['error'][:300] if bad else 'no runs'}"
        elif bad:
            row["gate_reason"] = f"run {bad[0]['run']} failed: {bad[0]['error'][:300]}"
        elif not (row["cases_ok"] == row["cases"] and row["errors"] == 0 and row["consistent"]):
            row["gate_reason"] = f"DISQUALIFIED (correctness gate at evaluated commit, no fallback): {row['cases_ok']}/{row['cases']} cases, {row['values_ok']}/{row['values_total']} values, {row['errors']} errors"
        else:
            row["gate"] = "pass"
        try:
            row["features"] = features(m, vd, a)
        except Exception as e:  # noqa: BLE001
            row["features"] = {"error": repr(e)[:300], "eft": 0, "rpc": 0, "search": 0, "type": 0}
        row["static"] = static_metrics(letter, vd, names, n_mod)
        row["portability"] = portability(vd)
        row["tests"] = {"found": test_command(m, vd)[0] is not None, "status": "not run"} if a.no_tests else run_tests(m, vd, a.test_timeout)
        log(f"{letter} gate={row['gate']} tests={row['tests'].get('status')} feat={ {k: row['features'].get(k) for k in ('eft','rpc','search','type')} }")
    score_all(rows)
    meta.update(finished=time.strftime("%Y-%m-%d %H:%M:%S %Z"), wall_s=round(time.time() - t_start, 1), host_loadavg_end=load3())
    print(write(rows, a, meta))


if __name__ == "__main__":
    main()
