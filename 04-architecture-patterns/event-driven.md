# 事件驱动架构（Event-Driven Architecture）

事件驱动架构（EDA）是一种以"事件"为核心通信单元的架构风格。服务之间不再直接调用彼此，而是通过发布和消费事件来协作。这种解耦方式在高并发、微服务和异步处理场景中极为强大，但也引入了调试困难、最终一致性等新的复杂度。

---

## 1. 什么是事件驱动架构

### 1.1 事件 vs 消息 vs 命令

这三个概念经常混用，但在架构层面有明确的语义区别：

| 维度 | 事件（Event） | 消息（Message） | 命令（Command） |
|------|-------------|---------------|---------------|
| 语义 | "某件事已经发生了" | 通用的数据传输单元 | "请你去做某件事" |
| 时态 | 过去时（OrderPlaced） | 无固定时态 | 祈使句（PlaceOrder） |
| 发送方意图 | 发布者不关心谁消费，也不关心结果 | 通用，不限制 | 发送方期望接收方执行特定操作 |
| 接收方数量 | 0 到 N 个消费者 | 通常一对一 | 通常一对一 |
| 耦合度 | 最低（发布者不知道消费者） | 中等 | 较高（发送方依赖接收方能力） |
| 典型载体 | Kafka Topic、SNS | RabbitMQ Queue | HTTP POST、gRPC、SQS |
| 示例 | `OrderPlaced`、`PaymentFailed` | 任意数据包 | `CreateOrder`、`RefundPayment` |

> **架构师提示：** 区分三者的关键在于**意图和耦合度**。事件说的是"我发生了什么"，命令说的是"你要做什么"。混淆两者会导致错误的耦合：一个服务不该通过事件直接命令另一个服务做事，那是命令的职责。

### 1.2 事件驱动 vs 请求/响应（同步）

| 对比维度 | 请求/响应（同步） | 事件驱动（异步） |
|---------|----------------|--------------|
| 通信方向 | 调用方等待响应 | 发布者即发即忘 |
| 耦合度 | 调用方需要知道被调用方的地址和接口 | 发布方只需知道事件格式 |
| 可用性 | 任何一方宕机，链路中断 | 消费方宕机，事件在 Broker 中等待 |
| 延迟特性 | 延迟低，但链路上所有服务延迟叠加 | 单个操作延迟高，但总体吞吐量更大 |
| 一致性 | 强一致性容易实现（事务内） | 最终一致性，需要额外设计 |
| 调试难度 | 调用栈清晰，容易追踪 | 跨服务事件链难以追踪 |
| 适合场景 | 用户需要即时反馈（查询余额、登录） | 后台处理、跨服务协作、削峰填谷 |
| 扩展性 | 水平扩展需要负载均衡 | 天然扩展（增加消费者实例即可） |

### 1.3 核心组件：Producer / Event Broker / Consumer

```python
# 事件驱动架构的三个角色

# 1. Producer（生产者）：发布事件，不关心谁消费
class OrderService:
    def __init__(self, event_broker):
        self.broker = event_broker

    def place_order(self, user_id: str, items: list) -> dict:
        # 执行核心业务逻辑
        order = self._create_order_record(user_id, items)

        # 发布事件到 Broker，不调用任何其他服务
        self.broker.publish(
            topic="orders",
            event={
                "event_type": "OrderPlaced",
                "event_id": generate_uuid(),
                "aggregate_id": order["id"],
                "occurred_at": utcnow_iso(),
                "payload": {
                    "user_id": user_id,
                    "items": items,
                    "total": order["total"]
                }
            }
        )
        return order

    def _create_order_record(self, user_id, items):
        # 仅保存到本地数据库
        ...


# 2. Event Broker（事件代理）：负责接收、存储、路由事件
# 真实场景中是 Kafka / RabbitMQ / AWS SNS+SQS
# 这里用伪代码表示接口
class EventBroker:
    def publish(self, topic: str, event: dict):
        """将事件写入持久化存储，保证至少投递一次"""
        ...

    def subscribe(self, topic: str, consumer_group: str, handler):
        """订阅主题，同一消费组内只有一个实例处理同一条消息"""
        ...


# 3. Consumer（消费者）：独立服务，订阅感兴趣的事件
class InventoryService:
    def __init__(self, broker: EventBroker):
        broker.subscribe(
            topic="orders",
            consumer_group="inventory-service",
            handler=self.handle_event
        )

    def handle_event(self, event: dict):
        if event["event_type"] == "OrderPlaced":
            self._deduct_stock(event["payload"]["items"])

    def _deduct_stock(self, items):
        ...


class NotificationService:
    def __init__(self, broker: EventBroker):
        broker.subscribe(
            topic="orders",
            consumer_group="notification-service",
            handler=self.handle_event
        )

    def handle_event(self, event: dict):
        if event["event_type"] == "OrderPlaced":
            self._send_confirmation_email(event["payload"]["user_id"])
```

这段伪代码展示了核心优势：`OrderService` 不知道 `InventoryService` 和 `NotificationService` 的存在。新增一个 `LoyaltyPointsService` 只需订阅同一个 topic，完全不修改 `OrderService`。

---

## Key Architect Takeaways

- 事件说"发生了什么"，命令说"去做什么"——混淆两者是架构耦合的根源
- Producer 对 Consumer 零感知，这是事件驱动解耦的本质
- 同步调用适合需要即时反馈的用户操作；异步事件适合可以延迟执行的后台协作
- Event Broker 的可靠性（持久化、副本、幂等投递）是整个系统的关键基础设施
- 事件驱动不是银弹：它用可观测性复杂度换取了解耦和扩展性

---

## 2. 编排 vs 协同（Orchestration vs Choreography）

当多个服务需要协作完成一个业务流程时，有两种组织方式：编排（中央指挥官）和协同（各自响应事件）。

### 2.1 编排（Orchestration）：中央协调者模式

编排模式中存在一个"指挥官"（Orchestrator），它明确地调用每个参与者并管理整个流程。

**优点：**
- 流程逻辑集中，易于理解和追踪
- 错误处理和补偿逻辑在一个地方
- 容易实现复杂的条件分支和循环
- 可观测性强：一个服务的日志能看到完整流程

**缺点：**
- Orchestrator 成为核心耦合点，所有服务都依赖它
- Orchestrator 本身成为单点故障和性能瓶颈
- 难以扩展：添加新步骤必须修改 Orchestrator
- 违反单一职责：Orchestrator 知道太多其他服务的细节

