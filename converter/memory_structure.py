"""Source-backed queue, cache hierarchy and conditional fetch features."""
import ast
from functools import lru_cache

from front_structure import Source, part, connect, scenarios

ENTRY = "configs/example/xiangshan.py"
BASE = "src/cpu/o3/BaseO3CPU.py"
CACHES = "configs/common/Caches.py"
CACHE_CONFIG = "configs/common/CacheConfig.py"
MEM_CONFIG = "configs/common/MemConfig.py"
OPTIONS = "configs/common/Options.py"
CACHE_IMPL = "src/mem/cache/base.cc"
UNIT = "src/cpu/o3/lsq_unit.cc"
FETCH = "src/cpu/o3/fetch.cc"
UNKNOWN = object()


def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return UNKNOWN


def predicate(node, options):
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "args":
        return options.get(node.attr, UNKNOWN)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        result = predicate(node.operand, options)
        return UNKNOWN if result is UNKNOWN else not result
    if isinstance(node, ast.BoolOp):
        values = [predicate(n, options) for n in node.values]
        if isinstance(node.op, ast.Or):
            return True if True in values else UNKNOWN if UNKNOWN in values else False
        return False if False in values else UNKNOWN if UNKNOWN in values else True
    if isinstance(node, ast.Compare) and len(node.ops) == 1:
        a, b = predicate(node.left, options), predicate(node.comparators[0], options)
        if a is not UNKNOWN and b is not UNKNOWN:
            if isinstance(node.ops[0], (ast.Eq, ast.Is)):
                return a == b
            if isinstance(node.ops[0], (ast.NotEq, ast.IsNot)):
                return a != b
    return literal(node)


class PythonSource:
    def __init__(self, root, file):
        self.file = file
        try:
            text = (root / file).read_text(encoding="utf-8-sig")
            self.tree = ast.parse(text, filename=file)
            self.lines = text.splitlines()
        except (OSError, SyntaxError, UnicodeError):
            self.tree = ast.Module(body=[], type_ignores=[])
            self.lines = []
        self.parents = {child: parent for parent in ast.walk(self.tree) for child in ast.iter_child_nodes(parent)}

    def evidence(self, node):
        return dict(file=self.file, line=node.lineno, endLine=node.end_lineno,
                    text="\n".join(self.lines[node.lineno-1:node.end_lineno]).strip())

    def default(self, clsname, field):
        cls = next((n for n in self.tree.body if isinstance(n, ast.ClassDef) and n.name == clsname), None)
        if not cls:
            return UNKNOWN, None
        for s in cls.body:
            if isinstance(s, ast.Assign) and any(isinstance(t, ast.Name) and t.id == field for t in s.targets):
                expr = s.value
                if isinstance(expr, ast.Call) and ast.unparse(expr.func).startswith("Param.") and len(expr.args)>1:
                    expr = expr.args[0]
                return literal(expr), self.evidence(s)
        return UNKNOWN, None

    def conditions(self, node):
        result = []
        while node in self.parents:
            child, node = node, self.parents[node]
            if isinstance(node, ast.If):
                if "__m5_main__" in ast.unparse(node.test):
                    continue
                result.append(ast.UnaryOp(ast.Not(),node.test) if child in node.orelse else node.test)
        return result[::-1]

    def ideal(self):
        # Follow the guarded call at the entry point and then any nested predictor/cache guards.
        call = next((s for s in ast.walk(self.tree) if isinstance(s, ast.Call) and
                     isinstance(s.func,ast.Name) and s.func.id == "setkuanglangv1IdealParams"), None)
        if not call:
            return {}
        named = next((s for s in self.tree.body if isinstance(s, ast.FunctionDef) and s.name == call.func.id), None)
        values = {}
        if named:
            outer = self.conditions(call)
            for s in sorted((s for s in ast.walk(named) if isinstance(s,ast.Assign)),key=lambda s:s.lineno):
                guards = outer + self.conditions(s)
                values.setdefault(ast.unparse(s.targets[0]),[]).append((literal(s.value),self.evidence(s),guards))
        return values

    def arguments(self):
        result = {}
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Call) or not ast.unparse(node.func).endswith(".add_argument"):
                continue
            flags = [a.value for a in node.args if isinstance(a, ast.Constant) and
                     isinstance(a.value,str) and a.value.startswith("--")]
            if not flags:
                continue
            kw = {k.arg:k.value for k in node.keywords}
            key = literal(kw["dest"]) if "dest" in kw else flags[0][2:].replace("-","_")
            if "default" in kw:
                value = literal(kw["default"])
            else:
                value = {"store_true":False,"store_false":True}.get(literal(kw.get("action")), None)
            result[key] = (value,self.evidence(node))
        return result


