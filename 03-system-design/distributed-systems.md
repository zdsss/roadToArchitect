# 分布式系统（Distributed Systems）

分布式系统的本质是：多台机器通过网络协作，对外表现为一个整体。网络的不可靠性使得分布式系统面临单机系统从未遇到的挑战：部分失败、时钟漂移、网络分区。理解这些挑战是架构师的核心能力之一。

---

## 1. 分布式计算的 8 个谬误

1990年代，Sun 公司工程师总结了新手常犯的8个认知错误：

| 谬误 | 现实 |
|------|------|
| 网络是可靠的 | 数据包会丢失、延迟、乱序 |
| 延迟为零 | 同机房~1ms，跨城市~50ms，跨洲~200ms |
| 带宽无限 | 带宽有上限，大数据传输是瓶颈 |
| 网络是安全的 | 中间人攻击、嗅探无处不在 |
| 网络拓扑不变 | 节点上线、下线、切换随时发生 |
| 只有一个管理员 | 分布式团队，配置不一致 |
| 传输成本为零 | 序列化、网络 I/O 都有成本 |
| 网络是同构的 | 混合云、多地域部署，协议版本各异 |

> **架构师意义：** 每一个"谬误"对应一类架构决策。例如"网络不可靠" → 需要重试机制、幂等设计；"延迟不为零" → 需要异步处理、缓存。

---

## 2. CAP 定理

### 2.1 三角不可能

**一致性（Consistency）、可用性（Availability）、分区容忍（Partition Tolerance）**，在网络分区发生时，最多只能同时保证两个。

```
         一致性（C）
           /\
          /  \
         /    \
        /  ？  \
       /________\
可用性（A）       分区容忍（P）

网络分区（P）在分布式系统中不可避免
→ 真正的选择是：CP（牺牲可用性）还是 AP（牺牲一致性）
```

### 2.2 网络分区时的抉择

```
场景：集群有节点 A 和节点 B，网络故障导致 A 和 B 无法通信

CP 系统的选择（如 ZooKeeper）：
    节点 A：网络分区了，我不知道节点 B 的状态
    → 拒绝服务（返回 503），保证不返回过时数据
    代价：可用性降低

AP 系统的选择（如 Cassandra）：
    节点 A：网络分区了，但我还有数据
    → 继续服务，可能返回过时数据
    代价：数据可能不是最新的
```

| 系统 | 类型 | 牺牲什么 | 适用场景 |
|------|------|---------|---------|
| ZooKeeper, etcd | CP | 网络分区时停止服务 | 分布式配置、领导选举 |
| PostgreSQL, MySQL | CP | 主节点宕机时需要人工切换 | 金融、订单 |
| Cassandra, DynamoDB | AP | 短期内不同节点数据可能不一致 | 用户行为、社交动态 |
| Redis（默认配置） | AP | 主从复制可能丢失少量数据 | 缓存 |

### 2.3 PACELC 定理（CAP 的扩展）

CAP 定理只描述了分区发生时的权衡，忽略了正常运行时的权衡。PACELC 扩展：

```
If Partition → choose between Availability and Consistency
Else（正常运行）→ choose between Latency and Consistency

PA/EL：Cassandra — 分区时选A，正常时优化延迟（牺牲一致性）
PC/EC：ZooKeeper — 分区时选C，正常时也保证一致性（延迟较高）
PA/EC：MongoDB（可配置）— 分区时选A，正常时可选强一致
```

---

## 3. 一致性模型

分布式系统中的"一致性"不是非黑即白，有多个强度级别：

| 一致性模型 | 含义 | 实现成本 | 典型应用 |
|---------|------|---------|---------|
| 强一致性（Linearizability） | 读总是看到最新写入，如同单机 | 高（需要共识协议） | 银行账户、库存 |
| 顺序一致性（Sequential） | 所有操作看起来像按某个全局顺序执行 | 较高 | 分布式锁 |
| 因果一致性（Causal） | 有因果关系的操作保序，无关操作可乱序 | 中 | 聊天消息顺序 |
| 读己之写（Read-your-writes） | 用户总是看到自己写入的最新数据 | 低 | 用户资料更新 |
| 最终一致性（Eventual） | 没有新写入的情况下，最终所有节点数据相同 | 最低 | DNS、社交动态 |

