# 论文实验科研智能体项目设计规范

## 0. 项目定位

设计一个独立的科研辅助项目，面向计算机科学、人工智能、数据驱动工科及相关工程方法类论文，专门负责：

> 将已经形成基本 Research Idea、论文故事主线、创新方向和评价目标的研究设想，进一步转化为具体可实现的方法，通过受约束的技术方案设计、代码实现、实验执行、结果诊断、方法修正和证据补全，最终形成能够完整支撑论文核心 Claim 的实验体系。

本项目重点解决的是：

**“Idea 已经基本确定，但具体方法尚未完全确定，接下来怎样把它真正做出来，并通过严谨实验形成一篇完整论文的证据链？”**

本项目不是开放式 Idea 生成系统，也不是单纯的代码执行器。

其核心能力应位于两者之间：

```text
已有科研 Idea
    ↓
理解论文故事
    ↓
将抽象创新转化为技术需求
    ↓
设计具体模型 / 算法 / 模块 / 约束
    ↓
受约束地尝试多个实现方案
    ↓
实验验证
    ↓
分析结果
    ↓
针对性修改方法
    ↓
逐步收敛
    ↓
完成核心实验
    ↓
补充必要证据
    ↓
形成实验总结和论文展示规划
```

核心原则：

> Research Spine 稳定，Method Realization 开放，Evidence 驱动迭代。

---

# 1. 与上游 Research Idea 项目的关系

本项目是一个完全独立的新项目。

可以兼容上游 `clarify-research-idea` 输出的 `Research Idea Brief`，但：

- 不属于该项目内部；
- 不修改原项目；
- 不要求用户必须使用原项目；
- 可以独立接受普通 Research Idea、已有 Method Description、代码仓库或研究计划作为输入。

存在标准 Research Idea Brief 时，应优先解析其中已经确认的信息，避免重新讨论 Idea。

没有 Research Idea Brief 时，项目仅执行轻量级 Experiment Intake，不重新进行完整 Idea 构思。

---

# 2. 项目边界

本项目负责：

```text
Idea实验可执行性检查
↓
目标期刊/会议确认
↓
论文故事与Claim恢复
↓
具体方法设计
↓
候选技术方案筛选
↓
代码和实验环境构建
↓
Baseline复现
↓
主实验
↓
方法迭代
↓
结果分析
↓
消融和机制验证
↓
数据分析
↓
稳定性/鲁棒性/效率等必要实验
↓
目标Venue实验完整度审查
↓
实验补全
↓
Figure/Table规划
↓
实验总结
↓
Submission Readiness评级
```

本项目默认不负责：

```text
重新构思完全不同的论文问题
大范围Idea brainstorming
完整Related Work写作
Introduction正式写作
完整论文正文生成
语言润色
投稿流程
```

如果实验发现核心科学假设可能失效，应明确报告并建议返回 Idea 阶段，而不是自行改变论文研究主题。

---

# 3. 项目核心理念：Research Spine

不要把项目设计成死板的 Story Lock。

建立 `Research Spine`。

Research Spine 表示论文不能随实验结果任意改变的科学主线。

主要包含：

```yaml
research_spine:
  research_question:
  problem_context:
  core_hypothesis:
  contributions:
  primary_claims:
  secondary_claims:
  evaluation_goals:
  task_boundary:
  exclusions:
  target_venue:
```

Research Spine 原则上保持稳定。

但是具体技术实现不冻结。

---

# 4. 三层自由度模型

项目必须明确区分三个层级。

| 层级 | 内容 | 权限 |
|---|---|---|
| L1 Scientific Spine | 问题、Hypothesis、Contribution方向、Claim、评价目标 | 稳定 |
| L2 Method Realization | 网络结构、模块、编码机制、约束、Loss、Fusion、优化方法 | 允许主动设计和迭代 |
| L3 Engineering | 参数、代码、训练配置、数据处理、优化器、工程实现 | 高度自由 |

例如：

```text
Contribution:
改进多模态信息的层级表示
```

这是 Research Spine。

但智能体可以探索：

```text
Hierarchical cross-attention
Shared latent tokens
Dynamic modality routing
Multi-scale fusion
Modality-specific adapter
Gated interaction
```

