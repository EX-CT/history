#!/usr/bin/env python3
"""Inventory of Pyfa (eos/effects.py) effect handlers vs SDE modifierInfo.

Reads Pyfa's effects module with `ast` (nothing is imported or executed, no Pyfa code is copied into outputs):
for every handler we record *which attributes it touches, how (operation verbs) and on which targets/filters*. That
behaviour summary is compared with the dataset's `mods` to find effects that CCP's modifierInfo cannot express.

    python tools/pyfa_effects.py --pyfa /path/to/pyfa --dataset dist/dataset-<build>.json.gz \
        [--engine-src /path/to/eve-dogma-rs/src] --out reports/
"""
from __future__ import annotations

import argparse, ast, gzip, json, os, re, sys
from collections import Counter

# Pyfa helper names -> neutral verbs used in our behaviour descriptions
VERBS = {
    "boostItemAttr": "percent bonus (PostPercent)", "multiplyItemAttr": "multiply (PostMul)", "increaseItemAttr": "add (ModAdd)",
    "forceItemAttr": "assign (PostAssign)", "preAssignItemAttr": "pre-assign (PreAssign)",
    "filteredItemBoost": "percent bonus on filtered items", "filteredItemMultiply": "multiply on filtered items",
    "filteredItemIncrease": "add on filtered items", "filteredItemForce": "assign on filtered items",
    "filteredChargeBoost": "percent bonus on filtered charges", "filteredChargeMultiply": "multiply on filtered charges",
    "filteredChargeIncrease": "add on filtered charges", "filteredChargeForce": "assign on filtered charges",
    "addCommandBonus": "warfare/command buff", "addDrain": "capacitor drain/fill (projected)", "addProjectedEcm": "ECM jam (projected)",
    "_addArmorRr": "remote armor repair", "_addShieldRr": "remote shield repair", "_addHullRr": "remote hull repair",
    "addSpeedFactor": "speed factor", "addSpoolup": "spool-up",
}
TARGETS = ("ship", "modules", "drones", "fighters", "character", "charges", "appliedImplants", "boosters")


def _const(n):
    return n.value if isinstance(n, ast.Constant) else None


def summarize_handler(fn: ast.FunctionDef):
    ops, attrs, skills, groups, names = [], set(), set(), set(), set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            f = node.func
            meth = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if meth == "requiresSkill" and node.args and _const(node.args[0]):
                skills.add(_const(node.args[0]))
            if meth in VERBS:
                target = None
                if isinstance(f, ast.Attribute):
                    v = f.value
                    while isinstance(v, ast.Attribute):
                        if v.attr in TARGETS:
                            target = v.attr
                            break
                        v = v.value
                    if target is None and isinstance(f.value, ast.Name):
                        target = f.value.id
                strs = [_const(a) for a in node.args if isinstance(_const(a), str)]
                ops.append({"op": meth, "target": target, "attrs": strs})
                attrs.update(strs)
            if meth in ("getModifiedItemAttr", "getModifiedChargeAttr", "getModifiedOwnerAttr") and node.args and isinstance(_const(node.args[0]), str):
                attrs.add(_const(node.args[0]))
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Attribute) and node.left.attr == "name":
            for c in node.comparators:
                if isinstance(_const(c), str):
                    groups.add(_const(c))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.add(node.value)
    trivial = not ops and not any(isinstance(n, (ast.Call, ast.Assign, ast.AugAssign)) for n in ast.walk(fn))
    return {"ops": ops, "attrs": sorted(attrs), "skills": sorted(skills), "name_filters": sorted(groups), "trivial": trivial}


