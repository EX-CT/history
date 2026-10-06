#!/usr/bin/env python3
"""Generate patches/proposed/*.json: modifier patches for effects CCP ships WITHOUT modifierInfo and that the
EXCT engines do not special-case (the `gap` rows of reports/pyfa-effects-coverage.md).

Behaviour is described from Pyfa's eos/effects.py (LGPL/GPL); no Pyfa code is copied - only which attribute is
modified by which source attribute, which is game data. Proposed patches are NOT applied by default
(`python -m sdepipe build --with-proposed` applies them) because they change fit results versus the current
bench parity and need engine review first (projected domain / range factor / stacking semantics).

Modifier tuple: [func, domain, modifiedAttr, modifyingAttr, operation, groupID|skillTypeID]
func: 0 Item, 1 Location, 2 LocationGroup, 3 LocationRequiredSkill, 4 OwnerRequiredSkill
domain: 0 item, 1 ship, 2 char, 5 targetID ; op 6 = PostPercent
"""
import gzip, json, os, sys

ds = json.load(gzip.open(sys.argv[1]))
# 0101-0103 were reviewed by engine owner A and promoted in dataset revision 4: they now live in patches/
# (applied by default) and keep their review notes there. This script regenerates only the modifier lists.
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "patches")
A = {a["name"]: int(k) for k, a in ds["attributes"].items()}
E = {e["name"]: int(k) for k, e in ds["effects"].items()}
T = {t["name"]: int(k) for k, t in ds["types"].items()}
G = {g["name"]: int(k) for k, g in ds["groups"].items()}
GUNNERY, MLO = T["Gunnery"], T["Missile Launcher Operation"]
PP = 6
DMG = ("em", "thermal", "kinetic", "explosive")


def disrupt_mods(dom):
    m = [[4, dom, A[t], A[s], PP, MLO] for s, t in (("aoeCloudSizeBonus", "aoeCloudSize"), ("aoeVelocityBonus", "aoeVelocity"),
                                                  ("missileVelocityBonus", "maxVelocity"), ("explosionDelayBonus", "explosionDelay"))]
    m += [[3, dom, A[t], A[s], PP, GUNNERY] for s, t in (("trackingSpeedBonus", "trackingSpeed"), ("maxRangeBonus", "maxRange"),
                                                       ("falloffBonus", "falloff"))]
    return m


PATCHES = [
    ("0101-aoe-burst-projectors", "Burst projectors / Standup burst projectors (doomsdayAOE*) and Standup weapon "
     "disruptor. Pyfa: when projected onto a ship that does not have disallowOffensiveModifiers, PostPercent the "
     "target ship attribute by the module attribute (web: maxVelocity by speedFactor; paint: signatureRadius by "
     "signatureRadiusBonus; damp: maxTargetRange by maxTargetRangeBonus and scanResolution by scanResolutionBonus; "
     "track/weapon disruption: missile charges (Missile Launcher Operation) aoeCloudSize/aoeVelocity/maxVelocity/"
     "explosionDelay and Gunnery turrets trackingSpeed/maxRange/falloff by the matching *Bonus attribute), all "
     "stacking-penalised. Standup Weapon Disruptor additionally scales by the optimal/falloff range factor, which the "
     "engine must apply (as for ordinary weapon disruptors). ECM and neut bursts (doomsdayAOEECM/Neut) are not "
     "modifiers (jam chance / cap drain stats) and stay engine-side.",
     {E["doomsdayAOEWeb"]: [[0, 5, A["maxVelocity"], A["speedFactor"], PP, 0]],
      E["doomsdayAOEPaint"]: [[0, 5, A["signatureRadius"], A["signatureRadiusBonus"], PP, 0]],
      E["doomsdayAOEDamp"]: [[0, 5, A["maxTargetRange"], A["maxTargetRangeBonus"], PP, 0],
                             [0, 5, A["scanResolution"], A["scanResolutionBonus"], PP, 0]],
      E["doomsdayAOETrack"]: disrupt_mods(5),
      E["structureModuleEffectWeaponDisruption"]: disrupt_mods(5)}),
    ("0102-incursion-system-effects", "OffensiveDefensiveReduction (Sansha/Drifter incursion system-effect beacons). "
     "Pyfa: PostPercent by systemEffectDamageReduction on missile charges' em/thermal/kinetic/explosive damage, on "
     "Smart Bomb modules' damage, on drones' and Gunnery turrets' damageMultiplier; and PostPercent the ship's "
     "armor/shield <type>DamageResonance by armor/shield<Type>DamageResistanceBonus. Drones are modelled here as "
     "OwnerRequiredSkill(Drones) on the character domain - engines should confirm drone scoping.",
     {E["OffensiveDefensiveReduction"]:
      [[4, 2, A[f"{d}Damage"], A["systemEffectDamageReduction"], PP, MLO] for d in DMG]
      + [[2, 1, A[f"{d}Damage"], A["systemEffectDamageReduction"], PP, G["Smart Bomb"]] for d in DMG]
      + [[3, 1, A["damageMultiplier"], A["systemEffectDamageReduction"], PP, GUNNERY],
         [4, 2, A["damageMultiplier"], A["systemEffectDamageReduction"], PP, T["Drones"]]]
      + [[0, 1, A[f"{l}{d.capitalize()}DamageResonance"], A[f"{l}{d.capitalize()}DamageResistanceBonus"], PP, 0]
         for l in ("armor", "shield") for d in DMG]}),
    ("0103-breacher-pod-damage-control", "moduleBonusBreacherPodDamageControl (Breach Control). Pyfa: while active, "
     "PostPercent ship breacherPodDamageResistance by breacherPodActivatedDamageReceivedPercentage.",
     {E["moduleBonusBreacherPodDamageControl"]:
      [[0, 1, A["breacherPodDamageResistance"], A["breacherPodActivatedDamageReceivedPercentage"], PP, 0]]}),
]

os.makedirs(out, exist_ok=True)
for pid, desc, effs in PATCHES:
    path = os.path.join(out, pid + ".json")
    prev = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    effects = {str(k): {"mods": v} for k, v in effs.items()}
    if pid.startswith("0102"):  # Pyfa: incursion system effects are not stacking-penalised
        for e in effects.values():
            e["stacking_exempt"] = True
    body = {"id": pid, "status": prev.get("status", "proposed"), "description": prev.get("description", desc),
            "reference": "Pyfa eos/effects.py (behaviour only)", "set": {"effects": effects}}
    if "applied_in_revision" in prev:
        body["applied_in_revision"] = prev["applied_in_revision"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(pid, sum(len(v) for v in effs.values()), "mods")
