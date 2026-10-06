#!/usr/bin/env python3
"""Generate fitting-tool preset data that the SDE does not ship as such (damage profiles, target profiles,
implant sets, search aliases, character skill presets, NPC damage types).

Two outputs, kept apart on purpose because their licences differ:

* presets/presets.json        derived from CCP's SDE (CCP third-party developer licence, see LICENSE.EVE) by the
                              rules in this script, plus hand-written EX-CT tables (MIT). No Pyfa data.
* presets/presets-pyfa.json   optional: Pyfa's built-in damage patterns / target profiles (eos, LGPL-2.1-or-later)
                              and its search jargon table (service/jargon, GPL-3.0-or-later), read as data from a
                              Pyfa checkout (`--pyfa`). Only the literal data tables are extracted (parsed with
                              `ast` / a minimal YAML-list reader); no Pyfa code is used or copied.

Usage:
    python tools/make_presets.py --sde SDE_JSONL_DIR [--pyfa PYFA_DIR] [--out presets]

Pure stdlib, deterministic (sorted keys, no timestamps besides the SDE build/release date in the input).
"""
import argparse
import ast
import json
import os
import re
import statistics
import subprocess
import sys

GENERATOR = "tools/make_presets.py"
FORMAT_VERSION = 1
DMG = ("em", "thermal", "kinetic", "explosive")
DMG_ATTR = {"em": "emDamage", "thermal": "thermalDamage", "kinetic": "kineticDamage", "explosive": "explosiveDamage"}
RES_ATTR = {
    "shield": {"em": "shieldEmDamageResonance", "thermal": "shieldThermalDamageResonance",
               "kinetic": "shieldKineticDamageResonance", "explosive": "shieldExplosiveDamageResonance"},
    "armor": {"em": "armorEmDamageResonance", "thermal": "armorThermalDamageResonance",
              "kinetic": "armorKineticDamageResonance", "explosive": "armorExplosiveDamageResonance"},
    "hull": {"em": "emDamageResonance", "thermal": "thermalDamageResonance",
             "kinetic": "kineticDamageResonance", "explosive": "explosiveDamageResonance"},
}
HP_ATTR = {"shield": "shieldCapacity", "armor": "armorHP", "hull": "hp"}

CCP_LICENSE = {
    "id": "CCP-EVE-third-party",
    "text": "EVE Online data (c) CCP hf., used under CCP's third-party developer licence; see LICENSE.EVE",
}
MIT_LICENSE = {"id": "MIT", "text": "EX-CT hand-written table, MIT (see LICENSE)"}

# ---------------------------------------------------------------------------------------------------------------
# NPC classification rules (EX-CT, MIT). NPC types are SDE category 11 (Entity). The faction comes from the type's
# factionID when present, else from keywords in the group name (first match wins; order matters: e.g. "Hidden Zenith
# Drifters" must be Drifters, not an empire).
FACTION_KEYWORDS = [
    ("Drifters", ("Drifter",)),
    ("Sleepers", ("Sleeper",)),
    ("Triglavian Collective", ("Triglavian",)),
    ("EDENCOM", ("EDENCOM",)),
    ("Rogue Drones", ("Rogue Drone",)),
    ("Angel Cartel", ("Angel",)),
    ("Blood Raider Covenant", ("Blood Raider",)),
    ("Guristas Pirates", ("Guristas",)),
    ("Sansha's Nation", ("Sansha",)),
    ("Serpentis", ("Serpentis",)),
    ("Mordu's Legion Command", ("Mordu",)),
    ("CONCORD Assembly", ("CONCORD", "Concord")),
    ("Khanid Kingdom", ("Khanid",)),
    ("Thukker Tribe", ("Thukker",)),
    ("Amarr Empire", ("Amarr",)),
    ("Caldari State", ("Caldari",)),
    ("Gallente Federation", ("Gallente",)),
    ("Minmatar Republic", ("Minmatar",)),
]
# context = how the NPCs are met, from the group name's first word(s)
CONTEXT_PREFIXES = [
    ("Asteroid", "asteroid_belt"), ("Deadspace", "deadspace"), ("Mission", "mission"), ("Storyline", "mission"),
    ("FW", "faction_warfare"), ("Incursion", "incursion"), ("Roaming", "roaming"), ("Ghost Sites", "ghost_site"),
    ("Hidden Zenith", "hidden_zenith"), ("Insurgency", "insurgency"), ("Homefront", "homefront"),
    ("Warpath", "warpath"), ("Abyssal", "abyssal"), ("Fabricator", "fabricator"),
]
# hull class from the group name (whole-word, case-insensitive; first match wins)
HULL_CLASSES = [
    ("titan", ("Titan",)), ("supercarrier", ("Supercarrier", "Super Carrier")), ("dreadnought", ("Dreadnought",)),
    ("carrier", ("Carrier",)), ("force_auxiliary", ("Force Auxiliary",)), ("capital", ("Capital",)),
    ("battleship", ("Battleship", "Battleships")), ("battlecruiser", ("BattleCruiser", "Battlecruiser",
                                                                      "Battlecruisers", "Battle Cruisers")),
    ("cruiser", ("Cruiser", "Cruisers")), ("destroyer", ("Destroyer", "Destroyers")),
    ("frigate", ("Frigate", "Frigates")), ("drone", ("Drone", "Swarm")),
]

