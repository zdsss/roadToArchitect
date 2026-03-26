# 分层架构（Layered Architecture）

分层架构是最广泛使用的架构模式。它通过将职责分配到不同层次，使系统各部分可以独立理解、测试和替换。理解分层架构是掌握更复杂架构（六边形、微服务）的基础。

---

## 1. 为什么需要分层

### 1.1 没有分层时会发生什么

```python
# 反模式：一个路由函数做所有事情
@app.post("/orders")
async def create_order(request: Request):
    body = await request.json()

    # 直接操作数据库（没有抽象）
    conn = psycopg2.connect("postgresql://...")
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM products WHERE id = %s", (body["product_id"],))
    product = cursor.fetchone()

    # 业务逻辑混在路由里
    if product is None:
        return {"error": "Product not found"}, 404
    total = product[0] * body["quantity"]
    if total > 10000:
        total = total * 0.9  # 超过1万打九折

    # 直接发邮件
    smtp = smtplib.SMTP("mail.example.com")
    smtp.sendmail("no-reply@shop.com", body["email"], f"订单总额: {total}")

    cursor.execute(
        "INSERT INTO orders (product_id, quantity, total) VALUES (%s, %s, %s)",
        (body["product_id"], body["quantity"], total)
    )
    conn.commit()
    return {"total": total}
```

**问题：**
- 无法单独测试折扣逻辑（必须连数据库和邮件服务）
- 换数据库（从 PostgreSQL 换成 MySQL）需要改路由代码
- 折扣规则变了，要在所有"类似"的路由里找并改
- 代码无法复用（另一个路由需要相同的折扣逻辑，只能复制粘贴）

### 1.2 分层带来的价值

| 问题 | 分层的解决方式 |
|------|-------------|
| 难以测试 | 每层可以独立测试，可以 mock 下层 |
| 难以变更 | 接口不变，可以替换实现（换数据库不影响业务逻辑） |
| 难以复用 | 业务逻辑在 Service 层，多个 Controller 可以调用同一个 Service |
| 难以理解 | 每层职责明确，读代码时知道去哪里找什么 |

---

## 2. 四层经典模型

```
┌─────────────────────────────────────────┐
│          Presentation Layer             │  ← Controller / API Routes
│   处理 HTTP 请求/响应，参数验证，序列化     │
├─────────────────────────────────────────┤
│          Business Logic Layer           │  ← Service
│   业务规则，用例编排，事务管理             │
├─────────────────────────────────────────┤
│          Data Access Layer              │  ← Repository
│   数据持久化抽象，SQL 查询，ORM 映射       │
├─────────────────────────────────────────┤
│          Database / Infrastructure      │  ← PostgreSQL, Redis, 第三方API
│   实际的存储和外部服务                    │
└─────────────────────────────────────────┘
```

### 2.1 依赖方向：只能向下

**关键原则：上层可以调用下层，下层不能调用上层。**

```
Controller → Service → Repository → Database
```

Controller 知道 Service 的存在，Service 不知道 Controller 的存在。
Service 知道 Repository 的存在，Repository 不知道 Service 的存在。

违反这个规则会导致循环依赖和测试困难。

---

## 3. 各层职责详解

### 3.1 Presentation Layer（表示层）

**职责：**
- 接收并解析 HTTP 请求
- 输入验证（格式、类型、必填项）
- 调用 Service 层处理业务
- 把结果序列化为 HTTP 响应
- 处理认证（从 JWT 中提取用户信息）

**不应该做：**
- 包含业务规则（折扣计算、库存扣减逻辑）
- 直接操作数据库
- 处理复杂的数据转换

```python
# shop/api/product_router.py — 表示层
from fastapi import APIRouter, HTTPException, Depends, Query
from shop.service.product_service import ProductService
from shop.schemas.product import CreateProductRequest, ProductResponse
from shop.auth import get_current_user

router = APIRouter(prefix="/products", tags=["products"])

@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    request: CreateProductRequest,  # Pydantic 自动验证
    service: ProductService = Depends(),
    current_user = Depends(get_current_user)
):
    # 只做授权检查，不做业务逻辑
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create products")

    # 委托给 Service 层
    product = await service.create_product(request.name, request.price, request.stock)
    return ProductResponse.from_domain(product)

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int, service: ProductService = Depends()):
    product = await service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.from_domain(product)
```

