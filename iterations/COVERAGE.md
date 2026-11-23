# 两份 gem5 模型的结构覆盖清单

GEM5-1 对应 GEM5-1 源码，GEM5-2 对应 zenas-dev 源码。计数来自两张独立页面内嵌的模型，子图节点包括上下游边界，边按有向边 ID 计数，场景为已绑定边的源码演示。

| 模块 | GEM5-1 节点 / 边 / 场景 | GEM5-2 节点 / 边 / 场景 | 图中重点 |
|---|---:|---:|---|
| BPU | 11 / 16 / 5 | 11 / 16 / 5 | FTB · 6 个注册组件 |
| FTQ | 8 / 7 / 2 | 8 / 7 / 2 | FTQ 128 项 · FSQ 64 项 |
| IFU | 10 / 9 / 3 | 7 / 6 / 2 | resident window replay、resident window replay · 条件配置 |
| Decode | 5 / 4 / 2 | 5 / 4 / 2 | 6 条/周期 · 译码 |
| Rename | 4 / 3 / 1 | 4 / 3 / 1 | 6 条/周期 · 重命名 |
| Issue / Execute | 13 / 19 / 9 | 13 / 19 / 9 | 3 个 IQ · 544 项 · 23 个出口 → 12 个 IQ · 272 项 · 19 个出口 |
| Commit | 15 / 14 / 4 | 15 / 14 / 4 | ROB · 分支恢复 / 精确异常 / LVP 失配 → ROB · 分支恢复 / 精确异常 |
| LSU / LSQ | 9 / 10 / 2 | 9 / 10 / 2 | LQ 容量、SQ 容量 |
| MMU | 9 / 19 / 8 | 9 / 19 / 8 | 双侧 Walker · 动态 root_level → 双侧 Walker · SV48/SV39 分支 |
| L1 I-Cache | 7 / 9 / 3 | 7 / 9 / 3 | 缓存容量、MSHR 数量 |
| L1 D-Cache | 7 / 9 / 3 | 7 / 9 / 3 | 缓存容量、MSHR 数量 |
| L2 Cache | 9 / 13 / 5 | 9 / 13 / 5 | 缓存容量、MSHR 数量 |
| L3 Cache | 7 / 9 / 3 | 7 / 9 / 3 | 缓存容量、缓存容量 · 条件配置 |
| 系统互联 | 5 / 5 / 1 | 5 / 5 / 1 | 请求侧端口记录、响应侧查找 |
| 内存控制器 | 6 / 7 / 2 | 6 / 7 / 2 | 内存模型、DRAM 时序配置文件 |

## 阅读差异

已映射表示有源码定位，合并表示多个具体对象或 CPU 内部阶段共用图中节点，条件启用表示实现受配置或运行分支约束。未知保留尚不能定值的结构，缺失仅指当前映射在对应输入中明确记录的缺口。两边记录集合不同时，表格用“未列此项”表示该页没有提供该项记录。

- **发射与依赖唤醒。** GEM5-1 将 3 个 IQ 配到 23 个出口，显式源到目的队列有 9 条连接。GEM5-2 将 12 个 IQ 配到 19 个出口，显式源到目的队列有 92 条连接。
- **取指驻留窗口的默认状态。** GEM5-1 为关闭（已映射），GEM5-2 为无对应声明与实现（缺失）。
- **页表遍历起点。** GEM5-1 为动态 root_level（条件启用），GEM5-2 为SV48/SV39 分支（条件启用）。
- **满足理想参数条件时的 ROB 容量。** GEM5-1 为384（条件启用），GEM5-2 为256（条件启用）。

### BPU

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 预测器注册集合 | 已映射 · ["uftb", "uras", "ftb", "tage", "ras", "ittage"] · [src/cpu/pred/ftb/decoupled_bpred.cc:99](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:99) | 已映射 · ["uftb", "uras", "ftb", "tage", "ras", "ittage"] · [src/cpu/pred/ftb/decoupled_bpred.cc:99](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:99) |
| cpu.branchPred.tage.numWays | 条件启用 · 4 · [configs/example/xiangshan.py:371](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:371) | 条件启用 · 2 · [configs/example/xiangshan.py:364](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:364) |
| cpu.branchPred.tage.histLengths | 条件启用 · [4, 8, 16, 32, 64, 128, 256, 512] · [configs/example/xiangshan.py:390](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:390) | 条件启用 · [4, 8, 15, 28, 50, 90, 160, 300] · [configs/example/xiangshan.py:372](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:372) |

覆盖记录数按两页顺序列示，已映射 16/16，合并 0/0，条件启用 5/3，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · BPU | [configs/example/xiangshan.py:104](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:104) | 已映射 · BPU | [configs/example/xiangshan.py:103](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:103) |
| 内部组件 | 已映射 · PC / History、预测组件、Override、Fetch Stream Queue、FTB、TAGE、ITTAGE、RAS、uFTB、uRAS | [configs/example/xiangshan.py:104](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:104) | 已映射 · PC / History、预测组件、Override、Fetch Stream Queue、FTB、TAGE、ITTAGE、RAS、uFTB、uRAS | [configs/example/xiangshan.py:103](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:103) |
| 配置对象路径 | 已映射 · system.cpu[i].branchPred | [configs/example/xiangshan.py:104](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:104) | 已映射 · system.cpu[i].branchPred | [configs/example/xiangshan.py:103](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:103) |
| 预测器注册集合 | 已映射 · ["uftb", "uras", "ftb", "tage", "ras", "ittage"]（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:99](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:99) | 已映射 · ["uftb", "uras", "ftb", "tage", "ras", "ittage"]（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:99](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:99) |
| 配置入口选择表达式 | 条件启用 · DecoupledBPUWithBTB() if args.bp_type == 'DecoupledBPUWithBTB' else DecoupledBPUWithFTB()（args.bp_type == 'DecoupledBPUWithBTB'） | [configs/example/xiangshan.py:103](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:103) | 条件启用 · DecoupledBPUWithBTB() if args.bp_type == 'DecoupledBPUWithBTB' else DecoupledBPUWithFTB()（args.bp_type == 'DecoupledBPUWithBTB'） | [configs/example/xiangshan.py:102](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:102) |
| cpu.branchPred.tage.numWays | 条件启用 · 4（--ideal-kuanglangv1；args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB'；not (args.bp_type == 'DecoupledBPUWithFTB')） | [configs/example/xiangshan.py:371](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:371) | 条件启用 · 2（--ideal-kuanglangv1；args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB'；not (args.bp_type == 'DecoupledBPUWithFTB')） | [configs/example/xiangshan.py:364](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:364) |
| cpu.enableFetchResidentWindowReplay | 条件启用 · True（--ideal-kuanglangv1；args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB'；not (args.bp_type == 'DecoupledBPUWithFTB')） | [configs/example/xiangshan.py:376](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:376) | 未列此项 | — |
| cpu.branchPred.ras.numEntries | 条件启用 · 32（--ideal-kuanglangv1；args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB'；not (args.bp_type == 'DecoupledBPUWithFTB')） | [configs/example/xiangshan.py:381](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:381) | 未列此项 | — |
| cpu.branchPred.tage.histLengths | 条件启用 · [4, 8, 16, 32, 64, 128, 256, 512]（--ideal-kuanglangv1；args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB'） | [configs/example/xiangshan.py:390](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:390) | 条件启用 · [4, 8, 15, 28, 50, 90, 160, 300]（--ideal-kuanglangv1；args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB'） | [configs/example/xiangshan.py:372](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:372) |
| uFTB 注册 | 已映射 · UFTB()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:99](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:99) | 已映射 · UFTB()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:99](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:99) |
| uFTB 声明 | 已映射 · UFTB() | [src/cpu/pred/BranchPredictor.py:952](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:952) | 已映射 · UFTB() | [src/cpu/pred/BranchPredictor.py:952](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:952) |
| uRAS 注册 | 已映射 · FTBuRAS()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:100](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:100) | 已映射 · FTBuRAS()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:100](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:100) |
| uRAS 声明 | 已映射 · FTBuRAS() | [src/cpu/pred/BranchPredictor.py:954](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:954) | 已映射 · FTBuRAS() | [src/cpu/pred/BranchPredictor.py:954](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:954) |
| FTB 注册 | 已映射 · DefaultFTB()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:101](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:101) | 已映射 · DefaultFTB()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:101](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:101) |
| FTB 声明 | 已映射 · DefaultFTB() | [src/cpu/pred/BranchPredictor.py:949](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:949) | 已映射 · DefaultFTB() | [src/cpu/pred/BranchPredictor.py:949](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:949) |
| TAGE 注册 | 已映射 · FTBTAGE()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:102](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:102) | 已映射 · FTBTAGE()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:102](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:102) |
| TAGE 声明 | 已映射 · FTBTAGE() | [src/cpu/pred/BranchPredictor.py:950](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:950) | 已映射 · FTBTAGE() | [src/cpu/pred/BranchPredictor.py:950](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:950) |
| RAS 注册 | 已映射 · FTBRAS()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:103](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:103) | 已映射 · FTBRAS()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:103](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:103) |
| RAS 声明 | 已映射 · FTBRAS() | [src/cpu/pred/BranchPredictor.py:953](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:953) | 已映射 · FTBRAS() | [src/cpu/pred/BranchPredictor.py:953](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:953) |
| ITTAGE 注册 | 已映射 · FTBITTAGE()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:104](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:104) | 已映射 · FTBITTAGE()（--bp-type 未指定或等于 DecoupledBPUWithFTB） | [src/cpu/pred/ftb/decoupled_bpred.cc:104](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:104) |
| ITTAGE 声明 | 已映射 · FTBITTAGE() | [src/cpu/pred/BranchPredictor.py:951](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:951) | 已映射 · FTBITTAGE() | [src/cpu/pred/BranchPredictor.py:951](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:951) |

</details>

### FTQ

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| ftq_size 声明 | 已映射 · 128 · [src/cpu/pred/BranchPredictor.py:943](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:943) | 已映射 · 128 · [src/cpu/pred/BranchPredictor.py:943](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:943) |
| fsq_size 声明 | 已映射 · 64 · [src/cpu/pred/BranchPredictor.py:944](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:944) | 已映射 · 64 · [src/cpu/pred/BranchPredictor.py:944](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:944) |
| FTQ 释放 | 已映射 · 供给项消费后释放 · [src/cpu/pred/ftb/fetch_target_queue.cc:65](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/fetch_target_queue.cc:65) | 已映射 · 供给项消费后释放 · [src/cpu/pred/ftb/fetch_target_queue.cc:65](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/fetch_target_queue.cc:65) |

