# 消息队列与异步通信（Messaging）

同步调用让系统强耦合——调用方必须等待被调用方响应。消息队列将"发送"和"处理"解耦，是构建弹性、可扩展系统的核心基础设施。

---

## 1. 同步 vs 异步

### 1.1 同步调用的问题

```
用户请求
    ↓
订单服务（等待...）
    ↓ HTTP调用（等待...）
库存服务（等待...）
    ↓ HTTP调用（等待...）
邮件服务（等待...）
    ↓ SMTP（等待...）
用户收到响应（2.5秒后）
```

**问题：**
- 链条上任何一个服务超时，整个请求失败
- 用户要等所有后续操作完成才能收到响应
- 邮件服务宕机 → 用户无法下单（本不应该这样）

### 1.2 异步消息的解法

```
用户请求
    ↓
订单服务（创建订单 + 发消息）→ 立即响应给用户（< 100ms）
    ↓ 发布消息（非阻塞）
消息队列
    ↓             ↓
库存服务        邮件服务
（异步处理）    （异步处理）
```

| 维度 | 同步（HTTP调用） | 异步（消息队列） |
|------|--------------|--------------|
| 响应时间 | 等所有处理完成 | 仅等消息入队（极快） |
| 耦合性 | 调用方必须知道被调用方地址 | 只需知道消息格式 |
| 容错性 | 被调用方宕机 → 调用方失败 | 消息在队列中积压，服务恢复后继续处理 |
| 一致性 | 强一致性（事务） | 最终一致性 |
| 调试难度 | 简单（调用栈清晰） | 复杂（需要 Correlation ID 串联） |
| 适用场景 | 需要立即返回结果的操作 | 后台任务、通知、耗时操作 |

---

## 2. 核心概念

### 2.1 消息模式对比

| 模式 | 描述 | 典型工具 | 适用场景 |
|------|------|---------|---------|
| 点对点（P2P）队列 | 一条消息只被一个消费者处理 | RabbitMQ Queue, SQS | 任务分发，负载均衡 |
| 发布/订阅（Pub/Sub） | 一条消息广播给所有订阅者 | Kafka Topic, Redis Pub/Sub | 事件通知，多消费者 |
| 请求/回复（RPC over MQ） | 通过消息队列模拟同步调用 | RabbitMQ Direct Reply-To | 跨服务查询 |

### 2.2 消息投递语义

这是消息系统最重要的概念之一：

| 语义 | 含义 | 实现方式 | 风险 |
|------|------|---------|------|
| At-most-once（最多一次） | 可能丢消息，但绝不重复 | 发送后不确认，失败不重试 | 消息丢失 |
| At-least-once（至少一次） | 不会丢消息，但可能重复 | 处理后才 ACK，失败则重新投递 | 消息重复（需要幂等消费者） |
| Exactly-once（精确一次） | 不丢不重 | 分布式事务或幂等性机制 | 复杂，性能开销大 |

**实践选择：** 绝大多数系统选择 **At-least-once + 幂等消费者**，因为：
- Exactly-once 实现代价高昂
- 幂等消费者相对容易实现
- At-most-once 在业务系统中几乎不可接受（可以丢消息）

---

## 3. RabbitMQ 深度解析

### 3.1 核心概念

```
Producer → Exchange → Queue → Consumer
                ↑
          Routing Key + Binding
```

- **Exchange**：消息路由器，根据 Routing Key 决定消息去哪个队列
- **Queue**：消息的暂存区
- **Binding**：Exchange 和 Queue 之间的路由规则

### 3.2 Exchange 类型

| 类型 | 路由规则 | 适用场景 |
|------|---------|---------|
| Direct | Routing Key 完全匹配 | 点对点，任务分发 |
| Fanout | 忽略 Routing Key，广播给所有绑定队列 | 事件通知，日志广播 |
| Topic | Routing Key 通配符匹配（`*` 匹配单词，`#` 匹配多词） | 灵活路由 |
| Headers | 根据消息 Headers 匹配 | 复杂路由条件 |

### 3.3 Python 示例（pika 库）