**读己之写的实现（常见场景：用户更新头像）：**
```python
def update_user_profile(user_id: int, data: dict):
    # 写入主库
    primary_db.execute("UPDATE users SET avatar_url=$1 WHERE id=$2",
                       data["avatar_url"], user_id)

    # 在用户的 Session 里记录"最近写入时间"
    session["last_write_at"] = time.time()

def get_user_profile(user_id: int, session: dict):
    # 如果用户最近有写入操作，强制读主库（保证读己之写）
    if time.time() - session.get("last_write_at", 0) < 5:
        return primary_db.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
    # 否则读副本（分担主库压力）
    return replica_db.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
```

---

## 4. 分布式事务

### 4.1 为什么两阶段提交（2PC）在微服务中不可用

2PC 是传统数据库的分布式事务协议：

```
阶段1（Prepare）：协调者问所有参与者"你准备好了吗？"
    订单服务：是 ✓
    库存服务：是 ✓
    支付服务：是 ✓

阶段2（Commit）：所有人都准备好了，协调者发出 Commit
    全部提交 ✓
```

**为什么微服务不用 2PC：**

| 问题 | 说明 |
|------|------|
| 同步阻塞 | 所有参与者在 Prepare 和 Commit 之间持有锁，阻塞时间长 |
| 协调者单点 | 协调者宕机 → 所有参与者永久锁死（无法判断提交还是回滚） |
| 跨服务事务 | 每个微服务有自己的数据库，没有统一的事务管理器 |
| 性能差 | 两次网络往返，所有服务串行等待 |

### 4.2 Saga 模式

Saga 把一个大的分布式事务拆成多个本地事务，每个本地事务有对应的**补偿事务**（回滚操作）。

```
正常流程（Happy Path）：
    T1（订单服务）: 创建订单（status=pending）
    T2（库存服务）: 扣减库存
    T3（支付服务）: 扣款

    全部成功 → 订单完成

失败回滚（Compensating Transactions）：
    T1: 创建订单 ✓
    T2: 扣减库存 ✓
    T3: 扣款 ✗（用户余额不足）
    → 执行补偿事务：
        C2: 恢复库存（反向操作T2）
        C1: 取消订单（反向操作T1）
```

**编排式 Saga（Orchestration-based）— 推荐初学者使用：**

```python
# shop/sagas/place_order_saga.py
class PlaceOrderSaga:
    """
    编排式 Saga：由中央协调者（Saga Orchestrator）管理整个流程
    优点：流程清晰，易于追踪和调试
    缺点：协调者是中心点，所有服务都依赖它
    """
    def __init__(self, order_service, inventory_service, payment_service):
        self.order_svc = order_service
        self.inventory_svc = inventory_service
        self.payment_svc = payment_service

    def execute(self, user_id: int, items: list, payment_method: str) -> dict:
        order_id = None
        inventory_reserved = False

        try:
            # Step 1: 创建订单（本地事务T1）
            order_id = self.order_svc.create_order(user_id, items)
            print(f"[Saga] T1 success: order {order_id} created")

            # Step 2: 预留库存（本地事务T2）
            self.inventory_svc.reserve_items(order_id, items)
            inventory_reserved = True
            print(f"[Saga] T2 success: inventory reserved")

            # Step 3: 支付（本地事务T3）
            self.payment_svc.charge(user_id, order_id, payment_method)
            print(f"[Saga] T3 success: payment charged")

            # 全部成功，确认订单
            self.order_svc.confirm(order_id)
            return {"status": "success", "order_id": order_id}

        except PaymentFailedError as e:
            print(f"[Saga] T3 failed: {e}. Compensating...")
            # 补偿事务：按反序执行
            if inventory_reserved:
                self.inventory_svc.release_items(order_id, items)  # C2
                print(f"[Saga] C2: inventory released")
            if order_id:
                self.order_svc.cancel(order_id)  # C1
                print(f"[Saga] C1: order cancelled")
            return {"status": "failed", "reason": str(e)}

        except InventoryShortageError as e:
            print(f"[Saga] T2 failed: {e}. Compensating...")
            if order_id:
                self.order_svc.cancel(order_id)  # C1
            return {"status": "failed", "reason": str(e)}
```