覆盖记录数按两页顺序列示，已映射 8/8，合并 1/1，条件启用 2/2，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · FTQ | [src/cpu/pred/ftb/fetch_target_queue.cc:15](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/fetch_target_queue.cc:15) | 已映射 · FTQ | [src/cpu/pred/ftb/fetch_target_queue.cc:15](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/fetch_target_queue.cc:15) |
| 内部组件 | 已映射 · FTQ entries、Demand cursor、Supply buffer、FSQ 预测流、按 streamId 取流、消费目标项 | [src/cpu/pred/ftb/fetch_target_queue.cc:15](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/fetch_target_queue.cc:15) | 已映射 · FTQ entries、Demand cursor、Supply buffer、FSQ 预测流、按 streamId 取流、消费目标项 | [src/cpu/pred/ftb/fetch_target_queue.cc:15](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/fetch_target_queue.cc:15) |
| 实现归属 | 合并 · cpu.branchPred.fetchTargetQueue · 预测器内部 C++ 成员 | [src/cpu/pred/ftb/decoupled_bpred.cc:31](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:31) | 合并 · cpu.branchPred.fetchTargetQueue · 预测器内部 C++ 成员 | [src/cpu/pred/ftb/decoupled_bpred.cc:31](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:31) |
| FSQ 写入 | 已映射 · 预测器生成 FetchStream | [src/cpu/pred/ftb/decoupled_bpred.cc:2579](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:2579) | 已映射 · 预测器生成 FetchStream | [src/cpu/pred/ftb/decoupled_bpred.cc:2579](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:2579) |
| FSQ 读取 | 已映射 · 按目标流编号查找 | [src/cpu/pred/ftb/decoupled_bpred.cc:2221](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:2221) | 已映射 · 按目标流编号查找 | [src/cpu/pred/ftb/decoupled_bpred.cc:2221](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:2221) |
| FTQ 写入 | 已映射 · 切分预测块入队 | [src/cpu/pred/ftb/decoupled_bpred.cc:2288](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/decoupled_bpred.cc:2288) | 已映射 · 切分预测块入队 | [src/cpu/pred/ftb/decoupled_bpred.cc:2288](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/decoupled_bpred.cc:2288) |
| FTQ 释放 | 已映射 · 供给项消费后释放 | [src/cpu/pred/ftb/fetch_target_queue.cc:65](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/ftb/fetch_target_queue.cc:65) | 已映射 · 供给项消费后释放 | [src/cpu/pred/ftb/fetch_target_queue.cc:65](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/ftb/fetch_target_queue.cc:65) |
| ftq_size 声明 | 已映射 · 128 | [src/cpu/pred/BranchPredictor.py:943](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:943) | 已映射 · 128 | [src/cpu/pred/BranchPredictor.py:943](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:943) |
| ftq_size 配置赋值 | 条件启用 · 64（--ideal-kuanglangv1 且显式选择 FTB 或 BTB） | [configs/example/xiangshan.py:385](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:385) | 条件启用 · 64（--ideal-kuanglangv1 且显式选择 FTB 或 BTB） | [configs/example/xiangshan.py:367](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:367) |
| fsq_size 声明 | 已映射 · 64 | [src/cpu/pred/BranchPredictor.py:944](D:/huanjian-project/stage-two/GEM5-1/src/cpu/pred/BranchPredictor.py:944) | 已映射 · 64 | [src/cpu/pred/BranchPredictor.py:944](D:/codex-project/model-convert/zenas-dev/src/cpu/pred/BranchPredictor.py:944) |
| fsq_size 配置赋值 | 条件启用 · 64（--ideal-kuanglangv1 且显式选择 FTB 或 BTB） | [configs/example/xiangshan.py:386](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:386) | 条件启用 · 64（--ideal-kuanglangv1 且显式选择 FTB 或 BTB） | [configs/example/xiangshan.py:368](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:368) |

</details>

### IFU

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| resident window replay | 已映射 · 关闭 · [src/cpu/o3/BaseO3CPU.py:140](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:140) | 缺失 · 无对应声明与实现 · [src/cpu/o3/BaseO3CPU.py:80](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:80) |
| resident window replay · 条件配置 | 条件启用 · 启用 · [configs/example/xiangshan.py:376](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:376) | 未列此项 |
| 双 FTQ 目标取指 · 条件配置 | 条件启用 · 启用 · [configs/example/xiangshan.py:380](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:380) | 未列此项 |

覆盖记录数按两页顺序列示，已映射 8/2，合并 1/1，条件启用 5/0，未知 0/0，缺失 0/1。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · IFU | [src/cpu/o3/fetch.cc:949](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/fetch.cc:949) | 已映射 · IFU | [src/cpu/o3/fetch.cc:826](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/fetch.cc:826) |
| 内部组件 | 已映射 · Fetch request、ICache port、取指缓冲、Resident byte window、Active snapshot、Decoder bytes | [src/cpu/o3/fetch.cc:949](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/fetch.cc:949) | 已映射 · Fetch request、ICache port、取指缓冲 | [src/cpu/o3/fetch.cc:826](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/fetch.cc:826) |
| 实现归属 | 合并 · cpu.fetch · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:444](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/cpu.hh:444) | 合并 · cpu.fetch · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:434](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/cpu.hh:434) |
| resident window replay | 已映射 · 关闭 | [src/cpu/o3/BaseO3CPU.py:140](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:140) | 缺失 · 无对应声明与实现（检查 BaseO3CPU 类体及 Fetch 实现） | [src/cpu/o3/BaseO3CPU.py:80](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:80) |
| resident window replay · 条件配置 | 条件启用 · 启用（args.ideal_kuanglangv1 且 args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB' 且 not args.bp_type == 'DecoupledBPUWithFTB'） | [configs/example/xiangshan.py:376](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:376) | 未列此项 | — |
| resident window probe | 已映射 · 关闭 | [src/cpu/o3/BaseO3CPU.py:137](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:137) | 未列此项 | — |
| resident window probe · 条件配置 | 条件启用 · 关闭（args.ideal_kuanglangv1 且 args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB' 且 not args.bp_type == 'DecoupledBPUWithFTB'） | [configs/example/xiangshan.py:377](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:377) | 未列此项 | — |
| resident window count | 已映射 · 4 | [src/cpu/o3/BaseO3CPU.py:143](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:143) | 未列此项 | — |
| resident window count · 条件配置 | 条件启用 · 4（args.ideal_kuanglangv1 且 args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB' 且 not args.bp_type == 'DecoupledBPUWithFTB'） | [configs/example/xiangshan.py:378](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:378) | 未列此项 | — |
| 双 FTQ 目标取指 | 已映射 · 关闭 | [src/cpu/o3/BaseO3CPU.py:135](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:135) | 未列此项 | — |
| 双 FTQ 目标取指 · 条件配置 | 条件启用 · 启用（args.ideal_kuanglangv1 且 args.bp_type == 'DecoupledBPUWithFTB' or args.bp_type == 'DecoupledBPUWithBTB' 且 not args.bp_type == 'DecoupledBPUWithFTB'） | [configs/example/xiangshan.py:380](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:380) | 未列此项 | — |
| 双目标取指的构造约束 | 已映射 · 单硬件线程、单取指线程、BTB 预测器 | [src/cpu/o3/fetch.cc:161](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/fetch.cc:161) | 未列此项 | — |
| 驻留窗口容量约束 | 已映射 · 重放开启时窗口数须在 1 到 FetchResidentWindowMaxWays 之间 | [src/cpu/o3/fetch.cc:166](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/fetch.cc:166) | 未列此项 | — |
| 驻留窗口数据通路 | 条件启用 · 关闭（在有效的单线程 BTB 双目标配置上启用重放，主缓冲未完整覆盖，下一个目标命中有效驻留窗口） | [src/cpu/o3/fetch.cc:2810](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/fetch.cc:2810) | 未列此项 | — |

</details>

### Decode

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| decodeWidth | 已映射 · 6 · [src/cpu/o3/BaseO3CPU.py:152](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:152) | 已映射 · 6 · [src/cpu/o3/BaseO3CPU.py:141](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:141) |
| decodeWidth · 理想配置 | 条件启用 · 10 · [configs/example/xiangshan.py:319](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:319) | 条件启用 · 8 · [configs/example/xiangshan.py:317](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:317) |
| Decode → Rename 阶段边界 | 合并 · decodeQueue 由同一 O3CPU 注入，两个阶段通过 CPU 内部时间缓冲传递指令 · [src/cpu/o3/cpu.cc:199](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/cpu.cc:199) | 合并 · decodeQueue 由同一 O3CPU 注入，两个阶段通过 CPU 内部时间缓冲传递指令 · [src/cpu/o3/cpu.cc:199](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/cpu.cc:199) |

覆盖记录数按两页顺序列示，已映射 3/3，合并 2/2，条件启用 1/1，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · Decode | [src/cpu/o3/decode.cc:592](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/decode.cc:592) | 已映射 · Decode | [src/cpu/o3/decode.cc:592](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/decode.cc:592) |
| 内部组件 | 已映射 · 译码队列、控制流检查 | [src/cpu/o3/decode.cc:592](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/decode.cc:592) | 已映射 · 译码队列、控制流检查 | [src/cpu/o3/decode.cc:592](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/decode.cc:592) |
| 实现归属 | 合并 · cpu.decode · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:447](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/cpu.hh:447) | 合并 · cpu.decode · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:437](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/cpu.hh:437) |
| decodeWidth | 已映射 · 6 | [src/cpu/o3/BaseO3CPU.py:152](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:152) | 已映射 · 6 | [src/cpu/o3/BaseO3CPU.py:141](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:141) |
| decodeWidth · 理想配置 | 条件启用 · 10（ideal_kuanglangv1=true） | [configs/example/xiangshan.py:319](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:319) | 条件启用 · 8（ideal_kuanglangv1=true） | [configs/example/xiangshan.py:317](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:317) |
| Decode → Rename 阶段边界 | 合并 · decodeQueue 由同一 O3CPU 注入，两个阶段通过 CPU 内部时间缓冲传递指令 | [src/cpu/o3/cpu.cc:199](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/cpu.cc:199) | 合并 · decodeQueue 由同一 O3CPU 注入，两个阶段通过 CPU 内部时间缓冲传递指令 | [src/cpu/o3/cpu.cc:199](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/cpu.cc:199) |

</details>

### Rename

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| renameWidth · 理想配置 | 条件启用 · 10 · [configs/example/xiangshan.py:320](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:320) | 条件启用 · 8 · [configs/example/xiangshan.py:318](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:318) |
| numPhysIntRegs · 理想配置 | 条件启用 · 384 · [configs/example/xiangshan.py:331](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:331) | 条件启用 · 256 · [configs/example/xiangshan.py:326](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:326) |
| RAT 硬件 bank 及端口数 | 未知 · UnifiedRenameMap 提供按寄存器类别寻址的接口，未获得物理 RAT 分库和读写端口配置 · [src/cpu/o3/rename_map.hh:168](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/rename_map.hh:168) | 未知 · UnifiedRenameMap 提供按寄存器类别寻址的接口，未获得物理 RAT 分库和读写端口配置 · [src/cpu/o3/rename_map.hh:168](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/rename_map.hh:168) |