### 3.2 Business Logic Layer（业务逻辑层）

**职责：**
- 业务规则和决策（打折、库存检查、订单状态流转）
- 用例编排（创建订单 = 检查库存 + 创建订单记录 + 发通知）
- 事务边界（跨多个 Repository 操作的原子性）
- 领域对象操作

**不应该做：**
- 了解 HTTP 协议（不依赖 request/response 对象）
- 直接执行 SQL（不了解 ORM 细节）
- 格式化展示数据（那是表示层的事）

```python
# shop/service/product_service.py — 业务逻辑层
from shop.repository.product_repo import ProductRepository
from shop.domain.product import Product

class ProductService:
    def __init__(self, repo: ProductRepository):
        self.repo = repo  # 依赖注入，不自己创建

    async def create_product(self, name: str, price: float, stock: int) -> Product:
        # 业务规则：价格不能为负
        if price < 0:
            raise ValueError("Price cannot be negative")

        # 业务规则：商品名不能重复
        existing = await self.repo.find_by_name(name)
        if existing:
            raise ValueError(f"Product '{name}' already exists")

        product = Product(name=name, price=price, stock=stock)
        return await self.repo.save(product)

    async def apply_discount(self, product_id: int, discount_pct: float) -> Product:
        # 业务规则：折扣不能超过 50%
        if discount_pct > 0.5:
            raise ValueError("Discount cannot exceed 50%")

        product = await self.repo.find_by_id(product_id)
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        product.price = product.price * (1 - discount_pct)
        return await self.repo.save(product)

    async def get_product(self, product_id: int) -> Product | None:
        return await self.repo.find_by_id(product_id)
```

### 3.3 Data Access Layer（数据访问层）

**职责：**
- 抽象数据持久化（调用方不知道是 PostgreSQL 还是 MongoDB）
- SQL 查询、ORM 映射
- 数据库连接管理
- 查询优化（索引使用、分页）

**Repository 模式的核心价值：** 调用方（Service）只知道"获取/保存 Product"，不知道底层是什么数据库，也不知道用了什么 SQL。

```python
# shop/repository/product_repo.py — 数据访问层
from abc import ABC, abstractmethod
from shop.domain.product import Product

# 接口定义（抽象基类）
class ProductRepository(ABC):
    @abstractmethod
    async def find_by_id(self, product_id: int) -> Product | None:
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Product | None:
        pass

    @abstractmethod
    async def save(self, product: Product) -> Product:
        pass

    @abstractmethod
    async def find_all(self, page: int = 1, size: int = 20) -> list[Product]:
        pass


# PostgreSQL 实现
class PostgreSQLProductRepository(ProductRepository):
    def __init__(self, db_connection):
        self.db = db_connection

    async def find_by_id(self, product_id: int) -> Product | None:
        row = await self.db.fetchrow(
            "SELECT id, name, price, stock, created_at FROM products WHERE id = $1",
            product_id
        )
        return Product.from_row(row) if row else None

    async def find_by_name(self, name: str) -> Product | None:
        row = await self.db.fetchrow(
            "SELECT id, name, price, stock, created_at FROM products WHERE name = $1",
            name
        )
        return Product.from_row(row) if row else None

    async def save(self, product: Product) -> Product:
        if product.id is None:
            # 创建
            row = await self.db.fetchrow(
                """INSERT INTO products (name, price, stock)
                   VALUES ($1, $2, $3)
                   RETURNING id, name, price, stock, created_at""",
                product.name, product.price, product.stock
            )
        else:
            # 更新
            row = await self.db.fetchrow(
                """UPDATE products SET name=$1, price=$2, stock=$3
                   WHERE id=$4
                   RETURNING id, name, price, stock, created_at""",
                product.name, product.price, product.stock, product.id
            )
        return Product.from_row(row)

    async def find_all(self, page: int = 1, size: int = 20) -> list[Product]:
        offset = (page - 1) * size
        rows = await self.db.fetch(
            "SELECT id, name, price, stock, created_at FROM products ORDER BY id LIMIT $1 OFFSET $2",
            size, offset
        )
        return [Product.from_row(row) for row in rows]


# 内存实现（用于测试）
class InMemoryProductRepository(ProductRepository):
    def __init__(self):
        self._store: dict[int, Product] = {}
        self._next_id = 1

    async def find_by_id(self, product_id: int) -> Product | None:
        return self._store.get(product_id)

    async def find_by_name(self, name: str) -> Product | None:
        return next((p for p in self._store.values() if p.name == name), None)

    async def save(self, product: Product) -> Product:
        if product.id is None:
            product.id = self._next_id
            self._next_id += 1
        self._store[product.id] = product
        return product

    async def find_all(self, page: int = 1, size: int = 20) -> list[Product]:
        items = list(self._store.values())
        start = (page - 1) * size
        return items[start:start + size]
```