```python
# 编排模式：OrderOrchestrator 控制整个下单流程
import asyncio

class OrderOrchestrator:
    """
    中央协调者：显式调用每个服务，管理完整的业务流程
    缺点：高耦合，任何步骤的接口变化都要修改这里
    """
    def __init__(self, inventory_svc, payment_svc, notification_svc, order_repo):
        self.inventory = inventory_svc
        self.payment = payment_svc
        self.notification = notification_svc
        self.order_repo = order_repo

    async def execute_place_order(self, user_id: str, items: list, payment_info: dict):
        order_id = None
        reserved = False
        charged = False

        try:
            # Step 1: 创建订单记录
            order_id = await self.order_repo.create(
                user_id=user_id,
                items=items,
                status="PENDING"
            )
            print(f"[Orchestrator] Order {order_id} created")

            # Step 2: 锁定库存（显式调用 InventoryService）
            await self.inventory.reserve(order_id=order_id, items=items)
            reserved = True
            print(f"[Orchestrator] Inventory reserved for order {order_id}")

            # Step 3: 扣款（显式调用 PaymentService）
            charge_id = await self.payment.charge(
                order_id=order_id,
                amount=self._calc_total(items),
                payment_info=payment_info
            )
            charged = True
            print(f"[Orchestrator] Payment charged: {charge_id}")

            # Step 4: 更新订单状态
            await self.order_repo.update_status(order_id, "CONFIRMED")

            # Step 5: 发送通知
            await self.notification.send_confirmation(user_id=user_id, order_id=order_id)

            return {"order_id": order_id, "status": "CONFIRMED"}

        except InventoryError as e:
            # 库存不足，取消订单
            if order_id:
                await self.order_repo.update_status(order_id, "CANCELLED")
            raise

        except PaymentError as e:
            # 扣款失败，释放库存
            if reserved:
                await self.inventory.release(order_id=order_id, items=items)
            if order_id:
                await self.order_repo.update_status(order_id, "CANCELLED")
            raise

    def _calc_total(self, items):
        return sum(item["price"] * item["quantity"] for item in items)
```

### 2.2 协同（Choreography）：服务通过事件自主响应

协同模式中没有中央指挥官。每个服务监听事件，做自己的事，再发布新的事件。整个流程是各服务"跳舞"出来的。

**优点：**
- 服务之间真正解耦：每个服务只需了解事件格式
- 添加新服务只需订阅现有事件，不修改任何现有服务
- 每个服务可以独立部署、扩展和故障恢复
- 没有单点故障的 Orchestrator

**缺点：**
- 整体流程逻辑分散在各个服务中，难以从单一视角理解全貌
- 分布式追踪困难：需要 Correlation ID 串联所有事件
- 循环事件风险：服务 A 响应事件发布新事件，服务 B 响应又发布事件触发服务 A
- 测试复杂：需要模拟整个事件链

```python
# 协同模式：每个服务自主响应事件，无中央协调者

# OrderService：接收用户请求，发布初始事件
class OrderService:
    def __init__(self, broker, order_repo):
        self.broker = broker
        self.order_repo = order_repo

    def place_order(self, user_id: str, items: list, correlation_id: str):
        # 只做自己的事：创建订单
        order = self.order_repo.create(user_id=user_id, items=items, status="PENDING")

        # 发布事件，让其他服务自己决定要做什么
        self.broker.publish("order-events", {
            "event_type": "OrderPlaced",
            "event_id": generate_uuid(),
            "aggregate_id": order.id,
            "correlation_id": correlation_id,  # 用于跨服务追踪
            "occurred_at": utcnow_iso(),
            "payload": {"user_id": user_id, "items": items, "total": order.total}
        })
        return order


# InventoryService：监听 OrderPlaced，完成后发布自己的结果事件
class InventoryService:
    def __init__(self, broker, inventory_repo):
        self.broker = broker
        self.repo = inventory_repo
        broker.subscribe("order-events", "inventory-group", self.on_event)

    def on_event(self, event: dict):
        if event["event_type"] != "OrderPlaced":
            return

        items = event["payload"]["items"]
        order_id = event["aggregate_id"]
        correlation_id = event["correlation_id"]

        try:
            self.repo.reserve(order_id=order_id, items=items)
            # 成功：发布库存已锁定事件
            self.broker.publish("inventory-events", {
                "event_type": "InventoryReserved",
                "event_id": generate_uuid(),
                "aggregate_id": order_id,
                "correlation_id": correlation_id,
                "occurred_at": utcnow_iso(),
                "payload": {"items": items}
            })
        except InsufficientStockError:
            # 失败：发布库存失败事件，让其他服务自行处理
            self.broker.publish("inventory-events", {
                "event_type": "InventoryReservationFailed",
                "event_id": generate_uuid(),
                "aggregate_id": order_id,
                "correlation_id": correlation_id,
                "occurred_at": utcnow_iso(),
                "payload": {"reason": "INSUFFICIENT_STOCK"}
            })


# PaymentService：监听 InventoryReserved，完成后发布支付结果
class PaymentService:
    def __init__(self, broker, payment_gateway):
        self.broker = broker
        self.gateway = payment_gateway
        broker.subscribe("inventory-events", "payment-group", self.on_event)

    def on_event(self, event: dict):
        if event["event_type"] == "InventoryReserved":
            order_id = event["aggregate_id"]
            correlation_id = event["correlation_id"]

            try:
                charge_id = self.gateway.charge(order_id=order_id)
                self.broker.publish("payment-events", {
                    "event_type": "PaymentCharged",
                    "event_id": generate_uuid(),
                    "aggregate_id": order_id,
                    "correlation_id": correlation_id,
                    "occurred_at": utcnow_iso(),
                    "payload": {"charge_id": charge_id}
                })
            except PaymentError as e:
                self.broker.publish("payment-events", {
                    "event_type": "PaymentFailed",
                    "event_id": generate_uuid(),
                    "aggregate_id": order_id,
                    "correlation_id": correlation_id,
                    "occurred_at": utcnow_iso(),
                    "payload": {"reason": str(e)}
                })

        elif event["event_type"] == "InventoryReservationFailed":
            # 库存失败，不需要支付，什么都不做（或者通知其他服务）
            pass
```

### 2.3 编排 vs 协同对比

| 对比维度 | 编排（Orchestration） | 协同（Choreography） |
|---------|---------------------|-------------------|
| 流程可见性 | 高：流程逻辑集中在 Orchestrator | 低：流程分散在各服务中 |
| 服务耦合度 | 高：所有服务都被 Orchestrator 调用 | 低：服务只依赖事件格式 |
| 可扩展性 | 低：新步骤需改 Orchestrator | 高：新服务订阅即可，不改现有代码 |
| 错误处理 | 集中、清晰 | 分散、复杂 |
| 可观测性 | 高：一个日志看全貌 | 低：需要分布式追踪 |
| 单点故障 | 存在（Orchestrator） | 不存在 |
| 适合场景 | 流程复杂、需要严格顺序控制 | 服务独立性强、流程简单或线性 |
| 典型工具 | Temporal、AWS Step Functions | Kafka、RabbitMQ、SNS |

**实际建议：** 复杂的有状态流程（订单、退款、审批）用编排；简单的广播通知型流程（用户注册后发邮件、发积分）用协同。许多系统会混合使用两种模式。

---

## Key Architect Takeaways

- 编排用于需要严格顺序、复杂补偿逻辑的业务流程；协同用于松散、广播型的事件通知
- 编排的最大风险是 Orchestrator 成为单点耦合；协同的最大风险是流程逻辑无处可读
- Temporal 等工具提供了"有持久化状态的 Orchestrator"，解决了编排的单点故障问题
- 协同模式必须有完善的分布式追踪（Correlation ID）才能在生产环境可维护
- 大多数成熟系统混合使用两种模式：用协同解耦服务，用编排管理复杂事务

---

## 3. Saga 模式（分布式事务）

### 3.1 为什么分布式环境不能用 2PC