覆盖记录数按两页顺序列示，已映射 10/10，合并 2/2，条件启用 3/3，未知 1/1，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · Rename | [src/cpu/o3/rename.cc:570](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/rename.cc:570) | 已映射 · Rename | [src/cpu/o3/rename.cc:570](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/rename.cc:570) |
| 内部组件 | 已映射 · 源映射表、目的分配 | [src/cpu/o3/rename.cc:570](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/rename.cc:570) | 已映射 · 源映射表、目的分配 | [src/cpu/o3/rename.cc:570](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/rename.cc:570) |
| 实现归属 | 合并 · cpu.rename · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:450](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/cpu.hh:450) | 合并 · cpu.rename · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:440](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/cpu.hh:440) |
| renameWidth | 已映射 · 6 | [src/cpu/o3/BaseO3CPU.py:158](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:158) | 已映射 · 6 | [src/cpu/o3/BaseO3CPU.py:147](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:147) |
| renameWidth · 理想配置 | 条件启用 · 10（ideal_kuanglangv1=true） | [configs/example/xiangshan.py:320](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:320) | 条件启用 · 8（ideal_kuanglangv1=true） | [configs/example/xiangshan.py:318](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:318) |
| numPhysIntRegs | 已映射 · 224 | [src/cpu/o3/BaseO3CPU.py:220](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:220) | 已映射 · 224 | [src/cpu/o3/BaseO3CPU.py:209](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:209) |
| numPhysIntRegs · 理想配置 | 条件启用 · 384（ideal_kuanglangv1=true） | [configs/example/xiangshan.py:331](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:331) | 条件启用 · 256（ideal_kuanglangv1=true） | [configs/example/xiangshan.py:326](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:326) |
| numPhysFloatRegs | 已映射 · 192 | [src/cpu/o3/BaseO3CPU.py:222](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:222) | 已映射 · 192 | [src/cpu/o3/BaseO3CPU.py:211](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:211) |
| numPhysFloatRegs · 理想配置 | 条件启用 · 320（ideal_kuanglangv1=true） | [configs/example/xiangshan.py:332](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:332) | 条件启用 · 320（ideal_kuanglangv1=true） | [configs/example/xiangshan.py:327](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:327) |
| numPhysVecRegs | 已映射 · 384 | [src/cpu/o3/BaseO3CPU.py:224](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:224) | 已映射 · 384 | [src/cpu/o3/BaseO3CPU.py:213](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:213) |
| numPhysVecPredRegs | 已映射 · 32 | [src/cpu/o3/BaseO3CPU.py:226](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:226) | 已映射 · 32 | [src/cpu/o3/BaseO3CPU.py:215](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:215) |
| numPhysVecBufRegs | 已映射 · 128 | [src/cpu/o3/BaseO3CPU.py:228](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:228) | 已映射 · 128 | [src/cpu/o3/BaseO3CPU.py:217](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:217) |
| numPhysCCRegs | 已映射 · 0 | [src/cpu/o3/BaseO3CPU.py:232](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:232) | 已映射 · 0 | [src/cpu/o3/BaseO3CPU.py:221](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:221) |
| numPhysRMiscRegs | 已映射 · 40 | [src/cpu/o3/BaseO3CPU.py:233](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:233) | 已映射 · 40 | [src/cpu/o3/BaseO3CPU.py:222](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:222) |
| RAT 与自由表归属 | 合并 · CPU 拥有各线程 renameMap、regFile 和 freeList；Rename 引用这些对象 | [src/cpu/o3/cpu.cc:257](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/cpu.cc:257) | 合并 · CPU 拥有各线程 renameMap、regFile 和 freeList；Rename 引用这些对象 | [src/cpu/o3/cpu.cc:257](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/cpu.cc:257) |
| RAT 硬件 bank 及端口数 | 未知 · UnifiedRenameMap 提供按寄存器类别寻址的接口，未获得物理 RAT 分库和读写端口配置 | [src/cpu/o3/rename_map.hh:168](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/rename_map.hh:168) | 未知 · UnifiedRenameMap 提供按寄存器类别寻址的接口，未获得物理 RAT 分库和读写端口配置 | [src/cpu/o3/rename_map.hh:168](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/rename_map.hh:168) |

</details>

### Issue / Execute

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 整数 IQ | 已映射 · 1 队列 · 192 项 · 10 个输入端口 · [configs/common/FUScheduler.py:45](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:45) | 合并 · 4 队列 · 72 项 · 8 个输入端口 · [configs/common/FUScheduler.py:30](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:30) |
| 访存 IQ | 已映射 · 1 队列 · 192 项 · 10 个输入端口 · [configs/common/FUScheduler.py:90](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:90) | 合并 · 4 队列 · 72 项 · 8 个输入端口 · [configs/common/FUScheduler.py:48](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:48) |
| 浮点 / 向量 IQ | 已映射 · 1 队列 · 160 项 · 10 个输入端口 · [configs/common/FUScheduler.py:109](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:109) | 合并 · 4 队列 · 128 项 · 8 个输入端口 · [configs/common/FUScheduler.py:65](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:65) |
| 推测唤醒网络 | 已映射 · 显式定向网络 · 9 条已确认有向连接（包含自唤醒） · [configs/common/FUScheduler.py:137](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:137) | 已映射 · 显式定向网络 · 92 条已确认有向连接（包含自唤醒） · [configs/common/FUScheduler.py:98](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:98) |

