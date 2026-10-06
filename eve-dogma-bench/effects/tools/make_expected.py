#!/usr/bin/env python3
"""effects/expected/<case>.json from the Pyfa oracle with ORACLE_EXTRA=attrs (modified attribute dump).
usage: python3 effects/tools/make_expected.py [--jobs N] [effects/cases/*.json]
Per item (ship, modules[i] item + charge, drones[i], fighters[i]) the expected dump keeps attribute A when
  - A is a dataset attribute name (Pyfa's pseudo-attributes such as armorRepair are dropped),
  - Pyfa's base value of A for that type equals the dataset's (else excluded as data_drift: Pyfa data build 3532181
    vs SDE 3569502; mostly `radius` of non-ships),
  - A is not one of Pyfa's internal representations (pyfa_internal: NOS capacitorNeed, command-burst
    warfareBuffN Value/Multiplier routing),
  - A is not modified only by SDE effects Pyfa does not implement while Pyfa leaves it at base (not_in_pyfa),
  - A is not a modifier-source attribute that Pyfa leaves at its base value (excluded as bonus_source: Pyfa folds
    skill levels into the handler, e.g. ship.shipBonusMF stays -7.5, while SDE-expression engines multiply the
    attribute itself; the bonus is still checked through the attributes it modifies).
Also writes the bench metric values (tools/metrics.py from_pyfa) so the standard stats are scored too (all dropped,
as excluded.values, when the hull itself has data drift other than radius, e.g. the Marauders' agility)."""
import collections, gzip, json, os, pathlib, sqlite3, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from metrics import from_pyfa, METRICS  # noqa: E402
REF = os.environ.get("EXCT_REF", "/workspace/exct-eve/ref")
PYFA = os.environ.get("PYFA", f"{REF}/pyfa")
PY = os.environ.get("PYFA_PY", f"{REF}/pyfa-venv/bin/python")
STUB = os.environ.get("WX_STUB", f"{REF}/stubs")
DATASET = os.environ.get("EVE_DOGMA_DATASET", "/workspace/exct-eve/data/dataset-3569502.json.gz")
SUITE = ROOT / "effects"

D = json.load(gzip.open(DATASET))
T = {int(k): v for k, v in D["types"].items()}
DS_ID = {v["name"]: int(k) for k, v in D["attributes"].items()}
DS_DEF = {int(k): v.get("default") or 0.0 for k, v in D["attributes"].items()}
SOURCES = {D["attributes"][str(m[3])]["name"] for e in D["effects"].values() for m in e["mods"] if str(m[3]) in D["attributes"]}
# plus attributes Pyfa's hand-written handlers read by name (bonus attributes such as shipBonusForceAuxiliaryA3)
import re  # noqa: E402
SOURCES |= set(re.findall(r"""getModifiedItemAttr\(\s*['"](\w+)['"]""", open(os.path.join(PYFA, "eos/effects.py")).read()))
db = sqlite3.connect(os.path.join(PYFA, "eve.db"))
P_ID = {n: i for i, n in db.execute("select attributeID, attributeName from dgmattribs")}
P_DEF = {i: (v or 0.0) for i, v in db.execute("select attributeID, defaultValue from dgmattribs")}
PB = collections.defaultdict(dict)
for v, t, a in db.execute("select value, typeID, attributeID from dgmtypeattribs"):
    PB[t][a] = v
FIELDS = {4: "mass", 161: "volume", 38: "capacity", 162: "radius"}
PYCLS = set(re.findall(r'^class Effect\d+\(BaseEffect\):\n    """\n    (\w+)\n', open(os.path.join(PYFA, "eos/effects.py")).read(), re.M))
ANAME = {int(k): v["name"] for k, v in D["attributes"].items()}
EFF = {int(k): v for k, v in D["effects"].items()}
SKILLS = [t for t, v in T.items() if v["category"] == 16 and v.get("published")]
# Pyfa-internal representations (documented in effects/README.md): Pyfa's nosferatu handler stores the drain as a
# negative capacitorNeed; Pyfa's command-burst handlers route strength bonuses through the module's
# warfareBuffNValue / the charge's warfareBuffNMultiplier, where SDE-expression engines modify other attributes.
# The resulting buffs are scored by bench fleet_* / ext fleet_buffs_* cases.
PYFA_INTERNAL = {"warfareBuff1Value", "warfareBuff2Value", "warfareBuff3Value", "warfareBuff4Value",
                 "warfareBuff1Multiplier", "warfareBuff2Multiplier", "warfareBuff3Multiplier", "warfareBuff4Multiplier"}
NOS_GROUP = 68


def not_in_pyfa_targets(req):
    """attribute names modified by SDE effects that Pyfa does not implement (no eos/effects.py class: mostly the
    skill-multiplier effects Pyfa folds into its handlers), carried by any type in this request"""
    types = {req["ship"]["type_id"]} | {m["type_id"] for m in req.get("modules", [])} | \
        {m["charge_type_id"] for m in req.get("modules", []) if m.get("charge_type_id")} | \
        {d["type_id"] for d in req.get("drones", [])} | {f["type_id"] for f in req.get("fighters", [])} | \
        set(req.get("implants", [])) | {b["type_id"] for b in req.get("boosters", [])} | \
        set(req.get("environment", {}).get("effect_type_ids", []))
    if req["ship"].get("mode_type_id"):
        types.add(req["ship"]["mode_type_id"])
    sk = req.get("character", {}).get("skills", {})
    if sk.get("default_level", 0):
        types |= set(SKILLS)
    types |= {int(k) for k, v in (sk.get("levels") or {}).items() if str(k).isdigit() and v}
    out = set()
    for t in types:
        for eid, _ in (T.get(t, {}).get("effects") or []):
            e = EFF.get(eid)
            if e and e["mods"] and e["name"] not in PYCLS:
                out |= {ANAME.get(m[2]) for m in e["mods"]}
    return out


