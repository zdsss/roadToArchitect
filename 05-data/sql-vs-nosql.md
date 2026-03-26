# SQL vs NoSQL：数据存储选型

数据存储是架构中最难推翻的决策之一。一旦选定，迁移代价极高。本章从架构师视角分析关系型与非关系型数据库的核心原理、适用场景和选型依据。

---

## 1. 关系型数据库基础

### 1.1 ACID 特性

ACID 是关系型数据库的核心保证，是"数据正确性"的基础：

| 特性 | 全称 | 含义 | 违反后果示例 |
|------|------|------|------------|
| 原子性（A） | Atomicity | 事务中的操作要么全部成功，要么全部回滚 | 转账：扣款成功但入账失败 |
| 一致性（C） | Consistency | 事务前后数据库始终处于合法状态 | 库存变为负数 |
| 隔离性（I） | Isolation | 并发事务互不干扰，如同串行执行 | 两人同时购买最后一件商品 |
| 持久性（D） | Durability | 已提交的事务永久保存，即使系统崩溃 | 下单成功但重启后订单消失 |

**原子性示例：**
```python
# 转账：扣款 + 入账必须原子执行
def transfer(from_account: int, to_account: int, amount: float):
    with db.transaction():  # 事务开始
        db.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s",
                   amount, from_account)
        # 如果这里崩溃，上面的扣款会自动回滚
        db.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s",
                   amount, to_account)
    # 事务提交：两条 UPDATE 同时生效
```

### 1.2 事务隔离级别

隔离性有程度之分。更高的隔离级别更安全，但并发性能更低：

| 隔离级别 | 脏读 | 不可重复读 | 幻读 | 性能 |
|---------|------|---------|------|------|
| Read Uncommitted | 可能 | 可能 | 可能 | 最高 |
| Read Committed | 否 | 可能 | 可能 | 高 |
| Repeatable Read | 否 | 否 | 可能（MySQL InnoDB 用 MVCC 避免） | 中 |
| Serializable | 否 | 否 | 否 | 最低 |

**三种并发问题：**

```
脏读（Dirty Read）：
    事务A 修改数据（未提交）→ 事务B 读到了 A 未提交的修改
    → 事务A 回滚 → 事务B 读到了不存在的数据

不可重复读（Non-Repeatable Read）：
    事务A 两次读同一行 → 中间事务B 修改并提交了该行
    → 事务A 两次读到不同值

幻读（Phantom Read）：
    事务A 两次查询同一范围 → 中间事务B 插入了符合条件的新行
    → 事务A 第二次查询看到了"幽灵"行
```

> **架构师提示：** PostgreSQL 默认 Read Committed；MySQL InnoDB 默认 Repeatable Read。绝大多数 OLTP 场景用默认级别足够。只有在需要强一致读（如对账）时才升级到 Serializable。

### 1.3 索引原理

索引是用空间换时间的数据结构，让查询从 O(n) 提升到 O(log n) 或 O(1)。

#### B-Tree 索引（最常用）

```
无索引：全表扫描 O(n)
SELECT * FROM products WHERE id = 42
→ 检查每一行，直到找到 id=42

B-Tree 索引：O(log n)
索引结构（树形）：
           [50]
          /    \
       [25]    [75]
      /   \    /  \
   [10] [30][60] [90]

查找 id=42：根节点50 → 左子树25 → 右子树30 → ...
每次比较排除一半，远快于全表扫描
```

#### 索引类型对比

| 类型 | 适用场景 | 示例 |
|------|---------|------|
| B-Tree（默认） | 等值查询、范围查询、排序 | `WHERE id = 42`，`WHERE price > 100` |
| Hash | 仅等值查询（比B-Tree快） | `WHERE session_id = 'abc'` |
| 覆盖索引 | 索引包含查询所需全部字段，无需回表 | `INDEX (category_id, price, name)` |
| 全文索引 | 文本搜索 | `WHERE MATCH(description) AGAINST('wifi')` |
| 复合索引 | 多字段联合查询 | `INDEX (user_id, created_at)` |

**复合索引的最左前缀原则：**
```sql
-- 创建复合索引
CREATE INDEX idx_order_user_date ON orders (user_id, created_at, status);

-- ✅ 能用索引：包含最左前缀 user_id
SELECT * FROM orders WHERE user_id = 1;
SELECT * FROM orders WHERE user_id = 1 AND created_at > '2026-01-01';
SELECT * FROM orders WHERE user_id = 1 AND created_at > '2026-01-01' AND status = 'paid';

-- ❌ 无法用索引：跳过了 user_id
SELECT * FROM orders WHERE created_at > '2026-01-01';
SELECT * FROM orders WHERE status = 'paid';
```

