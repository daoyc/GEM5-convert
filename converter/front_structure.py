"""Source-bound predictor, address-translation and recovery structure for XiangShan."""
import ast
import re
from bisect import bisect_right
from pathlib import Path

from semantics import relation
from zenas_details import bind_scenarios


class Source:
    """Token-level searches retain offsets and ignore C/C++ comments and string contents."""

    def __init__(self, root, file):
        self.file = file
        try:
            self.text = (root / file).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            self.text = ""
        self.lines = self.text.splitlines()
        self.starts = [0] + [m.end() for m in re.finditer("\n", self.text)]
        self.code = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',
                           lambda m: re.sub(r'[^\n]', ' ', m[0]), self.text, flags=re.S)

    def anchor(self, start, end):
        line = bisect_right(self.starts, start)
        last = bisect_right(self.starts, end - 1)
        return dict(file=self.file, line=line, endLine=last,
                    text="\n".join(self.lines[line - 1:last]).strip())

    def find(self, pattern):
        m = re.search(pattern, self.code, re.M)
        return self.anchor(*m.span()) if m else None


def coverage(module, label, value, evidence, status="已映射", origin="源码结构", condition=None):
    row = dict(label=label, value=value, evidence=evidence or {}, status=status if evidence else "未知", origin=origin)
    if condition:
        row["condition"] = condition
    module.setdefault("coverage", []).append(row)


def part(module, key, title, description, evidence, target=None, role="internal"):
    if not evidence:
        return
    uid = module["id"] + "." + key
    data = dict(id=uid, name=title, description=description, evidence=evidence, role=role)
    if target:
        data["target"] = target
    for old in module["parts"]:
        if old["id"] == uid:
            old.update(data)
            return
    module["parts"].append(data)


def connect(module, a, b, label, evidence):
    prefix = module["id"] + "."
    ids = {n["id"] for n in module["parts"]}
    if prefix+a in ids and prefix+b in ids and evidence:
        if not any(e["a"] == prefix+a and e["b"] == prefix+b for e in module["internalEdges"]):
            module["internalEdges"].append(relation("logical-flow",prefix+a,prefix+b,label,evidence))


def scenarios(module, recipes):
    new = bind_scenarios(module["parts"], module["internalEdges"], recipes, module["id"]+".")
    existing = {s["id"] for s in module["scenarios"]}
    module["scenarios"].extend(s for s in new if s["id"] not in existing)


def python_values(root, file, class_name):
    source = Source(root, file)
    try:
        tree = ast.parse(source.text)
    except SyntaxError:
        return {}
    cls = next((c for c in tree.body if isinstance(c, ast.ClassDef) and c.name == class_name), None)
    result = {}
    for node in cls.body if cls else []:
        if not isinstance(node, ast.Assign) or not isinstance(node.targets[0], ast.Name):
            continue
        val = node.value
        if isinstance(val, ast.Call) and val.args:
            ev = dict(file=file, line=node.lineno, endLine=node.end_lineno,
                      text="\n".join(source.lines[node.lineno-1:node.end_lineno]).strip())
            try:
                value = ast.literal_eval(val.args[0])
            except (ValueError,TypeError):
                value = ast.unparse(val.args[0])
            result[node.targets[0].id] = (value, ev)
    return result


def conditional_value(module, field, default, assignments, apply, condition):
    if default:
        coverage(module, field+" 声明", *default, origin="源码默认")
    for row in assignments:
        try:
            value = ast.literal_eval(row["value"])
        except (ValueError, SyntaxError):
            value = row["value"]
        coverage(module, field+" 配置赋值",value,row["evidence"],
                 status="已映射" if apply else "条件启用",origin="配置覆盖",condition=condition)
    value = assignments[-1]["value"] if assignments and apply else default[0] if default else None
    return value