最终选择哪一种由实验决定。

但不能因为某个无关方案指标更高，就把论文重新变成另外一个研究故事。

---

# 5. 核心技术思想：受约束的 Method Design Search

项目必须具备真正的科研设计能力。

不能要求输入 Idea 已经包含完整模块设计。

针对每项 Contribution，智能体需要完成：

```text
Contribution
↓
问题成因分析
↓
Functional Requirement
↓
Technical Hypothesis
↓
Candidate Mechanisms
↓
Conceptual Screening
↓
Cheap Experiment
↓
Candidate Selection
↓
Full Experiment
↓
Diagnosis
↓
Refinement
```

例如：

```text
Idea:
设计分层表征多模态生成模型

Contribution 1:
改进多模态信息编码表示

Contribution 2:
增加物理层表示和约束
```

智能体需要主动分析：

```text
C1解决的具体问题是什么？
→ 模态异质性？
→ 跨模态交互不足？
→ 多尺度信息不能充分融合？
→ 共享表示出现信息污染？

C2解决什么？
→ 输出违反物理规则？
→ Latent representation缺少结构？
→ Decoder生成空间过度自由？
```

然后建立 Functional Requirement，并产生技术候选方案。

---

# 6. Design Search Envelope

为了避免开放式搜索失控，每项 Contribution 必须建立一个设计搜索边界。

示例：

```yaml
design_envelope:

  contribution_id: C1

  scientific_goal:
    hierarchical multimodal representation

  problem_to_solve:
    insufficient cross-modal interaction across representation levels

  allowed_design_dimensions:
    - encoder architecture
    - latent representation
    - fusion strategy
    - cross-modal interaction
    - attention mechanism
    - routing mechanism
    - representation hierarchy

  forbidden_drift:
    - change research task
    - remove multimodal setting
    - abandon hierarchical representation motivation
    - redefine primary evaluation objective

  evaluation_targets:
    - task performance
    - cross-modal consistency
    - parameter efficiency
```

搜索必须发生在 Design Envelope 内。

---

# 7. 方法搜索采用“宽 → 窄 → 深”

禁止无限扩展搜索树。

采用：

```text
Stage A — Candidate Generation
生成2~5个非重复的合理机制；机制类别开始重复时提前停止

Stage B — Conceptual Screening
从科学一致性、实现难度、可验证性、
创新合理性、计算成本筛选

Gate 1 — Protocol Approval
确认Research Spine、Claim、实验协议、
设计筛选预算与停止条件

Stage C — Cheap Evaluation
小数据 / 少Epoch / 小模型 / Proxy metric

Stage D — Candidate Selection
保留1~2个候选

Stage E — Full Evaluation
正式训练和比较

Stage F — Targeted Refinement
只围绕优胜方案进一步优化
```

不得每轮重新产生大量全新架构。

搜索空间需要逐渐收缩。

---

# 8. 实验决策不能只追求指标

Method Candidate 不以单一 Metric 最大化作为唯一标准。

内部至少判断：

```text
Task Performance
Claim Alignment
Scientific Interpretability
Evidence Strength
Complexity
Compute Cost
Stability
```

避免出现：

```text
某个大型模型性能最高
↓
但与原Contribution没有关系
↓
仍然被选为论文方法
```

这种情况应被拒绝。

优先选择：

> 能达到较好性能，同时能够解释论文 Contribution 并产生清晰验证证据的方案。

---

# 9. 项目架构

第一版本采用：

```text
               Experiment Orchestrator
                       │
       ┌───────────────┼────────────────┐
       ↓               ↓                ↓
Method/Experiment   Result          Venue Evidence
    Runner          Auditor             Audit
```

建议最终实现四个核心 Skill。

## 9.1 experiment-orchestrator

负责整个项目科研决策。

职责：

```text
读取Idea
恢复Research Spine
检查实验准备度
管理Venue
建立Claim
建立Design Envelope
规划方法设计搜索
生成Experiment Contract
维护Experiment Registry
控制P0/P1/P2/P3优先级
管理Budget
控制阶段状态
处理Human Gate
决定是否继续/停止/回退
生成最终Experiment Report
生成Figure/Table Plan
生成Submission Readiness
```