# ---------------------------------------------------------------------------------------------------------------
# Search aliases (EX-CT, MIT): common EVE community abbreviations -> expansion (case-insensitive phrase matched
# against English type names). Written for EX-CT from general community usage; each alias is kept only if its
# expansion matches at least one published type, and the matching type ids are listed in the output.
ALIASES = {
    # propulsion / navigation
    "ab": "afterburner", "mwd": "microwarpdrive", "mjd": "micro jump drive", "mjfg": "micro jump field generator",
    "nano": "nanofiber internal structure", "ods": "overdrive injector system", "istab": "inertial stabilizer",
    "hyperspatial": "hyperspatial velocity optimizer", "cloak": "cloaking device",
    # tackle / ewar
    "scram": "warp scrambler", "point": "warp disruptor", "disruptor": "warp disruptor", "web": "stasis webifier",
    "webs": "stasis webifier", "neut": "energy neutralizer", "nos": "nosferatu", "tp": "target painter",
    "painter": "target painter", "damp": "remote sensor dampener", "rsd": "remote sensor dampener",
    "td": "tracking disruptor", "gd": "guidance disruptor", "ecm": "ecm", "bubble": "warp disruption field generator",
    "wdfg": "warp disruption field generator", "hic": "heavy interdiction cruiser", "eccm": "eccm",
    "sebo": "sensor booster", "rsb": "remote sensor booster", "sb": "smartbomb",
    # tank
    "dc": "damage control", "dcu": "damage control", "lse": "large shield extender",
    "mse": "medium shield extender", "sse": "small shield extender", "asb": "ancillary shield booster",
    "xlasb": "x-large ancillary shield booster", "lasb": "large ancillary shield booster",
    "masb": "medium ancillary shield booster", "aar": "ancillary armor repairer", "eanm": "energized adaptive nano membrane",
    "anp": "adaptive nano plating", "rah": "reactive armor hardener", "ar": "armor repairer",
    "sba": "shield boost amplifier", "invuln": "multispectrum shield hardener", "invu": "multispectrum shield hardener",
    "plate": "armor plate", "trimark": "trimark armor pump", "cdfe": "core defense field extender",
    "scr": "shield power relay", "pdu": "power diagnostic system", "rcu": "reactor control unit",
    "cpr": "capacitor power relay", "ccc": "capacitor control circuit", "cb": "cap booster", "cap": "capacitor",
    "rar": "remote armor repairer", "rsr": "remote shield booster", "rep": "repairer",
    # damage
    "bcs": "ballistic control system", "mfs": "magnetic field stabilizer", "hs": "heat sink", "gyro": "gyrostabilizer",
    "dda": "drone damage amplifier", "te": "tracking enhancer", "tc": "tracking computer", "mgc": "missile guidance computer",
    "mge": "missile guidance enhancer", "ecu": "entropic radiation sink", "vorton": "vorton projector",
    "hml": "heavy missile launcher", "haml": "heavy assault missile launcher", "rlml": "rapid light missile launcher",
    "rhml": "rapid heavy missile launcher", "lml": "light missile launcher", "cml": "cruise missile launcher",
    "torp": "torpedo launcher", "rl": "rocket launcher", "xl": "x-large", "ac": "autocannon", "arty": "artillery",
    "rail": "railgun", "blaster": "blaster", "pulse": "pulse laser", "beam": "beam laser", "ion": "ion blaster",
    "neutron": "neutron blaster", "mega": "mega", "dis": "disintegrator", "ddd": "doomsday",
    # drones
    "hobgob": "hobgoblin", "ogre": "ogre", "ec": "ec-", "wasp": "wasp", "hammer": "hammerhead",
    # rigs and misc
    "ancil": "ancillary", "mtu": "mobile tractor unit",
    "mju": "micro jump unit", "nrp": "nanite repair paste", "lo": "liquid ozone",
    # meta / faction
    "t1": " i", "t2": " ii", "rf": "republic fleet", "cn": "caldari navy", "fn": "federation navy",
    "in": "imperial navy", "dg": "dread guristas", "ds": "domination", "tss": "true sansha", "sh": "shadow serpentis",
    "db": "dark blood", "cs": "caldari state", "ore": "ore",
}

