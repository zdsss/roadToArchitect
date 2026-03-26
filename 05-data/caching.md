# 缓存（Caching）

缓存是用"空间"换"时间"的经典权衡。内存访问比磁盘快10万倍，合理使用缓存是系统性能提升最高性价比的手段之一。但缓存也带来了数据一致性、故障场景和复杂度的挑战。

---

## 1. 为什么缓存重要

### 1.1 存储介质速度差异

| 存储类型 | 典型延迟 | 相对速度 |
|---------|---------|---------|
| CPU L1 缓存 | 0.5 ns | 基准 |
| CPU L2 缓存 | 7 ns | 14x |
| 内存（RAM） | 100 ns | 200x |
| NVMe SSD | 100 μs | 200,000x |
| 机械硬盘 | 10 ms | 20,000,000x |
| 网络请求（同机房） | 0.5 ms | 1,000,000x |
| 网络请求（跨城市） | 50 ms | 100,000,000x |

**实践意义：** 从数据库读一条记录需要 5-10ms；从 Redis 读同样的数据需要 < 1ms。在高并发场景下，这个差距决定系统能否撑住。

### 1.2 缓存命中率的影响

```
场景：10,000 QPS，数据库最多承受 1,000 QPS

缓存命中率 90%：
    → 1,000 QPS 需要查数据库 ✅ 刚好能撑住

缓存命中率 95%：
    → 500 QPS 查数据库 ✅ 压力减半

缓存命中率 99%：
    → 100 QPS 查数据库 ✅ 从容不迫
```

---

## 2. 缓存策略

### 2.1 Cache-Aside（旁路缓存）— 最常用

应用代码负责管理缓存。读时先查缓存，未命中再查数据库并回填；写时直接写数据库，使缓存失效（而非更新）。

**读流程：**
```python
def get_product(product_id: int) -> dict:
    cache_key = f"product:{product_id}"

    # 1. 先查缓存
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)  # 缓存命中，直接返回

    # 2. 缓存未命中，查数据库
    product = db.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
    if product is None:
        return None

    # 3. 回填缓存（设置过期时间）
    redis.setex(cache_key, 3600, json.dumps(dict(product)))  # TTL = 1小时
    return dict(product)
```

**写流程（先写DB，再删缓存）：**
```python
def update_product_price(product_id: int, new_price: float):
    # 1. 更新数据库
    db.execute("UPDATE products SET price = $1 WHERE id = $2", new_price, product_id)

    # 2. 删除缓存（而非更新）
    # 为什么删除而不是更新？→ 避免并发场景下缓存与DB不一致
    redis.delete(f"product:{product_id}")
```

> **为什么先写 DB 再删缓存？** 如果先删缓存再写 DB：
> 1. 删缓存 → 另一个请求读取（缓存未命中，查旧数据库，回填旧值）→ 写 DB 完成
> 2. 结果：缓存里存了旧值，但 DB 是新值 → 不一致

### 2.2 Read-Through（透明读缓存）

缓存层自动处理缓存未命中，应用代码只与缓存交互：

```python
# 应用代码：只管读缓存
product = cache.get(f"product:{product_id}")  # 缓存未命中时自动从DB加载

# 缓存层内部（封装了数据加载逻辑）
class ProductCache:
    def get(self, product_id: int):
        cached = redis.get(f"product:{product_id}")
        if cached:
            return json.loads(cached)
        # 自动从数据库加载并回填
        product = db.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
        redis.setex(f"product:{product_id}", 3600, json.dumps(dict(product)))
        return dict(product)
```

**对比 Cache-Aside：** Read-Through 封装了加载逻辑（代码更简洁），但灵活性较低。

### 2.3 Write-Through（同步写穿）

写操作同时更新缓存和数据库（由缓存层完成）：

```python
def update_product(product_id: int, data: dict):
    # 同时更新缓存和 DB
    db.execute("UPDATE products SET name=$1, price=$2 WHERE id=$3",
               data["name"], data["price"], product_id)
    redis.setex(f"product:{product_id}", 3600, json.dumps(data))
```

**优点：** 缓存始终是最新数据，读取无需担心过时。
**缺点：** 每次写操作都有两次 I/O（DB + 缓存），写入延迟稍高。

### 2.4 Write-Behind（异步写回）

写操作先更新缓存，异步批量写入数据库：

