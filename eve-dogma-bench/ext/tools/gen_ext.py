#!/usr/bin/env python3
"""stats-ext / heat / fleet.buffs / overrides suite generator (docs/20 P0-3, P0-4; bench 1.10 draft).
  python3 ext/tools/gen_ext.py [POOL_LIST LEGAL_JSONL]
Writes ext/cases/<case>.json and ext/MANIFEST.json ({case: {feature, source}}).
  hand-built Pyfa reference fits (mining, outgoing RR, drone/fighter EHP, bombing, fleet.buffs) by type name;
  random LEGAL fits picked from a gen_legal pool (oracle/fuzz/gen_legal.py + check_legal.py), when given:
  first fits per distinct hull that have the feature (mining modules/drones, RR modules/drones, drones,
  fighters, overheated modules);
  overrides: hand-derived expectations, written by this script to ext/expected/ (non-Pyfa, see ext/README.md).
Pyfa expectations for the rest: ext/tools/make_expected.py."""
import copy, gzip, json, os, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
SUITE = ROOT / "ext"
D = json.load(gzip.open(os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")))
T = {int(k): v for k, v in D["types"].items()}
NAME = {}
for k, v in sorted(T.items()):
    NAME.setdefault(v["name"], k)


def tid(n):
    if n not in NAME:
        raise KeyError(n)
    return NAME[n]


def base_req(ship, skills=5):
    return {"schema_version": 1, "ship": {"type_id": tid(ship), "mode_type_id": None},
            "character": {"skills": {"default_level": skills, "levels": {}}, "security_status": None},
            "modules": [], "drones": [], "fighters": [], "implants": [], "boosters": [], "cargo": [],
            "fleet": {"buffs": [], "booster_fits": []}, "projected": [],
            "environment": {"effect_type_ids": [], "system_security": None}, "damage_pattern": None,
            "options": {}}


def mod(n, state="active", charge=None, slot=None):
    m = {"type_id": tid(n), "state": state, "charge_type_id": tid(charge) if charge else None, "mutation": None, "spool": None}
    if slot:
        m["slot"] = slot
    return m


def fit(ship, mods=(), drones=(), skills=5, **kw):
    r = base_req(ship, skills)
    for m in mods:
        if isinstance(m, tuple):
            n, k = m[0], m[1]
            r["modules"] += [mod(n, *m[2:]) for _ in range(k)]
        else:
            r["modules"].append(mod(m))
    for n, q, act in drones:
        r["drones"].append({"type_id": tid(n), "quantity": q, "active": act, "mutation": None})
    for k, v in kw.items():
        r[k] = v
    return r


cases, man = {}, {}


def add(name, feature, req, source="hand-built (Pyfa oracle)"):
    cases[name] = req
    man[name] = {"feature": feature, "source": source}


# ---- mining ------------------------------------------------------------------------------------------------------
add("mining_venture", "mining", fit("Venture", [("Miner II", 2), ("Mining Laser Upgrade II", 1, "online")], [("Mining Drone II", 2, 2)]))
add("mining_venture_skills0", "mining", fit("Venture", [("Miner II", 2)], [("Mining Drone I", 2, 2)], skills=0))
add("mining_hulk_strip", "mining", fit("Hulk", [("Modulated Strip Miner II", 2),
                                                 ("Mining Laser Upgrade II", 2, "online")], [("Mining Drone II", 5, 5)]))
add("mining_hulk_skills4", "mining", fit("Hulk", [("Modulated Strip Miner II", 2)], skills=4))
add("mining_covetor_strip_i", "mining", fit("Covetor", [("Strip Miner I", 2)], [("Mining Drone I", 5, 5)]))
add("mining_procurer_ice", "mining", fit("Procurer", [("Ice Harvester II", 1)]))
add("mining_venture_gas", "mining", fit("Venture", [("Gas Cloud Scoop II", 2)]))
add("mining_porpoise_drones", "mining", fit("Porpoise", [], [("Mining Drone II", 5, 5)]))
add("mining_porpoise_ice_drones", "mining", fit("Porpoise", [], [("Ice Harvesting Drone II", 2, 1)]))
r = fit("Hulk", [("Modulated Strip Miner II", 2)])
r["fleet"]["buffs"] = [{"buff_id": 23, "value": 30.0}, {"buff_id": 24, "value": -15.0}]
add("mining_hulk_fleet_buffs", "mining+fleet.buffs", r)
# ---- outgoing remote reps / cap transfer ---------------------------------------------------------------------------
add("rr_guardian", "outgoing", fit("Guardian", [("Large Remote Armor Repairer II", 4), ("Large Remote Capacitor Transmitter II", 1)]))
add("rr_basilisk", "outgoing", fit("Basilisk", [("Large Remote Shield Booster II", 4), ("Large Remote Capacitor Transmitter II", 1)]))
add("rr_oneiros", "outgoing", fit("Oneiros", [("Large Remote Armor Repairer II", 4)]))
add("rr_scimitar", "outgoing", fit("Scimitar", [("Large Remote Shield Booster II", 4)]))
add("rr_zarmazd_spool", "outgoing", fit("Zarmazd", [("Heavy Mutadaptive Remote Armor Repairer II", 1), ("Large Remote Armor Repairer II", 2)]))
r = fit("Zarmazd", [("Heavy Mutadaptive Remote Armor Repairer II", 1), ("Large Remote Armor Repairer II", 2)])
for m in r["modules"]:
    m["spool"] = {"type": "spool_scale", "amount": 1.0}
add("rr_zarmazd_spool_full", "outgoing", r)
add("rr_vexor_light_bots", "outgoing", fit("Vexor", [], [("Light Armor Maintenance Bot I", 5, 5)]))
add("rr_dominix_heavy_bots", "outgoing", fit("Dominix", [], [("Heavy Armor Maintenance Bot II", 5, 5)]))
add("rr_dominix_shield_bots", "outgoing", fit("Dominix", [], [("Heavy Shield Maintenance Bot II", 5, 5)]))
add("rr_guardian_skills0", "outgoing", fit("Guardian", [("Large Remote Armor Repairer II", 4)], skills=0))
# ---- drone / fighter EHP -----------------------------------------------------------------------------------------
add("dehp_vexor_hobgoblin", "drone_ehp", fit("Vexor", [], [("Hobgoblin II", 5, 5)]))
add("dehp_vexor_hobgoblin_skills0", "drone_ehp", fit("Vexor", [], [("Hobgoblin II", 5, 5)], skills=0))
r = fit("Ishtar", [], [("Hammerhead II", 5, 5)])
r["damage_pattern"] = {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 100}
add("dehp_ishtar_hammerhead_explosive", "drone_ehp", r)
add("dehp_dominix_ogre_enhancer", "drone_ehp", fit("Dominix", [("Large Drone Durability Enhancer II", 2, "online")], [("Ogre II", 5, 5)]))
add("dehp_dominix_mixed", "drone_ehp", fit("Dominix", [], [("Ogre II", 2, 2), ("Hobgoblin II", 3, 3), ("Hammerhead II", 5, 0)]))
# ---- bombing panel ------------------------------------------------------------------------------------------------
for ship in ("Rifter", "Vexor", "Dominix", "Purifier", "Ishtar", "Hulk", "Rorqual", "Basilisk"):
    add(f"bomb_{ship.lower()}", "bombing", fit(ship, []))
add("bomb_ishtar_shieldext", "bombing", fit("Ishtar", [("Large Shield Extender II", 2, "online"), ("Damage Control II", 1, "online")]))
r = fit("Dominix", [])
r["environment"]["effect_type_ids"] = [tid("Class 6 Red Giant Effects")]
add("bomb_dominix_red_giant6", "bombing", r)
r = fit("Rifter", [])
r["environment"]["effect_type_ids"] = [tid("Class 3 Red Giant Effects")]
add("bomb_rifter_red_giant3", "bombing", r)
# ---- fleet.buffs (explicit warfare buffs; Pyfa command bonuses) -------------------------------------------------
def fb(name, ship, mods, buffs, drones=(), base=None):
    r = base or fit(ship, mods, drones)
    r["fleet"]["buffs"] = [{"buff_id": b, "value": v} for b, v in buffs]
    add(name, "fleet.buffs", r)


SHIELD = [("Medium Shield Booster II", 1), ("5MN Microwarpdrive II", 1), ("Warp Scrambler II", 1), ("Stasis Webifier II", 1)]
fb("fleet_buffs_shield_resist", "Vexor", SHIELD, [(10, -10.0)])
fb("fleet_buffs_shield_all", "Vexor", SHIELD, [(10, -12.5), (11, -15.0), (12, 25.0)])
fb("fleet_buffs_armor_all", "Vexor", [("Medium Armor Repairer II", 1), ("Damage Control II", 1, "online")], [(13, -10.0), (14, -15.0), (15, 20.0)])
fb("fleet_buffs_skirmish", "Vexor", SHIELD, [(20, -12.0), (21, 30.0), (22, 15.0), (60, -10.0)])
fb("fleet_buffs_info", "Vexor", SHIELD, [(16, 25.0), (17, 15.0), (18, 20.0), (19, -20.0), (26, 25.0)])
fb("fleet_buffs_min_aggregate_dup", "Vexor", SHIELD, [(10, -5.0), (10, -12.0), (20, -3.0), (20, -9.0)])
fb("fleet_buffs_max_aggregate_dup", "Vexor", SHIELD, [(12, 10.0), (12, 22.0), (26, 5.0), (26, 18.0)])
fb("fleet_buffs_drones", "Vexor", SHIELD, [(10, -10.0), (20, -10.0)], drones=[("Hammerhead II", 5, 5)])
fb("fleet_buffs_skills0", "Vexor", SHIELD, [(10, -10.0), (12, 10.0)], base=fit("Vexor", SHIELD, skills=0))
fb("fleet_buffs_titan_generators", "Vexor", SHIELD, [(39, -20.0), (42, 15.0), (45, -10.0)])
CLAY = fit("Claymore", [("Shield Command Burst II", 1, "active", "Shield Harmonizing Charge"),
                        ("Shield Command Burst II", 1, "active", "Shield Extension Charge")])
r = fit("Vexor", SHIELD)
r["fleet"]["booster_fits"] = [CLAY]
add("fleet_booster_claymore_only", "fleet.buffs", r)
r = copy.deepcopy(r)
r["fleet"]["buffs"] = [{"buff_id": 10, "value": -5.0}]
add("fleet_buffs_override_booster_claymore", "fleet.buffs", r)
# ---- overrides: hand-derived (non-Pyfa) -----------------------------------------------------------------------------
A = {v["name"]: int(k) for k, v in D["attributes"].items()}


def base(t, attr):
    v = T[t]["attrs"].get(str(A[attr]))
    return v if v is not None else T[t].get({"mass": "mass", "capacity": "capacity", "volume": "volume"}.get(attr, ""), 0.0)


ovr_expected = {}


def ovr(name, req, overrides, values, derivation):
    req["overrides"] = [{"type_id": t, "attribute_id": A[a], "value": v} for t, a, v in overrides]
    add(name, "overrides", req, "hand-derived (non-Pyfa)")
    ovr_expected[name] = {"case": name, "oracle": "hand-derived (non-Pyfa)", "values": values, "ext": {},
                          "derivation": derivation, "excluded": {}}


RIF = tid("Rifter")
ovr("ovr_rifter_velocity_skills0", fit("Rifter", [], skills=0), [(RIF, "maxVelocity", 400.0)], {"max_velocity": 400.0},
    "Empty Rifter, all skills 0: no modifier touches maxVelocity, so max_velocity = the overridden base 400.")
ovr("ovr_rifter_velocity_skills5", fit("Rifter", []), [(RIF, "maxVelocity", 400.0)], {"max_velocity": 500.0},
    "All skills V: Navigation +5%/level on ship maxVelocity -> 400 * 1.25 = 500 (no other velocity modifier on an empty Rifter).")
ovr("ovr_rifter_shield_skills0", fit("Rifter", [], skills=0), [(RIF, "shieldCapacity", 1000.0)], {"hp.shield": 1000.0},
    "Skills 0, no modules: hp.shield = overridden shieldCapacity 1000.")
ovr("ovr_rifter_shield_skills5", fit("Rifter", []), [(RIF, "shieldCapacity", 1000.0)], {"hp.shield": 1250.0},
    "Shield Management +5%/level on shieldCapacity: 1000 * 1.25 = 1250.")
lse = tid("Medium Shield Extender II")
sb = base(RIF, "shieldCapacity")
ovr("ovr_module_shield_extender_x2", fit("Rifter", [("Medium Shield Extender II", 2, "online")], skills=0),
    [(lse, "capacityBonus", 1000.0)], {"hp.shield": sb + 2000.0},
    f"Skills 0: Rifter base shieldCapacity {sb} + 2 extenders x overridden capacityBonus 1000 (modAdd, not stacking"
    f"-penalised; the override applies to every module of that type) = {sb + 2000.0}.")
ac = tid("200mm AutoCannon I")
emp = tid("EMP S")
dm = base(ac, "damageMultiplier")
r = fit("Rifter", [("200mm AutoCannon I", 1, "active", "EMP S")], skills=0)
ovr("ovr_charge_damage_volley", r, [(emp, "emDamage", 100.0), (emp, "thermalDamage", 0.0), (emp, "kineticDamage", 0.0),
                                    (emp, "explosiveDamage", 0.0)], {"weapon_volley": 100.0 * dm},
    f"Skills 0 (no Gunnery / Minmatar Frigate bonuses): volley = charge damage (overridden to 100 EM, 0 else) x "
    f"200mm AutoCannon I damageMultiplier {dm} = {100.0 * dm}.")


def pool_pick(pool_list, legal_jsonl):
    MIN, RR = {54, 464, 483, 737}, {41, 325, 585, 67, 2018, 1697, 1698}
    legal = {}
    for l in open(legal_jsonl):
        r = json.loads(l)
        legal[r["file"]] = r["legal"]
    want = {"mining": 12, "mining_drones": 8, "outgoing": 14, "outgoing_drones": 8, "drone_ehp": 10, "fighter_ehp": 6, "heat": 30, "bombing": 4}
    got = {k: [] for k in want}
    hulls = {k: set() for k in want}
    for p in sorted(open(pool_list).read().split()):
        f = os.path.basename(p)
        if not legal.get(f):
            continue
        r = json.load(open(p))
        sh = r["ship"]["type_id"]
        act = [T[m["type_id"]]["group"] for m in r.get("modules", []) if m.get("state") in ("active", "overheated")]
        ad = [T[d["type_id"]]["group"] for d in r.get("drones", []) if d.get("active")]
        feats = []
        if any(g in MIN for g in act):
            feats.append("mining")
        if 101 in ad:
            feats.append("mining_drones")
        if any(g in RR for g in act):
            feats.append("outgoing")
        if 640 in ad:
            feats.append("outgoing_drones")
        if r.get("drones"):
            feats.append("drone_ehp")
        if r.get("fighters"):
            feats.append("fighter_ehp")
        if any(m.get("state") == "overheated" for m in r.get("modules", [])):
            feats.append("heat")
        feats.append("bombing")
        for k in feats:
            if len(got[k]) < want[k] and sh not in hulls[k]:
                got[k].append((f, r))
                hulls[k].add(sh)
                break  # one feature per pool fit
    for k, lst in got.items():
        for f, r in lst:
            add(f"pool_{k}_{f[:-5]}", k.replace("_drones", "").replace("fighter_ehp", "drone_ehp"), r,
                f"random legal fit {f} (gen_legal pool; Pyfa oracle)")


if len(sys.argv) == 3:
    pool_pick(sys.argv[1], sys.argv[2])
(SUITE / "cases").mkdir(parents=True, exist_ok=True)
(SUITE / "expected").mkdir(parents=True, exist_ok=True)
for n, r in cases.items():
    (SUITE / "cases" / f"{n}.json").write_text(json.dumps(r, indent=1, sort_keys=True) + "\n")
for n, e in ovr_expected.items():
    (SUITE / "expected" / f"{n}.json").write_text(json.dumps(e, indent=1, sort_keys=True) + "\n")
(SUITE / "MANIFEST.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n")
import collections  # noqa: E402
print(len(cases), "cases:", dict(collections.Counter(m["feature"] for m in man.values())))