覆盖记录数按两页顺序列示，已映射 64/76，合并 1/4，条件启用 1/1，未知 1/1，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · Issue / Execute | [src/cpu/o3/iew.cc:2478](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/iew.cc:2478) | 已映射 · Issue / Execute | [src/cpu/o3/iew.cc:1945](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/iew.cc:1945) |
| 内部组件 | 已映射 · Dispatch、Issue Queue、Execute、Writeback、整数 IQ、访存 IQ、浮点 / 向量 IQ、发射端口与 FU、寄存器读仲裁、推测唤醒 | [src/cpu/o3/iew.cc:2478](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/iew.cc:2478) | 已映射 · Dispatch、Issue Queue、Execute、Writeback、整数 IQ、访存 IQ、浮点 / 向量 IQ、发射端口与 FU、寄存器读仲裁、推测唤醒 | [src/cpu/o3/iew.cc:1945](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/iew.cc:1945) |
| 实现归属 | 合并 · cpu.iew · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:453](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/cpu.hh:453) | 合并 · cpu.iew · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:443](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/cpu.hh:443) |
| CPU 配置类 | 已映射 · huanjianV1Core | [configs/example/xiangshan.py:36](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:36) | 已映射 · huanjianV1Core | [configs/example/xiangshan.py:36](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:36) |
| 发射调度器 | 已映射 · HUANJIANV1Scheduler | [configs/example/xiangshan.py:30](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:30) | 已映射 · HUANJIANV1Scheduler | [configs/example/xiangshan.py:30](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:30) |
| 整数 IQ | 已映射 · 1 队列 · 192 项 · 10 个输入端口 | [configs/common/FUScheduler.py:45](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:45) | 合并 · 4 队列 · 72 项 · 8 个输入端口 | [configs/common/FUScheduler.py:30](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:30) |
| IQ · intIQ | 已映射 · 容量 192 · 输入端口 10 | [configs/common/FUScheduler.py:46](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:46) | 未列此项 | — |
| 访存 IQ | 已映射 · 1 队列 · 192 项 · 10 个输入端口 | [configs/common/FUScheduler.py:90](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:90) | 合并 · 4 队列 · 72 项 · 8 个输入端口 | [configs/common/FUScheduler.py:48](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:48) |
| IQ · memIQ | 已映射 · 容量 192 · 输入端口 10 | [configs/common/FUScheduler.py:91](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:91) | 未列此项 | — |
| 浮点 / 向量 IQ | 已映射 · 1 队列 · 160 项 · 10 个输入端口 | [configs/common/FUScheduler.py:109](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:109) | 合并 · 4 队列 · 128 项 · 8 个输入端口 | [configs/common/FUScheduler.py:65](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:65) |
| IQ · fpIQ | 已映射 · 容量 160 · 输入端口 10 | [configs/common/FUScheduler.py:110](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:110) | 未列此项 | — |
| intIQ / 出口 0 | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数9(P0), 整数10(P0) | [configs/common/FUScheduler.py:48](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:48) | 未列此项 | — |
| intIQ / 出口 1 | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数11(P0), 整数12(P0) | [configs/common/FUScheduler.py:50](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:50) | 未列此项 | — |
| intIQ / 出口 2 | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数13(P0), 整数14(P0) | [configs/common/FUScheduler.py:52](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:52) | 未列此项 | — |
| intIQ / 出口 3 | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数15(P0), 整数16(P0) | [configs/common/FUScheduler.py:54](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:54) | 未列此项 | — |
| intIQ / 出口 4 | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数17(P0), 整数18(P0) | [configs/common/FUScheduler.py:56](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:56) | 未列此项 | — |
| intIQ / 出口 5 | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数19(P0), 整数20(P0) | [configs/common/FUScheduler.py:58](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:58) | 未列此项 | — |
| intIQ / 出口 6 | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数21(P0), 整数22(P0) | [configs/common/FUScheduler.py:60](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:60) | 未列此项 | — |
| intIQ / 出口 7 | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数23(P0), 整数24(P0) | [configs/common/FUScheduler.py:62](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:62) | 未列此项 | — |
| intIQ / 出口 8 | 已映射 · FU IntBRU · 读端口 整数25(P0), 整数26(P0) | [configs/common/FUScheduler.py:65](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:65) | 未列此项 | — |
| intIQ / 出口 9 | 已映射 · FU IntBRU · 读端口 整数27(P0), 整数28(P0) | [configs/common/FUScheduler.py:66](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:66) | 未列此项 | — |
| intIQ / 出口 10 | 已映射 · FU IntBRU · 读端口 整数29(P0), 整数30(P0) | [configs/common/FUScheduler.py:67](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:67) | 未列此项 | — |
| memIQ / 出口 0 | 已映射 · FU ReadPort · 读端口 整数7(P1) | [configs/common/FUScheduler.py:92](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:92) | 未列此项 | — |
| memIQ / 出口 1 | 已映射 · FU ReadPort · 读端口 整数5(P1) | [configs/common/FUScheduler.py:93](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:93) | 未列此项 | — |
| memIQ / 出口 2 | 已映射 · FU ReadPort · 读端口 整数3(P2) | [configs/common/FUScheduler.py:94](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:94) | 未列此项 | — |
| memIQ / 出口 3 | 已映射 · FU ReadPort · 读端口 整数2(P1) | [configs/common/FUScheduler.py:95](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:95) | 未列此项 | — |
| memIQ / 出口 4 | 已映射 · FU WritePort · 读端口 整数1(P1) | [configs/common/FUScheduler.py:96](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:96) | 未列此项 | — |
| memIQ / 出口 5 | 已映射 · FU WritePort · 读端口 整数0(P1) | [configs/common/FUScheduler.py:97](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:97) | 未列此项 | — |
| memIQ / 出口 6 | 已映射 · FU StoreDataPort · 读端口 整数6(P2), 浮点16(P0) | [configs/common/FUScheduler.py:98](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:98) | 未列此项 | — |
| memIQ / 出口 7 | 已映射 · FU StoreDataPort · 读端口 整数4(P2), 浮点17(P0) | [configs/common/FUScheduler.py:99](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:99) | 未列此项 | — |
| fpIQ / 出口 0 | 已映射 · FU VAU + VMA + SFT + RED + DIV + MSC_0 + MSC_1 + PRM + FAU + FAU_CMP + FMA + FDV + FCV_F2F + FCV_F2I + FCV_I2F · 读端口 浮点0(P0), 浮点1(P0), 浮点2(P0) | [configs/common/FUScheduler.py:111](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:111) | 未列此项 | — |
| fpIQ / 出口 1 | 已映射 · FU VAU + VMA + SFT + RED + DIV + MSC_0 + MSC_1 + PRM + FAU + FAU_CMP + FMA + FDV + FCV_F2F + FCV_F2I + FCV_I2F · 读端口 浮点3(P0), 浮点4(P0), 浮点5(P0) | [configs/common/FUScheduler.py:115](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:115) | 未列此项 | — |
| fpIQ / 出口 2 | 已映射 · FU VAU + VMA + SFT + RED + DIV + MSC_0 + MSC_1 + PRM + FAU + FAU_CMP + FMA + FDV + FCV_F2F + FCV_F2I + FCV_I2F · 读端口 浮点6(P0), 浮点7(P0), 浮点8(P0), 整数8(P0) | [configs/common/FUScheduler.py:119](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:119) | 未列此项 | — |
| fpIQ / 出口 3 | 已映射 · FU VAU + VMA + SFT + RED + DIV + MSC_0 + MSC_1 + PRM + FAU + FAU_CMP + FMA + FDV + FCV_F2F + FCV_F2I + FCV_I2F · 读端口 浮点9(P0), 浮点10(P0), 浮点11(P0) | [configs/common/FUScheduler.py:123](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:123) | 未列此项 | — |
| FU · IntALU | 已映射 · IntAlu | [src/cpu/o3/FuncUnitConfig.py:51](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:51) | 已映射 · IntAlu | [src/cpu/o3/FuncUnitConfig.py:51](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:51) |
| FU · IntMult | 已映射 · IntMult | [src/cpu/o3/FuncUnitConfig.py:77](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:77) | 已映射 · IntMult | [src/cpu/o3/FuncUnitConfig.py:77](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:77) |
| FU · IntDiv | 已映射 · IntDiv | [src/cpu/o3/FuncUnitConfig.py:73](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:73) | 已映射 · IntDiv | [src/cpu/o3/FuncUnitConfig.py:73](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:73) |
| FU · IntMisc | 已映射 · No_OpClass, VectorConfig | [src/cpu/o3/FuncUnitConfig.py:47](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:47) | 已映射 · No_OpClass, VectorConfig | [src/cpu/o3/FuncUnitConfig.py:47](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:47) |
| FU · INT_VFP | 已映射 · VectorConvertI2I, FloatMv | [src/cpu/o3/FuncUnitConfig.py:174](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:174) | 已映射 · VectorConvertI2I, FloatCvtI2F | [src/cpu/o3/FuncUnitConfig.py:172](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:172) |
| FU · IntBRU | 已映射 · IntBr | [src/cpu/o3/FuncUnitConfig.py:54](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:54) | 已映射 · IntBr | [src/cpu/o3/FuncUnitConfig.py:54](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:54) |
| FU · ReadPort | 已映射 · MemRead, FloatMemRead, VectorUnitStrideLoad, VectorSegUnitStrideLoad, VectorUnitStrideMaskLoad, VectorSegUnitStrideMaskLoad, VectorStridedLoad, VectorSegStridedLoad, VectorIndexedLoad, VectorSegIndexedLoad, VectorUnitStrideFaultOnlyFirstLoad, VectorWholeRegisterLoad | [src/cpu/o3/FuncUnitConfig.py:198](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:198) | 已映射 · MemRead, FloatMemRead, VectorUnitStrideLoad, VectorSegUnitStrideLoad, VectorUnitStrideMaskLoad, VectorSegUnitStrideMaskLoad, VectorStridedLoad, VectorSegStridedLoad, VectorIndexedLoad, VectorSegIndexedLoad, VectorUnitStrideFaultOnlyFirstLoad, VectorWholeRegisterLoad | [src/cpu/o3/FuncUnitConfig.py:196](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:196) |
| FU · WritePort | 已映射 · MemWrite, MemAtomic, FloatMemWrite, VectorUnitStrideStore, VectorSegUnitStrideStore, VectorUnitStrideMaskStore, VectorStridedStore, VectorIndexedStore, VectorWholeRegisterStore | [src/cpu/o3/FuncUnitConfig.py:212](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:212) | 已映射 · MemWrite, MemAtomic, FloatMemWrite, VectorUnitStrideStore, VectorSegUnitStrideStore, VectorUnitStrideMaskStore, VectorStridedStore, VectorIndexedStore, VectorWholeRegisterStore | [src/cpu/o3/FuncUnitConfig.py:210](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:210) |
| FU · StoreDataPort | 已映射 · StoreData | [src/cpu/o3/FuncUnitConfig.py:223](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:223) | 已映射 · StoreData | [src/cpu/o3/FuncUnitConfig.py:221](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:221) |
| FU · VAU | 已映射 · VectorArith | [src/cpu/o3/FuncUnitConfig.py:101](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:101) | 已映射 · VectorArith | [src/cpu/o3/FuncUnitConfig.py:100](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:100) |
| FU · VMA | 已映射 · VectorMult, VectorMultAcc | [src/cpu/o3/FuncUnitConfig.py:106](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:106) | 已映射 · VectorMult, VectorMultAcc | [src/cpu/o3/FuncUnitConfig.py:105](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:105) |
| FU · SFT | 已映射 · VectorSpecialFunc | [src/cpu/o3/FuncUnitConfig.py:111](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:111) | 已映射 · VectorSpecialFunc | [src/cpu/o3/FuncUnitConfig.py:110](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:110) |
| FU · RED | 已映射 · VectorReduction | [src/cpu/o3/FuncUnitConfig.py:115](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:115) | 已映射 · VectorReduction | [src/cpu/o3/FuncUnitConfig.py:114](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:114) |
| FU · DIV | 已映射 · VectorDiv | [src/cpu/o3/FuncUnitConfig.py:119](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:119) | 已映射 · VectorDiv | [src/cpu/o3/FuncUnitConfig.py:118](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:118) |
| FU · MSC_0 | 已映射 · VectorMisc0 | [src/cpu/o3/FuncUnitConfig.py:123](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:123) | 已映射 · VectorMisc0 | [src/cpu/o3/FuncUnitConfig.py:122](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:122) |
| FU · MSC_1 | 已映射 · VectorMisc1 | [src/cpu/o3/FuncUnitConfig.py:127](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:127) | 已映射 · VectorMisc1 | [src/cpu/o3/FuncUnitConfig.py:126](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:126) |
| FU · PRM | 已映射 · VectorPermute | [src/cpu/o3/FuncUnitConfig.py:131](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:131) | 已映射 · VectorPermute | [src/cpu/o3/FuncUnitConfig.py:130](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:130) |
| FU · FAU | 已映射 · VectorFloatArith, FloatAdd, FloatMisc | [src/cpu/o3/FuncUnitConfig.py:135](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:135) | 已映射 · VectorFloatArith, FloatAdd, FloatMisc | [src/cpu/o3/FuncUnitConfig.py:134](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:134) |
| FU · FAU_CMP | 已映射 · VectorFloatCmp, FloatCmp | [src/cpu/o3/FuncUnitConfig.py:141](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:141) | 已映射 · VectorFloatCmp, FloatCmp | [src/cpu/o3/FuncUnitConfig.py:140](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:140) |
| FU · FMA | 已映射 · VectorFloatMult, VectorFloatMultAcc, FloatMult, FloatMultAcc | [src/cpu/o3/FuncUnitConfig.py:146](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:146) | 已映射 · VectorFloatMult, VectorFloatMultAcc, FloatMult, FloatMultAcc | [src/cpu/o3/FuncUnitConfig.py:145](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:145) |
| FU · FDV | 已映射 · VectorFloatDiv, FloatDiv, FloatSqrt | [src/cpu/o3/FuncUnitConfig.py:153](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:153) | 已映射 · VectorFloatDiv, FloatDiv, FloatSqrt | [src/cpu/o3/FuncUnitConfig.py:152](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:152) |
| FU · FCV_F2F | 已映射 · VectorConvertF2F, FloatCvtF2F | [src/cpu/o3/FuncUnitConfig.py:159](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:159) | 已映射 · VectorConvertF2F, FloatCvtF2F | [src/cpu/o3/FuncUnitConfig.py:158](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:158) |
| FU · FCV_F2I | 已映射 · VectorConvertF2I, FloatCvtF2I | [src/cpu/o3/FuncUnitConfig.py:164](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:164) | 已映射 · VectorConvertF2I, FloatCvtF2I | [src/cpu/o3/FuncUnitConfig.py:163](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:163) |
| FU · FCV_I2F | 已映射 · VectorConvertI2F, FloatCvtI2F | [src/cpu/o3/FuncUnitConfig.py:169](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FuncUnitConfig.py:169) | 已映射 · VectorConvertI2F | [src/cpu/o3/FuncUnitConfig.py:168](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:168) |
| 寄存器读端口 | 已映射 · 整数 31 个（0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30）；浮点 14 个（0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 17） | [src/cpu/o3/issue_queue.cc:1359](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/issue_queue.cc:1359) | 已映射 · 整数 9 个（0, 1, 2, 3, 4, 5, 6, 7, 8）；浮点 14 个（0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 16, 17） | [src/cpu/o3/issue_queue.cc:1359](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/issue_queue.cc:1359) |
| 寄存器写端口 | 未知 · 当前 IssuePort.rp 声明读端口；独立写端口连接待核对 | [src/cpu/o3/FUPool.py:64](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FUPool.py:64) | 未知 · 当前 IssuePort.rp 声明读端口；独立写端口连接待核对 | [src/cpu/o3/FUPool.py:64](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FUPool.py:64) |
| 推测唤醒网络 | 已映射 · 显式定向网络 · 9 条已确认有向连接（包含自唤醒） | [configs/common/FUScheduler.py:137](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:137) | 已映射 · 显式定向网络 · 92 条已确认有向连接（包含自唤醒） | [configs/common/FUScheduler.py:98](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:98) |
| 唤醒源 · intIQ | 已映射 · intIQ, memIQ, fpIQ | [configs/common/FUScheduler.py:138](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:138) | 未列此项 | — |
| 唤醒源 · memIQ | 已映射 · intIQ, memIQ, fpIQ | [configs/common/FUScheduler.py:139](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:139) | 未列此项 | — |
| 唤醒源 · fpIQ | 已映射 · intIQ, memIQ, fpIQ | [configs/common/FUScheduler.py:140](D:/huanjian-project/stage-two/GEM5-1/configs/common/FUScheduler.py:140) | 未列此项 | — |
| numDQEntries 声明 | 已映射 · [32, 16, 16] | [src/cpu/o3/BaseO3CPU.py:167](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:167) | 已映射 · [32, 16, 16] | [src/cpu/o3/BaseO3CPU.py:156](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:156) |
| numDQEntries 配置赋值 | 条件启用 · [36, 36, 36]（--ideal-kuanglangv1） | [configs/example/xiangshan.py:337](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:337) | 条件启用 · [16, 16, 16]（--ideal-kuanglangv1） | [configs/example/xiangshan.py:332](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:332) |
| IQ 回滚 | 已映射 · 按提交边界清除年轻指令或访存项 | [src/cpu/o3/iew.cc:876](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/iew.cc:876) | 已映射 · 按提交边界清除年轻指令或访存项 | [src/cpu/o3/iew.cc:536](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/iew.cc:536) |
| IQ · intIQ0 | 未列此项 | — | 已映射 · 容量 18 · 输入端口 2 | [configs/common/FUScheduler.py:31](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:31) |
| IQ · intIQ1 | 未列此项 | — | 已映射 · 容量 18 · 输入端口 2 | [configs/common/FUScheduler.py:35](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:35) |
| IQ · intIQ2 | 未列此项 | — | 已映射 · 容量 18 · 输入端口 2 | [configs/common/FUScheduler.py:39](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:39) |
| IQ · intIQ3 | 未列此项 | — | 已映射 · 容量 18 · 输入端口 2 | [configs/common/FUScheduler.py:43](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:43) |
| IQ · ld0 | 未列此项 | — | 已映射 · 容量 18 · 输入端口 2 | [configs/common/FUScheduler.py:49](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:49) |
| IQ · ld1 | 未列此项 | — | 已映射 · 容量 18 · 输入端口 2 | [configs/common/FUScheduler.py:52](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:52) |
| IQ · st0 | 未列此项 | — | 已映射 · 容量 18 · 输入端口 2 | [configs/common/FUScheduler.py:56](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:56) |
| IQ · st1 | 未列此项 | — | 已映射 · 容量 18 · 输入端口 2 | [configs/common/FUScheduler.py:60](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:60) |
| IQ · fpIQ0 | 未列此项 | — | 已映射 · 容量 32 · 输入端口 2 | [configs/common/FUScheduler.py:67](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:67) |
| IQ · fpIQ1 | 未列此项 | — | 已映射 · 容量 32 · 输入端口 2 | [configs/common/FUScheduler.py:73](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:73) |
| IQ · fpIQ2 | 未列此项 | — | 已映射 · 容量 32 · 输入端口 2 | [configs/common/FUScheduler.py:79](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:79) |
| IQ · fpIQ3 | 未列此项 | — | 已映射 · 容量 32 · 输入端口 2 | [configs/common/FUScheduler.py:86](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:86) |
| intIQ0 / 出口 0 | 未列此项 | — | 已映射 · FU IntALU · 读端口 整数0(P0), 整数1(P0) | [configs/common/FUScheduler.py:32](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:32) |
| intIQ0 / 出口 1 | 未列此项 | — | 已映射 · FU IntBRU · 读端口 整数7(P2), 整数6(P1) | [configs/common/FUScheduler.py:33](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:33) |
| intIQ1 / 出口 0 | 未列此项 | — | 已映射 · FU IntALU · 读端口 整数2(P0), 整数3(P0) | [configs/common/FUScheduler.py:36](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:36) |
| intIQ1 / 出口 1 | 未列此项 | — | 已映射 · FU IntBRU · 读端口 整数5(P2), 整数4(P1) | [configs/common/FUScheduler.py:37](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:37) |
| intIQ2 / 出口 0 | 未列此项 | — | 已映射 · FU IntALU · 读端口 整数4(P0), 整数5(P0) | [configs/common/FUScheduler.py:40](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:40) |
| intIQ2 / 出口 1 | 未列此项 | — | 已映射 · FU IntBRU · 读端口 整数3(P1), 整数2(P1) | [configs/common/FUScheduler.py:41](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:41) |
| intIQ3 / 出口 0 | 未列此项 | — | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数6(P0), 整数7(P0) | [configs/common/FUScheduler.py:44](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:44) |
| intIQ3 / 出口 1 | 未列此项 | — | 已映射 · FU IntALU + IntMult + IntDiv + IntMisc + INT_VFP · 读端口 整数1(P2), 整数0(P2) | [configs/common/FUScheduler.py:45](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:45) |
| ld0 / 出口 0 | 未列此项 | — | 已映射 · FU ReadPort · 读端口 整数7(P1) | [configs/common/FUScheduler.py:50](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:50) |
| ld1 / 出口 0 | 未列此项 | — | 已映射 · FU ReadPort · 读端口 整数5(P1) | [configs/common/FUScheduler.py:53](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:53) |
| ld1 / 出口 1 | 未列此项 | — | 已映射 · FU ReadPort · 读端口 整数3(P2) | [configs/common/FUScheduler.py:54](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:54) |
| st0 / 出口 0 | 未列此项 | — | 已映射 · FU WritePort · 读端口 整数1(P1) | [configs/common/FUScheduler.py:57](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:57) |
| st0 / 出口 1 | 未列此项 | — | 已映射 · FU StoreDataPort · 读端口 整数6(P2), 浮点16(P0) | [configs/common/FUScheduler.py:58](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:58) |
| st1 / 出口 0 | 未列此项 | — | 已映射 · FU WritePort · 读端口 整数0(P1) | [configs/common/FUScheduler.py:61](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:61) |
| st1 / 出口 1 | 未列此项 | — | 已映射 · FU StoreDataPort · 读端口 整数4(P2), 浮点17(P0) | [configs/common/FUScheduler.py:62](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:62) |
| fpIQ0 / 出口 0 | 未列此项 | — | 已映射 · FU VAU + VMA + SFT + MSC_0 + FAU + FMA · 读端口 浮点0(P0), 浮点1(P0), 浮点2(P0) | [configs/common/FUScheduler.py:68](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:68) |
| fpIQ1 / 出口 0 | 未列此项 | — | 已映射 · FU VAU + VMA + SFT + MSC_0 + FAU + FMA · 读端口 浮点3(P0), 浮点4(P0), 浮点5(P0) | [configs/common/FUScheduler.py:74](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:74) |
| fpIQ2 / 出口 0 | 未列此项 | — | 已映射 · FU VAU + SFT + RED + MSC_0 + MSC_1 + FAU + FAU_CMP + FMA + FCV_F2F + FCV_F2I + FCV_I2F + FP_MISC · 读端口 浮点6(P0), 浮点7(P0), 浮点8(P0), 整数8(P0) | [configs/common/FUScheduler.py:80](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:80) |
| fpIQ3 / 出口 0 | 未列此项 | — | 已映射 · FU VAU + SFT + RED + DIV + MSC_0 + MSC_1 + PRM + FAU + FAU_CMP + FMA + FDV + FCV_F2F + FCV_F2I + FCV_I2F · 读端口 浮点9(P0), 浮点10(P0), 浮点11(P0) | [configs/common/FUScheduler.py:87](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:87) |
| FU · FP_MISC | 未列此项 | — | 已映射 · FloatCvtF2F, FloatCvtF2I, FloatMv | [src/cpu/o3/FuncUnitConfig.py:90](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FuncUnitConfig.py:90) |
| 唤醒源 · intIQ0 | 未列此项 | — | 已映射 · intIQ0, intIQ1, intIQ2, intIQ3, ld0, ld1, st0, st1 | [configs/common/FUScheduler.py:99](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:99) |
| 唤醒源 · intIQ1 | 未列此项 | — | 已映射 · intIQ0, intIQ1, intIQ2, intIQ3, ld0, ld1, st0, st1 | [configs/common/FUScheduler.py:100](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:100) |
| 唤醒源 · intIQ2 | 未列此项 | — | 已映射 · intIQ0, intIQ1, intIQ2, intIQ3, ld0, ld1, st0, st1 | [configs/common/FUScheduler.py:101](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:101) |
| 唤醒源 · intIQ3 | 未列此项 | — | 已映射 · intIQ0, intIQ1, intIQ2, intIQ3, ld0, ld1, st0, st1, fpIQ0, fpIQ1, fpIQ2, fpIQ3 | [configs/common/FUScheduler.py:102](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:102) |
| 唤醒源 · ld0 | 未列此项 | — | 已映射 · intIQ0, intIQ1, intIQ2, intIQ3, ld0, ld1, st0, st1, fpIQ0, fpIQ1, fpIQ2, fpIQ3 | [configs/common/FUScheduler.py:104](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:104) |
| 唤醒源 · ld1 | 未列此项 | — | 已映射 · intIQ0, intIQ1, intIQ2, intIQ3, ld0, ld1, st0, st1, fpIQ0, fpIQ1, fpIQ2, fpIQ3 | [configs/common/FUScheduler.py:106](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:106) |
| 唤醒源 · st0 | 未列此项 | — | 已映射 · 无发送通道 | [configs/common/FUScheduler.py:98](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:98) |
| 唤醒源 · st1 | 未列此项 | — | 已映射 · 无发送通道 | [configs/common/FUScheduler.py:98](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:98) |
| 唤醒源 · fpIQ0 | 未列此项 | — | 已映射 · fpIQ0, fpIQ1, fpIQ2, fpIQ3, st0, st1 | [configs/common/FUScheduler.py:108](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:108) |
| 唤醒源 · fpIQ1 | 未列此项 | — | 已映射 · fpIQ0, fpIQ1, fpIQ2, fpIQ3, st0, st1 | [configs/common/FUScheduler.py:109](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:109) |
| 唤醒源 · fpIQ2 | 未列此项 | — | 已映射 · fpIQ0, fpIQ1, fpIQ2, fpIQ3, st0, st1, intIQ0, intIQ1, intIQ2, intIQ3 | [configs/common/FUScheduler.py:110](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:110) |
| 唤醒源 · fpIQ3 | 未列此项 | — | 已映射 · fpIQ0, fpIQ1, fpIQ2, fpIQ3, st0, st1, intIQ0, intIQ1, intIQ2, intIQ3 | [configs/common/FUScheduler.py:112](D:/codex-project/model-convert/zenas-dev/configs/common/FUScheduler.py:112) |