两阶段提交（2PC）在单数据库中可行，但在微服务环境中存在致命缺陷：

| 问题 | 描述 |
|------|------|
| 阻塞 | 准备阶段所有参与者都持有锁，等待协调者响应 |
| 协调者单点故障 | 协调者宕机后，所有参与者永久阻塞 |
| 服务边界 | 每个微服务有自己的数据库，无法共享同一个分布式事务 |
| 性能 | 锁持有时间长，并发度极低 |
| 跨技术栈 | PostgreSQL + MongoDB + 第三方支付 API 无法参与同一个 2PC |

**结论：** 微服务环境中不使用 2PC，改用 Saga。

### 3.2 Saga 基本原理

Saga 将一个分布式事务拆解为一系列**本地事务**（Local Transaction）。每个本地事务完成后发布事件，触发下一步。如果某一步失败，则触发**补偿事务**（Compensating Transaction）逆序回滚之前的操作。

```
正向流程（Happy Path）：
  T1（创建订单）→ T2（锁定库存）→ T3（扣款）→ T4（确认订单）

失败场景（T3 扣款失败）：
  T1 → T2 → T3 失败 → C2（释放库存）→ C1（取消订单）

关键认知：
- 每个 Ti 是一个本地数据库事务，ACID 保证
- 补偿事务 Ci 在语义上"撤销" Ti，但不是数据库级别的回滚
- Saga 提供的是最终一致性，不是强一致性
```

### 3.3 编排式 Saga 示例（订单 + 库存 + 支付）

```python
# 编排式 Saga：SagaOrchestrator 管理整个分布式事务的状态和补偿逻辑
import enum

class SagaState(enum.Enum):
    STARTED = "STARTED"
    INVENTORY_RESERVED = "INVENTORY_RESERVED"
    PAYMENT_CHARGED = "PAYMENT_CHARGED"
    COMPLETED = "COMPLETED"
    COMPENSATING = "COMPENSATING"
    FAILED = "FAILED"


class PlaceOrderSaga:
    """
    编排式 Saga：负责协调订单创建的分布式事务
    状态持久化到数据库，服务重启后可以从断点恢复
    """
    def __init__(self, saga_repo, inventory_svc, payment_svc, order_repo):
        self.saga_repo = saga_repo        # 持久化 Saga 状态
        self.inventory = inventory_svc
        self.payment = payment_svc
        self.order_repo = order_repo

    async def start(self, saga_id: str, user_id: str, items: list, payment_info: dict):
        """启动 Saga：创建 Saga 状态记录，开始正向流程"""
        # 持久化初始状态（幂等：已存在则跳过）
        await self.saga_repo.create(saga_id=saga_id, state=SagaState.STARTED, data={
            "user_id": user_id,
            "items": items,
            "payment_info": payment_info
        })

        # Step 1: 本地事务 T1 — 创建订单（本服务自己的数据库，ACID 保证）
        order = await self.order_repo.create(
            user_id=user_id,
            items=items,
            status="PENDING",
            saga_id=saga_id
        )
        await self.saga_repo.update(saga_id, data={"order_id": order.id})

        # 触发下一步
        await self._reserve_inventory(saga_id, order.id, items)

    async def _reserve_inventory(self, saga_id: str, order_id: str, items: list):
        """Step 2: 本地事务 T2 — 调用库存服务（RPC 或事件）"""
        try:
            await self.inventory.reserve(order_id=order_id, items=items)
            await self.saga_repo.update(saga_id, state=SagaState.INVENTORY_RESERVED)
            await self._charge_payment(saga_id, order_id)
        except InventoryError as e:
            # T2 失败，只需补偿 T1（取消订单）
            await self._compensate(saga_id, step="AFTER_T1")

    async def _charge_payment(self, saga_id: str, order_id: str):
        """Step 3: 本地事务 T3 — 调用支付服务"""
        saga = await self.saga_repo.get(saga_id)
        payment_info = saga.data["payment_info"]

        try:
            charge_id = await self.payment.charge(
                order_id=order_id,
                amount=saga.data.get("total"),
                payment_info=payment_info
            )
            await self.saga_repo.update(saga_id,
                state=SagaState.PAYMENT_CHARGED,
                data={"charge_id": charge_id}
            )
            # 所有步骤成功，完成
            await self._complete(saga_id, order_id)
        except PaymentError as e:
            # T3 失败，补偿 T2 和 T1
            await self._compensate(saga_id, step="AFTER_T2")

    async def _complete(self, saga_id: str, order_id: str):
        """正向流程全部成功"""
        await self.order_repo.update_status(order_id, "CONFIRMED")
        await self.saga_repo.update(saga_id, state=SagaState.COMPLETED)
        print(f"[Saga {saga_id}] Completed successfully")

    async def _compensate(self, saga_id: str, step: str):
        """补偿流程：根据已完成的步骤逆序回滚"""
        saga = await self.saga_repo.get(saga_id)
        await self.saga_repo.update(saga_id, state=SagaState.COMPENSATING)

        order_id = saga.data.get("order_id")
        items = saga.data["items"]

        try:
            if step == "AFTER_T2":
                # 补偿事务 C2：释放库存
                await self.inventory.release(order_id=order_id, items=items)
                print(f"[Saga {saga_id}] C2: Inventory released")

            if step in ("AFTER_T2", "AFTER_T1"):
                # 补偿事务 C1：取消订单
                await self.order_repo.update_status(order_id, "CANCELLED")
                print(f"[Saga {saga_id}] C1: Order cancelled")

            await self.saga_repo.update(saga_id, state=SagaState.FAILED)

        except Exception as e:
            # 补偿失败是最严重的情况，需要人工介入
            print(f"[Saga {saga_id}] CRITICAL: Compensation failed at {step}: {e}")
            await self.saga_repo.update(saga_id, state=SagaState.FAILED,
                data={"compensation_error": str(e), "requires_manual_intervention": True})
            raise
```

### 3.4 补偿事务的关键设计

```python
# 补偿事务设计原则：必须是幂等的
# 相同的补偿事务执行多次，结果一样

class InventoryService:
    async def release(self, order_id: str, items: list):
        """
        补偿事务 C2：释放库存
        必须是幂等的：如果已经释放过，再次调用不应该多释放
        """
        # 通过 order_id 检查是否已经释放过
        reservation = await self.repo.find_reservation(order_id)

        if reservation is None:
            # 已经释放或从未预留，幂等处理，直接返回成功
            print(f"[Inventory] Release skipped: no reservation found for order {order_id}")
            return

        if reservation.status == "RELEASED":
            # 已释放，幂等处理
            print(f"[Inventory] Release already done for order {order_id}")
            return

        # 执行实际释放
        async with self.db.transaction():
            for item in items:
                await self.repo.add_stock(
                    product_id=item["product_id"],
                    quantity=item["quantity"]
                )
            await self.repo.update_reservation_status(order_id, "RELEASED")


class PaymentService:
    async def refund(self, order_id: str, charge_id: str):
        """
        补偿事务：退款
        注意：退款不等于"没有扣款"，这是语义补偿，不是物理回滚
        外部支付系统（支付宝、Stripe）的退款 API 是新的操作
        """
        # 检查是否已退款
        existing_refund = await self.repo.find_refund(order_id=order_id)
        if existing_refund:
            return existing_refund

        # 调用外部支付网关
        refund_id = await self.payment_gateway.refund(charge_id=charge_id)
        await self.repo.record_refund(order_id=order_id, refund_id=refund_id)
        return refund_id
```