def ds_base(t, name):
    aid = DS_ID[name]
    v = T[t]["attrs"].get(str(aid))
    if v is None and aid in FIELDS:
        v = T[t].get(FIELDS[aid])
    return DS_DEF.get(aid, 0.0) if v is None else v


def py_base(t, name):
    aid = P_ID.get(name)
    if aid is None:
        return None
    return PB[t].get(aid, P_DEF.get(aid, 0.0))


def same(x, y):
    return x is not None and y is not None and abs(x - y) <= 1e-9 * max(1.0, abs(x))


def filt(t, dump, path, excl, nip=frozenset()):
    out = {}
    for k, v in sorted(dump.items()):
        if k not in DS_ID:
            continue
        if k in PYFA_INTERNAL or (k == "capacitorNeed" and T[t]["group"] == NOS_GROUP):
            excl.setdefault("pyfa_internal", []).append(f"{path}.{k}")
            continue
        pb = py_base(t, k)
        if not same(pb, ds_base(t, k)):
            excl.setdefault("data_drift", []).append(f"{path}.{k}")
            continue
        if k in SOURCES and same(v, pb):
            excl.setdefault("bonus_source", []).append(f"{path}.{k}")
            continue
        if k in nip and same(v, pb):
            excl.setdefault("not_in_pyfa", []).append(f"{path}.{k}")
            continue
        out[k] = v
    return out


def expected_for(req, st):
    excl = {}
    nip = frozenset(not_in_pyfa_targets(req))
    at = st["attrs"]
    exp = {"ship": filt(req["ship"]["type_id"], at["ship"], "ship", excl, nip), "modules": [], "drones": [], "fighters": []}
    for i, (m, r) in enumerate(zip(at["modules"], req["modules"])):
        e = {"item": filt(r["type_id"], m["item"], f"modules[{i}]", excl, nip)}
        if "charge" in m and r.get("charge_type_id"):
            e["charge"] = filt(r["charge_type_id"], m["charge"], f"modules[{i}].charge", excl, nip)
        exp["modules"].append(e)
    for i, (d, r) in enumerate(zip(at["drones"], req["drones"])):
        exp["drones"].append(filt(r["type_id"], d, f"drones[{i}]", excl, nip))
    for i, (f, r) in enumerate(zip(at["fighters"], req["fighters"])):
        exp["fighters"].append(filt(r["type_id"], f, f"fighters[{i}]", excl, nip))
    return exp, excl


CACHE = os.environ.get("EFF_ORACLE_CACHE")  # dir: reuse raw oracle output per case (re-filtering without Pyfa runs)


def run_chunk(files):
    if CACHE and all(os.path.exists(os.path.join(CACHE, os.path.basename(f))) for f in files):
        return [json.load(open(os.path.join(CACHE, os.path.basename(f)))) for f in files], ""
    env = dict(os.environ, PYTHONPATH=STUB, ORACLE_REPEAT="0", PYFA=PYFA, ORACLE_EXTRA="attrs")
    out = subprocess.run([PY, str(ROOT / "oracle/pyfa_oracle.py"), *files], capture_output=True, text=True, cwd=PYFA, env=env)
    return [json.loads(l) for l in out.stdout.splitlines() if l.startswith("{")], out.stderr[-2000:] if out.returncode else ""


def main(argv):
    jobs = 4
    if argv[:1] == ["--jobs"]:
        jobs, argv = int(argv[1]), argv[2:]
    files = [str(pathlib.Path(f).resolve()) for f in argv] or sorted(str(p) for p in (SUITE / "cases").glob("*.json"))
    man = json.loads((SUITE / "MANIFEST.json").read_text())
    (SUITE / "expected").mkdir(exist_ok=True)
    chunks = [files[i:i + 100] for i in range(0, len(files), 100)]
    n = err = 0
    errors = {}
    with ThreadPoolExecutor(jobs) as ex:
        for res, stderr in ex.map(run_chunk, chunks):
            if stderr:
                print(stderr, file=sys.stderr)
            for r in res:
                name = r["file"][:-5]
                if CACHE:
                    os.makedirs(CACHE, exist_ok=True)
                    json.dump(r, open(os.path.join(CACHE, r["file"]), "w"))
                if "error" in r:
                    errors[name] = str(r["error"])[:300]
                    err += 1
                    continue
                req = json.loads((SUITE / "cases" / r["file"]).read_text())
                attrs, excl = expected_for(req, r["stats"])
                vals = from_pyfa(r["stats"])
                if any(not x.endswith(".radius") for x in excl.get("data_drift", []) if x.startswith("ship.")):
                    # the hull's own base values differ between Pyfa's data and the SDE: its stats are not comparable
                    excl["values"] = sorted(vals)
                    vals = {}
                exp = {"case": name, "oracle": "pyfa-eos", "effect": {k: man.get(name, {}).get(k) for k in ("effect_id", "effect", "carrier", "how")},
                       "attrs": attrs, "values": {k: v for k, v in sorted(vals.items()) if k in METRICS}, "excluded": excl}
                (SUITE / "expected" / f"{name}.json").write_text(json.dumps(exp, sort_keys=True, default=str, separators=(",", ":")) + "\n")
                n += 1
    (SUITE / "oracle_errors.json").write_text(json.dumps(errors, indent=1, sort_keys=True) + "\n")
    print(f"wrote {n} expected files, {err} oracle errors (effects/oracle_errors.json)")


if __name__ == "__main__":
    main(sys.argv[1:])
