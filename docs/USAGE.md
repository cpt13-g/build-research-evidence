# Forge Research Evidence 完整使用说明

这份说明写给第一次下载本项目的用户。推荐在 Codex 中打开完整仓库，由 `experiment-orchestrator` 统一推进；其余三个 Skill 会在适当阶段参与执行、审计和投稿证据检查。命令行工具负责确定性校验、状态写入和实验记录。

## 1. 下载前先确认

### 适用任务

本项目适合计算机科学、人工智能和数据驱动工科论文的实验阶段，尤其适合：

- 已经有较明确的 Idea，需要规划并自动化完成论文实验；
- 实验周期长，需要跨会话恢复状态；
- 候选方法多，但希望控制算力和发散范围；
- 需要完整保留方法变化、失败结果和结论证据。

它不是一键生成论文的工具，也不会替研究者决定是否改变研究问题、增加预算或接受结论。它负责把这些决策变成可检查的流程，并把已经批准的工作持续推进下去。

### 运行条件

- Codex Desktop、CLI 或 IDE 扩展；宿主需要具备项目文件和终端访问能力。
- Python 3.10 或更新版本。
- 能运行你的研究代码并访问数据的 CPU/GPU 环境。
- 具体 PyTorch、TensorFlow、CUDA、数据集等依赖由研究任务自行提供。

项目自带的 `requirements.txt` 仅安装框架工具依赖，不会替你安装具体训练栈。

## 2. 下载完整项目

### 方式 A：Git 克隆

正式发布后，把下面的占位地址替换成仓库地址：

```bash
git clone <GitHub 仓库地址>
cd forge-research-evidence
```

### 方式 B：下载 ZIP

在 GitHub 仓库页面选择 **Code → Download ZIP**，解压后用 Codex 打开解压目录。不要只下载 `.agents/skills/` 中的某一个文件夹：四个 Skill 依赖同一套 `AGENTS.md`、状态机、Schema、模板和工具。

### 一项研究，一份副本

`research/research_state.yaml` 是一项研究的唯一决策状态源。两个无关课题不要共用同一份工作目录。开始新课题时重新克隆或复制一份干净项目；已有实验目录不要直接覆盖。

## 3. 安装并验证

在项目根目录执行：

```bash
python -m pip install -r requirements.txt
python tools/validate_project.py
python tools/state_manager.py show
```

预期结果：

- 项目校验通过；
- 状态显示 `BLOCKED_INPUT / S0_INTAKE_RECOVERY`；
- `revision` 初始为 `0`。

`BLOCKED_INPUT` 不是报错，只表示还没有接入你的 Research Idea。

### 确认 Skill 已加载

从仓库根目录新建 Codex 任务，运行 `/skills` 或输入 `$experiment-orchestrator`。应能看到：

- `experiment-orchestrator`
- `experiment-runner`
- `result-auditor`
- `venue-evidence-audit`

Codex 会扫描仓库中的 `.agents/skills/`，并在任务开始时读取根目录 `AGENTS.md`。如果列表没有更新，确认打开的是仓库根目录，然后重新启动任务。

## 4. 准备你的研究输入

最理想的输入是上一个 Idea Skill 产出的 `Research Idea Brief`。没有该文件也可以使用自然语言 Idea 或现有代码，但建议尽量提供：

| 信息 | 最少需要说明什么 |
|---|---|
| 研究问题 | 要解决什么问题，当前方法哪里不足 |
| 核心设想 | 计划通过什么机制改善，为什么可能有效 |
| 任务边界 | 输入、输出、约束，以及明确不做什么 |
| 实验对象 | 数据集、划分、指标、主要 Baseline |
| 现有资产 | 代码和数据路径、当前是否可运行 |
| 投稿目标 | 目标期刊/会议，或说明尚未决定 |
| 资源预算 | GPU、时间、完整运行次数、可接受调试轮数 |

信息缺失时，Orchestrator 会先提出真正影响科研决策的问题，不会直接消耗算力。

## 5. 第一次启动：复制这段提示词

```text
使用 $experiment-orchestrator 接续这个科研项目。
请先读取 research/research_state.yaml，并遵守 AGENTS.md、Research Spine.md
和共享协议。从输入恢复开始，梳理核心 Claim、Evidence Question、
Functional Requirement、Design Envelope 与骨干实验依赖，准备 Gate 1。
Gate 1 通过前不要运行任何实验。

Research Idea Brief：<粘贴内容或文件路径>
现有代码：<路径、运行方式和当前状态>
数据集：<路径、版本、划分和访问方式>
目标 Venue：<名称或待选择>
资源预算：<GPU、时间、完整实验次数、调试上限>
```

