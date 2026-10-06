#!/usr/bin/env python3
"""Effect suite generator (docs/20 P0-2): one legal micro-fit per dogma effect that Pyfa implements
(eos/effects.py classes, matched by name) and that some dataset type carries.

For effect E: pick a carrier type (published and known to Pyfa's eve.db first, lowest type id), then build a
FitRequest by carrier category, using Pyfa's own fitting rules (Module.fits, getValidCharges, isValidState,
Drone/Fighter.fits) so every case is a fit Pyfa can build:
  module / structure module  fitted on the first candidate hull it fits (state from the effect: overload ->
                             overheated, active/target/area -> active, else online; first valid charge loaded);
                             effects Pyfa marks 'projected' with dataset category target(2) -> projected onto the
                             standard target fit (TARGET below) instead
  charge                     loaded in the first module that accepts it (getValidCharges), that module fitted
  drone / fighter            in the bay of the first candidate hull that takes it, active; projected like modules
                             when the effect is a projected one
  implant / booster          on the standard fit; booster side effects listed in `side_effects` when E is one
  subsystem                  on its T3C with the first subsystem of every other slot
  ship (incl. T3D modes)     that hull (mode_type_id for modes)
  skill                      default_level 0, that skill at 5
  celestial (beacons, weather, clouds)  environment.effect_type_ids on the standard fit
plus "affectees": items E modifies, derived from E's SDE modifiers (LocationGroup -> an item of that group,
Location/OwnerRequiredSkill -> an item requiring that skill, having the modified attribute), fitted when legal.
Output: OUT/cases/eff_<effectID>_<name>.json and OUT/MANIFEST.json (effect id/name, carrier, how, affectees,
handler_only, unverified37, or the skip reason).
Run with the Pyfa venv: cd $PYFA && PYTHONPATH=$STUBS $PYFA_PY effects/tools/gen_effects.py OUT"""
import copy, gzip, json, os, re, sys, tempfile
PYFA = os.environ.get("PYFA", "/workspace/exct-eve/ref/pyfa")
DATASET = os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")
sys.path.insert(0, PYFA)
import config  # noqa
config.defPaths(tempfile.mkdtemp(prefix="eff-gen-"))
import eos.config  # noqa
eos.config.gamedata_connectionstring = "sqlite:///" + os.path.join(PYFA, "eve.db") + "?check_same_thread=False"
import eos.db  # noqa
eos.db.saveddata_meta.create_all(eos.db.saveddata_engine)
from eos.saveddata.character import Character  # noqa
from eos.saveddata.fit import Fit  # noqa
from eos.saveddata.ship import Ship  # noqa
from eos.saveddata.citadel import Citadel  # noqa
from eos.saveddata.module import Module  # noqa
from eos.saveddata.drone import Drone  # noqa
from eos.saveddata.fighter import Fighter  # noqa
from eos.const import FittingModuleState as S, FittingSlot  # noqa

OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, "cases"), exist_ok=True)
D = json.load(gzip.open(DATASET))
T = {int(k): v for k, v in D["types"].items()}
EFF = {int(k): v for k, v in D["effects"].items()}
ANAME = {int(k): v["name"] for k, v in D["attributes"].items()}
src = open(os.path.join(PYFA, "eos/effects.py")).read()
PYCLS = {}
for m in re.finditer(r'^class Effect\d+\(BaseEffect\):\n    """\n    (\w+)\n.*?(?=^class |\Z)', src, re.M | re.S):
    tm = re.search(r"^    type = (.*)$", m.group(0), re.M)
    PYCLS[m.group(1)] = tm.group(1) if tm else ""
UNVERIFIED37 = set("""targetAttack projectileFired powerBooster targetHostiles miningLaser doHacking tractorBeamCan miningClouds
salvaging useMissiles remoteSensorDampFalloff remoteTargetPaintFalloff remoteWebifierFalloff remoteSensorBoostFalloff pointDefense
lightningWeapon doomsdayAOEBubble remoteWebifierEntity remoteTargetPaintEntity remoteSensorDampEntity
moduleBonusWarfareLinkArmor moduleBonusWarfareLinkShield moduleBonusWarfareLinkSkirmish moduleBonusWarfareLinkInfo
moduleBonusWarfareLinkMining moduleTitanEffectGenerator targetDisintegratorAttack aoe_beacon_bioluminescence_cloud
aoe_beacon_caustic_cloud aoe_beacon_filament_cloud weather_caustic_toxin weather_darkness weather_electric_storm
weather_infernal weather_xenon_gas weather_basic moduleBonusBreacherPodDamageControl""".split())
item = eos.db.getItem
_known = {}


