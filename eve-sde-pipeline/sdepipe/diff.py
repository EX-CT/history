"""Diff two engine datasets -> machine-readable dict + Markdown report (CHANGELOG-<build>.md)."""
from __future__ import annotations

import gzip
import json
from typing import Any, Dict, List

SECTIONS = ("types", "groups", "categories", "attributes", "effects", "dbuffs", "mutaplasmids", "market_groups", "traits")
MAX_LINES = 200  # per Markdown list (the JSON diff is complete)


def load(path: str) -> Dict[str, Any]:
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _name(sec: str, key: str, v: Dict[str, Any] | None) -> str:
    if isinstance(v, dict) and v.get("name"):
        return f"{v['name']} ({key})"
    return key


def diff(old: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {"old": {"build": old.get("sde", {}).get("build"), "revision": old.get("dataset_revision", 1)},
                           "new": {"build": new.get("sde", {}).get("build"), "revision": new.get("dataset_revision", 1)},
                           "sections": {}}
    for sec in SECTIONS:
        a, b = old.get(sec), new.get(sec)
        if a is None and b is None:
            continue
        a, b = a or {}, b or {}
        added = sorted(set(b) - set(a), key=lambda k: int(k) if k.isdigit() else k)
        removed = sorted(set(a) - set(b), key=lambda k: int(k) if k.isdigit() else k)
        changed = []
        for k in sorted(set(a) & set(b), key=lambda k: int(k) if k.isdigit() else k):
            if a[k] == b[k]:
                continue
            entry: Dict[str, Any] = {"key": k, "name": (b[k] or {}).get("name") if isinstance(b[k], dict) else None}
            if isinstance(a[k], dict) and isinstance(b[k], dict):
                fields = {}
                for f in sorted(set(a[k]) | set(b[k])):
                    if a[k].get(f) == b[k].get(f):
                        continue
                    if f == "attrs" and sec == "types":
                        x, y = a[k].get(f, {}), b[k].get(f, {})
                        fields[f] = {aid: [x.get(aid), y.get(aid)] for aid in sorted(set(x) | set(y), key=int) if x.get(aid) != y.get(aid)}
                    elif f == "effects" and sec == "types":
                        x = {e for e, _ in a[k].get(f, [])}; y = {e for e, _ in b[k].get(f, [])}
                        fields[f] = {"added": sorted(y - x), "removed": sorted(x - y)} if x != y else "isDefault changed"
                    else:
                        fields[f] = [a[k].get(f), b[k].get(f)]
                entry["fields"] = fields
            changed.append(entry)
        out["sections"][sec] = {"added": [{"key": k, "name": (b[k] or {}).get("name") if isinstance(b[k], dict) else None} for k in added],
                                "removed": [{"key": k, "name": (a[k] or {}).get("name") if isinstance(a[k], dict) else None} for k in removed],
                                "changed": changed}
    return out


def _attr_name(ds: Dict[str, Any], aid: str) -> str:
    a = ds.get("attributes", {}).get(aid)
    return a["name"] if a else aid


def markdown(d: Dict[str, Any], new: Dict[str, Any]) -> str:
    o, n = d["old"], d["new"]
    lines: List[str] = [f"# SDE dataset changes: build {o['build']} r{o['revision']} → {n['build']} r{n['revision']}", ""]
    lines += ["| section | added | removed | changed |", "|---|---|---|---|"]
    for sec, s in d["sections"].items():
        lines.append(f"| {sec} | {len(s['added'])} | {len(s['removed'])} | {len(s['changed'])} |")
    for sec, s in d["sections"].items():
        if not (s["added"] or s["removed"] or s["changed"]):
            continue
        lines += ["", f"## {sec}"]
        for label, items in (("Added", s["added"]), ("Removed", s["removed"])):
            if items:
                lines += ["", f"**{label}** ({len(items)})", ""]
                lines += [f"- {i['name'] or ''} `{i['key']}`" for i in items[:MAX_LINES]]
                if len(items) > MAX_LINES:
                    lines.append(f"- … {len(items) - MAX_LINES} more (see diff JSON)")
        if s["changed"]:
            lines += ["", f"**Changed** ({len(s['changed'])})", ""]
            for c in s["changed"][:MAX_LINES]:
                parts = []
                for f, v in (c.get("fields") or {}).items():
                    if f == "attrs":
                        parts.append(", ".join(f"{_attr_name(new, aid)}: {x} → {y}" for aid, (x, y) in list(v.items())[:12])
                                     + (" …" if len(v) > 12 else ""))
                    elif f == "effects":
                        parts.append(f"effects {v}")
                    elif f == "mods":
                        parts.append("modifierInfo changed")
                    else:
                        x, y = v
                        sx, sy = json.dumps(x, ensure_ascii=False), json.dumps(y, ensure_ascii=False)
                        parts.append(f"{f}: {sx[:80]} → {sy[:80]}")
                lines.append(f"- {c.get('name') or ''} `{c['key']}`: " + "; ".join(parts))
            if len(s["changed"]) > MAX_LINES:
                lines.append(f"- … {len(s['changed']) - MAX_LINES} more (see diff JSON)")
    if not any(x["added"] or x["removed"] or x["changed"] for x in d["sections"].values()):
        lines += ["", "_No changes in engine-relevant data (published types, dogma, names, environment)._"]
    return "\n".join(lines) + "\n"


def ccp_changes_markdown(path: str) -> str:
    """Summarise CCP's raw changes feed (changes/<build>.jsonl): per-table added/changed/removed key counts.
    Covers tables and items the engine dataset filters out (NPCs, unpublished types, ...)."""
    meta, rows = {}, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("_key") == "_meta":
                meta = r
            else:
                rows.append(r)
    lines = ["", f"## CCP raw SDE changes (build {meta.get('lastBuildNumber')} → {meta.get('buildNumber')})", "",
             "| table | added | changed | removed |", "|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: r["_key"]):
        c = lambda k: len(r.get(k) or [])
        lines.append(f"| {r['_key']} | {c('added')} | {c('changed')} | {c('removed')} |")
    return "\n".join(lines) + "\n"