def predictors(root, settings, view, modules):
    bpu, queue = modules["bpu"], modules["ftq"]
    selection = bpu["parameters"].get("预测器", {})
    cls = selection.get("value")
    variant = {"DecoupledBPUWithBTB":"btb","DecoupledBPUWithFTB":"ftb"}.get(cls)
    if not variant:
        coverage(bpu,"预测器注册集合",None,selection.get("dynamic"),"未知",
                 condition="ObjectList.bp_list.get(args.bp_type) 的动态对象未确认")
        bpu["structureCaption"]="预测器为动态选择"
        return
    file = "src/cpu/pred/"+variant+"/decoupled_bpred.cc"
    src = Source(root,file)
    ftq = Source(root,file.replace("decoupled_bpred", "fetch_target_queue"))
    registrations = list(re.finditer(r'\bcomponents\s*\.\s*push_back\s*\(\s*(\w+)\s*\)\s*;',src.code))
    names = [m[1] for m in registrations]
    condition = ("--bp-type 未指定或等于 DecoupledBPUWithFTB" if variant=="ftb"
                 else "--bp-type=DecoupledBPUWithBTB")
    anchors = {m[1]:src.anchor(*m.span()) for m in registrations}
    coverage(bpu,"预测器注册集合",names,next(iter(anchors.values()),None),condition=condition)
    bpu["structureCaption"] = f"{variant.upper()} · {len(names)} 个注册组件" if names else cls+" · 注册集合未知"
    entry=Source(root,"configs/example/xiangshan.py")
    tree=ast.parse(entry.text)
    for assignment in ast.walk(tree):
        if (isinstance(assignment,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="BPClass" for t in assignment.targets)
                and isinstance(assignment.value,ast.IfExp)):
            ev=dict(file=entry.file,line=assignment.lineno,endLine=assignment.end_lineno,
                    text=ast.get_source_segment(entry.text,assignment))
            coverage(bpu,"配置入口选择表达式",ast.unparse(assignment.value),ev,"条件启用","配置覆盖",
                     ast.unparse(assignment.value.test))
    for r in view["overrides"]:
        if r["target"] in ("cpu.enableFetchResidentWindowReplay","cpu.branchPred.ras.numEntries",
                           "cpu.branchPred.tage.numWays","cpu.branchPred.tage.histLengths"):
            override_condition="--ideal-kuanglangv1；"+"；".join(r["conditions"])
            # These are source branches; even with runtime settings they remain separate from instance facts.
            coverage(bpu,r["target"],r["value"],r["evidence"],"条件启用","配置覆盖",override_condition)
    declarations = python_values(root, "src/cpu/pred/BranchPredictor.py", cls)
    for key, ev in anchors.items():
        title = {"uftb":"uFTB","uras":"uRAS"}.get(key,key.upper())
        value, param = declarations.get(key,(None,None))
        coverage(bpu,title+" 注册",value or key,ev,condition=condition)
        if param:
            coverage(bpu,title+" 声明",value,param,origin="源码默认")
        part(bpu,key,title,"构造函数注册的预测组件 "+str(value or key),ev)
        connect(bpu,"banks",key,"向已注册组件分发 PC 与历史",src.find(r'components\s*\[\s*i\s*\]\s*->\s*putPCHistory\('))
        connect(bpu,key,"select","组件参与逐级预测结果选择",src.find(r'numOverrideBubbles\s*=\s*generateFinalPredAndCreateBubbles\('))
    # A declaration may survive in Python after its registration was removed in C++.
    for key in sorted((set(declarations) & {"uftb","uras","ftb","ubtb","abtb","btb","mgsc"}) - set(names)):
        coverage(bpu,key+" 注册", "当前实现只有参数声明", declarations[key][1],"缺失",condition=condition)
    fsq = src.find(r'fetchStreamQueue\s*\.\s*emplace\s*\(')
    lookup = src.find(r'fetchStreamQueue\s*\.\s*find\s*\(\s*ftq_enq_state\.streamId\s*\)')
    enqueue = src.find(r'fetchTargetQueue\s*\.\s*enqueue\s*\(')
    finish = ftq.find(r'ftq\s*\.\s*erase\s*\(\s*supplyFetchTargetState\.targetId\s*\)')
    for key,title,evidence in [("fsq","FSQ 预测流",fsq),("lookup","按 streamId 取流",lookup),("finish","消费目标项",finish)]:
        part(queue,key,title,title,evidence)
    connect(queue,"fsq","lookup","FTQ 填充按 streamId 查找 FSQ",lookup)
    connect(queue,"lookup","entries","从预测流生成目标项入队",enqueue)
    connect(queue,"ifu","finish","目标块消耗完成后释放对应项",finish)
    scenarios(queue,[("from-stream","预测流生产与取指消费","fsq lookup entries demand supply ifu finish")])
    for key,desc,ev in [("FSQ 写入","预测器生成 FetchStream",fsq),("FSQ 读取","按目标流编号查找",lookup),
                        ("FTQ 写入","切分预测块入队",enqueue),("FTQ 释放","供给项消费后释放",finish)]:
        coverage(queue,key,desc,ev)
    explicit = settings.get("bp_type")==cls
    sizes=[]
    for key in ("ftq_size","fsq_size"):
        assigns = [a for a in view["overrides"] if a["target"]=="cpu.branchPred."+key]
        size=conditional_value(queue,key,declarations.get(key),assigns,
                               explicit and bool(settings.get("ideal_kuanglangv1")),
                               "--ideal-kuanglangv1 且显式选择 FTB 或 BTB")
        sizes.append(str(size) if size is not None else "未知")
    queue["structureCaption"]="FTQ "+sizes[0]+" 项 · FSQ "+sizes[1]+" 项"