def known(t):
    if t not in _known:
        _known[t] = item(t) is not None
    return _known[t]


def a(t, aid, d=0.0):
    return T[t]["attrs"].get(str(aid), d)


# standard fit for implants/boosters/skills/environment/projected effects: Vexor with turrets, a launcher-free
# rack, prop, rep, drones (drones_active_vexor from bench 1.9.0, a known-good Pyfa fit, minus Drones-skill modules)
STD = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../cases/drones_active_vexor.json")))
STD.pop("options", None)
# drop modules that require the Drones skill (Drone Damage Amplifiers etc.): engines that apply OwnerRequiredSkill
# modifiers to fitted modules (Pyfa applies them to drones only) would fail every standard-fit case on module hp
STD["modules"] = [m for m in STD["modules"] if 3436 not in [int(a(m["type_id"], x)) for x in (182, 183, 184, 1285, 1289, 1290)]]
STD["options"] = {"include_attributes": "all"}
STD.setdefault("projected", [])

SKILLREQ = (182, 183, 184, 1285, 1289, 1290)
carriers = {}
for t, v in T.items():
    for eid, _dflt in v.get("effects") or []:
        carriers.setdefault(eid, []).append(t)
char = Character("eff", 5)
SLOTN = {FittingSlot.HIGH: "high", FittingSlot.MED: "mid", FittingSlot.LOW: "low", FittingSlot.RIG: "rig",
         FittingSlot.SUBSYSTEM: "subsystem", FittingSlot.SERVICE: "service"}
STN = {S.OFFLINE: "offline", S.ONLINE: "online", S.ACTIVE: "active", S.OVERHEATED: "overheated"}
BASE = {"schema_version": 1, "boosters": [], "cargo": [], "character": {"security_status": None,
        "skills": {"default_level": 5, "levels": {}}}, "damage_pattern": None, "drones": [],
        "environment": {"effect_type_ids": [], "system_security": None}, "fighters": [],
        "fleet": {"booster_fits": [], "buffs": []}, "implants": [], "modules": [], "projected": [],
        "options": {"include_attributes": "all"}}
PREF = [587, 626, 645, 641, 24690, 23911, 23913, 22852, 23757, 23915, 671, 3514, 23773, 28352, 11567, 671, 642, 24688,
        17738, 32878, 17476, 17480, 22544, 32880, 33697, 37135, 28606, 42241, 35833, 35832, 35834, 40340, 47512,
        34317, 34562, 29984, 22546, 11393, 12005, 638, 639, 17920, 24694, 11176, 33468, 2006, 11387, 29988, 3756]
ships = [t for t, v in T.items() if v["category"] == 6 and v.get("published") and v["group"] != 29 and known(t)
         and not a(t, 1367)]  # no T3C (subsystems) as generic hulls
structs = [t for t, v in T.items() if v["category"] == 65 and v.get("published") and known(t)]
seen = set()
CAND = [t for t in PREF + sorted(ships, key=lambda t: (T[t]["group"], t)) if t in T and known(t) and not (t in seen or seen.add(t))]
CAND = [t for t in CAND if T[t]["category"] == 6 and not a(t, 1367)]


def new_fit(st, mode=None):
    sh = item(st)
    f = Fit(Citadel(sh) if sh.category.name == "Structure" else Ship(sh), "eff")
    f.character = char
    if f.ship.modes:
        f.mode = f.ship.validateModeItem(item(mode) if mode else None)
    return f


def mod_entry(m, st, charge=None):
    return {"type_id": int(m.item.ID), "slot": SLOTN.get(m.slot, "high"), "state": STN[st],
            "charge_type_id": int(charge.ID) if charge else None, "mutation": None, "spool": None}


def want_state(eff):
    c = eff["category"]
    return S.OVERHEATED if c == 5 else S.ACTIVE if c in (1, 2, 3) else S.ONLINE


def best_state(m, want):
    for cand in (S.OVERHEATED, S.ACTIVE, S.ONLINE, S.OFFLINE):
        if cand <= want and m.isValidState(cand):
            return cand
    return S.OFFLINE


def first_charge(m, prefer=None):
    vc = sorted((c for c in (m.getValidCharges() or []) if int(c.ID) in T), key=lambda c: (not c.published, c.ID))
    if prefer is not None:
        return next((c for c in vc if int(c.ID) == prefer), None)
    return vc[0] if vc else None


_charge_host = None