**索引失效的常见场景：**
```sql
-- ❌ 对索引列使用函数
WHERE YEAR(created_at) = 2026          -- 改为 BETWEEN '2026-01-01' AND '2026-12-31'

-- ❌ 隐式类型转换
WHERE user_id = '123'                   -- user_id 是 INT，'123' 是字符串

-- ❌ LIKE 前缀通配符
WHERE name LIKE '%Widget%'              -- 改用全文索引或 Elasticsearch

-- ❌ OR 两侧不都是索引列
WHERE indexed_col = 1 OR non_indexed = 2
```

#### 何时加索引

```
适合加索引：
+ 频繁出现在 WHERE、JOIN ON、ORDER BY 子句的列
+ 选择性高的列（唯一值多，如 user_id）
+ 外键列（加速 JOIN）

不适合加索引：
- 写多读少的表（索引会拖慢 INSERT/UPDATE/DELETE）
- 选择性低的列（如 gender 只有两个值，索引效果差）
- 小表（全表扫描可能更快）
```

### 1.4 范式化与反范式化

**第一范式（1NF）：** 每列不可再分，没有重复组。
```sql
-- 违反 1NF：tags 字段存多个值
id | name    | tags
1  | Widget  | "electronics,gadget,sale"

-- 符合 1NF：拆成关联表
products: id, name
product_tags: product_id, tag
```

**第三范式（3NF）：** 非主键字段只依赖于主键，不存在传递依赖。
```sql
-- 违反 3NF：city_name 依赖 zip_code，zip_code 依赖 id（传递依赖）
orders: id, zip_code, city_name

-- 符合 3NF
orders: id, zip_code
zip_codes: zip_code, city_name
```

**反范式化（何时故意违反）：**

| 场景 | 反范式化策略 | 理由 |
|------|------------|------|
| 读多写少的报表 | 冗余 user_name 到 orders 表 | 避免每次 JOIN users 表 |
| 订单历史 | 冗余 product_price 到 order_items | 价格可能变化，历史订单要记录下单时的价格 |
| 计数器 | 在表中维护 comment_count | 避免每次 COUNT(*) 全表扫描 |

> **Key Architect Takeaways：**
> - 索引是最常用的性能优化手段，但不是越多越好——索引会拖慢写入
> - EXPLAIN ANALYZE 是诊断慢查询的必备工具，先分析再优化
> - 反范式化不是"错误"，是权衡——当读性能重要到值得牺牲写入一致性维护成本时，它是正确选择

---

## 2. NoSQL 数据库类型

### 2.1 文档型（Document Store）— 代表：MongoDB

```python
# 文档存储：整个对象作为一个文档（JSON/BSON）
{
    "_id": "prod-123",
    "name": "Wireless Headphones",
    "price": 99.99,
    "specs": {                      # 嵌套对象
        "battery_hours": 30,
        "connectivity": "Bluetooth 5.0"
    },
    "variants": [                   # 数组
        {"color": "black", "stock": 50},
        {"color": "white", "stock": 30}
    ]
}
```

| 优点 | 缺点 |
|------|------|
| Schema 灵活，可随时添加字段 | 跨文档事务有限（新版本有所改进） |
| 嵌套数据天然表达，无需 JOIN | 数据重复（冗余）在所难免 |
| 水平扩展容易（分片内置） | 不适合强关系型数据 |
| 读单个文档性能好 | 跨集合查询性能不如 SQL |

**适用场景：** 商品目录（字段差异大）、CMS、用户配置、日志

### 2.2 键值型（Key-Value Store）— 代表：Redis

```python
# 最简单的数据模型：key → value
redis.set("session:user-123", json.dumps({"user_id": 123, "role": "admin"}), ex=3600)
redis.get("session:user-123")

# 也支持复杂数据结构
redis.hset("product:42", mapping={"name": "Widget", "price": "9.99", "stock": "100"})
redis.zincrby("leaderboard", 1, "user-456")  # 排行榜
```

| 优点 | 缺点 |
|------|------|
| 极高吞吐量（内存操作，微秒级） | 不支持复杂查询 |
| 数据结构丰富（String/Hash/List/Set/Sorted Set） | 数据量受内存限制 |
| 原生 TTL 支持（缓存、会话） | 持久化比磁盘数据库弱（可配置） |

**适用场景：** 缓存、会话、排行榜、分布式锁、计数器、限流

### 2.3 列族型（Wide Column Store）— 代表：Cassandra

