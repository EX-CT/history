# 05 — Stateless API schema (v1)

> 中文：一个请求（技能、配置、状态、弹药、突变、植入体、增效剂、无人机、舰载机、舰队加成、投射、环境、目标、伤害模型、选项）
> → 一个确定性的结果。CLI、HTTP、WASM、MCP 全部使用同一个 JSON 契约。JSON Schema 文件见 `schema/`。

## Transport

| Surface | Call |
|---|---|
| CLI | `eve-dogma calc --dataset dataset.json.gz < request.json > stats.json` (also `--batch` JSONL in/out) |
| HTTP | `POST /v1/calc` (body = request) → stats; `POST /v1/batch`; `GET /v1/types?q=`; `GET /v1/meta` |
| WASM | `calc(requestJson) -> statsJson` |
| MCP | `compute_fit` tool (see 06) |

Determinism: same `(dataset sha256, request)` → byte-identical response (keys ordered, no timestamps).
Response `meta` echoes `engine_version`, `schema_version`, `sde_build`, `dataset_sha256`, `request_hash`.

## Request (`schema/fit-request.schema.json`)

```jsonc
{
  "schema_version": 1,
  "ship": { "type_id": 587, "mode_type_id": null },          // T3D mode, optional
  "character": {
    "skills": { "default_level": 5, "levels": { "3300": 4 } }, // default_level fills every skill (Pyfa "All 5")
    "security_status": 0.0
  },
  "modules": [
    { "type_id": 2873, "slot": "high", "state": "active", "charge_type_id": 12608 },
    { "type_id": 47732, "slot": "low", "state": "online",
      "mutation": { "base_type_id": 2048, "mutaplasmid_type_id": 47408, "attributes": { "974": 1.12 } } },
    { "type_id": 3841, "slot": "mid", "state": "overheated", "spool": { "type": "spool_scale", "amount": 1.0 } }
  ],
  "drones":   [ { "type_id": 2486, "quantity": 5, "active": 5 } ],
  "fighters": [ { "type_id": 40556, "quantity": 9, "active": true, "abilities": [6431] } ],
  "implants": [ 13209 ],
  "boosters": [ { "type_id": 28672, "side_effects": [] } ],
  "cargo":    [ { "type_id": 12608, "quantity": 1000 } ],
  "fleet":    { "buffs": [ { "buff_id": 10, "value": -25.875 } ], "booster_fits": [ /* FitRequest without fleet */ ] },
  "projected": [
    { "kind": "module", "module": { "type_id": 526, "state": "active" }, "amount": 2, "distance_m": 9000 },
    { "kind": "fit", "fit": { /* FitRequest */ }, "amount": 1, "distance_m": 20000 }
  ],
  "environment": { "effect_type_ids": [ 30574 ], "system_security": "nullsec" },
  "damage_pattern": { "em": 25, "thermal": 25, "kinetic": 25, "explosive": 25 },
  "target_profile": { "em": 0.0, "thermal": 0.0, "kinetic": 0.0, "explosive": 0.0,
                      "signature_radius": null, "max_velocity": null, "radius": null },
  "overrides": [ { "type_id": 2873, "attribute_id": 51, "value": 1000 } ],
  "options": {
    "factor_reload": false,
    "default_spool": { "type": "spool_scale", "amount": 1.0 },
    "rah": "adapt",                 // adapt | disable ("disable" = unadapted RAH)
    "include_attributes": "none",   // none | ship | all
    "sources": false,
    "validate": true,
    "cap_sim": { "reload": false, "stagger": false, "max_time_s": 86400 }
  }
}
```

Slots: `high|mid|low|rig|subsystem|service`. States: `offline|online|active|overheated`.
Spool types (Pyfa `SpoolType`): `spool_scale|cycle_scale|time|cycles`.

## Response (`schema/fit-stats.schema.json`)

