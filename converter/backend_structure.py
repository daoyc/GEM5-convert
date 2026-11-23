"""Resolve the active scheduler of an xiangshan.py CPU without executing gem5."""
import ast
from pathlib import Path

ENTRY = "configs/example/xiangshan.py"
SCHED = "configs/common/FUScheduler.py"
POOL = "src/cpu/o3/FUPool.py"
QUEUE = "src/cpu/o3/issue_queue.cc"


class Source:
    def __init__(self, root, relative):
        self.file = relative
        self.lines = []
        self.tree = ast.Module(body=[], type_ignores=[])
        try:
            self.lines = (root / relative).read_text(encoding="utf-8-sig").splitlines()
            if relative.endswith(".py"):
                self.tree = ast.parse("\n".join(self.lines))
        except (OSError, SyntaxError, UnicodeError):
            pass

    def evidence(self, node):
        if node is None:
            return {"file": self.file, "unresolved": True}
        return {"file": self.file, "line": node.lineno, "text": self.lines[node.lineno - 1].strip()}

    def class_named(self, name):
        return next((n for n in self.tree.body if isinstance(n, ast.ClassDef) and n.name == name), None)


def named_field(statements, name):
    matches = [n for n in statements if isinstance(n, ast.Assign) and len(n.targets) == 1
               and ast.unparse(n.targets[0]) == name]
    return matches[-1] if matches else None


def constructor(node):
    return node.func.id if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) else None


def row(label, status, value, evidence, origin="源码结构", **extras):
    return dict(label=label, status=status, value=value, evidence=evidence, origin=origin, **extras)


def resolve_scheduler(entry, settings):
    build = next((n for n in entry.tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == "build_test_system"), None)
    select = named_field(build.body if build else [], "TestCPUClass")
    cpu = select.value.id if select and isinstance(select.value, ast.Name) else None
    core = entry.class_named(cpu)
    assignment = named_field(core.body if core else [], "scheduler")
    origin = "源码默认"
    if settings.get("ideal_kuanglangv1"):
        # Verify the option actually calls the override function in this input tree.
        for branch in ast.walk(entry.tree):
            if not isinstance(branch, ast.If) or ast.unparse(branch.test) != "args.ideal_kuanglangv1":
                continue
            active = {constructor(n) for stmt in branch.body for n in ast.walk(stmt) if isinstance(n, ast.Call)}
            for fn in entry.tree.body:
                if isinstance(fn, ast.FunctionDef) and fn.name in active:
                    override = named_field(ast.walk(fn), "cpu.scheduler")
                    if override:
                        assignment, origin = override, "配置覆盖"
    return cpu, select, constructor(assignment.value) if assignment else None, assignment, origin


def ideal_body(entry):
    """Resolve the setter called by the selected script's ideal-mode guard."""
    for branch in ast.walk(entry.tree):
        if isinstance(branch, ast.If) and ast.unparse(branch.test) == "args.ideal_kuanglangv1":
            names = {constructor(n.value) for n in branch.body if isinstance(n, ast.Expr)}
            for function in entry.tree.body:
                if isinstance(function, ast.FunctionDef) and function.name in names:
                    return [stmt for loop in function.body if isinstance(loop, ast.For)
                            and ast.unparse(loop.target) == "cpu" and ast.unparse(loop.iter) == "system.cpu"
                            for stmt in loop.body], branch
    return [], None


