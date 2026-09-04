# Rabbit 接入 HCD-WF 的源代码改动及必要性评估

**评估日期：** 2026-08-12  
**评估对象：** ITER Rabbit 最新 `master`（已合并 `feature/DD4_IMAS_Python`）  
**基准提交：** `e99ad70a12d4bcd7be0b28422bfa2ca051c9c3ab`  
**目标部署：** DD 4.1.0、MUSCLE3 0.8、GCC 13.2 Rabbit 独立进程、Intel 2023b HCD-WF 其余进程

## 1. 结论摘要

当前 HCD-WF 使用的 Rabbit 是从 Schneim 的原始 Rabbit actor 派生出来的本地构建，
并不是一个完全独立重写的 actor。`feature/DD4_IMAS_Python` 已通过 MR !5 合并到 Rabbit
`master`。HCD-WF 兼容改动现已在最新 `master` 上最小化、提交并完成回归验证：

```text
.local_dev/rabbit_upstream_master_hcdwf_minimal
branch: HCD-WF/PDS
HEAD:   8d9ce5bcbeea48d524d7defba125e49e570eeea1
```

可移植补丁和 MR 说明分别为：

```text
actor_install/rabbit_master_e99ad70_hcdwf_minimal.patch
actor_install/rabbit_master_e99ad70_hcdwf_minimal_MR.md
```

对于我们已经确定的目标组合——场景 `ITER/4/105102@100 s`、DD 4.1.0、
GCC 13.2、MUSCLE3 0.8、Pure M3 Rabbit 以及下游 `HCD2CORE_SOURCES`——
**不能直接使用未经修改的 Schneim 原始代码**。至少有四项独立问题会阻止编译、Rabbit 执行
或完整 HCD-WF 执行：

1. `core_profiles.ion(:)` 的氢同位素/杂质索引假设不成立，会造成越界写入。
2. 输入只提供 `rho_tor_norm`，原代码却直接访问未填充的 `rho_tor`。
3. GCC 13.2 编译 `mod_eq.F90` 时发生 Fortran 前端内部错误（ICE）。
4. Rabbit 输出的碰撞离子缺少 `element.a` 和 `element.z_n`，导致
   `HCD2CORE_SOURCES` 物种匹配失败。

最小分支只保留上述四项硬性修复。MUSCLE3 端口接收顺序调整、大量输入检查和 Hybrid
iWrap 成功状态消息均不在这次准备推送的版本中，应按独立问题分别评审。

## 2. 代码来源、改动范围和当前版本状态

### 2.1 原始来源

原始开发分支为：

```text
/home/ITER/schneim/public/git/rabbit
branch: feature/DD4_IMAS_Python
HEAD:   a99bda8fec0d2b7b7bdade2cb0efbd5f87ea01b0
```

该提交现已合并到远端 `master@e99ad70`。最小兼容分支直接从该最新远端提交创建，没有修改
Schneim 的个人工作树。

### 2.2 原完整补丁与当前最小补丁

原完整补丁 `rabbit_feature_DD4_IMAS_Python_hcdwf.patch` 修改三个文件：

| 文件 | 增加 | 删除 | 目的 |
|---|---:|---:|---|
| `imas/src/rabbit_ids.f90` | 59 | 11 | 物种索引、径向坐标、输入保护、碰撞离子元数据 |
| `imas/src/rabbit_m3.f90` | 14 | 13 | 将 `F_INIT` wall 接收移到动态 `S` 端口之前 |
| `src/mod_eq.F90` | 31 | 36 | 绕过 GCC 13.2 Fortran 前端 ICE |
| **合计** | **104** | **60** | |

准备推送的最小分支只修改两个文件：

| 文件 | 增加 | 删除 | 目的 |
|---|---:|---:|---|
| `imas/src/rabbit_ids.f90` | 25 | 9 | 物种索引、规范化径向坐标、碰撞离子元数据 |
| `src/mod_eq.F90` | 9 | 14 | 以直接组件引用绕过 GCC 13.2 ICE |
| **合计** | **34** | **23** | |

### 2.3 提交与推送状态

最小修改已经形成三个本地 Rabbit commits：

1. `c286ca6` — DD4 物种与径向网格映射。
2. `903e063` — collision-ion 物种元数据。
3. `8d9ce5b` — GCC 13.2 ICE workaround。

工作树干净，分支相对 `origin/master` ahead 3；尚未 push。原完整补丁继续保留作为审计记录，
但不建议将它作为当前 MR 内容。