def charge_host(ct):
    """first module type (by id) whose getValidCharges contains charge ct"""
    global _charge_host
    if _charge_host is None:
        _charge_host = {}
        grp2mods = {}
        for t, v in sorted(T.items()):
            if v["category"] not in (7, 66) or not v.get("published") or not known(t):
                continue
            for aid in (604, 605, 606, 609, 610, 2076, 2077, 2078):
                g = a(t, aid)
                if g:
                    grp2mods.setdefault(int(g), []).append(t)
        _charge_host = grp2mods
    for t in _charge_host.get(T[ct]["group"], []):
        try:
            m = Module(item(t))
        except ValueError:
            continue
        if any(int(c.ID) == ct for c in (m.getValidCharges() or [])):
            return t
    return None


def try_fit_module(t, hulls, want, charge_pref=None, extra=None):
    """fit module type t (+charge) on the first hull it fits; returns (ship, fit, [module entries]) or None"""
    try:
        Module(item(t))
    except ValueError:
        return None
    for st in hulls:
        fit = new_fit(st)
        m = Module(item(t))
        if not m.fits(fit):
            continue
        ch = first_charge(m, charge_pref) if charge_pref is not None else first_charge(m)
        if charge_pref is not None and ch is None:
            continue
        fit.modules.append(m)
        if ch:
            m.charge = ch
        stt = best_state(m, want)
        m.state = stt
        return st, fit, [mod_entry(m, stt, ch)]
    return None


def affectee_types(eff, exclude):
    """types the effect modifies, from its SDE modifiers: (category, type) list, at most 3"""
    out = []
    for func, dom, tgt, _src, _op, extra in eff["mods"]:
        cands = []
        if func == 2:  # LocationGroup
            cands = [t for t, v in T.items() if v["group"] == extra]
        elif func in (3, 4):  # Location/OwnerRequiredSkill
            cands = [t for t, v in T.items() if any(int(a(t, x)) == extra for x in SKILLREQ)]
        elif func == 1 and dom == 1:  # LocationModifier on ship items
            cands = [t for t, v in T.items() if v["category"] == 7 and str(tgt) in v["attrs"]]
        cands = [t for t in cands if T[t]["category"] in (7, 8, 18, 87) and T[t].get("published") and known(t)
                 and str(tgt) in T[t]["attrs"] and t not in exclude and "Mutated" not in T[t]["name"]]
        cands.sort(key=lambda t: (T[t].get("meta_level") or 0, t))
        if cands:
            t = cands[0]
            if t not in [x for _c, x in out]:
                out.append((T[t]["category"], t))
        if len(out) >= 3:
            break
    return out


def add_affectees(req, fit, aff):
    added = []
    for cat, t in aff:
        if cat == 7:
            m = Module(item(t))
            if m.fits(fit):
                ch = first_charge(m)
                fit.modules.append(m)
                if ch:
                    m.charge = ch
                stt = best_state(m, S.ACTIVE)
                m.state = stt
                req["modules"].append(mod_entry(m, stt, ch))
                added.append(t)
        elif cat == 8:
            h = charge_host(t)
            if h is None:
                continue
            m = Module(item(h))
            if m.fits(fit):
                ch = first_charge(m, t)
                if ch is None:
                    continue
                fit.modules.append(m)
                m.charge = ch
                stt = best_state(m, S.ACTIVE)
                m.state = stt
                req["modules"].append(mod_entry(m, stt, ch))
                added.append(t)
        elif cat == 18:
            dr = Drone(item(t))
            bay = fit.ship.getModifiedItemAttr("droneCapacity") or 0
            if (T[t].get("volume") or 0) <= bay and dr.fits(fit) and not req["drones"]:
                bw = fit.ship.getModifiedItemAttr("droneBandwidth") or 0
                req["drones"].append({"type_id": t, "quantity": 1, "active": 1 if a(t, 1272) <= bw else 0, "mutation": None})
                added.append(t)
        elif cat == 87:
            fi = Fighter(item(t))
            if fit.ship.getModifiedItemAttr("fighterTubes") and fi.fits(fit) and not req["fighters"]:
                req["fighters"].append({"type_id": t, "quantity": int(a(t, 2215) or 1), "active": True, "abilities": None})
                added.append(t)
    return added