### 3.5 Saga 的局限性

| 局限性 | 说明 | 应对策略 |
|--------|------|---------|
| 隔离性弱 | T1 完成后，其他事务可以读到"中间状态"的数据 | 使用语义锁（如订单 PENDING 状态）防止并发冲突 |
| 补偿逻辑复杂 | 补偿事务本身可能失败，需要重试和告警机制 | 补偿事务必须设计为幂等；最终人工介入兜底 |
| 调试困难 | 跨服务的事务状态难以追踪 | 持久化 Saga 状态记录；使用 Correlation ID 追踪 |
| 不可补偿操作 | 发送了短信/邮件无法撤回 | 将不可逆操作放在 Saga 最后一步执行 |
| 脏读问题 | 库存 RESERVED 但订单最终 CANCELLED，中间窗口内可能误判库存 | 读操作过滤掉 PENDING/RESERVING 状态的记录 |

---

## Key Architect Takeaways

- Saga 的本质是：用最终一致性替代强一致性，用补偿事务替代物理回滚
- 补偿事务必须是幂等的：网络重试可能导致同一补偿被执行多次
- 不可逆操作（发短信、扣外部账户）永远放在 Saga 的最后一步，减少需要补偿的概率
- Saga 状态必须持久化到数据库，服务重启后才能从断点恢复
- 补偿失败比原始失败更严重，必须有告警和人工干预机制

---

## 4. 事件溯源（Event Sourcing）

### 4.1 核心思想

传统系统保存的是"当前状态"（当前余额是 500 元）。事件溯源保存的是"导致状态的所有事件"（存入 1000 元、取出 300 元、转出 200 元）。**当前状态是所有历史事件重放的结果。**

```
传统 CRUD：
  数据库保存：{ "order_id": 1, "status": "SHIPPED" }
  问题：无法知道"为什么变成 SHIPPED"，也无法知道中间经历了什么状态

事件溯源：
  事件存储（Append-Only）：
    [0] OrderPlaced    { user_id: 1, items: [...], total: 200 }
    [1] PaymentCharged { charge_id: "ch_123", amount: 200 }
    [2] OrderConfirmed { confirmed_at: "2024-01-01T10:00:00Z" }
    [3] OrderShipped   { tracking_no: "SF123456" }

  重放所有事件 → 当前状态是 SHIPPED
```

### 4.2 与传统 CRUD 的对比

| 维度 | 传统 CRUD | 事件溯源 |
|------|----------|---------|
| 存储内容 | 当前状态快照 | 所有历史事件（只追加，不修改） |
| 数据模型 | 可变行（UPDATE/DELETE） | 不可变事件日志（仅 INSERT） |
| 历史审计 | 需要额外的 audit_log 表 | 天然的完整审计日志 |
| 时间旅行 | 不支持（除非有备份） | 支持：重放到任意时间点 |
| 查询复杂度 | 低：直接查当前状态 | 高：需要重放事件或维护读模型 |
| 写入性能 | 需要加锁更新 | 仅追加，无锁冲突，性能极高 |
| 事件演化 | 不涉及 | 复杂：旧事件格式需要兼容或迁移 |
| 调试能力 | 弱：只能看到当前状态 | 强：可以重放任意历史状态 |

### 4.3 优点详解

**审计日志（Audit Log）：** 每个事件天然记录"谁、在什么时候、做了什么"，满足金融、医疗等行业的合规要求，无需额外开发。

**时间旅行（Time Travel）：** 将事件重放到某个时间点，可以精确还原系统的历史状态，用于排查生产问题。

**事件回放（Event Replay）：** 新增一个读模型（如分析报表），只需重放所有历史事件，不需要数据迁移。

### 4.4 缺点和挑战

| 挑战 | 说明 |
|------|------|
| 查询复杂 | 不能直接 SELECT 当前状态，必须重放事件或维护专门的读模型（CQRS） |
| 快照机制 | 事件积累到百万级后，每次重放性能极差，需要定期生成状态快照 |
| 事件演化 | 事件 Schema 变化后，历史事件格式不同，需要版本化和"向上转型"（Upcasting） |
| 学习曲线 | 团队需要彻底改变思维模式，从"状态"转向"事件" |
| 存储增长 | 事件只追加，存储持续增长，需要归档策略 |

### 4.5 Python 伪代码：带事件溯源的 OrderAggregate