</details>

### Commit

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| ROB 容量 | 已映射 · 160 · [src/cpu/o3/BaseO3CPU.py:238](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:238) | 已映射 · 160 · [src/cpu/o3/BaseO3CPU.py:227](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:227) |
| ROB 容量 · 条件配置 | 条件启用 · 384 · [configs/example/xiangshan.py:334](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:334) | 条件启用 · 256 · [configs/example/xiangshan.py:329](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:329) |
| Load 值预测失配 | 条件启用 · LSQ → IEW → Commit · [src/cpu/o3/lsq_unit.cc:3410](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/lsq_unit.cc:3410) | 未列此项 |

覆盖记录数按两页顺序列示，已映射 9/9，合并 1/1，条件启用 4/3，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · Commit | [src/cpu/o3/commit.cc:823](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/commit.cc:823) | 已映射 · Commit | [src/cpu/o3/commit.cc:819](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/commit.cc:819) |
| 内部组件 | 已映射 · ROB entries、队首检查、Retire、Trap、恢复仲裁、ROB 回滚、Commit 广播、Trap event、精确异常清空 | [src/cpu/o3/commit.cc:823](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/commit.cc:823) | 已映射 · ROB entries、队首检查、Retire、Trap、恢复仲裁、ROB 回滚、Commit 广播、Trap event、精确异常清空 | [src/cpu/o3/commit.cc:819](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/commit.cc:819) |
| 实现归属 | 合并 · cpu.commit · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:456](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/cpu.hh:456) | 合并 · cpu.commit · CPU 内部 C++ 成员 | [src/cpu/o3/cpu.hh:446](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/cpu.hh:446) |
| 误预测仲裁 | 已映射 · 存在可接受的 IEW squash 请求 | [src/cpu/o3/commit.cc:1035](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/commit.cc:1035) | 已映射 · 存在可接受的 IEW squash 请求 | [src/cpu/o3/commit.cc:1031](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/commit.cc:1031) |
| ROB 清理 | 已映射 · 保留恢复边界，丢弃年轻指令 | [src/cpu/o3/commit.cc:1107](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/commit.cc:1107) | 已映射 · 保留恢复边界，丢弃年轻指令 | [src/cpu/o3/commit.cc:1103](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/commit.cc:1103) |
| 精确异常 | 已映射 · squashAll + isTrapSquash | [src/cpu/o3/commit.cc:756](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/commit.cc:756) | 已映射 · squashAll + isTrapSquash | [src/cpu/o3/commit.cc:752](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/commit.cc:752) |
| 恢复 PC | 已映射 · Fetch 使用 Commit 提供的 PC | [src/cpu/o3/fetch.cc:1659](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/fetch.cc:1659) | 已映射 · Fetch 使用 Commit 提供的 PC | [src/cpu/o3/fetch.cc:1494](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/fetch.cc:1494) |
| numROBEntries 声明 | 已映射 · 160 | [src/cpu/o3/BaseO3CPU.py:238](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:238) | 已映射 · 160 | [src/cpu/o3/BaseO3CPU.py:227](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:227) |
| numROBEntries 配置赋值 | 条件启用 · 384（--ideal-kuanglangv1） | [configs/example/xiangshan.py:334](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:334) | 条件启用 · 256（--ideal-kuanglangv1） | [configs/example/xiangshan.py:329](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:329) |
| squashWidth 声明 | 已映射 · 8 | [src/cpu/o3/BaseO3CPU.py:177](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:177) | 已映射 · 8 | [src/cpu/o3/BaseO3CPU.py:166](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:166) |
| squashWidth 配置赋值 | 条件启用 · 10（--ideal-kuanglangv1） | [configs/example/xiangshan.py:322](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:322) | 条件启用 · 12（--ideal-kuanglangv1） | [configs/example/xiangshan.py:320](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:320) |
| Load 值预测失配 | 条件启用 · LSQ → IEW → Commit（编译时 LVP_ON，Load 具有预测且实际值与预测值不同） | [src/cpu/o3/lsq_unit.cc:3410](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/lsq_unit.cc:3410) | 未列此项 | — |
| ROB 容量 | 已映射 · 160 | [src/cpu/o3/BaseO3CPU.py:238](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:238) | 已映射 · 160 | [src/cpu/o3/BaseO3CPU.py:227](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:227) |
| ROB 容量 · 条件配置 | 条件启用 · 384（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:334](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:334) | 条件启用 · 256（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:329](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:329) |

