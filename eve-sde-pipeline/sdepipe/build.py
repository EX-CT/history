"""Convert CCP's JSONL SDE into the EXCT engine dataset (format v1).

Deterministic: same input -> byte-identical output (sorted keys, no timestamps).
Only the Python standard library is used so it runs anywhere (GitHub Actions, dev boxes).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from typing import Any, Dict, Iterator

from . import DATASET_REVISION, FORMAT, FORMAT_VERSION, __version__
from .extras import build_extras

# Categories relevant to fitting.
FIT_CATEGORIES = {
    6,   # Ship
    7,   # Module
    8,   # Charge
    16,  # Skill
    18,  # Drone
    20,  # Implant (implants + boosters)
    32,  # Subsystem
    65,  # Structure
    66,  # Structure Module
    87,  # Fighter
}
EXTRA_TYPES = {1373}  # Character type (owner of skills; char attributes like maxActiveDrones)
CELESTIAL_CATEGORY = 2  # effect beacons (wormhole / abyssal / incursion / system effects) when they carry dogma

FUNC_CODES = {
    "ItemModifier": 0,
    "LocationModifier": 1,
    "LocationGroupModifier": 2,
    "LocationRequiredSkillModifier": 3,
    "OwnerRequiredSkillModifier": 4,
    "EffectStopper": 5,
}
DOMAIN_CODES = {
    "itemID": 0, "shipID": 1, "charID": 2, "otherID": 3, "structureID": 4, "targetID": 5, "target": 6,
}
# CCP operation name -> numeric code used in modifierInfo
OP_NAMES = {
    "PreAssign": -1, "PreMul": 0, "PreDiv": 1, "ModAdd": 2, "ModSub": 3,
    "PostMul": 4, "PostDiv": 5, "PostPercent": 6, "PostAssign": 7,
}
LANGS = ("en", "zh")


def read_jsonl(path: str) -> Iterator[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def _name(obj: Dict[str, Any], lang: str = "en") -> str | None:
    n = obj.get("name")
    if isinstance(n, dict):
        return n.get(lang) or n.get("en")
    return n


def _opt(d: Dict[str, Any], key: str):
    v = d.get(key)
    return v if v not in (0, None) else None


def build(sde_dir: str) -> Dict[str, Any]:
    p = lambda f: os.path.join(sde_dir, f + ".jsonl")
    meta = next(read_jsonl(p("_sde")))

    categories = {}
    for c in read_jsonl(p("categories")):
        categories[str(c["_key"])] = {"name": _name(c)}

    groups = {}
    for g in read_jsonl(p("groups")):
        groups[g["_key"]] = {"name": _name(g), "category": g["categoryID"]}

    type_dogma = {}
    for td in read_jsonl(p("typeDogma")):
        type_dogma[td["_key"]] = td

    muta = {}
    muta_related = set()
    for m in read_jsonl(p("dynamicItemAttributes")):
        attrs = {str(a["_key"]): [a["min"], a["max"]] for a in m.get("attributeIDs", [])}
        mapping = []
        for io in m.get("inputOutputMapping", []):
            mapping.append({"inputs": sorted(io.get("applicableTypes", [])), "output": io["resultingType"]})
            muta_related.add(io["resultingType"])
            muta_related.update(io.get("applicableTypes", []))
        muta[str(m["_key"])] = {"attrs": attrs, "mapping": mapping}
        muta_related.add(m["_key"])

    types = {}
    names_zh = {}
    for t in read_jsonl(p("types")):
        tid = t["_key"]
        g = groups.get(t["groupID"])
        if g is None:
            continue
        cat = g["category"]
        td = type_dogma.get(tid)
        keep = cat in FIT_CATEGORIES or tid in EXTRA_TYPES or tid in muta_related or (cat == CELESTIAL_CATEGORY and td and td.get("dogmaEffects"))
        if not keep:
            continue
        entry = {
            "name": _name(t),
            "group": t["groupID"],
            "category": cat,
            "published": bool(t.get("published", False)),
            "mass": t.get("mass", 0.0),
            "volume": t.get("volume", 0.0),
            "capacity": t.get("capacity", 0.0),
            "radius": t.get("radius", 0.0),
        }
        for k_src, k_dst in (("marketGroupID", "market_group"), ("metaGroupID", "meta_group"),
                             ("metaLevel", "meta_level"), ("techLevel", "tech_level"),
                             ("variationParentTypeID", "variation_parent"), ("raceID", "race")):
            if t.get(k_src) is not None:
                entry[k_dst] = t[k_src]
        if td:
            entry["attrs"] = {str(a["attributeID"]): a["value"] for a in td.get("dogmaAttributes", [])}
            entry["effects"] = [[e["effectID"], 1 if e.get("isDefault") else 0] for e in td.get("dogmaEffects", [])]
        else:
            entry["attrs"] = {}
            entry["effects"] = []
        types[str(tid)] = entry
        zh = _name(t, "zh")
        if zh and zh != entry["name"]:
            names_zh[str(tid)] = zh

    attributes = {}
    for a in read_jsonl(p("dogmaAttributes")):
        dn = a.get("displayName")
        attributes[str(a["_key"])] = {
            "name": a["name"],
            "default": a.get("defaultValue", 0.0),
            "stackable": bool(a.get("stackable", True)),
            "high_is_good": bool(a.get("highIsGood", True)),
            "min_attr": _opt(a, "minAttributeID"),
            "max_attr": _opt(a, "maxAttributeID"),
            "unit": _opt(a, "unitID"),
            "display": dn.get("en") if isinstance(dn, dict) else dn,
            "published": bool(a.get("published", False)),
        }

    effects = {}
    unknown = set()
    for e in read_jsonl(p("dogmaEffects")):
        mods = []
        for m in e.get("modifierInfo", []) or []:
            func = FUNC_CODES.get(m.get("func"))
            dom = DOMAIN_CODES.get(m.get("domain"))
            if func is None or (dom is None and func != 5):
                unknown.add((m.get("func"), m.get("domain")))
                continue
            extra = m.get("groupID") or m.get("skillTypeID") or 0
            mods.append([func, dom if dom is not None else -1, m.get("modifiedAttributeID", 0),
                         m.get("modifyingAttributeID", 0), m.get("operation", 0), extra])
        effects[str(e["_key"])] = {
            "name": e["name"],
            "category": e.get("effectCategoryID", 0),
            "duration_attr": _opt(e, "durationAttributeID"),
            "discharge_attr": _opt(e, "dischargeAttributeID"),
            "range_attr": _opt(e, "rangeAttributeID"),
            "falloff_attr": _opt(e, "falloffAttributeID"),
            "tracking_attr": _opt(e, "trackingSpeedAttributeID"),
            "resistance_attr": _opt(e, "resistanceAttributeID"),
            "fitting_usage_chance_attr": _opt(e, "fittingUsageChanceAttributeID"),
            "is_offensive": bool(e.get("isOffensive")),
            "is_assistance": bool(e.get("isAssistance")),
            "mods": mods,
        }

    dbuffs = {}
    for b in read_jsonl(p("dbuffCollections")):
        dbuffs[str(b["_key"])] = {
            "name": b.get("developerDescription"),
            "aggregate": b.get("aggregateMode"),
            "op": OP_NAMES.get(b.get("operationName"), 6),
            "item": [m["dogmaAttributeID"] for m in b.get("itemModifiers", [])],
            "location": [m["dogmaAttributeID"] for m in b.get("locationModifiers", [])],
            "location_group": [[m["dogmaAttributeID"], m["groupID"]] for m in b.get("locationGroupModifiers", [])],
            "location_skill": [[m["dogmaAttributeID"], m["skillID"]] for m in b.get("locationRequiredSkillModifiers", [])],
        }

    fighter_abilities = {}
    if os.path.exists(p("fighterAbilitiesByType")):
        for f in read_jsonl(p("fighterAbilitiesByType")):
            slots = []
            for i in range(3):
                s = f.get(f"abilitySlot{i}")
                if s:
                    slots.append({"ability": s["abilityID"], "cooldown_s": s.get("cooldownSeconds"), "charges": s.get("charges", {}).get("chargeCount") if isinstance(s.get("charges"), dict) else None})
            fighter_abilities[str(f["_key"])] = slots

    ds = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "generator": f"eve-sde-pipeline {__version__}",
        "sde": {"build": meta["buildNumber"], "release_date": meta.get("releaseDate")},
        "dataset_revision": DATASET_REVISION,
        "categories": categories,
        "attributes": attributes,
        "effects": effects,
        "types": types,
        "dbuffs": dbuffs,
        "mutaplasmids": muta,
        "fighter_abilities": fighter_abilities,
        "names": {"zh": names_zh},
        "patches": [],
    }
    # keep groups referenced by kept types (e.g. mutaplasmid commodity groups)
    used_groups = {t["group"] for t in types.values()}
    ds["groups"] = {str(k): v for k, v in groups.items() if k in used_groups}
    ds["_unknown_modifiers"] = sorted([list(map(str, u)) for u in unknown])
    ds.update(build_extras(sde_dir, read_jsonl, types, groups))
    return ds


def apply_patches(ds: Dict[str, Any], patch_dir: str) -> None:
    if not os.path.isdir(patch_dir):
        return
    for fn in sorted(os.listdir(patch_dir)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(patch_dir, fn), encoding="utf-8") as fh:
            patch = json.load(fh)
        for section, entries in patch.get("set", {}).items():
            for key, value in entries.items():
                if isinstance(value, dict) and isinstance(ds[section].get(key), dict):
                    ds[section][key].update(value)
                else:
                    ds[section][key] = value
        ds["patches"].append({"id": patch["id"], "description": patch.get("description", "")})


def dataset_filename(build_no: int, revision: int) -> str:
    """Revision 1 kept the historic name; later revisions get a suffix so published files are never overwritten."""
    return f"dataset-{build_no}.json.gz" if revision <= 1 else f"dataset-{build_no}-r{revision}.json.gz"


def release_tag(build_no: int, revision: int) -> str:
    return f"sde-{build_no}" if revision <= 1 else f"sde-{build_no}-r{revision}"


def dump(ds: Dict[str, Any], out_dir: str) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    raw = json.dumps(ds, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    build_no = ds["sde"]["build"]
    path = os.path.join(out_dir, dataset_filename(build_no, ds.get("dataset_revision", 1)))
    with open(path, "wb") as fh:
        # mtime=0 for determinism
        with gzip.GzipFile(fileobj=fh, mode="wb", mtime=0, compresslevel=9, filename="") as gz:
            gz.write(raw)
    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "sde_build": build_no,
        "dataset_revision": ds.get("dataset_revision", 1),
        "release_tag": release_tag(build_no, ds.get("dataset_revision", 1)),
        "sde_release_date": ds["sde"]["release_date"],
        "file": os.path.basename(path),
        "sha256_json": hashlib.sha256(raw).hexdigest(),
        "sha256_gz": hashlib.sha256(open(path, "rb").read()).hexdigest(),
        "bytes_json": len(raw),
        "bytes_gz": os.path.getsize(path),
        "counts": {k: len(ds[k]) for k in ("types", "groups", "attributes", "effects", "dbuffs", "mutaplasmids", "market_groups",
                                            "traits", "required_skills") if k in ds},
        "patches": ds["patches"],
        "generator": ds["generator"],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return manifest
