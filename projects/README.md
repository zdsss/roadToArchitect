# ShopFlow — 项目制学习路径

> 用一个真实系统贯穿全程，从命令行工具演化到微服务集群。
> 每个 Sprint 都是可运行的系统，功能在前一个基础上叠加。

---

## 系统演化路径

```
Sprint 1        Sprint 2        Sprint 3        Sprint 4-5
命令行工具  →   REST API  →   分层单体  →   订单+认证
                                                   ↓
Sprint 9        Sprint 8        Sprint 7        Sprint 6
熔断+限流  ←   六边形重构  ←   异步消息  ←   Redis缓存
    ↓
Sprint 10       Sprint 11       Sprint 12       Sprint 13
服务拆分   →   Kafka事件流  →   可观测性  →   容器化+CI/CD
```

---

## 目录结构

```
projects/
├── README.md                   ← 本文件：全局规划总览
├── shopflow-python/            ← 第一、二阶段（Sprint 1-9，Python）
│   ├── README.md               ← Sprint 1 任务说明
│   ├── shop/
│   │   ├── cli.py              ← Sprint 1: 命令行入口
│   │   ├── product_store.py    ← Sprint 1: 商品存储（dict）
│   │   ├── api.py              ← Sprint 2: FastAPI 路由（待实现）
│   │   ├── repository/         ← Sprint 3: Repository 层（待实现）
│   │   ├── service/            ← Sprint 3: Service 层（待实现）
│   │   ├── order/              ← Sprint 4: 订单模块（待实现）
│   │   ├── auth/               ← Sprint 5: 认证模块（待实现）
│   │   ├── cache/              ← Sprint 6: 缓存层（待实现）
│   │   ├── workers/            ← Sprint 7: 消息队列 Worker（待实现）
│   │   ├── domain/             ← Sprint 8: 六边形-领域层（待实现）
│   │   ├── ports/              ← Sprint 8: 六边形-端口接口（待实现）
│   │   ├── adapters/           ← Sprint 8: 六边形-适配器（待实现）
│   │   └── resilience/         ← Sprint 9: 熔断+限流（待实现）
│   └── tests/
│       └── test_product_store.py  ← Sprint 1: 单元测试（已有脚手架）
└── shopflow-java/              ← 第三阶段（Sprint 10-13，Java）
    ├── user-service/           ← Sprint 10（待创建）
    ├── product-service/        ← Sprint 10（待创建）
    ├── order-service/          ← Sprint 10（待创建）
    └── api-gateway/            ← Sprint 10（待创建）
```

---

## Sprint 进度总览

### 第一阶段：单体起步（Python，约 4 周）

| Sprint | 状态 | 新增功能 | 核心知识点 | 对应知识库 |
|--------|------|---------|-----------|-----------|
| **Sprint 1** | 🟡 脚手架已就绪 | 命令行商品管理，JSON持久化 | Big-O，dict vs list | `01-fundamentals/algorithms-complexity.md` |
| **Sprint 2** | ⬜ 待开始 | FastAPI REST API | HTTP协议，RESTful设计，状态码 | `01-fundamentals/networking.md`，`03-system-design/api-design.md` |
| **Sprint 3** | ⬜ 待开始 | PostgreSQL + 分层架构 | Controller/Service/Repository，SQL索引，事务 | `04-architecture-patterns/layered.md`，`05-data/sql-vs-nosql.md` |
| **Sprint 4** | ⬜ 待开始 | 订单系统（含3个设计模式） | Factory / Observer / Strategy | `02-design-patterns/`（全部） |
| **Sprint 5** | ⬜ 待开始 | 用户注册登录，JWT认证 | AuthN vs AuthZ，密码哈希，OWASP | `01-fundamentals/security.md` |

### 第二阶段：系统演进（Python 进阶，约 4 周）

| Sprint | 状态 | 新增功能 | 核心知识点 | 对应知识库 |
|--------|------|---------|-----------|-----------|
| **Sprint 6** | ⬜ 待开始 | Redis 缓存商品详情 | Cache-Aside，缓存击穿/雪崩/穿透 | `05-data/caching.md` |
| **Sprint 7** | ⬜ 待开始 | RabbitMQ 异步消息（发邮件/扣库存） | 同步vs异步权衡，幂等消费者，Outbox | `05-data/messaging.md`，`04-architecture-patterns/event-driven.md` |
| **Sprint 8** | ⬜ 待开始 | 六边形架构重构（不加新功能） | 依赖倒置，端口与适配器，可测试性 | `04-architecture-patterns/hexagonal.md` |
| **Sprint 9** | ⬜ 待开始 | 熔断器 + Redis 限流 | 三状态熔断，Token Bucket算法 | `03-system-design/reliability-and-availability.md` |

### 第三阶段：微服务化（Java + Spring Boot，约 5 周）