首次响应应该聚焦于输入缺口、研究主线、实验依赖和 Gate 1 准备。如果系统绕过 Gate 直接运行实验，请停止执行并要求它重新读取 `AGENTS.md` 与状态文件。

## 6. 四个 Skill 怎样协作

| Skill | 何时工作 | 交付什么 | 不能做什么 |
|---|---|---|---|
| `experiment-orchestrator` | 全程 | Claim、方法候选、批准的 Card、队列、预算和决策 | 不能替用户通过 Human Gate |
| `experiment-runner` | Card 获批且激活后 | 代码、配置、日志、指标、Artifact、Run Manifest | 不能改 Claim、预算和科研优先级 |
| `result-auditor` | 运行结束后 | 有效性、公平性、结果类型、Claim 影响和诊断 | 不能直接修改方法或调度实验 |
| `venue-evidence-audit` | P0 核心证据形成后 | 与目标 Venue 相关的证据缺口建议 | 不能把建议自动变成实验任务 |

正常循环是：

```text
Orchestrator 批准实验 → Runner 执行并保存事实
→ Auditor 独立审计 → Orchestrator 根据证据决定下一步
```

已批准、彼此独立且写入路径不冲突的任务可以并行；优先级、Gate 和共享状态仍由 Orchestrator 顺序更新。

## 7. 完整工作流

### 阶段一：把 Idea 变成研究骨架

系统提取研究问题、贡献、可检验 Claim、Evidence Question 和任务边界，再从贡献推导 Functional Requirement 与 Design Envelope。

你需要确认：核心 Claim 是否真的对应创新点；哪些实验决定论文能否成立；哪些只是辅助说明；允许方法改变到什么程度。

### 阶段二：有界探索并通过 Gate 1

系统在 Design Envelope 内提出 2–5 个非重复候选，先做概念筛选。Gate 1 由研究者确认：

- Research Spine、目标 Venue 和主要 Claim；
- 数据、划分、Baseline、Metric、公平规则和统计协议；
- 初始预算、停止条件和候选验证范围。

Gate 1 前不能运行任何实验，包括 Cheap Evaluation。

### 阶段三：先筛路线，再完成 P0 骨干

Gate 1 后，候选在统一代理协议下接受 Cheap Evaluation。它只能用于路线筛选，标记为 `PRELIMINARY_NON_PAPER`，不能进入正式证据。

主路线确定后，预算优先投入数据检查、Baseline 复现、公平比较和核心主表。每次科学实验必须使用已批准的 `E####` Experiment Card，预先声明改变什么、控制什么、什么结果支持或削弱 Claim、最低检查、成本和停止条件。

每轮结果都先交给 Auditor。系统先区分：

- `F1 Execution Failure`：代码、环境、数据或指标流程失败；
- `F2 Method Failure`：运行有效，但方法机制没有产生预期效果；
- `F3 Hypothesis Risk`：多个合理方案在公平条件下形成一致负面证据。

只有形成观察、诊断、科学理由、预期效果、拒绝条件和成本估计后，才允许修改方法。无关模块、额外数据集和“顺手再试”的想法进入 Backlog。

### 阶段四：Gate 2 后补齐证据矩阵

P0 达到关键节点后，Gate 2 审查当前方法、核心结果、失败证据、剩余风险和继续投入的价值。获批后，系统才根据 Claim–Evidence Matrix 安排消融、稳健性、泛化、边界和展示实验。

有依赖的任务按先后执行；独立且获批的任务可以并行。Venue Evidence Audit 会参考目标 Venue 补充审稿风险，但与 Claim 关系弱的惯例实验会降为 P3 或 SKIP。

### 阶段五：Gate 3、Evidence Freeze 与交付

系统分别检查方法是否收敛、Claim 是否受到支持、证据是否充分、投稿是否就绪。Gate 3 通过后执行 Evidence Freeze，停止常规扩展并生成：

- `reports/EXPERIMENT_REPORT.md`
- `reports/FIGURE_TABLE_PLAN.md`
- Claim–Evidence Matrix
- Venue Evidence Gap
- 方法演化记录与实验记忆

这些产物说明“为什么这样设计、结果支持什么、哪里存在边界、为什么做到这里”，可直接交接给绘图和论文写作智能体。

## 8. 一个完整但简化的例子

假设你的输入是：

```text
任务：长文本分类。
问题：普通池化会稀释分散在不同章节的关键信息。
Idea：保留章节层级，再进行层级感知聚合。
目标：在相同编码器与训练预算下提高 macro-F1，
      并验证提升是否真正来自层级机制。
```

