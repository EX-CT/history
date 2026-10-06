#!/usr/bin/env python3
"""Legality filter for FitRequests (ships only): re-checks each module in request order with Pyfa's fitting
rules (Module.fits: slots after subsystems, hardpoints, rig size, canFitShipGroup/Type, fitsToShipType,
maxGroupFitted, capital-size), maxTypeFitted, state validity (isValidState, maxGroupOnline/Active),
charge validity (Module.isValidCharge), T3D mode, drone bay/bandwidth/5 active, fighter tubes/bay,
implant/booster slot uniqueness, structure hulls (out of scope). CPU/PG/calibration not checked.
usage (Pyfa venv, cwd $PYFA): check_legal.py req.json ... -> one line per file: OK | ILLEGAL: reasons"""
import gzip, json, os, sys, tempfile
PYFA = os.environ.get("PYFA", "/workspace/exct-eve/ref/pyfa")
sys.path.insert(0, PYFA)
import config  # noqa
config.defPaths(tempfile.mkdtemp(prefix="fz-chk-"))
import eos.config  # noqa
eos.config.gamedata_connectionstring = "sqlite:///" + os.path.join(PYFA, "eve.db") + "?check_same_thread=False"
import eos.db  # noqa
eos.db.saveddata_meta.create_all(eos.db.saveddata_engine)
from eos.saveddata.character import Character  # noqa
from eos.saveddata.fit import Fit  # noqa
from eos.saveddata.ship import Ship  # noqa
from eos.saveddata.module import Module  # noqa
from eos.saveddata.fighter import Fighter  # noqa
from eos.const import FittingModuleState as S, FittingSlot  # noqa
item = eos.db.getItem
STATES = {"offline": S.OFFLINE, "online": S.ONLINE, "active": S.ACTIVE, "overheated": S.OVERHEATED}
SLOTN = {FittingSlot.HIGH: "high", FittingSlot.MED: "mid", FittingSlot.LOW: "low", FittingSlot.RIG: "rig",
         FittingSlot.SUBSYSTEM: "subsystem", FittingSlot.SERVICE: "service"}
char = Character("chk", 5)
DS = json.load(gzip.open("/workspace/exct-eve/data/dataset-3569502.json.gz"))["types"]


def dsattr(t, aid):
    v = DS.get(str(t), {})
    return v.get("attrs", {}).get(str(aid)) if aid != "volume" else v.get("volume")


notes = []


