import gzip, json, os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DRIFT = os.path.join(HERE, "..", "docs", "pyfa-data-drift.json")
DIST = os.environ.get("SDEPIPE_DIST", "dist")


class TestDriftFile(unittest.TestCase):
    def test_schema(self):
        d = json.load(open(DRIFT))
        self.assertEqual(d["schema"], 1)
        self.assertIsInstance(d["pyfa"]["client_build"], int)
        ids = [e["id"] for e in d["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        for e in d["entries"]:
            self.assertIn(e["status"], ("expected_difference", "decision_no_pipeline_patch"))
            self.assertTrue(e["reason"])
            self.assertIsInstance(e["metrics"], list)


class TestDriftAgainstDataset(unittest.TestCase):
    """For the SDE build the list was verified on, the dataset must still hold the recorded SDE values."""

    def setUp(self):
        self.drift = json.load(open(DRIFT))
        fns = [f for f in os.listdir(DIST) if f.startswith("dataset-") and f.endswith(".json.gz")] if os.path.isdir(DIST) else []
        if not fns:
            raise unittest.SkipTest("no dataset built")
        self.ds = json.load(gzip.open(os.path.join(DIST, sorted(fns)[-1])))
        if self.ds["sde"]["build"] != self.drift["dataset"]["sde_build"]:
            raise unittest.SkipTest("drift list verified for another SDE build; re-run tools/pyfa_drift.py")

    def test_type_attribute_values(self):
        for e in self.drift["entries"]:
            if e["kind"] != "type_attribute":
                continue
            for t in e["type_ids"]:
                self.assertEqual(self.ds["types"][str(t)]["attrs"].get(str(e["attribute_id"])), e["sde"], (e["id"], t))

    def test_remote_capacitor_impedance(self):
        e = next(x for x in self.drift["entries"] if x["id"] == "remote-capacitor-impedance")
        self.assertEqual(self.ds["effects"]["6184"]["resistance_attr"], 6463)
        for t in e["target_ship_type_ids"]:
            self.assertEqual(self.ds["types"][str(t)]["attrs"].get("6463"), 1.0, t)
        for t in e["impedance_module_type_ids"]:
            self.assertEqual(self.ds["types"][str(t)]["attrs"].get("6464"), -99.9999, t)
