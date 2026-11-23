"""Source-backed architecture profile for configs/example/xiangshan.py."""
import ast
import re
from functools import lru_cache
from semantics import relation

ENTRY = "configs/example/xiangshan.py"
CACHE = "configs/common/CacheConfig.py"
OPTIONS = "configs/common/Options.py"
MMU = "src/arch/riscv/RiscvMMU.py"
FETCH = "src/cpu/o3/fetch.cc"
BASE = "src/mem/cache/base.cc"
MODULES = [
 ("bpu","BPU",0,r"branchPred",ENTRY,"test_sys.cpu[i].branchPred = BPClass"),
 ("ftq","FTQ",0,r"ftq","src/cpu/pred/ftb/fetch_target_queue.cc","FetchTargetQueue::"),
 ("ifu","IFU",0,r"fetch",FETCH,"Fetch::fetchCacheLine"),
 ("decode","Decode",1,r"decode","src/cpu/o3/decode.cc","Decode::tick"),
 ("rename","Rename",1,r"rename","src/cpu/o3/rename.cc","Rename::tick"),
 ("issue","Issue / Execute",1,r"iew","src/cpu/o3/iew.cc","IEW::tick"),
 ("commit","Commit",1,r"commit","src/cpu/o3/commit.cc","Commit::tick"),
 ("lsu","LSU / LSQ",2,r"lsq","src/cpu/o3/lsq.cc","LSQ::"),
 ("mmu","MMU",2,r"mmu",MMU,"class RiscvMMU"),
 ("icache","L1 I-Cache",2,r"icache",CACHE,"icache = icache_class"),
 ("dcache","L1 D-Cache",2,r"dcache",CACHE,"dcache = dcache_class"),
 ("l2","L2 Cache",3,r"l2_caches\d*|l2",CACHE,"system.l2_caches ="),
 ("l3","L3 Cache",3,r"l3",CACHE,"system.l3 = L3Cache"),
 ("bus","系统互联",3,r"membus",CACHE,"system.l3.mem_side = system.membus"),
 ("mem","内存控制器",3,r"mem_ctrls\d*","configs/common/MemConfig.py","subsystem.mem_ctrls =")]
FLOWS = [
 ("bpu","ftq","预测目标入队","src/cpu/pred/ftb/decoupled_bpred.cc","fetchTargetQueue.enqueue("),
 ("ftq","ifu","提供取指目标",FETCH,"dbpftb->getSupplyingFetchTarget()"),
 ("ifu","mmu","取指地址翻译",FETCH,"cpu->mmu->translateTiming(first_mem_req"),
 ("mmu","ifu","翻译完成","src/cpu/o3/fetch.hh","fetch->finishTranslation(fault, req)"),
 ("ifu","icache","指令请求",FETCH,"icachePort.sendTimingReq(data_pkt)"),
 ("ifu","decode","发送指令",FETCH,"toDecode->insts[toDecode->size++]"),
 ("decode","rename","送往重命名","src/cpu/o3/decode.cc","toRename->insts[toRename->size++]"),
 ("rename","issue","送往执行","src/cpu/o3/rename.cc","toIEW->insts[toIEWIndex]"),
 ("issue","lsu","分派到访存队列","src/cpu/o3/iew.cc","ldstQueue.insertLoad("),
 ("issue","commit","提交输入","src/cpu/o3/commit.cc","fromIEW->insts"),
 ("icache","l2","经 L2 总线",CACHE,"system.l2_caches[i].cpu_side ="),
 ("dcache","l2","经 L2 总线",CACHE,"system.l2_caches[i].cpu_side ="),
 ("l2","l3","经 L3 总线",CACHE,"system.l2_caches[i].mem_side = system.tol3bus"),
 ("l3","bus","访问系统总线",CACHE,"system.l3.mem_side = system.membus"),
 ("bus","mem","内存请求","configs/common/MemConfig.py","mem_ctrls[i].port = xbar.mem_side_ports")]


