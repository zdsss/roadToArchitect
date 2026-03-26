# API 设计（API Design）

API 是系统与外界的契约。一个设计良好的 API 能让调用方直觉性地使用，能独立演化，能在规模增长时保持稳定。本章从架构师视角审视 API 设计的全貌。

---

## 1. API 风格对比：REST vs GraphQL vs gRPC

在开始设计之前，先选对工具。三种主流 API 风格各有适用场景：

| 维度 | REST | GraphQL | gRPC |
|------|------|---------|------|
| 协议 | HTTP/1.1 | HTTP/1.1 or HTTP/2 | HTTP/2 |
| 数据格式 | JSON/XML | JSON | Protobuf（二进制） |
| 请求方式 | 多端点（每资源一个URL） | 单端点（POST /graphql） | 强类型服务定义（.proto） |
| 获取数据 | 可能 over-fetch 或 under-fetch | 精确获取所需字段 | 精确获取所需字段 |
| 类型系统 | 弱（靠文档约定） | 强（Schema 即契约） | 强（.proto 文件） |
| 浏览器友好 | 是 | 是 | 否（需要代理） |
| 流式支持 | 有限（SSE/Chunked） | Subscription | 原生支持双向流 |
| 性能 | 中等 | 中等（查询解析有开销） | 高（Protobuf 序列化快） |
| 学习曲线 | 低 | 中 | 中 |
| 典型场景 | 公共API、Web服务 | 移动端、复杂前端 | 服务间通信、高性能场景 |

### 选型决策树

```
需要对外暴露给浏览器/移动端？
├── 是 → 前端数据需求复杂（字段差异大）？
│         ├── 是 → 考虑 GraphQL
│         └── 否 → REST（99%的情况下足够）
└── 否（微服务内部通信）
          ├── 需要高性能 / 低延迟 → gRPC
          ├── 需要流式处理 → gRPC
          └── 团队已熟悉HTTP + JSON → REST
```

> **架构师提示：** 不要为了时髦而选 GraphQL。REST 在大多数场景下足够，且维护成本更低。如果前端团队在抱怨 over-fetching，才是考虑 GraphQL 的信号。

---

## 2. RESTful 设计原则

### 2.1 资源导向（Resource-Oriented）

REST 的核心是**资源**，URL 表示名词（资源），HTTP 方法表示动词（操作）。

**好的设计：**
```
GET    /products          # 获取商品列表
POST   /products          # 创建商品
GET    /products/{id}     # 获取单个商品
PUT    /products/{id}     # 全量更新商品
PATCH  /products/{id}     # 部分更新商品
DELETE /products/{id}     # 删除商品

GET    /orders/{id}/items # 获取订单下的商品列表
```

**错误的设计（动词 URL）：**
```
POST /createProduct       # ❌ 用HTTP方法表达动词，URL不该有动词
GET  /getProductById/1    # ❌ getById 是动词
POST /deleteProduct/1     # ❌ 用POST做删除，混淆HTTP语义
```

### 2.2 HTTP 方法语义

| 方法 | 幂等性 | 安全性 | 用途 | 成功状态码 |
|------|--------|--------|------|-----------|
| GET | 是 | 是 | 获取资源，不修改状态 | 200 |
| POST | 否 | 否 | 创建资源 | 201 Created |
| PUT | 是 | 否 | 全量替换资源 | 200 or 204 |
| PATCH | 否* | 否 | 部分更新 | 200 or 204 |
| DELETE | 是 | 否 | 删除资源 | 204 No Content |
| HEAD | 是 | 是 | 获取响应头（不含Body） | 200 |
| OPTIONS | 是 | 是 | 获取可用方法（CORS预检） | 200 |

> **幂等性**：多次相同请求，结果与一次相同。PUT 是幂等的（重复设置同一值），POST 不是（每次创建新资源）。
> **安全性**：不修改服务器状态。

### 2.3 HTTP 状态码规范

状态码是 API 与调用方之间的沟通语言。正确使用状态码能让调用方不用解析 body 就知道发生了什么。

| 范围 | 含义 | 常用状态码 |
|------|------|-----------|
| 2xx | 成功 | 200 OK, 201 Created, 204 No Content |
| 3xx | 重定向 | 301 Moved Permanently, 304 Not Modified |
| 4xx | 客户端错误 | 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 422 Unprocessable Entity, 429 Too Many Requests |
| 5xx | 服务端错误 | 500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout |

