#!/usr/bin/env python3
"""Generate expected/<case>.json by running the Pyfa oracle (oracle/pyfa_oracle.py, GPL) on cases/<case>.json.
usage: python3 tools/make_expected.py [cases/*.json]
env: PYFA (Pyfa checkout with eve.db), PYFA_PY (python with Pyfa deps), WX_STUB (dir with stub wx module)"""
import json, os, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from metrics import from_pyfa, METRICS  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
STUB = os.environ.get("WX_STUB", f"{REF}/stubs")


def main(files):
    files = [str(pathlib.Path(f).resolve()) for f in files] or sorted(str(p) for p in (ROOT / "cases").glob("*.json"))
    known = json.loads((ROOT / "expected/known_divergences.json").read_text()) if (ROOT / "expected/known_divergences.json").exists() else {}
    env = dict(os.environ, PYTHONPATH=STUB, ORACLE_REPEAT="0", PYFA=PYFA)
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
        vals = from_pyfa(r["stats"])
        skip = known.get(name, {})
        exp = {"case": name, "oracle": "pyfa-eos", "values": {k: v for k, v in sorted(vals.items()) if k in METRICS and k not in skip},
               "excluded": skip}
        (ROOT / "expected" / f"{name}.json").write_text(json.dumps(exp, indent=1, sort_keys=True, default=str) + "\n")
        n += 1
    print(f"wrote {n} expected files")


if __name__ == "__main__":
    main(sys.argv[1:])