```python
# 事件溯源核心实现：Order 聚合根
import dataclasses
from typing import Any

# --- 事件定义 ---

@dataclasses.dataclass
class DomainEvent:
    event_id: str
    event_type: str
    aggregate_id: str
    occurred_at: str
    version: int         # 该事件在聚合根事件序列中的位置（乐观锁）
    payload: dict


def make_event(event_type: str, aggregate_id: str, version: int, payload: dict) -> DomainEvent:
    return DomainEvent(
        event_id=generate_uuid(),
        event_type=event_type,
        aggregate_id=aggregate_id,
        occurred_at=utcnow_iso(),
        version=version,
        payload=payload
    )


# --- 聚合根 ---

class OrderAggregate:
    """
    Order 聚合根：使用事件溯源
    - 状态不直接修改，通过 apply(event) 演化
    - 所有未提交的事件记录在 _pending_events
    """

    def __init__(self):
        self.order_id = None
        self.user_id = None
        self.status = None
        self.items = []
        self.total = 0.0
        self.charge_id = None
        self._version = 0              # 当前事件序号（乐观锁）
        self._pending_events = []      # 尚未持久化的新事件

    # ==================== 命令方法（产生新事件）====================

    def place_order(self, order_id: str, user_id: str, items: list):
        """命令：下单。产生 OrderPlaced 事件。"""
        if self.status is not None:
            raise ValueError("Order already exists")

        total = sum(i["price"] * i["quantity"] for i in items)
        event = make_event(
            event_type="OrderPlaced",
            aggregate_id=order_id,
            version=self._version + 1,
            payload={"user_id": user_id, "items": items, "total": total}
        )
        self._apply_and_record(event)

    def charge_payment(self, charge_id: str):
        """命令：记录扣款成功。"""
        if self.status != "PENDING":
            raise ValueError(f"Cannot charge payment in status '{self.status}'")

        event = make_event(
            event_type="PaymentCharged",
            aggregate_id=self.order_id,
            version=self._version + 1,
            payload={"charge_id": charge_id}
        )
        self._apply_and_record(event)

    def confirm(self):
        """命令：确认订单。"""
        if self.status != "PAYMENT_CHARGED":
            raise ValueError(f"Cannot confirm in status '{self.status}'")

        event = make_event(
            event_type="OrderConfirmed",
            aggregate_id=self.order_id,
            version=self._version + 1,
            payload={}
        )
        self._apply_and_record(event)

    def cancel(self, reason: str):
        """命令：取消订单。"""
        if self.status in ("SHIPPED", "DELIVERED"):
            raise ValueError("Cannot cancel shipped or delivered orders")

        event = make_event(
            event_type="OrderCancelled",
            aggregate_id=self.order_id,
            version=self._version + 1,
            payload={"reason": reason}
        )
        self._apply_and_record(event)

    # ==================== 事件应用方法（演化状态）====================

    def _apply_and_record(self, event: DomainEvent):
        """应用事件并记录到待提交列表"""
        self._apply(event)
        self._pending_events.append(event)

    def _apply(self, event: DomainEvent):
        """
        根据事件类型演化内部状态。
        此方法也用于从事件存储重建（重放历史事件）。
        """
        self._version = event.version

        if event.event_type == "OrderPlaced":
            self.order_id = event.aggregate_id
            self.user_id = event.payload["user_id"]
            self.items = event.payload["items"]
            self.total = event.payload["total"]
            self.status = "PENDING"

        elif event.event_type == "PaymentCharged":
            self.charge_id = event.payload["charge_id"]
            self.status = "PAYMENT_CHARGED"

        elif event.event_type == "OrderConfirmed":
            self.status = "CONFIRMED"

        elif event.event_type == "OrderCancelled":
            self.status = "CANCELLED"

        else:
            raise ValueError(f"Unknown event type: {event.event_type}")

    # ==================== 重建方法（从历史事件恢复）====================

    @classmethod
    def reconstitute(cls, events: list[DomainEvent]) -> "OrderAggregate":
        """从事件历史重建聚合根状态（时间旅行的基础）"""
        if not events:
            raise ValueError("Cannot reconstitute from empty event list")

        aggregate = cls()
        for event in events:
            aggregate._apply(event)   # 重放每个事件（不记录到 _pending_events）
        return aggregate

    @classmethod
    def reconstitute_until(cls, events: list[DomainEvent], until_iso: str) -> "OrderAggregate":
        """时间旅行：重建到某个时间点的状态"""
        filtered = [e for e in events if e.occurred_at <= until_iso]
        return cls.reconstitute(filtered)

    def pop_pending_events(self) -> list[DomainEvent]:
        """取出待持久化的事件（由 Repository 调用后清空）"""
        events = list(self._pending_events)
        self._pending_events.clear()
        return events


# --- 事件存储 Repository ---

class OrderEventStoreRepository:
    """
    事件存储 Repository：只追加，不更新
    """
    def __init__(self, event_store_db):
        self.db = event_store_db

    async def save(self, aggregate: OrderAggregate):
        """持久化新事件（带乐观锁防止并发冲突）"""
        pending = aggregate.pop_pending_events()
        if not pending:
            return

        # 乐观锁：验证事件版本连续性
        latest_version = await self.db.get_latest_version(pending[0].aggregate_id)
        expected_version = pending[0].version - 1
        if latest_version != expected_version:
            raise OptimisticLockError(
                f"Concurrency conflict: expected version {expected_version}, "
                f"got {latest_version}"
            )

        # 批量插入事件（Append-Only）
        await self.db.insert_events([
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "aggregate_id": e.aggregate_id,
                "version": e.version,
                "occurred_at": e.occurred_at,
                "payload": json.dumps(e.payload)
            }
            for e in pending
        ])

    async def load(self, order_id: str) -> OrderAggregate:
        """从事件存储加载聚合根（重放所有事件）"""
        rows = await self.db.query(
            "SELECT * FROM order_events WHERE aggregate_id = ? ORDER BY version ASC",
            order_id
        )
        if not rows:
            raise OrderNotFoundError(order_id)

        events = [
            DomainEvent(
                event_id=r["event_id"],
                event_type=r["event_type"],
                aggregate_id=r["aggregate_id"],
                occurred_at=r["occurred_at"],
                version=r["version"],
                payload=json.loads(r["payload"])
            )
            for r in rows
        ]
        return OrderAggregate.reconstitute(events)


# --- 快照机制（性能优化）---

class OrderSnapshotRepository:
    """
    快照优化：每 N 个事件生成一次状态快照
    加载时：先加载最近的快照，再重放快照之后的事件
    """
    SNAPSHOT_THRESHOLD = 50  # 每 50 个事件生成一次快照

    async def load_with_snapshot(self, order_id: str) -> OrderAggregate:
        # 尝试加载最近的快照
        snapshot = await self.db.get_latest_snapshot(order_id)

        if snapshot:
            # 只重放快照之后的事件（性能从 O(N) → O(N - snapshot_version)）
            events_since = await self.db.query(
                "SELECT * FROM order_events WHERE aggregate_id = ? AND version > ? ORDER BY version",
                order_id, snapshot["version"]
            )
            aggregate = OrderAggregate.from_snapshot(snapshot)
            for event in events_since:
                aggregate._apply(event)
            return aggregate
        else:
            # 没有快照，重放所有事件
            return await self.event_repo.load(order_id)

    async def maybe_take_snapshot(self, aggregate: OrderAggregate):
        """超过阈值时自动生成快照"""
        if aggregate._version % self.SNAPSHOT_THRESHOLD == 0:
            await self.db.save_snapshot({
                "aggregate_id": aggregate.order_id,
                "version": aggregate._version,
                "state": aggregate.to_dict()
            })
```

---

## Key Architect Takeaways

- 事件溯源的核心价值不是"存事件"，而是"事件是真相的唯一来源"——状态是派生产物
- 快照机制是生产级事件溯源的必要条件，否则百万级事件重放性能不可接受
- 乐观锁（版本号）是防止并发写入冲突的关键机制，不能省略
- 事件演化是最大的长期成本：一旦发布的事件格式就是"公共契约"，修改需要向后兼容
- 事件溯源几乎总是和 CQRS 配合使用，因为直接查询事件日志的体验极差

---

## 5. CQRS（命令查询职责分离）

### 5.1 核心思想

CQRS（Command Query Responsibility Segregation）将系统的**写操作（Command）**和**读操作（Query）**拆分到不同的模型中：

- **写模型（Command Side）：** 处理业务规则、验证、状态变更。以"聚合根"为中心，保证数据一致性。
- **读模型（Query Side）：** 专为查询优化。可以是关系数据库、Redis、Elasticsearch，结构完全根据查询需求设计。

```
传统 CRUD（读写共用同一个模型）：
  客户端 → Service → 同一张 Orders 表 ← 查询也从这里

CQRS（读写分离）：
  写请求 → Command Handler → Write DB（以聚合为单位）
                           ↓ 事件
  读请求 → Query Handler ← Read DB（以查询为单位，多个物化视图）
```

### 5.2 为什么与事件溯源天然配对

| 事件溯源的问题 | CQRS 的解决 |
|-------------|-----------|
| 无法直接查询当前状态 | 消费事件，构建专用的读模型（物化视图） |
| 复杂的聚合查询（多聚合 JOIN）难以从事件重建 | 读模型可以跨聚合 JOIN，专为查询优化 |
| 写操作需要强一致性，读操作需要高性能 | 写用事件存储，读用 Redis/Elasticsearch |

**事件溯源生产新事件 → CQRS 读模型消费事件 → 构建物化视图** 这是两者结合的标准模式。

### 5.3 同步 CQRS vs 异步 CQRS

