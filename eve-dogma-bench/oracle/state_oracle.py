#!/usr/bin/env python3
"""Module-state oracle (GPL-3.0-or-later, test tool only; uses oracle/pyfa_oracle.py's Pyfa fit builder).
For each FitRequest JSON prints {"file", "states": [corrected state per modules[] entry]} as Pyfa sets them
(isValidState else ONLINE). usage: PYFA=... python state_oracle.py req.json [...]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pyfa_oracle as po  # noqa: E402
NAME = {v: k for k, v in po.STATES.items()}
for path in sys.argv[1:]:
    req = json.load(open(path))
    fit = po.build(req)
    mods = po.ORACLE_MODS.get(id(fit), [])
    print(json.dumps({"file": os.path.basename(path), "states": [NAME[m.state] for m in mods]}))