def translation(root, view, module):
    tlb=Source(root,"src/arch/riscv/tlb.cc")
    walker=Source(root,"src/arch/riscv/pagetable_walker.cc")
    mmu=Source(root,"src/arch/riscv/RiscvMMU.py")
    lookup=tlb.find(r'e\[i_e\]\s*=\s*l2tlb->lookupL2TLB\(\s*vaddr,\s*satp\.asid,\s*mode,\s*false,\s*i_e,\s*true,\s*direct\s*\);')
    start=tlb.find(r'fault\s*=\s*walker->start\(\s*0,\s*tc,\s*translation,\s*req,\s*mode,\s*false,\s*false,\s*(?:2|root_level),\s*false,\s*0\s*\);')
    root_rule=walker.find(r'const\s+int\s+root_level\s*=\s*[^;]*;')
    mode_rule=walker.find(r'if\s*\(walker->openSv48\s*&&\s*satp\.mode\s*==\s*AddrXlateMode::SV48\)\s*\{\s*level\s*=\s*3;[^{}]*\}\s*else\s*\{\s*level\s*=\s*2;')
    actual="动态 root_level" if root_rule else "SV48/SV39 分支" if mode_rule else None
    coverage(module,"遍历根层级",actual,root_rule or mode_rule,
             status="条件启用",condition="由当前 SATP 模式和扩展翻译开关决定")
    coverage(module,"L2 TLB miss → walker",start["text"] if start else None,start)
    if root_rule:
        paging=Source(root,"src/arch/riscv/pagetable.hh")
        coverage(module,"层级数","按虚拟地址位数求页表级数",
                 paging.find(r'return\s+bits\s*\?\s*\(bits\s*-\s*12\)\s*/\s*LEVEL_BITS\s*:\s*0;'))
        wide=paging.find(r'return\s+mode\s*==\s*SV48\s*\|\|\s*mode\s*==\s*SV57;')
        coverage(module,"扩展分页模式","SV48 / SV57",wide,"条件启用",condition="扩展分页启用且 SATP 选择相应模式")
    if mode_rule:
        coverage(module,"层级数","SV39 从 2 级、SV48 从 3 级开始，级编号从 0 起",mode_rule,"条件启用",condition="openSv48 且 SATP 为 SV48 时走 3 级分支")
    send=walker.find(r'if\s*\(port\.sendTimingReq\(pkt\)\)')
    recv=walker.find(r'return\s+walker->recvTimingResp\(pkt\);')
    refill=walker.find(r'walker->tlb->insert\(entry\.vaddr,\s*entry,\s*false,\s*direct\);')
    for side,owner,title,walk in [("itb","ifu","取指","iwalk"),("dtb","lsu","访存","dwalk")]:
        port=mmu.find(r'self\.'+side+r'\.walker\.port\s*=\s*[id]port')
        coverage(module,side.upper()+" walker 端口",side+".walker.port",port)
        for a,b,ev,label in [(side,"l2",lookup,"一级 miss 查询共享 L2 TLB"),
                              ("l2",walk,start,"共享项未命中，由 L1 的 walker 发起遍历")]:
            old=next((e for e in module["internalEdges"] if e["a"]=="mmu."+a and e["b"]=="mmu."+b),None)
            if ev and old:
                old["evidence"]=ev
            else:
                connect(module,a,b,label,ev)
        if all((port,start,send,recv,refill)):
            scenarios(module,[(side+"-walk",title+" · 叶项遍历与回填",f"{owner} {side} l2 {walk} pte {walk} {side}")])
    coverage(module,"页表读取","发送 PTE 请求",send)
    coverage(module,"WalkerPort 响应","接收 PTE 数据",recv)
    coverage(module,"成功叶项回填","插入发起翻译的 TLB",refill)
    if not start:
        view["warnings"].append("映射未匹配 src/arch/riscv/tlb.cc · L2 miss 后启动 walker 的参数或根层级")
    mode_evidence=root_rule or mode_rule
    if mode_evidence and start:
        part(module,"paging","SATP / 页表层级","由当前模式和扩展分页开关决定起始层级",mode_evidence)
        connect(module,"l2","paging","L2 miss 选择遍历根层级",start)
        for owner,side,walk in [("ifu","itb","iwalk"),("lsu","dtb","dwalk")]:
            connect(module,"paging",walk,"walker 在 setupWalk 中按模式选取层级",mode_evidence)
            scenarios(module,[(side+"-paging","条件模式 · "+side.upper()+" 按 SATP 遍历",
                               f"{owner} {side} l2 paging {walk} pte {walk} {side}")])
    module["structureCaption"]="双侧 Walker · "+(actual or "根层级未解析")