def row(module,label,value,ev,origin="源码结构",status="已映射",**extra):
    if module is None:
        return
    if value is UNKNOWN:
        status, value = "未知", None
    module.setdefault("coverage",[]).append(dict(label=label,value=value,evidence=ev or {},origin=origin,status=status,**extra))


def option_settings(arguments, settings, entry):
    opts = {key:value for key,(value,_) in arguments.items()}
    opts.update(settings)
    # The classic system builder turns on cache options even when argparse starts them at false.
    for node in ast.walk(entry.tree):
        if not isinstance(node,ast.For) or not isinstance(node.iter,ast.List):
            continue
        names = literal(node.iter)
        if names is UNKNOWN or not any(isinstance(call,ast.Call) and
                ast.unparse(call.func)=="setattr" and len(call.args)==3 and
                ast.unparse(call.args[1])==ast.unparse(node.target) and literal(call.args[-1]) is True
                for call in ast.walk(node)):
            continue
        if opts.get("ruby"):
            continue
        for k in names:
            if k in ("caches","l2cache") or (k=="l3cache" and not opts.get("no_l3cache")):
                opts[k]=True
    return opts


def param(module,label,key,owner,default,target,ideal,options,base_origin="源码默认"):
    value, ev = default
    origin = base_origin
    alternatives = []
    for variant,evidence,guards in ideal.get(target,[]):
        condition = " 且 ".join(ast.unparse(g) for g in guards)
        evaluated = [predicate(g,options) for g in guards]
        active = False if False in evaluated else UNKNOWN if UNKNOWN in evaluated else True
        if active is not False:
            value,ev,origin = variant if active is True else UNKNOWN,evidence,"配置覆盖"
        alternatives.append(dict(value=None if variant is UNKNOWN else variant,condition=condition,evidence=evidence))
    row(module,label,value,ev,origin,runtime={"owner":owner,"key":key},
        defaultValue=None if default[0] is UNKNOWN else default[0],
        defaultEvidence=default[1],overrides=alternatives)
    for alternative in alternatives:
        row(module,label+" · 条件配置",alternative["value"],alternative["evidence"],"配置覆盖",
            status="条件启用",condition=alternative["condition"])
    return value


def structural(module,label,value,evidence,**extra):
    row(module,label,value if evidence else UNKNOWN,evidence,**extra)


