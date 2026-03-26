# 六边形架构（Hexagonal Architecture）

六边形架构，又称"端口与适配器架构"（Ports and Adapters），由 Alistair Cockburn 于2005年提出。它的核心思想是：**领域（业务逻辑）不依赖任何技术框架或基础设施，框架和基础设施依赖领域**。

这与分层架构的本质区别在于：分层架构中，依赖是单向向下的，但领域层仍然"感知"数据库的存在（通过 Repository 接口）。六边形架构将这种感知彻底切断——领域层不知道任何外部世界的存在。

---

## 1. 核心思想：反转依赖

### 1.1 分层架构的隐性问题

```python
# 分层架构中的 Service 层
from shop.repository.product_repo import ProductRepository  # 依赖 Repository 接口

class ProductService:
    def __init__(self, repo: ProductRepository):
        self.repo = repo
    # Service 知道"有个东西叫 Repository"，即使是接口
```

问题：如果要把 ProductService 移植到另一个项目，还得带着 ProductRepository 的接口。领域逻辑和数据访问层仍然隐性耦合。

### 1.2 六边形架构的解法

```
           外部世界
    ┌──────────────────────────┐
    │  HTTP API  │  CLI  │ ... │  ← 驱动适配器（Driving Adapters）
    └────────────┬─────────────┘
                 │ 实现 Port（接口）
    ┌────────────▼─────────────┐
    │                          │
    │      领域（Hexagon）      │  ← 纯业务逻辑，不 import 任何框架
    │                          │
    └────────────┬─────────────┘
                 │ 定义 Port（接口），由适配器实现
    ┌────────────▼─────────────┐
    │  PostgreSQL │ Redis │ ... │  ← 被驱动适配器（Driven Adapters）
    └──────────────────────────┘
```

**关键反转：** 领域层定义接口（Port），基础设施层实现接口（Adapter）。领域不知道数据库的存在，数据库适配器知道领域的存在。

---

## 2. 核心概念：Port 和 Adapter

### 2.1 Port（端口）——接口定义

Port 是领域层对外部世界的抽象，用接口（抽象类）表达。

```python
# shop/domain/ports/product_repository_port.py
# 这是领域层定义的接口——领域说"我需要一个能存取商品的东西"
# 但领域不关心是 PostgreSQL、MongoDB 还是内存字典

from abc import ABC, abstractmethod
from shop.domain.model.product import Product

class ProductRepositoryPort(ABC):
    """商品持久化端口——领域定义，基础设施实现"""

    @abstractmethod
    def find_by_id(self, product_id: int) -> Product | None:
        pass

    @abstractmethod
    def save(self, product: Product) -> Product:
        pass

    @abstractmethod
    def find_all(self, page: int = 1, size: int = 20) -> list[Product]:
        pass


# shop/domain/ports/notification_port.py
class NotificationPort(ABC):
    """通知端口——领域说"我需要发通知"，但不关心是邮件、短信还是 Slack"""

    @abstractmethod
    def send_order_confirmation(self, user_email: str, order_id: int, total: float) -> None:
        pass
```

### 2.2 Adapter（适配器）——接口实现

```
适配器类型：
- 驱动适配器（Primary/Driving）：外部调用领域。例如：HTTP Controller、CLI、定时任务
- 被驱动适配器（Secondary/Driven）：领域调用外部。例如：数据库、邮件服务、消息队列
```