| Sprint | 状态 | 新增功能 | 核心知识点 | 对应知识库 |
|--------|------|---------|-----------|-----------|
| **Sprint 10** | ⬜ 待开始 | 拆分为3个Spring Boot服务 + API Gateway | 按业务能力拆分，Conway定律，服务发现 | `04-architecture-patterns/microservices.md` |
| **Sprint 11** | ⬜ 待开始 | Kafka事件流 + Saga分布式事务 | 事件驱动，编排式Saga，补偿事务 | `03-system-design/distributed-systems.md` |
| **Sprint 12** | ⬜ 待开始 | Prometheus + 结构化日志 + OpenTelemetry | 四黄金指标，Trace ID，三大支柱 | `06-devops-infrastructure/observability.md` |
| **Sprint 13** | ⬜ 待开始 | Dockerfile + docker-compose + GitHub Actions | 多阶段构建，CI/CD流水线，金丝雀发布 | `06-devops-infrastructure/ci-cd.md`，`containers-and-orchestration.md` |

### 第四阶段：案例研究（约 2 周）

| 任务 | 状态 | 说明 |
|------|------|------|
| URL Shortener 设计文档 | ⬜ 待开始 | 独立设计，放入 `docs/designs/url-shortener.md` |
| Twitter Feed 设计文档 | ⬜ 待开始 | 重点：明星用户 fan-out 问题，放入 `docs/designs/twitter-feed.md` |

---

## 每个 Sprint 的固定产出

每个 Sprint 结束，除了代码之外，还需要完成：

| 产出 | 存放位置 | 说明 |
|------|---------|------|
| ADR（架构决策记录） | `docs/decisions/ADR-NNN.md` | 每次做重要技术选型时写，参考 `ADR-template.md` |
| Trade-off 分析 | Sprint README 或代码注释 | 写明"选了X，获得了A，失去了B" |
| Git commit | 本仓库 | 使用约定式提交：`feat:` / `refactor:` / `test:` / `docs:` |

### 已创建的 ADR

| 编号 | 文件 | 决策内容 | Sprint |
|------|------|---------|--------|
| ADR-001 | `docs/decisions/ADR-template.md` | 用 dict 存储商品（模板示例） | Sprint 1 |

---

## Sprint 详细说明

### Sprint 1 — 命令行商品管理 ✅ 脚手架已就绪

**目标：** 在终端管理商品（增删查改），理解数据结构的时间复杂度

**代码位置：** `shopflow-python/`

**你需要完成的工作：**
1. 打开 `shop/product_store.py`，在每个方法的 `# Time Complexity: TODO` 处填写复杂度分析
2. 运行测试确认通过：`cd shopflow-python && pytest`
3. 写一份 ADR-001，记录"为什么用 dict 不用 list"

**先读这个：** `01-fundamentals/algorithms-complexity.md`

---

### Sprint 2 — REST API（待实现）

**目标：** 把 Sprint 1 的功能通过 HTTP 暴露出去

**你需要新建的文件：** `shop/api.py`

**核心任务：**
1. 用 FastAPI 实现商品 CRUD 的 5 个端点
2. 用 curl 验证每个端点，记录请求/响应
3. 解释每个 HTTP 方法的幂等性（GET/PUT 是幂等的，POST/DELETE 不是）
4. 写 ADR-002：为什么选 REST 而不是 GraphQL

**先读这个：** `01-fundamentals/networking.md`，`03-system-design/api-design.md`

---

### Sprint 3 — 分层架构 + PostgreSQL（待实现）

**目标：** 把内存存储换成真实数据库，引入分层架构

**你需要新建的文件：**
- `shop/repository/product_repo.py` — 负责和数据库通话
- `shop/service/product_service.py` — 负责业务逻辑
- `alembic/` — 数据库迁移配置

**核心任务：**
1. 用 SQLAlchemy 连接 PostgreSQL（Docker 启动：`docker run -e POSTGRES_PASSWORD=pw -p 5432:5432 postgres:16`）
2. 给 `products` 表的 `name` 字段加索引，并用 `EXPLAIN ANALYZE` 验证效果
3. 写一个需要事务的场景（下单时同时扣库存）

**先读这个：** `04-architecture-patterns/layered.md`，`05-data/sql-vs-nosql.md`

---

### Sprint 4 — 订单系统 + 设计模式（待实现）

**目标：** 加入订单模块，在代码中显式使用 3 个设计模式

**你需要新建的文件：** `shop/order/` 模块

**3 个必须用的模式（代码里加注释标注）：**
- `# Pattern: Factory` — 订单状态对象创建（pending/paid/shipped）
- `# Pattern: Observer` — 下单后通知库存和邮件（控制台打印模拟）
- `# Pattern: Strategy` — 不同商品类型的价格计算（普通/会员/促销）

**先读这个：** `02-design-patterns/` 全部（creational / behavioral / structural / anti-patterns）

---

### Sprint 5 — 用户认证（待实现）

**目标：** 加用户系统，保护需要登录才能访问的 API

**你需要新建的文件：** `shop/auth/` 模块

**核心任务：**
1. 用 `passlib[bcrypt]` 哈希存储密码（不能明文！）
2. 登录成功后返回 JWT token
3. 在需要认证的路由上加 `Depends(get_current_user)`
4. 对照 OWASP Top 10，在 README 里写一份自查清单

