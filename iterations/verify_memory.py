"""Rebuild and verify the source-backed memory checkpoints against both read-only input trees."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
CONVERTER = HERE.parent / "converter" / "convert_model.py"
INPUTS = {"GEM5-1": Path(os.environ.get("HUANJIAN_SOURCE", "D:/huanjian-project/stage-two/GEM5-1")),
          "zenas-dev": Path(os.environ.get("ZENAS_SOURCE", HERE.parent / "zenas-dev"))}
FIXTURE = HERE / "08-runtime.json"


def convert(root, round_number, dest, *options):
    json_file=dest/"model.json"
    html_file=dest/"model.html"
    subprocess.run([sys.executable, "-W","ignore","-B",str(CONVERTER),str(root),"--through-round",str(round_number),
                    "-o",str(json_file),"--html",str(html_file),*options],check=True,capture_output=True)
    model=json.loads(json_file.read_text(encoding="utf-8"))
    assert "core-atlas/2" in html_file.read_text(encoding="utf-8")
    return model


def rows(model, uid):
    return {r["label"]:r for r in module(model,uid)["coverage"]}


def module(model,uid):
    return next(m for m in model["view"]["modules"] if m["id"]==uid)


def checked_source(root, evidence):
    lines=(root/evidence["file"]).read_text(encoding="utf-8-sig").splitlines()
    text="\n".join(lines[evidence["line"]-1:evidence.get("endLine",evidence["line"])])
    assert evidence["text"].strip() in text, (evidence,text)


def verify7(root, name, dest):
    model=convert(root,7,dest)
    ideal=convert(root,7,dest,"--set","ideal_kuanglangv1=true")
    assert rows(model,"commit")["ROB 容量"]["value"]==160
    assert rows(ideal,"commit")["ROB 容量"]["value"]==(384 if name=="GEM5-1" else 256)
    for test,lq,sq,sb in [(model,80,64,16),(ideal,128,64,48 if name=="GEM5-1" else 24)]:
        for label,value in [("LQ 容量",lq),("SQ 容量",sq),("Store Buffer 容量",sb)]:
            item=rows(test,"lsu")[label]
            assert item["value"]==value
            checked_source(root,item["evidence"])
            checked_source(root,item["defaultEvidence"])
        for uid in ["icache","dcache","l2","l3"]:
            assert any(s["id"]==uid+".coalesced" for s in module(test,uid)["scenarios"])
            checked_source(root,rows(test,uid)["返回端口"]["evidence"])
        for side in ("itb","dtb"):
            chains=rows(test,"l2")[side.upper()+" walker 连接"]["evidenceChain"]
            assert len(chains)==8
            for evidence in chains:
                checked_source(root,evidence)
            assert any(s["id"]=="l2."+side+"-ptw" for s in module(test,"l2")["scenarios"])
        assert any(s["id"]=="mem.backpressure" for s in module(test,"mem")["scenarios"])
        assert "lsu.forward" in {p["id"] for p in module(test,"lsu")["parts"]}
    assert rows(model,"dcache")["MSHR 数量"]["value"]==16
    assert rows(ideal,"dcache")["MSHR 数量"]["value"]==32
    assert rows(ideal,"l3")["缓存容量"]["value"]==("32MB" if name=="GEM5-1" else "16MB")
    timing=rows(model,"mem")["DRAM 时序配置文件"]
    assert (root/timing["value"]).is_file()
    for evidence in timing["evidenceChain"]:
        checked_source(root,evidence)
    no_l3=convert(root,7,dest,"--set","no_l3cache=true","--set","mem_type=SimpleMemory",
                  "--set","xiangshan_ecore=true","--config",str(FIXTURE))
    assert "l3" not in {m["id"] for m in no_l3["view"]["modules"]}
    assert rows(no_l3,"l2")["缓存容量"]["value"]=="4MB"
    assert not module(no_l3,"mem")["scenarios"]
    assert rows(no_l3,"mem")["后端事务时序"]["status"]=="未知"
    assert {n["id"]:n["fields"] for n in no_l3["instances"]}["system.cpu0"]["LQEntries"]==96
    print(f"{name} R7: default / ideal / no-L3 + SimpleMemory + runtime verified")


def verify8(root,name,dest):
    default=convert(root,8,dest)
    ideal=convert(root,8,dest,"--set","ideal_kuanglangv1=true","--set","bp_type=DecoupledBPUWithBTB")
    ftb=convert(root,8,dest,"--set","ideal_kuanglangv1=true","--set","bp_type=DecoupledBPUWithFTB")
    runtime=convert(root,8,dest,"--config",str(FIXTURE))
    for data,enabled in [(default,False),(ideal,True),(ftb,False),(runtime,False)]:
        record=rows(data,"ifu")["resident window replay"]
        checked_source(root,record["evidence"])
        scenes=[s for s in module(data,"ifu")["scenarios"] if s["id"]=="ifu.resident-replay"]
        if name=="zenas-dev":
            assert record["status"]=="缺失" and not scenes
            continue
        assert record["value"] is enabled
        assert len(scenes)==1 and scenes[0]["sourceEnabled"] is enabled
        for step in scenes[0]["steps"]:
            edge=next(e for e in module(data,"ifu")["internalEdges"] if e["id"]==step["edgeId"])
            checked_source(root,edge["evidence"])
        assert {r["key"] for r in scenes[0]["requiresRuntime"]}=={"enableFetchResidentWindowReplay","enableTwoFetch","type"}
    rt={n["id"]:n["fields"] for n in runtime["instances"]}
    assert rt["system.cpu0"]["enableFetchResidentWindowReplay"] is True
    assert rt["system.cpu1"]["enableFetchResidentWindowReplay"] is False
    assert "enableFetchResidentWindowReplay" not in rt["system.cpu2"]
    print(f"{name} R8: default / ideal+BTB / ideal+FTB / three-CPU partial runtime verified")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("round",type=int,choices=(7,8))
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as dest:
        for name,root in INPUTS.items():
            (verify7 if args.round==7 else verify8)(root,name,Path(dest))