</details>

### LSU / LSQ

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| LQ 容量 | 已映射 · 80 · [src/cpu/o3/BaseO3CPU.py:190](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:190) | 已映射 · 80 · [src/cpu/o3/BaseO3CPU.py:179](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:179) |
| SQ 容量 | 已映射 · 64 · [src/cpu/o3/BaseO3CPU.py:191](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:191) | 已映射 · 64 · [src/cpu/o3/BaseO3CPU.py:180](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:180) |
| Store Buffer 容量 · 条件配置 | 条件启用 · 48 · [configs/example/xiangshan.py:329](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:329) | 条件启用 · 24 · [configs/example/xiangshan.py:324](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:324) |

覆盖记录数按两页顺序列示，已映射 13/13，合并 1/1，条件启用 8/8，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · LSU / LSQ | [src/cpu/o3/lsq.cc:100](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/lsq.cc:100) | 已映射 · LSU / LSQ | [src/cpu/o3/lsq.cc:100](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/lsq.cc:100) |
| 内部组件 | 已映射 · Load Queue、Store Queue、Store Buffer、LSQRequest、Load completion、Store Buffer 转发 | [src/cpu/o3/lsq.cc:100](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/lsq.cc:100) | 已映射 · Load Queue、Store Queue、Store Buffer、LSQRequest、Load completion、Store Buffer 转发 | [src/cpu/o3/lsq.cc:100](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/lsq.cc:100) |
| 实现归属 | 合并 · cpu.iew.ldstQueue · CPU 内部 C++ 成员 | [src/cpu/o3/iew.hh:543](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/iew.hh:543) | 合并 · cpu.iew.ldstQueue · CPU 内部 C++ 成员 | [src/cpu/o3/iew.hh:451](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/iew.hh:451) |
| LQEntries 声明 | 已映射 · 80 | [src/cpu/o3/BaseO3CPU.py:190](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:190) | 已映射 · 80 | [src/cpu/o3/BaseO3CPU.py:179](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:179) |
| LQEntries 配置赋值 | 条件启用 · 128（--ideal-kuanglangv1） | [configs/example/xiangshan.py:327](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:327) | 条件启用 · 128（--ideal-kuanglangv1） | [configs/example/xiangshan.py:322](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:322) |
| SQEntries 声明 | 已映射 · 64 | [src/cpu/o3/BaseO3CPU.py:191](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:191) | 已映射 · 64 | [src/cpu/o3/BaseO3CPU.py:180](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:180) |
| SQEntries 配置赋值 | 条件启用 · 64（--ideal-kuanglangv1） | [configs/example/xiangshan.py:328](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:328) | 条件启用 · 64（--ideal-kuanglangv1） | [configs/example/xiangshan.py:323](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:323) |
| SbufferEntries 声明 | 已映射 · 16 | [src/cpu/o3/BaseO3CPU.py:196](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:196) | 已映射 · 16 | [src/cpu/o3/BaseO3CPU.py:185](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:185) |
| SbufferEntries 配置赋值 | 条件启用 · 48（--ideal-kuanglangv1） | [configs/example/xiangshan.py:329](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:329) | 条件启用 · 24（--ideal-kuanglangv1） | [configs/example/xiangshan.py:324](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:324) |
| LSQ 回滚 | 已映射 · 按提交边界清除年轻指令或访存项 | [src/cpu/o3/iew.cc:879](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/iew.cc:879) | 已映射 · 按提交边界清除年轻指令或访存项 | [src/cpu/o3/iew.cc:539](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/iew.cc:539) |
| LQ 容量 | 已映射 · 80 | [src/cpu/o3/BaseO3CPU.py:190](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:190) | 已映射 · 80 | [src/cpu/o3/BaseO3CPU.py:179](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:179) |
| LQ 容量 · 条件配置 | 条件启用 · 128（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:327](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:327) | 条件启用 · 128（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:322](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:322) |
| SQ 容量 | 已映射 · 64 | [src/cpu/o3/BaseO3CPU.py:191](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:191) | 已映射 · 64 | [src/cpu/o3/BaseO3CPU.py:180](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:180) |
| SQ 容量 · 条件配置 | 条件启用 · 64（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:328](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:328) | 条件启用 · 64（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:323](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:323) |
| Store Buffer 容量 | 已映射 · 16 | [src/cpu/o3/BaseO3CPU.py:196](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:196) | 已映射 · 16 | [src/cpu/o3/BaseO3CPU.py:185](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:185) |
| Store Buffer 容量 · 条件配置 | 条件启用 · 48（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:329](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:329) | 条件启用 · 24（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:324](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:324) |
| Store Buffer 排出阈值 | 已映射 · 7 | [src/cpu/o3/BaseO3CPU.py:197](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:197) | 已映射 · 7 | [src/cpu/o3/BaseO3CPU.py:186](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:186) |
| Store Buffer 排出阈值 · 条件配置 | 条件启用 · 8（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:330](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:330) | 条件启用 · 8（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:325](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:325) |
| Load miss 重放 | 已映射 · 启用 | [src/cpu/o3/BaseO3CPU.py:217](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:217) | 已映射 · 启用 | [src/cpu/o3/BaseO3CPU.py:206](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:206) |
| Store 写回级 | 已映射 · 4 | [src/cpu/o3/BaseO3CPU.py:200](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/BaseO3CPU.py:200) | 已映射 · 4 | [src/cpu/o3/BaseO3CPU.py:189](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:189) |
| Store 写回级 · 条件配置 | 条件启用 · 4（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:346](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:346) | 条件启用 · 4（args.ideal_kuanglangv1） | [configs/example/xiangshan.py:342](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:342) |
| LSQ 响应 | 已映射 · DCache 响应按 Packet 的 LSQRequest 完成 | [src/cpu/o3/lsq.cc:1713](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/lsq.cc:1713) | 已映射 · DCache 响应按 Packet 的 LSQRequest 完成 | [src/cpu/o3/lsq.cc:1664](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/lsq.cc:1664) |

</details>

### MMU

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 遍历根层级 | 条件启用 · 动态 root_level · [src/arch/riscv/pagetable_walker.cc:1539](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable_walker.cc:1539) | 条件启用 · SV48/SV39 分支 · [src/arch/riscv/pagetable_walker.cc:1532](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/pagetable_walker.cc:1532) |
| 层级数 | 已映射 · 按虚拟地址位数求页表级数 · [src/arch/riscv/pagetable.hh:75](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable.hh:75) | 条件启用 · SV39 从 2 级、SV48 从 3 级开始，级编号从 0 起 · [src/arch/riscv/pagetable_walker.cc:1532](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/pagetable_walker.cc:1532) |
| 扩展分页模式 | 条件启用 · SV48 / SV57 · [src/arch/riscv/pagetable.hh:81](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable.hh:81) | 未列此项 |

覆盖记录数按两页顺序列示，已映射 10/9，合并 0/0，条件启用 2/2，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · MMU | [src/arch/riscv/RiscvMMU.py:46](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/RiscvMMU.py:46) | 已映射 · MMU | [src/arch/riscv/RiscvMMU.py:46](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/RiscvMMU.py:46) |
| 内部组件 | 已映射 · ITLB、DTLB、Shared L2 TLB、I-side walker、D-side walker、SATP / 页表层级 | [src/arch/riscv/RiscvMMU.py:46](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/RiscvMMU.py:46) | 已映射 · ITLB、DTLB、Shared L2 TLB、I-side walker、D-side walker、SATP / 页表层级 | [src/arch/riscv/RiscvMMU.py:46](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/RiscvMMU.py:46) |
| 配置对象路径 | 已映射 · system.cpu[i].mmu | [src/arch/riscv/RiscvCPU.py:53](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/RiscvCPU.py:53) | 已映射 · system.cpu[i].mmu | [src/arch/riscv/RiscvCPU.py:53](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/RiscvCPU.py:53) |
| 遍历根层级 | 条件启用 · 动态 root_level（由当前 SATP 模式和扩展翻译开关决定） | [src/arch/riscv/pagetable_walker.cc:1539](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable_walker.cc:1539) | 条件启用 · SV48/SV39 分支（由当前 SATP 模式和扩展翻译开关决定） | [src/arch/riscv/pagetable_walker.cc:1532](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/pagetable_walker.cc:1532) |
| L2 TLB miss → walker | 已映射 · fault = walker-&gt;start( 0, tc, translation, req, mode, false, false, root_level, false, 0); | [src/arch/riscv/tlb.cc:1898](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/tlb.cc:1898) | 已映射 · fault = walker-&gt;start(0, tc, translation, req, mode, false, false, 2, false, 0); | [src/arch/riscv/tlb.cc:1867](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/tlb.cc:1867) |
| 层级数 | 已映射 · 按虚拟地址位数求页表级数 | [src/arch/riscv/pagetable.hh:75](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable.hh:75) | 条件启用 · SV39 从 2 级、SV48 从 3 级开始，级编号从 0 起（openSv48 且 SATP 为 SV48 时走 3 级分支） | [src/arch/riscv/pagetable_walker.cc:1532](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/pagetable_walker.cc:1532) |
| 扩展分页模式 | 条件启用 · SV48 / SV57（扩展分页启用且 SATP 选择相应模式） | [src/arch/riscv/pagetable.hh:81](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable.hh:81) | 未列此项 | — |
| ITB walker 端口 | 已映射 · itb.walker.port | [src/arch/riscv/RiscvMMU.py:65](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/RiscvMMU.py:65) | 已映射 · itb.walker.port | [src/arch/riscv/RiscvMMU.py:65](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/RiscvMMU.py:65) |
| DTB walker 端口 | 已映射 · dtb.walker.port | [src/arch/riscv/RiscvMMU.py:66](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/RiscvMMU.py:66) | 已映射 · dtb.walker.port | [src/arch/riscv/RiscvMMU.py:66](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/RiscvMMU.py:66) |
| 页表读取 | 已映射 · 发送 PTE 请求 | [src/arch/riscv/pagetable_walker.cc:246](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable_walker.cc:246) | 已映射 · 发送 PTE 请求 | [src/arch/riscv/pagetable_walker.cc:246](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/pagetable_walker.cc:246) |
| WalkerPort 响应 | 已映射 · 接收 PTE 数据 | [src/arch/riscv/pagetable_walker.cc:189](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable_walker.cc:189) | 已映射 · 接收 PTE 数据 | [src/arch/riscv/pagetable_walker.cc:189](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/pagetable_walker.cc:189) |
| 成功叶项回填 | 已映射 · 插入发起翻译的 TLB | [src/arch/riscv/pagetable_walker.cc:1268](D:/huanjian-project/stage-two/GEM5-1/src/arch/riscv/pagetable_walker.cc:1268) | 已映射 · 插入发起翻译的 TLB | [src/arch/riscv/pagetable_walker.cc:1267](D:/codex-project/model-convert/zenas-dev/src/arch/riscv/pagetable_walker.cc:1267) |

