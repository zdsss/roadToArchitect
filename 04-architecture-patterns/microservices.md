# 微服务架构（Microservices Architecture）

微服务不是银弹。它解决了大规模团队协作和系统独立扩展的问题，但代价是显著增加的运维复杂度和分布式系统挑战。本章的核心问题是：**什么时候该拆，怎么拆，以及什么时候不该拆**。

---

## 1. 从单体到微服务

### 1.1 单体架构的痛点（在合适的规模下才是痛点）

```
单体应用（Monolith）：
┌─────────────────────────────────────────┐
│  用户模块 │ 商品模块 │ 订单模块 │ 支付模块  │
│          同一个进程，同一个数据库          │
└─────────────────────────────────────────┘
```

| 痛点 | 触发条件 | 症状 |
|------|---------|------|
| 部署耦合 | 团队 > 10人 | 改一行代码，整个应用重新部署，影响所有模块 |
| 扩展粒度粗 | 某模块是性能瓶颈 | 只能整体扩展，无法只扩展热点模块 |
| 技术栈锁定 | 需要用不同语言优化不同模块 | 全部必须用同一种语言和框架 |
| 启动时间长 | 应用体积变大 | 本地开发启动需要分钟级，影响开发体验 |
| 代码库臃肿 | 代码量 > 百万行 | 修改任何功能都需要理解整个系统 |

> **重要警告：** 上表中的痛点需要在"合适的规模"才真正出现。10人团队的单体应用通常没有这些问题——微服务带来的运维成本可能远超收益。

### 1.2 康威定律

> "系统的设计倾向于反映产生这个系统的组织的沟通结构。" — Mel Conway

```
如果你有4个团队开发一个编译器，你会得到一个4遍的编译器。

ShopFlow 的正确做法：
    用户团队 → user-service
    商品团队 → product-service
    订单团队 → order-service
    支付团队 → payment-service

错误做法（技术层拆分，违反康威定律）：
    前端团队 → frontend-service
    API团队  → api-gateway-service
    DB团队   → database-service
    → 每个功能变更都需要三个团队协调，效率更低
```

---

## 2. 服务边界划分

### 2.1 按业务能力拆分（正确做法）

核心原则：每个服务围绕一个**业务能力**（Business Capability）构建，而不是技术层次。

```
ShopFlow 微服务拆分方案：

user-service（用户服务）
    职责：注册、登录、用户资料、JWT 颁发
    数据：users 表、credentials 表
    边界：所有"这个请求是谁发的"的问题

product-service（商品服务）
    职责：商品 CRUD、分类管理、库存管理
    数据：products 表、categories 表、inventory 表
    边界：所有"卖什么"的问题

order-service（订单服务）
    职责：创建订单、订单状态流转、订单历史
    数据：orders 表、order_items 表
    边界：所有"买了什么"的问题

payment-service（支付服务）
    职责：支付处理、退款、对账
    数据：payments 表、refunds 表
    边界：所有"钱的问题"
```

### 2.2 识别服务边界的实用方法

**高内聚低耦合原则：**
```
好的边界：修改一个服务的内部实现，不需要修改其他服务
坏的边界：改一个字段，要同时改3个服务 → 说明边界画错了

检验方法：
问："完成这个需求，需要同时改几个服务？"
→ 1个服务：好，边界清晰
→ 2-3个服务：可接受，说明是跨服务协作
→ 4个以上：警告！可能是分布式单体（Distributed Monolith）
```

**什么不该拆：**
```
反模式：分布式单体（Distributed Monolith）
    服务A 和 服务B 频繁同步调用对方
    → 部署顺序有依赖（先部署A才能部署B）
    → 本质上还是耦合的，只是加了网络延迟
    → 比单体还差：没有单体的简单，也没有微服务的独立
```

| 场景 | 是否拆分 | 理由 |
|------|---------|------|
| 核心业务功能（订单、支付） | 是 | 高频变更，需要独立扩展 |
| 简单 CRUD（公告管理） | 否 | 变更频率低，单独服务收益 < 成本 |
| 强事务关联（订单+库存） | 谨慎 | 跨服务事务复杂，评估是否值得 |
| 团队规模 < 10人 | 否 | 微服务的运维成本 > 单体的维护成本 |

---

## 3. 服务间通信

### 3.1 同步通信（请求/响应）

| 方案 | 协议 | 数据格式 | 适用场景 |
|------|------|---------|---------|
| REST | HTTP/1.1 | JSON | 通用，外部暴露 |
| gRPC | HTTP/2 | Protobuf（二进制） | 内部高性能服务间调用 |
| GraphQL | HTTP | JSON | 复杂查询，移动端 |

**gRPC 服务定义示例：**
```protobuf
// user.proto
syntax = "proto3";

service UserService {
    rpc GetUser(GetUserRequest) returns (UserResponse);
    rpc ValidateToken(ValidateTokenRequest) returns (TokenValidationResponse);
}

message GetUserRequest {
    int64 user_id = 1;
}

message UserResponse {
    int64 id = 1;
    string email = 2;
    string role = 3;
}
```

