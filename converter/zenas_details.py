"""Bind semantic replay paths to concrete directed links in the selected XS model.

A recipe is an ordered list of endpoint roles. A graph emits the whole scenario
only if every requested endpoint and directed edge has verified source evidence.
"""
from semantics import relation

O3 = "src/cpu/o3/"
FETCH = O3+"fetch.cc"
DECODE = O3+"decode.cc"
RENAME = O3+"rename.cc"
IEW = O3+"iew.cc"
COMMIT = O3+"commit.cc"
LSQ = O3+"lsq.cc"
UNIT = O3+"lsq_unit.cc"
BASE = "src/mem/cache/base.cc"
MMU = "src/arch/riscv/RiscvMMU.py"
WALK = "src/arch/riscv/pagetable_walker.cc"
TLB = "src/arch/riscv/tlb.cc"
XBAR = "src/mem/coherent_xbar.cc"
DRAM = "src/mem/dramsim3.cc"


def bind_scenarios(parts, edges, recipes, prefix=""):
    ids = {p["id"] for p in parts if not p.get("evidence", {}).get("unresolved")}
    pairs = {}
    for edge in edges:
        if not edge.get("evidence", {}).get("unresolved"):
            pair = (edge["a"], edge["b"])
            # A role-only template cannot choose between parallel directed links.
            pairs[pair] = None if pair in pairs else edge
    result = []
    for key, title, path in recipes:
        nodes = [prefix + role for role in path.split()]
        if not set(nodes) <= ids:
            continue
        steps = []
        for pair in zip(nodes, nodes[1:]):
            edge = pairs.get(pair)
            if edge is None:
                break
            steps.append(dict(edgeId=edge["id"], a=edge["a"], b=edge["b"],
                              type=edge.get("eventType", edge["label"]),
                              text=edge.get("description", edge["label"])))
        else:
            if steps:
                result.append(dict(id=prefix+key, name=title, steps=steps))
    return result