| 维度 | 同步 CQRS | 异步 CQRS |
|------|----------|---------|
| 读模型更新时机 | 写操作成功后立即更新读模型（同一事务） | 写操作发布事件，读模型异步消费 |
| 一致性 | 强一致性（读写同步） | 最终一致性（读模型滞后） |
| 性能 | 写入延迟高（需要同时更新两个模型） | 写入延迟低，读模型更新异步 |
| 故障处理 | 任一更新失败，整体回滚 | 读模型更新失败可独立重试 |
| 适合场景 | 读写数量差不多，强一致性要求高 | 读远多于写，可以接受短暂不一致 |

### 5.4 最终一致性的含义和影响

```
时间线（异步 CQRS）：
  t=0ms   用户提交"下单"请求
  t=5ms   写模型保存事件（OrderPlaced），返回 HTTP 202 Accepted
  t=5ms   事件发布到 Kafka
  t=50ms  读模型消费者处理 OrderPlaced，更新 orders_view 表
  t=50ms  用户刷新"我的订单"列表，此时读模型已更新 ✓

  如果消费者滞后：
  t=5ms   写成功，返回 202
  t=6ms   用户立即查询"我的订单"
  t=6ms   读模型还没更新 → 查不到刚下的订单 ✗（短暂不一致）

应对策略：
1. 写完后返回 202 Accepted + 订单 ID，前端用订单 ID 轮询状态
2. 乐观 UI：前端在本地临时显示"处理中"的订单，不依赖读模型
3. 对延迟敏感的操作（如支付确认），走同步路径，不走 CQRS
```

### 5.5 Python 伪代码示例

```python
# CQRS 完整示例：命令端 + 查询端

# ==================== 写端（Command Side）====================

class PlaceOrderCommand:
    """命令：封装用户意图，不含业务逻辑"""
    def __init__(self, user_id: str, items: list, payment_info: dict):
        self.command_id = generate_uuid()
        self.user_id = user_id
        self.items = items
        self.payment_info = payment_info
        self.issued_at = utcnow_iso()


class PlaceOrderCommandHandler:
    """命令处理器：包含业务逻辑，写入事件存储"""
    def __init__(self, order_repo: OrderEventStoreRepository, event_bus):
        self.repo = order_repo
        self.event_bus = event_bus

    async def handle(self, cmd: PlaceOrderCommand) -> str:
        # 1. 创建聚合根，执行业务逻辑
        order = OrderAggregate()
        order.place_order(
            order_id=generate_uuid(),
            user_id=cmd.user_id,
            items=cmd.items
        )

        # 2. 持久化事件到事件存储
        await self.repo.save(order)

        # 3. 发布事件到消息总线（供读模型消费）
        for event in order.pop_pending_events():
            await self.event_bus.publish("order-events", event)

        return order.order_id


# ==================== 读端（Query Side）====================

class OrderSummaryView:
    """读模型：为"订单列表"查询优化的物化视图"""
    order_id: str
    user_id: str
    status: str
    total: float
    item_count: int
    created_at: str
    last_updated: str


class OrderReadModelProjector:
    """
    投影器（Projector）：消费事件，维护读模型
    本质上是事件的"物化"：把事件流转换为查询友好的表结构
    """
    def __init__(self, read_db):
        self.db = read_db

    async def on_event(self, event: DomainEvent):
        """处理事件，更新读模型（必须是幂等的）"""
        if event.event_type == "OrderPlaced":
            # 插入或更新（幂等：同一 event_id 不重复处理）
            await self.db.upsert("order_summary_view", {
                "order_id": event.aggregate_id,
                "user_id": event.payload["user_id"],
                "status": "PENDING",
                "total": event.payload["total"],
                "item_count": len(event.payload["items"]),
                "created_at": event.occurred_at,
                "last_updated": event.occurred_at,
                "processed_event_id": event.event_id   # 幂等键
            }, conflict_column="order_id")

        elif event.event_type == "PaymentCharged":
            await self.db.update("order_summary_view",
                where={"order_id": event.aggregate_id},
                values={"status": "PAYMENT_CHARGED", "last_updated": event.occurred_at}
            )

        elif event.event_type == "OrderConfirmed":
            await self.db.update("order_summary_view",
                where={"order_id": event.aggregate_id},
                values={"status": "CONFIRMED", "last_updated": event.occurred_at}
            )

        elif event.event_type == "OrderCancelled":
            await self.db.update("order_summary_view",
                where={"order_id": event.aggregate_id},
                values={
                    "status": "CANCELLED",
                    "cancel_reason": event.payload["reason"],
                    "last_updated": event.occurred_at
                }
            )


class OrderQueryService:
    """查询服务：直接查询读模型，不碰事件存储"""
    def __init__(self, read_db):
        self.db = read_db

    async def get_user_orders(self, user_id: str, page: int = 1, size: int = 20) -> list:
        """直接查物化视图，性能极佳（可加索引、可接 Redis 缓存）"""
        return await self.db.query(
            """SELECT order_id, status, total, item_count, created_at
               FROM order_summary_view
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            user_id, size, (page - 1) * size
        )

    async def get_order_detail(self, order_id: str) -> dict:
        return await self.db.query_one(
            "SELECT * FROM order_summary_view WHERE order_id = ?",
            order_id
        )

    async def get_revenue_by_date(self, date: str) -> float:
        """聚合查询：直接在读模型上执行，不影响写端性能"""
        result = await self.db.query_one(
            """SELECT COALESCE(SUM(total), 0) as revenue
               FROM order_summary_view
               WHERE DATE(created_at) = ? AND status = 'CONFIRMED'""",
            date
        )
        return result["revenue"]


# ==================== API 层：命令和查询走不同路径 ====================

class OrderAPI:
    def __init__(self, command_handler: PlaceOrderCommandHandler,
                 query_service: OrderQueryService):
        self.commands = command_handler
        self.queries = query_service

    async def post_order(self, request: dict) -> dict:
        """写端：返回 202 Accepted + order_id"""
        cmd = PlaceOrderCommand(
            user_id=request["user_id"],
            items=request["items"],
            payment_info=request["payment_info"]
        )
        order_id = await self.commands.handle(cmd)
        # 202：请求已接受，但处理是异步的
        return {"status": "accepted", "order_id": order_id}

    async def get_orders(self, user_id: str, page: int) -> list:
        """读端：直接查物化视图，极快"""
        return await self.queries.get_user_orders(user_id, page)
```

---

## Key Architect Takeaways

- CQRS 的本质是：读和写有不同的优化目标，不要强迫同一个模型同时满足两者
- 读模型可以有多个，为不同的查询场景单独优化（列表视图、详情视图、报表视图）
- 最终一致性要在 API 设计上体现：写端返回 202 Accepted，而非 200 OK with body
- 读模型的 Projector 必须是幂等的，因为事件可能被重复投递（at-least-once delivery）
- 不要对简单的 CRUD 应用 CQRS——它增加的复杂度只有在读写压力不对称时才值得

---

## 6. 事件设计最佳实践

### 6.1 事件命名约定

事件表达"已经发生的事实"，因此必须使用**过去时**命名：