Orchestrator 是唯一具有科研调度权的组件。

---

## 9.2 experiment-runner

严格执行已经批准的：

```text
Design Card
Experiment Card
Tuning Card
```

负责：

```text
读取已有代码
设计或修改具体实现
创建Config
运行实验
Debug
保存日志
保存Checkpoint
收集Metrics
记录Runtime
记录Environment
生成Artifacts
生成Run Manifest
```

Runner 不允许自行修改 Research Spine。

Run Manifest 至少记录Card/代码/配置身份、数据与Seed声明、环境、日志、Metric与Artifact哈希；缺失项必须显式标记，不能把不完整记录描述为可复现。

---

## 9.3 result-auditor

负责科学解释。

不是只提取最佳 Metric。

首轮审计必须先读取Card、合同和原始运行证据，在不知道Orchestrator期望结论的情况下固定Validity、Fairness和Result Type，再进行解释对照。

必须回答：

```text
实验是否有效？
结果是否可信？
是否存在Bug？
是否收敛？
Baseline是否公平？
结果支持哪个Claim？
削弱哪个Claim？
是否出现Confound？
是否需要诊断实验？
Performance Value如何？
Scientific Value如何？
下一步最高价值动作是什么？
```

---

## 9.4 venue-evidence-audit

仅在 P0 主实验基本完成后启动。

负责分析目标 Venue 近期高度相关论文的实验惯例。

重点分析：

```text
常用Datasets
强Baseline
Metric
随机种子
显著性
Ablation
Sensitivity
Robustness
Generalization
Efficiency
Complexity
Case Study
Failure Analysis
Figure/Table形式
```

最终输出：

```text
Venue Evidence Gap Matrix
```

但不自行执行实验。

是否补实验由 Orchestrator 决定。

---

# 10. 项目状态机

采用如下状态：

```text
S0  Intake & Project Recovery
↓
S1  Research–Venue Contract
↓
S2  Research Spine & Claim Formalization
↓
S3  Method Realization
↓
S4  Experimental Protocol
↓
S5  Infrastructure & Baseline
↓
S6  P0 Main Experiments
↓
S7  Claim Audit & Method Refinement
↓
S8  Supporting Experiments
↓
S9  Venue Evidence Audit
↓
S10 Evidence Freeze & Final Report
```

---

# 11. S0 — Intake & Project Recovery

接受：

```text
Research Idea Brief
自然语言Idea
论文方案
现有代码仓库
实验代码
方法设计草稿
```

首先判断是否存在已有项目状态。

如果：

```text
research_state.yaml
```

存在，则恢复状态，而不是重新规划。

如果是新项目，提取：

```text
Research Question
Hypothesis
Contribution
Claim
Dataset情况
Metric
Method已有程度
资源
Venue
```

---

# 12. S1 — Research–Venue Contract

目标 Venue 必须明确。

如果用户没有明确 Venue：

智能体根据：

```text
研究方向
研究任务
论文类型
数据规模
创新特点
预计实验规模
用户期望
```

生成 2~4 个候选 Venue。

说明：

```text
适配程度
典型论文特点
实验要求
潜在风险
```

必须由用户选择。

此阶段为：

## Human Gate 1

确认：

```text
Research Spine
Target Venue
主要Claims
初始Budget
实验目标
```

---

# 13. S2 — Claim Formalization

为每项 Contribution 建立：

```text
Contribution
↓
Claim
↓
Evidence Question
```

注意：

主实验预注册的是：

**Evidence Questions**

而不是最终 Method。

例如：

```text
P0-EQ1
分层多模态表示是否提高跨模态信息建模能力？

P0-EQ2
物理表示约束是否降低物理无效生成？

P0-EQ3
完整方法是否优于主要Baseline？
```

这些问题保持稳定。

具体技术实现允许后续搜索。

---

# 14. S3 — Method Realization

这是整个项目最重要的智能能力之一。

针对每个 Contribution：

```text
问题成因
↓
Functional Requirement
↓
Design Envelope
↓
Candidate Mechanism
↓
Screening
↓
Cheap Experiment
↓
Winner
↓
Refinement
```

