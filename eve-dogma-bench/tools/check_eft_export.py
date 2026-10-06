#!/usr/bin/env python3
"""Informational check (not part of accuracy): EFT export vs Pyfa's exporter (contract 1.4.1, ruling 4).

  python3 tools/check_eft_export.py --rpc-cmd "<engine> serve-stdio --dataset ..." [--cwd DIR] [--show N]

Sends one JSONL request per case `{"id": i, "method": "eft_export", "params": {"fit": <FitRequest>, "name": <name>}}`
and expects `{"id": i, "result": {"text": "..."}}` lines back (any order; non-JSON lines such as banners are
ignored). Expected texts: expected_extra/eft_export.jsonl (Pyfa exportEft, all options on, after fill()).
Known data divergence: SDE 3569502 gives T3 cruisers maxSubSystems = 5 (Pyfa eve.db: 4) → one extra
"[Empty Subsystem slot]" line is accepted for those fits."""
import argparse, json, pathlib, shlex, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def check(rpc_cmd, cwd=None, show=0, timeout=600):
    exp = [json.loads(l) for l in open(ROOT / "expected_extra/eft_export.jsonl")]
    inp = "".join(json.dumps({"id": i, "method": "eft_export", "params": {"fit": e["fit"], "name": e["name"]}}) + "\n"
                  for i, e in enumerate(exp))
    r = subprocess.run(rpc_cmd, shell=True, cwd=cwd, input=inp, capture_output=True, text=True, timeout=timeout)
    got = {}
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if isinstance(o, dict) and "id" in o:
            res = o.get("result")
            got[o["id"]] = res.get("text") if isinstance(res, dict) else res
    ok, bad = 0, []
    for i, e in enumerate(exp):
        t = got.get(i)
        if isinstance(t, str) and (t == e["text"] or t.replace("\n[Empty Subsystem slot]", "", 1) == e["text"]):
            ok += 1
        else:
            bad.append((e["file"], e["text"], t))
    for f, want, t in bad[:show]:
        print(f"MISMATCH {f}\n--- pyfa\n{want}\n--- got\n{t}\n")
    return {"ok": ok, "total": len(exp), "failed": [b[0] for b in bad][:50]}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rpc-cmd", required=True)
    ap.add_argument("--cwd")
    ap.add_argument("--show", type=int, default=3)
    a = ap.parse_args()
    res = check(a.rpc_cmd, a.cwd, a.show)
    print(f"eft_export: {res['ok']}/{res['total']}")
    sys.exit(0 if res["ok"] == res["total"] else 1)