系统会先建立：

```text
C1：层级感知聚合在公平设置下优于普通池化。
C2：章节层级信息是提升的主要来源。
P0-EQ1：固定编码器、数据和预算后，C1 是否成立？
Design Envelope：允许修改池化和层级交互；
                 不允许换任务、扩大预训练模型或增加外部数据。
```

候选阶段可以比较层级池化、跨章节注意力和章节图聚合。图聚合若成本高、对 C2 的解释不直接，可在概念筛选时暂缓。Gate 1 后，其余候选用同一数据子集、Epoch 和 Seed 做低成本比较。

即使跨章节注意力代理分数略高，系统也可能因为层级池化更贴合 C2、消融更清楚、成本更低而选择后者，并记录理由。进入 P0 后，只集中完成普通池化 Baseline、层级池化和公平主表。此时提出更大模型或更多数据集，会先进入 Backlog。

如果首轮没有提升，Auditor 先判断是 F1、F2 还是 F3；不会看到负结果就无限调参，也不会马上改写 Idea。主表稳定支持 C1 后，Gate 2 再安排 C2 消融、跨数据集泛化和失败案例可视化。证据足够后通过 Gate 3 并停止扩展。

这个例子体现了项目的核心节奏：**候选阶段允许比较，主实验阶段集中算力，辅助实验沿已经出现的证据缺口逐项生长。**

## 9. Human Gate 怎么回复

Gate 不是仪式，而是研究者保留科研判断的位置。可以直接复制以下格式。

### 批准 Gate 1

```text
批准 Gate 1。
确认当前 Research Spine、目标 Venue、实验合同 v1 与初始预算。
Cheap Evaluation 仅按已声明的统一协议执行。
批准人：<姓名或标识>
```

### 批准 Gate 2

```text
批准 Gate 2，进入支持实验阶段。
优先补齐与 C1、C2 直接相关的 P1 证据；
P2 任务需要再次比较证据价值与成本。
批准人：<姓名或标识>
```

### 批准 Gate 3

```text
批准 Gate 3，并按当前 readiness 执行 Evidence Freeze。
冻结理由：核心 Claim 与必要支持证据已经完成。
批准人：<姓名或标识>
```

如果不同意，只需指出需要修改的 Claim、Baseline、预算项或证据缺口，无需要求系统推倒整个项目。

## 10. 最小 Experiment Card 示例

实际文件应从 `templates/experiment_card.yaml` 创建。下面只展示理解流程所需的核心字段：

```yaml
experiment:
  experiment_id: E0001
  status: draft
  claim_id: C1
  evidence_question_id: P0-EQ1
  priority: P0
  experiment_role: CORE_P0
  purpose: 公平检验层级池化是否优于普通池化
  changed_variables: [pooling_method]
  controlled_variables: [dataset, split, encoder, training_budget]
  datasets: [long_text_dataset_v1]
  baselines: [flat_pooling]
  metrics: [macro_f1]
  seed_protocol:
    seeds: [7, 17, 27]
  expected_supporting_result: 多 Seed 下稳定提升且公平检查通过
  falsifying_result: 排除主要混杂后仍无稳定提升或稳定下降
  estimated_budget:
    gpu_hours: 6
  completion_contract:
    minimum_required_checks: [dataset_integrity, baseline_fairness, three_seeds]
    acceptance_condition: 达到预声明的支持模式且必要检查通过
    rejection_condition: 达到预声明的削弱模式且主要混杂已排除
    stop_when_decided: true
    extension_requires_evidence_gap: true
```

Seed、阈值和预算只是示例，应依据你的任务和统计协议设置。

## 11. 常见使用情境

| 情境 | 系统应怎么做 | 你需要决定什么 |
|---|---|---|
| Idea 清楚但没有代码 | 先完成 Claim、Envelope 和实验设计，再构建最小实现 | 数据访问、环境和预算 |
| 已有代码但聊天与状态冲突 | 以 `research_state.yaml` 为准，核对代码和 Artifact | 哪些现有改动需要保留 |
| 代理分最高的方案很复杂 | 同时比较 Claim 对齐、稳定性、解释性、成本和风险 | 是否接受总控的路线选择理由 |
| 单次主实验没有提升 | 先排查有效性和混杂，再判断 F1/F2 | 是否批准定向修复或改动 |
| 出现有趣的新模块 | 与当前 Claim 无关时放入 Backlog | Gate 2 后是否值得预算 |
| P0 成立但机制解释不足 | 优先补充对应消融或机制实验 | 证据价值是否高于成本 |
| Venue 常见实验与 Claim 很弱 | 标记 P3 或 SKIP | 是否仍有明确投稿风险需要覆盖 |
| 预算即将耗尽 | 给出停止影响和扩展建议 | 增加预算或接受当前证据边界 |
| 结果已经足够，AI 仍建议测试 | Completion Contract 阻止无理由扩展 | 是否存在新的明确证据问题 |