```python
import pika
import json

# 生产者：发布订单创建事件
def publish_order_created(order_id: int, user_id: int, total: float):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost')
    )
    channel = connection.channel()

    # 声明 Exchange（幂等操作）
    channel.exchange_declare(
        exchange='shopflow',
        exchange_type='topic',
        durable=True  # 重启后不丢失
    )

    message = {
        "event_type": "order.created",
        "order_id": order_id,
        "user_id": user_id,
        "total": total
    }

    channel.basic_publish(
        exchange='shopflow',
        routing_key='order.created',  # Topic Exchange 路由键
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # 消息持久化（重启后不丢失）
            content_type='application/json'
        )
    )
    connection.close()


# 消费者：库存服务订阅订单创建事件
def start_inventory_consumer():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost')
    )
    channel = connection.channel()

    # 声明队列（durable=True 持久化，重启后不丢失队列元数据）
    channel.queue_declare(queue='inventory.order-created', durable=True)

    # 绑定：监听 order.* 的所有事件
    channel.queue_bind(
        exchange='shopflow',
        queue='inventory.order-created',
        routing_key='order.*'
    )

    # prefetch_count=1：一次只处理一条消息，处理完再取下一条
    channel.basic_qos(prefetch_count=1)

    def handle_message(ch, method, properties, body):
        message = json.loads(body)
        try:
            deduct_inventory(message["order_id"])
            # 手动 ACK：处理成功后才确认，RabbitMQ 才会删除消息
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            # NACK + requeue=True：处理失败，消息重新入队
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    channel.basic_consume(
        queue='inventory.order-created',
        on_message_callback=handle_message
    )
    channel.start_consuming()  # 阻塞，持续监听
```

### 3.4 死信队列（Dead Letter Queue）

消费多次失败的消息不能无限重试，需要送入死信队列人工处理：

```python
# 声明队列时指定死信 Exchange
channel.queue_declare(
    queue='inventory.order-created',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'shopflow.dlx',  # 死信Exchange
        'x-max-retries': 3                          # 最多重试3次
    }
)

# 死信队列：人工检查、告警
channel.queue_declare(queue='dead-letter', durable=True)
channel.queue_bind(
    exchange='shopflow.dlx',
    queue='dead-letter',
    routing_key='#'  # 接收所有死信
)
```

---

## 4. Kafka 深度解析

### 4.1 Kafka 的核心思想

Kafka 不是传统意义的消息队列，而是**分布式提交日志（Distributed Commit Log）**。

关键区别：
- RabbitMQ：消息被消费后**删除**
- Kafka：消息**保留**（默认7天），消费者用 offset 记录自己读到哪里

```
Topic: order-events
    ├── Partition 0: [msg1, msg2, msg3, msg4, ...]
    ├── Partition 1: [msg1, msg2, msg3, ...]
    └── Partition 2: [msg1, msg2, ...]
                                   ↑
                              Consumer offset（消费者自己记录位置）
```

### 4.2 核心概念

| 概念 | 说明 |
|------|------|
| Topic | 消息分类（类似数据库的表） |
| Partition | Topic 的物理分片，是并行的单位 |
| Offset | 消息在 Partition 中的位置，消费者自己维护 |
| Consumer Group | 一组消费者共同消费一个 Topic，每个 Partition 只分配给组内一个消费者 |
| Broker | Kafka 服务节点 |
| Replication Factor | 每个 Partition 的副本数（容错） |

### 4.3 消费者组与分区分配

```
Topic: order-events (3 Partitions)

Consumer Group A（库存服务，3个实例）：
    Consumer A1 → Partition 0
    Consumer A2 → Partition 1
    Consumer A3 → Partition 2
    （充分并行，每个实例处理一个分区）

Consumer Group B（邮件服务，1个实例）：
    Consumer B1 → Partition 0, 1, 2
    （一个实例处理所有分区，但同一 Group B 里消息只被处理一次）
```

**架构师关键点：** Partition 数量决定了最大并行度。如果 Consumer 数量 > Partition 数量，多余的 Consumer 空闲等待。

### 4.4 Python 示例（kafka-python 库）