每次技术修改必须产生：

```text
Design Iteration Record
```

推荐格式：

```yaml
design_iteration:

  id: D007

  contribution: C1

  current_mechanism:

  observed_problem:

  diagnosis:

  proposed_change:

  scientific_reason:

  expected_effect:

  evaluation_metric:

  rejection_condition:

  estimated_cost:
```

禁止没有明确诊断就随意增加模块。

---

# 15. S4 — Experimental Protocol

方法方案具备基本可行性后，创建：

```text
EXPERIMENT_CONTRACT.yaml
```

包括：

```yaml
experiment_contract:

  research_spine:

  claims:

  evidence_questions:

  datasets:

  data_split:

  baselines:

  primary_metrics:

  secondary_metrics:

  seed_protocol:

  statistical_protocol:

  fairness_rules:

  compute_environment:

  execution_policy:

  initial_budget:

  experiment_priorities:

  stop_conditions:
```

---

# 16. 实验优先级

固定使用：

```text
P0 — Core Evidence

P1 — Mechanism / Necessary Support

P2 — Venue / Presentation Completeness

P3 — Optional Exploration
```

核心规则：

```text
P0未完成
→ 禁止执行P1/P2/P3
```

但是：

```text
必要Debug
必要诊断
Method Refinement
```

允许服务于 P0。

所有暂时有价值但非核心的想法进入：

```text
Experiment Backlog
```

不能立即执行。

---

# 17. Experiment Card

任何正式实验运行前必须创建 Card。

没有 Experiment Card：

```text
NO EXECUTION
```

Schema：

```yaml
experiment:

  experiment_id:

  evidence_question:

  claim_id:

  contribution_id:

  priority:

  purpose:

  hypothesis:

  changed_variables:

  controlled_variables:

  datasets:

  baselines:

  method_variant:

  metrics:

  seed_protocol:

  expected_supporting_result:

  falsifying_result:

  possible_confounders:

  dependencies:

  estimated_budget:

  stop_condition:

  completion_contract:
    minimum_required_checks:
    acceptance_condition:
    rejection_condition:
    stop_when_decided: true
    extension_requires_evidence_gap: true
```

实验问题一旦被接受条件或拒绝条件回答，就停止该Card。继续运行必须对应明确的未解决证据缺口、预期信息增益和成本，不能只以“做得更完整”为理由。

---

# 18. Tuning 与 Scientific Experiment 分离

必须明确区分：

```text
Txxxx = Tuning / Engineering

Exxxx = Scientific Experiment
```

例如：

```text
T003
学习率选择

T007
Batch Size稳定性

E011
移除物理约束验证C2
```

Tuning 的结果不能直接作为科学 Claim 证据。

---

# 19. S5 — Infrastructure & Baseline

正式主实验前必须确认：

```text
数据正确
Split正确
不存在明显泄漏
Metric实现正确
Baseline能运行
Environment可复现
随机种子有效
训练正常收敛
Result Parser正常
Artifact保存正常
```

所有项目都执行检查。

不适用项必须写：

```text
N/A + reason
```

不能静默跳过。

---

# 20. S6 — P0 Main Experiments

主实验是项目最高优先级。

默认检查：

```text
Dataset integrity
Baseline reproduction
Proposed method
Fair comparison
Primary metrics
Secondary metrics
Multi-seed
Statistical summary
Main result table
Claim interpretation
```

无法使用 Multi-seed 的确定性任务：

```text
Multi-seed: N/A
Reason: ...
```

---

# 21. S7 — Claim Audit & Method Refinement

实验结果不理想时禁止立即修改 Research Spine。

采用三级失败体系，与 L1/L2/L3 权限层分开命名。

## F1 — Execution Failure

例如：

```text
Bug
OOM
Data error
Evaluation error
Training failure
```

处理：

```text
DEBUG
```

---

## F2 — Method Failure

例如：

```text
当前融合机制效果差
当前Loss无效
训练不稳定
模块无法实现预期作用
```

允许：

```text
在Design Envelope内重新设计
```

形成新的 Design Iteration。