def recovery(root, settings, view, modules):
    c=modules["commit"]
    commit=Source(root,"src/cpu/o3/commit.cc")
    fetch=Source(root,"src/cpu/o3/fetch.cc")
    iew=Source(root,"src/cpu/o3/iew.cc")
    unit=Source(root,"src/cpu/o3/lsq_unit.cc")
    wb=iew.find(r'execWB->mispredictInst\[tid\]\s*=\s*inst;')
    arbitrate=commit.find(r'if\s*\(fromIEW->squash\[tid\]\s*&&[^)]+\)')
    rollback=commit.find(r'youngestSeqNum\[tid\]\s*=\s*squashed_inst;\s*rob->squash\(squashed_inst,\s*tid\);')
    signal=commit.find(r'toIEW->commitInfo\[tid\]\.mispredictInst\s*=\s*fromIEW->mispredictInst\[tid\];')
    redirect=fetch.find(r'squash\(\*fromCommit->commitInfo\[tid\]\.pc,\s*fromCommit->commitInfo\[tid\]\.doneSeqNum,\s*fromCommit->commitInfo\[tid\]\.squashInst,\s*tid\);')
    variant={"DecoupledBPUWithBTB":"btb","DecoupledBPUWithFTB":"ftb"}.get(
        modules.get("bpu",{}).get("parameters",{}).get("预测器",{}).get("value"))
    control=fetch.find(r'dbp'+variant+r'->controlSquash\(\s*mispred_inst->getFtqId\(\),\s*mispred_inst->getFsqId\(\)') if variant else None
    trap=fetch.find(r'dbp'+variant+r'->trapSquash\(\s*fromCommit->commitInfo\[tid\]\.squashedTargetId') if variant else None
    enqueue_fault=commit.find(r'generateTrapEvent\(tid,\s*inst_fault\);')
    trap_redirect=commit.find(r'Commit::squashFromTrap\([^)]*\)\s*\{\s*squashAll\(tid\);\s*toIEW->commitInfo\[tid\]\.isTrapSquash\s*=\s*true;')
    for key,title,desc,ev,target,role in [
        ("mispredict","IEW 误预测","报告错误的控制流与修正 PC",wb,"issue","up"),
        ("arbitrate","恢复仲裁","按线程状态和序列号筛选来自 IEW 的 squash",arbitrate,None,"internal"),
        ("rollback","ROB 回滚","丢弃恢复边界后的年轻指令",rollback,None,"internal"),
        ("signal","Commit 广播","回传误预测指令、恢复边界和 PC",signal,None,"internal"),
        ("trapEvent","Trap event","调度异常恢复事件",enqueue_fault,None,"internal"),
        ("trapFlush","精确异常清空","squashAll 后广播 isTrapSquash",trap_redirect,None,"internal"),
        ("fetchRedirect","Fetch 重定向","恢复 PC、清理前端错误流",redirect,"ifu","down"),
        ("controlRecovery","BPU 分支恢复","根据 FTQ/FSQ ID 和实际方向恢复预测历史",control,"bpu","down"),
        ("trapRecovery","BPU 异常恢复","以异常入口和提交 PC 恢复预测流",trap,"bpu","down")]:
        part(c,key,title,desc,ev,target,role)
    for a,b,label,ev in [("mispredict","arbitrate","提交仲裁 IEW 恢复请求",arbitrate),
                         ("arbitrate","rollback","从确定的 ROB 边界开始清除",rollback),
                         ("rollback","signal","向前序阶段发布恢复信息",signal),
                         ("signal","fetchRedirect","前端消费 Commit 的恢复 PC",redirect),
                         ("trap","trapEvent","队首异常调度 trap event",enqueue_fault),
                         ("trapEvent","trapFlush","异常事件触发全线程恢复",trap_redirect),
                         ("trapFlush","fetchRedirect","Fetch 消费精确异常的重定向",redirect),
                         ("fetchRedirect","controlRecovery","误预测触发 controlSquash",control),
                         ("fetchRedirect","trapRecovery","异常触发 trapSquash",trap)]:
        connect(c,a,b,label,ev)
    scenarios(c,[("branch-recovery","分支误预测、回滚与前端恢复","mispredict arbitrate rollback signal fetchRedirect controlRecovery"),
                 ("fault-recovery","队首异常、清空与重定向","rob head trap trapEvent trapFlush fetchRedirect trapRecovery")])
    overview_path=[("issue","commit","通知分支误预测",wb),
                   ("commit","ifu","广播 squash 边界与恢复 PC",redirect),
                   ("ifu","bpu","按目标与流编号恢复预测器",control)]
    if all(a in modules and b in modules and ev for a,b,_,ev in overview_path):
        steps=[]
        for a,b,label,ev in overview_path:
            e=relation("logical-flow",a,b,label,ev,eventType="恢复",description=label)
            view["edges"].append(e)
            steps.append(dict(edgeId=e["id"],a=a,b=b,type="恢复",text=label))
        view["scenarios"].append(dict(id="branch-recovery",name="分支误预测与前端重定向",steps=steps))
    for label,desc,ev in [("误预测仲裁","存在可接受的 IEW squash 请求",arbitrate),
                          ("ROB 清理","保留恢复边界，丢弃年轻指令",rollback),
                          ("精确异常","squashAll + isTrapSquash",trap_redirect),
                          ("恢复 PC","Fetch 使用 Commit 提供的 PC",redirect)]:
        coverage(c,label,desc,ev)
    decl=python_values(root,"src/cpu/o3/BaseO3CPU.py","BaseO3CPU")
    for module,keys in [(c,("numROBEntries","squashWidth")),
                        (modules["lsu"],("LQEntries","SQEntries","SbufferEntries")),
                        (modules["issue"],("numDQEntries",))]:
        for key in keys:
            assigns=[a for a in view["overrides"] if a["target"]=="cpu."+key]
            conditional_value(module,key,decl.get(key),assigns,bool(settings.get("ideal_kuanglangv1")),"--ideal-kuanglangv1")
    for module,label,pat in [(modules["issue"],"IQ 回滚",r'instQueue\.squash\(tid\);'),
                             (modules["lsu"],"LSQ 回滚",r'ldstQueue\.squash\(fromCommit->commitInfo\[tid\]\.doneSeqNum,\s*tid\);')]:
        coverage(module,label,"按提交边界清除年轻指令或访存项",iew.find(pat))
    lvp=unit.find(r'iewStage->squashDueToLVPMiss\(inst,\s*inst->threadNumber\);')
    if lvp:
        coverage(c,"Load 值预测失配","LSQ → IEW → Commit",lvp,"条件启用",condition="编译时 LVP_ON，Load 具有预测且实际值与预测值不同")
    c["structureCaption"]="ROB · 分支恢复 / 精确异常"+(" / LVP 失配" if lvp else "")




def enrich(root, settings, view, round_number=10):
    modules = {m["id"]:m for m in view["modules"]}
    if round_number >= 4 and "bpu" in modules and "ftq" in modules:
        predictors(Path(root),settings,view,modules)
    if round_number >= 5 and "mmu" in modules:
        translation(Path(root),view,modules["mmu"])
    if round_number >= 6 and {"commit","issue","lsu"} <= modules.keys():
        recovery(Path(root),settings,view,modules)

