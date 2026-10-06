#!/usr/bin/env python3
"""Pyfa (eos) black-box oracle: runs Pyfa's engine headless on an EXCT FitRequest JSON and prints
comparable stats + timing. This script *uses* Pyfa as a library and is therefore GPL-3.0-or-later
(see ./LICENSE-GPL-NOTE). It is a test tool only; nothing here is linked into eve-dogma-rs.

usage: PYFA=/path/to/Pyfa python pyfa_oracle.py request.json [request2.json ...]
Requires Pyfa's eve.db (python db_update.py) and a stub `wx` module on PYTHONPATH.
"""
import json, math, os, sys, time, tempfile

PYFA = os.environ.get("PYFA", "/workspace/exct-eve/ref/pyfa")
sys.path.insert(0, PYFA)
import config  # noqa: E402
config.defPaths(tempfile.mkdtemp(prefix="pyfa-oracle-"))
import eos.config  # noqa: E402
eos.config.gamedata_connectionstring = "sqlite:///" + os.path.join(PYFA, "eve.db") + "?check_same_thread=False"
import eos.db  # noqa: E402
eos.db.saveddata_meta.create_all(eos.db.saveddata_engine)
from eos.saveddata.character import Character  # noqa: E402
from eos.saveddata.fit import Fit  # noqa: E402
from eos.saveddata.ship import Ship  # noqa: E402
from eos.saveddata.citadel import Citadel  # noqa: E402
from eos.saveddata.module import Module  # noqa: E402
from eos.saveddata.drone import Drone  # noqa: E402
from eos.saveddata.fighter import Fighter  # noqa: E402
from eos.saveddata.implant import Implant  # noqa: E402
from eos.saveddata.booster import Booster  # noqa: E402
from eos.saveddata.damagePattern import DamagePattern  # noqa: E402
from eos.const import FittingModuleState, FittingSlot, SpoolType  # noqa: E402
from eos.utils.spoolSupport import SpoolOptions  # noqa: E402

# what Pyfa's GUI passes (globalDefaultSpoolupPercentage = 100 %); matches EXCT's default spool = max
SPOOL = SpoolOptions(SpoolType.SPOOL_SCALE, eos.config.settings["globalDefaultSpoolupPercentage"], False)

STATES = {"offline": FittingModuleState.OFFLINE, "online": FittingModuleState.ONLINE,
          "active": FittingModuleState.ACTIVE, "overheated": FittingModuleState.OVERHEATED}

_chars = {}


def character(req):
    sk = req.get("character", {}).get("skills", {})
    lvl = sk.get("default_level", 0) or 0
    key = (lvl, json.dumps(sk.get("levels", {}), sort_keys=True))
    if key in _chars:
        return _chars[key]
    ch = Character("oracle-%d" % lvl, lvl)
    for k, v in sk.get("levels", {}).items():
        s = ch.getSkill(int(k))
        s.setLevel(v, ignoreRestrict=True)
    _chars[key] = ch
    return ch


def item(tid):
    if isinstance(tid, dict):
        tid = tid["type_id"]
    it = eos.db.getItem(int(tid))
    if it is None:
        raise KeyError("type %s not in Pyfa eve.db" % tid)
    return it


def mutated(cls, spec):
    mu = spec.get("mutation")
    if not mu:
        return cls(item(spec["type_id"]))
    dyn = eos.db.getDynamicItem(mu["mutaplasmid_type_id"])
    if dyn is None:
        raise KeyError("mutaplasmid %s not in Pyfa eve.db" % mu["mutaplasmid_type_id"])
    obj = cls(dyn.resultingItem, item(mu["base_type_id"]), dyn)
    vals = {int(k): v for k, v in mu.get("attributes", {}).items()}
    for aid, m in obj.mutators.items():
        if aid in vals:
            m.value = vals[aid]
    return obj


_DBUFF_AGG = None


