# Research: FamBank 家庭内部银行核心系统

**Date**: 2026-02-28
**Branch**: `001-fambank-core`

## 1. Backend Language/Framework

**Decision**: Python 3.12 + FastAPI

**Rationale**: Python 的 `decimal.Decimal` 是标准库内置类型，天然满足金额精确计算要求（宪章原则 II）。FastAPI 的 Pydantic 集成可在 API 边界强制 Decimal 类型校验，防止浮点污染。最小化样板代码，符合简洁优先原则（宪章原则 VII）。

**Alternatives considered**:
- Flask: 更简单但缺少内置请求校验和自动 API 文档，需额外引入 marshmallow 等库
- Django: 对单家庭应用过于臃肿，ORM/Admin/中间件栈为多租户 SaaS 设计
- Node.js (Express): JavaScript 的 `number` 类型为 IEEE 754 浮点，金额计算需处处使用 `decimal.js`，易出错
- Go: 适合高性能服务，但对 CRUD + 业务逻辑应用偏冗长

## 2. Database

**Decision**: MySQL 8.0

**Rationale**: MySQL 提供成熟的 ACID 事务支持（InnoDB），满足结算原子性要求（宪章原则 IV）。`DECIMAL(12,2)` 类型原生支持定点小数存储，金额精确到分。支持触发器（用于审计表保护）。作为最广泛部署的关系型数据库之一，运维工具和文档丰富。

**Alternatives considered**:
- SQLite: 零运维但缺少网络访问能力，不便于远程管理和未来扩展
- PostgreSQL: 功能更强但对单家庭应用偏重

**金额存储策略**: 数据库中所有金额以整数分存储（如 ¥12.34 存为 1234），使用 `BIGINT` 类型。应用层使用 Python `Decimal` 处理显示和计算。

## 3. Frontend Framework

**Decision**: Vue 3 (Composition API) + Vite

**Rationale**: Vue 的单文件组件（template + script + style）直观简洁，学习曲线最平缓。Vite 提供近即时热更新。对于5-6个页面的小型应用，Vue 的响应式系统完全够用，无需 React 生态的状态管理复杂度。

**Alternatives considered**:
- React: 生态更大但复杂度表面也更大（JSX、状态管理选择困难），5-6个页面不需要
- Svelte: 可能更简单，但生态较小、社区资源较少
- 纯 HTML + CSS + JS: 手动 DOM 管理在金融数据表格和表单校验场景下易产生混乱代码
- HTMX + 服务端模板: 强有力的竞争者，但多步结算向导等交互模式会受限

## 4. Testing

**Decision**: pytest (后端) + Vitest (前端)

**Rationale**: pytest 是 Python 测试事实标准，支持参数化测试用例，可精确断言 `Decimal` 相等。配合 FastAPI TestClient 可做 API 集成测试。Vitest 是 Vite 项目的自然搭配，比 Jest 更快。

**测试策略**:
- 单元测试：所有金额计算函数（分层利率、分流、罚金公式），使用 Decimal 断言
- 集成测试：结算原子性（验证部分失败时回滚），审计日志完整性
- 审计测试：验证仅追加（无记录消失或被修改）

## 5. Deployment

**Decision**: 直接部署（uv 管理 Python 依赖）

**Rationale**: 使用 uv 作为 Python 包管理器，依赖安装速度快且锁文件可重复。前端通过 npm 构建后由 FastAPI 托管静态文件。MySQL 作为独立服务运行。无需 Docker 容器化，减少部署复杂度。

**备份策略**: 使用 `mysqldump` 定期备份数据库，可通过 cron 自动执行。

**Alternatives considered**:
- Docker Compose: 增加一层容器抽象，对此项目不必要

## 6. Financial Precision Chain

```
HTTP 请求 (JSON string "12.34")
  → Pydantic Decimal field (校验)
    → Python Decimal 运算 (业务逻辑)
      → MySQL BIGINT (存储: 1234 分)
```

浮点数在任何环节都不参与。

## 7. Key Architectural Decisions

| Decision | Rationale | Constitution Principle |
|----------|-----------|----------------------|
| 整数分存储 | 消除存储层小数歧义 | II. 金额精确 |
| MySQL InnoDB 事务 | 4步结算包裹在单一事务中 | IV. 结算原子性 |
| MySQL trigger 禁止审计表 UPDATE/DELETE | 数据库级别强制仅追加 | V. 审计可追溯 |
| 直接部署 + uv | 最简部署方案 | VII. 简洁优先 |
| Pydantic Decimal 校验 | API 边界拦截浮点 | II. 金额精确 |