```python
# shop/adapters/driven/postgresql_product_repository.py
# 被驱动适配器：实现领域定义的端口
import asyncpg
from shop.domain.ports.product_repository_port import ProductRepositoryPort
from shop.domain.model.product import Product

class PostgreSQLProductRepository(ProductRepositoryPort):
    """PostgreSQL 适配器——实现 ProductRepositoryPort"""

    def __init__(self, connection: asyncpg.Connection):
        self._conn = connection

    def find_by_id(self, product_id: int) -> Product | None:
        row = self._conn.fetchrow(
            "SELECT id, name, price, stock FROM products WHERE id = $1",
            product_id
        )
        return Product(id=row['id'], name=row['name'], price=row['price'], stock=row['stock']) if row else None

    def save(self, product: Product) -> Product:
        if product.id is None:
            row = self._conn.fetchrow(
                "INSERT INTO products (name, price, stock) VALUES ($1, $2, $3) RETURNING *",
                product.name, product.price, product.stock
            )
            return Product(id=row['id'], name=row['name'], price=row['price'], stock=row['stock'])
        else:
            self._conn.execute(
                "UPDATE products SET name=$1, price=$2, stock=$3 WHERE id=$4",
                product.name, product.price, product.stock, product.id
            )
            return product

    def find_all(self, page: int = 1, size: int = 20) -> list[Product]:
        offset = (page - 1) * size
        rows = self._conn.fetch(
            "SELECT id, name, price, stock FROM products ORDER BY id LIMIT $1 OFFSET $2",
            size, offset
        )
        return [Product(**row) for row in rows]


# shop/adapters/driven/smtp_notification_adapter.py
import smtplib
from shop.domain.ports.notification_port import NotificationPort

class SmtpNotificationAdapter(NotificationPort):
    def send_order_confirmation(self, user_email: str, order_id: int, total: float) -> None:
        # SMTP 细节在这里，领域不知道
        with smtplib.SMTP('mail.example.com') as smtp:
            smtp.sendmail(
                'no-reply@shopflow.com',
                user_email,
                f"Subject: Order {order_id} confirmed\n\nTotal: {total}"
            )


# shop/adapters/driving/fastapi_product_router.py
# 驱动适配器：把 HTTP 请求转换为领域用例调用
from fastapi import APIRouter, Depends
from shop.domain.use_cases.product_use_cases import ProductUseCases

router = APIRouter(prefix="/products")

@router.post("/", status_code=201)
def create_product(request: CreateProductRequest, use_cases: ProductUseCases = Depends()):
    # 驱动适配器的职责：把 HTTP 请求转换为领域用例调用
    product = use_cases.create_product(request.name, request.price, request.stock)
    return ProductResponse.from_domain(product)
```

---

## 3. 领域层：纯净无依赖

领域层是六边形架构的核心。它包含：
- **领域模型（Domain Model）**：业务实体，富含行为
- **用例（Use Cases / Application Services）**：业务流程编排
- **端口（Ports）**：领域定义的接口

**关键约束：领域层的 `import` 里绝对不能出现框架或数据库库的名字。**

```python
# shop/domain/model/product.py
# 纯 Python，没有任何 import fastapi / sqlalchemy / pika

from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Product:
    name: str
    price: float
    stock: int
    id: Optional[int] = None

    def __post_init__(self):
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.stock < 0:
            raise ValueError("Stock cannot be negative")

    def apply_discount(self, discount_pct: float) -> None:
        if not 0 < discount_pct <= 0.5:
            raise ValueError("Discount must be between 0% and 50%")
        self.price = round(self.price * (1 - discount_pct), 2)

    def reserve_stock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.stock < quantity:
            raise ValueError(f"Insufficient stock: have {self.stock}, need {quantity}")
        self.stock -= quantity


# shop/domain/model/order.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

class OrderStatus(Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

@dataclass
class OrderItem:
    product_id: int
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price

@dataclass
class Order:
    user_id: int
    id: Optional[int] = None
    _status: OrderStatus = field(default=OrderStatus.PENDING, init=False)
    _items: list[OrderItem] = field(default_factory=list, init=False)

    @property
    def status(self) -> OrderStatus:
        return self._status

    @property
    def total(self) -> float:
        return sum(item.subtotal for item in self._items)

    def add_item(self, product_id: int, quantity: int, unit_price: float) -> None:
        self._items.append(OrderItem(product_id, quantity, unit_price))

    def pay(self) -> None:
        if self._status != OrderStatus.PENDING:
            raise ValueError(f"Cannot pay order in {self._status.value} status")
        self._status = OrderStatus.PAID

    def cancel(self) -> None:
        if self._status in (OrderStatus.SHIPPED, OrderStatus.DELIVERED):
            raise ValueError("Cannot cancel shipped or delivered order")
        self._status = OrderStatus.CANCELLED
```

### 3.1 用例层（Use Cases）