def hull_for_drone(t, need_fighter=False):
    for st in CAND + structs:
        fit = new_fit(st)
        if need_fighter:
            if not fit.ship.getModifiedItemAttr("fighterTubes"):
                continue
            fi = Fighter(item(t))
            if fi.fits(fit) and (T[t].get("volume") or 0) * int(a(t, 2215) or 1) <= (fit.ship.getModifiedItemAttr("fighterCapacity") or 0):
                return st, fit
        else:
            bay = fit.ship.getModifiedItemAttr("droneCapacity") or 0
            bw = fit.ship.getModifiedItemAttr("droneBandwidth") or 0
            if (T[t].get("volume") or 0) <= bay and a(t, 1272) <= bw and Drone(item(t)).fits(fit):
                return st, fit
    return None


def build_case(eid, eff, ct):
    """returns (request, how, affectees) or (None, reason, None)"""
    cat = T[ct]["category"]
    name = eff["name"]
    pytype = PYCLS.get(name, "")
    projected = "projected" in pytype and eff["category"] == 2
    want = want_state(eff)
    req = copy.deepcopy(BASE)
    if T[ct]["group"] == 1306:  # T3D / Anhinga / Skua modes (category 7 in the SDE)
        hull = next((s for s in ships if any(int(mm.item.ID) == ct for mm in (new_fit(s).ship.modes or []))), None)
        if hull is None:
            return None, "mode without hull", None
        req["ship"] = {"type_id": hull, "mode_type_id": ct}
        fit = new_fit(hull, ct)
        aff = add_affectees(req, fit, affectee_types(eff, {hull, ct}))
        return req, "mode", aff
    if cat in (7, 66):
        if projected and cat == 7:
            req = copy.deepcopy(STD)
            m = Module(item(ct))
            ch = first_charge(m)
            pm = {"type_id": ct, "state": "active"}
            if ch:
                pm["charge_type_id"] = int(ch.ID)
            req["projected"] = [{"kind": "module", "module": pm, "amount": 1, "distance_m": 1000}]
            return req, "projected-module", []
        hulls = CAND if cat == 7 else structs
        r = try_fit_module(ct, hulls, want)
        if r is None and cat == 7:
            r = try_fit_module(ct, structs, want)
        if r is None:
            return None, "no hull Pyfa fits it on", None
        st, fit, ents = r
        req["ship"] = {"type_id": st, "mode_type_id": None}
        req["modules"] = ents
        aff = add_affectees(req, fit, affectee_types(eff, {ct}))
        return req, "fitted-module", aff
    if cat == 8:
        h = charge_host(ct)
        if h is None:
            return None, "no module accepts the charge", None
        r = try_fit_module(h, CAND + structs, S.ACTIVE, charge_pref=ct)
        if r is None:
            return None, "charge host module fits no hull", None
        st, fit, ents = r
        req["ship"] = {"type_id": st, "mode_type_id": None}
        req["modules"] = ents
        aff = add_affectees(req, fit, affectee_types(eff, {ct, h}))
        return req, "charge", aff
    if cat in (18, 87):
        fighter = cat == 87
        if projected:
            req = copy.deepcopy(STD)
            req["projected"] = [{"kind": "fighter", "fighter": {"type_id": ct}, "amount": 1, "distance_m": 1000} if fighter else
                                {"kind": "drone", "drone": {"type_id": ct, "quantity": 1}, "amount": 1, "distance_m": 1000}]
            return req, "projected-" + ("fighter" if fighter else "drone"), []
        r = hull_for_drone(ct, fighter)
        if r is None:
            return None, "no hull takes it", None
        st, fit = r
        req["ship"] = {"type_id": st, "mode_type_id": None}
        if fighter:
            req["fighters"] = [{"type_id": ct, "quantity": int(a(ct, 2215) or 1), "active": True, "abilities": None}]
        else:
            req["drones"] = [{"type_id": ct, "quantity": 1, "active": 1, "mutation": None}]
        return req, "fighter" if fighter else "drone", []
    if cat == 20:
        req = copy.deepcopy(STD)
        if a(ct, 1087):  # boosterness
            se = [eid] if "boosterSideEffect" in pytype else []
            req["boosters"] = [{"type_id": ct, "side_effects": se}]
            return req, "booster", []
        if a(ct, 331):
            req["implants"] = [ct]
            return req, "implant", []
        return None, "implant without slot", None
    if cat == 32:
        st = int(a(ct, 1380))
        if not st or not known(st):
            return None, "subsystem hull unknown to Pyfa", None
        bys = {}
        for t, v in sorted(T.items()):
            if v["category"] == 32 and v.get("published") and int(a(t, 1380)) == st and known(t):
                bys.setdefault(int(a(t, 1366)), []).append(t)
        mine = int(a(ct, 1366))
        subs = [ct] + [ts[0] for sl, ts in sorted(bys.items()) if sl != mine]
        req["ship"] = {"type_id": st, "mode_type_id": None}
        req["modules"] = [{"type_id": t, "slot": "subsystem", "state": "online", "charge_type_id": None,
                           "mutation": None, "spool": None} for t in subs]
        fit = new_fit(st)
        for t in subs:
            fit.modules.append(Module(item(t)))
        fit.calculateModifiedAttributes()
        aff = add_affectees(req, fit, affectee_types(eff, set(subs)))
        return req, "subsystem", aff
    if cat == 6:
        mode = None
        st = ct
        req["ship"] = {"type_id": st, "mode_type_id": mode}
        fit = new_fit(st, mode)
        if a(st, 1367):  # T3C: first subsystem of every slot
            bys = {}
            for t, v in sorted(T.items()):
                if v["category"] == 32 and v.get("published") and int(a(t, 1380)) == st and known(t):
                    bys.setdefault(int(a(t, 1366)), []).append(t)
            for sl, ts in sorted(bys.items()):
                req["modules"].append({"type_id": ts[0], "slot": "subsystem", "state": "online", "charge_type_id": None,
                                       "mutation": None, "spool": None})
                fit.modules.append(Module(item(ts[0])))
            fit.calculateModifiedAttributes()
        aff = add_affectees(req, fit, affectee_types(eff, {st}))
        return req, "mode" if mode else "ship", aff
    if cat == 65:
        req["ship"] = {"type_id": ct, "mode_type_id": None}
        fit = new_fit(ct)
        aff = add_affectees(req, fit, affectee_types(eff, {ct}))
        return req, "structure", aff
    if cat == 16:
        st = 626  # Vexor
        req["ship"] = {"type_id": st, "mode_type_id": None}
        req["character"]["skills"] = {"default_level": 0, "levels": {str(ct): 5}}
        fit = new_fit(st)
        aff = add_affectees(req, fit, affectee_types(eff, {ct}))
        if not aff and not any(dom == 1 for _f, dom, *_r in eff["mods"]):
            # character/drone/charge-domain skill without a derivable affectee: use the standard fit
            req = copy.deepcopy(STD)
            req["character"]["skills"] = {"default_level": 0, "levels": {str(ct): 5}}
            return req, "skill-std", []
        return req, "skill", aff
    if cat == 2:
        req = copy.deepcopy(STD)
        req["environment"] = {"effect_type_ids": [ct], "system_security": None}
        return req, "environment", []
    return None, f"carrier category {cat} not fittable", None


