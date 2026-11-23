"""Replay the cumulative conversions. Round 10 uses only the zipapp in each working directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent
CONVERTER=PROJECT/"converter"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def payload(page):
    match=re.search(r'<script type="application/json" id="embedded">(.+?)</script>', page, flags=re.S)
    if not match:
        raise ValueError("missing embedded model")
    return json.loads(match[1])

def stats(model):
    view=model["view"]
    output={"declarations":len(model["nodes"]), "declarationRelations":len(model["edges"]),
            "warnings":view["warnings"], "modules":{}}
    for graph in [view,*view["modules"]]:
        is_overview=graph is view
        nodes=graph["modules" if is_overview else "parts"]
        edges=graph["edges" if is_overview else "internalEdges"]
        ids={n["id"] for n in nodes}
        edge_ids={e["id"]:(e["a"],e["b"]) for e in edges}
        assert len(ids)==len(nodes) and len(edge_ids)==len(edges),graph["id"]
        assert all(a in ids and b in ids for a,b in edge_ids.values()),graph["id"]
        for s in graph["scenarios"]:
            assert all(edge_ids[step["edgeId"]]==(step["a"],step["b"]) for step in s["steps"]),s["name"]
        rows=graph.get("coverage",[])
        output["modules"][graph["id"]]=dict(nodes=len(nodes),edges=len(edges),scenarios=len(graph["scenarios"]),
            steps=sum(len(s["steps"]) for s in graph["scenarios"]),coverage=len(rows),
            structure=graph.get("structureCaption"),statuses=sorted({r["status"] for r in rows}))
    return output

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--round", type=int, choices=range(1,11), action="append",
                        help="repeatable; default runs 1 through 10 in order")
    parser.add_argument("--main", type=Path,default=Path("D:/huanjian-project/stage-two/GEM5-1"))
    parser.add_argument("--other",type=Path,default=PROJECT/"zenas-dev")
    parser.add_argument("--publish",action="store_true",help="replace the two delivery HTML files after successful round 10")
    parser.add_argument("--log",type=Path,default=HERE/"conversions.json")
    args=parser.parse_args()
    rounds=sorted(set(args.round or range(1,11)))
    records={}
    previous=None
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        for number in rounds:
            results={}
            for name,source in [("GEM5-1",args.main.resolve()),("GEM5-2",args.other.resolve())]:
                work=tmp/str(number)/name
                work.mkdir(parents=True)
                page=work/(name+".html")
                command=[sys.executable,"-B","-W","ignore::SyntaxWarning"]
                if number==10:
                    archive=work/"GEM5-converter.pyz"
                    shutil.copyfile(CONVERTER/archive.name,archive)
                    command.append(str(archive))
                else:
                    command.append(str(CONVERTER/"convert_model.py"))
                command.extend([str(source),"--entry","configs/example/xiangshan.py","--name",name,"--html",str(page)])
                if number<10:
                    command+=["--through-round",str(number)]
                subprocess.run(command,cwd=work,check=True,stdout=subprocess.PIPE)
                raw=page.read_bytes()
                m=payload(raw.decode())
                result=stats(m)
                result.update(htmlSha256=digest(raw),bytes=len(raw),source=str(source))
                if number==10:
                    result["pyzSha256"]=digest(archive.read_bytes())
                    assert {p.name for p in work.iterdir()}=={page.name,archive.name}
                results[name]=result
            if number==10 and previous:
                for name in results:
                    assert results[name]["modules"]==previous[name]["modules"]
            records[str(number)]=results
            previous=results if number==9 else None
            print(f'Round {number}: checked both standalone pages',flush=True)
        if 10 in rounds and args.publish:
            for name in ["GEM5-1","GEM5-2"]:
                dest=PROJECT/(name+".html")
                with tempfile.NamedTemporaryFile(dir=PROJECT,delete=False) as f:
                    path=Path(f.name)
                try:
                    shutil.copyfile(tmp/"10"/name/dest.name,path)
                    os.replace(path,dest)
                finally:
                    path.unlink(missing_ok=True)
    args.log.write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf8")

if __name__=="__main__":
    main()