```python
from kafka import KafkaProducer, KafkaConsumer
import json

# 生产者
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    # 幂等性生产者：防止网络重试导致重复消息
    enable_idempotence=True,
    acks='all'  # 等待所有副本确认
)

producer.send(
    topic='order-events',
    key=b'order-123',  # 相同 key 总是发到同一 Partition（保证顺序）
    value={
        "event_type": "order.created",
        "order_id": 123,
        "user_id": 456
    }
)
producer.flush()

# 消费者
consumer = KafkaConsumer(
    'order-events',
    bootstrap_servers=['localhost:9092'],
    group_id='inventory-service',          # 消费者组ID
    auto_offset_reset='earliest',           # 从最早的消息开始
    enable_auto_commit=False,               # 手动提交 offset（更安全）
    value_deserializer=lambda b: json.loads(b.decode('utf-8'))
)

for message in consumer:
    try:
        handle_order_event(message.value)
        # 处理成功后手动提交 offset
        consumer.commit()
    except Exception as e:
        # 不提交 offset，下次重新消费这条消息
        print(f"Processing failed: {e}")
```

---

## 5. RabbitMQ vs Kafka 选型

| 维度 | RabbitMQ | Kafka |
|------|---------|-------|
| 消息模型 | 消费后删除（push-based） | 保留日志，消费者拉取（pull-based） |
| 吞吐量 | 中等（~5万/秒） | 极高（~百万/秒） |
| 消息保留 | 消费后删除 | 可配置（默认7天，可永久保留） |
| 消息顺序 | 单队列内有序 | 单 Partition 内有序 |
| 路由灵活性 | 高（4种Exchange类型） | 低（Topic + Partition） |
| 延迟 | 极低（< 1ms） | 较低（单位：ms） |
| 多消费者重放 | 不支持（消息删除后无法重放） | 支持（改变 offset 即可重放） |
| 运维复杂度 | 中等 | 高（依赖 ZooKeeper/KRaft） |
| 适用场景 | 任务队列、RPC、复杂路由 | 事件流、日志、大数据管道、事件溯源 |

### ADR 模板：为什么 ShopFlow 第一阶段选 RabbitMQ

```
背景：Sprint 7 需要将下单后的"扣库存"和"发邮件"改为异步处理

选择 RabbitMQ，理由：
1. 团队规模小，运维 Kafka 的 ZooKeeper 集群成本高
2. 消息量级（日订单千级）远未达到 Kafka 的适用规模
3. 不需要消息回放（邮件已发就已发，不需要重放）
4. RabbitMQ 的 Topic Exchange 满足灵活路由需求

后续迁移信号：
- 日消息量 > 100万时考虑 Kafka
- 需要事件溯源或消息回放时考虑 Kafka
```

---

## 6. 幂等消费者设计

At-least-once 投递意味着**消息可能被重复投递**，消费者必须能安全地处理重复消息。

### 6.1 为什么会重复投递

```
消费者处理消息 → 处理成功 → 网络故障 → ACK 未送达 → RabbitMQ 重新投递
                                              ↑
                                    同一条消息被消费两次！
```

### 6.2 幂等消费者实现

**方案1：数据库唯一约束**

```python
def process_order_created(message: dict):
    order_id = message["order_id"]
    event_id = message["event_id"]  # 每条消息有唯一ID

    # 用唯一约束防止重复处理
    # 如果 event_id 已存在，INSERT 失败，但不抛异常
    try:
        db.execute(
            "INSERT INTO processed_events (event_id, processed_at) VALUES (?, NOW())",
            event_id
        )
    except UniqueConstraintViolation:
        # 已经处理过这条消息，直接返回
        return

    # 真正的业务处理
    deduct_inventory(order_id)
```

**方案2：Redis 去重（适合高吞吐）**

```python
def process_order_created(message: dict):
    event_id = message["event_id"]
    dedup_key = f"processed_event:{event_id}"

    # SET NX（Not eXists）+ 过期时间
    # 如果 key 已存在，SET NX 返回 False → 说明已处理
    is_new = redis.set(dedup_key, "1", nx=True, ex=86400)  # 24小时
    if not is_new:
        return  # 重复消息，跳过

    # 处理业务
    deduct_inventory(message["order_id"])
```

**方案3：乐观锁（基于版本号）**