---

## 4. 依赖注入（Dependency Injection）

分层架构中，依赖注入是连接各层的机制。Service 不自己创建 Repository，而是通过构造函数接收。

### 4.1 为什么用依赖注入

```python
# 反模式：硬编码依赖
class ProductService:
    def __init__(self):
        # 直接创建，测试时无法替换
        self.repo = PostgreSQLProductRepository(get_db_connection())

# 好的做法：注入依赖
class ProductService:
    def __init__(self, repo: ProductRepository):  # 接受接口，不绑定实现
        self.repo = repo

# 测试时注入内存实现
service = ProductService(repo=InMemoryProductRepository())

# 生产时注入真实实现
service = ProductService(repo=PostgreSQLProductRepository(db))
```

### 4.2 FastAPI 的依赖注入

```python
# shop/dependencies.py
from fastapi import Depends
import asyncpg

async def get_db():
    conn = await asyncpg.connect("postgresql://user:pass@localhost/shopflow")
    try:
        yield conn
    finally:
        await conn.close()

def get_product_repo(db=Depends(get_db)) -> ProductRepository:
    return PostgreSQLProductRepository(db)

def get_product_service(repo=Depends(get_product_repo)) -> ProductService:
    return ProductService(repo)

# 在路由中使用
@router.post("/products/")
async def create_product(
    request: CreateProductRequest,
    service: ProductService = Depends(get_product_service)
):
    ...
```

---

## 5. 领域模型：贫血 vs 富血

### 5.1 贫血领域模型（Anemic Domain Model）

只有数据，没有行为。业务逻辑全在 Service 层。

```python
# 贫血模型：只是数据容器
class Order:
    def __init__(self):
        self.id = None
        self.status = "pending"
        self.items = []
        self.total = 0.0

# Service 里包含所有逻辑
class OrderService:
    def pay_order(self, order: Order):
        if order.status != "pending":
            raise ValueError("Can only pay pending orders")
        order.status = "paid"
        # ... 其他逻辑
```

### 5.2 富血领域模型（Rich Domain Model）

业务规则封装在领域对象内部。

```python
# 富血模型：数据 + 行为
class Order:
    def __init__(self, id: int = None):
        self.id = id
        self._status = "pending"
        self._items: list[OrderItem] = []

    @property
    def status(self):
        return self._status

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self._items)

    def pay(self):
        # 业务规则内聚在领域对象里
        if self._status != "pending":
            raise ValueError(f"Cannot pay order in '{self._status}' status")
        self._status = "paid"

    def cancel(self):
        if self._status in ("shipped", "delivered"):
            raise ValueError("Cannot cancel shipped or delivered orders")
        self._status = "cancelled"

    def add_item(self, product_id: int, quantity: int, price: float):
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self._items.append(OrderItem(product_id, quantity, price))
```

### 5.3 如何选择

| 场景 | 推荐 |
|------|------|
| CRUD 为主，业务规则简单 | 贫血模型（更简单，直接） |
| 复杂业务规则，多状态流转 | 富血模型（业务规则内聚，易测试） |
| 初学阶段 | 从贫血模型开始，理解分层后再尝试富血 |

> **架构师提示：** Martin Fowler 称贫血模型为"反模式"，但在实践中，大多数企业应用都是贫血模型，原因是更简单直观。不要教条式地追求富血模型——先让代码工作，再考虑是否需要更丰富的领域模型。

---

## 6. 跨层关注点（Cross-Cutting Concerns）

某些逻辑横跨多层，不属于任何一层，如日志、事务、认证。

### 6.1 事务管理

事务通常在 Service 层管理（因为一个用例可能跨多个 Repository 操作）：