## 3. 目标运行架构

HCD-WF 主进程通过以下 Intel 2023b 环境启动：

```text
IMAS-Fortran/5.5.0-intel-2023b-DD-4.1.0
MUSCLE3/0.8.0-intel-2023b
XMLlib/3.2.0-intel-compilers-2023.2.1
INTERPOS/9.2.0-iimkl-2023b
```

Rabbit 由 yMMSL 单独启动 `tools/run_rabbit_m3_gcc_2023b.sh`；该脚本在 Rabbit 子进程中
执行 `module purge` 并加载：

```text
IMAS-Fortran/5.5.0-foss-2023b-DD-4.1.0
MUSCLE3/0.8.0-foss-2023b
XMLlib/3.3.2-GCC-13.2.0
INTERPOS/9.2.0-gfbf-2023b
```

因此 Intel 和 GCC runtime 不会被加载到同一个进程。两个进程通过相同的 DD 4.1.0
IDS 序列化格式和 MUSCLE3 0.8 wire protocol 交换数据。

## 4. 各项改动的详细评估

### 4.1 氢同位素和杂质的紧凑索引

**位置：** `imas/src/rabbit_ids.f90`

原代码先统计 `z_n == 1` 的离子数 `nsp_plasma`，之后却默认这些氢同位素位于
`ion(1:nsp_plasma)`。它还直接使用原始离子下标写入长度为 `nsp_plasma` 的
`sp_plasma_ratio`，并使用 `i - nsp_plasma` 作为杂质数组下标。

`ITER/4/105102/3@100 s` 的实际离子顺序是：

| 原始下标 | 离子 | A | Z |
|---:|---|---:|---:|
| 1 | D | 2 | 1 |
| 2 | T | 3 | 1 |
| 3 | He | 4 | 2 |
| 4 | Be | 9 | 4 |
| 5 | W | 183.84 | 74 |
| 6 | O | 16 | 8 |
| 7 | H | 1 | 1 |

这里有三个氢同位素，但它们不是连续放在前三项。原实现会产生以下错误：

- 将 `ion(3)=He` 当成第三个氢同位素，同时漏掉 `ion(7)=H`。
- 处理 `ion(3)=He` 时写入 `nimp(0)`。
- 处理 `ion(7)=H` 时写入只有三个元素的 `sp_plasma_ratio(7)`。

本地 standalone 运行在 Rabbit 进入计算后以 `corrupted size vs. prev_size` 终止，
与上述越界写入分析一致。

修复使用独立的紧凑计数器：

- `isp=1...nsp_plasma` 只写氢同位素数组。
- `iimp=1...nimp_count` 只写杂质数组。

**必要性结论：必须。** 对当前 105102 输入，不修复存在确定的越界访问，不能认为结果可靠。
这不是 Rabbit 物理模型修改，而是 IDS 物种列表到 Rabbit 内部紧凑数组的正确映射。

### 4.2 `rho_tor` 到 `rho_tor_norm` 的径向网格回退

**位置：** `imas/src/rabbit_ids.f90`

原代码使用：

```fortran
grid%rho_tor / grid%rho_tor(p)
```

但检查的 DD 4.1.0 输入中：

```text
rho_tor:      未关联/长度 0
rho_tor_norm: 长度 50，范围 0 到 1
volume:       长度 50
```

原代码在这个输入上会访问未关联数组。最小补丁直接使用 `rho_tor_norm` 进行体积插值；
这也与同一段代码已经用 `rho_tor_norm` 决定数组长度的行为一致。

**必要性结论：对当前 DD 4.1.0 输入必须。** 这并不表示所有 DD 4.1.0 数据都缺少
`rho_tor`；如果其他场景正确填充该字段，原表达式可能运行。但 Rabbit actor 不应假设
一个在 IDS 中可选或未必填充的字段总是存在。

原完整补丁中的“优先 `rho_tor`、否则回退”实现更通用，但会引入额外分支和 guards。
本次 MR 的目标是当前 DD4/HCDWF 契约下的最小修改，因此选择直接使用规范化坐标。

### 4.3 Rabbit 输出碰撞离子的物种元数据

**位置：** `imas/src/rabbit_ids.f90`

原代码创建：

```text
distributions.distribution(:).profiles_1d(1).collisions.ion(1)
```

并设置 `z_ion`，但没有分配和填充 `element(1).a`、`element(1).z_n`。

