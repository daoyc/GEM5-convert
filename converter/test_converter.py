"""Regression checks for the zenas-dev profile and port identities."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from semantics import runtime
from xiangshan import profile

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("ZENAS_SOURCE", HERE.parents[1] / "model-convert" / "zenas-dev"))


class ConversionTests(unittest.TestCase):
    def test_parallel_ports(self):
        fixture = HERE / "test-config.json"
        nodes, edges, issues = runtime(fixture, {}, {})
        self.assertEqual(len(nodes), 6)
        self.assertFalse(issues)
        expected = json.loads((HERE / "test-trace.json").read_text(encoding="utf-8-sig"))
        ids = {step["edgeId"] for step in expected["steps"]}
        ports = [e for e in edges if e["kind"] == "port"]
        self.assertEqual(len(ports), 2)
        self.assertEqual({e["id"] for e in ports}, ids)
        self.assertEqual({(e["sourcePort"]["index"], e["targetPort"]["index"])
                          for e in ports}, {(0, 1), (1, 0)})
        self.assertEqual(edges, runtime(fixture, {}, {})[1])

    def test_ini_vector_direction(self):
        decl = {"id": "Cache", "lineage": ["Cache"],
                "ports": {"out": "VectorRequestPort", "in": "VectorResponsePort"}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text("[system.cpu.icache]\ntype=Cache\nout=system.l2.in[1] system.l2.in[0]\n"
                            "[system.l2]\ntype=Cache\nin=system.cpu.icache.out[1] system.cpu.icache.out[0]\n")
            _, edges, issues = runtime(path, {"Cache": decl}, {"Cache": ["Cache"]})
        self.assertFalse(issues)
        self.assertEqual(len(edges), 2)
        self.assertTrue(all(e["evidence"]["direction"] == "源码端口推断" for e in edges))
        ports = [e for e in runtime(HERE / "test-config.json", {}, {})[1] if e["kind"] == "port"]
        self.assertEqual({e["id"] for e in edges}, {e["id"] for e in ports})

    def test_architecture_options(self):
        normal = profile(ROOT, {})
        self.assertFalse(normal["warnings"])
        self.assertEqual(len(normal["demo"]), 5)
        options = {"bp_type": "DecoupledBPUWithBTB", "l2_size": "3MB",
                   "ideal_kuanglangv1": True, "no_l3cache": True}
        alternate = profile(ROOT, options)
        modules = {m["id"]: m for m in alternate["modules"]}
        self.assertNotIn("l3", modules)
        self.assertEqual(modules["l2"]["parameters"]["容量"]["value"], "2MB")
        self.assertEqual(modules["bpu"]["parameters"]["预测器"]["value"], options["bp_type"])
        self.assertTrue(any(e["a"] == "l2" and e["b"] == "bus" for e in alternate["edges"]))
        self.assertFalse(alternate["warnings"])
        dynamic = profile(ROOT, {"bp_type": "Other"})
        self.assertTrue(dynamic["warnings"])
        self.assertLess(len(dynamic["demo"]), 5)

    def test_generated_declarations(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "zenas-dev.json"
            subprocess.run([sys.executable, "-B", str(HERE / "convert_model.py"),
                            str(ROOT), "-o", str(output)], check=True, capture_output=True)
            model = json.loads(output.read_text(encoding="utf-8"))
        nodes = {n["id"]: n for n in model["nodes"]}
        base = next(n for n in nodes.values() if n["name"] == "BaseO3CPU")
        cpu = next(n for n in nodes.values() if n["name"] == "RiscvO3CPU")
        self.assertIn(base["id"], cpu["lineage"])
        self.assertIn("DecoupledBPUWithBTB()", base["parameters"]["branchPred"]["value"])
        self.assertTrue(any(e["a"] == base["id"] and e["label"] == "branchPred" and
                            nodes[e["b"]]["name"] == "DecoupledBPUWithBTB" for e in model["edges"]))
        self.assertTrue(any("Parent.l2_shared" in e["label"] for e in model["edges"]))
        self.assertTrue(model["view"]["overrides"])


if __name__ == "__main__":
    unittest.main()