---

## F3 — Hypothesis Risk

经过合理 Method Search 后：

```text
不同合理机制均无法获得预期证据
```

或者出现直接反证。

状态进入：

```text
HYPOTHESIS_AT_RISK
```

此时与用户确认。

不能自动改论文故事。

---

# 22. 方法优化必须是 Targeted Refinement

禁止：

```text
结果差
→ 加模块
→ 再加Loss
→ 再换模型
→ 再增加Dataset
```

要求：

```text
Observation
↓
Diagnosis
↓
Specific Cause
↓
Targeted Change
↓
Expected Effect
↓
Experiment
```

没有 Diagnosis 不允许修改。

---

# 23. Result Auditor

每个结果必须分类。

建议：

```yaml
result_type:

  - SUPPORTING
  - FALSIFYING
  - BOUNDARY
  - NULL
  - CONFOUNDING
  - IMPLEMENTATION_FAILURE
  - INCONCLUSIVE
```

并分别评价：

```yaml
result_value:

  performance_value:

  scientific_value:

  claim_impact:

  confidence:

  next_action:
```

重点：

> 指标没有提高不代表实验没有科研价值。

---

# 24. Experiment Memory

必须保存所有有意义的尝试。

包括：

```text
成功实验
失败实验
Null Result
异常结果
Bug
放弃方法
候选机制
参数探索
诊断实验
边界实验
```

禁止只保存 Best Run。

Experiment Memory 主要用于：

```text
避免重复尝试
理解为什么停止某条路线
保留负结果
后续论文讨论
Reviewer response
方法分析
研究复盘
```

---

# 25. Budget Management

Budget 必须存在，但是可动态协商。

包括：

```yaml
budget:

  gpu_hours:

  wall_time:

  max_full_runs:

  max_debug_rounds:

  max_tuning_rounds:

  max_design_iterations:

  max_failed_runs:
```

执行中记录：

```text
Used
Remaining
Expected next cost
Expected information gain
```

当预算不足时：

智能体不能自行扩大。

必须向用户报告：

```text
当前Evidence
剩余不确定性
为什么建议增加Budget
建议增加多少
预计获得什么信息
如果不增加预算有什么影响
```

由用户确认。

项目结束时生成：

```text
Budget Review
```

分析：

```text
哪些实验价值最高
哪些尝试没有价值
哪些失败实验有科学价值
如果增加资源，最高ROI实验是什么
```

---

# 26. Human Gates

只设置三个主要 Gate。

## Gate 1

```text
Research Spine
Venue
Claim
Budget
Experiment Contract
```

---

## Gate 2

P0 完成或达到关键节点后：

```text
Primary Claim Status
Current Method
Evidence Quality
是否继续Method Refinement
是否进入Supporting Experiments
```

---

## Gate 3

最终：

```text
Evidence completeness
Venue gaps
Remaining experiments
是否Evidence Freeze
```

正常实验不要求用户逐次确认。

---

# 27. 并行策略

允许：

```text
执行层并行
```

例如：

```text
Seed 42
Seed 123
Seed 456
```

或者相互独立的已批准 P0 实验。

禁止：

```text
多个Agent同时自由设计不同论文故事
```

研究决策保持单一 Orchestrator。

---

# 28. S8 — Supporting Experiments

P0 基本完成后才启动。

候选：

```text
Ablation
Mechanism Validation
Parameter Sensitivity
Dataset Analysis
Efficiency
Complexity
Robustness
Generalization
Statistical Significance
Qualitative Analysis
Failure Case
Case Study
```

不是全部执行。

排序考虑：

```text
Claim relevance
Reviewer risk
Venue convention
Information gain
Cost
Presentation value
```

---

# 29. S9 — Venue Evidence Audit

分析目标 Venue 最近几年高度相关的 5~10 篇论文。

优先：

```text
同任务
>
同研究问题
>
同方法类别
>
同Venue
>
近期
```

生成：

```text
Venue Evidence Gap Matrix
```

Schema：

```yaml
evidence_gap:

  evidence_type:

  current_status:

  venue_frequency:

  claim_relevance:

  reviewer_risk:

  estimated_cost:

  information_gain:

  recommended_priority:
```

