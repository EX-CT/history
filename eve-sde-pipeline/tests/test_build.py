import gzip, json, os, unittest

DIST = os.environ.get("SDEPIPE_DIST", "dist")


def load():
    for fn in os.listdir(DIST):
        if fn.startswith("dataset-") and fn.endswith(".json.gz"):
            return json.load(gzip.open(os.path.join(DIST, fn)))
    raise unittest.SkipTest("no dataset built")


class TestDataset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ds = load()

    def test_rifter(self):
        t = self.ds["types"]["587"]
        self.assertEqual(t["name"], "Rifter")
        self.assertEqual(t["category"], 6)
        self.assertIn("9", t["attrs"])  # structure hp

    def test_skill_effects_have_modifiers(self):
        gunnery = self.ds["types"]["3300"]
        effs = [self.ds["effects"][str(e)] for e, _ in gunnery["effects"]]
        self.assertTrue(any(e["mods"] for e in effs))

    def test_operator_codes(self):
        ops = {m[4] for e in self.ds["effects"].values() for m in e["mods"]}
        self.assertTrue(ops <= {-1, 0, 1, 2, 3, 4, 5, 6, 7, 9}, ops)

    def test_warfare_buffs(self):
        self.assertIn("10", self.ds["dbuffs"])

    def test_revision_and_sections(self):
        from sdepipe import DATASET_REVISION
        self.assertEqual(self.ds["dataset_revision"], DATASET_REVISION)
        for sec in ("market_groups", "meta_groups", "units", "traits", "required_skills", "clone_grades",
                    "environment", "names_i18n", "mutaplasmids"):
            self.assertIn(sec, self.ds)

    def test_chinese_names(self):
        self.assertTrue(self.ds["types"]["587"].get("name_zh") or self.ds["names"]["zh"].get("587"))
        self.assertTrue(self.ds["names_i18n"]["zh"]["groups"])

    def test_traits_and_skills(self):
        self.assertIn("587", self.ds["traits"])          # Rifter has bonus text
        self.assertIn("587", self.ds["required_skills"])  # Minmatar Frigate

    def test_environment(self):
        env = self.ds["environment"]
        kinds = {b["kind"] for b in env["effect_beacons"].values()}
        self.assertTrue({"wormhole", "abyssal", "triglavian", "incursion"} <= kinds, kinds)
        self.assertTrue(any(b["dbuffs"] for b in env["effect_beacons"].values()))


    def test_promoted_patches_r4(self):
        ids = [p["id"] for p in self.ds["patches"]]
        for pid in ("0101-aoe-burst-projectors", "0102-incursion-system-effects", "0103-breacher-pod-damage-control"):
            self.assertIn(pid, ids)
        eff = {e["name"]: e for e in self.ds["effects"].values()}
        self.assertTrue(eff["OffensiveDefensiveReduction"].get("stacking_exempt"))  # Pyfa: no stacking penalty
        for n in ("doomsdayAOEWeb", "doomsdayAOEPaint", "moduleBonusBreacherPodDamageControl"):
            self.assertTrue(eff[n]["mods"], n)
        self.assertFalse(eff["doomsdayAOEWeb"].get("stacking_exempt"))


class TestDiff(unittest.TestCase):
    def test_synthetic(self):
        from sdepipe import diff as dmod
        old = {"sde": {"buildNumber": 1}, "dataset_revision": 3,
               "types": {"1": {"name": "A", "attrs": {"9": 1.0}}, "2": {"name": "B", "attrs": {}}},
               "attributes": {"9": {"name": "hp"}}}
        new = {"sde": {"buildNumber": 2}, "dataset_revision": 3,
               "types": {"1": {"name": "A", "attrs": {"9": 2.0}}, "3": {"name": "C", "attrs": {}}},
               "attributes": {"9": {"name": "hp"}}}
        d = dmod.diff(old, new)
        t = d["sections"]["types"]
        self.assertEqual([i["key"] for i in t["added"]], ["3"])
        self.assertEqual([i["key"] for i in t["removed"]], ["2"])
        self.assertEqual([c["key"] for c in t["changed"]], ["1"])
        md = dmod.markdown(d, new)
        self.assertIn("hp: 1.0 → 2.0", md)


if __name__ == "__main__":
    unittest.main()