```
Cassandra 数据模型（与关系型的区别）：
- 行按 Partition Key 分布到不同节点
- 每行可以有不同的列
- 查询必须包含 Partition Key（否则全表扫描）

表结构示例（时序数据）：
Partition Key: (sensor_id)
Clustering Key: (timestamp DESC)

sensor_id | timestamp           | temperature | humidity
--------- | ------------------- | ----------- | --------
sensor-1  | 2026-03-26 10:00:00 | 25.3        | 60
sensor-1  | 2026-03-26 09:59:00 | 25.1        | 61
sensor-2  | 2026-03-26 10:00:00 | 22.0        | 55
```

| 优点 | 缺点 |
|------|------|
| 极高写入吞吐（无主节点瓶颈） | 不支持 JOIN，不支持任意查询 |
| 线性水平扩展 | 数据建模难度高（需要按查询设计表） |
| 跨数据中心复制内置 | 最终一致性（不适合强一致场景） |

**适用场景：** 物联网时序数据、用户行为日志、消息历史

### 2.4 图数据库（Graph Database）— 代表：Neo4j

```
图数据库：节点（Node）+ 关系（Relationship）+ 属性（Property）

(User:Alice) -[:FOLLOWS]-> (User:Bob)
(User:Bob) -[:PURCHASED]-> (Product:Widget)
(User:Alice) -[:FRIEND_OF]-> (User:Carol)

Cypher 查询（找 Alice 的朋友买过的商品）：
MATCH (alice:User {name: 'Alice'})-[:FRIEND_OF*1..2]->(friend)
      -[:PURCHASED]->(product)
RETURN DISTINCT product.name
```

**适用场景：** 社交网络、推荐引擎、欺诈检测、知识图谱

### 2.5 搜索引擎（Search Engine）— 代表：Elasticsearch

```python
# 全文搜索：SQL LIKE '%widget%' 慢，ES 快
es.search(index="products", body={
    "query": {
        "multi_match": {
            "query": "wireless headphones",
            "fields": ["name^3", "description"],  # name 权重是 description 的3倍
            "fuzziness": "AUTO"  # 容错拼写
        }
    },
    "highlight": {"fields": {"description": {}}}
})
```

**适用场景：** 全文搜索、日志分析（ELK Stack）、复杂聚合查询

---

## 3. CAP 定理

### 3.1 三角不可能

分布式系统在网络分区发生时，无法同时保证**一致性**和**可用性**：

| 属性 | 含义 |
|------|------|
| 一致性（Consistency） | 所有节点看到相同的数据（读总是得到最新写入） |
| 可用性（Availability） | 每个请求都能得到响应（不保证是最新数据） |
| 分区容忍（Partition Tolerance） | 网络分区（节点间通信中断）时系统仍可运行 |

> **关键洞察：** 网络分区在分布式系统中不可避免（网络故障是常态，不是异常）。因此 P 是必选项，真正的选择是 CP 还是 AP。

| 系统类型 | 牺牲什么 | 例子 |
|---------|---------|------|
| CP | 可用性（分区时拒绝服务，保证一致性） | PostgreSQL, ZooKeeper, HBase |
| AP | 一致性（分区时返回可能过时的数据） | Cassandra, DynamoDB, CouchDB |
| CA（单机） | 分区容忍（不适用于分布式） | 单机 MySQL |

### 3.2 BASE vs ACID

| 特性 | ACID（关系型） | BASE（NoSQL） |
|------|-------------|--------------|
| 一致性 | 强一致性 | **B**asically Available（基本可用） |
| 状态 | 始终一致 | **S**oft state（软状态，允许中间状态） |
| 一致时机 | 事务提交时立即一致 | **E**ventually consistent（最终一致） |
| 适用场景 | 金融、订单、库存 | 社交动态、推荐、用户行为日志 |

---

## 4. 选型决策矩阵

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 商品目录（字段差异大） | MongoDB | Schema 灵活，商品属性各不相同 |
| 订单数据 | PostgreSQL | 强 ACID，跨表事务（订单+库存） |
| 用户会话 | Redis | TTL 自动过期，读写极快 |
| 商品搜索 | Elasticsearch | 全文搜索、模糊匹配、聚合分析 |
| 用户行为日志 | Cassandra / ClickHouse | 高写入，时序查询 |
| 社交关系图 | Neo4j | 多跳关系查询天然高效 |
| 实时排行榜 | Redis Sorted Set | O(log n) 插入，O(log n+k) 范围查询 |
| 购物车 | Redis Hash | 用户购物车是临时状态，TTL 自动清理 |

