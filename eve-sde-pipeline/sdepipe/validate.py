"""Invariant checks for a built dataset."""
from typing import Any, Dict, List


def validate(ds: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    attrs, effects, types, groups = ds["attributes"], ds["effects"], ds["types"], ds["groups"]
    for tid, t in types.items():
        if str(t["group"]) not in groups:
            errs.append(f"type {tid}: unknown group {t['group']}")
        for aid in t["attrs"]:
            if aid not in attrs:
                errs.append(f"type {tid}: unknown attribute {aid}")
        for eid, _ in t["effects"]:
            if str(eid) not in effects:
                errs.append(f"type {tid}: unknown effect {eid}")
    for eid, e in effects.items():
        for func, dom, modified, modifying, op, extra in e["mods"]:
            if func == 5:
                continue
            for a in (modified, modifying):
                if str(a) not in attrs:
                    errs.append(f"effect {eid}: unknown attribute {a}")
            if op not in (-1, 0, 1, 2, 3, 4, 5, 6, 7, 9):
                errs.append(f"effect {eid}: unknown op {op}")
    for name in ("Rifter", "Raven", "Gunnery"):
        if not any(t["name"] == name for t in types.values()):
            errs.append(f"sanity: type {name!r} missing")
    return errs