def explicit_buffs(fit, buffs):
    """Contract `fleet.buffs` (explicit warfare buffs) through Pyfa's own command-boost path, the same one Pyfa's
    generic command links use (eos/saveddata/commandLink.py: Fit.addCommandBonus -> Fit.__runCommandBoosts).
    Contract precedence: an explicit entry overrides bursts, booster fits and beacons for its buff id; several entries
    with one id aggregate by the dbuff's aggregate mode (Minimum -> min, else max). No-op when `buffs` is empty, so
    requests without fleet.buffs are computed exactly as before."""
    global _DBUFF_AGG
    if not buffs:
        return
    if _DBUFF_AGG is None:
        import gzip
        ds = os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")
        _DBUFF_AGG = {int(k): v.get("aggregate") for k, v in json.load(gzip.open(ds)).get("dbuffs", {}).items()}
    from eos.saveddata.commandLink import _getAfflictor, _BUFF_CATEGORY, _GANG_EFFECT
    vals = {}
    for b in buffs:
        bid, v = int(b["buff_id"]), float(b["value"])
        if bid in vals:
            vals[bid] = min(vals[bid], v) if _DBUFF_AGG.get(bid) == "Minimum" else max(vals[bid], v)
        else:
            vals[bid] = v
    orig = fit.addCommandBonus

    def add(warfareBuffID, value, module, effect, runTime="normal"):
        if warfareBuffID in vals:  # explicit entry wins for this id
            return
        orig(warfareBuffID, value, module, effect, runTime)
    fit.addCommandBonus = add
    for bid, v in vals.items():
        afflictor = _getAfflictor(_BUFF_CATEGORY.get(bid, "shield")) or _getAfflictor("shield")
        fit.commandBonuses[bid] = ("normal", v, afflictor, _GANG_EFFECT)


def apply_overrides(req):
    """`overrides` through Pyfa's Attribute Overrides (eos/saveddata/override.py; gamedata Item.overrides, read by
    ModifiedAttributeDict.getOriginal while overrides are enabled). Pyfa semantics: per type and global for the
    whole request (own fit, projected fits, booster fits); only attributes the type itself has (Item.overrides
    never loads others; for a mutated item: base + mutated type attributes); a mutated attribute's rolled value wins over an override (getOriginal reads mutators
    after overrides); the last entry for a (type, attribute) wins. Returns a function removing them again
    (gamedata items are cached across requests). No-op without overrides: default output unchanged."""
    ovs = req.get("overrides") or []
    if not ovs:
        return lambda: None
    from eos.saveddata.override import Override
    from eos.modifiedAttributeDict import ModifiedAttributeDict
    by_type = {}
    for o in ovs:
        it = eos.db.getItem(int(o["type_id"]))
        at = eos.db.getAttributeInfo(int(o["attribute_id"]))
        if it is None or at is None:
            continue
        by_type.setdefault(it.ID, {})[at.name] = Override(it, at, float(o["value"]))
    # Serve eos.db.getOverrides (the saveddata lookup behind the lazy gamedata Item.overrides) from the request and
    # drop the items' loaded tables, so Item.overrides applies its own filter (the type's attributes; for a mutated
    # item the fresh getItemWithBaseItemAttribute copy, i.e. base + mutated type attributes).
    orig_get, orig_mut = eos.db.getOverrides, eos.db.getItemWithBaseItemAttribute
    seen = [eos.db.getItem(t) for t in by_type]

    def get_mut(*a, **k):
        item = orig_mut(*a, **k)
        item._Item__overrides = None
        seen.append(item)
        return item

    eos.db.getOverrides = lambda item_id, eager=None: list(by_type.get(item_id, {}).values())
    eos.db.getItemWithBaseItemAttribute = get_mut
    for it in seen:
        it._Item__overrides = None
    ModifiedAttributeDict.overrides_enabled = True

    def restore():
        eos.db.getOverrides, eos.db.getItemWithBaseItemAttribute = orig_get, orig_mut
        for it in seen:
            it._Item__overrides = None  # reloads from the (empty) saveddata DB on next use
        ModifiedAttributeDict.overrides_enabled = False
    return restore


