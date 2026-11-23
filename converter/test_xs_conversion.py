"""Validate the KMHV3 architecture generated from the supplied checkout."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SOURCE = Path(os.environ.get("XS_GEM5_SOURCE", HERE.parent / "GEM5"))
MODULES = set("bpu ftq ifu icache decode rename dispatch iew commit lsu mmu dcache l2 llc fabric mem".split())


class Kmhv3ConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name)
        model_file = cls.work / "result.json"
        subprocess.run(
            [sys.executable, "-B", "-W", "ignore::SyntaxWarning", str(HERE / "convert_model.py"),
             str(SOURCE), "-o", str(model_file), "--html", str(cls.work / "result.html")],
            check=True, cwd=cls.work, capture_output=True, text=True, encoding="utf-8",
        )
        cls.model = json.loads(model_file.read_text(encoding="utf-8"))
        cls.profile = cls.model["architecture"]

    def test_reference_inventory_and_paths(self):
        data = self.profile
        self.assertFalse(data["warnings"], data["warnings"])
        self.assertEqual(set(data["modules"]), MODULES)
        overview = data["overview"]
        self.assertEqual({n["id"] for n in overview["nodes"]}, MODULES)
        self.assertEqual(len(overview["edges"]), 21)
        self.assertEqual([(e["a"], e["b"]) for e in overview["edges"] if e.get("legacy")],
                         [("decode", "iew")])
        counts = [0, 0, 0, 0]
        for graph in [overview, *data["modules"].values()]:
            with self.subTest(graph=graph["id"]):
                ids = {n["id"] for n in graph["nodes"]}
                edges = {(e["a"], e["b"]) for e in graph["edges"]}
                self.assertEqual(len(ids), len(graph["nodes"]))
                for a, b in edges:
                    self.assertIn(a, ids)
                    self.assertIn(b, ids)
                for entity in [*graph["nodes"], *graph["edges"], *graph["streams"]]:
                    file, number = entity["path"].rsplit(":", 1)
                    relative = file.removeprefix("GEM5/")
                    self.assertIn(relative, data["sources"])
                    line = int(number)
                    self.assertGreater(line, 0)
                    self.assertLessEqual(line, len(data["sources"][relative].splitlines()))
                edge_ids = {e["id"] for e in graph["edges"]}
                self.assertEqual(len(edge_ids), len(graph["edges"]))
                for scene in graph["streams"]:
                    for step in scene["steps"]:
                        self.assertIn(step["edgeId"], edge_ids)
                        a, b = step["a"], step["b"]
                        self.assertTrue((a, b) in edges or (b, a) in edges, (scene["name"], a, b))
                totals = (len(ids), len(graph["edges"]), len(graph["streams"]),
                          sum(len(s["steps"]) for s in graph["streams"]))
                counts = [total + n for total, n in zip(counts, totals)]
        self.assertEqual(counts, [112, 126, 42, 188])
        for relative, snapshot in data["sources"].items():
            self.assertEqual(snapshot.splitlines(), (SOURCE / relative).read_text(encoding="utf-8-sig").splitlines(),
                             relative)

    def test_source_parameter_follows_changed_configuration(self):
        from xs_parameters import ENTRY, source_parameters
        directory = self.work / "changed-parameters"
        file = directory / ENTRY
        file.parent.mkdir(parents=True)
        text = (SOURCE / ENTRY).read_text(encoding="utf-8")
        self.assertIn("cpu.fetchWidth = 32", text)
        file.write_text(text.replace("cpu.fetchWidth = 32", "cpu.fetchWidth = 37"), encoding="utf-8")
        changed = source_parameters(directory, {})["cpu.fetchWidth"]
        self.assertEqual(changed["value"], 37)
        line = int(changed["path"].rsplit(":", 1)[1])
        self.assertIn("cpu.fetchWidth = 37", file.read_text(encoding="utf-8").splitlines()[line-1])

    def test_changed_checkout_reports_missing_evidence(self):
        from xs_profile import build_profile
        source_copy = self.work / "edited-checkout"
        for relative in self.profile["sources"]:
            dest = source_copy / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / relative, dest)
        source_file = "src/cpu/o3/fetch.cc"
        original = self.profile["sources"][source_file]
        # Preserve the line count so a range check alone cannot pass.
        (source_copy / source_file).write_text("// no implementation\n" * len(original.splitlines()), encoding="utf-8")
        changed = build_profile(source_copy)
        self.assertTrue(any(source_file in str(w) for w in changed["warnings"]))
        self.assertTrue(changed["overview"]["excludedSources"])
        for graph in [changed["overview"], *changed["modules"].values()]:
            for item in [*graph["nodes"], *graph["edges"], *graph["streams"]]:
                self.assertFalse(item.get("path", "").startswith("GEM5/" + source_file + ":"),
                                 (graph["id"], item))


if __name__ == "__main__":
    unittest.main()