```python
def update_product_write_behind(product_id: int, data: dict):
    # 只更新缓存，立即返回
    redis.setex(f"product:{product_id}", 3600, json.dumps(data))
    # 将写入任务加入队列，异步批量写 DB
    write_queue.push({"op": "update", "id": product_id, "data": data})

# 后台 worker：批量写入 DB
def flush_write_queue():
    batch = write_queue.pop_many(100)
    db.executemany("UPDATE products SET ...", batch)
```

**优点：** 极低写入延迟（只写内存）。
**风险：** 如果缓存服务在批量写入前崩溃，数据丢失。**仅适用于可接受少量数据丢失的场景**（如页面浏览计数、非关键状态）。

### 2.5 四种策略对比

| 策略 | 一致性 | 写入性能 | 实现复杂度 | 适用场景 |
|------|--------|---------|----------|---------|
| Cache-Aside | 弱（删缓存后短暂不一致） | 好 | 中 | 通用场景，最常用 |
| Read-Through | 中 | 中 | 低（代码更简洁） | 读多写少 |
| Write-Through | 强 | 较慢（双写） | 中 | 读多、一致性要求高 |
| Write-Behind | 弱（有丢失风险） | 极快 | 高 | 可接受少量丢失的高频写入 |

---

## 3. 缓存三大问题

### 3.1 缓存穿透（Cache Penetration）

**问题：** 查询**根本不存在**的数据。缓存不存在 → 每次都查数据库 → 数据库也查不到 → 缓存无法回填 → 循环穿透。

```
攻击场景：恶意用户用不存在的 id=-1, id=-2, ... 不断请求
→ 全部缓存未命中 → 全打到数据库 → 数据库被打爆
```

**解决方案1：缓存空值**
```python
def get_product(product_id: int):
    cache_key = f"product:{product_id}"
    cached = redis.get(cache_key)

    if cached is not None:  # 注意：空值 "" 也算命中
        if cached == "":
            return None  # 缓存了"不存在"这个结论
        return json.loads(cached)

    product = db.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
    if product is None:
        redis.setex(cache_key, 300, "")  # 缓存"不存在"，TTL短一些（5分钟）
        return None

    redis.setex(cache_key, 3600, json.dumps(dict(product)))
    return dict(product)
```

**解决方案2：布隆过滤器（Bloom Filter）**

布隆过滤器是一种空间极省的概率性数据结构：
- "不存在"：100% 准确（可以拦截不存在的 key）
- "存在"：可能误判（False Positive，但比例可控）

```python
from pybloom_live import BloomFilter

# 初始化：用所有合法 product_id 填充布隆过滤器
bloom = BloomFilter(capacity=1000000, error_rate=0.01)  # 容量100万，误判率1%
for product_id in db.fetchall("SELECT id FROM products"):
    bloom.add(str(product_id))

def get_product(product_id: int):
    # 布隆过滤器检查：如果"不存在"，直接返回（100%准确）
    if str(product_id) not in bloom:
        return None  # 绝对不存在，不查缓存也不查DB

    # 通过布隆过滤器后，按正常流程处理
    ...

# 新增商品时，同步更新布隆过滤器
def add_product(product: dict):
    db.execute("INSERT INTO products ...")
    bloom.add(str(product["id"]))
```

### 3.2 缓存击穿（Cache Breakdown）

**问题：** 一个**热点 Key** 过期的瞬间，大量并发请求同时缓存未命中，全部打到数据库（"惊群效应"）。

```
热门商品的缓存过期
→ 10,000 个并发请求同时发现缓存未命中
→ 10,000 个请求同时查数据库
→ 数据库被压垮
```

**解决方案1：互斥锁（Mutex Lock）**
```python
import redis
import time

def get_hot_product(product_id: int):
    cache_key = f"product:{product_id}"
    lock_key = f"lock:product:{product_id}"

    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # 缓存未命中，尝试获取分布式锁
    # SET NX（只有不存在时才设置）+ EX（锁的过期时间，防止死锁）
    acquired = redis.set(lock_key, "1", nx=True, ex=5)

    if acquired:
        try:
            # 获得锁，查数据库
            product = db.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
            redis.setex(cache_key, 3600, json.dumps(dict(product)))
            return dict(product)
        finally:
            redis.delete(lock_key)  # 释放锁
    else:
        # 没获得锁，等待后重试（其他请求在更新缓存）
        time.sleep(0.05)
        cached = redis.get(cache_key)
        return json.loads(cached) if cached else get_hot_product(product_id)
```