# ---------------------------------------------------------------------------------------------------------------


def jl(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def en(x):
    return (x or {}).get("en") if isinstance(x, dict) else x


def r6(x):
    return float(f"{x:.6g}") if isinstance(x, float) else x


def norm4(v):
    s = sum(v)
    return [r6(x / s) for x in v] if s > 0 else [0.25, 0.25, 0.25, 0.25]


class SDE:
    def __init__(self, d):
        self.dir = d
        meta = next(jl(os.path.join(d, "_sde.jsonl")))
        self.build, self.release = meta.get("buildNumber"), meta.get("releaseDate")
        self.cats = {c["_key"]: c for c in jl(os.path.join(d, "categories.jsonl"))}
        self.groups = {g["_key"]: g for g in jl(os.path.join(d, "groups.jsonl"))}
        self.types = {t["_key"]: t for t in jl(os.path.join(d, "types.jsonl"))}
        self.factions = {f["_key"]: f for f in jl(os.path.join(d, "factions.jsonl"))}
        self.attrs = {a["_key"]: a for a in jl(os.path.join(d, "dogmaAttributes.jsonl"))}
        self.aid = {a["name"]: k for k, a in self.attrs.items()}
        self.adef = {k: a.get("defaultValue", 0.0) for k, a in self.attrs.items()}
        self.effect_name = {e["_key"]: e["name"] for e in jl(os.path.join(d, "dogmaEffects.jsonl"))}
        self.dogma, self.effects = {}, {}
        for t in jl(os.path.join(d, "typeDogma.jsonl")):
            self.dogma[t["_key"]] = {a["attributeID"]: a["value"] for a in t.get("dogmaAttributes", [])}
            self.effects[t["_key"]] = {self.effect_name.get(e["effectID"]) for e in t.get("dogmaEffects", [])}
        self.clone_grades = list(jl(os.path.join(d, "cloneGrades.jsonl")))

    def cat_of(self, tid):
        return self.groups[self.types[tid]["groupID"]]["categoryID"]

    def group_name(self, tid):
        return en(self.groups[self.types[tid]["groupID"]]["name"]) or ""

    def name(self, tid):
        return en(self.types[tid].get("name")) or ""

    def attr(self, tid, name, default=None):
        a = self.aid.get(name)
        if a is None:
            return default
        v = self.dogma.get(tid, {}).get(a)
        if v is None:
            return self.adef.get(a, 0.0) if default is None else default
        return v


# ---------------------------------------------------------------------------------------------------------------
# NPCs


def classify_npc(sde, tid):
    t = sde.types[tid]
    g = sde.group_name(tid)
    fac = None
    how = None
    if t.get("factionID") in sde.factions:
        fac, how = en(sde.factions[t["factionID"]]["name"]), "type.factionID"
    else:
        for name, kws in FACTION_KEYWORDS:
            if any(k in g for k in kws):
                fac, how = name, "group-name keyword"
                break
    ctx = "other"
    for p, c in CONTEXT_PREFIXES:
        if g.startswith(p):
            ctx = c
            break
    hull = None
    for h, kws in HULL_CLASSES:
        if any(re.search(r"\b" + re.escape(k) + r"\b", g) for k in kws):
            hull = h
            break
    return fac, how, ctx, hull, g


NPC_TURRET_EFFECTS = {"targetAttack", "projectileFired", "targetDisintegratorAttack"}
NPC_MISSILE_EFFECTS = {"missileLaunchingForEntity"}


def npc_dps(sde, tid):
    """turret + missile damage per second by type (NPC entity attributes; a weapon counts only when the type has
    the matching weapon effect: leftover weapon attributes without the effect deal no damage)"""
    out = [0.0, 0.0, 0.0, 0.0]
    effs = sde.effects.get(tid, set())
    speed = sde.attr(tid, "speed", 0.0)
    if speed > 0 and effs & NPC_TURRET_EFFECTS:
        mult = sde.attr(tid, "damageMultiplier", 1.0)
        for k, d in enumerate(DMG):
            out[k] += sde.attr(tid, DMG_ATTR[d], 0.0) * mult / (speed / 1000.0)
    mid = int(sde.attr(tid, "entityMissileTypeID", 0.0) or 0)
    if mid and mid in sde.types and effs & NPC_MISSILE_EFFECTS:
        dur = sde.attr(tid, "missileLaunchDuration", 20000.0)
        mm = sde.attr(tid, "missileDamageMultiplier", 1.0)
        if dur > 0:
            for k, d in enumerate(DMG):
                out[k] += sde.attr(mid, DMG_ATTR[d], 0.0) * mm / (dur / 1000.0)
    return out


def build_npc(sde):
    npcs = []
    for tid in sorted(sde.types):
        if sde.cat_of(tid) != 11:
            continue
        fac, how, ctx, hull, g = classify_npc(sde, tid)
        dps = npc_dps(sde, tid)
        hp = {l: sde.attr(tid, HP_ATTR[l], 0.0) for l in HP_ATTR}
        res = {l: {d: 1.0 - sde.attr(tid, RES_ATTR[l][d], 1.0) for d in DMG} for l in RES_ATTR}
        npcs.append({"type_id": tid, "name": sde.name(tid), "group": g, "faction": fac, "faction_source": how,
                     "context": ctx, "hull": hull, "dps": dps, "hp": hp, "resist": res,
                     "signature_radius": sde.attr(tid, "signatureRadius", 0.0),
                     "max_velocity": sde.attr(tid, "maxVelocity", 0.0), "radius": sde.types[tid].get("radius")})
    return npcs


def hp_weighted_resist(n):
    tot = sum(n["hp"].values())
    if tot <= 0:
        return None
    return [sum(n["hp"][l] * n["resist"][l][d] for l in n["hp"]) / tot for d in DMG]


def npc_sections(npcs):
    armed = [n for n in npcs if sum(n["dps"]) > 0]
    # per-type damage table
    types = [{"type_id": n["type_id"], "name": n["name"], "group": n["group"], "faction": n["faction"],
              "context": n["context"], "hull": n["hull"], "dps": [r6(x) for x in n["dps"]],
              "dps_total": r6(sum(n["dps"])), "damage_share": norm4(n["dps"]),
              "primary": [DMG[k] for k in sorted(range(4), key=lambda k: -n["dps"][k]) if n["dps"][k] > 0][:2]}
             for n in armed]

    def agg(key):
        acc = {}
        for n in armed:
            k = key(n)
            if k is None or k[0] is None:
                continue
            a = acc.setdefault(k, [[0.0] * 4, 0, [0.0] * 4])
            sh = norm4(n["dps"])
            for i in range(4):
                a[0][i] += n["dps"][i]
                a[2][i] += sh[i]
            a[1] += 1
        return acc

    fac = agg(lambda n: (n["faction"],))
    fac_ctx = agg(lambda n: (n["faction"], n["context"]))
    profiles = []
    for (f,), (v, c, m) in sorted(fac.items()):
        profiles.append({"id": f"npc.{slug(f)}", "name": f"[NPC] {f}", "faction": f, "context": None,
                         "ratio": norm4(v), "ratio_type_mean": norm4(m), "npc_types": c})
    for (f, ctx), (v, c, m) in sorted(fac_ctx.items()):
        if ctx == "other":
            continue
        profiles.append({"id": f"npc.{slug(f)}.{ctx}", "name": f"[NPC][{ctx}] {f}", "faction": f, "context": ctx,
                         "ratio": norm4(v), "ratio_type_mean": norm4(m), "npc_types": c})
    damage_types = []
    for (f,), (v, c, m) in sorted(fac.items()):
        share = norm4(v)
        order = sorted(range(4), key=lambda k: -share[k])
        damage_types.append({"faction": f, "share": dict(zip(DMG, share)),
                             "primary": DMG[order[0]], "secondary": DMG[order[1]] if share[order[1]] > 0.05 else None,
                             "npc_types": c})
    # target profiles: median per (faction, hull) over combat NPCs that have HP
    tp = {}
    for n in npcs:
        if n["faction"] is None or n["hull"] is None or sum(n["hp"].values()) <= 0:
            continue
        tp.setdefault((n["faction"], n["hull"]), []).append(n)
    targets = []
    for (f, h), lst in sorted(tp.items()):
        med = lambda xs: r6(statistics.median(xs))  # noqa: E731
        layers = {l: {d: med([x["resist"][l][d] for x in lst]) for d in DMG} for l in RES_ATTR}
        hw = [hp_weighted_resist(x) for x in lst]
        hw = [x for x in hw if x is not None]
        targets.append({"id": f"npc.{slug(f)}.{h}", "name": f"[NPC] {f} {h.replace('_', ' ')}", "faction": f,
                        "hull": h, "resist": dict(zip(DMG, [med([x[k] for x in hw]) for k in range(4)])),
                        "resist_by_layer": layers,
                        "signature_radius": med([x["signature_radius"] for x in lst]),
                        "max_velocity": med([x["max_velocity"] for x in lst]),
                        "radius": med([x["radius"] or 0.0 for x in lst]),
                        "hp": {l: med([x["hp"][l] for x in lst]) for l in HP_ATTR}, "npc_types": len(lst)})
    return types, profiles, damage_types, targets


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


# ---------------------------------------------------------------------------------------------------------------


def ammo_profiles(sde):
    out = []
    for tid in sorted(sde.types):
        t = sde.types[tid]
        if not t.get("published") or sde.cat_of(tid) != 8:
            continue
        v = [sde.attr(tid, DMG_ATTR[d], 0.0) for d in DMG]
        if sum(v) <= 0:
            continue
        out.append({"id": f"ammo.{tid}", "type_id": tid, "name": sde.name(tid), "group": sde.group_name(tid),
                    "damage": [r6(x) for x in v], "ratio": norm4(v)})
    return out


def generic_damage_profiles():
    base = [("uniform", "Uniform", [1, 1, 1, 1])] + [(d, f"[Generic] {d.capitalize()}", [int(d == x) for x in DMG])
                                                     for d in DMG]
    return [{"id": f"generic.{k}", "name": n, "ratio": norm4([float(x) for x in v])} for k, n, v in base]


def generic_target_profiles():
    out = [{"id": "ideal", "name": "Ideal target", "resist": dict.fromkeys(DMG, 0.0), "signature_radius": None,
            "max_velocity": 0.0, "radius": None, "note": "no resistances, infinite signature, stationary"}]
    for p in (25, 50, 75, 90):
        out.append({"id": f"uniform.{p}", "name": f"Uniform ({p}%)", "resist": dict.fromkeys(DMG, p / 100.0),
                    "signature_radius": None, "max_velocity": None, "radius": None})
    return out


def implant_sets(sde):
    """implants carrying an implantSet* attribute (the set-bonus multiplier), grouped by attribute and grade"""
    # Only real set-bonus multipliers: skip per-implant modifiers (implantSetHackingVirusCoherenceModifier, which
    # scales 1..5 by slot) and client display copies (...SetBonusFAKE), which would otherwise form bogus "sets".
    set_attrs = {k: a for k, a in sde.attrs.items() if a["name"].startswith("implantSet")
                 and not a["name"].endswith("Modifier") and not a["name"].upper().endswith("FAKE")}
    sets = {}
    for tid in sorted(sde.types):
        t = sde.types[tid]
        if not t.get("published") or sde.cat_of(tid) != 20:
            continue
        d = sde.dogma.get(tid, {})
        for aid, a in set_attrs.items():
            if aid not in d:
                continue
            nm = sde.name(tid)
            m = re.match(r"^(Low-grade|Mid-grade|High-grade)\s+(.*?)\s+(Alpha|Beta|Gamma|Delta|Epsilon|Omega)\b", nm)
            grade = m.group(1).lower() if m else None
            disp = m.group(2) if m else (en(a.get("displayName")) or a["name"])
            sets.setdefault((a["name"], grade), {"attr": a, "disp": disp, "members": []})["members"].append(
                {"type_id": tid, "name": nm, "slot": int(sde.attr(tid, "implantness", 0.0) or 0),
                 "set_bonus_multiplier": r6(d[aid])})
    out, seen = [], set()
    for (an, grade), s in sorted(sets.items(), key=lambda x: (x[0][0], x[0][1] or "")):
        mem = sorted(s["members"], key=lambda m: (m["slot"], m["type_id"]))
        setname = re.sub(r"\s*Set [Bb]onus$", "", s["disp"]).strip()
        sid = f"{slug(setname)}.{grade or 'any'}"
        if sid in seen:  # two set attributes on the same implant line (e.g. Wedge): qualify by the attribute
            sid += "." + slug(an)
        seen.add(sid)
        out.append({"id": sid, "name": f"{grade.capitalize() + ' ' if grade else ''}{setname}",
                    "set_attribute": an, "set_attribute_id": s["attr"]["_key"], "grade": grade,
                    "slots": sorted({m["slot"] for m in mem}), "members": mem,
                    "complete": len({m["slot"] for m in mem}) >= 6})
    return out


def skill_presets(sde):
    skills = sorted(tid for tid, t in sde.types.items() if t.get("published") and sde.cat_of(tid) == 16)
    out = [{"id": f"all{n}", "name": f"All {n}", "default_level": n, "skills": "all_published_skills"}
           for n in range(6)]
    for cg in sorted(sde.clone_grades, key=lambda c: c["_key"]):
        out.append({"id": f"clone_grade.{cg['_key']}", "name": en(cg.get("name")), "default_level": 0,
                    "skills": {str(s["typeID"]): s["level"] for s in cg.get("skills", [])},
                    "note": "alpha clone skill caps from SDE cloneGrades; skills not listed are 0"})
    return skills, out


def aliases(sde):
    names = {}
    for tid, t in sde.types.items():
        if t.get("published") and sde.cat_of(tid) in (6, 7, 8, 18, 20, 22, 32, 65, 66, 87):
            names[tid] = " " + sde.name(tid).lower() + " "
    out, dropped = [], []
    for a, exp in sorted(ALIASES.items()):
        e = exp.lower()
        if e.strip() in ("i", "ii"):  # meta suffix aliases: match the name ending
            ids = sorted(tid for tid, n in names.items() if n.rstrip().endswith(" " + e.strip()))
        else:
            rx = re.compile((r"\b" if e[0].isalnum() else "") + re.escape(e) + (r"\b" if e[-1].isalnum() else ""))
            ids = sorted(tid for tid, n in names.items() if rx.search(n))
        if ids:
            out.append({"alias": a, "expansion": exp.strip(), "type_ids": ids, "matches": len(ids)})
        else:
            dropped.append(a)
    return out, dropped


# ---------------------------------------------------------------------------------------------------------------
# Pyfa data tables (optional, separate output)


def _eval_builtin(node):
    """evaluate the literal data of a Pyfa BUILTINS table: tuples, numbers, strings, '+', and the identity /
    bracket helpers _t(x) / _c(x)"""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_builtin(node.operand)
    if isinstance(node, ast.Tuple) or isinstance(node, ast.List):
        return [_eval_builtin(e) for e in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _eval_builtin(node.left) + _eval_builtin(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("_t", "_c") \
            and len(node.args) == 1:
        v = _eval_builtin(node.args[0])
        return v if node.func.id == "_t" else "[" + v + "]"
    raise ValueError(f"unexpected node {ast.dump(node)[:80]}")


def pyfa_builtins(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for st in tree.body:
        if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BUILTINS" for t in st.targets):
            call = st.value  # OrderedDict([...])
            return [_eval_builtin(e) for e in call.args[0].elts]
    raise ValueError(f"no BUILTINS in {path}")


def pyfa_jargon(path):
    """service/jargon/defaults.yaml: `key:` followed by `- 'pattern'` items (minimal reader for this layout)"""
    out, cur = {}, None
    for line in open(path, encoding="utf-8"):
        s = line.split("#", 1)[0].rstrip() if not line.lstrip().startswith("- '") else line.rstrip()
        if not s.strip():
            continue
        m = re.match(r"^(\S.*):\s*$", s)
        if m:
            cur = m.group(1).strip().strip("'\"")
            out[cur] = []
            continue
        m = re.match(r"^\s+-\s+'((?:[^']|'')*)'", s)
        if m and cur is not None:
            out[cur].append(m.group(1).replace("''", "'"))
    return out


def git_rev(d):
    try:
        return subprocess.run(["git", "-C", d, "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_pyfa(pyfa):
    rev = git_rev(pyfa)
    dp = pyfa_builtins(os.path.join(pyfa, "eos/saveddata/damagePattern.py"))
    tp = pyfa_builtins(os.path.join(pyfa, "eos/saveddata/targetProfile.py"))
    jg = pyfa_jargon(os.path.join(pyfa, "service/jargon/defaults.yaml"))
    tp_fields = ("em", "thermal", "kinetic", "explosive", "max_velocity", "signature_radius", "radius", "hp")
    lgpl = {"id": "LGPL-2.1-or-later", "text": "Pyfa eos (c) Diego Duclos and contributors, GNU LGPL v2.1 or "
                                                "later (file header of eos/saveddata/*.py)"}
    gpl = {"id": "GPL-3.0-or-later", "text": "Pyfa (c) Pyfa contributors, GNU GPL v3 or later (Pyfa LICENSE)"}
    src = lambda f: {"repo": "https://github.com/pyfa-org/Pyfa", "commit": rev, "file": f}  # noqa: E731
    return {
        "format": "exct-presets-pyfa", "format_version": FORMAT_VERSION, "generator": GENERATOR,
        "notice": "Data tables extracted from Pyfa as data only (no code). Copyleft licences apply to this file: "
                  "keep it separate from MIT/CCP-licensed outputs and comply with LGPL/GPL when redistributing.",
        "damage_patterns": {
            "provenance": src("eos/saveddata/damagePattern.py (BUILTINS)"), "license": lgpl,
            "fields": ["pyfa_id", "name", "em", "thermal", "kinetic", "explosive"],
            "items": [{"pyfa_id": i, "name": v[0], "amounts": dict(zip(DMG, v[1:5])), "ratio": norm4([float(x) for x in v[1:5]])}
                      for i, v in dp],
        },
        "target_profiles": {
            "provenance": src("eos/saveddata/targetProfile.py (BUILTINS)"), "license": lgpl,
            "items": [dict({"pyfa_id": i, "name": v[0]}, **{k: x for k, x in zip(tp_fields, v[1:])}) for i, v in tp],
        },
        "jargon": {
            "provenance": src("service/jargon/defaults.yaml"), "license": gpl,
            "note": "key -> [regex patterns...]; the last pattern is the replacement in Pyfa's jargon semantics "
                    "(single-item lists: the key itself is the pattern)",
            "items": jg,
        },
    }


# ---------------------------------------------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sde", required=True, help="directory with the SDE JSONL files")
    ap.add_argument("--pyfa", help="optional Pyfa checkout for presets-pyfa.json")
    ap.add_argument("--out", default="presets")
    a = ap.parse_args()
    sde = SDE(a.sde)
    sde_src = {"source": "CCP EVE Online Static Data Export (JSONL)", "build": sde.build,
               "release_date": sde.release, "url": "https://developers.eveonline.com/static-data"}
    npcs = build_npc(sde)
    npc_types, npc_profiles, npc_dt, npc_targets = npc_sections(npcs)
    skills, sk_presets = skill_presets(sde)
    al, al_dropped = aliases(sde)
    imps = implant_sets(sde)
    ammo = ammo_profiles(sde)

    def prov(method, files, lic=CCP_LICENSE, extra=None):
        p = {"sde": sde_src, "sde_files": files, "method": method, "generator": GENERATOR, "license": lic}
        if extra:
            p.update(extra)
        return p

    out = {
        "format": "exct-presets", "format_version": FORMAT_VERSION, "sde_build": sde.build,
        "sde_release_date": sde.release, "generator": GENERATOR,
        "licenses": {"data": CCP_LICENSE, "rules_and_hand_written_tables": MIT_LICENSE},
        "damage_types": list(DMG),
        "damage_profiles": {
            "generic": {"provenance": {"method": "definition (uniform and single damage type)", "license": MIT_LICENSE,
                                       "generator": GENERATOR}, "items": generic_damage_profiles()},
            "ammo": {"provenance": prov("published charges (category 8) with damage attributes; ratio = damage / "
                                        "sum (base values, no skills or launcher bonuses)",
                                        ["types", "groups", "typeDogma"]), "items": ammo},
            "npc": {"provenance": prov("sum of NPC entity DPS by damage type (turret: damage attrs x damageMultiplier"
                                       " / speed; missile: entityMissileTypeID charge damage x missileDamageMultiplier"
                                       " / missileLaunchDuration) over the NPC types of a faction (and context); "
                                       "unweighted by spawn frequency; `ratio` = DPS-weighted, `ratio_type_mean` = mean of the per-type ratios",
                                       ["types", "groups", "typeDogma", "dogmaEffects", "factions"],
                                       extra={"classification_rules": "FACTION_KEYWORDS / CONTEXT_PREFIXES in the "
                                                                      "generator (MIT)"}),
                    "items": npc_profiles},
        },
        "target_profiles": {
            "generic": {"provenance": {"method": "definition", "license": MIT_LICENSE, "generator": GENERATOR},
                        "items": generic_target_profiles()},
            "npc": {"provenance": prov("median over the NPC types of a (faction, hull class): resist = 1 - "
                                       "resonance per layer and HP-weighted over shield/armor/hull; signature radius,"
                                       " max velocity, radius, HP", ["types", "groups", "typeDogma", "factions"],
                                       extra={"classification_rules": "FACTION_KEYWORDS / HULL_CLASSES in the "
                                                                      "generator (MIT)"}),
                    "items": npc_targets},
        },
        "npc_damage_types": {
            "provenance": prov("as damage_profiles.npc; per faction share, primary and secondary (share > 5 %) "
                               "damage type; per NPC type DPS by damage type", ["types", "groups", "typeDogma",
                                                                               "factions"]),
            "factions": npc_dt, "types": npc_types,
        },
        "implant_sets": {
            "provenance": prov("published implants (category 20) carrying an implantSet* attribute (the set bonus "
                               "multiplier), grouped by that attribute and the Low/Mid/High-grade name prefix; slot "
                               "= implantness; set name = the members' common name between the grade prefix "
                               "and the Greek slot letter (else the attribute's display name)",
                               ["types", "groups", "typeDogma", "dogmaAttributes"]),
            "items": imps,
        },
        "character_skill_presets": {
            "provenance": prov("All 0..All 5: every published skill (category 16) at that level; clone grades "
                               "(alpha clones) from cloneGrades", ["types", "groups", "cloneGrades"]),
            "published_skills": skills, "items": sk_presets,
        },
        "search_aliases": {
            "provenance": {"method": "hand-written EX-CT abbreviation table (ALIASES in the generator) resolved "
                                     "against published English type names (whole-word phrase, case-insensitive; t1/t2 by "
                                     "name suffix); aliases without a match are dropped", "license": MIT_LICENSE,
                           "names": sde_src, "names_license": CCP_LICENSE, "generator": GENERATOR},
            "items": al, "dropped_no_match": al_dropped,
        },
    }
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "presets.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    counts = {
        "damage_profiles.generic": len(out["damage_profiles"]["generic"]["items"]),
        "damage_profiles.ammo": len(ammo), "damage_profiles.npc": len(npc_profiles),
        "target_profiles.generic": len(out["target_profiles"]["generic"]["items"]),
        "target_profiles.npc": len(npc_targets), "npc_damage_types.factions": len(npc_dt),
        "npc_damage_types.types": len(npc_types), "implant_sets": len(imps),
        "character_skill_presets": len(sk_presets), "published_skills": len(skills), "search_aliases": len(al),
    }
    if a.pyfa:
        p = build_pyfa(a.pyfa)
        with open(os.path.join(a.out, "presets-pyfa.json"), "w", encoding="utf-8") as f:
            json.dump(p, f, indent=1, sort_keys=True, ensure_ascii=False)
            f.write("\n")
        counts.update({"pyfa.damage_patterns": len(p["damage_patterns"]["items"]),
                       "pyfa.target_profiles": len(p["target_profiles"]["items"]),
                       "pyfa.jargon": len(p["jargon"]["items"])})
    json.dump(counts, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