def build(req):
    sh = item(req["ship"]["type_id"])
    ship = Citadel(sh) if sh.category.name == "Structure" else Ship(sh)
    fit = Fit(ship, "oracle")
    from eos.const import ImplantLocation
    fit.implantLocation = ImplantLocation.FIT
    fit.character = character(req)
    if req["ship"].get("mode_type_id"):
        fit.mode = ship.validateModeItem(eos.db.getItem(req["ship"]["mode_type_id"]))
    for m in req.get("modules", []):
        mod = mutated(Module, m)
        if m.get("charge_type_id"):
            mod.charge = item(m["charge_type_id"])
        fit.modules.append(mod)
        ORACLE_MODS.setdefault(id(fit), []).append(mod)
        mod.owner = fit
        st = STATES[m.get("state", "online")]
        mod.state = st if mod.isValidState(st) else FittingModuleState.ONLINE
    for d in req.get("drones", []):
        dr = mutated(Drone, d)
        dr.amount = d.get("quantity", 1)
        dr.amountActive = d.get("active", 0) or 0
        fit.drones.append(dr)
        ORACLE_DRONES.setdefault(id(fit), []).append(dr)
        dr.owner = fit
    for f in req.get("fighters", []):
        fi = Fighter(item(f["type_id"]))
        if f.get("quantity"):
            fi.amount = f["quantity"]
        fi.active = bool(f.get("active", True))
        if f.get("abilities") is not None:
            for ab in fi.abilities:
                ab.active = ab.effectID in f["abilities"]
        fit.fighters.append(fi)
        ORACLE_FIGHTERS.setdefault(id(fit), []).append(fi)
        fi.owner = fit
    for i in req.get("implants", []):
        fit.implants.append(Implant(item(i)))
    for b in req.get("boosters", []):
        bo = Booster(item(b["type_id"]))
        for se in bo.sideEffects:
            se.active = se.effectID in b.get("side_effects", [])
        fit.boosters.append(bo)
    for p in req.get("projected", []):
        if p.get("kind") == "module":
            for _ in range(p.get("amount", 1)):
                pm = mutated(Module, p["module"])
                if p["module"].get("charge_type_id"):
                    pm.charge = item(p["module"]["charge_type_id"])
                pm.state = FittingModuleState.ACTIVE if pm.isValidState(FittingModuleState.ACTIVE) else FittingModuleState.ONLINE
                pm.projectionRange = p.get("distance_m")
                fit.projectedModules.append(pm)
        elif p.get("kind") == "drone":
            pd = Drone(item(p["drone"]["type_id"]))
            pd.amount = p["drone"].get("quantity", 1) * p.get("amount", 1)
            pd.amountActive = pd.amount
            pd.projectionRange = p.get("distance_m")
            fit.projectedDrones.append(pd)
        elif p.get("kind") == "fighter":
            for _ in range(p.get("amount", 1)):
                pf = Fighter(item(p["fighter"]["type_id"]))
                if p["fighter"].get("quantity"):
                    pf.amount = p["fighter"]["quantity"]
                pf.active = bool(p["fighter"].get("active", True))
                pf.projectionRange = p.get("distance_m")
                if p["fighter"].get("abilities") is not None:
                    for ab in pf.abilities:
                        ab.active = ab.effectID in p["fighter"]["abilities"]
                fit.projectedFighters.append(pf)
        elif p.get("kind") == "fit":
            sreq = dict(p["fit"]); sreq["projected"] = []
            sf = build(sreq)
            eos.db.save(fit)
            eos.db.save(sf)
            fit.projectedFitDict[sf.ID] = sf
            eos.db.commit()
            pi = sf.getProjectionInfo(fit.ID)
            pi.active = True
            pi.amount = p.get("amount", 1)
            pi.projectionRange = p.get("distance_m")
            eos.db.commit()
        else:
            raise KeyError("projected kind %s unsupported by oracle" % p.get("kind"))
    for e in req.get("environment", {}).get("effect_type_ids", []):
        bm = Module(item(e))
        bm.state = FittingModuleState.ONLINE
        fit.projectedModules.append(bm)
    sec = (req.get("environment", {}).get("system_security") or "").lower()
    if sec:
        from eos.const import FitSystemSecurity
        fit.systemSecurity = {"hisec": FitSystemSecurity.HISEC, "lowsec": FitSystemSecurity.LOWSEC,
                              "nullsec": FitSystemSecurity.NULLSEC, "wspace": FitSystemSecurity.WSPACE}[sec]
    boosters = req.get("fleet", {}).get("booster_fits", [])
    if boosters:
        eos.db.save(fit)
        for b in boosters:
            bf = build(b)
            eos.db.save(bf)
            fit.commandFitDict[bf.ID] = bf
            eos.db.commit()
            ci = bf.getCommandInfo(fit.ID)
            ci.active = True
        eos.db.commit()
    explicit_buffs(fit, req.get("fleet", {}).get("buffs") or [])
    dp = req.get("damage_pattern") or {"em": 25, "thermal": 25, "kinetic": 25, "explosive": 25}
    fit.damagePattern = DamagePattern(dp["em"], dp["thermal"], dp["kinetic"], dp["explosive"])
    fit.factorReload = bool(req.get("options", {}).get("factor_reload", False))
    return fit