### 3.2 异步通信（消息/事件）

```
同步调用的问题：
    order-service → HTTP → inventory-service
    如果 inventory-service 宕机 → order-service 也失败
    如果 inventory-service 慢 → order-service 也慢

异步消息的优势：
    order-service → Kafka → inventory-service（异步处理）
    inventory-service 宕机 → 消息积压，恢复后继续处理
    inventory-service 慢 → 不影响 order-service 的响应时间
```

### 3.3 选型决策

```
需要立即得到响应？（查询用户信息、获取商品价格）
├── 是 → 同步（REST 或 gRPC）

需要通知其他服务，但不需要立即响应？（下单后扣库存、发邮件）
├── 是 → 异步（消息队列/事件）

需要在多个服务间执行原子操作？（下单+扣库存+支付）
└── Saga 模式（通过补偿事务保证最终一致性）
```

---

## 4. API Gateway

### 4.1 为什么需要 API Gateway

没有 API Gateway 时，客户端需要了解每个服务的地址：

```
客户端 → user-service:8001（登录）
客户端 → product-service:8002（查商品）
客户端 → order-service:8003（下单）

问题：
- 客户端必须知道所有服务地址（内部实现泄露）
- 每个服务都要独立处理认证、限流、SSL
- 服务地址变了，客户端全部要改
```

有了 API Gateway：
```
客户端 → API Gateway（统一入口）
         ├── /auth/* → user-service
         ├── /products/* → product-service
         └── /orders/* → order-service

API Gateway 负责：
- 路由（根据 URL 转发到对应服务）
- 认证（验证 JWT，服务不需要各自验证）
- 限流（集中限流，而非各服务分散实现）
- SSL 终结（Gateway 处理 HTTPS，内部服务可以用 HTTP）
- 日志（统一记录所有入站请求）
- 请求聚合（一个请求组合多个服务的数据）
```

### 4.2 Nginx 路由配置示例

```nginx
# nginx.conf
upstream user_service {
    server user-service:8001;
}
upstream product_service {
    server product-service:8002;
}
upstream order_service {
    server order-service:8003;
}

server {
    listen 443 ssl;
    server_name api.shopflow.com;

    # SSL 终结：外部 HTTPS，内部 HTTP
    ssl_certificate /etc/ssl/shopflow.crt;
    ssl_certificate_key /etc/ssl/shopflow.key;

    # 限流：每个 IP 每秒 10 个请求
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # 路由规则
    location /v1/auth/ {
        proxy_pass http://user_service/;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /v1/products/ {
        proxy_pass http://product_service/;
        # 商品查询可以缓存
        proxy_cache products_cache;
        proxy_cache_valid 200 60s;
    }

    location /v1/orders/ {
        # 订单接口需要认证（通过 auth_request 验证 JWT）
        auth_request /auth/validate;
        proxy_pass http://order_service/;
    }
}
```

### 4.3 API Gateway vs Service Mesh

| 维度 | API Gateway | Service Mesh（Istio/Linkerd） |
|------|------------|---------------------------|
| 位置 | 南北流量（外部到内部） | 东西流量（服务间） |
| 关注点 | 入口路由、认证、限流 | 服务间可靠通信、mTLS、熔断 |
| 实现方式 | 独立服务（Nginx/Kong） | Sidecar 代理（每个 Pod 旁边注入） |
| 复杂度 | 低 | 高（运维复杂） |
| 适用阶段 | 任何微服务架构 | 大规模微服务（> 20个服务） |

---

## 5. 服务发现（Service Discovery）

微服务的实例 IP 地址是动态的（Pod 重启、扩缩容），服务间如何找到对方？

### 5.1 客户端发现 vs 服务端发现

```
客户端发现：
    服务A → 查注册中心（Eureka/Consul）→ 获取服务B的地址列表 → 自行负载均衡 → 服务B
    优点：客户端控制负载均衡策略
    缺点：每个客户端都要实现服务发现逻辑

服务端发现（Kubernetes 内置）：
    服务A → DNS（product-service.default.svc.cluster.local） → kube-proxy → 服务B
    优点：客户端无感知，平台处理
    缺点：对平台有依赖
```

**Kubernetes 中的服务发现（推荐）：**
```yaml
# Service 对象：提供稳定的 DNS 名称
apiVersion: v1
kind: Service
metadata:
  name: product-service
spec:
  selector:
    app: product-service  # 选择所有标签为 app=product-service 的 Pod
  ports:
    - port: 80
      targetPort: 8002
  type: ClusterIP  # 仅集群内部可访问

# 其他服务通过 DNS 访问：
# http://product-service/products/42
# （Kubernetes 自动解析并负载均衡到健康的 Pod）
```

---

## 6. 数据管理：每服务一个数据库

### 6.1 Database per Service 模式

微服务的核心原则：**每个服务独占自己的数据库，不共享**。