**常见误用：**
```
# ❌ 永远返回 200，把错误信息放 body
HTTP/1.1 200 OK
{"code": 404, "message": "Product not found"}

# ✅ 正确使用状态码
HTTP/1.1 404 Not Found
{"error": "PRODUCT_NOT_FOUND", "message": "Product with id=123 does not exist"}
```

### 2.4 统一错误响应格式

```python
# 推荐的错误响应结构
{
    "error": {
        "code": "PRODUCT_NOT_FOUND",      # 机器可读的错误码
        "message": "Product not found",    # 人类可读的描述
        "detail": "No product with id=123 in the catalog",  # 可选：详细说明
        "trace_id": "abc-123-def"          # 链路追踪ID，方便排查
    }
}
```

> **架构师提示：** `trace_id` 是可观测性的起点。在响应里返回 trace_id，调用方遇到问题时可以用它在日志系统里追踪整条链路。

---

## 3. URL 设计规范

### 3.1 命名约定

```
# 使用复数名词
/products          ✅
/product           ❌

# 使用连字符分隔单词（kebab-case）
/product-categories   ✅
/productCategories    ❌（URL不推荐camelCase）
/product_categories   ❌（下划线在URL里不直观）

# 嵌套资源表达归属关系（不超过2层）
/orders/{orderId}/items           ✅
/orders/{orderId}/items/{itemId}  ✅
/users/{userId}/orders/{orderId}/items/{itemId}  ❌（太深）

# 超过2层时，用查询参数过滤
GET /items?orderId=123&userId=456  ✅（扁平化）
```

### 3.2 版本控制（API Versioning）

API 版本控制是管理 Breaking Change 的策略。常见方案：

| 方案 | 示例 | 优点 | 缺点 |
|------|------|------|------|
| URL 路径版本 | `/v1/products` | 直观，易测试，可书签 | URL 不纯粹 |
| 请求头版本 | `Accept: application/vnd.api+json;version=1` | URL 干净 | 不直观，难调试 |
| 查询参数版本 | `/products?version=1` | 简单 | 容易被忽略 |
| 日期版本（Stripe风格） | `Stripe-Version: 2023-10-01` | 精确到变更日期 | 维护复杂 |

**推荐：URL路径版本**，最直观，最容易被各类工具支持。

```python
# FastAPI 版本化路由示例
from fastapi import FastAPI

app_v1 = FastAPI()
app_v2 = FastAPI()

@app_v1.get("/products/{id}")
async def get_product_v1(id: int):
    return {"id": id, "name": "Widget"}  # v1: 返回name

@app_v2.get("/products/{id}")
async def get_product_v2(id: int):
    return {"id": id, "title": "Widget", "slug": "widget"}  # v2: name改为title

from fastapi import FastAPI
root_app = FastAPI()
root_app.mount("/v1", app_v1)
root_app.mount("/v2", app_v2)
```

> **架构师提示：** 版本控制的本质是**管理 Breaking Change**。尽量设计向后兼容的变更（添加字段 ≠ breaking，删除/重命名字段 = breaking）。只有在必须引入 breaking change 时才升版本号。

---

## 4. 分页、过滤与排序

大列表 API 必须支持分页。不分页的 API 在数据量增长后会拖垮服务。

### 4.1 分页方案对比

| 方案 | 示例 | 适用场景 | 局限性 |
|------|------|---------|--------|
| Offset 分页 | `?page=2&size=20` | 小数据量，需要随机跳页 | 数据插入/删除时出现重复/跳过 |
| Cursor 分页 | `?cursor=eyJpZCI6MTAwfQ&size=20` | 无限滚动，实时数据 | 不支持跳页 |
| Keyset 分页 | `?after_id=100&size=20` | 大数据量，高性能 | 不支持跳页，需要有序列 |

**Offset 分页的幽灵数据问题：**
```
# 第1页：返回 id=1,2,3,4,5
# 用户看第1页时，有人插入了 id=0
# 第2页：page=2 → OFFSET 5 → 返回 id=6,7,8,9,10
# 结果：id=5 被跳过了！
```

**Cursor 分页（推荐用于实时数据）：**
```python
# 请求
GET /products?cursor=eyJpZCI6NX0&size=20

# cursor 是 base64 编码的 JSON，里面存的是上一页最后一条记录的位置
# cursor = base64.encode(json.dumps({"id": 5, "created_at": "..."}))

# 服务端处理
def get_products(cursor: str = None, size: int = 20):
    if cursor:
        last = decode_cursor(cursor)  # 解码得到 {"id": 5}
        items = db.query(
            "SELECT * FROM products WHERE id > ? ORDER BY id LIMIT ?",
            last["id"], size + 1
        )
    else:
        items = db.query("SELECT * FROM products ORDER BY id LIMIT ?", size + 1)

    has_more = len(items) > size
    items = items[:size]
    next_cursor = encode_cursor({"id": items[-1]["id"]}) if has_more else None

    return {
        "data": items,
        "pagination": {
            "next_cursor": next_cursor,
            "has_more": has_more
        }
    }
```