def stats(fit):
    s = fit.ship
    g = s.getModifiedItemAttr
    dps = fit.getTotalDps(spoolOptions=SPOOL)
    vol = fit.getTotalVolley(spoolOptions=SPOOL)
    out = {
        "cpu_used": fit.cpuUsed, "cpu_total": g("cpuOutput"), "power_used": fit.pgUsed, "power_total": g("powerOutput"),
        "calibration_used": fit.calibrationUsed, "drone_bandwidth_used": fit.droneBandwidthUsed,
        "hp": fit.hp, "ehp": fit.ehp,
        "resonance": {l: {t: g(("%s%sDamageResonance" % (l, t.capitalize())) if l != "hull" else "%sDamageResonance" % t)
                          for t in ("em", "thermal", "kinetic", "explosive")} for l in ("shield", "armor", "hull")},
        "tank": fit.tank, "sustainable_tank": fit.sustainableTank, "cap_used": fit.capUsed, "cap_recharge_peak_plus_added": fit.capRecharge,
        "weapon_dps": fit.getWeaponDps(spoolOptions=SPOOL).total, "weapon_volley": fit.getWeaponVolley(spoolOptions=SPOOL).total,
        "weapon_pure_dps": fit.getWeaponDps(spoolOptions=SPOOL).pure, "weapon_pure_volley": fit.getWeaponVolley(spoolOptions=SPOOL).pure,
        "drone_dps": fit.getDroneDps().total, "drone_volley": fit.getDroneVolley().total,
        "dps": dps.total, "volley": vol.total,
        "cap_capacity": g("capacitorCapacity"), "cap_recharge_s": g("rechargeRate") / 1000,
        "cap_stable": fit.capStable, "cap_state": fit.capState, "cap_used": fit.capUsed, "cap_recharge_peak": fit.capRecharge,
        "max_velocity": fit.maxSpeed, "align_time_s": fit.alignTime, "mass": g("mass"), "agility": g("agility"),
        "signature_radius": g("signatureRadius"), "warp_speed": fit.warpSpeed, "max_warp_distance": fit.maxWarpDistance,
        "max_targets": fit.maxTargets, "max_target_range": fit.maxTargetRange, "scan_resolution": g("scanResolution"),
        "scan_strength": fit.scanStrength, "jam_chance": fit.jamChance, "warp_scramble_status": g("warpScrambleStatus"), "probe_size": fit.probeSize,
        "hi_slots": g("hiSlots"), "med_slots": g("medSlots"), "low_slots": g("lowSlots"),
        "turret_hardpoints": g("turretSlotsLeft"), "launcher_hardpoints": g("launcherSlotsLeft"),
    }
    return out