def main():
    man = {}
    used = sorted(e for e in EFF if e in carriers and EFF[e]["name"] in PYCLS)
    only = set(int(x) for x in os.environ.get("EFF_ONLY", "").split(",") if x)
    for eid in used:
        if only and eid not in only:
            continue
        eff = EFF[eid]
        cs = sorted(carriers[eid], key=lambda t: (not T[t].get("published"), not known(t), T[t]["category"] == 2 and 0, t))
        cs = [t for t in cs if known(t)]
        safe = re.sub(r"[^A-Za-z0-9_]", "_", eff["name"])[:60]
        cid = f"eff_{eid}_{safe}"
        rec = {"effect_id": eid, "effect": eff["name"], "pyfa_type": PYCLS[eff["name"]], "category": eff["category"],
               "handler_only": not eff["mods"], "unverified37": eff["name"] in UNVERIFIED37, "carriers": len(carriers[eid])}
        if not cs:
            rec["skip"] = "no carrier type in Pyfa's eve.db"
            man[cid] = rec
            continue
        res = (None, "no carrier buildable", None)
        for ct in cs[:6]:  # first carrier that builds
            try:
                res = build_case(eid, eff, ct)
            except Exception as ex:  # noqa
                res = (None, f"generator error {type(ex).__name__}: {ex}", None)
            if res[0] is not None:
                rec["carrier"] = ct
                rec["carrier_name"] = T[ct]["name"]
                break
        req, how, aff = res
        if req is None:
            rec["skip"] = how
        else:
            rec["how"] = how
            rec["affectees"] = aff
            req["schema_version"] = 1
            json.dump(req, open(os.path.join(OUT, "cases", cid + ".json"), "w"), sort_keys=True, separators=(",", ":"))
        man[cid] = rec
    json.dump(man, open(os.path.join(OUT, "MANIFEST.json"), "w"), indent=1, sort_keys=True)
    n = sum(1 for r in man.values() if "skip" not in r)
    print(f"effects {len(man)}, cases {n}, skipped {len(man) - n}", file=sys.stderr)


main()