```python
# shop/domain/use_cases/order_use_cases.py
# 完全没有框架依赖，只依赖领域模型和端口接口

from shop.domain.model.order import Order
from shop.domain.model.product import Product
from shop.domain.ports.order_repository_port import OrderRepositoryPort
from shop.domain.ports.product_repository_port import ProductRepositoryPort
from shop.domain.ports.notification_port import NotificationPort

class OrderUseCases:
    """订单相关用例——业务流程的编排者"""

    def __init__(
        self,
        order_repo: OrderRepositoryPort,      # 注入端口，不是具体实现
        product_repo: ProductRepositoryPort,
        notification: NotificationPort
    ):
        self._order_repo = order_repo
        self._product_repo = product_repo
        self._notification = notification

    def place_order(self, user_id: int, user_email: str, items: list[dict]) -> Order:
        """下单用例：检查库存 → 创建订单 → 扣减库存 → 发通知"""
        order = Order(user_id=user_id)

        for item_data in items:
            product = self._product_repo.find_by_id(item_data["product_id"])
            if product is None:
                raise ValueError(f"Product {item_data['product_id']} not found")

            # 领域方法包含业务规则（库存不足会抛异常）
            product.reserve_stock(item_data["quantity"])
            self._product_repo.save(product)

            order.add_item(
                product_id=product.id,
                quantity=item_data["quantity"],
                unit_price=product.price
            )

        saved_order = self._order_repo.save(order)

        # 通过端口发通知——不知道底层是邮件还是短信
        self._notification.send_order_confirmation(
            user_email=user_email,
            order_id=saved_order.id,
            total=saved_order.total
        )

        return saved_order
```

---

## 4. 六边形架构的最大收益：可测试性

这是六边形架构的杀手级特性。因为领域层不依赖任何框架，可以在**不启动数据库、不启动 HTTP 服务器**的情况下测试完整的业务逻辑。

```python
# tests/domain/test_order_use_cases.py
# pytest + 纯内存实现，无需任何基础设施

import pytest
from shop.domain.use_cases.order_use_cases import OrderUseCases
from shop.domain.model.product import Product
from shop.domain.model.order import OrderStatus

# 内存实现（测试用）
class InMemoryOrderRepository:
    def __init__(self):
        self._store = {}
        self._next_id = 1

    def save(self, order):
        order.id = self._next_id
        self._next_id += 1
        self._store[order.id] = order
        return order

    def find_by_id(self, order_id):
        return self._store.get(order_id)


class InMemoryProductRepository:
    def __init__(self, products):
        self._store = {p.id: p for p in products}

    def find_by_id(self, product_id):
        return self._store.get(product_id)

    def save(self, product):
        self._store[product.id] = product
        return product


class FakeNotificationAdapter:
    def __init__(self):
        self.sent_notifications = []

    def send_order_confirmation(self, user_email, order_id, total):
        self.sent_notifications.append({
            "email": user_email,
            "order_id": order_id,
            "total": total
        })


class TestOrderUseCases:
    def setup_method(self):
        # 准备测试数据
        self.products = [
            Product(id=1, name="Widget", price=10.0, stock=100),
            Product(id=2, name="Gadget", price=25.0, stock=5),
        ]
        self.order_repo = InMemoryOrderRepository()
        self.product_repo = InMemoryProductRepository(self.products)
        self.notification = FakeNotificationAdapter()

        self.use_cases = OrderUseCases(
            order_repo=self.order_repo,
            product_repo=self.product_repo,
            notification=self.notification
        )

    def test_place_order_success(self):
        order = self.use_cases.place_order(
            user_id=1,
            user_email="user@example.com",
            items=[{"product_id": 1, "quantity": 3}]
        )

        assert order.id is not None
        assert order.total == 30.0  # 10.0 * 3
        assert order.status == OrderStatus.PENDING

        # 验证库存被扣减
        product = self.product_repo.find_by_id(1)
        assert product.stock == 97  # 100 - 3

        # 验证通知被发出
        assert len(self.notification.sent_notifications) == 1
        assert self.notification.sent_notifications[0]["email"] == "user@example.com"

    def test_place_order_insufficient_stock(self):
        with pytest.raises(ValueError, match="Insufficient stock"):
            self.use_cases.place_order(
                user_id=1,
                user_email="user@example.com",
                items=[{"product_id": 2, "quantity": 10}]  # 库存只有5
            )

    def test_place_order_product_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            self.use_cases.place_order(
                user_id=1,
                user_email="user@example.com",
                items=[{"product_id": 999, "quantity": 1}]  # 不存在的商品
            )

# 运行测试：pytest tests/domain/ -v
# 不需要数据库！不需要 FastAPI！不需要邮件服务！
# 测试速度：毫秒级
```

---

## 5. 项目目录结构

