"""Check the historical coverage profiles directly from two independent input trees."""
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

CONVERTER = Path(__file__).resolve().parents[1] / "converter"
sys.path.insert(0, str(CONVERTER))
from backend_structure import add_scheduler_structure
from xiangshan import profile


class BackendRounds(unittest.TestCase):
    def test_active_schedulers(self):
        roots = (Path(os.environ.get("GEM5_FIRST_SOURCE", "D:/huanjian-project/stage-two/GEM5-1")),
                 Path(os.environ.get("ZENAS_SOURCE", CONVERTER.parent / "zenas-dev")))
        for i, root in enumerate(roots):
            with self.subTest(root=root):
                view = profile(root, {}, 3)
                module = next(m for m in view["modules"] if m["id"] == "issue")
                model = module["scheduler"]
                self.assertEqual(model["className"], "HUANJIANV1Scheduler")
                self.assertEqual([g["size"] for g in model["groups"]], ([192,192,160], [72,72,128])[i])
                self.assertEqual([g["inports"] for g in model["groups"]], ([10,10,10], [8,8,8])[i])
                self.assertEqual([g["outputPorts"] for g in model["groups"]], ([11,8,4], [8,7,4])[i])
                self.assertEqual(len(model["registerReadPorts"]["整数"]), (31,9)[i])
                self.assertEqual(model["registerReadPorts"]["浮点"], list(range(12))+[16,17])
                self.assertEqual(model["fuCapabilities"]["IntBRU"]["operations"], ["IntBr"])
                self.assertEqual("FP_MISC" in model["fuCapabilities"], i == 1)
                pairs = {(e["a"],e["b"]) for e in model["wakeupRoutes"]}
                self.assertEqual(len(pairs), (9,92)[i])
                if i:
                    self.assertIn(("intIQ3", "fpIQ0"), pairs)
                    self.assertNotIn(("fpIQ0", "intIQ3"), pairs)
                for g in model["groups"]:
                    for q in g["queues"]:
                        for p in q["issuePorts"]:
                            self.assertTrue(p["complete"])
                            src = p["evidence"]
                            actual = (root/src["file"]).read_text(encoding="utf-8").splitlines()
                            self.assertEqual(src["text"], actual[src["line"] - 1].strip())

    def test_dynamic_input_and_crossbar(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            loc = root / "configs/common/FUScheduler.py"
            loc.parent.mkdir(parents=True)
            loc.write_text(
                "class Selected(Scheduler):\n"
                "    sizes = make_sizes()\n"
                "    active = [IssueQue(name='q1',size=sizes[0],inports=2,oports=[]),\n"
                "              IssueQue(name='q2',size=1+2*3,inports=1,oports=[])]\n"
                "    unused = [IssueQue(name='wrong',size=999)]\n"
                "    IQs = active\n"
                "    xbarWakeup = True\n"
                "    specWakeupNetwork = []\n",encoding="utf-8")
            m = dict(id="issue",parts=[],internalEdges=[],coverage=[],structureCaption="")
            add_scheduler_structure(root, "Selected", m, 3)
            sched = m["scheduler"]
            group, = sched["groups"]
            self.assertEqual([q["name"] for q in group["queues"]],["q1","q2"])
            self.assertEqual([q["size"] for q in group["queues"]],[None,7])
            self.assertIsNone(group["size"])
            self.assertEqual(sched["wakeupPolicy"],"全部 IQ 交叉互连")
            self.assertEqual(len(sched["wakeupRoutes"]),4)


if __name__ == "__main__":
    unittest.main()

