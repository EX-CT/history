#!/usr/bin/env python3
"""Compare Pyfa's bundled game data (eve.db) with a pipeline dataset and list differences.

usage: pyfa_drift.py --eve-db PATH/eve.db --dataset dataset-<build>.json.gz [--json]
Reports: per-type attribute value diffs (types present in both), attributes only on one side for shared types,
and effects whose resistance attribute differs. Entries already in docs/pyfa-data-drift.json are marked known."""
import argparse, gzip, json, math, os, sqlite3, collections

HERE = os.path.dirname(os.path.abspath(__file__))
KNOWN = os.path.join(HERE, "..", "docs", "pyfa-data-drift.json")


def known_keys():
    k = set()
    for e in json.load(open(KNOWN))["entries"]:
        for t in e.get("type_ids", []):
            k.add((t, e.get("attribute_id")))
        for t in e.get("target_ship_type_ids", []):
            for a in e.get("attribute_ids", []):
                k.add((t, a))
        for t in e.get("impedance_module_type_ids", []):
            for a in e.get("attribute_ids", []):
                k.add((t, a))
    return k


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eve-db", required=True)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    ds = json.load(gzip.open(a.dataset))
    db = sqlite3.connect(a.eve_db)
    meta = dict(db.execute("select field_name, field_value from metadata"))
    py = collections.defaultdict(dict)
    for t, at, v in db.execute("select typeID, attributeID, value from dgmtypeattribs"):
        py[t][at] = v
    known = known_keys()
    diffs, only = [], collections.Counter()
    for ts, x in ds["types"].items():
        t = int(ts)
        if t not in py:
            continue
        d = {int(k): v for k, v in x["attrs"].items()}
        p = py[t]
        for at in set(d) & set(p):
            if not math.isclose(d[at], p[at], rel_tol=1e-9, abs_tol=1e-12):
                diffs.append({"type_id": t, "name": x.get("name"), "attribute_id": at, "pyfa": p[at], "dataset": d[at],
                              "known": (t, at) in known})
        for at in set(d) - set(p):
            only[("dataset", at, (t, at) in known)] += 1
        for at in set(p) - set(d) - {4, 38, 161, 162}:
            only[("pyfa", at, (t, at) in known)] += 1
    res = []
    for eid, r in db.execute("select effectID, resistanceID from dgmeffects"):
        e = ds["effects"].get(str(eid))
        if e is not None and (e.get("resistance_attr") or None) != (r or None):
            res.append({"effect_id": eid, "name": e.get("name"), "pyfa": r, "dataset": e.get("resistance_attr")})
    out = {"pyfa_client_build": meta.get("client_build"), "sde_build": ds.get("sde", {}).get("build"),
           "attribute_diffs": diffs,
           "attribute_only": [{"side": s, "attribute_id": at, "known": k, "types": n} for (s, at, k), n in sorted(only.items())],
           "effect_resistance_diffs": res}
    if a.json:
        print(json.dumps(out, indent=1))
        return
    print(f"Pyfa client build {out['pyfa_client_build']} vs dataset SDE {out['sde_build']}")
    for x in diffs:
        print(f"  attr  {x['type_id']:>6} {x['name']!r:28} {x['attribute_id']:>5}: pyfa {x['pyfa']} dataset {x['dataset']}"
              f"{'  (known)' if x['known'] else '  NEW'}")
    for x in out["attribute_only"]:
        print(f"  only-{x['side']:7} attr {x['attribute_id']:>5} on {x['types']} shared types{'  (known)' if x['known'] else ''}")
    for x in res:
        print(f"  effect {x['effect_id']} {x['name']}: resistance pyfa {x['pyfa']} dataset {x['dataset']}")


if __name__ == "__main__":
    main()