`HCD2CORE_SOURCES` 在处理离子碰撞功率时，对每个 `collisions.ion` 调用
`source_species_index`。当电荷相同而一侧 `element` 未关联时，当前
`same_species_v3` 的逻辑返回值可能保持未定义。未修复的 Pure M3 流程留下了直接证据：

```text
forrtl: severe (194): Run-Time Check Failure
SAME_SPECIES ... is being used ... without being defined
particle_sources.f90(349)
```

在 Rabbit 输出中补充来自 `nbi.unit(ibeam).species` 的 `a` 和 `z_n` 后，
相同 HCD-WF 拓扑中的 `rabbit`、`hcd2core_sources`、driver 及其他 actor 均以 0 退出，
manager 报告 `The simulation finished without error.`

**必要性结论：对完整 HCD-WF 必须；对 Rabbit standalone 非必须。** 如果只运行 Rabbit
并保存 `distributions`，缺失元数据不会阻止 Rabbit 自身结束；只要数据被
`HCD2CORE_SOURCES` 消费，这些字段就是当前接口契约的一部分。

从长期维护角度，`HCD2CORE_SOURCES.same_species_v3` 也应初始化返回值，以避免任何不完整
外部 IDS 触发未定义逻辑。但这属于下游鲁棒性修复，不能替代 Rabbit 正确描述其输出物种。

### 4.4 GCC 13.2 的 `mod_eq.F90` 编译器前端 ICE

**位置：** `src/mod_eq.F90`，函数 `fnbcd_redl`

未经修改的代码在 GCC 13.2 编译时稳定失败：

```text
[73%] Building Fortran object .../src/mod_eq.F90.o
f951: internal compiler error: Segmentation fault
gfc_expression_rank
```

该失败已在不同优化级别以及禁用 front-end optimization 的条件下复现，因此不是通过
将 `-O3` 改为 `-O0` 即可解决的问题。原始表达式可以由 Intel Fortran 2023.2.1 编译，
也有 GCC 14.3 编译成功的证据，故这是 **GCC 13.2 特定的编译器前端问题**，不是
DD 4.1.0 或 MUSCLE3 本身的问题。

原完整补丁将径向 rank-one 表达式改为逐径向点的标量循环。进一步的最小化发现：
去除局部 `associate(Te=>..., Zeff=>..., ne=>...)`，直接使用
`nbidepo%Te`、`nbidepo%Zeff` 和 `nbidepo%ne`，同时保留原向量表达式，也可以通过
GCC 13.2 编译。该更小实现现已完成三个目标的重编译、端到端 HCD-WF 运行和与标量版本的
IDS 数值回归。

**必要性结论：在固定 GCC 13.2 时必须有 workaround；去除 `associate` aliases 是当前
已经验证的最小实现。** 它不改变向量公式，只改变编译器解析表达式的方式。

### 4.5 MUSCLE3 `F_INIT`/`S` 端口接收顺序

**位置：** `imas/src/rabbit_m3.f90`

Rabbit 的 `wall` 端口声明为 `F_INIT`，而 `core_profiles`、`equilibrium`、`nbi`、
`workflow` 为动态 `S` 端口。原代码先接收多个 `S` 端口，再接收 `wall`。
补丁将 `wall` 接收移动到其他输入之前，与 driver 的发送顺序一致。

MUSCLE3 0.8 的实际行为是给出 MMSF sequence warning，而不是立即中止：

- 调整前，日志包含“先收到 `rabbit_core_profiles_in`，但期望 `rabbit_wall_in`”等多条警告。
- 调整后，与 wall 顺序相关的警告消失，Rabbit 可以完成运行。
- 调整后仍存在关于后续 `S` 端口和 `reuse_instance()` 的警告，说明单独移动 wall
  并没有让 Rabbit 的完整状态机完全符合 MMSF。

**必要性结论：建议保留，但不是单切片成功执行的硬前提。** 它修复了明确的 `F_INIT`
顺序问题并降低潜在死锁风险，但不能把它描述成已彻底解决所有 MMSF 顺序问题。
完整修复需要联合审查 Rabbit 的 port operators、接收循环、发送时机和
`reuse_instance()` 生命周期。

### 4.6 输入 guard/`stop` 检查

**位置：** `imas/src/rabbit_ids.f90`

补丁同时检查：

- 至少存在一个氢同位素和一个杂质。
- 杂质密度与氢同位素粒子数为正。
- 径向网格至少有两个点、严格递增且外边界有效。
- `volume` 已关联，并与径向网格长度一致。