def parse_pyfa(path: str):
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = {}
    for cls in tree.body:
        if not (isinstance(cls, ast.ClassDef) and re.fullmatch(r"Effect\d+", cls.name)):
            continue
        doc = ast.get_docstring(cls) or ""
        name = doc.strip().splitlines()[0].strip() if doc.strip() else None
        info = {"class": cls.name, "pyfa_id": int(cls.name[6:]), "name": name, "type": None, "runTime": None}
        handler = None
        for st in cls.body:
            if isinstance(st, ast.Assign) and st.targets and isinstance(st.targets[0], ast.Name):
                k = st.targets[0].id
                if k in ("type", "runTime"):
                    try:
                        info[k] = ast.literal_eval(st.value)
                    except Exception:
                        pass
            if isinstance(st, ast.FunctionDef) and st.name == "handler":
                handler = st
        info.update(summarize_handler(handler) if handler else {"ops": [], "attrs": [], "skills": [], "name_filters": [], "trivial": True})
        if name:
            out[name] = info
    return out


def engine_names(src_dir: str | None):
    """String literals in engine sources: exact effect names, plus prefixes used with starts_with/StartsWith."""
    if not src_dir:
        return set(), set()
    names, prefixes = set(), set()
    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith((".rs", ".cs")):
                src = open(os.path.join(root, f), encoding="utf-8").read()
                names.update(re.findall(r'"([A-Za-z][A-Za-z0-9_]+)"', src))
                prefixes.update(re.findall(r'(?:starts_with|StartsWith)\(\s*"([A-Za-z][A-Za-z0-9_]+)"', src))
                # C# prefix tables: new[] { "remoteWebifier" } next to StartsWith usage
                for m in re.finditer(r'new\("[^"]+",\s*new\[\]\s*\{([^}]*)\}', src):
                    prefixes.update(re.findall(r'"([A-Za-z][A-Za-z0-9_]+)"', m.group(1)))
    return names, prefixes


def classify(ds, pyfa, eng, prefixes=frozenset()):
    effects = ds["effects"]
    by_name = {e["name"]: (k, e) for k, e in effects.items()}
    used = Counter(eid for t in ds["types"].values() for eid, _ in t.get("effects", []))
    patched = {}
    for p in ds.get("patches", []):
        patched[p["id"]] = p
    rows = []
    for name, info in sorted(pyfa.items(), key=lambda kv: kv[1]["pyfa_id"]):
        k, e = by_name.get(name, (None, None))
        has_mods = bool(e and e["mods"])
        if e is None:
            status = "pyfa-custom" if info["pyfa_id"] >= 100000 else "not-in-sde"
        elif info["trivial"]:
            status = "pyfa-noop"
        elif has_mods:
            status = "sde-modifiers"
        elif name in eng or any(name.startswith(pf) for pf in prefixes):
            status = "engine-special"
        elif info["ops"] and all(o["op"] == "addCommandBonus" for o in info["ops"]):
            kinds = info["type"] if isinstance(info["type"], (list, tuple)) else (info["type"],)
            status = "engine-generic" if "active" in kinds else "data-provided"
        else:
            status = "gap"
        rows.append({"effect_id": int(k) if k else None, "name": name, "status": status, "sde_mods": len(e["mods"]) if e else None,
                     "types_using": used.get(int(k), 0) if k else 0, "pyfa_type": info["type"], "run_time": info["runTime"],
                     "ops": info["ops"], "skills": info["skills"], "name_filters": info["name_filters"], "attrs": info["attrs"]})
    return rows


