#!/usr/bin/env python3
"""Random LEGAL fit generator for differential triage (A vs Pyfa oracle).
Legality is decided with Pyfa's own fitting rules (Module.fits: slot counts after subsystems, hardpoints,
rig size, canFitShipGroup/Type, fitsToShipType, maxGroupFitted, capital-size modules; isValidState /
canHaveState for states; Module.getValidCharges for charges) plus maxTypeFitted, drone bay/bandwidth,
fighter tubes/bay, distinct implant/booster slots, valid T3D mode. CPU/PG are NOT enforced.
Ships only (category 6, published); structures are out of scope here.
run with Pyfa venv: cd $PYFA && PYTHONPATH=$STUBS $PYFA_PY oracle/fuzz/gen_legal.py OUTDIR N SEED"""
import gzip, json, os, random, sys, tempfile
PYFA = os.environ.get("PYFA", "/workspace/exct-eve/ref/pyfa")
sys.path.insert(0, PYFA)
import config  # noqa
config.defPaths(tempfile.mkdtemp(prefix="fz-gen-"))
import eos.config  # noqa
eos.config.gamedata_connectionstring = "sqlite:///" + os.path.join(PYFA, "eve.db") + "?check_same_thread=False"
import eos.db  # noqa
eos.db.saveddata_meta.create_all(eos.db.saveddata_engine)
from eos.saveddata.character import Character  # noqa
from eos.saveddata.fit import Fit  # noqa
from eos.saveddata.ship import Ship  # noqa
from eos.saveddata.module import Module  # noqa
from eos.saveddata.drone import Drone  # noqa
from eos.saveddata.fighter import Fighter  # noqa
from eos.const import FittingModuleState as S, FittingSlot  # noqa

out, N, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
os.makedirs(out, exist_ok=True)
rnd = random.Random(seed)
DS = json.load(gzip.open("/workspace/exct-eve/data/dataset-3569502.json.gz"))["types"]
pub = {int(k): v for k, v in DS.items() if v.get("published")}
def a(t, aid, d=0.0):
    return pub[t]["attrs"].get(str(aid), d)
ships = [t for t, v in pub.items() if v["category"] == 6 and v["group"] not in (29,)]
mods = [t for t, v in pub.items() if v["category"] == 7]
subs = [t for t, v in pub.items() if v["category"] == 32]
drones = [t for t, v in pub.items() if v["category"] == 18 and "Mutated" not in v["name"]]
fighters = [t for t, v in pub.items() if v["category"] == 87]
implants = [t for t, v in pub.items() if v["category"] == 20 and a(t, 331)]
boosters = [t for t, v in pub.items() if v["category"] == 20 and a(t, 1087)]
modes = [t for t, v in pub.items() if v["group"] == 1306]
item = eos.db.getItem
# only types the oracle's eve.db knows (Pyfa data build can lag the engines' dataset)
drones, fighters, implants, boosters = ([t for t in L if item(t) is not None] for L in (drones, fighters, implants, boosters))
ships = [t for t in ships if item(t) is not None]
ship_groups = [sorted(t for t in ships if pub[t]["group"] == g) for g in sorted({pub[t]["group"] for t in ships})]
char = Character("fz", 5)
SLOTN = {FittingSlot.HIGH: "high", FittingSlot.MED: "mid", FittingSlot.LOW: "low", FittingSlot.RIG: "rig",
         FittingSlot.SUBSYSTEM: "subsystem", FittingSlot.SERVICE: "service"}
STN = {S.OFFLINE: "offline", S.ONLINE: "online", S.ACTIVE: "active", S.OVERHEATED: "overheated"}
item = eos.db.getItem
# pre-bucket modules by Pyfa slot
bucket = {}
for t in mods:
    it = item(t)
    if it is None:
        continue
    sl = Module.calculateSlot(it)
    try:
        Module(it)
    except ValueError:
        continue
    if sl in SLOTN:
        bucket.setdefault(sl, []).append(t)

def new_fit(st):
    f = Fit(); f.ship = Ship(item(st)); f.character = char
    return f