**必要性结论：不是当前有效输入成功运行的最小要求，但属于合理的防御性编程。**
它们把内存损坏或数值异常转化为可诊断错误。正式 actor 中最好不要直接 `stop`；
更合适的实现是设置 `output_flag/output_message`，或由 M3 进程输出明确错误并受控退出。

### 4.7 Hybrid iWrap 的成功状态消息初始化

**位置：** 本地 Intel Hybrid 构建的 `imas/src/rabbit_ids.f90`；当前三文件补丁中不包含此项。

原 actor 只在 workflow 中找不到 Rabbit 时设置 `output_flag/output_message`，成功路径没有
初始化它们。生成的 iWrap wrapper 在 actor 返回后无条件执行
`convert_string2Cptr(status_msg)`；如果 Fortran character pointer 未关联，该转换会访问
无效对象。

本地 Intel Hybrid 构建增加了：

```fortran
output_flag = 0
allocate(character(len=256) :: output_message)
output_message = 'RABBIT completed successfully.'
```

**必要性结论：Hybrid iWrap 需要；Pure M3 不需要。** Pure M3 executable 不经过这条
iWrap 状态转换路径。若生产架构规定 Rabbit 只作为独立 GCC/M3 actor，应把此修复保留在
单独的 Hybrid 补丁中，不混入 Pure M3 最小补丁。

## 5. 必要性矩阵

| 改动 | Pure M3，GCC 13.2，当前 105102 输入 | Intel Hybrid iWrap | Rabbit standalone | 原因 |
|---|---|---|---|---|
| 氢同位素/杂质紧凑索引 | **必须** | **必须** | **必须** | 当前离子顺序非连续，会越界 |
| 使用 `rho_tor_norm` | **必须** | **必须** | **必须** | 当前输入未填充 `rho_tor` |
| 碰撞离子 `element.a/z_n` | **必须** | 下游连接 HCD2CORE 时必须 | 非必须 | HCD2CORE 需要物种匹配 |
| `mod_eq` GCC 13 workaround | **必须** | 非必须 | GCC 13 构建时必须 | GCC 13.2 前端 ICE |
| wall `F_INIT` 提前接收 | 建议 | 不适用 | M3 standalone 时建议 | 协议顺序和死锁风险 |
| 输入 guards | 建议 | 建议 | 建议 | 将未定义行为变成明确错误 |
| 成功状态消息初始化 | 不适用 | **必须** | iWrap standalone 时必须 | wrapper 无条件转换消息 |

这里的“必须”针对已定义的目标数据、编译器和下游拓扑。换用连续排列的离子输入、
已填充 `rho_tor` 的场景、Intel/GCC 14 编译器，或不连接 HCD2CORE 时，部分改动可能不会
被触发；这不能证明未经修改的 actor 对我们的生产目标可用。

## 6. 推荐的最小改动集合

### 6.1 当前 Pure M3 生产构建

已经实现并验证的最小功能集合是：

1. 在 `rabbit_ids.f90` 中用独立计数器压缩氢同位素、杂质和比例数组索引。
2. 在 `rabbit_ids.f90` 中直接使用 DD4 输入提供的 `rho_tor_norm`。
3. 在 `rabbit_ids.f90` 中为 `collisions.ion(1).element(1)` 填写 NBI 物种的 `a/z_n`。
4. 在 `mod_eq.F90` 中保留一个 GCC 13.2 workaround。

wall 接收顺序调整和额外 guards 已从最小分支排除；如需采用，应分别提交和评审。

### 6.2 GCC workaround 的最小化结果

已从最新 `master@e99ad70` 只移除 `fnbcd_redl` 的 `associate` aliases，并保留原向量公式。
GCC 13.2 的 clean build 和提交后增量重编译均通过；run 312 的端到端输出也通过 DD4 结构
验证和相对标量控制 run 311 的数值比较。

### 6.3 当前上游提交拆分

为了避免把数据兼容和编译器 workaround 混在一起，当前形成三个独立 commit：

1. `Fix DD4 plasma species and radial-grid mapping`
2. `Populate collision-ion species metadata`
3. `Avoid GCC 13.2 ICE in Redl current calculation`

MUSCLE3 wall 顺序和 Hybrid 状态消息分别留给后续独立提交。

## 7. 已有验证证据

