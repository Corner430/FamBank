<!--
  Sync Impact Report
  ===========================
  Version change: 1.0.0 → 2.0.0 (multi-tenant product evolution)
  Modified principles:
    - I. 章程即法: updated to reflect charter-as-template model
    - III. 分层账户隔离: expanded for per-child account isolation
    - VII. 简洁优先: relaxed to allow platform-level infrastructure
  Added sections:
    - VIII. 租户隔离 (Tenant Isolation) — new core principle
    - IX. 认证与身份 (Authentication & Identity) — new core principle
    - Domain Constraints: 平台与多租户 section
  Removed sections:
    - Domain Constraints > 安全与合规 > "该系统为家庭内部记账工具" (no longer accurate)
  Templates requiring updates:
    - .specify/templates/plan-template.md — review Constitution Check for new principles
    - .specify/templates/spec-template.md — may reference new tenant/auth constraints
    - .specify/templates/tasks-template.md — no changes needed
  Follow-up TODOs:
    - All future feature specs MUST address tenant isolation
    - Migration plan needed for existing single-family data
-->

# FamBank Constitution

## Core Principles

### I. 章程即法 (Charter-as-Code)

章程文档（`doc/家庭内部银行-分层资产管理章程.md`）是系统行为的
唯一权威来源。所有业务逻辑 MUST 与章程条款一一对应，不得自行
"合理推断"规则。若章程未明确定义的行为，系统 MUST 拒绝执行
并提示用户。

章程作为**平台默认模板**提供给每个新建家庭。各家庭可在平台允许
的参数范围内自定义配置（如分流比例、利率），但业务规则的执行
逻辑 MUST 忠于章程定义，不可由家庭自行覆盖。

**理由**: 该系统模拟银行契约，任何偏离章程的行为都会破坏甲乙
双方的信任基础。多家庭场景下，模板化确保一致的规则基础。

### II. 金额精确 (Financial Precision)

所有金额计算 MUST 使用定点小数（如 Decimal / 整数分），禁止
浮点运算。利息、罚金、分流比例的计算结果 MUST 精确到分
（0.01 元）。每一笔余额变动 MUST 可追溯至具体的章程条款编号。

**理由**: 金融计算的浮点误差会累积，导致对账失败，损害系统
可信度。

### III. 分层账户隔离 (Account Isolation)

**每位孩子（乙方）**独立持有 A-零钱宝、B-梦想金、C-牛马金
三个账户。同一家庭内不同孩子的账户 MUST 在数据层面严格隔离，
利率计算、溢出、结算 MUST 按孩子个体独立进行。

跨账户资金流转 MUST 且仅能通过章程明确定义的路径（分流、派息、
溢出、违约划转、紧急赎回）进行。任何未在章程中定义的转账路径
MUST 被拒绝。不同孩子的账户之间 MUST 不允许任何资金流转。

**理由**: 账户隔离是整个分层利率和风控体系的基础，混用将导致
利率计算和容量约束失效。多子女场景下，独立核算是公平性的保障。

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

系统 MUST 只实现章程明确要求的功能和产品化所必需的平台基础设施
（认证、租户隔离、家庭管理），不得预设未来需求。优先使用最简单
的技术方案满足要求。YAGNI 原则仍然适用于业务功能层面。

**理由**: 产品化需要认证和多租户等基础设施，但业务功能仍应保持
克制，核心价值在于忠实执行章程。

### VIII. 租户隔离 (Tenant Isolation)

每个家庭是独立的租户单元。家庭间数据 MUST 严格隔离，任何 API
请求 MUST 只能访问当前认证用户所属家庭的数据。数据库查询 MUST
在服务层强制注入 family_id 过滤条件，不依赖调用方手动传递。
跨家庭数据访问 MUST 在架构层面不可能发生，而非仅依靠业务逻辑
判断。

**理由**: 作为 To C 产品，数据隔离是用户信任和隐私保护的基础。
任何数据泄露都会造成不可挽回的信任损失。

### IX. 认证与身份 (Authentication & Identity)

用户身份认证 MUST 基于手机号 + 短信验证码，不使用密码。JWT
token MUST 携带 user_id、family_id 和 role 信息。认证凭据
（手机号）MUST 与业务数据分离存储。会话管理 MUST 支持 token
过期和刷新机制。

**理由**: 手机号验证码是国内用户最熟悉的认证方式，降低使用门槛。
去除 PIN 码简化了操作流程，适合面向 C 端用户的产品体验。

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
- 用户认证信息（手机号、验证码）MUST 安全传输和存储
- 家庭数据 MUST 不可被其他家庭访问（参见原则 VIII）
- 数据 MUST 有备份机制
- 系统 MUST 支持用户数据导出和账户注销

### 平台与多租户

- 每个家庭为独立租户，所有业务表 MUST 包含 family_id
- 每个孩子的账户 MUST 包含 user_id，按孩子维度独立核算
- 配置参数（分流比例、利率等）MUST 按 family_id 隔离
- 家庭内角色为两级：parent（家长）和 child（孩子）
- 家长可查看聚合 dashboard 和切换查看每个孩子
- 孩子仅可查看自己的数据
- 短信验证码服务：腾讯云 SMS（开发阶段使用假验证码）

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
- 所有新 feature spec MUST 说明如何满足租户隔离（原则 VIII）
  和认证（原则 IX）的要求
- 运行时开发指引参见 `.specify/` 目录下的模板文件

**Version**: 2.0.0 | **Ratified**: 2026-02-28 | **Last Amended**: 2026-03-01