```python
# shop/service/order_service.py
class OrderService:
    def __init__(self, order_repo: OrderRepository, product_repo: ProductRepository, db):
        self.order_repo = order_repo
        self.product_repo = product_repo
        self.db = db

    async def create_order(self, user_id: int, items: list[dict]) -> Order:
        async with self.db.transaction():  # 事务开始
            # 操作1：检查并扣减库存
            for item in items:
                product = await self.product_repo.find_by_id(item["product_id"])
                if product.stock < item["quantity"]:
                    raise ValueError(f"Insufficient stock for product {item['product_id']}")
                product.stock -= item["quantity"]
                await self.product_repo.save(product)

            # 操作2：创建订单
            order = Order(user_id=user_id)
            for item in items:
                order.add_item(item["product_id"], item["quantity"], item["price"])
            saved_order = await self.order_repo.save(order)

            return saved_order
        # 任何异常都会导致事务回滚
```

### 6.2 日志

使用 AOP（面向切面编程）思路，避免在每个方法里写日志：

```python
import logging
import functools
import time

def log_execution(func):
    """装饰器：记录函数执行时间和参数"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start = time.time()
        logger.info(f"Starting {func.__name__}", extra={"args": str(args[1:])})  # 跳过self
        try:
            result = await func(*args, **kwargs)
            elapsed = (time.time() - start) * 1000
            logger.info(f"Completed {func.__name__}", extra={"duration_ms": elapsed})
            return result
        except Exception as e:
            logger.error(f"Failed {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper

class ProductService:
    @log_execution
    async def create_product(self, name: str, price: float, stock: int) -> Product:
        ...
```

---

## 7. 分层架构的局限性

分层架构在大多数情况下都够用，但有其固有的局限：

| 问题 | 描述 | 解决方向 |
|------|------|---------|
| 层间穿透 | 简单的 CRUD 请求需要穿越所有层，过于繁琐 | 允许简单查询跳过 Service 层直接查 DB |
| 领域模型贫血 | 业务规则散落在 Service 层 | 引入富血领域模型或六边形架构 |
| 上层绑定框架 | Service 层如果用了 FastAPI 的 `Depends`，就绑定了 FastAPI | 通过 DI 容器解耦 |
| 单体瓶颈 | 所有层在同一进程，无法独立扩展 | 微服务（但别过早拆分） |
| 下层不知道上层 | Repository 无法感知调用上下文 | 通过上下文对象（如 trace_id）传递 |

> **架构师提示：** 分层架构最大的问题不是技术，而是**纪律**。很容易偷懒在 Controller 里写业务逻辑，或者在 Service 里写 SQL。这些"小捷径"积累起来，就会让分层失去意义。代码审查中最重要的一条规则：**Controller 里没有 if，Repository 里没有业务规则。**

---

## 8. 项目结构参考（ShopFlow Python）

```
shop/
├── api/                    # 表示层（Presentation）
│   ├── __init__.py
│   ├── product_router.py
│   ├── order_router.py
│   └── auth_router.py
│
├── service/                # 业务逻辑层（Business Logic）
│   ├── __init__.py
│   ├── product_service.py
│   └── order_service.py
│
├── repository/             # 数据访问层（Data Access）
│   ├── __init__.py
│   ├── product_repo.py     # 接口定义
│   └── pg_product_repo.py  # PostgreSQL 实现
│
├── domain/                 # 领域对象（跨层共享的数据模型）
│   ├── __init__.py
│   ├── product.py
│   └── order.py
│
├── schemas/                # 请求/响应 Schema（Pydantic 模型）
│   ├── product.py
│   └── order.py
│
├── dependencies.py         # FastAPI 依赖注入配置
└── main.py                 # 应用入口
```

---

## Key Architect Takeaways

- **分层的本质是关注点分离**：Controller 管"怎么接收请求"，Service 管"做什么业务"，Repository 管"怎么存数据"——三者互不干涉
- **依赖方向只能向下**：这是分层架构的铁律，违反它就会出现循环依赖和测试困难
- **Repository 接口是关键**：定义接口而非实现，让 Service 对数据库无感，测试时用内存实现替换
- **事务在 Service 层管理**：因为一个业务用例可能跨多个 Repository 操作，只有 Service 知道完整的事务边界
- **分层需要纪律**：Architecture is easy, discipline is hard——架构图画起来很容易，难的是团队每个人都遵守约定