```python
def process_inventory_deduction(order_id: int, expected_version: int):
    # 只有当版本号匹配时才更新（避免并发问题）
    rows_affected = db.execute(
        """UPDATE inventory
           SET stock = stock - 1, version = version + 1
           WHERE order_id = ? AND version = ?""",
        order_id, expected_version
    )
    if rows_affected == 0:
        # 版本不匹配 → 已被处理过，或被其他进程处理
        return
```

---

## 7. 消息队列高级模式

### 7.1 延迟消息（Delayed Message）

```python
# RabbitMQ：通过 TTL + 死信队列实现延迟
# 场景：下单后30分钟未支付，自动取消

def schedule_order_cancellation(order_id: int, delay_ms: int = 1800000):
    channel.queue_declare(
        queue=f'delay.{delay_ms}',
        durable=True,
        arguments={
            'x-message-ttl': delay_ms,              # 消息在这里停留N毫秒
            'x-dead-letter-exchange': 'shopflow',   # 超时后送到实际处理Exchange
            'x-dead-letter-routing-key': 'order.timeout'
        }
    )
    channel.basic_publish(
        exchange='',
        routing_key=f'delay.{delay_ms}',
        body=json.dumps({"order_id": order_id})
    )
```

### 7.2 消息优先级

```python
# 声明带优先级的队列（0-255，数字越大优先级越高）
channel.queue_declare(
    queue='tasks',
    durable=True,
    arguments={'x-max-priority': 10}
)

# 发送高优先级消息（VIP用户订单）
channel.basic_publish(
    exchange='',
    routing_key='tasks',
    body=json.dumps({"type": "vip_order", "order_id": 123}),
    properties=pika.BasicProperties(priority=8)
)
```

### 7.3 Outbox 模式（保证事务性消息）

问题：如何保证"写数据库"和"发消息"的原子性？

```python
# 反模式：两步操作可能部分失败
def create_order(order_data: dict):
    db.execute("INSERT INTO orders ...")  # 成功
    mq.publish("order.created", ...)     # 失败！订单创建了，但消息没发出

# 正确：Outbox 模式
def create_order(order_data: dict):
    with db.transaction():
        # 在同一个事务里写订单和消息
        order_id = db.execute("INSERT INTO orders ...")
        db.execute(
            "INSERT INTO outbox (event_type, payload, created_at) VALUES (?, ?, NOW())",
            "order.created",
            json.dumps({"order_id": order_id})
        )
        # 事务提交：订单和outbox记录同时成功或同时回滚

# 独立的Outbox轮询进程（或CDC）
def outbox_publisher():
    while True:
        pending = db.fetchall(
            "SELECT * FROM outbox WHERE published = FALSE ORDER BY created_at LIMIT 100"
        )
        for event in pending:
            mq.publish(event["event_type"], event["payload"])
            db.execute(
                "UPDATE outbox SET published = TRUE WHERE id = ?",
                event["id"]
            )
        time.sleep(0.1)
```

---

## 8. 背压（Backpressure）处理

当消费者处理速度跟不上生产者时，如何防止系统崩溃：

```python
# RabbitMQ：prefetch_count 限制在途消息数
channel.basic_qos(prefetch_count=10)  # 消费者最多同时处理10条

# Kafka：通过 pause/resume 控制拉取速度
consumer = KafkaConsumer(...)

for message in consumer:
    if is_overloaded():  # 系统负载高
        consumer.pause(consumer.assignment())  # 暂停拉取
        time.sleep(1)
        consumer.resume(consumer.assignment())  # 恢复拉取
    process(message)
```

---

## Key Architect Takeaways

- **At-least-once + 幂等消费者是标准组合**：Exactly-once 代价太高，而重复处理通过幂等设计可以安全忽略
- **RabbitMQ 适合任务队列，Kafka 适合事件流**：消息量 < 100万/天用 RabbitMQ；需要消息回放、事件溯源用 Kafka
- **Outbox 模式解决分布式原子性**：在同一个DB事务里写业务数据和待发消息，避免"写了DB但消息没发出"的半成功状态
- **死信队列是必配组件**：没有死信队列的消息系统是不完整的——失败消息需要有地方"落地"等待人工处理
- **prefetch_count 是消费者保护阀**：不设置 prefetch 的消费者会被大量 push 消息撑死；始终设置合理的 prefetch_count