def baseline_ownership(root, entry, cpu, settings, view):
    from functools import lru_cache

    @lru_cache(None)
    def src(file):
        return entry if file == ENTRY else Source(root, file)

    modules = {m["id"]:m for m in view["modules"]}
    hh = "src/cpu/o3/cpu.hh"
    cache = "configs/common/CacheConfig.py"
    base_cpu = "src/cpu/BaseCPU.py"
    members = {"ifu": ("cpu.fetch","Fetch fetch;",hh), "decode":("cpu.decode","Decode decode;",hh),
               "rename":("cpu.rename","Rename rename;",hh), "issue":("cpu.iew","IEW iew;",hh),
               "commit":("cpu.commit","Commit commit;",hh),
               "lsu":("cpu.iew.ldstQueue","LSQ ldstQueue;","src/cpu/o3/iew.hh")}
    for uid, (path, statement, file) in members.items():
        if uid in modules:
            ev = source_line(src(file),statement)
            modules[uid]["coverage"].append(row("实现归属", "未知" if ev.get("unresolved") else "合并",
                path+" · CPU 内部 C++ 成员", ev))

    pred = {None:"ftb","DecoupledBPUWithFTB":"ftb","DecoupledBPUWithBTB":"btb"}.get(settings.get("bp_type"))
    feature = "test_sys.cpu[i].branchPred = BPClass(" if pred else "test_sys.cpu[i].branchPred = ObjectList.bp_list.get("
    owners = {"bpu":("system.cpu[i].branchPred",ENTRY,feature),
              "icache":("system.cpu[i].icache",base_cpu,"self.icache = ic"),
              "dcache":("system.cpu[i].dcache",base_cpu,"self.dcache = dc"),
              "l2":("system.l2_caches[i]",cache,"system.l2_caches = ["),
              "l3":("system.l3",cache,"system.l3 = L3Cache("),
              "mem":("system.mem_ctrls[i]","configs/common/MemConfig.py","subsystem.mem_ctrls = mem_ctrls")}
    for uid,(path,file,token) in owners.items():
        if uid in modules:
            ev = source_line(src(file),token)
            modules[uid]["coverage"].append(row("配置对象路径","未知" if ev.get("unresolved") else "已映射",path,ev,"配置覆盖"))
    if "ftq" in modules:
        ev = source_line(src(f"src/cpu/pred/{pred}/decoupled_bpred.cc"),"fetchTargetQueue(p.ftq_size)") if pred else {"file":ENTRY,"unresolved":True}
        modules["ftq"]["coverage"].append(row("实现归属","未知" if ev.get("unresolved") else "合并",
            "cpu.branchPred.fetchTargetQueue · 预测器内部 C++ 成员" if pred else "动态预测器待核查",ev))
    if "bus" in modules:
        fs = src("configs/common/FSConfig.py")
        make = next((n for n in fs.tree.body if isinstance(n,ast.FunctionDef) and n.name=="makeBareMetalXiangshanSystem"),None)
        ev = fs.evidence(named_field(ast.walk(make),"self.membus") if make else None)
        modules["bus"]["coverage"].append(row("配置对象路径","未知" if ev.get("unresolved") else "已映射","system.membus",ev,"配置覆盖"))

    # Read only declarations on the active CPU class and its actual ISA/base classes.
    classes = {n.name:(n,source) for source in (src("src/cpu/o3/BaseO3CPU.py"),
               src("src/arch/riscv/RiscvCPU.py"),entry) for n in source.tree.body if isinstance(n,ast.ClassDef)}
    def lookup(name, field, seen=()):
        if name not in classes or name in seen:
            return None, None
        cls,source = classes[name]
        at = named_field(cls.body,field)
        if at:return at,source
        for base in cls.bases:
            at,source = lookup(ast.unparse(base),field,(*seen,name))
            if at:return at,source
        return None,None

    if "mmu" in modules:
        at,file = lookup(cpu,"mmu")
        ev = file.evidence(at) if at else {"file":ENTRY,"unresolved":True}
        modules["mmu"]["coverage"].append(row("配置对象路径","已映射" if at else "未知","system.cpu[i].mmu",ev,"源码默认"))

    ideal,guard = ideal_body(entry)
    for uid, fields in (("decode",["decodeWidth"]),("rename",["renameWidth","numPhysIntRegs","numPhysFloatRegs",
                        "numPhysVecRegs","numPhysVecPredRegs","numPhysVecBufRegs","numPhysCCRegs","numPhysRMiscRegs"])):
        if uid not in modules:continue
        m = modules[uid]
        limits = m.setdefault("cpuFields",{})
        coverage = m["coverage"]
        for field in fields:
            default, source = lookup(cpu,field)
            expression = default.value if default else None
            if isinstance(expression,ast.Call) and ast.unparse(expression.func).startswith("Param."):
                expression = expression.args[0] if expression.args else None
            default_value = int_value(expression)
            declaration = source.evidence(default) if default else {"file":ENTRY,"unresolved":True}
            alt = named_field(ideal,"cpu."+field)
            enabled = bool(alt and settings.get("ideal_kuanglangv1"))
            effective = int_value(alt.value) if enabled else default_value
            selected = entry.evidence(alt) if enabled else declaration
            origin = "配置覆盖" if enabled else "源码默认"
            limits[field] = dict(value=effective, declaration=declaration, default=default_value, evidence=selected, origin=origin)
            coverage.append(row(field,"未知" if effective is None else "已映射",effective,selected,origin,
                                defaultValue=default_value, defaultEvidence=declaration,
                                runtime={"owner":"cpu","key":field}))
            if alt:
                cond="ideal_kuanglangv1=true"
                limits[field]["conditionalOverride"]=dict(value=int_value(alt.value),condition=cond,
                                    evidence=entry.evidence(alt),guard=entry.evidence(guard),active=enabled)
                coverage.append(row(field+" · 理想配置","条件启用",int_value(alt.value),entry.evidence(alt),
                                    "配置覆盖",condition=cond))
        width=limits[uid+"Width"]["value"]
        if width is not None:m["structureCaption"]=f"{width} 条/周期 · "+("译码" if uid=="decode" else "重命名")
    cc=src("src/cpu/o3/cpu.cc")
    if "decode" in modules:
        modules["decode"]["coverage"].append(row("Decode → Rename 阶段边界","合并",
            "decodeQueue 由同一 O3CPU 注入，两个阶段通过 CPU 内部时间缓冲传递指令",
            source_line(cc,"rename.setDecodeQueue(&decodeQueue)")))
    if "rename" in modules:
        cov=modules["rename"]["coverage"]
        cov.append(row("RAT 与自由表归属","合并","CPU 拥有各线程 renameMap、regFile 和 freeList；Rename 引用这些对象",
                       source_line(cc,"renameMap[tid].init(regClasses, &regFile, &freeList)")))
        cov.append(row("RAT 硬件 bank 及端口数","未知","UnifiedRenameMap 提供按寄存器类别寻址的接口，未获得物理 RAT 分库和读写端口配置",
                       source_line(src("src/cpu/o3/rename_map.hh"),"class UnifiedRenameMap")))