</details>

### L1 I-Cache

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 缓存容量 | 已映射 · 64kB · [configs/common/Options.py:158](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:158) | 已映射 · 64kB · [configs/common/Options.py:158](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:158) |
| MSHR 数量 | 已映射 · 16 · [configs/common/Caches.py:60](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:60) | 已映射 · 16 · [configs/common/Caches.py:60](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:60) |
| 返回端口 | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp · [src/mem/cache/base.cc:3285](D:/huanjian-project/stage-two/GEM5-1/src/mem/cache/base.cc:3285) | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp · [src/mem/cache/base.cc:3285](D:/codex-project/model-convert/zenas-dev/src/mem/cache/base.cc:3285) |

覆盖记录数按两页顺序列示，已映射 6/6，合并 0/0，条件启用 1/1，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · L1 I-Cache | [configs/common/CacheConfig.py:185](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:185) | 已映射 · L1 I-Cache | [configs/common/CacheConfig.py:185](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:185) |
| 内部组件 | 已映射 · Tag / data、MSHR、Fill、Response、同一缓存行缺失合并 | [configs/common/CacheConfig.py:185](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:185) | 已映射 · Tag / data、MSHR、Fill、Response、同一缓存行缺失合并 | [configs/common/CacheConfig.py:185](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:185) |
| 配置对象路径 | 已映射 · system.cpu[i].icache | [src/cpu/BaseCPU.py:189](D:/huanjian-project/stage-two/GEM5-1/src/cpu/BaseCPU.py:189) | 已映射 · system.cpu[i].icache | [src/cpu/BaseCPU.py:189](D:/codex-project/model-convert/zenas-dev/src/cpu/BaseCPU.py:189) |
| 缓存容量 | 已映射 · 64kB | [configs/common/Options.py:158](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:158) | 已映射 · 64kB | [configs/common/Options.py:158](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:158) |
| 缓存容量 · 条件配置 | 条件启用 · 64kB（args.ideal_kuanglangv1 且 args.caches） | [configs/example/xiangshan.py:394](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:394) | 条件启用 · 64kB（args.ideal_kuanglangv1 且 args.caches） | [configs/example/xiangshan.py:376](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:376) |
| MSHR 数量 | 已映射 · 16 | [configs/common/Caches.py:60](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:60) | 已映射 · 16 | [configs/common/Caches.py:60](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:60) |
| 返回端口 | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp | [src/mem/cache/base.cc:3285](D:/huanjian-project/stage-two/GEM5-1/src/mem/cache/base.cc:3285) | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp | [src/mem/cache/base.cc:3285](D:/codex-project/model-convert/zenas-dev/src/mem/cache/base.cc:3285) |

</details>

### L1 D-Cache

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 缓存容量 | 已映射 · 64kB · [configs/common/Options.py:155](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:155) | 已映射 · 64kB · [configs/common/Options.py:155](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:155) |
| MSHR 数量 | 已映射 · 16 · [configs/common/Caches.py:72](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:72) | 已映射 · 16 · [configs/common/Caches.py:72](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:72) |
| 缺失目标保留 | 已映射 · 6 · [configs/common/Caches.py:92](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:92) | 已映射 · 6 · [configs/common/Caches.py:92](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:92) |

覆盖记录数按两页顺序列示，已映射 7/7，合并 0/0，条件启用 3/3，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · L1 D-Cache | [configs/common/CacheConfig.py:186](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:186) | 已映射 · L1 D-Cache | [configs/common/CacheConfig.py:186](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:186) |
| 内部组件 | 已映射 · Tag / data、MSHR、Fill、Response、同一缓存行缺失合并 | [configs/common/CacheConfig.py:186](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:186) | 已映射 · Tag / data、MSHR、Fill、Response、同一缓存行缺失合并 | [configs/common/CacheConfig.py:186](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:186) |
| 配置对象路径 | 已映射 · system.cpu[i].dcache | [src/cpu/BaseCPU.py:190](D:/huanjian-project/stage-two/GEM5-1/src/cpu/BaseCPU.py:190) | 已映射 · system.cpu[i].dcache | [src/cpu/BaseCPU.py:190](D:/codex-project/model-convert/zenas-dev/src/cpu/BaseCPU.py:190) |
| 缓存容量 | 已映射 · 64kB | [configs/common/Options.py:155](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:155) | 已映射 · 64kB | [configs/common/Options.py:155](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:155) |
| 缓存容量 · 条件配置 | 条件启用 · 64kB（args.ideal_kuanglangv1 且 args.caches） | [configs/example/xiangshan.py:395](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:395) | 条件启用 · 64kB（args.ideal_kuanglangv1 且 args.caches） | [configs/example/xiangshan.py:377](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:377) |
| MSHR 数量 | 已映射 · 16 | [configs/common/Caches.py:72](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:72) | 已映射 · 16 | [configs/common/Caches.py:72](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:72) |
| MSHR 数量 · 条件配置 | 条件启用 · 32（args.ideal_kuanglangv1 且 args.caches） | [configs/example/xiangshan.py:397](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:397) | 条件启用 · 32（args.ideal_kuanglangv1 且 args.caches） | [configs/example/xiangshan.py:379](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:379) |
| 缺失目标保留 | 已映射 · 6 | [configs/common/Caches.py:92](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:92) | 已映射 · 6 | [configs/common/Caches.py:92](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:92) |
| 缺失目标保留 · 条件配置 | 条件启用 · 2（args.ideal_kuanglangv1 且 args.caches） | [configs/example/xiangshan.py:398](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:398) | 条件启用 · 2（args.ideal_kuanglangv1 且 args.caches） | [configs/example/xiangshan.py:380](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:380) |
| 返回端口 | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp | [src/mem/cache/base.cc:3285](D:/huanjian-project/stage-two/GEM5-1/src/mem/cache/base.cc:3285) | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp | [src/mem/cache/base.cc:3285](D:/codex-project/model-convert/zenas-dev/src/mem/cache/base.cc:3285) |

</details>

### L2 Cache

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 缓存容量 | 已映射 · 1MB · [configs/common/Options.py:161](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:161) | 已映射 · 1MB · [configs/common/Options.py:161](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:161) |
| MSHR 数量 | 已映射 · 64 · [configs/common/Caches.py:95](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:95) | 已映射 · 64 · [configs/common/Caches.py:95](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:95) |
| ITB walker 连接 | 已映射 · itb.walker.port → itb_walker_cache.cpu_side · [src/cpu/BaseCPU.py:197](D:/huanjian-project/stage-two/GEM5-1/src/cpu/BaseCPU.py:197) | 已映射 · itb.walker.port → itb_walker_cache.cpu_side · [src/cpu/BaseCPU.py:197](D:/codex-project/model-convert/zenas-dev/src/cpu/BaseCPU.py:197) |
| DTB walker 连接 | 已映射 · dtb.walker.port → dtb_walker_cache.cpu_side · [src/cpu/BaseCPU.py:197](D:/huanjian-project/stage-two/GEM5-1/src/cpu/BaseCPU.py:197) | 已映射 · dtb.walker.port → dtb_walker_cache.cpu_side · [src/cpu/BaseCPU.py:197](D:/codex-project/model-convert/zenas-dev/src/cpu/BaseCPU.py:197) |

覆盖记录数按两页顺序列示，已映射 8/8，合并 0/0，条件启用 1/1，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · L2 Cache | [configs/common/CacheConfig.py:124](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:124) | 已映射 · L2 Cache | [configs/common/CacheConfig.py:124](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:124) |
| 内部组件 | 已映射 · Tag / data、MSHR、Fill、Response、同一缓存行缺失合并 | [configs/common/CacheConfig.py:124](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:124) | 已映射 · Tag / data、MSHR、Fill、Response、同一缓存行缺失合并 | [configs/common/CacheConfig.py:124](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:124) |
| 配置对象路径 | 已映射 · system.l2_caches[i] | [configs/common/CacheConfig.py:124](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:124) | 已映射 · system.l2_caches[i] | [configs/common/CacheConfig.py:124](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:124) |
| 缓存容量 | 已映射 · 1MB | [configs/common/Options.py:161](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:161) | 已映射 · 1MB | [configs/common/Options.py:161](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:161) |
| 缓存容量 · 条件配置 | 条件启用 · 2MB（args.ideal_kuanglangv1 且 args.l2cache） | [configs/example/xiangshan.py:402](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:402) | 条件启用 · 2MB（args.ideal_kuanglangv1 且 args.l2cache） | [configs/example/xiangshan.py:384](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:384) |
| MSHR 数量 | 已映射 · 64 | [configs/common/Caches.py:95](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:95) | 已映射 · 64 | [configs/common/Caches.py:95](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:95) |
| 返回端口 | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp | [src/mem/cache/base.cc:3285](D:/huanjian-project/stage-two/GEM5-1/src/mem/cache/base.cc:3285) | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp | [src/mem/cache/base.cc:3285](D:/codex-project/model-convert/zenas-dev/src/mem/cache/base.cc:3285) |
| ITB walker 连接 | 已映射 · itb.walker.port → itb_walker_cache.cpu_side | [src/cpu/BaseCPU.py:197](D:/huanjian-project/stage-two/GEM5-1/src/cpu/BaseCPU.py:197) | 已映射 · itb.walker.port → itb_walker_cache.cpu_side | [src/cpu/BaseCPU.py:197](D:/codex-project/model-convert/zenas-dev/src/cpu/BaseCPU.py:197) |
| DTB walker 连接 | 已映射 · dtb.walker.port → dtb_walker_cache.cpu_side | [src/cpu/BaseCPU.py:197](D:/huanjian-project/stage-two/GEM5-1/src/cpu/BaseCPU.py:197) | 已映射 · dtb.walker.port → dtb_walker_cache.cpu_side | [src/cpu/BaseCPU.py:197](D:/codex-project/model-convert/zenas-dev/src/cpu/BaseCPU.py:197) |

</details>

### L3 Cache

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 缓存容量 | 已映射 · 16MB · [configs/common/Options.py:164](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:164) | 已映射 · 16MB · [configs/common/Options.py:164](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:164) |
| 缓存容量 · 条件配置 | 条件启用 · 32MB · [configs/example/xiangshan.py:409](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:409) | 未列此项 |
| MSHR 数量 | 已映射 · 64 · [configs/common/Caches.py:119](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:119) | 已映射 · 64 · [configs/common/Caches.py:119](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:119) |