| 好的命名（过去时） | 坏的命名（原因） |
|----------------|--------------|
| `OrderPlaced` | `PlaceOrder`（这是命令，不是事件） |
| `PaymentFailed` | `PaymentFailure`（名词，不够精确） |
| `InventoryReserved` | `ReserveInventory`（这是命令） |
| `UserRegistered` | `UserRegistration`（名词化，语义模糊） |
| `OrderShipped` | `OrderShipping`（进行时，不准确） |
| `ProductPriceUpdated` | `UpdateProductPrice`（命令形式） |

**命名约定：** `{聚合名}{动词过去时}`，如 `OrderPlaced`、`PaymentCharged`、`ShipmentDispatched`

### 6.2 事件 Schema 设计

一个标准的事件 Schema 应包含以下字段：

```python
# 标准事件结构

@dataclasses.dataclass
class StandardEvent:
    # ===== 元数据（框架层关心）=====
    event_id: str        # 全局唯一 ID（UUID v4），用于幂等消费
    event_type: str      # 事件类型名称，如 "OrderPlaced"
    event_version: str   # 事件 Schema 版本，如 "1.0"（用于演化）
    aggregate_id: str    # 聚合根 ID（该事件所属的实体 ID）
    aggregate_type: str  # 聚合根类型，如 "Order"
    occurred_at: str     # 事件发生时间（ISO 8601 UTC）
    published_at: str    # 事件发布到 Broker 的时间（监控用）

    # ===== 追踪字段（可观测性）=====
    correlation_id: str  # 请求链路 ID，跨服务追踪
    causation_id: str    # 因果链：触发本事件的上一个事件 ID

    # ===== 业务数据（消费者关心）=====
    payload: dict        # 事件的业务数据（因事件类型不同而异）


# 具体事件实例
order_placed_event = {
    "event_id": "evt-550e8400-e29b-41d4-a716-446655440000",
    "event_type": "OrderPlaced",
    "event_version": "1.0",
    "aggregate_id": "ord-12345",
    "aggregate_type": "Order",
    "occurred_at": "2024-01-15T10:30:00.000Z",
    "published_at": "2024-01-15T10:30:00.050Z",
    "correlation_id": "req-abc123",    # 用户的原始请求 ID
    "causation_id": None,              # 第一个事件，没有因果事件
    "payload": {
        "user_id": "usr-789",
        "items": [
            {"product_id": "prod-001", "quantity": 2, "price": 99.99}
        ],
        "total": 199.98,
        "shipping_address": {
            "city": "Beijing",
            "street": "朝阳区建国路 88 号"
        }
    }
}


# Payload 设计原则：
# ✓ 包含消费者完成处理所需的所有数据（避免消费者回调查询）
# ✓ 不包含敏感信息（信用卡号、密码）
# ✗ 不要传递数据库内部 ID 作为唯一标识（应传业务 ID）
# ✗ 不要传递过大的嵌套对象（Payload 不是数据库 dump）
```

### 6.3 事件版本化（Schema 演化）

事件一旦发布，就成为"公共契约"。消费者可能运行旧版本，无法同步升级。版本化的目标是在演化 Schema 的同时，不破坏任何消费者。

**演化规则：**

| 操作 | 向后兼容？ | 处理方式 |
|------|---------|---------|
| 添加新的可选字段 | 是 | 直接添加，旧消费者忽略新字段 |
| 移除字段 | 否 | 先废弃（标记 deprecated），等所有消费者升级后再删除 |
| 重命名字段 | 否 | 同时保留新旧字段名，过渡期后删除旧字段 |
| 修改字段类型 | 否 | 升级 event_version，提供 Upcaster |
| 修改字段语义 | 否 | 视同新字段，创建新的事件类型 |

```python
# 事件版本化：Upcaster 模式
# 当 event_version 变化时，用 Upcaster 将旧格式转换为新格式

class OrderPlacedUpcaster:
    """
    将 OrderPlaced v1.0 升级到 v2.0
    v1.0：payload.total 是整数（分）
    v2.0：payload.total 是浮点数（元），新增 currency 字段
    """

    def can_upcast(self, event: dict) -> bool:
        return (event["event_type"] == "OrderPlaced"
                and event["event_version"] == "1.0")

    def upcast(self, event: dict) -> dict:
        new_event = dict(event)  # 浅拷贝
        new_event["event_version"] = "2.0"
        new_event["payload"] = dict(event["payload"])
        # 将分转换为元
        new_event["payload"]["total"] = event["payload"]["total"] / 100.0
        # 添加新字段（使用合理的默认值）
        new_event["payload"]["currency"] = "CNY"
        return new_event


class EventUpcasterChain:
    """Upcaster 链：支持跨多个版本的升级"""
    def __init__(self, upcasters: list):
        self.upcasters = upcasters

    def upcast(self, event: dict) -> dict:
        result = event
        for upcaster in self.upcasters:
            if upcaster.can_upcast(result):
                result = upcaster.upcast(result)
        return result


# 使用：在消费者加载事件时应用 Upcaster
upcaster_chain = EventUpcasterChain([
    OrderPlacedUpcaster(),
    # 未来的 v2.0 → v3.0 Upcaster 加在这里
])

def load_and_upcast_events(raw_events: list) -> list:
    return [upcaster_chain.upcast(e) for e in raw_events]
```

### 6.4 幂等消费者设计

消息队列保证"至少投递一次"（at-least-once delivery），同一条事件可能被消费多次。消费者必须设计为幂等的：

```python
# 幂等消费者：通过 event_id 去重

class IdempotentEventConsumer:
    """
    幂等消费者基类：自动处理重复投递
    使用 processed_events 表记录已处理的 event_id
    """
    def __init__(self, db):
        self.db = db

    async def consume(self, event: dict):
        event_id = event["event_id"]

        # 幂等检查：是否已处理过（原子操作，防并发）
        already_processed = await self.db.try_insert_processed_event(
            event_id=event_id,
            event_type=event["event_type"],
            processed_at=utcnow_iso()
        )

        if already_processed:
            # 重复事件，跳过处理
            print(f"[Consumer] Skipping duplicate event: {event_id}")
            return

        # 首次处理，执行业务逻辑
        try:
            await self.process(event)
        except Exception as e:
            # 处理失败，删除 processed_events 记录，允许重试
            await self.db.delete_processed_event(event_id)
            raise

    async def process(self, event: dict):
        """子类实现具体的业务逻辑"""
        raise NotImplementedError


# 具体消费者实现
class InventoryProjector(IdempotentEventConsumer):
    def __init__(self, db, inventory_repo):
        super().__init__(db)
        self.inventory = inventory_repo

    async def process(self, event: dict):
        if event["event_type"] == "OrderPlaced":
            # 幂等性已由基类保证，这里放心执行业务逻辑
            items = event["payload"]["items"]
            order_id = event["aggregate_id"]
            await self.inventory.reserve(order_id=order_id, items=items)

        elif event["event_type"] == "OrderCancelled":
            order_id = event["aggregate_id"]
            await self.inventory.release(order_id=order_id)


# processed_events 表结构（SQL 示例）：
# CREATE TABLE processed_events (
#     event_id    VARCHAR(36) PRIMARY KEY,   -- UUID，唯一约束保证原子幂等
#     event_type  VARCHAR(100),
#     consumer    VARCHAR(100),              -- 不同消费者独立去重
#     processed_at TIMESTAMP
# );
```

