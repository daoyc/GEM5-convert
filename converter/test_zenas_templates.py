"""Tests for direction-aware replay binding against actual XS component evidence."""
import os
import tempfile
import unittest
from pathlib import Path

from xiangshan import profile
from zenas_details import bind_scenarios


ROOT = Path(os.environ.get("ZENAS_SOURCE", Path(__file__).resolve().parent.parent / "zenas-dev"))


class TemplateBindingTests(unittest.TestCase):
    def setUp(self):
        self.parts = [{"id": key} for key in ("requester", "cache", "memory")]
        self.edges = [dict(id="e0", a="requester", b="cache", label="read"),
                      dict(id="e1", a="cache", b="memory", label="miss")]
        self.recipes = [("miss", "读缺失", "requester cache memory")]

    def test_ordered_directed_binding(self):
        scene, = bind_scenarios(self.parts, self.edges, self.recipes)
        self.assertEqual([s["edgeId"] for s in scene["steps"]], ["e0", "e1"])

    def test_require_every_part_and_directed_edge(self):
        def rejected(parts, edges):
            self.assertEqual(bind_scenarios(parts, edges, self.recipes), [])
        rejected(self.parts[:-1], self.edges)
        rejected(self.parts, self.edges[:-1])
        rejected(self.parts, [self.edges[0], dict(self.edges[1], a="memory", b="cache")])
        rejected(self.parts, self.edges + [dict(self.edges[1], id="parallel")])
        rejected(self.parts, [self.edges[0], dict(self.edges[1], evidence={"unresolved": True})])


@unittest.skipUnless((ROOT / "configs/example/xiangshan.py").is_file(), "requires zenas-dev")
class ZenasProfileTests(unittest.TestCase):
    def test_all_default_views_bind_concrete_edges(self):
        model = profile(ROOT, {})
        self.assertEqual(model["warnings"], [])
        self.assertEqual(len(model["modules"]), 15)
        for page, edges, parts in [(model, model["edges"], model["modules"]), *[
                (m, m["internalEdges"], m["parts"]) for m in model["modules"]]]:
            with self.subTest(page=page["id"]):
                ids = {p["id"] for p in parts}
                links = {e["id"]: (e["a"], e["b"]) for e in edges}
                self.assertTrue(page["scenarios"])
                self.assertGreaterEqual(len(ids), 4)
                self.assertTrue(all(a in ids and b in ids for a,b in links.values()))
                for s in page["scenarios"]:
                    for t in s["steps"]:
                        self.assertEqual(links[t["edgeId"]], (t["a"], t["b"]))

    def test_no_l3(self):
        model = profile(ROOT, {"no_l3cache": True})
        self.assertNotIn("l3", {m["id"] for m in model["modules"]})
        scenes = {scene["id"]: scene for scene in model["scenarios"]}
        self.assertNotIn("miss", scenes)
        self.assertIn(("l2", "bus"), [(s["a"], s["b"]) for s in scenes["direct-miss"]["steps"]])
        for m in model["modules"]:
            self.assertFalse(any(p.get("target") == "l3" for p in m["parts"]))

    def test_absent_owner_does_not_leak_into_overview(self):
        # Preserve all source used by this profile except the L3 instantiation.
        baseline=profile(ROOT,{})
        files=set()
        def visit(obj):
            if isinstance(obj,dict):
                if "file" in obj: files.add(obj["file"])
                for v in obj.values(): visit(v)
            elif isinstance(obj,(tuple,list)):
                for v in obj: visit(v)
        visit(baseline)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in files:
                dest=root/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                text=(ROOT/name).read_text(encoding="utf8")
                if name=="configs/common/CacheConfig.py":
                    text=text.replace("system.l3 = L3Cache","system.unmapped = L3Cache")
                dest.write_text(text,encoding="utf8")
            model=profile(root,{})
            self.assertTrue(model["warnings"])
            self.assertNotIn("l3", {m["id"] for m in model["modules"]})
            self.assertTrue(all("l3" not in (e["a"],e["b"]) for e in model["edges"]))
            self.assertNotIn("miss",{s["id"] for s in model["scenarios"]})
            l2 = next(m for m in model["modules"] if m["id"]=="l2")
            self.assertFalse(any(p.get("target")=="bus" for p in l2["parts"]))


if __name__ == "__main__":
    unittest.main()