ORACLE_MODS = {}
ORACLE_DRONES = {}
ORACLE_FIGHTERS = {}


def drones_fighters(fit):
    ds, fs = [], []
    for idx, d in enumerate(ORACLE_DRONES.get(id(fit), [])):
        try:
            if d.amountActive <= 0 or d.getDps().total <= 0:
                continue
        except Exception:
            continue
        ds.append({"drone_index": idx, "optimal_m": d.maxRange, "falloff_m": d.falloff, "tracking": d.getModifiedItemAttr("trackingSpeed"),
                   "max_velocity": d.getModifiedItemAttr("maxVelocity"), "signature_radius": d.getModifiedItemAttr("signatureRadius")})
    for idx, f in enumerate(ORACLE_FIGHTERS.get(id(fit), [])):
        try:
            if not f.active or f.getDps().total <= 0:
                continue
        except Exception:
            continue
        fs.append({"fighter_index": idx, "max_velocity": f.getModifiedItemAttr("maxVelocity"), "signature_radius": f.getModifiedItemAttr("signatureRadius")})
    return ds, fs


def weapons(fit):
    from eos.const import FittingHardpoint
    out = []
    for idx, mod in enumerate(ORACLE_MODS.get(id(fit), [])):
        try:
            if mod.state < FittingModuleState.ACTIVE or mod.getDps().total <= 0:
                continue
        except Exception:
            continue
        if mod.hardpoint == FittingHardpoint.TURRET:
            out.append({"module_index": idx, "optimal_m": mod.maxRange, "falloff_m": mod.falloff,
                        "tracking": mod.getModifiedItemAttr("trackingSpeed")})
        elif mod.hardpoint == FittingHardpoint.MISSILE and mod.charge is not None:
            out.append({"module_index": idx, "range_m": mod.maxRange,
                        "explosion_radius": mod.getModifiedChargeAttr("aoeCloudSize"),
                        "explosion_velocity": mod.getModifiedChargeAttr("aoeVelocity")})
    return out


# ---- ORACLE_EXTRA=profile: damage vs the request target profile, probe size (contract offense.vs_target_profile,
# targeting.probe_size) ------------------------------------------------------------------------------------------------
class _Profile:
    """Duck-typed TargetProfile for DmgTypes.profile (reads emAmount ... explosiveAmount, hp; resists as 0..1)."""
    def __init__(self, tp):
        self.emAmount, self.thermalAmount = float(tp.get("em") or 0), float(tp.get("thermal") or 0)
        self.kineticAmount, self.explosiveAmount = float(tp.get("kinetic") or 0), float(tp.get("explosive") or 0)


def profile_stats(fit, req):
    """Pyfa fit.calculateWeaponDmgStats / calculateDroneDmgStats set `profile = fit.targetProfile` on the DmgTypes;
    the stats panel then shows resist-applied damage (no signature / velocity application). Done here on the summed
    copies getTotalDps / getTotalVolley return, so the fit's own figures stay unprofiled."""
    tp = req.get("target_profile") or {}
    out = {}
    for k, dm in (("dps", fit.getTotalDps(spoolOptions=SPOOL)), ("volley", fit.getTotalVolley(spoolOptions=SPOOL))):
        dm.profile = _Profile(tp)
        out[k] = dm.total
    return {"vs_target_profile": out, "probe_size": fit.probeSize}