### 4.2 过滤与排序

```
# 过滤：用查询参数
GET /products?category=electronics&min_price=100&max_price=500&in_stock=true

# 排序
GET /products?sort=price&order=asc
GET /products?sort=-price          # 负号表示降序（简洁风格）
GET /products?sort=price,-created_at  # 多字段排序

# 字段选择（减少数据传输）
GET /products?fields=id,name,price
```

### 4.3 标准响应结构（列表接口）

```json
{
    "data": [
        {"id": 1, "name": "Widget", "price": 29.99},
        {"id": 2, "name": "Gadget", "price": 49.99}
    ],
    "pagination": {
        "page": 1,
        "size": 20,
        "total": 150,
        "total_pages": 8
    },
    "meta": {
        "request_id": "req-abc-123",
        "took_ms": 45
    }
}
```

> **Key Architect Takeaways：**
> - Offset 分页简单但有数据漂移问题；Cursor 分页适合实时/无限滚动场景
> - 始终限制最大 page_size（如 max=100），防止客户端请求过大数据集
> - 把过滤、排序、字段选择设计进去，后期加上去代价更高

---

## 5. 请求与响应设计

### 5.1 请求体设计

```python
# 创建资源：只传"需要调用方提供的字段"，不传 id/created_at
POST /products
{
    "name": "Wireless Headphones",
    "price": 99.99,
    "category_id": 5,
    "stock": 100
}

# 响应：返回完整资源，包含服务端生成的字段
HTTP/1.1 201 Created
Location: /products/42          # 告诉调用方新资源的 URL
{
    "id": 42,
    "name": "Wireless Headphones",
    "price": 99.99,
    "category_id": 5,
    "stock": 100,
    "created_at": "2026-03-26T10:00:00Z",
    "updated_at": "2026-03-26T10:00:00Z"
}
```

### 5.2 日期时间格式

始终使用 **ISO 8601 + UTC**：

```
✅ "2026-03-26T10:00:00Z"           # UTC
✅ "2026-03-26T18:00:00+08:00"      # 带时区偏移
❌ "2026-03-26 10:00:00"            # 缺少时区，歧义
❌ 1711447200                       # Unix 时间戳（不可读）
```

### 5.3 幂等性设计

对于可能重试的操作（网络不稳定），POST 可以通过 **Idempotency Key** 实现幂等：

```python
# 客户端生成唯一键
POST /orders
Idempotency-Key: client-uuid-abc-123

# 服务端：如果相同 key 的请求已处理过，直接返回缓存的结果
def create_order(idempotency_key: str, order_data: dict):
    # 检查是否已处理过
    cached = redis.get(f"idempotency:{idempotency_key}")
    if cached:
        return json.loads(cached)

    # 处理订单
    order = process_order(order_data)

    # 缓存结果（24小时TTL）
    redis.setex(
        f"idempotency:{idempotency_key}",
        86400,
        json.dumps(order)
    )
    return order
```

---

## 6. 认证与授权

### 6.1 认证方案对比

| 方案 | 适用场景 | 优点 | 缺点 |
|------|---------|------|------|
| API Key | 服务间调用，简单场景 | 简单，无状态 | 无过期，泄露后难撤销 |
| JWT（Bearer Token） | 用户认证，微服务 | 无状态，自包含信息 | 无法主动失效，需要刷新机制 |
| OAuth 2.0 | 第三方授权 | 标准化，支持授权委托 | 复杂 |
| Session Cookie | 传统Web应用 | 可随时失效 | 需要服务端存储，不适合分布式 |

### 6.2 JWT 在 API 中的标准用法

```
# 请求头格式
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# JWT 结构（Base64 编码的三段）
{
    "alg": "HS256",    # Header
    "typ": "JWT"
}.{
    "sub": "user-123",  # Payload：主题（用户ID）
    "role": "admin",
    "exp": 1711450800,  # 过期时间（Unix timestamp）
    "iat": 1711447200   # 签发时间
}.signature
```