**协同式 Saga（Choreography-based）— 通过事件驱动：**

```python
# 各服务通过事件自主响应，无中央协调者

# 订单服务：创建订单后发布事件
def create_order(user_id, items):
    order_id = db.insert_order(user_id, items)
    event_bus.publish("OrderCreated", {
        "order_id": order_id,
        "user_id": user_id,
        "items": items
    })

# 库存服务：监听 OrderCreated
def on_order_created(event):
    try:
        reserve_items(event["order_id"], event["items"])
        event_bus.publish("InventoryReserved", {"order_id": event["order_id"]})
    except InventoryShortageError:
        event_bus.publish("InventoryReservationFailed", {"order_id": event["order_id"]})

# 支付服务：监听 InventoryReserved
def on_inventory_reserved(event):
    try:
        charge(event["order_id"])
        event_bus.publish("PaymentProcessed", {"order_id": event["order_id"]})
    except PaymentFailedError:
        event_bus.publish("PaymentFailed", {"order_id": event["order_id"]})

# 库存服务：监听 PaymentFailed，执行补偿
def on_payment_failed(event):
    release_items(event["order_id"])  # 补偿事务：释放库存
    event_bus.publish("InventoryReleased", {"order_id": event["order_id"]})

# 订单服务：监听各种失败事件，取消订单
def on_inventory_reservation_failed(event):
    cancel_order(event["order_id"])

def on_inventory_released(event):
    cancel_order(event["order_id"])
```

**编排 vs 协同对比：**

| 维度 | 编排式（Orchestration） | 协同式（Choreography） |
|------|----------------------|-------------------|
| 控制点 | 中央协调者 | 无中心，各服务自主 |
| 可见性 | 高（流程在一处定义） | 低（流程分散在各事件处理器） |
| 耦合度 | 协调者知道所有服务 | 服务只知道事件，不知道彼此 |
| 调试难度 | 低 | 高（需要 Trace ID 串联） |
| 适合场景 | 流程固定、步骤多 | 服务自治、松耦合优先 |

---

## 5. 分布式 ID 生成

### 5.1 为什么数据库自增 ID 不够用

```
问题1：分布式环境多库多表，各自自增会产生重复 ID
问题2：ID 的大小泄露了业务量（id=42 意味着只有42个订单）
问题3：水平分片后，自增 ID 需要统一管理（性能瓶颈）
```

### 5.2 各方案对比

| 方案 | 唯一性 | 趋势递增 | 信息泄露 | 性能 | 复杂度 |
|------|--------|---------|---------|------|--------|
| 数据库自增 | 单库唯一 | 是 | 高 | 低（单点） | 低 |
| UUID v4 | 全局唯一（概率） | 否（随机） | 无 | 高（本地生成） | 低 |
| Snowflake | 全局唯一 | 趋势递增 | 低 | 高 | 中 |
| ULID | 全局唯一 | 是 | 无 | 高 | 低 |

### 5.3 Snowflake 算法

Twitter 开源的分布式 ID 生成算法，64位整数：

```
0 | 41位时间戳 | 10位机器ID | 12位序列号
  |（毫秒级，可用69年）| （最多1024台机器） | （每毫秒最多4096个）
```

