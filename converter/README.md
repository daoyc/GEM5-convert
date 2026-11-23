# gem5 模型转换器

## 生成与打开页面

在 `model-convert` 根目录运行下面的命令。转换器只依赖 Python 标准库。单文件包内含源码分析器、架构映射、HTML 模板、样式及交互脚本。

```powershell
python converter/GEM5-converter.pyz D:/huanjian-project/stage-two/GEM5-1 --entry configs/example/xiangshan.py --name GEM5-1 --html GEM5-1.html
python converter/GEM5-converter.pyz ./zenas-dev --entry configs/example/xiangshan.py --name GEM5-2 --html GEM5-2.html
```

双击 [GEM5-1](../GEM5-1.html) 或 [GEM5-2 · zenas-dev](../GEM5-2.html) 即可离线打开，从[两模型入口](index.html)也可以切换。两页均从各自提供的源码独立生成。源码模式默认使用配置入口的选项；例如追加 `--set ideal_kuanglangv1=true --set bp_type=DecoupledBPUWithBTB` 可重算 ideal 与 BTB 组合。

进入 Issue 可看 IQ 组、发射端口和唤醒方向。进入 MMU 可看两侧 walker 的请求、响应和回填。展开“结构覆盖与模型对照”，在“载入对照模型”选择另一份 HTML，即会按当前模块显示两套源码的差异和各自的定位。“导入运行配置”可载入该模型的 gem5 config.json，切换所选 CPU 或切回源码。运行实例未导出的字段会显示“未导出”。[十轮核验记录](../iterations/README.md)和[逐模块覆盖清单](../iterations/COVERAGE.md)提供复核入口。

开发时修改本目录中的 Python 或查看器资源，运行 `python -B converter/build_portable.py` 重建可移植包。ZIP 内嵌相同查看器。通过脚本入口 `python converter/convert_model.py <源码> -o model.json --html result.html` 还可同时生成图数据与独立页面。

## 昆明湖 V3 源码映射

当输入目录包含 `configs/example/kmhv3.py` 时，转换器选择昆明湖 V3 映射，扫描实际源码，并逐条定位映射中的语句。映射描述 16 个模块、内部组件与逻辑流。每次转换都会重新解析参数值和行号，打包源码用于离线检查。无法唯一定位的语句进入诊断，缺少依据的演示场景自动排除。内置场景描述单核、非 trace、切片 L2 的默认路径。在“模型配置”中导入运行配置后，可按 CPU 对照运行值。真实执行事件通过“导入 trace”加载。


## zenas-dev 的组件映射与事件模板

生成器根据配置入口和源码调用位置创建模块内部节点、上下游端口与有向边。每个场景声明一串语义端点，转换时逐步检查端点和连接方向，写入对应的 edgeId。缓存命中、缺失与回填共用同一套模板，绑定至各级缓存和当前配置的下一级。模板需要的组件缺失、方向不符或存在无法消解的并行边时，该场景不生成。

打开离线页，点击模块可查看内部组件。悬停或用 Tab 聚焦节点可查看直接上下游。点击事件行、单步或播放，画布会标出发送端、接收端和对应的移动光点。演示与导入 trace 在场景选择器旁标明来源。源码与实例检查可查看其依据。

## 其他配置和输出方式

从本目录运行 `.\convert.cmd D:\codex-project\model-convert\zenas-dev`，可为 `configs/example/xiangshan.py` 生成 zenas-dev 页面。默认文件名取输入目录名。可通过 `--entry` 显式选择配置入口。

以下为自定义输出和实例选择示例。

```powershell
python convert_model.py D:/codex-project/model-convert/zenas-dev --entry configs/example/xiangshan.py -o models/zenas-dev.json --html zenas-dev.html
python convert_model.py D:/codex-project/model-convert/zenas-dev --config m5out/config.json --instance system.cpu --name run1 -o run1.json
python convert_model.py D:/codex-project/model-convert/zenas-dev --set bp-type=DecoupledBPUWithBTB --set l2_size=2MB -o selected.json
```

`--set` 记录这次转换选用的配置参数。zenas-dev 映射覆盖香山 classic cache 配置。动态预测器查表、运行期索引和 Ruby 专用缓存结构需要结合运行实例核对。其他配置入口仍可提取 SimObject 源码图。

`core-atlas/2` 同时保存声明、实例、关系、源码片段及架构映射。导入 `core-atlas/1` 后可继续搜索和浏览对象。声明默认、带条件的配置赋值及实例有效值分别保留。浏览器中的“运行配置”可直接加载同源 gem5 的原始 config.json；实例选择框控制显示范围。命令行也可传入 config.ini，其中端口方向依赖源码声明推断。

## 回放与验证

内置回放为基于源码编排的演示。真实 trace 使用 `name`、`viewId` 和 `steps`。每步提供 `edgeId`、`type`、`text`，可附 `tick`；大整数 tick 使用十进制字符串。昆明湖 V3 总览 ID 为 `overview`，zenas-dev 总览 ID 为 `xiangshan.overview`，模块视图使用模块 ID，实例检查使用 `source`。端口边 ID 可从源码检查器或 JSON 的 `connections` 中复制。旧式 `a`、`b` 在端点唯一时可用。

`test-config.json` 是 zenas-dev 的合成验收输入，包含源端口与目标端口下标交叉的两条并行连接。导入它后，使用 `test-trace.json` 验证同 tick 单步，使用 `test-trace-ambiguous.json` 验证错误提示与当前场景保留。

```powershell
$env:XS_GEM5_SOURCE="D:\codex-project\model-view\GEM5"
python -B -m unittest test_converter test_xs_conversion
```






