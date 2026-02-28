<!--
  Sync Impact Report
  ===========================
  Version change: 0.0.0 → 1.0.0 (initial ratification)
  Modified principles: N/A (initial version)
  Added sections:
    - Core Principles (7 principles)
    - Domain Constraints (financial accuracy, rule fidelity)
    - Development Workflow (testing, review, deployment)
    - Governance
  Removed sections: N/A
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ no changes needed (Constitution Check placeholder intact)
    - .specify/templates/spec-template.md ✅ no changes needed
    - .specify/templates/tasks-template.md ✅ no changes needed
  Follow-up TODOs: None
-->

# FamBank Constitution

## Core Principles

### I. 章程即法 (Charter-as-Code)

章程文档（`doc/家庭内部银行-分层资产管理章程.md`）是系统行为的
唯一权威来源。所有业务逻辑 MUST 与章程条款一一对应，不得自行
"合理推断"规则。若章程未明确定义的行为，系统 MUST 拒绝执行
并提示用户。

**理由**: 该系统模拟银行契约，任何偏离章程的行为都会破坏甲乙
双方的信任基础。

### II. 金额精确 (Financial Precision)

所有金额计算 MUST 使用定点小数（如 Decimal / 整数分），禁止
浮点运算。利息、罚金、分流比例的计算结果 MUST 精确到分
（0.01 元）。每一笔余额变动 MUST 可追溯至具体的章程条款编号。

**理由**: 金融计算的浮点误差会累积，导致对账失败，损害系统
可信度。

### III. 分层账户隔离 (Account Isolation)

三个账户（A-零钱宝、B-梦想金、C-牛马金）MUST 在数据层面
严格隔离。跨账户资金流转 MUST 且仅能通过章程明确定义的路径
（分流、派息、溢出、违约划转、紧急赎回）进行。任何未在章程
中定义的转账路径 MUST 被拒绝。

**理由**: 账户隔离是整个分层利率和风控体系的基础，混用将导致
利率计算和容量约束失效。

### IV. 结算原子性 (Settlement Atomicity)

月度结算的四步 SOP（C派息 → B溢出 → B计息 → 违约划转）
MUST 作为不可分割的原子操作执行，严格按序执行。任何步骤
失败 MUST 回滚整个结算周期。结算过程中 MUST 禁止并发的
入账或消费操作。

**理由**: 章程附录明确定义了结算顺序依赖关系（如"溢出后
余额为计息基数"），乱序或部分执行会产生错误结果。

### V. 审计可追溯 (Audit Trail)

每一笔交易（入账、消费、利息、罚金、划转）MUST 记录完整
的审计日志，包含：时间戳、操作类型、涉及账户、金额、
结算前余额、结算后余额、关联章程条款编号。日志 MUST 不可
篡改（仅追加）。

**理由**: 甲乙双方需要透明的交易记录来验证系统行为符合章程，
这是建立信任和解决争议的基础。

### VI. 测试覆盖 (Test Discipline)

涉及资金计算的核心逻辑（分流、分层利率、溢出、罚金公式）
MUST 有对应的单元测试，测试用例 MUST 覆盖章程中所有公式的
边界条件。结算 SOP MUST 有集成测试验证完整流程。测试数据
MUST 包含章程公式可直接验算的案例。

**理由**: 金融系统的错误代价高昂且难以追溯，充分的测试是
保障章程执行正确性的最后一道防线。

### VII. 简洁优先 (Simplicity)

系统 MUST 只实现章程明确要求的功能，不得预设未来需求。
优先使用最简单的技术方案满足章程要求。YAGNI 原则：如果
章程没有要求，就不实现。

**理由**: 该系统的核心价值在于忠实执行章程而非功能丰富，
过度设计会增加维护成本和出错概率。

## Domain Constraints

### 金额与比例

- 分流比例（15%/30%/55%）MUST 在配置中可调但默认值与章程一致
- 利率参数（B层级利率 2.0%/1.2%/0.3%，C年化 5%）MUST 可配置
- 所有比例和利率调整 MUST 留存变更记录（对应章程第8条公告机制）
- 罚倍数 α=2 MUST 可配置

### 时间与周期

- 结算周期为自然月
- 愿望清单锁定期：3个月
- 账户B停息触发：12个月无合规购买
- 账户C锁定：18岁前不可动用本金（紧急赎回除外）

### 安全与合规

- 系统 MUST 不存储真实金融账户信息
- 该系统为家庭内部记账工具，不涉及真实资金转移
- 数据 MUST 有本地备份机制

## Development Workflow

### 代码审查

- 涉及资金计算逻辑的变更 MUST 附带对应章程条款的引用
- 结算 SOP 相关代码变更 MUST 通过全量结算测试

### 版本管理

- 遵循语义化版本：MAJOR（章程重大变更）、MINOR（新增功能）、
  PATCH（修复/优化）
- 章程版本与软件版本独立管理，但 MUST 记录对应关系

### 部署

- 结算相关变更 MUST 在非结算日部署
- 部署后 MUST 验证历史数据一致性

## Governance

本宪章是 FamBank 项目所有开发实践的最高准则。

- 所有 PR/代码审查 MUST 验证是否符合本宪章原则
- 任何与本宪章冲突的实践，以本宪章为准
- 宪章修订 MUST 记录变更理由、影响范围，并更新版本号
- 复杂性 MUST 有充分理由：每一个超出最简方案的设计决策
  都需要在 plan.md 的 Complexity Tracking 表中说明
- 运行时开发指引参见 `.specify/` 目录下的模板文件

**Version**: 1.0.0 | **Ratified**: 2026-02-28 | **Last Amended**: 2026-02-28