def describe(r):
    parts = []
    for o in r["ops"][:6]:
        verb = VERBS.get(o["op"], o["op"])
        tgt = o["target"] or "?"
        a = ", ".join(o["attrs"]) if o["attrs"] else "(computed attribute)"
        parts.append(f"{verb} on {tgt}: {a}")
    if len(r["ops"]) > 6:
        parts.append(f"… {len(r['ops']) - 6} more operations")
    if r["skills"]:
        parts.append("filter: requires skill " + ", ".join(r["skills"]))
    if r["name_filters"]:
        parts.append("filter: group/name " + ", ".join(r["name_filters"][:5]))
    return "; ".join(parts) if parts else "handler logic without attribute helpers (state, flags or stats-only)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pyfa", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--engine-src", action="append", default=[])
    ap.add_argument("--engine-names", help="JSON {names:[...], prefixes:[...]} snapshot (CI, engines are private)")
    ap.add_argument("--dump-engine-names", help="write the engine names/prefixes found via --engine-src to this file")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ds = json.load(gzip.open(a.dataset) if a.dataset.endswith(".gz") else open(a.dataset))
    pyfa = parse_pyfa(os.path.join(a.pyfa, "eos", "effects.py"))
    eng, prefixes = set(), set()
    for src in a.engine_src:
        n, pf = engine_names(src)
        eng |= n; prefixes |= pf
    if a.engine_names:
        snap = json.load(open(a.engine_names, encoding="utf-8"))
        eng |= set(snap["names"]); prefixes |= set(snap["prefixes"])
    if a.dump_engine_names:
        effect_names = {e["name"] for e in ds["effects"].values()}
        with open(a.dump_engine_names, "w", encoding="utf-8") as f:
            json.dump({"names": sorted(eng & effect_names), "prefixes": sorted(prefixes)}, f, indent=0)
    rows = classify(ds, pyfa, eng, prefixes)
    os.makedirs(a.out, exist_ok=True)
    json.dump(rows, open(os.path.join(a.out, "pyfa-effects.json"), "w"), indent=1, sort_keys=True)
    c = Counter(r["status"] for r in rows)
    sde_total = len(ds["effects"]); sde_mods = sum(1 for e in ds["effects"].values() if e["mods"])
    md = [f"# Pyfa effect handlers vs SDE modifierInfo (SDE build {ds['sde']['build']})", "",
          "Generated by `tools/pyfa_effects.py` from Pyfa's `eos/effects.py` (eos is LGPL; parsed with `ast`, nothing copied:",
          "the table below *describes* each handler's behaviour). Status:", "",
          "- `sde-modifiers`: the SDE effect has modifierInfo; engines apply it data-driven.",
          "- `engine-special`: no modifierInfo, but the reference engines handle the effect by name (hand-written rule).",
          "- `gap`: no modifierInfo and no engine rule: behaviour Pyfa implements that our data/engines do not (yet).",
          "- `engine-generic`: command-burst modules; engines read warfareBuffNID/Value generically (no per-effect rule).",
          "- `data-provided`: environment beacons whose handler only emits warfare buffs; the dataset lists their buffs in",
          "  `environment.effect_beacons[*].dbuffs` so an engine can apply them like fleet buffs (engines: not yet).",
          "- `pyfa-noop`: Pyfa's handler does nothing (effect is informational / handled elsewhere).",
          "- `pyfa-custom`: effect invented by Pyfa (ids >= 100000; e.g. sov/insurgency/Pochven beacons).",
          "- `not-in-sde`: Pyfa handler for an effect name no longer present in this SDE.", "",
          f"SDE: {sde_total} effects, {sde_mods} with modifierInfo. Pyfa: {len(rows)} handlers.", "",
          "| status | handlers |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(c.items())]
    for st, title in (("gap", "Gaps (no modifierInfo, no engine rule)"), ("data-provided", "Environment buff sources (data provided)"), ("engine-special", "Handled by engine rules"),
                      ("engine-generic", "Command bursts (generic engine handling)"),
                      ("pyfa-custom", "Pyfa custom effects"), ("not-in-sde", "Pyfa handlers for effects not in this SDE")):
        sel = [r for r in rows if r["status"] == st]
        if st == "gap":
            sel.sort(key=lambda r: -r["types_using"])
        md += ["", f"## {title} ({len(sel)})", "", "| effect | id | types | Pyfa kind | behaviour (described) |", "|---|---|---|---|---|"]
        for r in sel:
            kind = "/".join(r["pyfa_type"]) if isinstance(r["pyfa_type"], (list, tuple)) else (r["pyfa_type"] or "")
            md.append(f"| {r['name']} | {r['effect_id'] or ''} | {r['types_using']} | {kind} | {describe(r).replace('|', '/')} |")
    open(os.path.join(a.out, "pyfa-effects-coverage.md"), "w").write("\n".join(md) + "\n")
    print(json.dumps(c, sort_keys=True))


if __name__ == "__main__":
    main()