```
❌ 共享数据库（反模式）：
    order-service ──┐
    product-service─┤── 同一个 PostgreSQL
    user-service ───┘
    问题：一个服务的慢查询影响所有服务；Schema 变更需要所有团队协调

✅ 独立数据库（正确做法）：
    user-service → users_db（PostgreSQL）
    product-service → products_db（PostgreSQL）
    order-service → orders_db（PostgreSQL）
    每个服务完全控制自己的数据库，可以独立演化 Schema
```

### 6.2 跨服务查询（没有 JOIN 怎么办）

```python
# 场景：获取订单详情，需要订单信息 + 用户信息 + 商品信息

# 反模式：直接跨库 JOIN（破坏服务独立性）
SELECT o.*, u.email, p.name
FROM orders_db.orders o
JOIN users_db.users u ON u.id = o.user_id
JOIN products_db.products p ON p.id = oi.product_id
-- ❌ 不同服务的数据库混在一起

# 正确做法1：API 聚合（在 API Gateway 或 BFF 层）
async def get_order_detail(order_id: int) -> dict:
    # 并行调用多个服务
    order, items = await asyncio.gather(
        order_service.get_order(order_id),
        order_service.get_order_items(order_id)
    )
    user, products = await asyncio.gather(
        user_service.get_user(order["user_id"]),
        product_service.get_products([item["product_id"] for item in items])
    )
    # 在内存里聚合数据
    return assemble_order_detail(order, user, items, products)

# 正确做法2：CQRS + 数据冗余（读模型）
# 创建一个专门用于查询的"订单详情"读模型
# 通过事件驱动保持同步（不要求实时一致）
```

---

## 7. 微服务的代价

在决定拆分之前，必须了解这些成本：

| 成本 | 说明 |
|------|------|
| 运维复杂度 | 10个服务 = 10个部署流水线、10套监控、10个日志系统 |
| 分布式追踪 | 一次用户请求跨越5个服务，出错时如何找到问题？（需要 Trace ID） |
| 数据一致性 | 跨服务事务比本地事务复杂10倍（Saga 模式） |
| 网络延迟 | 服务间 HTTP 调用 ~1ms，积累起来不可忽视 |
| 本地开发 | 需要同时启动多个服务才能运行整个系统 |
| 团队技能要求 | Docker、Kubernetes、服务网格，每项都需要学习成本 |

### 何时开始拆分

```
信号1：单体部署频率受限（一天只能发布一次，因为测试太慢）
信号2：某个模块成为性能瓶颈，但无法独立扩展
信号3：不同模块需要不同技术栈（如推荐系统需要 Python ML，订单系统需要 Java）
信号4：团队规模增长到多个团队同时修改同一个代码库，合并冲突严重
信号5：不同模块有不同的可用性要求（支付需要五个九，推荐可以三个九）

永远不该拆分的时机：
- 产品还在验证阶段（先活下来，再优化架构）
- 团队少于10人
- 技术债严重的单体（先重构，再拆分）
```

---

## 8. ShopFlow 第三阶段架构

```
                        互联网
                          │
                    [API Gateway]
                    Nginx / Spring Cloud Gateway
                    - SSL 终结
                    - JWT 验证
                    - 限流（1000 req/s/IP）
                    - 路由
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    [user-service]  [product-service] [order-service]
    Java/Spring     Java/Spring        Java/Spring
    Port: 8001      Port: 8002         Port: 8003
    DB: users_db    DB: products_db    DB: orders_db
         │                │                │
         └────────────────┼────────────────┘
                          │
                    [Kafka Cluster]
                    事件总线
                    Topic: order-events
                    Topic: inventory-events
```

**服务间通信选择：**

| 调用 | 方式 | 理由 |
|------|------|------|
| API Gateway → 各服务 | 同步 REST | 客户端需要立即得到响应 |
| order-service → inventory-service（扣库存） | 异步 Kafka | 不需要立即确认，解耦容错 |
| order-service → notification-service（发邮件） | 异步 Kafka | 典型的"发出去不管"场景 |
| Gateway → user-service（验证JWT） | 同步 gRPC | 高频调用，性能敏感 |

---

## Key Architect Takeaways

- **微服务是组织架构的技术体现**：服务边界应该按业务能力划分，与团队边界对齐（康威定律）。按技术层划分是反模式
- **不要过早拆分**：10人团队的单体应用几乎没有微服务能解决的问题，却要承担全部微服务的复杂度。先把单体做好，等到真正的痛点出现再拆
- **分布式单体是最差的选择**：如果微服务之间有大量同步调用和部署依赖，它既没有单体的简单，也没有微服务的独立——是两者缺点的叠加
- **API Gateway 是标准配置**：认证、限流、路由在 Gateway 统一做，各服务专注业务逻辑。服务网格（Service Mesh）留到服务数量 > 20 再考虑
- **每服务独立数据库是底线**：共享数据库使服务间产生隐性耦合，Schema 变更变成全团队协调工作，彻底违背了微服务的初衷