# ---- ORACLE_EXTRA=validity: Pyfa's fitting checks mapped to contract violation codes --------------------------------
def validity(fit, req):
    """Pyfa checks, decomposed into the contract codes (CONTRACT.md "Draft 1.11: validity"):
    fit level: cpuUsed / pgUsed / calibrationUsed / droneBandwidthUsed vs ship totals; getSlotsUsed vs slot counts
    (SLOTS_EXCEEDED); getHardpointsUsed vs turret/launcherSlotsLeft. Per module (Module.fits / __fitRestrictions /
    canHaveState / isValidCharge, in that order of rules): fit.canFit -> SHIP_RESTRICTION, capital module on a
    sub-capital hull -> SHIP_RESTRICTION, rigSize -> RIG_SIZE, raw maxGroupFitted -> MAX_GROUP_FITTED, canHaveState
    -> MAX_GROUP_ONLINE / MAX_GROUP_ACTIVE, isValidCharge capacity / chargeSize / chargeGroup1-4 -> CHARGE_CAPACITY /
    CHARGE_SIZE / CHARGE_GROUP. Skills: service.character.checkRequirements (rigs and fighter charges skipped,
    prerequisites of a missing skill recursed) -> MISSING_SKILL, one per missing skill id. Pyfa has no maxTypeFitted
    check (not reported here)."""
    from eos.const import FittingHardpoint
    sh = fit.ship
    v = []

    def add(code, idx=None, **kw):
        v.append(dict({"code": code, "module_index": idx}, **kw))
    g = sh.getModifiedItemAttr
    for code, used, tot in (("CPU_OVERLOAD", fit.cpuUsed, g("cpuOutput")), ("POWER_OVERLOAD", fit.pgUsed, g("powerOutput")),
                            ("CALIBRATION_OVERLOAD", fit.calibrationUsed, g("upgradeCapacity")),
                            ("DRONE_BANDWIDTH", fit.droneBandwidthUsed, g("droneBandwidth"))):
        if (used or 0) > (tot or 0) + 1e-9:
            add(code)
    mods = ORACLE_MODS.get(id(fit), [])
    for slot in (FittingSlot.HIGH, FittingSlot.MED, FittingSlot.LOW, FittingSlot.RIG, FittingSlot.SUBSYSTEM, FittingSlot.SERVICE):
        if fit.getSlotsFree(slot.value) < 0:  # int, as the fitting view passes it (getSlotsUsed compares with `is`)
            add("SLOTS_EXCEEDED", None, slot=slot.name.lower(), modules=[i for i, m in enumerate(mods) if m.slot == slot])
    for code, hp in (("TURRET_HARDPOINTS", FittingHardpoint.TURRET), ("LAUNCHER_HARDPOINTS", FittingHardpoint.MISSILE)):
        if fit.getHardpointsFree(hp) < 0:
            add(code, None, modules=[i for i, m in enumerate(mods) if m.hardpoint == hp])
    for i, m in enumerate(mods):
        if not fit.canFit(m.item) or (not isinstance(sh, Citadel) and g("isCapitalSize", 0) != 1 and m.isCapitalSize):
            add("SHIP_RESTRICTION", i)
        if m.slot == FittingSlot.RIG and m.getModifiedItemAttr("rigSize") != g("rigSize"):
            add("RIG_SIZE", i)
        mx = m.item.attributes.get("maxGroupFitted")
        if mx is not None and mx.value:
            others = sum(1 for o in mods if o is not m and o.item.groupID == m.item.groupID)
            if others >= mx.value:
                add("MAX_GROUP_FITTED", i)
        if m.state >= FittingModuleState.ONLINE:
            ms = m.canHaveState(m.state)
            if ms is not True:
                add("MAX_GROUP_ONLINE" if ms <= FittingModuleState.OFFLINE else "MAX_GROUP_ACTIVE", i)
        c = m.charge
        if c is not None:
            cv, mc = c.attributes["volume"].value, m.item.attributes["capacity"].value
            if cv is not None and mc is not None and cv > mc:
                add("CHARGE_CAPACITY", i)
            ics = m.getModifiedItemAttr("chargeSize")
            if ics > 0 and ics != c.getAttribute("chargeSize"):
                add("CHARGE_SIZE", i)
            if not any(m.getModifiedItemAttr("chargeGroup%d" % k, None) == c.groupID for k in range(5)):
                add("CHARGE_GROUP", i)
    # service/character.py Character.checkRequirements + _checkRequirements (no wx import needed)
    char = fit.character
    missing = {}

    def walk(thing):
        for rq, lvl in thing.requiredSkills.items():
            if char is None or char.getSkill(rq).level < lvl:
                if missing.get(rq.ID, 0) < lvl:
                    missing[rq.ID] = lvl
                walk(rq)
    for thing in [*mods, *fit.drones, *fit.fighters, fit.ship, *fit.appliedImplants, *fit.boosters]:
        if isinstance(thing, Module) and thing.slot == FittingSlot.RIG:
            continue
        walk(thing.item)
        if not isinstance(thing, Fighter) and getattr(thing, "charge", None) is not None:
            walk(thing.charge)
    for sid, lvl in sorted(missing.items()):
        add("MISSING_SKILL", None, skill_type_id=sid, level=lvl)
    return v


