"""Re-run rounds 4–6 on both source inputs and audit bound evidence and scenarios."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
CONVERTER = HERE.parent / "converter" / "convert_model.py"
ROOTS = [Path(os.environ.get("HUANJIAN_SOURCE", "D:/huanjian-project/stage-two/GEM5-1")),
         Path(os.environ.get("ZENAS_SOURCE", HERE.parent / "zenas-dev"))]


def convert(root, output, n, *options):
    page, data = output / "graph.html", output / "graph.json"
    subprocess.run([sys.executable, "-B", "-W", "ignore", str(CONVERTER), str(root),
                    "--through-round",str(n),"--html",str(page),"-o",str(data),*options],
                   capture_output=True,check=True)
    model = json.loads(data.read_text(encoding="utf-8"))
    assert model["format"] in page.read_text(encoding="utf-8")
    return model


def verify(root, folder, n):
    model = convert(root, folder, n)
    v = model["view"]
    m = {x["id"]:x for x in v["modules"]}
    def rows(uid):
        return {r["label"]:r for r in m[uid].get("coverage",[])}
    for uid in ("bpu","ftq","mmu","commit","issue","lsu"):
        for row in rows(uid).values():
            ev = row["evidence"]
            if not ev.get("line"):
                continue
            source = (root/ev["file"]).read_text(encoding="utf-8-sig").splitlines()
            assert ev["text"].splitlines()[0].strip() in source[ev["line"]-1],ev
        by_id = {e["id"]:e for e in m[uid]["internalEdges"]}
        for scene in m[uid]["scenarios"]:
            for step in scene["steps"]:
                edge = by_id[step["edgeId"]]
                assert (step["a"],step["b"]) == (edge["a"],edge["b"])
    assert rows("bpu")["预测器注册集合"]["value"] == ["uftb","uras","ftb","tage","ras","ittage"]
    for record in rows("bpu").values():
        if record["label"].endswith(" 注册"):
            assert record["condition"] == rows("bpu")["预测器注册集合"]["condition"]
            assert "ideal" not in record["condition"]
    assert rows("ftq")["ftq_size 声明"]["value"] == 128
    assert rows("ftq")["fsq_size 声明"]["value"] == 64
    assert any(s["id"]=="ftq.from-stream" for s in m["ftq"]["scenarios"])
    alt=convert(root,folder,n,"--set","bp_type=DecoupledBPUWithBTB","--set","ideal_kuanglangv1=true")
    sm={x["id"]:x for x in alt["view"]["modules"]}
    sr={r["label"]:r for r in sm["bpu"]["coverage"]}
    assert sr["预测器注册集合"]["value"]==["ubtb","abtb","gshare","btb","tage","ras","ittage","mgsc"]
    assert sm["ftq"]["structureCaption"]=="FTQ 64 项 · FSQ 64 项"
    dynamic=convert(root,folder,n,"--set","bp_type=UnregisteredFoo")
    d=next(x for x in dynamic["view"]["modules"] if x["id"]=="bpu")
    assert next(r for r in d["coverage"] if r["label"]=="预测器注册集合")["status"]=="未知"
    if n>=5:
        dynamic_level=root==ROOTS[0]
        assert rows("mmu")["遍历根层级"]["value"]==("动态 root_level" if dynamic_level else "SV48/SV39 分支")
        for side in ("itb","dtb"):
            assert {f"mmu.{side}-walk",f"mmu.{side}-paging"} <= {s["id"] for s in m["mmu"]["scenarios"]}
        start=rows("mmu")["L2 TLB miss → walker"]["evidence"]
        assert (start["endLine"]>start["line"])==dynamic_level
    if n>=6:
        assert {"commit.retire","commit.branch-recovery","commit.fault-recovery"} <= {s["id"] for s in m["commit"]["scenarios"]}
        assert any(s["id"]=="branch-recovery" for s in v["scenarios"])
        assert rows("commit")["numROBEntries 配置赋值"]["value"]==(384 if root==ROOTS[0] else 256)
        assert ("Load 值预测失配" in rows("commit"))==(root==ROOTS[0])
    print(f"R{n} {root.name}: default, explicit ideal BTB and dynamic BP verified")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round",choices=(4,5,6),type=int,nargs="?")
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        for n in [args.round] if args.round else (4,5,6):
            for root in ROOTS:
                verify(root, Path(tmp), n)


