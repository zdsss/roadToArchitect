# ShopFlow 项目制学习路径

> **目标读者：** 初中级开发者（A级），通过构建真实系统来掌握软件架构师知识体系。
> **核心理念：** 做中学——每个 Sprint 都是一个可运行的系统，功能在前一个基础上叠加。

---

## 系统：ShopFlow（电商平台）

用同一个系统贯穿全程，从命令行工具一路演化到微服务集群。

```
命令行工具 → REST API → 分层单体 → 加缓存/消息 → 六边形重构 → 微服务拆分 → 容器化
```

---

## 三阶段 · 13个Sprint

### 第一阶段：单体起步（Python，约4周）

| Sprint | 功能 | 核心概念 | 知识库文件 |
|--------|------|---------|-----------|
| Sprint 1 | 命令行商品管理（JSON存储） | Big-O，数据结构选择 | `01-fundamentals/algorithms-complexity.md` |
| Sprint 2 | REST API（FastAPI） | HTTP协议，RESTful设计 | `01-fundamentals/networking.md`，`03-system-design/api-design.md` |
| Sprint 3 | PostgreSQL + 分层架构 | 分层职责，SQL索引，事务 | `04-architecture-patterns/layered.md`，`05-data/sql-vs-nosql.md` |
| Sprint 4 | 订单系统 + 设计模式 | Factory/Observer/Strategy | `02-design-patterns/`全部 |
| Sprint 5 | 用户认证（JWT） | AuthN vs AuthZ，OWASP | `01-fundamentals/security.md` |

### 第二阶段：系统演进（Python进阶，约4周）

| Sprint | 功能 | 核心概念 | 知识库文件 |
|--------|------|---------|-----------|
| Sprint 6 | Redis缓存层 | Cache-Aside，缓存三大问题 | `05-data/caching.md` |
| Sprint 7 | RabbitMQ异步消息 | 同步vs异步，幂等消费者 | `05-data/messaging.md`，`04-architecture-patterns/event-driven.md` |
| Sprint 8 | 六边形架构重构 | 依赖倒置，可测试性 | `04-architecture-patterns/hexagonal.md` |
| Sprint 9 | 熔断器 + 限流 | 三状态熔断，Token Bucket | `03-system-design/reliability-and-availability.md` |

### 第三阶段：微服务化（Java + Spring Boot，约5周）

| Sprint | 功能 | 核心概念 | 知识库文件 |
|--------|------|---------|-----------|
| Sprint 10 | 服务拆分 + API Gateway | 按业务能力拆分 | `04-architecture-patterns/microservices.md` |
| Sprint 11 | Kafka事件驱动 + Saga | 分布式事务，最终一致性 | `03-system-design/distributed-systems.md` |
| Sprint 12 | 可观测性（Metrics/Logs/Traces） | 四黄金指标，Trace ID | `06-devops-infrastructure/observability.md` |
| Sprint 13 | 容器化 + CI/CD | Docker多阶段构建，流水线 | `06-devops-infrastructure/containers-and-orchestration.md`，`ci-cd.md` |

### 第四阶段：案例研究（2周）

1. **URL Shortener**（参考 `08-case-studies/url-shortener.md`）
2. **Twitter Feed**（fan-out问题）

设计文档格式：需求分析 → 规模估算 → API设计 → 高层设计 → 深入组件 → 权衡分析

---

## 贯穿全程的软技能实践

| 实践 | 触发时机 | 产出 |
|------|---------|------|
| ADR | 每次做重要技术决策 | `docs/decisions/ADR-NNN.md` |
| 权衡分析 | Sprint结束复盘 | README里的Trade-off小节 |
| Git commit规范 | 每次提交 | `feat:` / `refactor:` / `docs:` 前缀 |

---

## 目录结构

```
roadToArchitect/
├── projects/
│   ├── shopflow-python/        # 第一、二阶段
│   └── shopflow-java/          # 第三阶段（多模块）
└── docs/
    ├── decisions/              # ADR 文件
    ├── designs/                # 案例研究设计文档
    └── plans/                  # 本文件所在目录
```

---

## 知识库优先完成顺序

**第一阶段前：** `api-design.md`、`layered.md`、`sql-vs-nosql.md`

**第二阶段前：** `caching.md`、`messaging.md`、`event-driven.md`、`hexagonal.md`、`reliability-and-availability.md`

**第三阶段前：** `microservices.md`、`distributed-systems.md`、`observability.md`、`ci-cd.md`、`containers-and-orchestration.md`