覆盖记录数按两页顺序列示，已映射 6/6，合并 0/0，条件启用 2/1，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · L3 Cache | [configs/common/CacheConfig.py:163](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:163) | 已映射 · L3 Cache | [configs/common/CacheConfig.py:163](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:163) |
| 内部组件 | 已映射 · Tag / data、MSHR、Fill、Response、同一缓存行缺失合并 | [configs/common/CacheConfig.py:163](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:163) | 已映射 · Tag / data、MSHR、Fill、Response、同一缓存行缺失合并 | [configs/common/CacheConfig.py:163](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:163) |
| 配置对象路径 | 已映射 · system.l3 | [configs/common/CacheConfig.py:163](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:163) | 已映射 · system.l3 | [configs/common/CacheConfig.py:163](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:163) |
| 缓存容量 | 已映射 · 16MB | [configs/common/Options.py:164](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:164) | 已映射 · 16MB | [configs/common/Options.py:164](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:164) |
| 缓存容量 · 条件配置 | 条件启用 · 32MB（args.ideal_kuanglangv1 且 args.l3cache） | [configs/example/xiangshan.py:409](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:409) | 未列此项 | — |
| MSHR 数量 | 已映射 · 64 | [configs/common/Caches.py:119](D:/huanjian-project/stage-two/GEM5-1/configs/common/Caches.py:119) | 已映射 · 64 | [configs/common/Caches.py:119](D:/codex-project/model-convert/zenas-dev/configs/common/Caches.py:119) |
| MSHR 数量 · 条件配置 | 条件启用 · 128（args.ideal_kuanglangv1 且 args.l3cache） | [configs/example/xiangshan.py:414](D:/huanjian-project/stage-two/GEM5-1/configs/example/xiangshan.py:414) | 条件启用 · 128（args.ideal_kuanglangv1 且 args.l3cache） | [configs/example/xiangshan.py:395](D:/codex-project/model-convert/zenas-dev/configs/example/xiangshan.py:395) |
| 返回端口 | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp | [src/mem/cache/base.cc:3285](D:/huanjian-project/stage-two/GEM5-1/src/mem/cache/base.cc:3285) | 已映射 · mem_side.recvTimingResp → cache.recvTimingResp | [src/mem/cache/base.cc:3285](D:/codex-project/model-convert/zenas-dev/src/mem/cache/base.cc:3285) |

</details>

### 系统互联

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 请求侧端口记录 | 已映射 · 以请求指针保存响应目的端 · [src/mem/coherent_xbar.cc:349](D:/huanjian-project/stage-two/GEM5-1/src/mem/coherent_xbar.cc:349) | 已映射 · 以请求指针保存响应目的端 · [src/mem/coherent_xbar.cc:349](D:/codex-project/model-convert/zenas-dev/src/mem/coherent_xbar.cc:349) |
| 响应侧查找 | 已映射 · 使用请求指针定位返回端口 · [src/mem/coherent_xbar.cc:462](D:/huanjian-project/stage-two/GEM5-1/src/mem/coherent_xbar.cc:462) | 已映射 · 使用请求指针定位返回端口 · [src/mem/coherent_xbar.cc:462](D:/codex-project/model-convert/zenas-dev/src/mem/coherent_xbar.cc:462) |
| 内存连接 | 已映射 · mem_ctrls[i].port ← membus.mem_side_ports · [configs/common/MemConfig.py:277](D:/huanjian-project/stage-two/GEM5-1/configs/common/MemConfig.py:277) | 已映射 · mem_ctrls[i].port ← membus.mem_side_ports · [configs/common/MemConfig.py:277](D:/codex-project/model-convert/zenas-dev/configs/common/MemConfig.py:277) |

覆盖记录数按两页顺序列示，已映射 6/6，合并 0/0，条件启用 0/0，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · 系统互联 | [configs/common/CacheConfig.py:168](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:168) | 已映射 · 系统互联 | [configs/common/CacheConfig.py:168](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:168) |
| 内部组件 | 已映射 · 地址译码、Request layer、Response layer | [configs/common/CacheConfig.py:168](D:/huanjian-project/stage-two/GEM5-1/configs/common/CacheConfig.py:168) | 已映射 · 地址译码、Request layer、Response layer | [configs/common/CacheConfig.py:168](D:/codex-project/model-convert/zenas-dev/configs/common/CacheConfig.py:168) |
| 配置对象路径 | 已映射 · system.membus | [configs/common/FSConfig.py:672](D:/huanjian-project/stage-two/GEM5-1/configs/common/FSConfig.py:672) | 已映射 · system.membus | [configs/common/FSConfig.py:672](D:/codex-project/model-convert/zenas-dev/configs/common/FSConfig.py:672) |
| 请求侧端口记录 | 已映射 · 以请求指针保存响应目的端 | [src/mem/coherent_xbar.cc:349](D:/huanjian-project/stage-two/GEM5-1/src/mem/coherent_xbar.cc:349) | 已映射 · 以请求指针保存响应目的端 | [src/mem/coherent_xbar.cc:349](D:/codex-project/model-convert/zenas-dev/src/mem/coherent_xbar.cc:349) |
| 响应侧查找 | 已映射 · 使用请求指针定位返回端口 | [src/mem/coherent_xbar.cc:462](D:/huanjian-project/stage-two/GEM5-1/src/mem/coherent_xbar.cc:462) | 已映射 · 使用请求指针定位返回端口 | [src/mem/coherent_xbar.cc:462](D:/codex-project/model-convert/zenas-dev/src/mem/coherent_xbar.cc:462) |
| 内存连接 | 已映射 · mem_ctrls[i].port ← membus.mem_side_ports（普通系统总线；HMC 有独立 xbar 分支） | [configs/common/MemConfig.py:277](D:/huanjian-project/stage-two/GEM5-1/configs/common/MemConfig.py:277) | 已映射 · mem_ctrls[i].port ← membus.mem_side_ports（普通系统总线；HMC 有独立 xbar 分支） | [configs/common/MemConfig.py:277](D:/codex-project/model-convert/zenas-dev/configs/common/MemConfig.py:277) |

</details>

### 内存控制器

| 核查项 | GEM5-1 | GEM5-2 |
|---|---|---|
| 内存模型 | 已映射 · DRAMsim3 · [configs/common/Options.py:120](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:120) | 已映射 · DRAMsim3 · [configs/common/Options.py:120](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:120) |
| DRAM 时序配置文件 | 已映射 · ext/dramsim3/xiangshan_configs/xiangshan_DDR4_8Gb_x8_3200_8ch_hybrid_CL22.ini · [configs/common/XSConfig.py:114](D:/huanjian-project/stage-two/GEM5-1/configs/common/XSConfig.py:114) | 已映射 · ext/dramsim3/xiangshan_configs/xiangshan_DDR4_8Gb_x8_3200_8ch_hybrid_CL22.ini · [configs/common/XSConfig.py:114](D:/codex-project/model-convert/zenas-dev/configs/common/XSConfig.py:114) |

覆盖记录数按两页顺序列示，已映射 5/5，合并 0/0，条件启用 0/0，未知 0/0，缺失 0/0。

<details><summary>全部覆盖项、适用条件与源码行</summary>

| 结构项 | GEM5-1 结果 | GEM5-1 依据 | GEM5-2 结果 | GEM5-2 依据 |
|---|---|---|---|---|
| 模块映射 | 已映射 · 内存控制器 | [configs/common/MemConfig.py:289](D:/huanjian-project/stage-two/GEM5-1/configs/common/MemConfig.py:289) | 已映射 · 内存控制器 | [configs/common/MemConfig.py:289](D:/codex-project/model-convert/zenas-dev/configs/common/MemConfig.py:289) |
| 内部组件 | 已映射 · MemoryPort、Outstanding reads、DRAMsim3、Response queue、请求重试 | [configs/common/MemConfig.py:289](D:/huanjian-project/stage-two/GEM5-1/configs/common/MemConfig.py:289) | 已映射 · MemoryPort、Outstanding reads、DRAMsim3、Response queue、请求重试 | [configs/common/MemConfig.py:289](D:/codex-project/model-convert/zenas-dev/configs/common/MemConfig.py:289) |
| 配置对象路径 | 已映射 · system.mem_ctrls[i] | [configs/common/MemConfig.py:289](D:/huanjian-project/stage-two/GEM5-1/configs/common/MemConfig.py:289) | 已映射 · system.mem_ctrls[i] | [configs/common/MemConfig.py:289](D:/codex-project/model-convert/zenas-dev/configs/common/MemConfig.py:289) |
| 内存模型 | 已映射 · DRAMsim3 | [configs/common/Options.py:120](D:/huanjian-project/stage-two/GEM5-1/configs/common/Options.py:120) | 已映射 · DRAMsim3 | [configs/common/Options.py:120](D:/codex-project/model-convert/zenas-dev/configs/common/Options.py:120) |
| DRAM 时序配置文件 | 已映射 · ext/dramsim3/xiangshan_configs/xiangshan_DDR4_8Gb_x8_3200_8ch_hybrid_CL22.ini（选择 DRAMsim3；未提供 ini 时使用配置入口给出的文件） | [configs/common/XSConfig.py:114](D:/huanjian-project/stage-two/GEM5-1/configs/common/XSConfig.py:114) | 已映射 · ext/dramsim3/xiangshan_configs/xiangshan_DDR4_8Gb_x8_3200_8ch_hybrid_CL22.ini（选择 DRAMsim3；未提供 ini 时使用配置入口给出的文件） | [configs/common/XSConfig.py:114](D:/codex-project/model-convert/zenas-dev/configs/common/XSConfig.py:114) |

</details>

## 当前仍需核对

- Rename · RAT 硬件 bank 及端口数（未知）。GEM5-1 · UnifiedRenameMap 提供按寄存器类别寻址的接口，未获得物理 RAT 分库和读写端口配置 · [src/cpu/o3/rename_map.hh:168](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/rename_map.hh:168)。GEM5-2 · UnifiedRenameMap 提供按寄存器类别寻址的接口，未获得物理 RAT 分库和读写端口配置 · [src/cpu/o3/rename_map.hh:168](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/rename_map.hh:168)。
- Issue / Execute · 寄存器写端口（未知）。GEM5-1 · 当前 IssuePort.rp 声明读端口；独立写端口连接待核对 · [src/cpu/o3/FUPool.py:64](D:/huanjian-project/stage-two/GEM5-1/src/cpu/o3/FUPool.py:64)。GEM5-2 · 当前 IssuePort.rp 声明读端口；独立写端口连接待核对 · [src/cpu/o3/FUPool.py:64](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/FUPool.py:64)。
- IFU · resident window replay（缺失）。GEM5-2 · 无对应声明与实现（检查 BaseO3CPU 类体及 Fetch 实现） · [src/cpu/o3/BaseO3CPU.py:80](D:/codex-project/model-convert/zenas-dev/src/cpu/o3/BaseO3CPU.py:80)。
- 源码页可以核对配置默认与条件覆盖。未附带实际运行配置的页面仍需同次运行的配置文件核对实例数量、端口绑定与参数有效值。
- 图中演示的步骤由源码映射生成。实际发生顺序、tick 与同周期事件顺序需由运行 trace 核对。

## 输入标识

- GEM5-1 · configs/example/xiangshan.py · HTML SHA-256 `e695e53d77021985696028bc704fcdc9907f3c570660993157754dec5524b756`
- GEM5-2 · configs/example/xiangshan.py · HTML SHA-256 `bff03697ebafc34b5ce56a764e1cc91de2944e2800b61056fc608cfc7c9c377d`