def enrich(root, settings, view, round_number=10):
    if round_number < 1:
        return
    root = Path(root)
    entry = Source(root, ENTRY)
    cpu, selection, scheduler, assignment, origin = resolve_scheduler(entry, settings)
    for module in view["modules"]:
        coverage = module.setdefault("coverage", [])
        coverage.append(row("模块映射", "已映射", module["name"], module["evidence"]))
        internal = [p for p in module["parts"] if p.get("role") == "internal"]
        coverage.append(row("内部组件", "已映射" if internal else "未知",
                            "、".join(p["name"] for p in internal) or "未提取", module["evidence"]))
    baseline_ownership(root, entry, cpu, settings, view)
    issue = next((m for m in view["modules"] if m["id"] == "issue"), None)
    if not issue:
        return
    coverage = issue["coverage"]
    coverage.append(row("CPU 配置类", "已映射" if cpu else "未知", cpu, entry.evidence(selection), "配置覆盖"))
    coverage.append(row("发射调度器", "已映射" if scheduler else "未知",
                        scheduler, entry.evidence(assignment), origin))
    issue["structureCaption"] = scheduler or "调度器未知"
    if round_number >= 2:
        add_scheduler_structure(root, scheduler, issue, round_number)


def int_value(node):
    """The scheduler files use integer literals, sums and products for queue sizes."""
    if isinstance(node, ast.Constant) and type(node.value) is int:
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mult)):
        a, b = int_value(node.left), int_value(node.right)
        if a is not None and b is not None:
            return a + b if isinstance(node.op, ast.Add) else a * b
    return None


def source_line(source, substring):
    for i, text in enumerate(source.lines, 1):
        if substring in text and not text.lstrip().startswith(("//", "#")):
            return dict(file=source.file, line=i, text=text.strip())
    return dict(file=source.file, symbol=substring, unresolved=True)


def assigned_fields(cls):
    return {n.targets[0].id: n.value for n in cls.body if isinstance(n, ast.Assign)
            and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)} if cls else {}


def keywords(call):
    return {kw.arg: kw.value for kw in call.keywords}