> **架构师提示：** 大多数系统需要多种数据库协同工作（Polyglot Persistence）。例如 ShopFlow：订单用 PostgreSQL，缓存用 Redis，搜索用 Elasticsearch。这不是过度设计，而是让每种数据库做它最擅长的事。

---

## 5. PostgreSQL 实战（ShopFlow）

### 5.1 建表示例

```sql
-- 商品表
CREATE TABLE products (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    slug        VARCHAR(200) UNIQUE NOT NULL,     -- URL友好名称
    price       NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    category_id INTEGER REFERENCES categories(id),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 索引设计
CREATE INDEX idx_products_category ON products (category_id);
-- 理由：按分类过滤商品是高频操作

CREATE INDEX idx_products_price ON products (price);
-- 理由：价格范围过滤

CREATE INDEX idx_products_name_search ON products USING gin(to_tsvector('chinese', name));
-- 理由：全文搜索索引（需要 pg_jieba 插件支持中文分词）

-- 订单表
CREATE TABLE orders (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'paid', 'shipped', 'delivered', 'cancelled')),
    total       NUMERIC(10, 2) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_user_id ON orders (user_id);
-- 理由：按用户查订单历史

CREATE INDEX idx_orders_status_created ON orders (status, created_at DESC);
-- 理由：运营后台按状态过滤 + 按时间排序

-- 订单明细（多对多：订单 ↔ 商品）
CREATE TABLE order_items (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10, 2) NOT NULL,  -- 记录下单时的价格（冗余，反范式）
    UNIQUE (order_id, product_id)
);
```

### 5.2 EXPLAIN ANALYZE 诊断慢查询

```sql
-- 找出某用户的所有已支付订单（最近10条）
EXPLAIN ANALYZE
SELECT o.id, o.total, o.created_at,
       array_agg(p.name) as product_names
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.user_id = 123
  AND o.status = 'paid'
ORDER BY o.created_at DESC
LIMIT 10;

-- 输出解读：
-- Seq Scan（顺序扫描）→ 说明没用到索引，需要加索引
-- Index Scan（索引扫描）→ 好，用到了索引
-- Hash Join vs Nested Loop → 大表JOIN用Hash Join更快
-- actual rows vs estimated rows 差异大 → 统计信息过时，需要 ANALYZE
```

### 5.3 事务示例（下单）

```python
async def place_order(conn, user_id: int, items: list[dict]) -> int:
    async with conn.transaction():
        # 1. 锁定商品行，防止超卖（SELECT FOR UPDATE）
        for item in items:
            product = await conn.fetchrow(
                "SELECT id, price, stock FROM products WHERE id = $1 FOR UPDATE",
                item["product_id"]
            )
            if product["stock"] < item["quantity"]:
                raise ValueError(f"Insufficient stock for product {item['product_id']}")

        # 2. 计算总价
        total = sum(
            item["quantity"] * await get_product_price(conn, item["product_id"])
            for item in items
        )

        # 3. 创建订单
        order_id = await conn.fetchval(
            "INSERT INTO orders (user_id, total) VALUES ($1, $2) RETURNING id",
            user_id, total
        )

        # 4. 写订单明细 + 扣库存
        for item in items:
            price = await get_product_price(conn, item["product_id"])
            await conn.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES ($1,$2,$3,$4)",
                order_id, item["product_id"], item["quantity"], price
            )
            await conn.execute(
                "UPDATE products SET stock = stock - $1 WHERE id = $2",
                item["quantity"], item["product_id"]
            )

        return order_id
    # 事务提交：以上所有操作原子生效
```

---

## Key Architect Takeaways

- **关系型数据库不是"旧技术"**：PostgreSQL 在 2026 年仍然是大多数业务系统的最佳选择。强 ACID 保证、成熟的工具生态、丰富的索引类型——不要因为 NoSQL 流行而放弃它
- **NoSQL 解决特定问题，不是通用替代**：Redis 做缓存无敌，Cassandra 做时序写入无敌，MongoDB 做 Schema 灵活存储好用——但它们都不是万能的
- **CAP 定理的实践含义**：网络分区时，你必须选择：拒绝服务（CP）还是返回旧数据（AP）。金融系统选 CP，社交动态可以选 AP
- **索引是最高性价比的优化**：加一个索引可能让查询从 10 秒降到 10 毫秒，代价只是一点磁盘空间和写入开销
- **Polyglot Persistence 是成熟系统的常态**：用 PostgreSQL 存事务数据，Redis 做缓存，Elasticsearch 做搜索——让每种数据库做它最擅长的事，而不是用一种数据库解决所有问题