def enrich(root, settings, view, round_number=10):
    if round_number < 7:
        return
    modules = {m["id"]:m for m in view["modules"]}
    py = lru_cache(None)(lambda file: PythonSource(root,file))
    src = lru_cache(None)(lambda file: Source(root,file))
    entry = py(ENTRY)
    ideal = entry.ideal()
    arguments = py(OPTIONS).arguments()
    opts = option_settings(arguments,settings,entry)
    cpu = py(BASE)
    for uid,label,key in (("commit","ROB 容量","numROBEntries"),("lsu","LQ 容量","LQEntries"),
                         ("lsu","SQ 容量","SQEntries"),("lsu","Store Buffer 容量","SbufferEntries"),
                         ("lsu","Store Buffer 排出阈值","SbufferEvictThreshold"),
                         ("lsu","Load miss 重放","EnableLdMissReplay"),("lsu","Store 写回级","StoreWbStage")):
        param(modules.get(uid),label,key,"cpu",cpu.default("BaseO3CPU",key),"cpu."+key,ideal,opts)

    cache_defs = py(CACHES)
    for uid, option, cls, owner, target in (
            ("icache","l1i","L1_ICache","cpu.icache","cpu.icache"),
            ("dcache","l1d","L1_DCache","cpu.dcache","cpu.dcache"),
            ("l2","l2","L2Cache","system.l2_caches","system.l2_caches[i]"),
            ("l3","l3","L3Cache","system.l3","system.l3")):
        m = modules.get(uid)
        if not m:
            continue
        size_key = option+"_size"
        size,ev = arguments.get(size_key,(UNKNOWN,None))
        if size_key in settings:
            size = settings[size_key]
        base_origin = "配置覆盖" if size_key in settings else "源码默认"
        if uid=="l2" and opts.get("no_l3cache") and opts.get("xiangshan_ecore"):
            for node in ast.walk(entry.tree):
                if isinstance(node,ast.Assign) and ast.unparse(node.targets[0])=="args.l2_size":
                    guards=entry.conditions(node)
                    # The classic builder is selected before applying the optional ideal profile.
                    if any("args.xiangshan_ecore" in ast.unparse(g) and "args.no_l3cache" in ast.unparse(g) for g in guards):
                        size,ev,base_origin=literal(node.value),entry.evidence(node),"配置覆盖"
        size = param(m,"缓存容量","size",owner,(size,ev),target+".size",ideal,opts,base_origin)
        old = m["parameters"].get("容量")
        if old:
            old["value"] = None if size is UNKNOWN else size
            old["override"] = next(r["evidence"] for r in m["coverage"] if r["label"]=="缓存容量")
        for label,key in (("MSHR 数量","mshrs"),("缺失目标保留","demand_mshr_reserve")):
            decl = cache_defs.default(cls,key)
            if decl[1] or target+"."+key in ideal:
                param(m,label,key,owner,decl,target+"."+key,ideal,opts)
        base = src(CACHE_IMPL)
        merge = base.find(r'mshr->allocateTarget\(pkt,\s*forward_time,\s*order\+\+')
        part(m,"merge","同一缓存行缺失合并","已有 MSHR 接纳同一行的后续请求目标",merge)
        connect(m,"tags","merge","已存在对应行 MSHR 时合并目标",merge)
        connect(m,"merge","reply","缓存行到达后服务合并目标",base.find(r'serviceMSHRTargets\(mshr,\s*pkt,\s*blk\)'))
        scenarios(m,[("coalesced","在途缓存行的第二个读请求","up tags merge reply up")])
        structural(m,"返回端口","mem_side.recvTimingResp → cache.recvTimingResp",base.find(r'cache->recvTimingResp\(pkt\)'))

    unit=src(UNIT)
    lsu=modules.get("lsu")
    if lsu:
        forward=unit.find(r'entry->recordForward\(request->mainReq\(\),\s*request\)')
        part(lsu,"forward","Store Buffer 转发","按缓存行和字节覆盖匹配加载",forward)
        connect(lsu,"sb","forward","使用缓冲写数据填入当前加载请求",forward)
        structural(lsu,"LSQ 响应","DCache 响应按 Packet 的 LSQRequest 完成",
                   src("src/cpu/o3/lsq.cc").find(r'_port\.completeDataAccess\(mainPacket\(\)\)'))
    l2=modules.get("l2")
    if l2:
        config=src(CACHE_CONFIG)
        wiring=src("src/cpu/BaseCPU.py")
        walker=src("src/arch/riscv/RiscvMMU.py")
        assign=config.find(r'walk_cache_class\s*=\s*PageTableWalkerCache\b')
        attach=wiring.find(r'self\.mmu\.connectWalkerPorts\(\s*iwc\.cpu_side,\s*dwc\.cpu_side\)')
        base_cpu=py("src/cpu/BaseCPU.py")
        walker_outputs=next((base_cpu.evidence(n) for n in ast.walk(base_cpu.tree) if isinstance(n,ast.AugAssign)
                        and ast.unparse(n.target)=="self._cached_ports" and literal(n.value)==
                        ["itb_walker_cache.mem_side","dtb_walker_cache.mem_side"]),None)
        bind_ports=next((base_cpu.evidence(fn) for cls in base_cpu.tree.body if isinstance(cls,ast.ClassDef)
                    for fn in cls.body if isinstance(fn,ast.FunctionDef) and fn.name=="connectCachedPorts"),None)
        downstream=config.find(r'connectAllPorts\(\s*system\.tol2bus_list\[i\]\.cpu_side_ports')
        endpoint=config.find(r'system\.l2_caches\[i\]\.cpu_side\s*=\s*system\.tol2bus_list\[i\]\.mem_side_ports')
        for side,cache_id in (("itb","iwalkcache"),("dtb","dwalkcache")):
            binding=walker.find(r'self\.'+side+r'\.walker\.port\s*=')
            construct=config.find(cache_id+r'\s*=\s*walk_cache_class\(\)')
            chain=[binding,assign,construct,attach,walker_outputs,bind_ports,downstream,endpoint]
            confirmed=all(chain)
            structural(l2,side.upper()+" walker 连接",f"{side}.walker.port → {side}_walker_cache.cpu_side",attach if confirmed else None,
                       evidenceChain=[v for v in chain if v])
            if confirmed:
                part(l2,cache_id,side.upper()+" 页表缓存","页表缓存未命中经 tol2bus 请求 L2",construct,"mmu","up")
                connect(l2,cache_id,"tags","通过 tol2bus 的 mem_side 端进入 L2",endpoint)
                connect(l2,"reply",cache_id,"L2 响应由总线送回原页表缓存端口",
                        src("src/mem/coherent_xbar.cc").find(r'cpuSidePorts\[cpu_side_port_id\]->schedTimingResp\('))
                scenarios(l2,[(side+"-ptw","页表缓存未命中、L2 命中 · "+side.upper(),
                               f"{cache_id} tags reply {cache_id}")])

    bus=modules.get("bus")
    if bus:
        xbar=src("src/mem/coherent_xbar.cc")
        structural(bus,"请求侧端口记录","以请求指针保存响应目的端",xbar.find(r'routeTo\[pkt->req\]\s*=\s*cpu_side_port_id'))
        structural(bus,"响应侧查找","使用请求指针定位返回端口",xbar.find(r'const auto route_lookup\s*=\s*routeTo\.find\(pkt->req\);'))
        structural(bus,"内存连接","mem_ctrls[i].port ← membus.mem_side_ports",
                   src(MEM_CONFIG).find(r'mem_ctrls\[i\]\.port\s*=\s*xbar\.mem_side_ports'),
                   condition="普通系统总线；HMC 有独立 xbar 分支")
    mem=modules.get("mem")
    if mem:
        typ=opts.get("mem_type",UNKNOWN)
        row(mem,"内存模型",typ,arguments.get("mem_type",(None,None))[1],
            "配置覆盖" if "mem_type" in settings else "源码默认")
        file_assignment=src(MEM_CONFIG).find(r'dram_intf\.configFile\s*=\s*opt_dramsim3_ini')
        if typ=="DRAMsim3":
            filename=opts.get("dramsim3_ini") or UNKNOWN
            source_ev=file_assignment
            source_origin="配置覆盖" if filename is not UNKNOWN else "源码结构"
            if filename is UNKNOWN:
                setup=py("configs/common/XSConfig.py")
                for item in ast.walk(setup.tree):
                    if not isinstance(item,ast.Assign) or ast.unparse(item.targets[0])!="args.dramsim3_ini":
                        continue
                    expr=item.value
                    if isinstance(expr,ast.Call) and ast.unparse(expr.func)=="os.path.join" and len(expr.args)==2 and ast.unparse(expr.args[0])=="root_dir":
                        path=literal(expr.args[1])
                        if isinstance(path,str) and (root/path).is_file():
                            filename,source_ev,source_origin=path,setup.evidence(item),"配置覆盖"
            row(mem,"DRAM 时序配置文件",filename,source_ev,source_origin,
                runtime={"owner":"system.mem_ctrls","key":"configFile"},
                evidenceChain=[v for v in (source_ev,file_assignment) if v],condition="选择 DRAMsim3；未提供 ini 时使用配置入口给出的文件")
            dram=src("src/mem/dramsim3.cc")
            retry=dram.find(r'retryReq\s*=\s*true;')
            wake=dram.find(r'port\.sendRetryReq\(\)')
            part(mem,"retry","请求重试","占用上限解除后通知请求方重发",retry)
            connect(mem,"port","retry","本次请求未被接收，设置待重试状态",retry)
            connect(mem,"retry","bus","队列有空间时发送重试通知",wake)
            scenarios(mem,[("backpressure","DRAM 请求受阻与重试通知","bus port retry bus")])
        else:
            row(mem,"后端事务时序",UNKNOWN,src(MEM_CONFIG).find(r'ObjectList\.mem_list\.get\(opt_mem_type\)'),
                condition="需按有效内存类型绑定其 C++ 后端")
    if round_number >= 8:
        conditional_features(root, modules, opts, ideal, cpu, src)