> **架构师提示：** JWT 的最大局限是**无法主动失效**。用户登出后，Token 在 `exp` 之前仍然有效。解决方案：短过期时间（15分钟）+ Refresh Token + Token 黑名单（用 Redis 存储已注销的 jti）。

---

## 7. 限流（Rate Limiting）

### 7.1 为什么需要限流

- 防止滥用（爬虫、DDoS）
- 保证服务质量（防止单个用户占用全部资源）
- 商业变现（付费用户更高配额）

### 7.2 限流算法对比

| 算法 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| 固定窗口（Fixed Window） | 每N秒计数，超限拒绝 | 简单 | 窗口边界突发问题 |
| 滑动窗口（Sliding Window） | 用最近N秒的请求数 | 更平滑 | 内存消耗大 |
| 令牌桶（Token Bucket） | 以固定速率生成令牌，取令牌才能请求 | 允许突发 | 实现稍复杂 |
| 漏桶（Leaky Bucket） | 请求以固定速率处理，多余的排队或丢弃 | 输出稳定 | 不允许突发 |

**固定窗口的边界问题：**
```
限制：每分钟100次
00:59 → 发100次请求（用完配额）
01:00 → 新窗口，再发100次请求
结果：2秒内发了200次请求，突破了"每分钟100次"的初衷
```

**令牌桶（推荐，Redis 实现）：**
```python
import redis
import time

def is_allowed(user_id: str, capacity: int = 100, refill_rate: float = 1.0) -> bool:
    """
    令牌桶限流
    capacity: 桶容量（最大突发量）
    refill_rate: 每秒补充令牌数
    """
    r = redis.Redis()
    key = f"rate_limit:{user_id}"
    now = time.time()

    pipe = r.pipeline()
    # 获取当前令牌数和上次更新时间
    pipe.hmget(key, "tokens", "last_refill")
    tokens_data = pipe.execute()[0]

    current_tokens = float(tokens_data[0] or capacity)
    last_refill = float(tokens_data[1] or now)

    # 计算新增令牌
    elapsed = now - last_refill
    new_tokens = min(capacity, current_tokens + elapsed * refill_rate)

    if new_tokens >= 1:
        # 有令牌，允许请求
        pipe.hset(key, mapping={"tokens": new_tokens - 1, "last_refill": now})
        pipe.expire(key, 3600)
        pipe.execute()
        return True
    else:
        return False
```

### 7.3 响应头规范

```
HTTP/1.1 200 OK
X-RateLimit-Limit: 100         # 配额总量
X-RateLimit-Remaining: 75      # 剩余配额
X-RateLimit-Reset: 1711450800  # 配额重置时间（Unix timestamp）

# 触发限流时
HTTP/1.1 429 Too Many Requests
Retry-After: 30                 # 多少秒后可以重试
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
```

> **Key Architect Takeaways：**
> - 限流应在 API Gateway 层统一实现，不要每个服务自己实现
> - 向调用方暴露限流相关响应头，让他们能感知自己的配额状态
> - 令牌桶适合允许短时突发的场景；漏桶适合需要稳定输出速率的场景

---

## 8. API 文档：OpenAPI（Swagger）规范

### 8.1 为什么 OpenAPI 重要

OpenAPI 规范（原 Swagger）让 API 文档、代码生成、测试都能从同一份契约文件派生，是"文档即代码"的最佳实践。

```yaml
# openapi.yaml 示例（精简版）
openapi: "3.0.3"
info:
  title: ShopFlow API
  version: "1.0.0"
  description: 电商平台 API

paths:
  /products:
    get:
      summary: 获取商品列表
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: size
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        "200":
          description: 成功
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/ProductList"
    post:
      summary: 创建商品
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CreateProductRequest"
      responses:
        "201":
          description: 创建成功
        "400":
          $ref: "#/components/responses/BadRequest"
        "401":
          $ref: "#/components/responses/Unauthorized"

components:
  schemas:
    Product:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        price:
          type: number
          format: float
        created_at:
          type: string
          format: date-time
      required: [id, name, price]

    CreateProductRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 200
        price:
          type: number
          minimum: 0
      required: [name, price]
```

### 8.2 FastAPI 自动生成 OpenAPI

FastAPI 的一大优势是从代码类型注解自动生成 OpenAPI 文档：

