#!/usr/bin/env python3
"""docs/18 exercise X2: add two synthetic items to dataset-3569502 (output: dataset-3569502-fvj.json.gz).
X2a = data-only modifier effect (has modifierInfo); X2b = hand-written effect (no modifierInfo, engine code needed)."""
import gzip, json, sys, copy
src, dst = sys.argv[1], sys.argv[2]
d = json.load(gzip.open(src))
A, E, T = d["attributes"], d["effects"], d["types"]
base_attr = dict(default=0.0, display=None, high_is_good=True, max_attr=None, min_attr=None,
                 published=False, stackable=False, unit=None)
A["990001"] = dict(base_attr, name="fvjExerciseVelocityBonus")
A["990002"] = dict(base_attr, name="fvjExerciseSigBonus", high_is_good=False)
eff = dict(discharge_attr=None, duration_attr=None, falloff_attr=None, fitting_usage_chance_attr=None,
           is_assistance=False, is_offensive=False, range_attr=None, resistance_attr=None, tracking_attr=None)
# [func, domain, target attr, source attr, op, filter]: ItemModifier, shipID, maxVelocity(37), PostPercent(6)
E["990001"] = dict(eff, category=4, name="fvjExerciseVelocityBonusOnline", mods=[[0, 1, 37, 990001, 6, 0]])
E["990002"] = dict(eff, category=4, name="fvjExerciseSigReductionOnline", mods=[])  # hand-written
oi = T["1244"]  # Overdrive Injector System I (low slot)
for tid, name, aid, val, eid in (("990001", "FVJ Exercise Injector", "990001", 10.0, 990001),
                                 ("990002", "FVJ Exercise Sig Suppressor", "990002", -5.0, 990002)):
    t = copy.deepcopy(oi)
    t["name"] = name
    t["market_group"] = None
    t["attrs"] = {k: v for k, v in oi["attrs"].items() if k != "1076"}
    t["attrs"][aid] = val
    t["effects"] = [[11, 0], [16, 0], [eid, 0]]
    T[tid] = t
with gzip.open(dst, "wt") as f:
    json.dump(d, f, separators=(",", ":"), sort_keys=True)
