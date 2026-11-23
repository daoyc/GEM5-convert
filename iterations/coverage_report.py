"""Build the paired coverage inventory from the JSON embedded in two delivery HTMLs."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import quote


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
STATUS = ("已映射", "合并", "条件启用", "未知", "缺失")
MODEL_SCRIPT = re.compile(r'<script type="application/json" id="embedded">(.*?)</script>', re.S)
FEATURES = {
    "bpu": ("预测器注册集合", "cpu.branchPred.tage.numWays", "cpu.branchPred.tage.histLengths"),
    "ftq": ("ftq_size 声明","fsq_size 声明","FTQ 释放"),
    "ifu": ("resident window replay","resident window replay · 条件配置","双 FTQ 目标取指 · 条件配置"),
    "decode": ("decodeWidth","decodeWidth · 理想配置","Decode → Rename 阶段边界"),
    "rename": ("renameWidth · 理想配置","numPhysIntRegs · 理想配置","RAT 硬件 bank 及端口数"),
    "issue": ("整数 IQ","访存 IQ","浮点 / 向量 IQ","推测唤醒网络"),
    "commit": ("ROB 容量","ROB 容量 · 条件配置","Load 值预测失配"),
    "lsu": ("LQ 容量","SQ 容量","Store Buffer 容量 · 条件配置"),
    "mmu": ("遍历根层级","层级数","扩展分页模式"),
    "icache": ("缓存容量","MSHR 数量","返回端口"),
    "dcache": ("缓存容量","MSHR 数量","缺失目标保留"),
    "l2": ("缓存容量","MSHR 数量","ITB walker 连接","DTB walker 连接"),
    "l3": ("缓存容量","缓存容量 · 条件配置","MSHR 数量"),
    "bus": ("请求侧端口记录","响应侧查找","内存连接"),
    "mem": ("内存模型","DRAM 时序配置文件"),
}


def load(page):
    raw = page.read_bytes()
    match = MODEL_SCRIPT.search(raw.decode("utf-8-sig"))
    if not match:
        raise ValueError(f"{page} 缺少独立模型数据")
    model = json.loads(match[1])
    modules = {m["id"]:m for m in model["view"]["modules"]}
    if not modules or any(not m.get("coverage") for m in modules.values()):
        raise ValueError(f"{page} 未提供逐模块覆盖记录")
    for m in modules.values():
        for r in m["coverage"]:
            if r["status"] not in STATUS:
                raise ValueError(f"未知覆盖状态 {m['id']} {r['status']}")
    return model, modules, sha256(raw).hexdigest()


def md(value):
    if isinstance(value, bool):
        return "启用" if value else "关闭"
    if value is None:
        return "未知"
    if isinstance(value, (list,dict)):
        value = json.dumps(value, ensure_ascii=False)
    return escape(" ".join(str(value).split()), quote=False).replace("|", r"\|")


def records(module):
    counts, result = Counter(), {}
    for r in module.get("coverage", []):
        key = r["label"]
        counts[key] += 1
        result[key,counts[key]] = r
    return result


def evidence(row, root):
    ref = row.get("evidence") or {}
    file, line = ref.get("file"), ref.get("line")
    if not file or not line:
        return "无已定位行" if not file else md(file)+"（无已定位行）"
    target = quote((root/file).resolve().as_posix(), safe="/:")
    return f"[{md(file)}:{line}]({target}:{line})"


def describe(row, show_condition=True):
    if row is None:
        return "未列此项"
    value = md(row.get("value"))
    condition = row.get("condition")
    if show_condition and condition:
        value += f"（{md(condition)}）"
    return value


def cells(row, root):
    if row is None:
        return "未列此项 | —"
    return f"{row['status']} · {describe(row)} | {evidence(row, root)}"


def shape(module):
    if module is None:
        return "未生成"
    return " / ".join(str(len(module[key])) for key in ("parts","internalEdges","scenarios"))


def focus_labels(uid, a, b):
    keyed = set(a) | set(b)
    keys = [(name,1) for name in FEATURES.get(uid, ()) if (name,1) in keyed]
    if not keys:
        keys = [k for k in dict.fromkeys([*a,*b]) if k[0] not in ("模块映射","内部组件")][:2]
    return keys


def write_report(output, pages, roots):
    inputs = [load(p) for p in pages]
    first, second = [x[1] for x in inputs]
    module_ids = list(dict.fromkeys([*first, *second]))
    a_name,b_name = [md(x[0]["name"]) for x in inputs]
    doc = ["# 两份 gem5 模型的结构覆盖清单", "",
           f"{a_name} 对应 {md(roots[0].name)} 源码，{b_name} 对应 {md(roots[1].name)} 源码。"
           "计数来自两张独立页面内嵌的模型，子图节点包括上下游边界，边按有向边 ID 计数，场景为已绑定边的源码演示。", "",
           f"| 模块 | {a_name} 节点 / 边 / 场景 | {b_name} 节点 / 边 / 场景 | 图中重点 |",
           "|---|---:|---:|---|"]
    for uid in module_ids:
        left, right = first.get(uid), second.get(uid)
        title = (left or right)["name"]
        captions = [m.get("structureCaption","") if m else "" for m in (left,right)]
        brief = " → ".join(map(md,captions)) if all(captions) and captions[0]!=captions[1] else md(captions[0] or captions[1])
        if not brief:
            keys = focus_labels(uid,records(left or {}),records(right or {}))
            brief = "、".join(k[0] for k in keys[:2]) or "、".join(p["name"] for p in (left or right)["parts"][:2])
        doc.append(f"| {md(title)} | {shape(left)} | {shape(right)} | {brief} |")

    doc += ["", "## 阅读差异", "",
            "已映射表示有源码定位，合并表示多个具体对象或 CPU 内部阶段共用图中节点，条件启用表示实现受配置或运行分支约束。"
            "未知保留尚不能定值的结构，缺失仅指当前映射在对应输入中明确记录的缺口。两边记录集合不同时，表格用“未列此项”表示该页没有提供该项记录。", ""]
    if "issue" in first and "issue" in second:
        schedulers = [m["issue"].get("scheduler") for m in (first,second)]
        if all(schedulers):
            doc.append("- **发射与依赖唤醒。** "+"。".join(
                f"{name} 将 {sum(len(g['queues']) for g in sched['groups'])} 个 IQ 配到 "
                f"{sched['outputPorts']} 个出口，显式源到目的队列有 {len(sched['wakeupRoutes'])} 条连接"
                for name,sched in zip((a_name,b_name),schedulers))+"。")
    def paired_summary(uid, label, heading):
        ra = records(first.get(uid,{})).get((label,1))
        rb = records(second.get(uid,{})).get((label,1))
        if ra and rb and (ra["status"],ra["value"])!=(rb["status"],rb["value"]):
            doc.append(f"- **{heading}。** {a_name} 为{describe(ra,False)}（{ra['status']}），"
                       f"{b_name} 为{describe(rb,False)}（{rb['status']}）。")
    paired_summary("ifu","resident window replay","取指驻留窗口的默认状态")
    paired_summary("mmu","遍历根层级","页表遍历起点")
    paired_summary("commit","ROB 容量 · 条件配置","满足理想参数条件时的 ROB 容量")
    doc.append("")
    for uid in module_ids:
        left, right = first.get(uid, {}), second.get(uid,{})
        a,b = records(left),records(right)
        keys = focus_labels(uid,a,b)
        title = (left or right)["name"]
        doc += [f"### {md(title)}", ""]
        if keys:
            doc += [f"| 核查项 | {a_name} | {b_name} |", "|---|---|---|"]
            for k in keys:
                av,bv=a.get(k),b.get(k)
                def short(r,root):
                    if not r:
                        return "未列此项"
                    text=describe(r,False)
                    return f"{r['status']} · {text} · {evidence(r,root)}"
                doc.append(f"| {md(k[0])} | {short(av,roots[0])} | {short(bv,roots[1])} |")
            doc.append("")
        counts=[Counter(r["status"] for r in rows.values()) for rows in (a,b)]
        doc += ["覆盖记录数按两页顺序列示，"+"，".join(f"{s} {counts[0][s]}/{counts[1][s]}" for s in STATUS)+"。", "",
                "<details><summary>全部覆盖项、适用条件与源码行</summary>", "",
                f"| 结构项 | {a_name} 结果 | {a_name} 依据 | {b_name} 结果 | {b_name} 依据 |",
                "|---|---|---|---|---|"]
        for name,index in dict.fromkeys([*a,*b]):
            label = md(name)+(f"（{index}）" if index>1 else "")
            doc.append(f"| {label} | {cells(a.get((name,index)),roots[0])} | {cells(b.get((name,index)),roots[1])} |")
        doc += ["","</details>", ""]

    doc+=["## 当前仍需核对", ""]
    remaining=defaultdict(list)
    for i,(model,graphs,_) in enumerate(inputs):
        for g in graphs.values():
            for r in g["coverage"]:
                if r["status"] in ("未知","缺失"):
                    desc = f"{g['name']} · {r['label']}（{r['status']}）"
                    remaining[desc].append(f"{md(model['name'])} · {describe(r)} · {evidence(r,roots[i])}")
    if remaining:
        for desc,items in remaining.items():
            doc.append("- "+md(desc)+"。"+"。".join(items)+"。")
    if not all(x[0].get("config") for x in inputs):
        doc.append("- 源码页可以核对配置默认与条件覆盖。未附带实际运行配置的页面仍需同次运行的配置文件核对实例数量、端口绑定与参数有效值。")
    doc.append("- 图中演示的步骤由源码映射生成。实际发生顺序、tick 与同周期事件顺序需由运行 trace 核对。")
    doc += ["","## 输入标识", ""]
    for model,_,digest in inputs:
        doc.append(f"- {md(model['name'])} · {md(model['view']['source'])} · HTML SHA-256 \x60{digest}\x60")
    output.write_text("\n".join(doc)+"\n",encoding="utf-8")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--main",type=Path,default=PROJECT/"GEM5-1.html")
    p.add_argument("--other",type=Path,default=PROJECT/"GEM5-2.html")
    p.add_argument("--main-source",type=Path,default=Path("D:/huanjian-project/stage-two/GEM5-1"))
    p.add_argument("--other-source",type=Path,default=PROJECT/"zenas-dev")
    p.add_argument("-o","--output",type=Path,default=HERE/"COVERAGE.md")
    args=p.parse_args()
    write_report(args.output,(args.main,args.other),(args.main_source,args.other_source))
    print(args.output)


if __name__=="__main__":
    main()

