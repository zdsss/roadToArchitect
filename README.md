# Road to Software Architect

A structured knowledge base for engineers growing into Software Architect roles.

## Recommended Reading Order

1. [Fundamentals](./01-fundamentals/README.md) — CS basics, networking, OS, security
2. [Design Patterns](./02-design-patterns/README.md) — GoF patterns, anti-patterns
3. [System Design](./03-system-design/README.md) — Scalability, reliability, distributed systems
4. [Architecture Patterns](./04-architecture-patterns/README.md) — Microservices, event-driven, layered, hexagonal
5. [Data](./05-data/README.md) — Databases, caching, messaging
6. [DevOps & Infrastructure](./06-devops-infrastructure/README.md) — CI/CD, containers, cloud
7. [Soft Skills](./07-soft-skills/README.md) — Communication, trade-off analysis, leadership
8. [Case Studies](./08-case-studies/README.md) — Real-world architecture teardowns

## Sections

| # | Topic | Description |
|---|-------|-------------|
| 1 | [Fundamentals](./01-fundamentals/README.md) | CS basics, networking, OS, security |
| 2 | [Design Patterns](./02-design-patterns/README.md) | GoF patterns, anti-patterns |
| 3 | [System Design](./03-system-design/README.md) | Scalability, reliability, distributed systems |
| 4 | [Architecture Patterns](./04-architecture-patterns/README.md) | Microservices, event-driven, layered, hexagonal |
| 5 | [Data](./05-data/README.md) | Databases, caching, messaging |
| 6 | [DevOps & Infrastructure](./06-devops-infrastructure/README.md) | CI/CD, containers, cloud |
| 7 | [Soft Skills](./07-soft-skills/README.md) | Communication, trade-off analysis, leadership |
| 8 | [Case Studies](./08-case-studies/README.md) | Real-world architecture teardowns |

## ShopFlow Project Progress

实践项目：通过构建电商系统学习架构知识（详见 [学习路径](./docs/plans/2026-03-26-project-learning-path.md)）

### 第一阶段：单体起步（Python）

- [x] **Sprint 1** — 命令行商品管理（JSON 存储）
  - 完成时间：2026-03-26
  - 核心概念：Big-O 复杂度分析，数据结构选择

- [x] **Sprint 2** — REST API（FastAPI）
  - 完成时间：2026-03-26
  - 核心概念：HTTP 协议，RESTful 设计，幂等性
  - ADR：[ADR-002 REST vs GraphQL](./docs/decisions/ADR-002-api-style-rest-vs-graphql.md)

- [ ] **Sprint 3** — PostgreSQL + 分层架构
- [ ] **Sprint 4** — 订单系统 + 设计模式
- [ ] **Sprint 5** — 用户认证（JWT）

### 第二阶段：系统演进（Python 进阶）

- [ ] **Sprint 6** — Redis 缓存层
- [ ] **Sprint 7** — RabbitMQ 异步消息
- [ ] **Sprint 8** — 六边形架构重构
- [ ] **Sprint 9** — 熔断器 + 限流

### 第三阶段：微服务化（Java + Spring Boot）

- [ ] **Sprint 10** — 服务拆分 + API Gateway
- [ ] **Sprint 11** — Kafka 事件驱动 + Saga
- [ ] **Sprint 12** — 可观测性（Metrics/Logs/Traces）
- [ ] **Sprint 13** — 容器化 + CI/CD

---

## How to Use

- Each section has its own `README.md` with a topic checklist.
- Each topic file is self-contained: theory, key concepts, examples, and further reading.
- Read sequentially or jump to any section you need.