**先读这个：** `01-fundamentals/security.md`

---

### Sprint 6 — Redis 缓存层（待实现）

**目标：** 用 Redis 缓存商品详情，对比加缓存前后的性能

**你需要新建的文件：** `shop/cache/product_cache.py`

**核心任务：**
1. 实现 Cache-Aside 策略（先查缓存，miss 才查 DB）
2. 用 `ab`（Apache Bench）压测：`ab -n 1000 -c 50 http://localhost:8000/products/1`
3. 填写压测报告（Markdown 表格：有缓存 vs 无缓存的 QPS 和 P99）
4. 故意制造一次缓存穿透（查一个不存在的商品 ID），然后修复它

**先读这个：** `05-data/caching.md`

---

### Sprint 7 — 异步消息队列（待实现）

**目标：** 把"下单后发邮件"和"下单后扣库存"改为异步处理

**你需要新建的文件：** `shop/workers/` 目录

**启动 RabbitMQ：**
```bash
docker run -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

**核心任务：**
1. 下单时只发消息到队列，立即返回给用户
2. Worker 消费消息，执行发邮件/扣库存
3. 故意让 Worker 崩溃，验证消息不丢失（RabbitMQ 持久化）
4. 验证幂等性：同一条消息消费两次，结果一样
5. 写 ADR-003：为什么选 RabbitMQ 而不是 Kafka

**先读这个：** `05-data/messaging.md`，`04-architecture-patterns/event-driven.md`

---

### Sprint 8 — 六边形架构重构（待实现）

**目标：** 把代码重构为六边形架构，不增加任何新功能

**重构后的目录结构：**
```
shop/
├── domain/         ← 纯业务逻辑，零框架依赖
├── ports/          ← 接口定义（ProductRepositoryPort 等）
└── adapters/
    ├── driving/    ← FastAPI 路由（入站适配器）
    └── driven/     ← PostgreSQL、Redis、RabbitMQ（出站适配器）
```

**验收标准：** `pytest tests/domain/` 不需要启动数据库，用 InMemory 适配器跑

**先读这个：** `04-architecture-patterns/hexagonal.md`

---

### Sprint 9 — 熔断器 + 限流（待实现）

**目标：** 给第三方支付调用加熔断器，给 API 加限流

**你需要新建的文件：**
- `shop/resilience/circuit_breaker.py` — 手写，不用库
- `shop/resilience/rate_limiter.py` — 用 Redis 实现 Token Bucket

**实验：**
1. 模拟支付服务宕机（让它一直抛异常），验证熔断器从 Closed → Open
2. 等待 30 秒，验证进入 Half-Open，一次请求成功后恢复 Closed
3. 用 `ab -n 200 -c 20` 验证限流：超过阈值的请求返回 429

**先读这个：** `03-system-design/reliability-and-availability.md`

---

### Sprint 10-13 — Java 微服务（待实现）

Sprint 10-13 在 `shopflow-java/` 目录下实现，使用 Java 21 + Spring Boot 3。

详细说明将在开始第三阶段时补充到各服务的 README 中。

**预计目录结构：**
```
shopflow-java/
├── user-service/       ← 用户注册、登录、JWT
├── product-service/    ← 商品 CRUD
├── order-service/      ← 订单创建、状态流转、Saga
└── api-gateway/        ← Spring Cloud Gateway
```

**先读这个：** `04-architecture-patterns/microservices.md`

---

## 知识库与 Sprint 映射速查

| 知识库文件 | 在哪个 Sprint 用 |
|-----------|----------------|
| `01-fundamentals/algorithms-complexity.md` | Sprint 1 |
| `01-fundamentals/networking.md` | Sprint 2 |
| `01-fundamentals/security.md` | Sprint 5 |
| `01-fundamentals/operating-systems.md` | Sprint 7（进程/线程/IO模型） |
| `02-design-patterns/`（全部） | Sprint 4 |
| `03-system-design/api-design.md` | Sprint 2 |
| `03-system-design/reliability-and-availability.md` | Sprint 9 |
| `03-system-design/distributed-systems.md` | Sprint 11 |
| `04-architecture-patterns/layered.md` | Sprint 3 |
| `04-architecture-patterns/hexagonal.md` | Sprint 8 |
| `04-architecture-patterns/event-driven.md` | Sprint 7、11 |
| `04-architecture-patterns/microservices.md` | Sprint 10 |
| `05-data/sql-vs-nosql.md` | Sprint 3 |
| `05-data/caching.md` | Sprint 6 |
| `05-data/messaging.md` | Sprint 7 |
| `06-devops-infrastructure/observability.md` | Sprint 12 |
| `06-devops-infrastructure/ci-cd.md` | Sprint 13 |
| `06-devops-infrastructure/containers-and-orchestration.md` | Sprint 13 |
| `07-soft-skills/`（全部） | 贯穿全程 |
| `08-case-studies/`（全部） | 第四阶段 |