def profile(root, options, round_number=10):
    warnings=[]
    @lru_cache(None)
    def lines(file):
        return (root/file).read_text(encoding="utf-8").splitlines() if (root/file).is_file() else []
    def find(file,symbol):
        for i,line in enumerate(lines(file),1):
            if symbol in line and not line.strip().startswith(("#","//")):
                return dict(file=file,line=i,symbol=symbol,text=line.strip())
        warnings.append(f"映射未匹配 {file} · {symbol}")
        return dict(file=file,symbol=symbol,unresolved=True)
    values={}
    for line in lines(OPTIONS):
        if "parser.add_argument(" in line and "default=" in line:
            match=re.search(r'add_argument\("--([^"]+)".*default=(".*?"|None)',line)
            if match:
                values[match[1].replace("-","_")]=(ast.literal_eval(match[2]),find(OPTIONS,line.strip()))
    values.update({k:(v,dict(origin="命令行",key=k)) for k,v in options.items()})
    known={"l1i_size","l1d_size","l2_size","l3_size","bp_type","ideal_kuanglangv1","ruby","xiangshan_ecore","no_l3cache","mem_type"}
    for key in options.keys()-known:
        warnings.append(f"配置选项 {key} 的架构影响未解析")
    bp=values.get("bp_type",(None,None))[0]
    predictor={"DecoupledBPUWithBTB":"btb","DecoupledBPUWithFTB":"ftb",None:"ftb"}.get(bp)
    modules=[]
    edges=[]
    disabled=set()
    if options.get("no_l3cache"):
        disabled.add("l3")
    if options.get("ruby"):
        disabled.update(("icache","dcache","l2","l3","bus","mem"))
        warnings.append("Ruby 配置需要专用缓存映射")
    for uid,name,band,selector,file,symbol in MODULES:
        if uid in disabled:
            continue
        if uid=="ftq" and predictor=="btb":
            file=file.replace("/ftb/","/btb/")
        ev=find(file,symbol)
        if ev.get("unresolved"):
            continue
        params={}
        if uid=="bpu":
            params["预测器"]=dict(default=find("src/cpu/o3/BaseO3CPU.py","branchPred = Param."),override=find(ENTRY,"BPClass = DecoupledBPU"),
                               dynamic=find(ENTRY,"ObjectList.bp_list.get(args.bp_type)"),
                               selection=values.get("bp_type"),value=(bp or "DecoupledBPUWithFTB") if predictor else None)
        if uid in ("icache","dcache","l2","l3"):
            key={"icache":"l1i","dcache":"l1d"}.get(uid,uid)+"_size"
            val,src=values.get(key,(None,None))
            if uid=="l2" and options.get("xiangshan_ecore") and options.get("no_l3cache"):
                val,src="4MB",find(ENTRY,"args.l2_size =")
            if options.get("ideal_kuanglangv1") and uid in ("icache","dcache","l2"):
                symbol={"icache":"cpu.icache.size =", "dcache":"cpu.dcache.size =", "l2":"system.l2_caches[i].size ="}[uid]
                src=find(ENTRY,symbol)
                val=ast.literal_eval(src["text"].split("=",1)[1].strip()) if "text" in src else None
            cache_class={"icache":"L1_ICache","dcache":"L1_DCache","l2":"L2Cache","l3":"L3Cache"}[uid]
            params["容量"]=dict(value=val,override=src,cacheClass=find("configs/common/Caches.py","class "+cache_class+"("))
        modules.append(dict(id=uid,name=name,band=band,selector=selector,evidence=ev,parameters=params))
    from zenas_details import detail, bind_scenarios
    active = {m["id"] for m in modules}
    llc = "l2" if options.get("no_l3cache") else "l3"
    for m in modules:
        detail(m, find, active, predictor, values.get("mem_type", ("DRAMsim3",))[0], llc, round_number)
    flows=list(FLOWS)
    flows.extend([
        ("icache","ifu","返回取指数据",FETCH,"fetch->processCacheCompletion(pkt)"),
        ("lsu","mmu","访存地址翻译","src/cpu/o3/lsq.cc","_port.getMMUPtr()->translateTiming("),
        ("mmu","lsu","访存翻译完成","src/cpu/o3/lsq.cc","LSQ::SingleDataRequest::finish("),
        ("lsu","dcache","请求数据缓存","src/cpu/o3/lsq_unit.cc","dcachePort->sendTimingReq(data_pkt)"),
        ("dcache","lsu","返回加载数据","src/cpu/o3/lsq_unit.cc","LSQUnit::recvTimingResp("),
        ("l2","dcache","返回 L1 缓存行",BASE,"BaseCache::MemSidePort::recvTimingResp("),
        ("l3","l2","返回 L2 缓存行",BASE,"BaseCache::MemSidePort::recvTimingResp("),
        ("bus","l3","返回 LLC 数据","src/mem/coherent_xbar.cc","cpuSidePorts[cpu_side_port_id]->schedTimingResp("),
    ])
    if values.get("mem_type", ("DRAMsim3",))[0] == "DRAMsim3":
        flows.append(("mem","bus","DRAM 响应","src/mem/dramsim3.cc","bool success = port.sendTimingResp(pkt)"))
    if "l3" in disabled:
        flows.append(("bus","l2","返回私有 L2 数据","src/mem/coherent_xbar.cc","cpuSidePorts[cpu_side_port_id]->schedTimingResp("))
        flows.append(("l2","bus","直连系统总线",CACHE,"system.l2_caches[i].mem_side = system.membus"))
    for a,b,label,file,symbol in flows:
        if a not in active or b not in active:
            continue
        if a in ("bpu","ftq"):
            if not predictor:
                warnings.append(f"{a} → {b}: 动态预测器，路径未确认")
                continue
            if predictor=="btb":
                file=file.replace("/ftb/","/btb/")
                symbol=symbol.replace("dbpftb","dbpbtb")
        ev=find(file,symbol)
        if not ev.get("unresolved"):
            edges.append(relation("logical-flow",a,b,label,ev))
    # Keep unevaluated configuration assignments with their enclosing conditions.
    overrides=[]
    tree=ast.parse("\n".join(lines(ENTRY)))
    def collect(node, conditions):
        if isinstance(node, ast.If):
            condition=ast.unparse(node.test)
            for items,branch in [(node.body,condition),(node.orelse,"not ("+condition+")")]:
                for item in items:
                    collect(item,conditions+[branch])
            return
        if isinstance(node,ast.Assign):
            for target in node.targets:
                target_name=ast.unparse(target)
                if isinstance(target,(ast.Attribute,ast.Subscript)):
                    overrides.append(dict(target=target_name,value=ast.unparse(node.value),
                        conditions=conditions,status="静态赋值证据，索引及动态值待实例核对",
                        evidence=dict(file=ENTRY,line=node.lineno,text=lines(ENTRY)[node.lineno-1].strip())))
        for item in ast.iter_child_nodes(node):
            collect(item,conditions)
    collect(tree,[])
    # Each event follows the direction of its own verified edge (including replies).
    scenarios = bind_scenarios(modules, edges, [
        ("fetch", "取指目标、翻译与读取", "bpu ftq ifu mmu ifu icache"),
        ("commit", "从取指到退休入口", "bpu ftq ifu mmu ifu icache ifu decode rename issue commit"),
        ("load", "Load 翻译与数据返回", "issue lsu mmu lsu dcache lsu"),
        ("miss", "数据缓存缺失与回填", "lsu dcache l2 l3 bus mem bus l3 l2 dcache lsu"),
        ("direct-miss", "数据缓存缺失 · 无 L3", "lsu dcache l2 bus mem bus l2 dcache lsu"),
    ])
    view = dict(scenarios=scenarios,overrides=overrides,id="xiangshan.overview",source=ENTRY,cpu=find(ENTRY,"TestCPUClass = huanjianV1Core"),
                modules=modules,edges=edges,demo=[e["id"] for e in edges if (e["a"],e["b"]) in
                [(a,b) for a,b,*_ in FLOWS[:5]]],warnings=warnings)


    if round_number >= 1:
        from backend_structure import enrich
        enrich(root, options, view, round_number)
    if round_number >= 4:
        from front_structure import enrich
        enrich(root, options, view, round_number)
    if round_number >= 7:
        from memory_structure import enrich
        enrich(root, options, view, round_number)
    if round_number >= 9:
        from replay_audit import audit_scenes
        audit_scenes(view)
    for module in modules:
        summary = next((r for r in module.get("coverage", []) if r["label"] == "内部组件"), None)
        if summary:
            names = [part["name"] for part in module["parts"] if part.get("role") == "internal"]
            summary.update(value="、".join(names) or "未提取", status="已映射" if names else "未知")
    return view
