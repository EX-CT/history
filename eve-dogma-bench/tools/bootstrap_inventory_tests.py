#!/usr/bin/env python3
"""One-off bootstrap of inventory/tests.yaml from docs/19 `f_evidence` strings: every token that names an existing
case (or case glob) in a file suite becomes a `suite:name` ref. Output is meant to be reviewed and curated by hand.
  python3 tools/bootstrap_inventory_tests.py INVENTORY.yaml > /tmp/auto.yaml"""
import os
import re
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_inventory import REPO, Resolver, load_yaml  # noqa: E402

TAG = {"B19": "bench", "FZ": "bench", "CAP": "cap", "MUT": "mut", "GR2": "graphs", "FMT": "fmt"}
ORDER = ["bench", "state", "cap", "mut", "graphs"]
inv = load_yaml(sys.argv[1])
suites = load_yaml(os.path.join(REPO, "inventory", "suites.yaml"))["suites"]
res = Resolver(suites, {}, REPO)
out = {}
for it in inv["items"]:
    ev = it.get("f_evidence") or ""
    refs = []
    cur = None
    for tok in re.findall(r"[A-Za-z0-9_*]+", ev):
        if tok in TAG:
            cur = TAG[tok]
            continue
        if not re.match(r"^[a-z][a-z0-9_]*\*?$", tok) or len(tok) < 4:
            continue
        for s in ([cur] if cur else []) + [x for x in ORDER if x != cur]:
            if res.exists(s, tok if tok.endswith("*") else tok) or (not tok.endswith("*") and res.exists(s, tok + "_*")):
                refs.append(f"{s}:{tok if tok.endswith('*') or res.exists(s, tok) else tok + '_*'}")
                break
    if refs:
        out[it["id"]] = sorted(set(refs))
yaml.safe_dump({"items": out}, sys.stdout, sort_keys=False, width=200)