def conditional_features(root,modules,options,ideal,cpu,src):
    ifu = modules.get("ifu")
    if not ifu:
        return
    fetch = src(FETCH)
    declared = cpu.default("BaseO3CPU","enableFetchResidentWindowReplay")
    implementation = fetch.find(r'Fetch::findFetchResidentWindow\s*\(')
    main_class = next((n for n in cpu.tree.body if isinstance(n,ast.ClassDef) and n.name=="BaseO3CPU"), None)
    if not declared[1] and not implementation:
        # A missing declaration alone is inconclusive if either input file could not be read.
        observed = main_class is not None and bool(fetch.lines)
        ev = dict(file=BASE,line=main_class.lineno,text=cpu.lines[main_class.lineno-1]) if main_class else None
        row(ifu,"resident window replay","无对应声明与实现" if observed else UNKNOWN,ev,
            status="缺失",scopeFiles=[BASE,FETCH],condition="检查 BaseO3CPU 类体及 Fetch 实现")
        return

    values = {}
    for label,key in (("resident window replay","enableFetchResidentWindowReplay"),
                      ("resident window probe","enableFetchResidentWindowProbe"),
                      ("resident window count","fetchResidentWindowCount"),
                      ("双 FTQ 目标取指","enableTwoFetch")):
        values[key] = param(ifu,label,key,"cpu",cpu.default("BaseO3CPU",key),"cpu."+key,ideal,options)
    guards = [{"owner":"cpu","key":"enableFetchResidentWindowReplay","value":True},
              {"owner":"cpu","key":"enableTwoFetch","value":True},
              {"owner":"cpu.branchPred","key":"type","value":"DecoupledBPUWithBTB"}]
    enabled = (values["enableFetchResidentWindowReplay"] is True and values["enableTwoFetch"] is True
               and options.get("bp_type")=="DecoupledBPUWithBTB")
    lookup = fetch.find(r'state\.table\.findCovering\(startPC,\s*endPC\)')
    retain = fetch.find(r'state\.table\.insert\(fetchBuffer\[tid\]\.data,')
    activation = fetch.find(r'state\.active\.activateFrom\(\*window,\s*identity,\s*curTick\(\)\)')
    data = fetch.find(r'memcpy\(dec_ptr->moreBytesPtr\(\),\s*active\.data\.data\(\)\s*\+\s*offset_in_window,\s*4\)')
    identity = fetch.find(r'window->epoch\s*!=\s*state\.epoch\s*\|\|\s*window->contextId\s*!=\s*cpu->thread\[tid\]->contextId\(\)')
    gate = fetch.find(r'assert\(enableTwoFetch\s*&&\s*isBTBPred\(\)\s*&&\s*usedUpFetchTargets\)')
    thread_guard = fetch.find(r'!isBTBPred\(\)\s*\|\|\s*numThreads\s*!=\s*1\s*\|\|\s*numFetchingThreads\s*!=\s*1')
    way_guard = fetch.find(r'fetchResidentWindowCount\s*>\s*FetchResidentWindowMaxWays')
    structural(ifu,"双目标取指的构造约束","单硬件线程、单取指线程、BTB 预测器",thread_guard)
    structural(ifu,"驻留窗口容量约束","重放开启时窗口数须在 1 到 FetchResidentWindowMaxWays 之间",way_guard)
    condition = "在有效的单线程 BTB 双目标配置上启用重放，主缓冲未完整覆盖，下一个目标命中有效驻留窗口"
    if not all((declared[1],implementation,lookup,retain,activation,data,identity,gate)):
        row(ifu,"驻留窗口数据通路",UNKNOWN,implementation,condition=condition)
        return
    row(ifu,"驻留窗口数据通路",enabled,gate,status="条件启用",condition=condition,
        evidenceChain=[retain,lookup,identity,activation,data],requiresRuntime=guards)
    existing = {p["id"] for p in ifu["parts"]}
    part(ifu,"resident","Resident byte window","保存先前已接纳的取指字节，并按范围、epoch 与上下文匹配",retain)
    part(ifu,"snapshot","Active snapshot","将命中窗口复制为当前 FTQ 目标专属快照",activation)
    part(ifu,"replayBytes","Decoder bytes","从有效快照取出四字节并交给 decoder",data)
    connect(ifu,"buffer","resident","接纳缓存返回后记录取指字节窗口",retain)
    connect(ifu,"resident","snapshot","第二取指目标完整命中且身份有效时激活快照",activation)
    connect(ifu,"snapshot","replayBytes","向 decoder 请求缓冲复制四字节",data)
    scenarios(ifu,[("resident-replay","驻留窗口命中与解码供给","buffer resident snapshot replayBytes")])
    for part_record in ifu["parts"]:
        if part_record["id"] not in existing:
            part_record.update(sourceEnabled=enabled,requiresRuntime=guards,condition=condition)
    for edge in ifu["internalEdges"]:
        if edge["a"] not in existing or edge["b"] not in existing:
            edge.update(sourceEnabled=enabled,requiresRuntime=guards,condition=condition)
    for scene in ifu["scenarios"]:
        if scene["id"]=="ifu.resident-replay":
            scene.update(sourceEnabled=enabled,requiresRuntime=guards,condition=condition)

