"""Additive dataset sections (format v1, dataset revision 2+).

Everything here is *new top-level keys*: the eve-dogma-rs loader (and the other engines) ignore unknown keys, so
datasets stay backward compatible. Each section mirrors what Pyfa's `db_update.py` imports from the client data:
market/meta groups, units, traits ("bonus text"), required skills, alpha clone limits, localisation, and the
environment (wormhole / Pochven / abyssal / sov) effect sources.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable

# requiredSkill1..6 -> requiredSkill1Level..6Level
REQ_SKILL_ATTRS = ((182, 277), (183, 278), (184, 279), (1285, 1286), (1289, 1287), (1290, 1288))

# mapRegions/mapConstellations/mapSolarSystems.wormholeClassID
WORMHOLE_CLASS_LABELS = {
    1: "C1", 2: "C2", 3: "C3", 4: "C4", 5: "C5", 6: "C6", 7: "highsec", 8: "lowsec", 9: "nullsec",
    12: "Thera", 13: "C13 (shattered)", 14: "Sentinel (drifter)", 15: "Barbican (drifter)", 16: "Vidette (drifter)",
    17: "Conflux (drifter)", 18: "Redoubt (drifter)", 19: "Abyssal", 20: "Abyssal", 21: "Abyssal", 22: "Abyssal",
    23: "Abyssal", 25: "Pochven",
}

LANGS = ("en", "zh")

# warfareBuffNID / warfareBuffNValue attribute ids (resolved by name at build time, see build_extras)
WARFARE_BUFF_ATTRS: Dict[int, tuple] = {}

# Celestial groups whose types are system / site environment effects (Pyfa "Effect Beacon" style projections)
ENV_GROUPS = {"Effect Beacon", "Destructible Effect Beacon", "Abyssal Hazards", "MassiveEnvironments",
              "Triglavian Support Pylons"}


def beacon_kind(name: str, group: str) -> str:
    n = name.lower()
    if any(w in n for w in ("pulsar", "black hole", "cataclysmic", "magnetar", "red giant", "wolf rayet")):
        return "wormhole"
    if group in ("MassiveEnvironments", "Abyssal Hazards", "Triglavian Support Pylons") or "weather" in n:
        return "abyssal"
    if "metaliminal" in n or "storm" in n:
        return "metaliminal_storm"
    if "incursion" in n and "triglavian" not in n:
        return "incursion"
    if "triglavian" in n or "liminality" in n:
        return "triglavian"
    if "war hq" in n or "tactical relay" in n or "observatory" in n:
        return "faction_warfare"
    return "other"


def _loc(v: Any, lang: str = "en"):
    if isinstance(v, dict):
        return v.get(lang) if lang != "en" else (v.get("en") or None)
    return v if lang == "en" else None


def _rows(read, path: str) -> Iterable[Dict[str, Any]]:
    return read(path) if os.path.exists(path) else ()


def build_extras(sde_dir: str, read, types: Dict[str, Any], groups_all: Dict[int, Any]) -> Dict[str, Any]:
    p = lambda f: os.path.join(sde_dir, f + ".jsonl")
    out: Dict[str, Any] = {}
    by_name = {a["name"]: a["_key"] for a in _rows(read, p("dogmaAttributes"))}
    for n in range(1, 5):
        WARFARE_BUFF_ATTRS[n] = (by_name.get(f"warfareBuff{n}ID"), by_name.get(f"warfareBuff{n}Value"))
    zh: Dict[str, Dict[str, str]] = {"groups": {}, "categories": {}, "market_groups": {}, "meta_groups": {},
                                     "attributes": {}, "units": {}}

    # market groups (tree) -- Pyfa's market browser / meta variations
    mg = {}
    for m in _rows(read, p("marketGroups")):
        k = str(m["_key"])
        mg[k] = {"name": _loc(m.get("name")), "parent": m.get("parentGroupID"), "has_types": bool(m.get("hasTypes")),
                 "icon": m.get("iconID")}
        if _loc(m.get("name"), "zh"):
            zh["market_groups"][k] = _loc(m.get("name"), "zh")
    out["market_groups"] = mg

    meta = {}
    for m in _rows(read, p("metaGroups")):
        k = str(m["_key"])
        meta[k] = {"name": _loc(m.get("name"))}
        if _loc(m.get("name"), "zh"):
            zh["meta_groups"][k] = _loc(m.get("name"), "zh")
    out["meta_groups"] = meta

    units = {}
    for u in _rows(read, p("dogmaUnits")):
        k = str(u["_key"])
        units[k] = {"name": u.get("name"), "display": _loc(u.get("displayName")), "description": _loc(u.get("description"))}
        if _loc(u.get("displayName"), "zh"):
            zh["units"][k] = _loc(u.get("displayName"), "zh")
    out["units"] = units

    for g in _rows(read, p("groups")):
        if _loc(g.get("name"), "zh"):
            zh["groups"][str(g["_key"])] = _loc(g.get("name"), "zh")
    for c in _rows(read, p("categories")):
        if _loc(c.get("name"), "zh"):
            zh["categories"][str(c["_key"])] = _loc(c.get("name"), "zh")
    for a in _rows(read, p("dogmaAttributes")):
        if _loc(a.get("displayName"), "zh"):
            zh["attributes"][str(a["_key"])] = _loc(a.get("displayName"), "zh")

    # traits / ship bonus text (Pyfa "traits"): role, per-skill and misc bonuses, en + zh
    traits = {}
    for t in _rows(read, p("typeBonus")):
        k = str(t["_key"])
        if k not in types:
            continue

        def bon(lst):
            res = []
            for b in lst or []:
                res.append({"bonus": b.get("bonus"), "unit": b.get("unitID"), "importance": b.get("importance"),
                            "text": _loc(b.get("bonusText")), "text_zh": _loc(b.get("bonusText"), "zh")})
            return res
        entry = {}
        if t.get("roleBonuses"):
            entry["role"] = bon(t["roleBonuses"])
        if t.get("miscBonuses"):
            entry["misc"] = bon(t["miscBonuses"])
        if t.get("types"):
            entry["skills"] = {str(s["_key"]): bon(s["_value"]) for s in t["types"]}
        if entry:
            traits[k] = entry
    out["traits"] = traits

    # required skills (derived from requiredSkillN / requiredSkillNLevel attributes)
    req = {}
    for k, t in types.items():
        a = t.get("attrs", {})
        lst = []
        for s_attr, l_attr in REQ_SKILL_ATTRS:
            s = a.get(str(s_attr))
            if s:
                lst.append([int(s), int(a.get(str(l_attr), 1) or 1)])
        if lst:
            req[k] = lst
    out["required_skills"] = req

    # alpha clone skill caps
    clones = {}
    for c in _rows(read, p("cloneGrades")):
        clones[str(c["_key"])] = {"name": c.get("name"), "skills": {str(s["typeID"]): s["level"] for s in c.get("skills", [])}}
    out["clone_grades"] = clones

    # environment: effect beacons (Celestial types with dogma) per system, wormhole classes, system-wide dbuffs
    regions = {r["_key"]: r for r in _rows(read, p("mapRegions"))}
    consts = {c["_key"]: c for c in _rows(read, p("mapConstellations"))}
    beacon_of = {s["solarSystemID"]: s.get("effectBeaconTypeID") for s in _rows(read, p("mapSecondarySuns"))}
    systems = {}
    for s in _rows(read, p("mapSolarSystems")):
        c = consts.get(s.get("constellationID"), {})
        r = regions.get(c.get("regionID") or s.get("regionID"), {})
        wc = s.get("wormholeClassID") or c.get("wormholeClassID") or r.get("wormholeClassID")
        beacon = beacon_of.get(s["_key"])
        if beacon is None and (wc is None or wc in (7, 8, 9)):
            continue  # k-space without an effect: not needed for fitting
        systems[str(s["_key"])] = {"name": _loc(s.get("name")), "wormhole_class": wc, "effect_beacon": beacon,
                                   "security": s.get("securityStatus"), "region": r.get("_key")}
    beacons = {}
    for k, t in types.items():
        gname = groups_all.get(t["group"], {}).get("name")
        if t.get("category") == 2 and t.get("effects") and gname in ENV_GROUPS:
            a = t.get("attrs", {})
            # warfare buffs the beacon emits (Pyfa applies them like fleet command bursts): warfareBuffNID/Value
            buffs = {}
            for n in range(1, 5):
                bid = a.get(str(WARFARE_BUFF_ATTRS[n][0]))
                if bid:
                    buffs[str(int(bid))] = a.get(str(WARFARE_BUFF_ATTRS[n][1]), 0.0)
            beacons[k] = {"name": t["name"], "group": t["group"], "group_name": gname, "kind": beacon_kind(t["name"], gname),
                          "dbuffs": buffs}
    sw = {}
    for e in _rows(read, p("systemWideEffects")):
        sw[str(e["_key"])] = {"dbuffs": {str(d["_key"]): d["_value"] for d in e.get("dbuffs", [])},
                              "eligible_type_list": e.get("eligibleTypeListID")}
    tl_needed = {v["eligible_type_list"] for v in sw.values() if v["eligible_type_list"]}
    type_lists = {}
    for tl in _rows(read, p("typeLists")):
        if tl["_key"] in tl_needed:
            type_lists[str(tl["_key"])] = {"name": tl.get("name"), "included_types": tl.get("includedTypeIDs", []),
                                           "included_groups": tl.get("includedGroupIDs", []),
                                           "included_categories": tl.get("includedCategoryIDs", []),
                                           "excluded_types": tl.get("excludedTypeIDs", [])}
    out["environment"] = {"wormhole_classes": {str(k): v for k, v in WORMHOLE_CLASS_LABELS.items()},
                          "systems": systems, "effect_beacons": beacons,
                          "system_wide_effects": sw, "type_lists": type_lists}
    out["names_i18n"] = {"zh": zh}
    return out
