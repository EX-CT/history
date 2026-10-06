#!/usr/bin/env python3
"""CI gate on a bench scorecard: every case fully correct and no engine errors.

  python3 tools/ci_gate.py LABEL results/<name>/scorecard.json
Appends one markdown line to $GITHUB_STEP_SUMMARY; exit 1 if not clean."""
import json, os, sys

label, path = sys.argv[1], sys.argv[2]
s = json.load(open(path))
ok = s["cases_fully_correct"] == s["cases"] and s.get("errors", 0) == 0 and s["values_correct"] == s["values_total"]
line = (f"- {'✅' if ok else '❌'} **{label}**: {s['cases_fully_correct']}/{s['cases']} cases, "
        f"{s['values_correct']}/{s['values_total']} values, engine errors {s.get('errors', 0)}"
        + (f", deterministic {s['perf'].get('deterministic')}" if isinstance(s.get("perf"), dict) and "deterministic" in s["perf"] else ""))
print(line)
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
        f.write(line + "\n")
if isinstance(s.get("perf"), dict) and s["perf"].get("deterministic") is False:
    ok = False
sys.exit(0 if ok else 1)