Venue Audit 只提出建议。

不得自动改变论文核心研究问题。

---

# 30. Evidence Freeze

当：

```text
核心Claim已有充分证据
关键Baseline完成
评价有效
结果可复现
必要P1完成
高价值Venue Gap完成
预算边际收益明显下降
```

进入：

```text
EVIDENCE_FREEZE
```

之后默认停止继续实验。

只有明确新理由才能重新开启。

---

# 31. 最终实验总结

生成：

```text
EXPERIMENT_REPORT.md
```

建议结构：

```text
1. Research Spine
2. Experimental Objectives
3. Final Method Realization
4. Design Evolution
5. Dataset and Protocol
6. Baselines
7. Main Experiments
8. Claim–Evidence Matrix
9. Ablation / Mechanism Analysis
10. Supporting Experiments
11. Negative / Null Results
12. Failure and Boundary Analysis
13. Reproducibility
14. Venue Evidence Audit
15. Remaining Weaknesses
16. Figure/Table Plan
17. Budget Review
18. Remaining High-ROI Experiments
19. Submission Readiness
```

---

# 32. Claim–Evidence Matrix

最终必须存在。

```text
Claim
↓
Required Evidence
↓
Experiment
↓
Result
↓
Verdict
```

示例：

| Claim | Evidence | Experiment | Result | Verdict |
|---|---|---|---|---|
| C1 | 多模态表示改善 | E004 | ... | SUPPORTED |
| C2 | 物理约束有效 | E009 | ... | PARTIAL |
| C3 | 完整模型优势 | E013 | ... | SUPPORTED |

---

# 33. Figure / Table Planner

不要问：

```text
还能画什么图？
```

必须问：

```text
哪个Claim需要怎样的展示？
```

形成：

```text
Figure–Claim Matrix
```

例如：

```text
Table 1
→ 主性能
→ C1/C2/C3

Table 2
→ Ablation
→ C1/C2

Figure 3
→ Representation analysis
→ C1

Figure 4
→ Physical validity
→ C2

Figure 5
→ Failure cases
→ Boundary
```

每个 Figure 建议：

```text
Purpose
Supported Claim
Data source
Chart type
X/Y axis
Comparison groups
Expected message
Potential misleading presentation
Caption suggestions
```

第一版本主要生成规划。

自动高质量绘图可以后续独立扩展。

---

# 34. Submission Readiness

先进行 Hard Gate：

```text
Primary Claim supported?
Evaluation valid?
Baseline fair?
Results reproducible?
```

任一关键项失败：

```text
NOT READY
```

通过后评级：

```text
A — Submission-grade evidence

B — Core story complete,
    targeted improvements recommended

C — Important experimental evidence missing

D — Core hypothesis unsupported
```

评级必须结合目标 Venue。

不输出所谓“录用概率”。

---

# 35. research_state.yaml

项目必须使用：

```text
research_state.yaml
```

作为唯一事实源。

所有 Skill 都必须读取它。

禁止依赖长聊天上下文记忆项目状态。

推荐：

```yaml
project:

  status:

  current_stage:

  research_spine:

  venue:

  claims:

  design_envelopes:

  current_method:

  design_iterations:

  experiment_contract:

  experiment_registry:

  active_queue:

  backlog:

  completed_experiments:

  failed_experiments:

  claim_status:

  budget:

  unresolved_risks:

  next_action:

  human_gate:
```

所有状态更新必须落盘。

---

# 36. 推荐仓库结构