**解决方案2：永不过期 + 异步更新**
```python
def get_hot_product_no_expire(product_id: int):
    cache_key = f"product:{product_id}"
    data = redis.get(cache_key)

    if data:
        result = json.loads(data)
        # 检查逻辑过期时间（存在数据里，不是 Redis TTL）
        if result["_expire_at"] < time.time():
            # 数据"逻辑上过期"了，异步更新，但仍返回旧数据
            asyncio.create_task(refresh_product_cache(product_id))
        return result["data"]

    # 完全没有缓存（冷启动），同步查询
    return sync_load_and_cache(product_id)
```

### 3.3 缓存雪崩（Cache Avalanche）

**问题：** 大量 Key **同时过期**，或缓存服务宕机，导致所有请求涌向数据库。

```
场景1（同时过期）：
    促销活动结束 → 所有商品缓存同时设置相同TTL → 同时过期
    → 大量请求同时打到数据库 → 崩溃

场景2（缓存宕机）：
    Redis 主节点宕机 → 所有请求失去缓存 → 全打数据库 → 数据库崩溃
```

**解决方案1：TTL 随机抖动**
```python
import random

def cache_product(product_id: int, product: dict):
    base_ttl = 3600  # 基础1小时
    jitter = random.randint(0, 600)  # 随机0-10分钟抖动
    redis.setex(f"product:{product_id}", base_ttl + jitter, json.dumps(product))
    # 不同商品的缓存过期时间分散，避免同时失效
```

**解决方案2：多级缓存**
```python
import functools

# 本地内存缓存（极快，无网络开销）
local_cache = {}  # 或使用 lru_cache / cachetools

def get_product_multilevel(product_id: int):
    cache_key = f"product:{product_id}"

    # 第1级：本地内存缓存（TTL极短，30秒）
    local_entry = local_cache.get(cache_key)
    if local_entry and local_entry["expire"] > time.time():
        return local_entry["data"]

    # 第2级：Redis 分布式缓存（TTL 1小时）
    redis_data = redis.get(cache_key)
    if redis_data:
        data = json.loads(redis_data)
        # 回填本地缓存
        local_cache[cache_key] = {"data": data, "expire": time.time() + 30}
        return data

    # 第3级：数据库
    product = db.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
    if product:
        data = dict(product)
        redis.setex(cache_key, 3600 + random.randint(0, 600), json.dumps(data))
        local_cache[cache_key] = {"data": data, "expire": time.time() + 30}
        return data

    return None
```

**解决方案3：缓存服务高可用（Redis 集群 / 哨兵）**

```
Redis Sentinel（哨兵模式）：
    Master ← 监控 → Sentinel1
                  → Sentinel2
                  → Sentinel3
    Master 宕机 → Sentinel 投票 → 自动选出新 Master

Redis Cluster（集群模式）：
    16384 个槽分布到多个节点
    每个节点有副本（Master-Replica）
    任意一个节点宕机，其副本接管
```

> **Key Architect Takeaways：**
> - 缓存穿透用布隆过滤器（大量随机 ID 攻击）或缓存空值（少量不存在 key）
> - 缓存击穿用互斥锁控制重建（热点 key 过期瞬间的惊群）
> - 缓存雪崩用 TTL 抖动分散过期时间 + 多级缓存作兜底
> - Redis 单点是致命的——生产环境必须使用 Sentinel 或 Cluster

---

## 4. Redis 数据结构与使用场景

### 4.1 String — 计数器、分布式锁

```python
# 计数器：原子自增
redis.incr("page_views:home")           # 首页访问次数
redis.incrby("cart_items:user-123", 3)  # 购物车增加3件

# 分布式锁（SETNX）
acquired = redis.set("lock:order-payment", "1", nx=True, ex=30)
if acquired:
    try:
        process_payment()
    finally:
        redis.delete("lock:order-payment")
```

### 4.2 Hash — 对象存储

```python
# 存储用户 Session
redis.hset("session:abc123", mapping={
    "user_id": "456",
    "role": "admin",
    "login_at": "2026-03-26T10:00:00Z"
})
redis.expire("session:abc123", 86400)  # 24小时过期

# 读取单个字段（比反序列化整个 JSON 快）
user_id = redis.hget("session:abc123", "user_id")

# 商品信息缓存（按字段更新）
redis.hset("product:42", "price", "12.99")  # 只更新价格字段
```

### 4.3 List — 消息队列、最近浏览

```python
# 最近浏览商品（保留最近10条）
def track_view(user_id: int, product_id: int):
    key = f"recent_views:{user_id}"
    redis.lpush(key, product_id)   # 头部插入
    redis.ltrim(key, 0, 9)         # 只保留前10个
    redis.expire(key, 86400)

def get_recent_views(user_id: int) -> list:
    return redis.lrange(f"recent_views:{user_id}", 0, -1)
```