def check(req):
    bad = []
    notes.clear()
    it = item(req["ship"]["type_id"])
    if it is None:
        return ["ship not in eve.db"]
    if it.category.name != "Ship":
        bad.append(f"hull category {it.category.name} (out of scope)")
        return bad
    fit = Fit(); fit.ship = Ship(it); fit.character = char
    ms = fit.ship.modes
    mt = req["ship"].get("mode_type_id")
    if ms and (mt is None or mt not in [int(m.item.ID) for m in ms]):
        bad.append(f"T3D needs a valid mode (got {mt})")
    if not ms and mt:
        bad.append("mode on a non-T3D hull")
    if ms and mt:
        fit.mode = fit.ship.validateModeItem(item(mt))
    reqm = req.get("modules", [])
    order = sorted(range(len(reqm)), key=lambda i: 0 if Module.calculateSlot(item(reqm[i]["type_id"])) == FittingSlot.SUBSYSTEM else 1)
    built = {}
    tc = {}
    for i in order:
        r = reqm[i]
        t = item(r["type_id"])
        try:
            m = Module(t)
        except ValueError:
            bad.append(f"mod[{i}] {r['type_id']} not a module"); continue
        if r.get("slot") and SLOTN.get(m.slot) != r["slot"]:
            bad.append(f"mod[{i}] {t.name} slot {r['slot']} != {SLOTN.get(m.slot)}")
        if m.slot == FittingSlot.SUBSYSTEM:
            fit.calculateModifiedAttributes()
        if not m.fits(fit):
            why = "slot full" if fit.getSlotsFree(m.slot) <= 0 else "restriction (ship type/group, rig size, maxGroupFitted, hardpoint or capital)"
            bad.append(f"mod[{i}] {t.name}: {why}")
        mx = t.attributes.get("maxTypeFitted")
        tc[t.ID] = tc.get(t.ID, 0) + 1
        if mx and mx.value and tc[t.ID] > mx.value:
            bad.append(f"mod[{i}] {t.name}: maxTypeFitted {mx.value}")
        fit.modules.append(m)
        if m.slot == FittingSlot.SUBSYSTEM:
            fit.calculateModifiedAttributes()
        if r.get("charge_type_id"):
            c = item(r["charge_type_id"])
            if c is None or not m.isValidCharge(c):
                bad.append(f"mod[{i}] {t.name}: invalid charge {r['charge_type_id']}")
            else:
                m.charge = c
        built[i] = m
        if m.slot != FittingSlot.SUBSYSTEM:
            m.state = S.OFFLINE
    fit.calculateModifiedAttributes()
    on = {}; act = {}
    for i, r in enumerate(reqm):
        m = built.get(i)
        if m is None:
            continue
        st = STATES[r.get("state", "online")]
        if st >= S.ONLINE and not m.isValidState(st):
            notes.append(f"mod[{i}] {m.item.name}: state {r.get('state')} above max (contract clamps)")
        if m.slot == FittingSlot.RIG and st < S.ONLINE:
            bad.append(f"mod[{i}] {m.item.name}: offline rig (rigs cannot be offlined in EVE)")
        g = m.item.groupID
        if st >= S.ONLINE:
            on[g] = on.get(g, 0) + 1
            mon = m.getModifiedItemAttr("maxGroupOnline", None)
            if mon and on[g] > mon:
                bad.append(f"mod[{i}] {m.item.name}: maxGroupOnline {mon}")
        if st >= S.ACTIVE:
            act[g] = act.get(g, 0) + 1
            mac = m.getModifiedItemAttr("maxGroupActive", None)
            if mac and act[g] > mac:
                bad.append(f"mod[{i}] {m.item.name}: maxGroupActive {mac}")
    sh = fit.ship
    vol = bw = na = 0
    for d in req.get("drones", []):
        di = item(d["type_id"])
        if di is None or di.category.name != "Drone":
            bad.append(f"drone {d['type_id']} not a drone"); continue
        vol += dsattr(di.ID, "volume") * d.get("quantity", 1)
        a = d.get("active", 0) or 0
        na += a; bw += a * (di.attributes["droneBandwidthUsed"].value if "droneBandwidthUsed" in di.attributes else 0)
    if vol > (sh.getModifiedItemAttr("droneCapacity") or 0) + 1e-6:
        bad.append(f"drone bay {vol} > {sh.getModifiedItemAttr('droneCapacity')}")
    if bw > (sh.getModifiedItemAttr("droneBandwidth") or 0) + 1e-6:
        bad.append(f"drone bandwidth {bw} > {sh.getModifiedItemAttr('droneBandwidth')}")
    if na > 5:
        bad.append(f"{na} active drones > 5")
    fvol = 0; kinds = {"light": 0, "support": 0, "heavy": 0}; nf = 0
    for f in req.get("fighters", []):
        fi_it = item(f["type_id"])
        if fi_it is None or fi_it.category.name != "Fighter":
            bad.append(f"fighter {f['type_id']} not a fighter"); continue
        fo = Fighter(fi_it)
        nf += 1
        fvol += dsattr(fi_it.ID, "volume") * (f.get("quantity") or fo.amount)
        for k, an in (("light", "fighterSquadronIsLight"), ("support", "fighterSquadronIsSupport"), ("heavy", "fighterSquadronIsHeavy")):
            if fi_it.attributes.get(an) and fi_it.attributes[an].value:
                kinds[k] += 1
    if nf > (sh.getModifiedItemAttr("fighterTubes") or 0):
        bad.append(f"{nf} squadrons > tubes")
    for k, an in (("light", "fighterLightSlots"), ("support", "fighterSupportSlots"), ("heavy", "fighterHeavySlots")):
        if kinds[k] > (sh.getModifiedItemAttr(an) or 0):
            bad.append(f"{kinds[k]} {k} squadrons > {an}")
    if fvol > (sh.getModifiedItemAttr("fighterCapacity") or 0) + 1e-6:
        bad.append("fighter bay overfull")
    for key, an in (("implants", 331), ("boosters", 1087)):
        seen = set()
        for x in req.get(key, []):
            s = dsattr(x["type_id"] if isinstance(x, dict) else x, an)
            if s is None:
                bad.append(f"{key[:-1]} {x} has no {an}")
            elif s in seen:
                bad.append(f"two {key} in slot {s}")
            seen.add(s)
    return bad


if __name__ == "__main__":
    for p in sys.argv[1:]:
        try:
            b = check(json.load(open(p)))
        except Exception as e:
            b = [f"checker error {type(e).__name__}: {e}"]
        print(json.dumps({"file": os.path.basename(p), "legal": not b, "reasons": b, "notes": list(notes)}))