```jsonc
{
  "meta": { "schema_version": 1, "engine": "eve-dogma-rs 0.1.0", "sde_build": 3569502, "dataset_sha256": "…" },
  "ship": { "type_id": 587, "name": "Rifter", "group": "Frigate" },
  "resources": { "cpu": {"used": 120.5, "total": 162.5}, "power": {...}, "calibration": {...},
                 "drone_bandwidth": {...}, "drone_bay": {...}, "fighter_bay": {...}, "cargo": {...},
                 "slots": {"high": {"used": 3, "total": 4}, "mid": ..., "low": ..., "rig": ..., "subsystem": ..., "service": ...},
                 "hardpoints": {"turret": {"used": 3, "total": 3}, "launcher": {"used": 1, "total": 2}},
                 "fighter_tubes": {"light": ..., "support": ..., "heavy": ...} },
  "offense": {
    "weapons": [ { "index": 0, "type_id": 2873, "kind": "turret|missile|smartbomb|bomb|vorton|breacher|doomsday|other",
                   "volley": {"em":0,"thermal":0,"kinetic":43.2,"explosive":12.1,"total":55.3},
                   "dps": {...}, "cycle_time_ms": 3420, "optimal_m": 1200, "falloff_m": 5000, "tracking": 0.4,
                   "explosion_radius": null, "explosion_velocity": null, "spool": null } ],
    "drones":  [ { "type_id": 2486, "count": 5, "volley": {...}, "dps": {...} } ],
    "fighters":[ ... ],
    "total": { "weapon_dps": ..., "drone_dps": ..., "fighter_dps": ..., "dps": {...}, "volley": {...} },
    "vs_target_profile": { "dps": 123.4, "volley": 50.1 }
  },
  "defense": {
    "hp": {"shield": 450, "armor": 380, "hull": 350, "total": 1180},
    "resonance": {"shield": {"em":1,"thermal":0.8,"kinetic":0.6,"explosive":0.5}, "armor": {...}, "hull": {...}},
    "ehp": {"shield": ..., "armor": ..., "hull": ..., "total": ...},
    "tank": {"raw": {"passive_shield": 2.1, "shield_repair": 0, "armor_repair": 30.5, "armor_repair_pre_spool": .., "armor_repair_full_spool": .., "hull_repair": 0},
             "effective": {...}, "sustainable": {...}, "effective_sustainable": {...}}
  },
  "capacitor": { "capacity": 312.5, "recharge_time_s": 140.6, "peak_recharge_gj_s": 5.55, "use_gj_s": 4.1, "delta_gj_s": 1.45,
                 "stable": true, "stable_percent": 48.1, "depletes_in_s": null, "eve_stable_percent": 47.9 },
  "navigation": { "max_velocity": 1650, "align_time_s": 3.4, "mass": 1.3e6, "agility": 3.2, "signature_radius": 120,
                  "warp_speed_au_s": 5.0, "max_warp_distance_au": 40.1, "warp_scramble_status": 0 },
  "targeting": { "max_targets": 4, "max_range_m": 22500, "scan_resolution": 660, "sensor_strength": 9.6,
                 "sensor_type": "ladar", "probe_size": 12.5, "lock_time_s": {"frigate_35m": 2.3, "cruiser_150m": 1.3, "battleship_400m": 1.0},
                 "jam_chance": 0 },
  "drones": { "active": 5, "max_active": 5, "control_range_m": 60000 },
  "mining": { "yield_m3_s": 0, "drain_m3_s": 0 },
  "remote": { "shield_rps": 0, "armor_rps": 0, "hull_rps": 0, "cap_gj_s": 0, "neut_gj_s": 0 },
  "modules": [ { "index": 0, "type_id": 2873, "state": "active", "cap_use_gj_s": 0.3, "attributes": {"51": 3420} } ],
  "violations": [ { "code": "CPU_OVERLOAD", "message": "…", "module_index": null } ],
  "attributes": { "ship": { "9": 350.0 } }   // when include_attributes != none
}
```

Errors: `{"error": {"code": "UNKNOWN_TYPE", "message": "...", "path": "/modules/3/type_id"}}`, exit code 2.

### Composability (no hidden state)

Projected/command *fits* are nested FitRequests and computed recursively inside a single call; depth limited to 2
(as Pyfa: projected fits are not projected-onto again). Engine caches nothing between calls (a host may memoise by
`request_hash`).
