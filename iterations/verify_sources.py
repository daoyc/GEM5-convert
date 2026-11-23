"""Independently re-build four offline pages with an isolated copy of the zipapp.

Cross-check the JSON actually embedded in HTML against declarations and C++
in the supplied inputs. Only Python's standard library is used.
"""
import argparse
import ast
import hashlib
import json
import operator
import re
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path


HERE = Path(__file__).resolve().parent
ENTRY = "configs/example/xiangshan.py"
CPU = "src/cpu/o3/BaseO3CPU.py"
SCHED = "configs/common/FUScheduler.py"


def require(test, context):
    if not test:
        raise AssertionError(context)


@lru_cache(None)
def text(root, file):
    return (root/file).read_text(encoding="utf-8-sig")


def cls(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)


def fields(scope):
    return {ast.unparse(n.targets[0]):n.value for n in scope.body if isinstance(n,ast.Assign)}


def kwargs(call):
    return {k.arg:k.value for k in call.keywords}


def number(node):
    if isinstance(node,ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node,ast.BinOp) and type(node.op) in (ast.Add,ast.Mult):
        return {ast.Add:operator.add,ast.Mult:operator.mul}[type(node.op)](number(node.left),number(node.right))
    raise AssertionError("Unrecognized source constant: "+ast.dump(node))


def payload(file):
    html = file.read_text(encoding="utf-8-sig")
    match = re.search(r'<script type="application/json" id="embedded">(.*?)</script>', html, re.S)
    require(match, f"{file}: missing offline data")
    return json.loads(match[1])


def source_line(root, ev):
    require(ev and not ev.get("unresolved"),ev)
    lines=text(root,ev["file"]).splitlines()
    require(0 < ev["line"] <= len(lines),ev)
    first=(ev.get("text") or "").splitlines()
    if first:
        require(first[0].strip() in lines[ev["line"]-1],(ev["file"],ev["line"],lines[ev["line"]-1],first[0]))
    return lines[ev["line"]-1]


def verify_scheduler(root, original, ideal, actual):
    build = next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=="build_test_system")
    cpu=fields(build)["TestCPUClass"].id
    chosen=fields(cls(original,cpu))["scheduler"].func.id
    ideal_fn=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=="setkuanglangv1IdealParams")
    if ideal:
        assigned=[n.value.func.id for n in ast.walk(ideal_fn) if isinstance(n,ast.Assign)
                  and ast.unparse(n.targets[0])=="cpu.scheduler"]
        if assigned:
            chosen=assigned[-1]
    require(chosen==actual["className"],(chosen,actual["className"]))
    sched=fields(cls(ast.parse(text(root,SCHED)),chosen))
    default=fields(cls(ast.parse(text(root,"src/cpu/o3/FUPool.py")),"IssueQue"))
    # Resolve only lists actually referenced by this selected class's IQs assignment.
    names=[n.id for n in ast.walk(sched["IQs"]) if isinstance(n,ast.Name)]
    calls=[q for name in names for q in sched[name].elts]
    by_name={q["name"]:q for g in actual["groups"] for q in g["queues"]}
    expected={}
    for call in calls:
        kw=kwargs(call)
        name=ast.literal_eval(kw["name"]);q=by_name[name]
        require(name not in expected,name)
        capacity=number(kw.get("size",default["size"].args[0]))
        inports=number(kw.get("inports",default["inports"].args[0]))
        oports=kw["oports"].elts
        require((q["size"],q["inports"],len(q["issuePorts"]))==(capacity,inports,len(oports)),name)
        source_line(root,q["evidence"])
        for port,p in zip(oports,q["issuePorts"]):
            k=kwargs(port)
            require(p["fu"]==[f.func.id for f in k["fu"].elts],(name,p["fu"]))
            read_ports=[({"IntRD":"整数","FpRD":"浮点"}[r.func.id],*(number(x) for x in r.args)) for r in k["rp"].elts]
            require(read_ports==[(v["bank"],v["port"],v["priority"]) for v in p["reads"]],(name,read_ports))
        expected[name]=dict(entries=capacity,inputs=inports,outputs=len(oports))
    require(set(expected)==set(by_name),list(expected))
    channels=set()
    for channel in sched["specWakeupNetwork"].elts:
        k=kwargs(channel)
        source=ast.literal_eval(k["srcs"]);targets=ast.literal_eval(k["dsts"])
        channels.update((a,b) for a in ([source] if isinstance(source,str) else source)
                        for b in ([targets] if isinstance(targets,str) else targets))
    require(channels=={(r["a"],r["b"]) for r in actual["wakeupRoutes"]},"wakeup matrix")
    return expected,len(channels)