### 4.4 Set — 去重、标签

```python
# 今日活跃用户（UV 统计）
redis.sadd("active_users:2026-03-26", user_id)
uv = redis.scard("active_users:2026-03-26")

# 商品标签
redis.sadd("product_tags:42", "electronics", "sale", "wireless")
# 查找有共同标签的商品（集合交集）
common_tags = redis.sinter("product_tags:42", "product_tags:88")
```

### 4.5 Sorted Set — 排行榜、延时队列

```python
# 商品销量排行榜
redis.zincrby("product_rank:sales", 1, "product:42")  # 商品42卖出1件
top10 = redis.zrevrange("product_rank:sales", 0, 9, withscores=True)

# 延时队列（用时间戳作为 score）
import time
def schedule_order_cancel(order_id: int, delay_seconds: int = 1800):
    execute_at = time.time() + delay_seconds
    redis.zadd("delayed_tasks", {f"cancel_order:{order_id}": execute_at})

def process_delayed_tasks():
    now = time.time()
    # 获取所有到期任务
    tasks = redis.zrangebyscore("delayed_tasks", 0, now)
    for task in tasks:
        redis.zrem("delayed_tasks", task)
        execute_task(task)
```

---

## 5. 缓存键设计规范

```
# 命名约定：{服务}:{资源类型}:{唯一标识}[:{子字段}]
product:detail:42              # 商品详情
product:list:category:5:p1    # 第1页分类5的商品列表
user:profile:123              # 用户资料
user:session:abc-token-123    # 用户会话
rate_limit:api:user:456       # 限流计数
order:lock:789                # 分布式锁

# 避免：
42                             # 太简单，全局冲突
product_42                    # 不规范
ProductDetail42               # 不规范
```

### 缓存版本控制

```python
# 当缓存数据结构改变时，通过版本号一次性让所有缓存失效
CACHE_VERSION = "v2"

def make_key(resource: str, id: int) -> str:
    return f"{CACHE_VERSION}:product:{id}"

# 升级 v1 → v2 时，旧的 v1:product:* 自动不再被访问
# 待 TTL 自然过期后清理，无需手动删除（避免大规模 DEL 操作阻塞 Redis）
```

---

## 6. 一致性：先删缓存还是先更新数据库

这是 Cache-Aside 中最重要的时序问题：

```
方案1：先删缓存，再更新DB（❌ 有问题）
    Thread A: 删除缓存
    Thread B: 发现缓存不存在 → 读DB（旧值）→ 回填缓存（旧值）
    Thread A: 更新DB（新值）
    结果：缓存里是旧值，DB 是新值 → 不一致

方案2：先更新DB，再删缓存（✅ 推荐）
    Thread A: 更新DB（新值）
    Thread A: 删除缓存
    Thread B: 发现缓存不存在 → 读DB（新值）→ 回填缓存（新值）
    结果：缓存和DB一致

方案3：延迟双删（在方案2基础上加保险）
    Thread A: 更新DB → 删除缓存 → 等100ms → 再次删除缓存
    目的：防止极端情况下（方案2中仍有小窗口），用第二次删除兜底
```

```python
def update_product_with_double_delete(product_id: int, data: dict):
    # 1. 更新数据库
    db.execute("UPDATE products SET price=$1 WHERE id=$2", data["price"], product_id)

    # 2. 第一次删除缓存
    redis.delete(f"product:{product_id}")

    # 3. 延迟100ms后第二次删除（异步，不阻塞请求）
    asyncio.get_event_loop().call_later(
        0.1,  # 100ms
        lambda: redis.delete(f"product:{product_id}")
    )
```

---

## Key Architect Takeaways

- **Cache-Aside 是默认选择**：大多数场景用"读缓存→未命中查DB→回填缓存，写DB→删缓存"模式就够了
- **先写DB再删缓存**：这个顺序不能颠倒，防止并发场景下的脏数据回填
- **缓存三大问题是面试高频考点，更是生产事故的根源**：穿透（不存在的 key）、击穿（热点 key 过期）、雪崩（大量 key 同时过期）——每种都有对应解法
- **TTL 设置是门艺术**：TTL 太短→命中率低；TTL 太长→一致性差。核心原则：允许多旧的数据？根据业务容忍度决定
- **Redis 的数据结构不要只用 String**：Sorted Set 做排行榜、Set 做去重、Hash 做对象缓存，选对数据结构性能差异显著