```
shop/
├── domain/                         # 领域层（纯 Python，无框架依赖）
│   ├── model/                      # 领域模型
│   │   ├── product.py
│   │   ├── order.py
│   │   └── user.py
│   ├── ports/                      # 端口定义（接口）
│   │   ├── product_repository_port.py
│   │   ├── order_repository_port.py
│   │   └── notification_port.py
│   └── use_cases/                  # 用例（业务流程）
│       ├── product_use_cases.py
│       └── order_use_cases.py
│
├── adapters/
│   ├── driving/                    # 驱动适配器（外部 → 领域）
│   │   ├── fastapi_product_router.py
│   │   ├── fastapi_order_router.py
│   │   └── cli_adapter.py
│   └── driven/                     # 被驱动适配器（领域 → 外部）
│       ├── postgresql_product_repository.py
│       ├── postgresql_order_repository.py
│       ├── redis_cache_adapter.py
│       └── smtp_notification_adapter.py
│
├── config/                         # 依赖注入配置
│   └── container.py
│
└── main.py

tests/
├── domain/                         # 领域层单元测试（无基础设施）
│   ├── test_order_use_cases.py
│   └── test_product_model.py
└── integration/                    # 集成测试（有数据库）
    └── test_postgresql_repository.py
```

---

## 6. 依赖注入配置

```python
# shop/config/container.py
import asyncpg
from shop.domain.use_cases.order_use_cases import OrderUseCases
from shop.adapters.driven.postgresql_product_repository import PostgreSQLProductRepository
from shop.adapters.driven.postgresql_order_repository import PostgreSQLOrderRepository
from shop.adapters.driven.smtp_notification_adapter import SmtpNotificationAdapter
from fastapi import Depends

async def get_db_connection():
    conn = await asyncpg.connect("postgresql://...")
    try:
        yield conn
    finally:
        await conn.close()

def get_order_use_cases(conn=Depends(get_db_connection)) -> OrderUseCases:
    return OrderUseCases(
        order_repo=PostgreSQLOrderRepository(conn),
        product_repo=PostgreSQLProductRepository(conn),
        notification=SmtpNotificationAdapter()
    )
```

---

## 7. 六边形架构 vs 分层架构

| 维度 | 分层架构 | 六边形架构 |
|------|---------|----------|
| 依赖方向 | Controller→Service→Repository→DB | Adapters→Domain（Port接口）←Adapters |
| 领域感知框架 | 是（Repository 接口在领域层） | 否（Port 在领域层，框架在适配器层） |
| 可测试性 | 需要 mock Repository | 可用内存实现，无需 mock |
| 复杂度 | 较低 | 较高（更多文件，更多目录） |
| 适用规模 | CRUD 为主，业务简单 | 复杂业务逻辑，多技术栈 |
| 迁移成本 | 低（直接开始） | 高（需要重新组织代码结构） |

### 何时选择六边形架构

```
业务逻辑是否足够复杂，值得独立出来？
├── 否（CRUD为主）→ 分层架构足够
└── 是 → 领域是否需要对接多种基础设施（多数据库、多消息队列）？
           ├── 否 → 分层架构 + 好的依赖注入也能达到效果
           └── 是 → 六边形架构，其可测试性和隔离性值得复杂度代价
```

---

## 8. Sprint 8 重构路线图

从分层架构（Sprint 1-7）迁移到六边形架构的步骤：

```
步骤1：提取领域模型（最低风险）
    shop/domain/model/product.py ← 从 shop/domain/product.py 移过去
    shop/domain/model/order.py

步骤2：定义 Port 接口
    shop/domain/ports/product_repository_port.py ← 从原 Repository 接口派生
    shop/domain/ports/notification_port.py        ← 新定义

步骤3：重组适配器
    shop/adapters/driven/postgresql_product_repository.py ← 原来的 PostgreSQLProductRepository
    shop/adapters/driving/fastapi_product_router.py       ← 原来的 api/product_router.py

步骤4：重写用例层
    shop/domain/use_cases/order_use_cases.py ← 原 service 层，改用 Port 接口

步骤5：更新依赖注入配置
    shop/config/container.py

步骤6：验证：pytest tests/domain/ 不启动数据库，全绿
```

---

## Key Architect Takeaways

- **六边形的核心是依赖反转**：不是领域层依赖数据库，而是数据库适配器依赖领域定义的端口接口
- **可测试性是最直观的收益**：能在不启动任何基础设施的情况下跑完所有业务逻辑测试，说明你真正实现了领域隔离
- **Port 是领域的声明**：Port 接口说的是"我需要什么能力"，不说"怎么实现"——这是领域层保持纯净的关键
- **不要过早引入**：六边形架构比分层架构复杂，更多文件更多概念。如果业务逻辑简单，分层架构足够；等到业务变复杂、测试变难，再考虑迁移
- **Sprint 8 是最好的学习时机**：在自己写的系统上做重构，能直接感受到两种架构在可测试性上的差距