def detail(module, find, active, predictor, mem_type, llc, round_number=0):
    uid = module["id"]
    parts, edges, recipes = [], [], []
    prefix = uid + "."

    def node(key, name, description, file, symbol, role="internal", target=None):
        if target and target not in active:
            return
        ev = find(file, symbol)
        if not ev.get("unresolved"):
            part = dict(id=prefix+key, name=name, description=description, role=role, evidence=ev)
            if target:
                part["target"] = target
            parts.append(part)

    def link(a, b, kind, action, file, symbol):
        ids = {part["id"] for part in parts}
        if prefix+a not in ids or prefix+b not in ids:
            return
        ev = find(file, symbol)
        if not ev.get("unresolved"):
            edges.append(relation("logical-flow", prefix+a, prefix+b, action, ev,
                                  eventType=kind, description=action))

    def scene(key, title, path):
        recipes.append((key, title, path))

    if uid in ("bpu", "ftq") and predictor:
        predfile = "src/cpu/pred/"+predictor+"/decoupled_bpred.cc"
        queue = predfile.replace("decoupled_bpred", "fetch_target_queue")
        get_target = "dbp"+predictor+"->getSupplyingFetchTarget()"
        if uid == "bpu":
            node("history","PC / History","预测起始地址与推测历史",predfile,"components[i]->putPCHistory(")
            node("banks","预测组件","各级查询同一块的地址与历史",predfile,"components[i]->putPCHistory(")
            node("select","Override","收集预测级结果并计算覆盖气泡",predfile,"::generateFinalPredAndCreateBubbles()")
            node("fsq","Fetch Stream Queue","保存已生成的预测流",predfile,"fetchStreamQueue.emplace(")
            node("ftq","FTQ","接收由预测流生成的目标块",predfile,"fetchTargetQueue.enqueue(","down","ftq")
            link("history","banks","查询","传入起始 PC 和历史，写入各级候选预测",predfile,"components[i]->putPCHistory(")
            link("banks","select","选择","合并预测结果并计算覆盖气泡",predfile,"numOverrideBubbles = generateFinalPredAndCreateBubbles();")
            link("select","fsq","入队","用最终预测构建流并写入 FSQ",predfile,"fetchStreamQueue.emplace(")
            link("fsq","ftq","供给","将预测流中的目标块写入 FTQ",predfile,"fetchTargetQueue.enqueue(")
            scene("predict","预测流生成与供给","history banks select fsq ftq")
            for key, title, filename, purpose in [
                (predictor, predictor.upper(), predictor+".cc", "分支位置与目标"),
                ("tage", "TAGE", predictor+"_tage.cc", "条件分支方向"),
                ("ittage", "ITTAGE", predictor+"_ittage.cc", "间接跳转目标"),
                ("ras", "RAS", "ras.cc", "调用返回地址"),
            ]:
                component = "src/cpu/pred/"+predictor+"/"+filename
                # Registration proves participation; method presence alone is insufficient.
                node(key, title, purpose, predfile, "components.push_back("+key+")")
                link("banks", key, "查询", "分发同一 PC 与历史查询，聚焦"+title, component, "::putPCHistory(")
                link(key, "select", "候选", "本次查询贡献"+purpose+"预测，参与各级结果选择", predfile,
                     "numOverrideBubbles = generateFinalPredAndCreateBubbles();")
                scene("via-"+key, title+" 对预测的贡献", "history banks "+key+" select fsq ftq")

        else:
            node("bpu","BPU","输入预测目标",predfile,"fetchTargetQueue.enqueue(","up","bpu")
            node("entries","FTQ entries","按目标编号保存预测块",queue,"FetchTargetQueue::enqueue(")
            node("demand","Demand cursor","使用 fetchDemandTargetId 查找队项",queue,"auto it = ftq.find(fetchDemandTargetId)")
            node("supply","Supply buffer","保留本次供给的目标编号与队项指针",queue,"supplyFetchTargetState.entry = &(it->second)")
            node("ifu","IFU","读取目标块提供的地址",FETCH,get_target,"down","ifu")
            link("bpu","entries","入队","接受一个预测目标块",predfile,"fetchTargetQueue.enqueue(")
            link("entries","demand","查找","以需求游标匹配目标队项",queue,"auto it = ftq.find(fetchDemandTargetId)")
            link("demand","supply","供给","将命中项填入供给状态",queue,"supplyFetchTargetState.entry = &(it->second)")
            link("supply","ifu","取出","取指端取得当前供给目标",FETCH,get_target)
            scene("supply","预测块供给","bpu entries demand supply ifu")

    if uid == "ifu":
        get_target="dbp"+(predictor or "ftb")+"->getSupplyingFetchTarget()"
        if predictor:
            node("ftq","FTQ","当前预测目标",FETCH,get_target,"up","ftq")
        node("req","Fetch request","按取指块地址构造请求",FETCH,"RequestPtr first_mem_req =")
        node("mmu","MMU","Execute 地址翻译",FETCH,"translateTiming(first_mem_req","down","mmu")
        node("port","ICache port","翻译完成后构造读取包",FETCH,"Fetch::finishTranslation(")
        node("icache","L1 I-Cache","接收物理地址读取请求",FETCH,"icachePort.sendTimingReq(data_pkt)","down","icache")
        node("buffer","取指缓冲","消费返回的指令字节",FETCH,"Fetch::processCacheCompletion(")
        node("decode","Decode","接收动态指令",FETCH,"toDecode->insts[toDecode->size++]","down","decode")
        link("ftq","req","供给","使用预测块起始地址构造指令请求",FETCH,get_target)
        link("req","mmu","翻译","向 MMU 提交 Execute 翻译",FETCH,"translateTiming(first_mem_req")
        link("mmu","port","回调","翻译完成后交回取指请求",O3+"fetch.hh","fetch->finishTranslation(fault, req)")
        link("port","icache","读取","发送指令缓存读包",FETCH,"icachePort.sendTimingReq(data_pkt)")
        link("icache","buffer","返回","处理返回的取指数据",FETCH,"fetch->processCacheCompletion(pkt)")
        link("buffer","decode","传递","向 Decode 缓冲写入已构造的动态指令",FETCH,"toDecode->insts[toDecode->size++]")
        scene("fetch","目标块到动态指令","ftq req mmu port icache buffer decode")
        scene("read","指令缓存请求与返回","port icache buffer")

    if uid == "decode":
        node("ifu","IFU","输入动态指令",DECODE,"const DynInstPtr &inst = fromFetch->insts[i]","up","ifu")
        node("window","译码队列","按线程取出待译码项",DECODE,"insts_to_decode.pop()")
        node("check","控制流检查","核对分支类型、预测方向和直接目标",DECODE,"if (inst->isDirectCtrl()")
        node("rename","Rename","接收译码结果",DECODE,"toRename->insts[toRename->size++]","down","rename")
        node("redirect","Fetch redirect","通知前端改用修正地址",DECODE,"toFetch->decodeInfo[tid].nextPC","down","ifu")
        link("ifu","window","入队","按线程接收 Fetch 的指令",DECODE,"const DynInstPtr &inst = fromFetch->insts[i]")
        link("window","check","检查","从窗口取指令并校验控制流",DECODE,"DynInstPtr inst = std::move(insts_to_decode.front())")
        link("check","rename","传递","通过检查后送往重命名",DECODE,"toRename->insts[toRename->size++]")
        link("check","redirect","重定向","发现预测错误时启动 squash",DECODE,"squash(inst, inst->threadNumber)")
        scene("decode","译码与传递","ifu window check rename")
        scene("redirect","译码纠错","ifu window check redirect")

    if uid == "rename":
        node("decode","Decode","译码输出",RENAME,"const DynInstPtr &inst = fromDecode->insts[i]","up","decode")
        node("src","源映射表","查找源操作数物理标签",RENAME,"Rename::renameSrcRegs(")
        node("dest","目的分配","分配目的物理寄存器并维护映射历史",RENAME,"Rename::renameDestRegs(")
        node("iew","Issue / Execute","接收重命名后的指令",RENAME,"toIEW->insts[toIEWIndex]","down","issue")
        link("decode","src","查询","为译码输出查找源寄存器映射",RENAME,"renameSrcRegs(inst, inst->threadNumber)")
        link("src","dest","分配","普通有目的操作数的指令分配新映射",RENAME,"renameDestRegs(inst, inst->threadNumber)")
        link("dest","iew","传递","将物理寄存器标签随指令交给 IEW",RENAME,"toIEW->insts[toIEWIndex]")
        scene("rename","整数指令重命名","decode src dest iew")

    if uid == "issue":
        node("rename","Rename","重命名输出",RENAME,"toIEW->insts[toIEWIndex]","up","rename")
        node("dispatch","Dispatch","队列容量与分派处理",IEW,"IEW::dispatchInsts(")
        node("iq","Issue Queue","等待操作数就绪并调度",IEW,"instQueue.scheduleReadyInsts()")
        node("execute","Execute","执行非访存指令",IEW,"inst->execute()")
        node("wb","Writeback","完成指令并唤醒依赖项",IEW,"IEW::writebackInsts()")
        node("commit","Commit","接收写回完成状态",COMMIT,"fromIEW->insts[inst_num]->setCanCommit()","down","commit")
        node("lsu","LSU / LSQ","为访存指令分配队项",IEW,"ldstQueue.insertLoad(","down","lsu")
        link("rename","dispatch","传递","将重命名结果送入执行阶段",RENAME,"toIEW->insts[toIEWIndex]")
        link("dispatch","iq","入队","为普通整数指令建立 IQ 项",IEW,"instQueue.insert(inst, disp_seq)")
        link("iq","execute","发射","就绪指令进入执行",IEW,"DynInstPtr inst = instQueue.getInstToExecute()")
        link("execute","wb","完成","执行完成的指令进入后续完成与写回路径",IEW,"readyToFinish(inst)")
        link("wb","commit","写回","Commit 消费 IEW 的完成标记",COMMIT,"fromIEW->insts[inst_num]->setCanCommit()")
        link("dispatch","lsu","分配","为 Load 指令分配 LSQ 项",IEW,"ldstQueue.insertLoad(")
        scene("alu","就绪选择、执行与写回","rename dispatch iq execute wb commit")
        scene("load","访存指令分派","rename dispatch lsu")

    if uid == "commit":
        node("rename","Rename","按程序顺序分配 ROB 项",COMMIT,"Commit::getInsts()","up","rename")
        node("wb","IEW","写回完成状态",COMMIT,"fromIEW->insts[inst_num]->setCanCommit()","up","issue")
        node("rob","ROB entries","维持程序顺序及完成状态",COMMIT,"rob->insertInst(inst)")
        node("head","队首检查","检查最老指令的完成状态和 Fault",COMMIT,"head_inst = rob->readHeadInst(commit_thread)")
        node("retire","Retire","成功退休并推进队首",COMMIT,"rob->retireHead(tid)")
        node("trap","Trap","精确异常交给 CPU 的 trap 处理",COMMIT,"cpu->trap(inst_fault")
        link("rename","rob","分配","按程序顺序将重命名后的指令插入 ROB",COMMIT,"rob->insertInst(inst)")
        link("wb","rob","完成","接收写回消息，允许该项参与提交",COMMIT,"fromIEW->insts[inst_num]->setCanCommit()")
        link("rob","head","检查","读取当前提交线程的队首指令",COMMIT,"head_inst = rob->readHeadInst(commit_thread)")
        link("head","retire","退休","成功提交后移除 ROB 队首",COMMIT,"rob->retireHead(tid)")
        link("head","trap","异常","处理队首指令携带的故障",COMMIT,"cpu->trap(inst_fault")
        scene("retire","完成到退休","wb rob head retire")
        scene("fault","队首精确异常","rob head trap")

    if uid == "lsu":
        node("issue","Issue / Execute","分配访存队列项",IEW,"ldstQueue.insertLoad(","up","issue")
        node("lq","Load Queue","跟踪在途加载及其翻译状态",UNIT,"LSQUnit::insertLoad(")
        node("sq","Store Queue","保存 Store 地址和数据",UNIT,"LSQUnit::insertStore(")
        node("sb","Store Buffer","合并普通可缓存的已提交写入",UNIT,"bool LSQUnit::insertStoreBuffer(")
        node("request","LSQRequest","组织拆分、翻译和数据包",LSQ,"LSQ::SingleDataRequest::initiateTranslation()")
        node("mmu","MMU","处理读写地址翻译",LSQ,"getMMUPtr()->translateTiming(","down","mmu")
        node("cache","D-Cache","接收已翻译的访存请求",UNIT,"dcachePort->sendTimingReq(data_pkt)","down","dcache")
        node("complete","Load completion","匹配响应并完成加载",UNIT,"LSQUnit::completeDataAccess(")
        link("issue","lq","分配","分派 Load 时在 LSQ 中占用项",IEW,"ldstQueue.insertLoad(")
        link("lq","request","请求","加载流水线发起地址访问",UNIT,"load_fault = inst->initiateAcc()")
        link("request","mmu","翻译","以 Read 模式翻译当前请求片段",LSQ,"getMMUPtr()->translateTiming(")
        link("mmu","request","回调","finish 记录该片段的翻译结果",LSQ,"LSQ::SingleDataRequest::finish(")
        link("request","cache","读取","无法转发的读请求通过 D-cache 端口发送",UNIT,"dcachePort->sendTimingReq(data_pkt)")
        link("cache","complete","返回","响应被交回 LSQ 并完成数据访问",LSQ,"_port.completeDataAccess(mainPacket())")
        link("issue","sq","分配","分派 Store 时申请队列项",IEW,"ldstQueue.insertStore(")
        link("sq","sb","写入","已提交普通 Store 转入写缓冲",UNIT,"bool success = insertStoreBuffer(")
        link("sb","cache","写回","驱逐的缓冲项形成写包",UNIT,"entry->request->sendPacketToCache()")
        scene("load","加载翻译与返回","issue lq request mmu request cache complete")
        scene("store","普通 Store 提交后排出","issue sq sb cache")

    if uid == "mmu":
        node("ifu","IFU","提交 Execute 请求",FETCH,"translateTiming(first_mem_req","up","ifu")
        node("lsu","LSU / LSQ","提交 Load/Store 请求",LSQ,"getMMUPtr()->translateTiming(","up","lsu")
        node("itb","ITLB","指令侧一级翻译",MMU,"itb = RiscvTLB")
        node("dtb","DTLB","数据侧一级翻译",MMU,"dtb = RiscvTLB")
        node("l2","Shared L2 TLB","双方共享的二级翻译项",MMU,"l2_shared = RiscvTLBL2")
        node("iwalk","I-side walker","指令侧页表遍历端口",MMU,"self.itb.walker.port =")
        node("dwalk","D-side walker","数据侧页表遍历端口",MMU,"self.dtb.walker.port =")
        node("pte","PTE memory","经 walker 请求端口读取页表项",WALK,"port.sendTimingReq(pkt)","down")
        for owner,tlb,walk,title,f,token in [
            ("ifu","itb","iwalk","取指",FETCH,"translateTiming(first_mem_req"),
            ("lsu","dtb","dwalk","访存",LSQ,"getMMUPtr()->translateTiming(")]:
            link(owner,tlb,"请求",title+"端提交地址翻译",f,token)
            link(tlb,owner,"命中","本例一级命中并成功通过权限检查，回调请求方",TLB,"translation->finish(fault, req, tc, mode)")
            link(tlb,"l2","查找","一级未命中，查询共享二级翻译项",TLB,"e[i_e] = l2tlb->lookupL2TLB(")
            if round_number < 5:
                link("l2",walk,"缺失","共享项未命中，由原 L1 的 walker 发起遍历",TLB,"fault = walker->start(0, tc, translation, req, mode, false, false, 2")
            link(walk,"pte","PTE 读","walker 发送一个物理页表项读取请求",WALK,"if (port.sendTimingReq(pkt))")
            link("pte",walk,"PTE 返回","WalkerPort 收到页表项读响应",WALK,"return walker->recvTimingResp(pkt)")
            link(walk,tlb,"回填","遇到有效叶项后向请求侧 TLB 插入直接翻译",WALK,"walker->tlb->insert(entry.vaddr, entry, false, direct)")
            link(walk,owner,"回调","页表遍历完成后结束原始翻译",WALK,"r.translation->finish(mainFault, r.req, r.tc, mode)")
            scene(tlb+"-hit",title+" · 一级 TLB 命中",f"{owner} {tlb} {owner}")
            scene(tlb+"-walk",title+" · 叶项遍历与回填",f"{owner} {tlb} l2 {walk} pte {walk} {tlb}")
            scene(tlb+"-finish",title+" · 遍历完成回调",f"pte {walk} {owner}")

    if uid in ("icache","dcache","l2","l3"):
        # One cache recipe, with boundary instances supplied by the active hierarchy.
        up={"icache":"ifu","dcache":"lsu","l2":"dcache","l3":"l2"}[uid]
        down={"icache":"l2","dcache":"l2","l2":"bus" if llc=="l2" else "l3","l3":"bus"}[uid]
        names={"ifu":"IFU","lsu":"LSU / LSQ","dcache":"L1 D-Cache","l2":"L2 Cache","l3":"L3 Cache","bus":"系统总线"}
        node("up",names[up],"示例读请求的上游端",BASE,"BaseCache::CpuSidePort::recvTimingReq","up",up)
        node("tags","Tag / data","查询地址、块状态和访问权限",BASE,"satisfied = access(pkt, blk, lat, writebacks)")
        node("mshr","MSHR","分配缺失请求，记录等待目标",BASE,"allocateMissBuffer(pkt, forward_time)")
        node("fill","Fill","安装缓存行并服务原始目标",BASE,"blk = handleFill(pkt, blk, writebacks, allocate)")
        node("reply","Response","按访问延迟发送读响应",BASE,"cpuSidePort.schedTimingResp(pkt, request_time)")
        node("down",names[down],"本级内存侧的下游接口",BASE,"BaseCache::sendMSHRQueuePacket(","down",down)
        link("up","tags","请求","CPU 侧端口接收读包并访问缓存块",BASE,"cache->recvTimingReq(pkt)")
        link("tags","reply","命中","满足本次访问，调度响应",BASE,"cpuSidePort.schedTimingResp(pkt, request_time)")
        link("tags","mshr","缺失","为全新的行缺失分配 MSHR",BASE,"allocateMissBuffer(pkt, forward_time)")
        link("mshr","down","读取","由内存侧端口向下一层请求缓存行",BASE,"if (!memSidePort.sendTimingReq(pkt))")
        link("down","fill","回填","响应匹配在途 MSHR，安装返回的缓存行",BASE,"blk = handleFill(pkt, blk, writebacks, allocate)")
        link("fill","reply","完成","处理等待本行的请求目标",BASE,"serviceMSHRTargets(mshr, pkt, blk)")
        link("reply","up","响应","将响应排入 CPU 侧返回队列",BASE,"cpuSidePort.schedTimingResp(pkt,")
        scene("hit","读命中与响应","up tags reply up")
        scene("miss","读缺失与缓存行回填","up tags mshr down fill reply up")

    if uid == "bus":
        up=llc
        node("up",up.upper()+" Cache","上游缓存端口",XBAR,"PortID mem_side_port_id = findPort(","up",up)
        node("route","地址译码","依据物理地址选择 mem-side 端口",XBAR,"PortID mem_side_port_id = findPort(")
        node("arb","Request layer","请求层仲裁、阻塞与重试",XBAR,"!reqLayers[mem_side_port_id]->tryTiming(")
        node("mem","内存控制器","总线下游请求与响应端",XBAR,"memSidePorts[mem_side_port_id]->sendTimingReq(pkt)","down","mem")
        node("resp","Response layer","为返回包定位原 CPU 侧端口",XBAR,"const auto route_lookup = routeTo.find(pkt->req)")
        link("up","route","请求","依据地址范围选择下游端口",XBAR,"PortID mem_side_port_id = findPort(")
        link("route","arb","仲裁","检查请求层本次传输的可用性",XBAR,"!reqLayers[mem_side_port_id]->tryTiming(")
        link("arb","mem","转发","成功仲裁后发送至选中的端口",XBAR,"memSidePorts[mem_side_port_id]->sendTimingReq(pkt)")
        link("mem","resp","返回","使用原请求身份查找返回路径",XBAR,"const auto route_lookup = routeTo.find(pkt->req)")
        link("resp","up","响应","将响应调度到原 CPU 侧端口",XBAR,"cpuSidePorts[cpu_side_port_id]->schedTimingResp(")
        scene("route","内存读请求与返回路由","up route arb mem resp up")

    if uid == "mem" and mem_type == "DRAMsim3":
        node("bus","系统总线","将物理地址请求送入控制器",DRAM,"DRAMsim3::MemoryPort::recvTimingReq(","up","bus")
        node("port","MemoryPort","接收请求并检查容量",DRAM,"DRAMsim3::recvTimingReq(")
        node("queue","Outstanding reads","按照地址记录尚未完成的读包",DRAM,"outstandingReads[pkt->getAddr()].push(pkt)")
        node("dram","DRAMsim3","接受事务，由时序后端驱动完成回调",DRAM,"wrapper.enqueue(")
        node("response","Response queue","查找原始请求并调度读响应",DRAM,"DRAMsim3::readComplete(")
        link("bus","port","请求","MemoryPort 接收来自系统总线的请求",DRAM,"DRAMsim3::MemoryPort::recvTimingReq(")
        link("port","queue","接纳","接受普通读包并按地址排队",DRAM,"outstandingReads[pkt->getAddr()].push(pkt)")
        link("queue","dram","入队","向 DRAMsim3 递交内存读事务",DRAM,"wrapper.enqueue(")
        link("dram","response","完成","读完成回调根据地址查找原始 Packet",DRAM,"auto p = outstandingReads.find(addr)")
        link("response","bus","响应","发回数据响应；端口拒绝时等待重试",DRAM,"bool success = port.sendTimingResp(pkt)")
        scene("read","DRAM 读事务与回调","bus port queue dram response bus")

    module.update(parts=parts, internalEdges=edges, scenarios=bind_scenarios(parts, edges, recipes, prefix))