```python
import time
import threading

class SnowflakeIDGenerator:
    EPOCH = 1711411200000  # 自定义起始时间（2024-03-26 00:00:00 UTC ms）
    WORKER_ID_BITS = 10
    SEQUENCE_BITS = 12
    MAX_WORKER_ID = (1 << WORKER_ID_BITS) - 1  # 1023
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1     # 4095
    WORKER_ID_SHIFT = SEQUENCE_BITS             # 12
    TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_ID_BITS  # 22

    def __init__(self, worker_id: int):
        if worker_id < 0 or worker_id > self.MAX_WORKER_ID:
            raise ValueError(f"worker_id must be 0-{self.MAX_WORKER_ID}")
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = threading.Lock()

    def generate(self) -> int:
        with self._lock:
            timestamp = int(time.time() * 1000)  # 当前毫秒时间戳

            if timestamp == self.last_timestamp:
                # 同一毫秒内，序列号自增
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    # 序列号溢出，等待下一毫秒
                    while timestamp <= self.last_timestamp:
                        timestamp = int(time.time() * 1000)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            return (
                ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT) |
                (self.worker_id << self.WORKER_ID_SHIFT) |
                self.sequence
            )

# 使用
generator = SnowflakeIDGenerator(worker_id=1)
order_id = generator.generate()
# 例如：7179048483086336001（趋势递增，数据库索引友好）
```

---

## 6. 共识算法：Raft 直觉解释

Raft 是最易理解的分布式共识算法，用于在多个节点间就某个值达成一致（如：谁是 Leader？日志的顺序是什么？）

### 6.1 节点角色

```
Leader：处理所有写请求，定期发送心跳
Follower：接受 Leader 的命令，响应心跳
Candidate：Leader 心跳超时后，Follower 自动升为 Candidate，发起选举
```

### 6.2 Leader 选举

```
正常状态：
    Leader → [心跳] → Follower A, B, C, D
    所有 Follower 重置超时计时器

Leader 宕机：
    Follower A：超时！Leader 不响应了，我要发起选举
    A → Candidate：给自己投票，向其他节点请求投票
    A → B, C, D: "请给我投票，我的任期号(term)是3"
    B, C, D: "好，我投给你（本任期还没投过票）"
    A 收到 3 票（包括自己）= 超过半数(5/2=2.5，需要3票）
    A → 成为新 Leader
```

**为什么需要奇数节点：**
```
3个节点：允许1个故障（需要2票 > 1.5）
5个节点：允许2个故障（需要3票 > 2.5）
4个节点：允许1个故障（需要3票 > 2），但只比3节点多容忍了0个故障
→ 奇数节点的容错比更高效
```

### 6.3 日志复制

```
客户端写入 → Leader 接收
Leader 将日志条目复制到 Follower
超过半数 Follower 确认 → Leader 提交（Commit）
Leader 告知 Follower 可以提交
→ 所有存活节点的日志最终一致
```

**实际应用：** ZooKeeper（ZAB 协议，类似 Raft）、etcd（Raft）、CockroachDB（Raft）都用这类共识算法保证分布式一致性。

---

## 7. 分布式 ID 与数据分片

### 7.1 一致性哈希（Consistent Hashing）

普通哈希（`hash(key) % N`）的问题：节点数 N 变化时，几乎所有 key 的归属节点都改变 → 大量缓存失效。

```
一致性哈希：将 key 和节点都映射到同一个环上
新增/删除节点时，只影响相邻节点的数据

Hash 环（0 ~ 2^32）：
    Node A: 位置 100
    Node B: 位置 250
    Node C: 位置 350

    Key "product:42" → hash = 180 → 顺时针找最近节点 = Node B
    Key "user:123" → hash = 80 → 顺时针找最近节点 = Node A

    新增 Node D（位置 150）：
    Key "product:42"(180) → 现在归 Node D（150 < 180 < 250）
    只有 Node B 的一部分数据转移到 Node D，其他不受影响
```

---

## Key Architect Takeaways

- **网络分区是事实，不是假设**：分布式系统设计必须从"网络会故障"的前提出发，而不是期望网络永远可靠
- **CAP 的实际选择是 CP vs AP**：P 是必须的，在一致性和可用性之间做选择，取决于业务容忍"读到旧数据"还是"拒绝服务"
- **Saga 是微服务事务的实用解法**：2PC 在微服务中代价太高，Saga（编排式或协同式）通过补偿事务实现最终一致性
- **Snowflake 是分布式 ID 的标准选择**：唯一、趋势递增（对 B-Tree 索引友好）、本地生成（无单点）
- **最终一致性不等于"随时不一致"**：在没有新写入的情况下，最终一致系统会收敛到一致状态。关键是设计补偿机制，让业务能容忍短暂的不一致窗口
