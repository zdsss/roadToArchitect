# Twitter 信息流系统设计

> 架构师视角：本文以 Twitter 时间线（Feed）系统为案例，深入剖析海量社交网络场景下的核心设计挑战——如何在极高读写比和明星用户写放大之间找到平衡点。

---

## 目录

1. [需求分析](#1-需求分析)
2. [规模估算](#2-规模估算)
3. [API 设计](#3-api-设计)
4. [高层设计](#4-高层设计)
5. [组件深入](#5-组件深入)
6. [权衡分析](#6-权衡分析)
7. [总结](#7-总结)

---

## 1. 需求分析

### 1.1 功能需求

| 功能模块 | 描述 | 优先级 |
|----------|------|--------|
| 发推（Tweet） | 用户发布最多 280 字符的推文，支持图片/视频附件 | P0 |
| 关注 / 取关（Follow/Unfollow） | 用户关注或取消关注其他用户，构建社交图谱 | P0 |
| 主页时间线（Home Timeline） | 展示当前用户所关注的所有人的最新推文，按时间倒序 | P0 |
| 用户时间线（User Timeline） | 展示某一特定用户自己发出的所有推文 | P1 |
| 推文详情（Tweet Detail） | 查看单条推文的完整内容、转推数、点赞数、评论列表 | P1 |
| 搜索（Search） | 全文检索推文内容（本文不展开） | P2 |
| 通知（Notification） | 被 @ 提及、被转推、被点赞时的消息提醒（本文不展开） | P2 |

**核心功能聚焦**：本文重点设计 **发推** 与 **主页时间线** 两个模块，它们共同构成了 Twitter 最核心的工程挑战。

### 1.2 非功能需求

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 时间线读取延迟 | P99 < 200ms | 用户体验底线，超过 300ms 跳出率显著上升 |
| 发推延迟 | P99 < 500ms | 写操作可以适当宽松 |
| 系统可用性 | 99.99%（四个九） | 年宕机 < 52 分钟 |
| 一致性模型 | 最终一致性 | 时间线短暂延迟可接受，但不能永远丢失 |
| 数据持久性 | 推文永久保存 | 不允许数据丢失 |
| 读写比 | 约 100:1 | 读远多于写，架构优化以读路径为核心 |

### 1.3 关键约束与假设

- 用户平均关注 200 人，粉丝中位数约 200 人，但存在严重的长尾分布（大V可达数千万粉丝）。
- 推文一旦发出不可编辑（简化设计，忽略编辑功能）。
- 时间线展示最近 800 条推文，超出部分通过翻页或归档查询。
- 图片/视频等媒体文件通过独立的对象存储（如 S3）处理，本文聚焦文本推文的信息流。

---

## 2. 规模估算

### 2.1 用户与流量

| 指标 | 数值 | 计算说明 |
|------|------|----------|
| DAU（日活跃用户） | 3 亿 | 题目给定 |
| 每用户平均关注数 | 200 人 | 题目给定 |
| 每日新发推文数 | 5 亿条 | 题目给定 |
| 发推 QPS（平均） | ~5,800 条/秒 | 5亿 ÷ 86,400 |
| 发推 QPS（峰值） | ~15,000 条/秒 | 按峰均比 ~2.5x 估算 |
| 时间线读取次数/日 | ~300 亿次 | 3亿用户，每人读约 100 次 |
| 时间线读取 QPS（平均） | ~350,000 次/秒 | 300亿 ÷ 86,400 |
| 时间线读取 QPS（峰值） | ~900,000 次/秒 | 按峰均比 ~2.5x 估算 |

读写比验证：350,000 / 5,800 ≈ **60:1**（保守估算），实际中用户刷新频率更高，真实读写比接近 **100:1**。

### 2.2 存储估算

**单条推文存储大小：**

| 字段 | 大小 |
|------|------|
| tweet_id（64位整数） | 8 Bytes |
| user_id（64位整数） | 8 Bytes |
| content（最多 280 字符，UTF-8） | ~560 Bytes |
| created_at（时间戳） | 8 Bytes |
| metadata（点赞数、转推数等） | ~20 Bytes |
| **单条推文合计** | **~600 Bytes** |

**每日新增存储：**

```
5亿条 × 600 Bytes = 300 GB/天
```

**5年总存储（仅推文文本）：**

```
300 GB × 365 × 5 ≈ 548 TB
```

**时间线缓存（Redis）估算：**

每个活跃用户的时间线缓存约 800 个推文 ID（每个 8 Bytes）：

```
3亿用户 × 800 × 8 Bytes = 1.92 TB（全量缓存）
```

实际上只需缓存活跃用户（约 DAU 的 20% 为高频用户），约需 **400 GB** Redis 内存，在可接受范围内。

### 2.3 带宽估算

| 方向 | 计算 | 带宽需求 |
|------|------|----------|
| 写入带宽（发推） | 15,000 条/秒 × 600 Bytes | ~9 MB/s |
| 读取带宽（时间线，每次返回 20 条） | 900,000 次/秒 × 20 × 600 Bytes | ~10 GB/s |

读取带宽是写入的约 **1,000 倍**，这再次验证了系统设计必须以优化读路径为核心目标。

---

## 3. API 设计

### 3.1 发推

```
POST /v1/tweets
Authorization: Bearer <token>

Request Body:
{
  "content": "string (max 280 chars)",
  "media_ids": ["string"],      // 可选，媒体文件 ID 列表
  "reply_to_tweet_id": "string" // 可选，回复某条推文
}

Response 201 Created:
{
  "tweet_id": "1234567890",
  "user_id": "987654321",
  "content": "Hello Twitter!",
  "created_at": "2026-03-26T10:00:00Z"
}
```

### 3.2 获取主页时间线

```
GET /v1/timeline/home
Authorization: Bearer <token>

Query Parameters:
  cursor  : string  // 分页游标（基于推文ID的游标分页，优于offset分页）
  limit   : int     // 每页数量，默认20，最大200

Response 200 OK:
{
  "tweets": [
    {
      "tweet_id": "1234567890",
      "author": { "user_id": "111", "username": "alice" },
      "content": "Hello World!",
      "created_at": "2026-03-26T09:55:00Z",
      "like_count": 42,
      "retweet_count": 7
    }
  ],
  "next_cursor": "1234567800",
  "has_more": true
}
```

**为何使用游标分页而非 offset 分页：**
- Offset 分页（LIMIT 20 OFFSET 100）在深翻页时数据库需扫描大量数据，性能差。
- 游标分页基于推文 ID（雪花 ID 天然有序），每次翻页只需 `WHERE tweet_id < cursor`，性能稳定为 O(1) 索引查找。

### 3.3 获取用户时间线

```
GET /v1/timeline/user/{user_id}
Authorization: Bearer <token>

Query Parameters:
  cursor  : string
  limit   : int

Response 200 OK:
{
  "tweets": [...],
  "next_cursor": "string",
  "has_more": true
}
```

用户时间线（自己的推文列表）相对简单：直接按 `user_id` 查询推文存储即可，不涉及 Fan-out 问题。

### 3.4 关注 / 取关

```
POST /v1/follow
Authorization: Bearer <token>

Request Body:
{
  "target_user_id": "string",
  "action": "follow" | "unfollow"
}

Response 200 OK:
{
  "success": true,
  "follower_count": 1523
}
```

### 3.5 推文详情

```
GET /v1/tweets/{tweet_id}
Authorization: Bearer <token>

Response 200 OK:
{
  "tweet_id": "1234567890",
  "author": { ... },
  "content": "string",
  "created_at": "2026-03-26T10:00:00Z",
  "like_count": 100,
  "retweet_count": 20,
  "reply_count": 5,
  "replies": [ ... ]  // 前几条回复
}
```

---

## 4. 高层设计

### 4.1 核心挑战

Twitter 系统设计中最核心的工程挑战是：**如何在用户打开 App 的瞬间（< 200ms），向其呈现由数百人构成的个性化时间线？**

这个问题的难点在于：
- 用户关注了 200 人，每人每天发多条推文，聚合计算量大。
- 读 QPS 极高（~90万/秒），远超任何单机数据库的承受极限。
- 存在"明星效应"：Lady Gaga 拥有 1.3 亿粉丝，每次发推理论上需要更新 1.3 亿个时间线。

### 4.2 两种基本方案

```
┌─────────────────────────────────────────────────────────────────┐
│                    时间线生成的两种极端方案                         │
├──────────────────────────┬──────────────────────────────────────┤
│      Pull（拉模型）        │        Push（推模型 / Fan-out）        │
├──────────────────────────┼──────────────────────────────────────┤
│ 读时间线时，实时查询所有      │ 发推时，立刻写入所有关注者的            │
│ 关注者的推文并聚合           │ 时间线缓存（预计算）                   │
├──────────────────────────┼──────────────────────────────────────┤
│ 读：慢（N次DB查询+聚合）     │ 读：快（O(1) 缓存读取）               │
│ 写：快（只写一份）           │ 写：慢（写N份，N=粉丝数）              │
├──────────────────────────┼──────────────────────────────────────┤
│ 存储：省                  │ 存储：费（冗余N份时间线缓存）            │
│ 实时性：高                 │ 实时性：有轻微延迟（异步Fan-out）        │
└──────────────────────────┴──────────────────────────────────────┘
```

### 4.3 高层架构图（文字描述）

```
客户端
  │
  ▼
API Gateway（负载均衡、限流、认证）
  │
  ├──► Tweet Service（发推服务）
  │        │
  │        ├──► Tweet Store（Cassandra，持久化）
  │        └──► Fan-out Service（异步，消息队列）
  │                  │
  │                  └──► Timeline Cache（Redis，各用户时间线）
  │
  ├──► Timeline Service（时间线服务）
  │        │
  │        ├──► Timeline Cache（Redis，优先读）
  │        └──► Tweet Store（Cache Miss 时降级查询）
  │
  └──► Follow Service（关注服务）
           │
           └──► Social Graph Store（Redis Set / 图数据库）
```

---

## 5. 组件深入

### 5.1 Fan-out on Write（写扩散）

#### 5.1.1 工作原理

用户 A 发推后，系统异步地将该推文 ID 写入所有关注 A 的用户的时间线缓存（Redis List）。

```
用户A发推 tweet_id=T1
    │
    ▼
Tweet Service 写入 Cassandra（持久化）
    │
    ▼
发布消息到 Message Queue（Kafka）
    │
    ▼
Fan-out Workers（多个消费者并行）
    │
    ├──► 查询 A 的粉丝列表（Social Graph）
    │
    └──► 对每个粉丝 B、C、D...
              LPUSH timeline:{user_id} tweet_id
              LTRIM timeline:{user_id} 0 799   # 只保留最新800条
```

#### 5.1.2 Python 伪代码

```python
import asyncio
from typing import List


async def handle_new_tweet(tweet_id: str, author_id: str) -> None:
    """
    发推后触发的 Fan-out 逻辑（异步执行，不阻塞发推响应）
    """
    # Step 1: 持久化推文到 Cassandra
    await tweet_store.save(tweet_id=tweet_id, author_id=author_id)

    # Step 2: 发布 Fan-out 任务到消息队列
    await message_queue.publish(
        topic="tweet.fanout",
        payload={"tweet_id": tweet_id, "author_id": author_id}
    )
    # 发推 API 在此处返回，用户无需等待 Fan-out 完成


async def fanout_worker(message: dict) -> None:
    """
    Fan-out Worker：消费消息队列，执行写扩散
    """
    tweet_id = message["tweet_id"]
    author_id = message["author_id"]

    # Step 3: 获取作者的所有粉丝 ID（分批获取，避免一次加载过多）
    cursor = 0
    batch_size = 1000

    while True:
        follower_ids: List[str] = await social_graph.get_followers(
            user_id=author_id,
            cursor=cursor,
            limit=batch_size
        )

        if not follower_ids:
            break

        # Step 4: 批量写入每个粉丝的时间线缓存
        pipeline = redis_client.pipeline()
        for follower_id in follower_ids:
            cache_key = f"timeline:{follower_id}"
            pipeline.lpush(cache_key, tweet_id)       # 头部插入（最新在前）
            pipeline.ltrim(cache_key, 0, 799)         # 保留最新800条
            pipeline.expire(cache_key, 7 * 24 * 3600) # 7天过期

        await pipeline.execute()
        cursor += batch_size


async def get_home_timeline(user_id: str, cursor: str = None, limit: int = 20) -> List[dict]:
    """
    读时间线：Fan-out on Write 模式下，直接读 Redis，O(1)
    """
    cache_key = f"timeline:{user_id}"

    if cursor:
        # 基于游标的翻页：找到 cursor 在 list 中的位置
        tweet_ids = await redis_client.lrange_after_cursor(cache_key, cursor, limit)
    else:
        tweet_ids = await redis_client.lrange(cache_key, 0, limit - 1)

    if not tweet_ids:
        # Cache Miss：降级到数据库聚合查询（慢路径）
        tweet_ids = await fallback_to_db(user_id, limit)

    # 批量获取推文详情（Tweet Store 或 Tweet Cache）
    tweets = await tweet_store.batch_get(tweet_ids)
    return tweets
```

#### 5.1.3 优缺点

| 维度 | 评价 |
|------|------|
| 读时间线速度 | 极快，O(1) Redis 读取，延迟 < 10ms |
| 写放大问题 | 严重，大V（百万粉丝）每发一条推文触发百万次写操作 |
| 存储冗余 | 同一推文 ID 被复制到所有粉丝的缓存列表中 |
| 实时性 | 有轻微延迟（异步 Fan-out），通常 1~5 秒可见 |
| 适合场景 | 粉丝数 < 10 万的普通用户 |

### 5.2 Fan-out on Read（读扩散）

#### 5.2.1 工作原理

用户发推时只写一份（到自己的推文列表）。当用户 B 请求时间线时，系统实时拉取 B 关注的所有人的最新推文，在内存中聚合、排序后返回。

```
用户B请求时间线
    │
    ▼
Timeline Service
    │
    ▼
查询 B 的关注列表（Social Graph）
获取 [A, C, D, E, ... 200人]
    │
    ▼
并发查询每个人的最新推文
（200次 Cassandra 查询 或 Redis 查询）
    │
    ▼
内存中归并排序（按时间倒序）
    │
    ▼
返回前20条
```

#### 5.2.2 Python 伪代码

```python
import heapq
from typing import List


async def get_home_timeline_pull(user_id: str, limit: int = 20) -> List[dict]:
    """
    Fan-out on Read：时间线即时聚合
    """
    # Step 1: 获取关注列表
    following_ids: List[str] = await social_graph.get_following(user_id)

    # Step 2: 并发拉取每个被关注者的最新推文（协程并发）
    tasks = [
        tweet_store.get_user_recent_tweets(followed_id, limit=limit)
        for followed_id in following_ids
    ]
    results = await asyncio.gather(*tasks)  # 并发执行，耗时 = 最慢的那个请求

    # Step 3: 内存归并排序（小顶堆按时间倒序）
    all_tweets = []
    for tweet_list in results:
        all_tweets.extend(tweet_list)

    # 按创建时间倒序排序，取前 limit 条
    all_tweets.sort(key=lambda t: t["created_at"], reverse=True)
    return all_tweets[:limit]
```

#### 5.2.3 优缺点

| 维度 | 评价 |
|------|------|
| 读时间线速度 | 慢，需要 N 次并发查询 + 内存聚合，延迟 100~500ms |
| 写操作简单 | 发推只写一份，无写放大 |
| 存储节省 | 无冗余缓存 |
| 大V支持 | 天然支持，发推开销与粉丝数无关 |
| 实时性 | 高，读到的永远是最新数据 |
| 适合场景 | 关注数极少（< 50）或粉丝数极多的大V |

### 5.3 混合策略（Twitter 实际采用）

#### 5.3.1 设计思路

Twitter 工程师的洞察：系统中存在两类极端用户，需要不同策略：

- **普通用户**（粉丝 < 10 万）：适合写扩散，Fan-out 开销可控。
- **明星用户 / 大V**（粉丝 > 10 万）：写扩散开销灾难性，改用读扩散。

混合策略核心规则：

```
发推时：
  if author.follower_count <= 100,000:
      执行 Fan-out on Write（写入所有粉丝的时间线缓存）
  else:
      只写自己的推文列表（不做 Fan-out）

读时间线时：
  timeline = 从 Redis 读取预计算的时间线缓存（普通用户推文）
  celebrity_tweets = 实时拉取用户关注的大V的最新推文
  merged_timeline = merge(timeline, celebrity_tweets)  # 归并排序
  return merged_timeline[:limit]
```

#### 5.3.2 混合时间线生成 Python 伪代码

```python
from dataclasses import dataclass
from typing import List, Tuple


CELEBRITY_THRESHOLD = 100_000  # 粉丝数超过此值视为大V


@dataclass
class Tweet:
    tweet_id: str
    author_id: str
    content: str
    created_at: float  # Unix timestamp


async def publish_tweet(author_id: str, content: str) -> str:
    """
    发推：根据作者粉丝数决定 Fan-out 策略
    """
    tweet_id = generate_snowflake_id()

    # 1. 持久化
    tweet = Tweet(tweet_id=tweet_id, author_id=author_id,
                  content=content, created_at=current_time())
    await tweet_store.save(tweet)

    # 2. 判断是否需要 Fan-out
    follower_count = await social_graph.get_follower_count(author_id)

    if follower_count <= CELEBRITY_THRESHOLD:
        # 普通用户：写扩散（异步，不阻塞响应）
        await message_queue.publish(
            topic="tweet.fanout.write",
            payload={"tweet_id": tweet_id, "author_id": author_id}
        )
    else:
        # 大V：不做 Fan-out，只更新自己的推文索引
        await tweet_store.update_user_tweet_index(author_id, tweet_id)

    return tweet_id


async def get_home_timeline_hybrid(user_id: str, limit: int = 20) -> List[Tweet]:
    """
    混合策略时间线：预计算缓存 + 实时合并大V推文
    """
    # --- Part 1: 读取预计算的时间线缓存（普通用户的推文） ---
    cached_tweet_ids = await redis_client.lrange(
        f"timeline:{user_id}", 0, limit * 2 - 1  # 多取一些，合并后再截断
    )
    cached_tweets: List[Tweet] = await tweet_store.batch_get(cached_tweet_ids)

    # --- Part 2: 实时拉取该用户关注的大V的推文 ---
    following_ids = await social_graph.get_following(user_id)
    celebrity_ids = await filter_celebrities(following_ids)

    celebrity_tweet_tasks = [
        tweet_store.get_user_recent_tweets(celeb_id, limit=limit)
        for celeb_id in celebrity_ids
    ]
    celebrity_tweet_lists = await asyncio.gather(*celebrity_tweet_tasks)
    celebrity_tweets = [t for sublist in celebrity_tweet_lists for t in sublist]

    # --- Part 3: 归并两部分结果，按时间倒序排列 ---
    merged = merge_by_time(cached_tweets, celebrity_tweets)
    return merged[:limit]


async def filter_celebrities(user_ids: List[str]) -> List[str]:
    """
    从关注列表中筛选出大V（粉丝数超过阈值）
    可以缓存此结果，避免频繁查询
    """
    counts = await social_graph.batch_get_follower_counts(user_ids)
    return [uid for uid, count in zip(user_ids, counts)
            if count > CELEBRITY_THRESHOLD]


def merge_by_time(list_a: List[Tweet], list_b: List[Tweet]) -> List[Tweet]:
    """
    两个已按时间倒序排列的列表进行归并（双指针）
    """
    result = []
    i, j = 0, 0
    while i < len(list_a) and j < len(list_b):
        if list_a[i].created_at >= list_b[j].created_at:
            result.append(list_a[i])
            i += 1
        else:
            result.append(list_b[j])
            j += 1
    result.extend(list_a[i:])
    result.extend(list_b[j:])
    return result
```

#### 5.3.3 混合策略处理边缘情况

```python
async def handle_new_follower(follower_id: str, target_id: str) -> None:
    """
    当用户 A 新关注用户 B 时，需要将 B 的历史推文注入 A 的时间线缓存
    （仅针对普通用户 B）
    """
    follower_count = await social_graph.get_follower_count(target_id)

    if follower_count <= CELEBRITY_THRESHOLD:
        # 普通用户：将 B 最近的推文注入 A 的时间线缓存
        recent_tweets = await tweet_store.get_user_recent_tweets(
            target_id, limit=20
        )
        pipeline = redis_client.pipeline()
        for tweet in recent_tweets:
            pipeline.lpush(f"timeline:{follower_id}", tweet.tweet_id)
        pipeline.ltrim(f"timeline:{follower_id}", 0, 799)
        await pipeline.execute()
    # 大V：不需要操作，下次读时间线时会实时拉取


async def handle_unfollow(follower_id: str, target_id: str) -> None:
    """
    取关时，清理时间线缓存中来自该用户的推文
    （实践中通常惰性清理：时间线显示时过滤，或等缓存过期重建）
    """
    # 惰性策略：标记 target_id 为已取关，读时过滤
    await redis_client.sadd(f"unfollowed:{follower_id}", target_id)
    # 缓存的时间线不立刻清理，在下次重建时生效
```

### 5.4 存储层设计

#### 5.4.1 推文存储（Cassandra）

选择 Cassandra 的理由：

| 需求 | Cassandra 的匹配点 |
|------|-------------------|
| 高写入吞吐（~15,000 QPS） | LSM-Tree 结构，写入性能极高 |
| 时序数据（按时间查询推文） | 支持按分区键+排序键的高效范围查询 |
| 水平扩展 | 无单点，线性扩展 |
| 高可用 | 多数据中心复制，自动故障转移 |

推文表设计（Cassandra CQL）：

```sql
-- 推文主表：按用户ID分区，推文ID（雪花ID，天然有序）排序
CREATE TABLE tweets (
    user_id     BIGINT,
    tweet_id    BIGINT,        -- 雪花ID，高位为时间戳，天然按时间倒序
    content     TEXT,
    created_at  TIMESTAMP,
    like_count  COUNTER,
    retweet_count COUNTER,
    PRIMARY KEY (user_id, tweet_id)
) WITH CLUSTERING ORDER BY (tweet_id DESC);

-- 查询某用户最新20条推文（用户时间线）
SELECT * FROM tweets
WHERE user_id = ?
LIMIT 20;
```

#### 5.4.2 时间线缓存（Redis）

```python
# 数据结构：Redis List（双端链表）
# Key:   timeline:{user_id}
# Value: [tweet_id_1, tweet_id_2, ...]  按时间倒序（最新在最左）

# 写入（Fan-out 时）
LPUSH timeline:12345 "tweet_id_new"
LTRIM timeline:12345 0 799   # 保留最新 800 条

# 读取（获取时间线）
LRANGE timeline:12345 0 19   # 获取前 20 条

# TTL 管理
EXPIRE timeline:12345 604800  # 7天过期，不活跃用户缓存自动清理
```

为何选 Redis List 而非 Sorted Set：
- 时间线已经是有序的（按推文 ID 天然有序），List 的 O(1) 头插和 O(N) 范围读取完全满足需求。
- Sorted Set 的 score 排序在这里是冗余的，且内存占用更大。
- 若需要支持按 engagement score 排序的算法时间线，则改用 Sorted Set 更合适。

#### 5.4.3 社交关系存储（Redis Set + 图数据库）

```python
# Redis Set 存储关注关系（适合读多写少的热点关系）
# Key:   following:{user_id}  → 该用户关注的人的 ID 集合
# Key:   followers:{user_id}  → 该用户的粉丝 ID 集合

# 关注操作
SADD following:A B      # A 关注了 B
SADD followers:B A      # B 的粉丝列表新增 A

# 查询 A 的关注列表（Fan-out 时使用）
SMEMBERS following:A

# 查询 A 的粉丝列表（Fan-out on Write 时遍历）
SMEMBERS followers:A
```

**大规模粉丝列表的挑战：**
- 大V的 followers Set 可能有数千万个元素，`SMEMBERS` 会阻塞 Redis。
- 解决方案：使用 `SSCAN` 游标分批迭代，配合 Fan-out Worker 的分页处理。
- 对于超过 1,000 万粉丝的顶级大V，考虑使用专门的图数据库（如 Twitter 自研的 FlockDB）或将粉丝列表分片存储。

```python
async def get_followers_batched(user_id: str, batch_size: int = 1000):
    """
    分批获取粉丝列表，避免一次性加载数千万条目到内存
    """
    cursor = 0
    while True:
        cursor, batch = await redis_client.sscan(
            f"followers:{user_id}",
            cursor=cursor,
            count=batch_size
        )
        yield batch
        if cursor == 0:  # cursor 归零表示遍历完成
            break
```

#### 5.4.4 推文 ID 生成（雪花算法）

```python
import time
import threading


class SnowflakeIDGenerator:
    """
    雪花算法 ID 生成器
    64位结构：
    - 1位符号位（固定0）
    - 41位时间戳（毫秒，约69年）
    - 10位机器ID（最多1024台机器）
    - 12位序列号（每毫秒最多4096个ID）
    """
    EPOCH = 1640995200000  # 2022-01-01 00:00:00 UTC（自定义纪元）

    def __init__(self, machine_id: int):
        assert 0 <= machine_id < 1024, "machine_id 超出范围"
        self.machine_id = machine_id
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = threading.Lock()

    def generate(self) -> int:
        with self._lock:
            now = int(time.time() * 1000)  # 当前毫秒时间戳

            if now == self.last_timestamp:
                self.sequence = (self.sequence + 1) & 0xFFF  # 12位，最大4095
                if self.sequence == 0:
                    # 同一毫秒内 ID 耗尽，等到下一毫秒
                    while now <= self.last_timestamp:
                        now = int(time.time() * 1000)
            else:
                self.sequence = 0

            self.last_timestamp = now
            return (
                ((now - self.EPOCH) << 22) |
                (self.machine_id << 12) |
                self.sequence
            )
```

雪花 ID 的优势：
- 全局唯一，无需中央协调。
- 天然有序（高位为时间戳），完美支持游标翻页和 Cassandra 的时序排序。
- 生成效率极高（每毫秒 4096 个，单机 400 万/秒）。

### 5.5 Fan-out Service 详细设计

```
Kafka Topic: tweet.fanout
  │
  ▼
Fan-out Consumer Group（多个 Worker 并行消费）
  │
  ├── Worker 1 处理普通用户的消息
  ├── Worker 2 处理普通用户的消息
  └── Worker 3 处理普通用户的消息
        │
        ▼
     Social Graph Service（获取粉丝列表）
        │
        ▼
     Redis Pipeline（批量写入时间线缓存）
```

```python
import asyncio
from typing import List


class FanoutWorker:
    """
    Fan-out Worker：从 Kafka 消费发推事件，执行写扩散
    """

    async def process_message(self, message: dict) -> None:
        tweet_id = message["tweet_id"]
        author_id = message["author_id"]

        # 分批获取粉丝，避免内存溢出
        async for follower_batch in get_followers_batched(author_id, batch_size=1000):
            await self._fanout_to_batch(tweet_id, follower_batch)

    async def _fanout_to_batch(self, tweet_id: str, follower_ids: List[str]) -> None:
        """
        批量写入一批粉丝的时间线缓存（Redis Pipeline 减少网络往返）
        """
        pipeline = redis_client.pipeline(transaction=False)  # 非事务 Pipeline，性能更高

        for follower_id in follower_ids:
            key = f"timeline:{follower_id}"
            pipeline.lpush(key, tweet_id)
            pipeline.ltrim(key, 0, 799)

        await pipeline.execute()

        # 记录 Fan-out 进度（用于监控和重试）
        await metrics.record_fanout_batch(
            tweet_id=tweet_id,
            batch_size=len(follower_ids)
        )
```

**Fan-out 的背压控制：**

当大V（即使粉丝 < 10万 的普通用户，也可能有 5万 粉丝）连续发推时，Kafka 消费者可能积压。需要：
- 对 Fan-out Worker 设置合理的并发度（如每个 Worker 最多 100 个并发协程）。
- Kafka Topic 按 `author_id` 分区，保证同一作者的推文有序处理。
- 设置消费者 lag 告警，超过阈值时动态扩容 Worker 数量。

---

## 6. 权衡分析

### 6.1 三种 Fan-out 策略对比

| 维度 | Fan-out on Write | Fan-out on Read | 混合策略 |
|------|-----------------|-----------------|----------|
| 读时间线延迟 | < 10ms（O(1) 缓存） | 100~500ms（实时聚合） | < 50ms（缓存+小规模实时拉取） |
| 发推延迟影响 | 极小（异步 Fan-out） | 极小（只写一份） | 极小（异步） |
| 写放大倍数 | = 粉丝数（最坏情况千万倍） | 1倍（无放大） | = 普通粉丝数（大V不参与） |
| 存储成本 | 高（时间线缓存冗余） | 低 | 中（只缓存普通用户推文） |
| 大V支持 | 差（需特殊处理） | 天然支持 | 好（大V用读扩散） |
| 关注/取关一致性 | 需要主动更新缓存 | 天然一致 | 部分需要主动更新 |
| 实现复杂度 | 中 | 低 | 高 |
| 适用场景 | 粉丝数均匀分布 | 读少写多（不适合Twitter） | 存在明显粉丝分布不均 |

**架构师判断**：对于 Twitter 这样的产品，混合策略是唯一合理的选择。纯写扩散无法应对明星用户的写放大问题；纯读扩散则使读取延迟无法满足 200ms SLA。混合策略以复杂度换取了性能和成本的平衡。

### 6.2 时间线一致性分析

**最终一致性在此场景下是可接受的：**

| 一致性场景 | 影响 | 可接受性 |
|-----------|------|---------|
| 发推后 1~5 秒粉丝才看到 | 用户体验轻微损失 | 可接受（类似消息通知延迟） |
| 刚取关的用户推文仍短暂出现 | 轻微干扰 | 可接受（几秒后消失） |
| 新关注后未能立刻看到历史推文 | 轻微不完整感 | 可接受（刷新后补全） |
| 时间线排序轻微乱序 | 时间线 "跳跃" | 可接受（不影响核心功能） |

**不可接受的一致性问题：**
- 推文永久丢失（通过 Cassandra 持久化 + 多副本保证）。
- 时间线长期不更新（通过 TTL + 重建机制保证）。

```python
async def rebuild_timeline(user_id: str) -> None:
    """
    时间线重建：当缓存失效或用户长期不活跃重新激活时触发
    """
    following_ids = await social_graph.get_following(user_id)

    # 筛选普通用户（大V在读时实时拉取）
    normal_following = [
        uid for uid in following_ids
        if await social_graph.get_follower_count(uid) <= CELEBRITY_THRESHOLD
    ]

    # 并发拉取每个关注者的最新推文
    tasks = [
        tweet_store.get_user_recent_tweets(uid, limit=20)
        for uid in normal_following
    ]
    all_tweet_lists = await asyncio.gather(*tasks)
    all_tweets = [t for sublist in all_tweet_lists for t in sublist]

    # 排序后取最新 800 条
    all_tweets.sort(key=lambda t: t.tweet_id, reverse=True)
    top_tweets = all_tweets[:800]

    # 写入 Redis
    pipeline = redis_client.pipeline()
    key = f"timeline:{user_id}"
    pipeline.delete(key)
    for tweet in top_tweets:
        pipeline.rpush(key, tweet.tweet_id)  # 尾部插入维持顺序
    pipeline.expire(key, 7 * 24 * 3600)
    await pipeline.execute()
```

### 6.3 热点用户（大V）的特殊处理

大V的挑战不仅仅是 Fan-out 的写放大，还包括：

#### 问题 1：大V推文读取热点

当大V发推后，短时间内大量粉丝刷新时间线，导致对大V推文的读请求激增（"热读"）。

**解决方案：推文级别缓存**

```python
async def get_tweet_with_cache(tweet_id: str) -> Tweet:
    """
    推文详情缓存：减少对 Cassandra 的热点读压力
    """
    cache_key = f"tweet:{tweet_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return deserialize(cached)

    tweet = await cassandra_client.get_tweet(tweet_id)
    await redis_client.setex(cache_key, 3600, serialize(tweet))  # 缓存1小时
    return tweet
```

#### 问题 2：大V的粉丝列表超大

即使不做 Fan-out，每次读取大V粉丝数量（用于监控或其他目的）也可能很慢。

**解决方案：** 单独维护粉丝数计数器（Redis 计数器），不依赖 `SCARD` 命令实时统计。

```python
# 关注时：计数器 +1
INCR follower_count:{user_id}

# 取关时：计数器 -1
DECR follower_count:{user_id}

# 读取时：O(1) 获取，不需要扫描整个 Set
GET follower_count:{user_id}
```

#### 问题 3：大V阈值的动态调整

固定阈值（10万粉丝）可能不够灵活：一个粉丝数 9.9 万的用户发推，Fan-out 9.9 万次，与 10.1 万次的大V差别很小，却走了完全不同的路径。

**解决方案：** 允许动态更新阈值；对于临界值附近的用户，采用渐进式迁移（逐步缩减 Fan-out 规模，同时开启部分读扩散）。

### 6.4 数据库选型对比

| 数据库 | 用途 | 选型理由 |
|--------|------|---------|
| Cassandra | 推文持久化存储 | 高写入吞吐、时序数据优化、线性扩展、多数据中心 |
| Redis（List） | 时间线缓存 | 极低延迟、List 语义完美匹配、内存数据库 |
| Redis（Set） | 社交关系热数据 | 集合操作（SISMEMBER、SMEMBERS）O(1) |
| MySQL / PostgreSQL | 用户账户信息 | 强一致性需求（登录、鉴权），数据量小 |
| Kafka | Fan-out 消息队列 | 高吞吐、持久化、消费者组并行消费 |
| Elasticsearch | 全文检索（推文搜索） | 倒排索引、全文搜索 |

### 6.5 缓存策略选择

| 策略 | 描述 | 适用推文时间线的场景 |
|------|------|---------------------|
| Cache-Aside | 应用层控制缓存读写，Miss 时加载 | 推文详情缓存（读多写少） |
| Write-Through | 写数据库同时写缓存 | 不适合（写放大问题） |
| Write-Behind | 先写缓存，异步写数据库 | 有数据丢失风险，不适合推文持久化 |
| Read-Through | 缓存层透明处理 Miss | 可用于时间线缓存，但需要缓存层理解业务逻辑 |

推文时间线采用 **Cache-Aside + 异步预热** 的组合：
- 正常读：Cache-Aside（先查缓存，Miss 时触发重建）。
- 用户首次登录或长期不活跃后重新激活：主动异步预热时间线缓存。

---

## 7. 总结

### 架构设计全景

```
┌────────────────────────────────────────────────────────────────────┐
│                        Twitter Feed 系统架构                         │
│                                                                    │
│  客户端 ──► API Gateway ──► Tweet Service ──► Cassandra（持久化）   │
│                    │              │                                 │
│                    │         Kafka Queue                            │
│                    │              │                                 │
│                    │        Fan-out Workers                         │
│                    │         ├── 普通用户 ──► Redis List（时间线）   │
│                    │         └── 大V用户 ──► 跳过 Fan-out           │
│                    │                                                │
│                    └──► Timeline Service                            │
│                              ├── Redis（预计算时间线，快速路径）       │
│                              ├── 实时拉取大V推文（慢速路径）           │
│                              └── 归并排序 → 返回结果                 │
└────────────────────────────────────────────────────────────────────┘
```

### Key Architect Takeaways

**1. 读写比决定架构方向**

当系统读写比达到 100:1 时，架构的首要目标是优化读路径，而不是写路径。Fan-out on Write 以牺牲写放大换取读时间线 O(1) 的极致性能，是高读写比场景下的正确权衡。任何在读时间线上引入实时计算的方案，都必须严格评估其延迟代价。

**2. 数据分布不均匀是系统设计的最大挑战**

Twitter 粉丝数服从幂律分布（少数用户拥有绝大多数粉丝），这使得单一策略（纯写扩散或纯读扩散）都会在某个极端情况下崩溃。混合策略的本质是：**识别数据分布的不均匀性，并为不同的数据段设计不同的路径**。这个思路（按数据特征分层处理）在缓存设计、分库分表、微服务拆分中普遍适用。

**3. 异步解耦是应对写放大的核心手段**

Fan-out 的写放大（最坏情况千万倍）如果同步执行，会使发推 API 的延迟变得不可控。通过消息队列（Kafka）将 Fan-out 异步化，发推操作的延迟与粉丝数量完全解耦，系统的可伸缩性从线性变为近乎独立。异步解耦的代价是引入了最终一致性，但对于社交时间线场景，这是完全可以接受的权衡。

**4. 阈值设计需要数据驱动，并预留调整机制**

大V阈值（10万粉丝）不是一个神圣的数字，而是基于系统容量和业务指标的工程决策。随着系统规模增长、Redis 容量变化、Fan-out Worker 能力提升，这个阈值可能需要调整。架构设计时应将阈值作为可配置的运行时参数（Feature Flag），而非硬编码常量，以支持无需重新部署即可调整策略。这体现了架构的可运维性（Operability）原则。