def gen_one(k):
    st = int(os.environ["FZ_SHIP"]) if os.environ.get("FZ_SHIP") else rnd.choice(rnd.choice(ship_groups))  # stratified by ship group
    if item(st) is None:
        return None
    fit = new_fit(st)
    req_mods = []
    ship_g = pub[st]["group"]
    # T3C subsystems first (one per subsystem slot, fitsToShipType == ship)
    if a(st, 1367):  # maxSubSystems
        bys = {}
        for t in subs:
            if int(a(t, 1380)) == st:
                bys.setdefault(int(a(t, 1366)), []).append(t)
        for sl in sorted(bys):
            t = rnd.choice(bys[sl])
            try:
                m = Module(item(t))
            except ValueError:
                print("bad sub", t, pub[t]["name"], file=sys.stderr); raise
            fit.modules.append(m)
            req_mods.append({"type_id": t, "slot": "subsystem", "state": "online", "charge_type_id": None, "mutation": None, "spool": None})
    mode = None
    ms = fit.ship.modes  # Pyfa: T3D / Anhinga must have a mode
    if ms:
        mode = int(rnd.choice(ms).item.ID)
        fit.mode = fit.ship.validateModeItem(item(mode))
    fit.calculateModifiedAttributes()
    order = [FittingSlot.HIGH, FittingSlot.MED, FittingSlot.LOW, FittingSlot.RIG, FittingSlot.SERVICE]
    typecount = {}
    for sl in order:
        n = int(fit.getNumSlots(sl) or 0)
        if not n or sl not in bucket:
            continue
        fill = rnd.choice([n, n, n, max(0, n - 1), rnd.randint(0, n)])
        tries = 0
        # bias: pick 1-3 module types per slot rack and repeat them (like real fits)
        while fit.getSlotsFree(sl) > 0 and fill > 0 and tries < 60:
            tries += 1
            t = rnd.choice(bucket[sl])
            reps = rnd.choice([1, 1, 2, 3, 4])
            for _ in range(reps):
                if fill <= 0 or fit.getSlotsFree(sl) <= 0:
                    break
                it = item(t); m = Module(it)
                mt = a(t, 2431)
                if mt and typecount.get(t, 0) >= mt:
                    break
                if not m.fits(fit):
                    break
                fit.modules.append(m)
                typecount[t] = typecount.get(t, 0) + 1
                fill -= 1
                ch = None
                vc = [c for c in (m.getValidCharges() or []) if c.published and int(c.ID) in pub]
                if vc and rnd.random() < 0.9:
                    ch = rnd.choice(sorted(vc, key=lambda c: c.ID)); m.charge = ch
                req_mods.append({"type_id": t, "slot": SLOTN[sl], "_m": m, "charge_type_id": int(ch.ID) if ch else None,
                                 "mutation": None, "spool": None})
    fit.calculateModifiedAttributes()
    # states, in request order; Pyfa rules: isValidState + maxGroupOnline / maxGroupActive (modified attrs)
    for r in req_mods:
        if "_m" in r:
            r["_m"].state = S.OFFLINE
    fit.calculateModifiedAttributes()
    grp_on = {}; grp_act = {}
    for r in req_mods:
        m = r.pop("_m", None)
        if m is None:
            continue
        g = m.item.groupID
        mon = m.getModifiedItemAttr("maxGroupOnline", None); mac = m.getModifiedItemAttr("maxGroupActive", None)
        want = rnd.choices([S.OFFLINE, S.ONLINE, S.ACTIVE, S.OVERHEATED], [1, 3, 8, 2])[0]
        stt = S.OFFLINE
        if m.slot == FittingSlot.RIG:
            want = S.ONLINE  # EVE: rigs cannot be offlined (Pyfa allows it; out of scope here)
        for cand in (S.OVERHEATED, S.ACTIVE, S.ONLINE):
            if cand > want or not m.isValidState(cand):
                continue
            if mon and grp_on.get(g, 0) + 1 > mon:
                continue
            if cand >= S.ACTIVE and mac and grp_act.get(g, 0) + 1 > mac:
                continue
            stt = cand; break
        if stt >= S.ONLINE:
            grp_on[g] = grp_on.get(g, 0) + 1
        if stt >= S.ACTIVE:
            grp_act[g] = grp_act.get(g, 0) + 1
        m.state = stt
        r["state"] = STN[stt]
    # drones
    req_dr = []
    bay = fit.ship.getModifiedItemAttr("droneCapacity") or 0
    bw = fit.ship.getModifiedItemAttr("droneBandwidth") or 0
    if bay and rnd.random() < 0.85:
        used_v = 0; used_bw = 0; act_n = 0
        for _ in range(rnd.randint(1, 3)):
            t = rnd.choice(drones); v = pub[t].get("volume") or 0; dbw = a(t, 1272)
            if v <= 0:
                continue
            q = min(int((bay - used_v) // v), rnd.randint(1, 5))
            if q <= 0:
                continue
            act = 0
            while act < q and act_n + act < 5 and used_bw + (act + 1) * dbw <= bw:
                act += 1
            act = rnd.randint(0, act)
            used_v += q * v; used_bw += act * dbw; act_n += act
            req_dr.append({"type_id": t, "quantity": q, "active": act, "mutation": None})
    # fighters
    req_fi = []
    tubes = int(fit.ship.getModifiedItemAttr("fighterTubes") or 0)
    fbay = fit.ship.getModifiedItemAttr("fighterCapacity") or 0
    if tubes and fighters:
        lim = {"light": int(fit.ship.getModifiedItemAttr("fighterLightSlots") or 0),
               "support": int(fit.ship.getModifiedItemAttr("fighterSupportSlots") or 0),
               "heavy": int(fit.ship.getModifiedItemAttr("fighterHeavySlots") or 0)}
        used = {"light": 0, "support": 0, "heavy": 0}; vol = 0
        for _ in range(tubes):
            t = rnd.choice(fighters)
            kind = "light" if a(t, 2212) else "support" if a(t, 2213) else "heavy" if a(t, 2214) else None
            if kind is None or used[kind] >= lim[kind]:
                continue
            q = int(a(t, 2215) or 1); v = (pub[t].get("volume") or 0) * q
            if vol + v > fbay:
                continue
            fi = Fighter(item(t))
            if not fi.fits(fit):
                continue
            used[kind] += 1; vol += v
            req_fi.append({"type_id": t, "quantity": q, "active": rnd.random() < 0.85, "abilities": None})
    # implants / boosters (distinct slots)
    imp = []; seen = set()
    for t in rnd.sample(implants, rnd.choice([0, 0, 1, 2, 3])):
        s_ = int(a(t, 331))
        if s_ not in seen:
            seen.add(s_); imp.append(t)
    boo = []; seen = set()
    for t in rnd.sample(boosters, rnd.choice([0, 0, 0, 1])):
        s_ = int(a(t, 1087))
        if s_ not in seen:
            seen.add(s_); boo.append({"type_id": t, "side_effects": []})
    req = {"schema_version": 1, "ship": {"type_id": st, "mode_type_id": mode}, "modules": req_mods, "drones": req_dr,
           "fighters": req_fi, "implants": imp, "boosters": boo, "cargo": [],
           "character": {"security_status": None, "skills": {"default_level": 5, "levels": {}}},
           "damage_pattern": None, "environment": {"effect_type_ids": [], "system_security": None},
           "fleet": {"booster_fits": [], "buffs": []}, "overrides": [], "projected": [], "target_profile": None,
           "options": {"cap_sim": {"max_time_s": None, "reload": False, "stagger": False}, "default_spool": None,
                       "factor_reload": False, "include_attributes": None, "nos_no_target_cap": False, "rah": None,
                       "sources": False, "validate": True}}
    return req

n = 0; k = 0
while n < N and k < N * 5:
    k += 1
    try:
        r = gen_one(k)
    except Exception as e:  # generator bug -> skip, report
        import traceback; print("gen error", type(e).__name__, e, traceback.format_exc().splitlines()[-3], file=sys.stderr); continue
    if r is None or not r["modules"]:
        continue
    name = f"lf{seed:02d}_{n:03d}_{r['ship']['type_id']}"
    open(os.path.join(out, name + ".json"), "w").write(json.dumps(r, indent=1, sort_keys=True))
    n += 1
print(f"generated {n} legal fits ({k} attempts)")