---

## Key Architect Takeaways

- 事件用过去时命名（`OrderPlaced`），区分于命令（`PlaceOrder`）——这不是风格问题，是语义问题
- 标准 Schema 中 `event_id` 和 `correlation_id` 是必须项：前者用于幂等，后者用于追踪
- 添加字段向后兼容，删除/修改字段向后不兼容——演化事件 Schema 时先废弃再删除
- 幂等消费是事件驱动系统的底线要求，`processed_events` 表的唯一约束是最简洁的实现
- Payload 应该自包含（消费者不需要再查询获取信息），但不要包含敏感数据

---

## 7. 实际权衡

### 7.1 什么时候不应该用事件驱动

事件驱动不是所有场景的最优解。以下是明确不适合的场景：

| 场景 | 原因 | 更好的选择 |
|------|------|---------|
| 用户登录 / 查询余额 | 用户需要即时响应，容不得异步延迟 | 同步 REST API |
| 简单 CRUD（博客、配置管理） | 引入 Broker 和消费者的复杂度完全不值得 | 传统分层架构 |
| 强一致性场景（银行转账） | 最终一致性不满足业务要求 | 分布式锁 + 2PC（同一数据库） |
| 小团队 / 单体应用 | 运维 Kafka 的成本高于收益 | 同步调用 + 异步任务队列（Celery） |
| 需要即时反馈的操作 | 异步处理无法在同一请求内返回结果 | 同步 RPC + 状态轮询 |
| 调试资源匮乏的团队 | 事件链追踪困难，没有工具支撑会严重降低开发效率 | 引入事件驱动前先投资可观测性工具 |

**决策规则：** 如果你能画出一个简单的请求/响应时序图，就用同步调用。只有当服务之间的解耦价值明显大于引入的复杂度时，才引入事件驱动。

### 7.2 调试技巧：Correlation ID 跨事件追踪

事件驱动系统的最大调试挑战是：一个用户操作会触发跨多个服务、多个事件的链式反应，传统的调用栈无法追踪。

**Correlation ID** 是解决方案的核心：在用户的原始请求中生成一个唯一 ID，并在整个事件链中传递下去。

```python
# Correlation ID：从请求入口到所有下游事件的完整追踪链

import logging
import contextvars

# 使用 ContextVar 在异步环境中传递 Correlation ID（线程安全）
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="unknown"
)


# 1. 在 API 入口层设置 Correlation ID
class CorrelationIdMiddleware:
    """FastAPI 中间件：从请求头读取或生成 Correlation ID"""
    async def __call__(self, request, call_next):
        # 优先使用客户端传入的，方便前端追踪
        corr_id = request.headers.get("X-Correlation-ID") or generate_uuid()
        correlation_id_var.set(corr_id)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = corr_id   # 回传给客户端
        return response


# 2. 结构化日志：每条日志自动带上 Correlation ID
class CorrelatedLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def info(self, msg: str, **extra):
        self._logger.info(msg, extra={
            "correlation_id": correlation_id_var.get(),
            **extra
        })

    def error(self, msg: str, **extra):
        self._logger.error(msg, extra={
            "correlation_id": correlation_id_var.get(),
            **extra
        }, exc_info=True)


# 3. 事件发布时自动附加 Correlation ID
class CorrelatedEventPublisher:
    def __init__(self, broker):
        self.broker = broker

    def publish(self, topic: str, event: dict):
        # 从上下文自动注入 Correlation ID
        enriched_event = {
            **event,
            "correlation_id": correlation_id_var.get(),
            "published_at": utcnow_iso()
        }
        self.broker.publish(topic, enriched_event)


# 4. 消费者恢复 Correlation ID 上下文
class CorrelatedEventConsumer:
    def consume(self, raw_event: dict):
        # 从事件中恢复 Correlation ID（使日志自动关联）
        correlation_id = raw_event.get("correlation_id", "no-correlation")
        correlation_id_var.set(correlation_id)

        # 后续的所有日志都会带上这个 Correlation ID
        logger.info(f"Processing event: {raw_event['event_type']}")
        self.process(raw_event)


# 5. 日志查询示例（使用结构化日志工具如 ELK、Loki）：
# 查询某个请求链路的完整日志：
#   SELECT * FROM logs WHERE correlation_id = 'req-abc123' ORDER BY timestamp
# 输出：
#   10:30:00.001 [OrderService]      OrderPlaced published        correlation_id=req-abc123
#   10:30:00.050 [InventoryService]  InventoryReserved published  correlation_id=req-abc123
#   10:30:00.120 [PaymentService]    PaymentCharged published     correlation_id=req-abc123
#   10:30:00.180 [NotificationSvc]   Email sent to user-789       correlation_id=req-abc123


# 6. Causation ID：更细粒度的因果追踪
# 除了 Correlation ID（链路），还可以用 Causation ID（因果）：
# - correlation_id：始终是用户原始请求 ID（整条链路不变）
# - causation_id：触发当前事件的上一个事件 ID（局部因果）

def publish_with_causation(publisher, topic: str, event: dict, caused_by_event_id: str = None):
    event_with_causation = {
        **event,
        "correlation_id": correlation_id_var.get(),  # 整链不变
        "causation_id": caused_by_event_id            # 直接原因
    }
    publisher.publish(topic, event_with_causation)

# 通过 causation_id 可以构建事件树（而非链），用于复杂的并行事件流追踪
```

### 7.3 生产环境事件驱动的运维清单

```
可观测性（没有它就是盲飞）：
  ✓ 结构化日志（JSON 格式，含 correlation_id、event_id）
  ✓ 分布式追踪（Jaeger / Zipkin，跨服务 trace）
  ✓ 消费者 Lag 监控（Kafka Consumer Group Lag，告警阈值 > 1000）
  ✓ 死信队列（DLQ）告警（有消息进 DLQ 立即通知 on-call）
  ✓ 事件 Schema 注册表（Schema Registry，防止格式不兼容）

可靠性：
  ✓ 消费者幂等（processed_events 表或 Redis SET NX）
  ✓ 重试策略（指数退避，最大重试 5 次后转 DLQ）
  ✓ 消费者健康检查（Liveness Probe 检测消费者是否卡住）
  ✓ Saga 状态持久化（服务重启不丢失 Saga 进度）

容量规划：
  ✓ Topic 分区数规划（分区数决定最大并行消费者数）
  ✓ 消息保留策略（Kafka 默认 7 天，根据业务需求调整）
  ✓ 快照策略（Event Sourcing 场景，防止无限增长的事件日志）
```

---

## Key Architect Takeaways

- 事件驱动引入的复杂度是真实的成本：调试困难、最终一致性、运维 Broker——只有当解耦价值超过这些成本时才值得
- Correlation ID 是事件驱动系统的"神经系统"：没有它，生产问题排查时间会成倍增加
- 死信队列（DLQ）是最后的安全网：消费失败的事件必须被捕获，不能静默丢弃
- 消费者 Lag 是最重要的业务指标：Lag 持续增长意味着消费能力跟不上生产速度，是系统过载的早期信号
- 在引入事件驱动之前，先投资可观测性基础设施：日志聚合、分布式追踪、监控告警——没有这些，事件驱动是噩梦