```python
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

app = FastAPI(title="ShopFlow API", version="1.0.0")

class Product(BaseModel):
    id: int
    name: str
    price: float
    created_at: datetime

class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="商品名称")
    price: float = Field(..., gt=0, description="商品价格，必须大于0")
    stock: int = Field(default=0, ge=0, description="库存数量")

@app.get(
    "/products",
    response_model=List[Product],
    summary="获取商品列表",
    tags=["products"]
)
async def list_products(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    category_id: Optional[int] = None
):
    """获取商品列表，支持分页和按分类过滤。"""
    ...

# 访问 /docs 查看 Swagger UI
# 访问 /redoc 查看 ReDoc 格式文档
# 访问 /openapi.json 获取原始 OpenAPI Schema
```

---

## 9. API 设计最佳实践

### 9.1 向后兼容性原则

API 的演进策略：能不升版本就不升版本。

| 变更类型 | 是否 Breaking | 处理方式 |
|---------|-------------|---------|
| 添加新字段（响应） | 否 | 直接添加，调用方忽略未知字段 |
| 添加新端点 | 否 | 直接添加 |
| 添加新可选参数 | 否 | 直接添加，给默认值 |
| 删除字段 | **是** | 先标记 deprecated，保留至少一个版本周期 |
| 重命名字段 | **是** | 先同时支持新旧名称，再删除旧名称 |
| 修改字段类型 | **是** | 需要升版本 |
| 修改 URL 结构 | **是** | 先301重定向，再废弃旧URL |

### 9.2 HATEOAS（超媒体约束）

HATEOAS（Hypermedia as the Engine of Application State）是 REST 成熟度模型的最高级别，让 API 返回下一步可执行的操作链接：

```json
{
    "id": 42,
    "status": "pending",
    "_links": {
        "self": {"href": "/orders/42"},
        "pay": {"href": "/orders/42/payment", "method": "POST"},
        "cancel": {"href": "/orders/42/cancel", "method": "POST"}
    }
}
```

> **架构师提示：** HATEOAS 在理论上很优雅，但实践中很少完整实现。大多数团队止步于 Richardson Maturity Level 2（正确使用 HTTP 方法和状态码），这已经足够了。

### 9.3 API 设计反模式

| 反模式 | 问题 | 正确做法 |
|--------|------|---------|
| 用 GET 做写操作 | 违反 HTTP 语义，可能被缓存 | 用 POST/PUT/PATCH |
| 把敏感信息放 URL | URL 会被记录在日志/代理/浏览器历史 | 敏感信息放请求头或请求体 |
| 返回裸数组 | `[...]` 无法在不破坏兼容性的情况下添加分页信息 | 总是返回对象 `{"data": [...], "pagination": {...}}` |
| 忽略状态码 | 调用方必须解析 body 才能判断成功/失败 | 正确使用 4xx/5xx |
| 无版本策略 | 第一个 breaking change 就破坏所有调用方 | 从第一天就设计版本策略 |
| 过于细粒度的端点 | N+1 请求问题（拿列表 + 逐个拿详情） | 设计复合端点或支持字段包含（include=） |

---

## 10. ADR 模板：REST vs GraphQL 决策记录

```markdown
# ADR-001: 选择 REST 作为 ShopFlow API 风格

**状态：** 已批准
**日期：** 2026-03-26

## 背景

ShopFlow 需要为 Web 前端和移动端暴露 API。前端需求相对固定，
主要是商品浏览、购物车操作和订单管理。

## 决策

选择 REST over GraphQL。

## 理由

1. 团队成员对 REST 熟悉，GraphQL 需要学习成本
2. 前端数据需求不复杂，over-fetching 问题不严重
3. REST 的 HTTP 缓存支持更好（GET 可以被 CDN 缓存）
4. 工具链更成熟（Postman、curl 等都天然支持）

## 后果

- 后期如果移动端需要精确字段控制，可能需要在特定端点支持 GraphQL
- 需要设计好的分页和过滤机制来补偿无法精确指定字段的问题
```

---

## Key Architect Takeaways

- **先选风格，再设计细节**：REST 适合大多数场景；gRPC 用于服务间高性能通信；GraphQL 只在 over-fetching 真正成为问题时才引入
- **URL 是资源，方法是动词**：`GET /products/42` 比 `GET /getProduct?id=42` 更直觉、更可缓存
- **状态码是协议**：正确使用 4xx/5xx 让调用方不用解析 body 就能做出决策
- **分页不是可选项**：没有分页的列表接口是定时炸弹，数据量一大就崩溃
- **版本控制从第一天开始**：不是等到需要 breaking change 才想这个问题，那时候已经晚了
- **文档是契约**：OpenAPI 规范让文档、测试、代码生成都从同一个源头派生，是团队协作的基础
