#!/usr/bin/env python3
"""Data drift between Pyfa eve.db (oracle data) and the engines' dataset for the types used in a fit.
usage: drift.py fit.json ... -> {file: [type, name, [(attr, pyfa, dataset)...], effects only-in]}"""
import gzip, json, sqlite3, sys
DS = json.load(gzip.open("/workspace/exct-eve/data/dataset-3569502.json.gz"))
T = DS["types"]
db = sqlite3.connect("/workspace/exct-eve/ref/pyfa/eve.db")
AN = {r[0]: r[1] for r in db.execute("select attributeID, attributeName from dgmattribs")}
_cache = {}


def tdrift(t):
    if t in _cache:
        return _cache[t]
    pa = dict(db.execute("select attributeID, value from dgmtypeattribs where typeID=?", (t,)).fetchall())
    pe = {r[0] for r in db.execute("select effectID from dgmtypeeffects where typeID=?", (t,))}
    d = T.get(str(t))
    if d is None:
        _cache[t] = ("missing in dataset",); return _cache[t]
    if not pa and not pe:
        _cache[t] = ("missing in eve.db",); return _cache[t]
    da = {int(k): v for k, v in d["attrs"].items()}
    for aid, key in ((161, "volume"), (162, "radius"), (4, "mass"), (38, "capacity")):
        if aid not in da and d.get(key) is not None:
            da[aid] = d[key]
    de = {e[0] for e in d["effects"]}
    ad = [(AN.get(a, a), pa.get(a), da.get(a)) for a in sorted(set(pa) | set(da))
          if abs((pa.get(a) or 0) - (da.get(a) or 0)) > 1e-9 * max(1, abs(da.get(a) or 0))]
    _cache[t] = (ad, sorted(pe - de), sorted(de - pe)) if ad or pe ^ de else None
    return _cache[t]


def types(req):
    s = {req["ship"]["type_id"]}
    if req["ship"].get("mode_type_id"):
        s.add(req["ship"]["mode_type_id"])
    for m in req.get("modules", []):
        s.add(m["type_id"]); m.get("charge_type_id") and s.add(m["charge_type_id"])
    for k in ("drones", "fighters", "boosters"):
        s |= {x["type_id"] for x in req.get(k, [])}
    s |= set(req.get("implants", []))
    return s


if __name__ == "__main__":
    out = {}
    for p in sys.argv[1:]:
        r = json.load(open(p))
        out[p.split("/")[-1][:-5]] = {t: [T.get(str(t), {}).get("name"), tdrift(t)] for t in sorted(types(r)) if tdrift(t)}
    print(json.dumps(out, indent=1))