# ---- opt-in extra outputs (ORACLE_EXTRA="attrs,ext"); unset = output identical to before -----------------------------
ORACLE_EXTRA = {x.strip() for x in os.environ.get("ORACLE_EXTRA", "").split(",") if x.strip()}


def _attrs(obj, charge=False):
    d = obj.chargeModifiedAttributes if charge else obj.itemModifiedAttributes
    out = {}
    for k in list(d.keys()):
        try:
            v = d[k]
        except Exception:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v):
            out[k] = v
    return out


def attr_dump(fit):
    """Modified attributes by name (Pyfa ModifiedAttributeDict), for the effect suite: ship, every modules[] entry
    (+ its charge), every drones[] entry, every fighters[] entry."""
    mods = []
    for m in ORACLE_MODS.get(id(fit), []):
        e = {"item": _attrs(m)}
        if m.charge is not None:
            e["charge"] = _attrs(m, charge=True)
        mods.append(e)
    return {"ship": _attrs(fit.ship), "modules": mods,
            "drones": [_attrs(d) for d in fit.drones], "fighters": [_attrs(f) for f in fit.fighters]}


_THERMO = None


def _thermodynamics():
    """gui/builtinViewColumns/heat.py `Thermodynamics`, loaded from Pyfa's source unmodified (the module itself
    imports the wx GUI, so only the class body is executed, with the names it uses)."""
    global _THERMO
    if _THERMO is None:
        src = open(os.path.join(PYFA, "gui/builtinViewColumns/heat.py")).read()
        body = src[src.index("class Thermodynamics"):src.index("class Heat(")]
        ns = {"math": math, "FittingModuleState": FittingModuleState}
        exec(compile(body, "heat.py:Thermodynamics", "exec"), ns)
        _THERMO = ns["Thermodynamics"]
    return _THERMO


def _bombing(fit):
    """gui/builtinStatsViews/bombingViewFull.py refreshPanel arithmetic: bombs needed per bomb type and Covert Ops
    level (the panel prints ceil(x*10)/10)."""
    def ga(a):
        return fit.ship.getModifiedItemAttr(a)
    env = 1.0
    reds = ["Class %d Red Giant Effects" % i for i in range(6, 0, -1)]
    for e in fit.projectedModules:
        if e.state == FittingModuleState.ONLINE and e.fullName in reds:
            env *= e.item.attributes["smartbombDamageMultiplier"].value
    sig = ga("signatureRadius")
    hull, armor, shield = ga("hp"), ga("armorHP"), ga("shieldCapacity")
    out = {}
    for dt, bomb_id in (("em", 27920), ("thermal", 27916), ("kinetic", 27912), ("explosive", 27918)):
        D = dt.capitalize()
        ehp = hull / ga("%sDamageResonance" % dt) + armor / ga("armor%sDamageResonance" % D) + shield / ga("shield%sDamageResonance" % D)
        bomb = item(bomb_id)
        base = sum(bomb.attributes[a].value for a in ("emDamage", "thermalDamage", "kineticDamage", "explosiveDamage"))
        bsig = bomb.attributes["signatureRadius"].value
        out[dt] = {str(lvl): math.ceil((ehp / (base * (1 + 0.05 * lvl) * env * (min(bsig, sig) / bsig))) * 10) / 10 for lvl in range(6)}
    return out