def group_calls(node, fields, seen=(), group="IQs"):
    """Follow the selected class's IQs expression, excluding unused class attributes."""
    if isinstance(node, ast.Name) and node.id not in seen and node.id in fields:
        return group_calls(fields[node.id], fields, (*seen, node.id), node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return group_calls(node.left, fields, seen, group) + group_calls(node.right, fields, seen, group)
    if isinstance(node, (ast.List, ast.Tuple)):
        return [(group, child) for child in node.elts]
    return [(group, node)]


def add_flow(module, a, b, label, evidence, text):
    from semantics import relation
    ids = {p["id"] for p in module["parts"]}
    a, b = module["id"] + "." + a, module["id"] + "." + b
    if a in ids and b in ids and not evidence.get("unresolved"):
        module["internalEdges"].append(relation("logical-flow", a, b, label, evidence,
                                                description=text, eventType=label))


def add_part(module, key, name, description, evidence):
    if not evidence.get("unresolved"):
        module["parts"].append(dict(id=module["id"]+"."+key, name=name, role="internal",
                                    description=description, evidence=evidence))


def qty(values):
    return sum(values) if all(v is not None for v in values) else None


def add_scheduler_structure(root, scheduler, module, round_number):
    source, pool, impl = Source(root, SCHED), Source(root, POOL), Source(root, QUEUE)
    cls = source.class_named(scheduler)
    fields = assigned_fields(cls)
    defaults = assigned_fields(pool.class_named("IssueQue"))
    coverage = module["coverage"]
    if not cls or "IQs" not in fields:
        coverage.append(row("IQ 实例列表", "未知", "未找到所选类的 IQs 声明", source.evidence(cls)))
        return
    groups = {}
    complete = True
    queue_inputs = {}
    for group, call in group_calls(fields["IQs"], fields):
        if constructor(call) != "IssueQue":
            complete = False
            coverage.append(row("IQ 实例表达式", "未知", ast.unparse(call) if call else None,
                                source.evidence(call)))
            continue
        kwargs = keywords(call)
        name_node = kwargs.get("name")
        if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
            complete = False
            coverage.append(row("IQ 名称", "未知", None, source.evidence(call)))
            continue
        name = name_node.value
        entries = {}
        for key in ("size", "inports"):
            value_node = kwargs.get(key)
            if value_node is None and isinstance(defaults.get(key), ast.Call):
                default_call = defaults[key]
                value_node = default_call.args[0] if default_call.args else None
                origin = pool
            else:
                origin = source
            entries[key] = int_value(value_node)
            entries[key+"Evidence"] = origin.evidence(value_node)
        entries.update(name=name, evidence=source.evidence(call))
        queue_inputs[name] = kwargs
        groups.setdefault(group, []).append(entries)

    group_rows = []
    for group, queues in groups.items():
        key = group.strip("_")
        label = {"intIQs": "整数 IQ", "memIQs": "访存 IQ", "fpIQs": "浮点 / 向量 IQ"}.get(key, key)
        size = qty([q["size"] for q in queues])
        inputs = qty([q["inports"] for q in queues])
        summary = f"{len(queues)} 队列 · {size if size is not None else '未知'} 项 · {inputs if inputs is not None else '未知'} 个输入端口"
        evidence = source.evidence(fields.get(group) or fields["IQs"])
        status = "合并" if len(queues) > 1 else "已映射"
        group_id = "group-" + key
        add_part(module, group_id, label, summary, evidence)
        add_flow(module, "dispatch", group_id, "按操作类型入队", source_line(impl, "iqs[dispSeqVec.at(disp_seq)]->insert(inst)"),
                 "Scheduler 按操作类型和已选队列索引分派指令。")
        add_flow(module, group_id, "iq", "就绪选择", source_line(impl, "IssueQue::selectInst("),
                 "本组中的队列选择已就绪的指令。")
        coverage.append(row(label, status, summary, evidence))
        for q in queues:
            known = q["size"] is not None and q["inports"] is not None
            coverage.append(row("IQ · " + q["name"], "已映射" if known else "未知",
                                f"容量 {q['size']} · 输入端口 {q['inports']}" if known else "容量或输入端口未知",
                                q["evidence"]))
        group_rows.append(dict(key=group, nodeId=module["id"]+"."+group_id, label=label,
                               queues=queues, size=size, inports=inputs, evidence=evidence))
    model = dict(className=scheduler, evidence=source.evidence(cls), groups=group_rows, complete=complete)
    module["scheduler"] = model
    count = sum(len(g["queues"]) for g in group_rows)
    total = qty([g["size"] for g in group_rows]) if complete else None
    module["structureCaption"] = (f"{count} 个 IQ · {total} 项" if total is not None else
                                  f"{count} 个已定位 IQ · 容量未知")


    if round_number >= 3:
        add_ports_and_wakeup(root, source, pool, impl, fields, model, queue_inputs, module)


def sequence(node):
    return node.elts if isinstance(node, (ast.Tuple, ast.List)) else None


def text_value(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def resolve_port(port, source):
    kw = keywords(port)
    devices = sequence(kw.get("fu"))
    functions = [constructor(device) for device in devices] if devices is not None else None
    reads = []
    complete = functions is not None and all(functions)
    refs = sequence(kw.get("rp"))
    if refs is None and "rp" in kw:
        complete = False
    for ref in refs or []:
        register = {"IntRD":"整数", "FpRD":"浮点"}.get(constructor(ref))
        if register and len(ref.args) == 2:
            number, priority = map(int_value, ref.args)
            if number is not None and priority is not None:
                reads.append(dict(bank=register, port=number, priority=priority, evidence=source.evidence(ref)))
                continue
        complete = False
        reads.append(dict(expression=ast.unparse(ref), evidence=source.evidence(ref)))
    return dict(fu=functions or [], reads=reads, complete=complete, evidence=source.evidence(port))


def fu_operations(func_source, name):
    cls = func_source.class_named(name)
    active = assigned_fields(cls).get("opList")
    names = []
    for op in sequence(active) or []:
        if constructor(op) == "OpDesc":
            text = text_value(keywords(op).get("opClass"))
            if text:
                names.append(text)
    return dict(operations=names, evidence=func_source.evidence(active or cls))


def iq_names(node, model, fields):
    if text_value(node) is not None:
        return [text_value(node)]
    values = sequence(node)
    if values is not None and all(text_value(v) is not None for v in values):
        return [text_value(v) for v in values]
    if isinstance(node, ast.Name):
        comp = fields.get(node.id)
        if isinstance(comp, ast.ListComp) and len(comp.generators) == 1:
            loop = comp.generators[0]
            if (not loop.ifs and isinstance(loop.iter, ast.Name) and isinstance(loop.target, ast.Name)
                    and ast.unparse(comp.elt) == loop.target.id + ".name"):
                group = next((g for g in model["groups"] if g["key"] == loop.iter.id), None)
                if group:
                    return [q["name"] for q in group["queues"]]
    return None


def add_ports_and_wakeup(root, source, pool, impl, fields, model, queue_inputs, module):
    func_source = Source(root,"src/cpu/o3/FuncUnitConfig.py")
    capabilities = {}
    module_reads = set()
    coverage = module["coverage"]
    port_count = 0
    ports_complete = True
    for group in model["groups"]:
        group_count = 0
        for q in group["queues"]:
            q["issuePorts"] = []
            outputs = sequence(queue_inputs[q["name"]].get("oports"))
            if outputs is None or any(constructor(p) != "IssuePort" for p in outputs):
                ports_complete = False
                coverage.append(row("发射端口 · "+q["name"],"未知","端口列表待实例核对",q["evidence"]))
                continue
            for idx, call in enumerate(outputs):
                port = resolve_port(call, source)
                port["index"] = idx
                q["issuePorts"].append(port)
                ports_complete &= port["complete"]
                for name in port["fu"]:
                    if name and name not in capabilities:
                        capabilities[name] = fu_operations(func_source, name)
                wires = []
                for r in port["reads"]:
                    if "bank" in r:
                        module_reads.add((r["bank"], r["port"]))
                        wires.append(f"{r['bank']}{r['port']}(P{r['priority']})")
                    else:
                        wires.append("未知")
                coverage.append(row(f"{q['name']} / 出口 {idx}", "已映射" if port["complete"] else "未知",
                                    f"FU {' + '.join(n or '未知' for n in port['fu'])} · 读端口 {', '.join(wires) or '未指定'}",
                                    port["evidence"]))
            group_count += len(outputs)
        group["outputPorts"] = group_count
        port_count += group_count

    model.update(fuCapabilities=capabilities, outputPorts=port_count if ports_complete else None,
                 registerReadPorts={bank:sorted(index for kind,index in module_reads if kind == bank)
                                    for bank in ("整数", "浮点")})
    for name, capability in capabilities.items():
        ops = capability["operations"]
        coverage.append(row("FU · "+name, "已映射" if ops else "未知",
                            ", ".join(ops) if ops else "操作类别未解析", capability["evidence"]))

    # Register IDs in IntRD and FpRD belong to separate banks; count physical IDs, not uses.
    rf_ev = source_line(impl, "Scheduler::useRegfilePort(")
    coverage.append(row("寄存器读端口", "已映射" if ports_complete else "未知",
                        "；".join(f"{bank} {len(ids)} 个（{', '.join(map(str,ids))}）"
                                 for bank,ids in model["registerReadPorts"].items()), rf_ev))
    coverage.append(row("寄存器写端口", "未知", "当前 IssuePort.rp 声明读端口；独立写端口连接待核对",
                        source_line(pool,"rp = VectorParam.Int")))
    add_part(module,"ports","发射端口与 FU",f"{port_count} 个已解析出口，按 FU 操作类别选择",source_line(impl,"IssuePort::IssuePort("))
    add_part(module,"rf","寄存器读仲裁",f"{len(module_reads)} 个已定位 bank/端口编号，共享端口按优先级仲裁",rf_ev)
    add_flow(module,"iq","ports","选择端口",source_line(impl,"auto readyQ = readyQs[pi]"),"依据出口的操作类别掩码选择就绪指令。")
    add_flow(module,"ports","rf","申请读端口",source_line(impl,"scheduler->useRegfilePort("),"按源操作数和出口配置的寄存器 bank、端口号与优先级申请读取。")
    add_flow(module,"ports","execute","供给执行",source_line(impl,"Scheduler::getInstToFU("),"调度器向执行阶段提供允许发射的指令。")
    add_wakeup(source, pool, impl, fields, module, model)
    if port_count and ports_complete:
        module["structureCaption"] += f" · {port_count} 个出口"


def add_wakeup(source, pool, impl, fields, module, model):
    names = [q["name"] for group in model["groups"] for q in group["queues"]]
    name_set = set(names)
    channels = fields.get("specWakeupNetwork")
    xbar = fields.get("xbarWakeup")
    default_xbar = assigned_fields(pool.class_named("Scheduler")).get("xbarWakeup")
    xbar_value = xbar or (default_xbar.args[0] if isinstance(default_xbar,ast.Call) and default_xbar.args else None)
    xbar_evidence = (source if xbar else pool).evidence(xbar_value)
    matrix = {}
    unknown = []
    if isinstance(xbar_value, ast.Constant) and xbar_value.value is True:
        matrix = {(a,b):xbar_evidence for a in names for b in names}
        policy = "全部 IQ 交叉互连"
        policy_evidence = xbar_evidence
    elif isinstance(xbar_value, ast.Constant) and xbar_value.value is False and sequence(channels) is not None:
        policy = "显式定向网络"
        policy_evidence = source.evidence(channels)
        for channel in channels.elts:
            if constructor(channel) != "SpecWakeupChannel":
                unknown.append(source.evidence(channel))
                continue
            args = keywords(channel)
            send,receive = iq_names(args.get("srcs"),model,fields),iq_names(args.get("dsts"),model,fields)
            if send is None or receive is None or not set(send+receive) <= name_set:
                unknown.append(source.evidence(channel))
                continue
            for a in send:
                for b in receive:
                    matrix[(a,b)] = source.evidence(channel)
    else:
        policy, policy_evidence = "拓扑未解析", source.evidence(channels)
        unknown.append(policy_evidence)

    routes = [dict(a=a,b=b,evidence=ref) for (a,b),ref in matrix.items()]
    model.update(wakeupRoutes=routes,wakeupPolicy=policy,wakeupComplete=not unknown)
    coverage = module["coverage"]
    coverage.append(row("推测唤醒网络","已映射" if not unknown else "未知",
                        f"{policy} · {len(matrix)} 条已确认有向连接（包含自唤醒）",policy_evidence))
    for a in names:
        targets = [r for r in routes if r["a"]==a]
        coverage.append(row("唤醒源 · "+a,"未知" if unknown else "已映射",
                            ", ".join(r["b"] for r in targets) if targets else ("未知" if unknown else "无发送通道"),
                            targets[0]["evidence"] if targets else policy_evidence))
    add_part(module,"wakeup","推测唤醒",f"{len(routes)} 条已解析源 IQ → 目的 IQ 路由",
             source_line(impl,"Scheduler::specWakeUpDependents("))
    add_flow(module,"ports","wakeup","发布依赖唤醒",source_line(impl,"scheduler->specWakeUpDependents(inst, this)"),
             "满足流水 FU、有目的寄存器等条件时，从生产者所在队列发出推测唤醒。")
    for g in model["groups"]:
        receives = [r for r in routes if any(q["name"]==r["b"] for q in g["queues"])]
        if receives:
            add_flow(module,"wakeup",g["nodeId"].split(".",1)[1],"定向通知",receives[0]["evidence"],
                     f"配置允许 {len(receives)} 个有向队列对通知本组；具体源与目的见唤醒矩阵。")