```text
research-experiment-agent/
│
├── README.md
├── LICENSE
├── AGENTS.md
│
├── .agents/
│   └── skills/
│       ├── experiment-orchestrator/
│       │   ├── SKILL.md
│       │   ├── references/
│       │   └── scripts/
│       │
│       ├── experiment-runner/
│       │   ├── SKILL.md
│       │   ├── references/
│       │   └── scripts/
│       │
│       ├── result-auditor/
│       │   ├── SKILL.md
│       │   └── references/
│       │
│       └── venue-evidence-audit/
│           ├── SKILL.md
│           └── references/
│
├── templates/
│   ├── research_state.yaml
│   ├── experiment_contract.yaml
│   ├── experiment_card.yaml
│   ├── tuning_card.yaml
│   ├── design_iteration.yaml
│   └── result_record.yaml
│
├── tools/
│   ├── state_manager.py
│   ├── experiment_registry.py
│   ├── metric_parser.py
│   ├── environment_capture.py
│   ├── budget_tracker.py
│   └── report_builder.py
│
├── research/
│   ├── research_idea_brief.md
│   ├── research_state.yaml
│   └── experiment_contract.yaml
│
├── src/
│
├── configs/
│
├── experiments/
│   ├── E001/
│   ├── E002/
│   └── ...
│
├── evidence/
│   ├── claim_evidence.yaml
│   └── experiment_memory.jsonl
│
├── figures/
│
└── reports/
    └── EXPERIMENT_REPORT.md
```

---

# 37. 实验代码组织原则

优先：

```text
共享代码
+
独立Config
```

例如：

```text
src/
  models.py
  trainer.py
  evaluator.py

configs/
  E001.yaml
  E002.yaml
  E003.yaml
```

避免：

```text
E001复制一份完整代码
E002再复制一份
E003再复制一份
```

这样才能保证公平比较。

---

# 38. 可选Git集成

Git 不是项目运行依赖。

配置：

```yaml
version_control:
  enabled: false
```

用户启用时：

可以在：

```text
Experiment Contract确认
P0完成
Evidence Freeze
```

建立 checkpoint commit/tag。

未安装Git或用户关闭：

项目必须正常运行。

---

# 39. Execution Safety

自动运行代码，但禁止：

```text
删除原始数据
覆盖重要Checkpoint
危险系统命令
sudo
未经允许修改CUDA/驱动
无预算的大规模下载
无限运行
```

建议设计：

```text
execution_policy.yaml
```

---

# 40. Orchestrator 决策原则

每次决定下一步前必须按顺序判断：

```text
1. Research Spine是什么？

2. 当前最重要Claim是什么？

3. 该Claim目前缺什么Evidence？

4. 当前实验是否真的解决这个Evidence Gap？

5. 是否存在更便宜或更直接的实验？

6. 是否属于当前Priority？

7. 当前Budget是否允许？

8. 什么结果会让我们停止？
```

不能回答这些问题：

```text
不执行实验。
```

---

# 41. 项目最重要的反失控规则

禁止以下模式：

```text
指标不好
→ 无理由增加模块

别人做了某实验
→ 自动跟做

发现新Idea
→ 自动改变研究主题

P0没完成
→ 做大量漂亮图

实验失败
→ 删除记录

性能下降
→ 认为没有价值

Budget用完
→ 自动继续

没有诊断
→ 修改方法

一个Candidate失败
→ 判断整个Idea失败
```

---

# 42. 项目最重要的积极能力

项目应该能够：

```text
理解不完整Idea
↓
恢复论文故事
↓
把抽象Contribution转成技术需求
↓
提出多个高质量技术实现
↓
快速筛选
↓
自动实现
↓
运行
↓
分析
↓
发现失败原因
↓
针对性调整
↓
重复实验
↓
逐步收敛
↓
得到清晰科学证据
```

核心不是“限制Agent”。

而是：

> **让Agent的强大设计和试错能力集中在真正有科学价值的搜索空间里。**

---

# 43. README核心表达原则

项目包装不要强调：

```text
全自动科研
一键写论文
完全替代研究者
无限自主科研
```

重点强调：

```text
面向Idea后的实验阶段
Claim-driven
Research Spine
Method Design Search
Main Experiment First
Evidence-oriented
Negative-result preservation
Venue-aware
Budget-aware
Reproducible
Human-controlled scientific decisions
```

推荐项目核心描述：

> 面向计算机与数据驱动工科论文实验阶段的科研智能体。输入已经形成基本科学故事、创新方向与评价目标的 Research Idea，智能体进一步完成具体方法设计、候选技术方案筛选、代码实现、实验执行、结果诊断与方法迭代，并以论文 Claim 为核心组织证据，在主实验完成后依据目标 Venue 补齐必要实验，最终形成完整、可审计、可复现的论文实验体系。