def verify(root, file, ideal):
    model=payload(file)
    require(model["format"]=="core-atlas/2",file)
    view=model["view"];mods={m["id"]:m for m in view["modules"]}
    def rows(uid):
        return {r["label"]:r for r in mods[uid]["coverage"]}
    entry=ast.parse(text(root,ENTRY))
    queues,wakes=verify_scheduler(root,entry,ideal,mods["issue"]["scheduler"])
    base=fields(cls(ast.parse(text(root,CPU)),"BaseO3CPU"))
    fn=next(n for n in entry.body if isinstance(n,ast.FunctionDef) and n.name=="setkuanglangv1IdealParams")
    assignments={ast.unparse(n.targets[0]):n.value for n in ast.walk(fn) if isinstance(n,ast.Assign)}
    # Check the selected object expression in build_test_system, independent of the graph.
    choose=next(n.value for n in ast.walk(entry) if isinstance(n,ast.Assign) and
                ast.unparse(n.targets[0])=="BPClass" and isinstance(n.value,ast.IfExp))
    selected=(choose.body if ideal else choose.orelse).func.id
    require(mods["bpu"]["parameters"]["预测器"]["value"]==selected,selected)
    variant=selected.removeprefix("DecoupledBPUWith").lower()
    cc=text(root,f"src/cpu/pred/{variant}/decoupled_bpred.cc")
    code=re.sub(r'//[^\n]*|/\*.*?\*/',' ',cc,flags=re.S)
    expected=re.findall(r'\bcomponents\.push_back\((\w+)\);',code)
    require(rows("bpu")["预测器注册集合"]["value"]==expected,expected)
    member_ids={p["id"] for p in mods["bpu"]["parts"]}
    require(all("bpu."+key in member_ids for key in expected),member_ids)
    for key,owner,label in [("numROBEntries","commit","ROB 容量"),("LQEntries","lsu","LQ 容量"),
                            ("SQEntries","lsu","SQ 容量"),("SbufferEntries","lsu","Store Buffer 容量")]:
        declared=ast.literal_eval(base[key].args[0]);override=assignments.get("cpu."+key)
        want=ast.literal_eval(override) if ideal and override is not None else declared
        row=rows(owner)[label]
        require(row["value"]==want,(owner,label,want,row["value"]))
        source_line(root,row["evidence"])
    walker=text(root,"src/arch/riscv/pagetable_walker.cc")
    dynamic="const int root_level" in walker
    rootrow=rows("mmu")["遍历根层级"]
    require(rootrow["value"]==("动态 root_level" if dynamic else "SV48/SV39 分支"),rootrow)
    for side in ("itb","dtb"):
        method="mmu."+side+"-walk"
        walk=next(sc for sc in mods["mmu"]["scenarios"] if sc["id"]==method)
        links={e["id"]:e for e in mods["mmu"]["internalEdges"]}
        starts=[links[s["edgeId"]]["evidence"] for s in walk["steps"] if s["a"]=="mmu.l2"]
        require(len(starts)==1,walk)
        ev=starts[0]
        statement="\n".join(text(root,ev["file"]).splitlines()[ev["line"]-1:ev["endLine"]])
        require("walker->start(" in statement and ("root_level" in statement)==dynamic,statement)
        require(any(s["a"]=="mmu.pte" for s in walk["steps"]),walk)
    for sid,needle in [("commit.branch-recovery","controlSquash"),("commit.fault-recovery","trapSquash"),
                       ("commit.retire","retireHead")]:
        scene=next(sc for sc in mods["commit"]["scenarios"] if sc["id"]==sid)
        edge=next(e for e in mods["commit"]["internalEdges"] if e["id"]==scene["steps"][-1]["edgeId"])
        require(needle in source_line(root,edge["evidence"]),(sid,edge))
    resident=rows("ifu")["resident window replay"]
    key="enableFetchResidentWindowReplay"
    if key in base:
        condition=next(n.test for n in ast.walk(fn) if isinstance(n,ast.If) and
                       any(isinstance(s,ast.Assign) and ast.unparse(s.targets[0])=="cpu."+key
                           for e in n.orelse for s in ast.walk(e)))
        require("DecoupledBPUWithFTB" in ast.unparse(condition),condition)
        require("recordFetchResidentWindow" in text(root,"src/cpu/o3/fetch.cc"),root)
        expected_value=ast.literal_eval(assignments["cpu."+key]) if ideal else ast.literal_eval(base[key].args[0])
        require(resident["value"] is expected_value, resident)
    else:
        require("recordFetchResidentWindow" not in text(root,"src/cpu/o3/fetch.cc"),root)
        require(resident["status"]=="缺失",resident)
    source_line(root,resident["evidence"])
    for page in [view,*view["modules"]]:
        edges=page["edges"] if page is view else page["internalEdges"]
        lookup={e["id"]:e for e in edges}
        require(len(edges)==len(lookup),f"duplicate edge in {page['id']}")
        for scene in page["scenarios"]:
            for s in scene["steps"]:
                e=lookup[s["edgeId"]]
                require((s["a"],s["b"])==(e["a"],e["b"]),(scene["id"],s))
                source_line(root,e["evidence"])
    return {"queues":queues,"wakeupRoutes":wakes,"predictor":selected,
            "registrations":expected,"walker":rootrow["value"],"resident":resident["value"],
            "rob":rows("commit")["ROB 容量"]["value"]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pyz",type=Path,default=HERE.parent/"converter"/"GEM5-converter.pyz")
    parser.add_argument("--huanjian-root",type=Path,default=Path("D:/huanjian-project/stage-two/GEM5-1"))
    parser.add_argument("--zenas-root",type=Path,default=HERE.parent/"zenas-dev")
    parser.add_argument("--huanjian-html",type=Path)
    parser.add_argument("--zenas-html",type=Path)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        out=Path(tmp);archive=out/"converter.pyz";shutil.copyfile(args.pyz,archive)
        print("archive SHA-256",hashlib.sha256(archive.read_bytes()).hexdigest())
        results=[]
        for root,published in [(args.huanjian_root,args.huanjian_html),(args.zenas_root,args.zenas_html)]:
            for ideal in (False,True):
                file=out/"result.html"
                file.unlink(missing_ok=True)
                argv=[sys.executable,"-I","-B","-W","ignore",str(archive),str(root.resolve()),"--html",str(file)]
                if ideal:
                    argv.extend(["--set","ideal_kuanglangv1=true","--set","bp_type=DecoupledBPUWithBTB"])
                subprocess.run(argv,cwd=out,check=True,stdout=subprocess.DEVNULL)
                summary=verify(root,file,ideal)
                if not ideal:
                    results.append(summary)
                    if published:
                        clean,final=payload(file),payload(published)
                        for k in ("view","nodes","edges","instances","connections","excerpts","warnings"):
                            require(clean[k]==final[k],f"Published {published} {k} differs from fresh archive output")
                print(root.name,"ideal-BTB" if ideal else "default",json.dumps(summary,ensure_ascii=False,sort_keys=True))
        require(results[0]["queues"]!=results[1]["queues"],"Different issue queues must survive conversion")
        require(results[0]["walker"]!=results[1]["walker"],"Different walker root logic must survive conversion")


if __name__=="__main__":
    main()