def ext_stats(fit):
    """Pyfa values for features beyond bench 1.9.0 (docs/20 P0-3 / P0-4 'stats-ext' and 'heat' suites)."""
    from eos.utils.spoolSupport import SpoolOptions as SO
    def rr(o):
        return {"shield": o.shield, "armor": o.armor, "hull": o.hull, "capacitor": o.capacitor}
    out = {
        "mining": {"miner_yield": fit.minerYield, "miner_drain": fit.minerDrain, "drone_yield": fit.droneYield,
                   "drone_drain": fit.droneDrain},
        "outgoing": {"current": rr(fit.getRemoteReps(spoolOptions=SPOOL)),
                     "min": rr(fit.getRemoteReps(spoolOptions=SO(SpoolType.SPOOL_SCALE, 0, True))),
                     "max": rr(fit.getRemoteReps(spoolOptions=SO(SpoolType.SPOOL_SCALE, 1, True)))},
        "bombing": _bombing(fit),
    }
    dr = []
    for i, d in enumerate(fit.drones):
        dr.append({"drone_index": i, "hp": d.hp, "ehp": d.ehp, "shield_regen": d.calculateShieldRecharge()})
    out["drones"] = dr
    fr = []
    for i, f in enumerate(fit.fighters):
        e = {"fighter_index": i, "hp": f.hp, "ehp": f.ehp}
        try:
            e["shield_regen"] = f.calculateShieldRecharge()
        except Exception:
            pass
        fr.append(e)
    out["fighters"] = fr
    heat = []
    th = None
    for i, m in enumerate(ORACLE_MODS.get(id(fit), [])):
        if m.state != FittingModuleState.OVERHEATED:
            continue
        th = th or _thermodynamics()(fit)
        cyc = th.calcBurnCycles(m)
        ct = (m.getModifiedItemAttr("duration") or 0) / 1000 or (m.getModifiedItemAttr("speed") or 0) / 1000
        heat.append({"module_index": i, "burn_cycles": cyc, "burnout_s": cyc * ct})
    out["heat"] = heat
    return out


def main():
    for path in sys.argv[1:]:
        req = json.load(open(path))
        restore = apply_overrides(req)
        try:
            run_one(path, req)
        finally:
            restore()


def run_one(path, req):
    if True:
        try:
            fit = build(req)
        except Exception as e:  # e.g. type missing from Pyfa's (older) eve.db
            try:
                eos.db.saveddata_session.rollback()
            except Exception:
                pass
            print(json.dumps({"file": os.path.basename(path), "error": repr(e)}))
            return
        t0 = time.perf_counter()
        fit.calculateModifiedAttributes()
        st = stats(fit)
        st["weapons"] = weapons(fit)
        st["drones"], st["fighters"] = drones_fighters(fit)
        st["drone_control_range"] = fit.extraAttributes["droneControlRange"]
        if "attrs" in ORACLE_EXTRA:
            st["attrs"] = attr_dump(fit)
        if "ext" in ORACLE_EXTRA:
            st["ext"] = ext_stats(fit)
        if "profile" in ORACLE_EXTRA:
            st["profile"] = profile_stats(fit, req)
        if "validity" in ORACLE_EXTRA:
            st["validity"] = validity(fit, req)
        first = time.perf_counter() - t0
        n = int(os.environ.get("ORACLE_REPEAT", "5"))
        t1 = time.perf_counter()
        for _ in range(n):
            f2 = build(req)
            f2.calculateModifiedAttributes()
            stats(f2)
        rep = (time.perf_counter() - t1) / max(n, 1)
        print(json.dumps({"file": os.path.basename(path), "stats": st, "timing_ms": {"first": first * 1000, "warm_avg_incl_build": rep * 1000}}, default=str))


if __name__ == "__main__":
    main()
