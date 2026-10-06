"""Structure checks for presets/presets.json (and presets-pyfa.json when present)."""
import json, os, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRESETS = os.environ.get("SDEPIPE_PRESETS", os.path.join(HERE, "presets"))


def load(name):
    p = os.path.join(PRESETS, name)
    if not os.path.exists(p):
        raise unittest.SkipTest(f"{p} not generated")
    return json.load(open(p, encoding="utf-8"))


class TestPresets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = load("presets.json")

    def sections(self):
        for k in ("damage_profiles", "target_profiles"):
            for sub, sec in self.p[k].items():
                yield f"{k}.{sub}", sec
        for k in ("npc_damage_types", "implant_sets", "character_skill_presets", "search_aliases"):
            yield k, self.p[k]

    def test_every_section_has_provenance_and_license(self):
        for name, sec in self.sections():
            self.assertIn("provenance", sec, name)
            self.assertIn("license", sec["provenance"], name)
            self.assertNotIn("pyfa", json.dumps(sec["provenance"]).lower(), name)  # no Pyfa data in this file

    def test_ratios_sum_to_one(self):
        for sub in ("generic", "ammo", "npc"):
            for x in self.p["damage_profiles"][sub]["items"]:
                self.assertAlmostEqual(sum(x["ratio"]), 1.0, places=4, msg=x["id"])

    def test_unique_ids(self):
        for name, sec in self.sections():
            items = sec.get("items")
            if isinstance(items, list) and items and "id" in items[0]:
                ids = [x["id"] for x in items]
                self.assertEqual(len(ids), len(set(ids)), name)

    def test_known_values(self):
        npc = {x["faction"]: x for x in self.p["npc_damage_types"]["factions"]}
        self.assertEqual(npc["Blood Raider Covenant"]["primary"], "em")
        self.assertEqual(npc["Guristas Pirates"]["primary"], "kinetic")
        self.assertEqual(npc["Angel Cartel"]["primary"], "explosive")
        sets = {x["id"]: x for x in self.p["implant_sets"]["items"]}
        self.assertEqual(sets["crystal.high-grade"]["slots"], [1, 2, 3, 4, 5, 6])
        self.assertEqual(sets["wedge.low-grade"]["set_attribute"], "implantSetHackingVirusCoherenceOmegaSetBonus")
        for x in sets.values():  # only genuine set-bonus attributes, no per-slot modifiers or FAKE display copies
            self.assertFalse(x["set_attribute"].endswith("Modifier") or x["set_attribute"].upper().endswith("FAKE"), x["id"])
        sk = {x["id"]: x for x in self.p["character_skill_presets"]["items"]}
        self.assertEqual(sk["all5"]["default_level"], 5)
        self.assertGreater(len(self.p["character_skill_presets"]["published_skills"]), 400)
        al = {x["alias"]: x for x in self.p["search_aliases"]["items"]}
        self.assertIn("mwd", al)

    def test_pyfa_file_is_marked_copyleft(self):
        try:
            q = load("presets-pyfa.json")
        except unittest.SkipTest:
            return
        for k in ("damage_patterns", "target_profiles", "jargon"):
            self.assertIn(q[k]["license"]["id"], ("LGPL-2.1-or-later", "GPL-3.0-or-later"))
            self.assertTrue(q[k]["provenance"]["commit"])


if __name__ == "__main__":
    unittest.main()