更简洁的描述：

> From Research Idea to Experimental Evidence.

中文：

> 从科研 Idea，到能够支撑论文故事的实验依据。

---

# 44. 第一版开发优先级

不要一开始开发过多功能。

## MVP Phase 1

首先实现：

```text
research_state
Experiment Contract
Experiment Card
Orchestrator状态机
Runner
Result Record
Experiment Memory
P0优先级
Budget Tracker
```

必须先让：

```text
一个真实小型科研项目
能够完整走通
```

---

## MVP Phase 2

加入：

```text
Method Realization
Design Envelope
Design Iteration
Candidate Screening
Cheap Experiment
Targeted Refinement
```

这是项目真正的科研智能核心。

---

## MVP Phase 3

加入：

```text
Venue Evidence Audit
Claim–Evidence Matrix
Figure–Claim Plan
Submission Readiness
Final Report
```

---

## Later

再考虑：

```text
自动绘图
更复杂并行调度
Dashboard
跨项目实验记忆
多服务器调度
实验数据库
自动论文Results Section接口
```

---

# 45. 项目验收测试

Codex完成第一版后，不要只检查文件是否存在。

必须选择至少一个真实计算机/AI科研Idea进行端到端测试。

验收时检查：

### Intake

能否从不完整 Idea 恢复实验需要的信息。

### Method Design

能否从抽象 Contribution 推导出合理技术机制，而不是要求用户自己设计完整模型。

### Scope Control

能否在合理发挥的同时保持 Research Spine。

### Main Experiment Priority

能否阻止非核心实验提前运行。

### Failure Handling

实验效果差时是否先诊断，而不是随意加模块。

### Method Refinement

能否根据结果进行针对性设计调整。

### Evidence Logic

是否明确每个实验服务哪个 Claim。

### Negative Results

是否完整保留。

### Budget

是否会在合理节点主动讨论资源扩展。

### Venue

是否先确认Venue，后做详细Evidence Audit。

### State Recovery

Codex会话中断后，是否可以仅依靠项目文件恢复实验状态。

### Final Report

是否可以回答：

```text
论文想证明什么？
目前证明到什么程度？
哪些证据可信？
哪些Claim较弱？
为什么停止当前方法搜索？
还缺什么实验？
哪些实验最值得补？
最终应该做哪些表和图？
现在是否已经适合进入论文写作？
```

如果无法清楚回答，项目仍未完成。

---

# 46. Codex开发要求

请基于以上规范设计完整项目。

开发时优先保证：

```text
科研逻辑 > 功能数量

明确状态 > Prompt记忆

结构化数据 > 长篇自然语言状态

可恢复性 > 一次性Agent运行

证据完整性 > 单纯Metric

Targeted Refinement > Random Search

Main Experiment > 辅助实验

Research Spine > 实验过程中临时发现的新故事
```

同时不要把 Research Spine 设计得过死。

项目必须允许：

```text
具体模块设计
模型内部结构
Loss
Representation
Constraint
Fusion
Training mechanism
```

在实验过程中根据证据不断调整。

正确边界是：

> 科学问题和论文故事相对稳定，解决问题的具体技术路径可以主动探索。

---

# 47. 最终期望

最终项目应该让研究者能够给出类似：

```text
我要设计一个多模态生成模型。

核心Idea是分层表征。

Contribution 1希望解决多模态信息编码问题。

Contribution 2希望解决物理表示与约束问题。

我的评价指标已经确定。

目标期刊是XXX。
```

然后科研智能体能够逐步完成：

```text
理解Idea
↓
分析Contribution真正需要解决的问题
↓
提出具体模型机制
↓
筛选候选
↓
实现代码
↓
设计实验
↓
运行
↓
发现问题
↓
改进模型
↓
继续验证
↓
得到稳定主实验
↓
做消融和机制验证
↓
审查Venue实验完整度
↓
补高价值实验
↓
规划表格和图片
↓
输出完整实验报告
```

最终不是得到：

> “很多实验”。

而是得到：

> **一条清晰、连续、能够经受论文审查的 Claim–Method–Evidence 科研故事。**