| 证据 | 结果 | 支持的判断 |
|---|---|---|
| `rabbit_standalone_105102_t100_run246_20260711.log` | `corrupted size vs. prev_size` | 原始 IDS 映射存在内存破坏，与索引分析一致 |
| `build_gcc2023b_dd410_muscle08_20260711.log` | `mod_eq.F90` 触发 `f951` ICE | GCC 13.2 必须使用源码 workaround 或更换编译器 |
| `runs/run_hcd_pure_m3_rabbit_no_fopla_20260711_020201` | HCD2CORE exit 194，`SAME_SPECIES` 未定义 | Rabbit 碰撞离子元数据不足 |
| `runs/run_hcd_pure_m3_rabbit_no_fopla_20260711_021439` | 所有 actor exit 0，simulation without error | 修复后的 actor 可以完成目标 Pure M3 工作流 |
| `.local_dev/rabbit_audit/mod_eq_noassociate.F90` | 早期 GCC 13.2 compile-only 通过 | 确定了后来进入最小分支的 workaround |

最小分支新增验证证据：

| 证据 | 结果 | 支持的判断 |
|---|---|---|
| GCC 13.2 clean build | `rabbitA_imas`、`rabbit_imas.exe`、`rabbit_m3.exe` 全部成功 | 最小源码在目标编译栈可构建 |
| IMAS run 312 / 105102 @ 100 s | 所有 actor exit 0，simulation without error | 最小分支可完成目标 Pure M3 工作流 |
| `tools/validate_dd4_hcd_run.py --run 312` | PASS，四个输出 IDS 均有效 | 输出结构和必要 HCD 源完整 |
| run 311 vs 312，`rtol=3e-4` | PASS；EC/IC 完全相同，最大 NBI 相对差 `1.986444e-4` | no-associate 版本与标量控制数值一致 |
| 同一标量 executable：run 249 vs 311 | 最大相对差 `1.347936e-4` | Rabbit 本身存在未固定随机数造成的运行间波动 |

当前补丁头还记录了 `ITER/4/105102/248-249@100 s` 的 DD 4.1.0/MUSCLE3 0.8
Pure M3 验证。正式上游提交前，应把验证命令、输入 commit、输出 run 和数值容差固化为
可重复测试，而不能只依赖个人目录中的日志。

## 8. 风险和未解决事项

### 8.1 当前修复不等于已验证 Rabbit + FoPla + Cyrano 协同效应

上述修改解决的是 Rabbit 的构建、输入映射、M3 调用和下游结构兼容性。
它们没有实现 Cyrano 对 Rabbit/FoPla 快粒子分布的正确消费。

现有 NBI+ICRH synergy 运行中，虽然 workflow 已把 Rabbit 放在 Cyrano/FoPla 前面，
Cyrano 和 FoPla 仍报告 `NBI sources=0`。因此：

- Rabbit actor 能运行，不代表 NBI 快粒子已经影响 Cyrano。
- `include_nbi=2` 已设置，不代表当前 Cyrano 版本识别 Rabbit 的 distribution 布局。
- 仍需确认或实现 Rabbit `distributions` 到 Cyrano 预期 NBI source/provenance 的映射。

这是一个独立的算法/接口任务，不应通过扩大 Rabbit 兼容补丁来掩盖。

### 8.2 仍需做的回归

- 对 species indexing 增加至少三种测试：氢同位素连续、非连续、缺失。
- 对径向网格增加 `rho_tor`、仅 `rho_tor_norm`、网格不一致三种测试。
- 对 Rabbit 输出运行 IDS schema/physics sanity checks。
- 完成单切片与多切片 Pure M3 回归。
- 若继续支持 Hybrid Rabbit，单独验证 iWrap status message 和 Intel ABI 路径。
- 完整消除或正式解释 Rabbit 的剩余 MMSF sequence warnings。

## 9. 最终建议

1. **不要在目标 GCC 13.2/DD 4.1.0/HCD2CORE 配置中回退到 Schneim 未修改版本。**
   已有编译、内存和下游物种匹配三类独立失败证据。
2. **使用当前已验证的最小 no-associate 分支准备 MR。** 原完整补丁只作为审计和备份。
3. **保持现有三个独立 commits。** 每个 commit 对应单一问题，方便上游逐项评审。
4. **将 MUSCLE3 顺序修复标为协议改进，而不是宣称已完全 MMSF-compliant。**
5. **将 Hybrid iWrap 状态修复与 Pure M3 补丁分开。** 当前推荐架构让 Rabbit 在独立 GCC
   进程中运行，不需要同时向 HCD 主进程加载 GCC runtime。
6. **继续把 NBI+ICRH synergy 作为独立任务。** Rabbit 兼容修复完成并不代表
   Rabbit+FoPla 分布已被 Cyrano 消费。