## 12. 中断后恢复

重新打开项目后发送：

```text
使用 $experiment-orchestrator 恢复项目。
以 research/research_state.yaml 为唯一决策状态源，检查 revision、当前阶段、
Active Queue、Backlog、预算、Human Gate 和 next_action，并核对引用工件。
先汇报 Current Stage、Current Finding、Decision 与 Next Action，再继续。
```

不要依靠聊天记录重建科研状态。原始日志、指标和 Artifact 保存在实验目录；状态文件保存当前决策和引用。

## 13. 命令行参考

正常使用时由智能体调用；你也可以用它们人工核验。

```bash
python tools/state_manager.py show
python tools/experiment_registry.py list
python tools/budget_tracker.py show
```

状态写入采用 `revision` 乐观锁。遇到 `stale revision` 时重新读取状态，使用最新 `--expected-revision`，不要覆盖新状态。

实验卡典型生命周期：

```bash
python tools/experiment_registry.py register experiments/E0001/experiment_card.yaml --expected-revision 12
python tools/experiment_registry.py approve E0001 --actor researcher --expected-revision 13
python tools/experiment_registry.py activate E0001 --expected-revision 14
python tools/experiment_registry.py status E0001 running --reason "run started" --expected-revision 15
```

运行实验时，Runner 选项放在实验 ID 前，真实执行命令放在 ID 和 `--` 后：

```bash
python tools/runner.py --timeout-seconds 7200 --metric-file experiments/E0001/raw_metrics.json --artifact experiments/E0001/checkpoint.pt E0001 -- python src/train.py --config configs/E0001.yaml
```

正式 Claim Evidence 必须显式提供原始指标文件。运行完成并经 Auditor 生成符合 Schema 的记录后：

```bash
python tools/experiment_registry.py status E0001 completed --reason "run completed" --expected-revision 16
python tools/result_recorder.py experiments/E0001/incoming_result.yaml
python tools/experiment_registry.py status E0001 audited --reason "audit persisted" --expected-revision 17
```

聚合证据并生成交付物：

```bash
python tools/evidence_builder.py claims
python tools/evidence_builder.py queue
python tools/readiness.py assess
python tools/report_builder.py figure-plan
python tools/report_builder.py final-report
```

具体参数以 `python tools/<工具名>.py --help` 为准。

## 14. 常见阻塞与解决办法

| 提示或状态 | 含义 | 处理方法 |
|---|---|---|
| 四个 Skill 未显示 | 没有从正确目录启动或任务未刷新 | 打开仓库根目录，新建任务后用 `/skills` 检查 |
| `BLOCKED_INPUT` | 缺少研究骨架所需输入 | 提供 Idea、边界、数据、指标和预算 |
| `Gate 1 ... required` | 尚未批准合同与预算 | 让 Orchestrator 提交 Gate 1 摘要，由研究者决定 |
| `stale revision` | 其他操作已更新状态 | 重读状态并使用最新 revision |
| `Incomplete dependencies` | 前置实验未完成 | 先完成依赖，不要手工跳过 |
| `BUDGET_EXTENSION_REQUIRED` | 已批准预算不足 | 审查扩展价值，明确批准或停止 |
| `HYPOTHESIS_AT_RISK` | 合理方案形成一致负面证据 | 重新审查核心假设，不要自动改故事 |
| `Run Manifest ... mismatch` | Card、环境、指标或 Artifact 已改变 | 恢复原文件或重新运行，不能改哈希绕过 |
| `EVIDENCE_FROZEN` | Gate 3 后停止常规实验 | 只有研究者说明理由并批准后才能解冻 |

## 15. 必须知道的边界

- Skill 提供角色和协议；真正的上下文隔离取决于宿主环境。`blind-first` 字段本身不能证明审计者没有提前看到总控解释。
- Run Manifest 会核验登记文件的哈希；数据集字段当前主要保存声明，不能代替完整数据版本管理。
- `COMPLETE` 表示要求的声明与材料齐备，不表示外部团队已独立复现。
- Schema 与测试保证流程约束，不保证研究假设正确、实验必然提升或论文录用。
- 项目不会自动增加预算、修改 Research Spine、通过 Human Gate 或解冻证据。

完成安装后，回到[项目首页](../README.md)，复制“5 分钟开始”中的启动提示即可进入第一个真实课题。
