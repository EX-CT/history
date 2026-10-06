#!/usr/bin/env python3
"""Contract draft 1.4.5 module-state check (informational, not scored yet):
  python3 tools/check_module_state.py --batch-cmd "<engine> batch"
Runs pending/state/state_*.json through the engine's batch command and compares `modules[].state` and the
state-correction entries of `warnings[]` with pending/state/*.expected.json (Pyfa isValidState, oracle/state_oracle.py)."""
import argparse, json, pathlib, shlex, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("--batch-cmd", required=True); ap.add_argument("--cwd")
a = ap.parse_args()
reqs = sorted(p for p in (ROOT / "pending/state").glob("state_*.json") if not p.name.endswith(".expected.json"))
inp = "".join(json.dumps(json.loads(p.read_text())) + "\n" for p in reqs)
out = subprocess.run(a.batch_cmd, shell=True, input=inp, capture_output=True, text=True, cwd=a.cwd).stdout.splitlines()
ok = 0
for p, line in zip(reqs, out):
    exp = json.loads(p.with_name(p.stem + ".expected.json").read_text())
    got = json.loads(line)
    st = [m.get("state") for m in got.get("modules", [])]
    w = [x for x in got.get("warnings", []) if "not possible for this module" in x]
    good = st == exp["modules_state"] and w == exp["warnings"]
    ok += good
    print(f"{p.stem}: {'ok' if good else 'MISMATCH'}" + ("" if good else f"\n  state got {st}\n  state want {exp['modules_state']}\n  warnings got {w}\n  warnings want {exp['warnings']}"))
print(f"module-state check: {ok}/{len(reqs)}")
sys.exit(0 if ok == len(reqs) and len(out) == len(reqs) else 1)
