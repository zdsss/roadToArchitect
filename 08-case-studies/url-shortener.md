# 案例研究：URL 短链服务设计

> 架构视角：从需求到生产级系统的完整推演

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

设计一个 URL 短链服务（类似 bit.ly、TinyURL）是系统设计面试中的经典题目。它的价值不在于"难"，而在于它覆盖了分布式系统的几乎所有核心问题：唯一 ID 生成、高并发读写、缓存策略、重定向语义选择。架构师需要在动手之前把需求彻底梳理清楚。

### 1.1 功能需求（Functional Requirements）

**核心功能（必须实现）**

| 功能 | 描述 | 优先级 |
|------|------|--------|
| 长链转短链 | 用户输入一个长 URL，系统返回唯一的短链 | P0 |
| 短链重定向 | 用户访问短链时，系统将其重定向到原始长 URL | P0 |
| 自定义短码 | 用户可以指定自己想要的短码（如 `/my-brand`） | P1 |
| 过期时间 | 短链可以设置有效期，过期后自动失效 | P1 |
| 删除短链 | 创建者可以删除自己的短链 | P2 |

**扩展功能（暂不实现，但需要在设计中预留扩展点）**

- 点击统计与分析（按地区、设备、时间维度）
- 用户账号与鉴权
- API 速率限制（Rate Limiting）
- 二维码生成

### 1.2 非功能需求（Non-Functional Requirements）

**高可用性**

短链服务是典型的**读多写少**场景。一旦短链被分发出去（写入），后续会被大量用户点击（读取）。任何读请求失败都会导致用户看到错误页面，直接影响业务方的转化率。因此：

- 系统可用性目标：**99.99%**（每年停机时间 < 52 分钟）
- 读路径（重定向）必须优先保证可用，允许短暂的最终一致性
- 写路径（创建短链）可以接受略高的延迟

**低延迟**

- 短链重定向延迟：**< 10ms**（P99）——用户感知不到跳转的停顿
- 短链创建延迟：**< 200ms**（P99）——可以接受略高延迟

**可扩展性**

- 水平扩展（Horizontal Scaling）：应用层无状态，可以任意增加节点
- 数据层需要在设计阶段就考虑分片（Sharding）策略
- 不能有单点故障（Single Point of Failure）

**数据持久性**

- 短链一旦创建，在有效期内不能丢失
- 数据库层需要主从复制或多副本机制

### 1.3 系统边界澄清（Scope Clarification）

在面试或实际设计中，以下问题需要在开始之前明确：

- 短码长度是固定的还是可变的？→ 本设计选择**固定 7 位**
- 短码字符集是什么？→ 本设计选择 **Base62**（`a-z`, `A-Z`, `0-9`）
- 自定义短码是否需要额外付费或鉴权？→ 本设计假设**已登录用户才能自定义**
- 同一个长 URL 多次提交是否返回同一个短链？→ 本设计选择**每次创建新短链**（幂等性可作为扩展）

---

## 2. 规模估算

规模估算（Back-of-the-Envelope Estimation）是架构设计的起点。它帮助我们在技术选型之前就确定系统的量级，从而判断哪些优化是必要的，哪些是过度设计。

### 2.1 基础假设

| 参数 | 假设值 | 说明 |
|------|--------|------|
| 每日新建短链数 | 1 亿条 / 天 | 类比 Twitter 每日推文量级 |
| 读写比 | 100 : 1 | 每条短链平均被访问 100 次 |
| 短链保留年限 | 5 年 | 超出有效期自动清理 |
| 每条记录大小 | ~500 字节 | 详见存储估算 |

### 2.2 QPS 估算

**写入 QPS（短链创建）**

```
每日写入量：100,000,000 条 / 天
每秒写入量：100,000,000 / 86,400 ≈ 1,157 次/秒 ≈ 1.2K 写 QPS
```

**读取 QPS（短链访问）**

```
读写比 100:1，每日读取量：100,000,000 × 100 = 100 亿次 / 天
每秒读取量：10,000,000,000 / 86,400 ≈ 115,740 次/秒 ≈ 116K 读 QPS
```

峰值流量通常是平均值的 2-5 倍，因此：
- **峰值写入 QPS**：约 6K/s
- **峰值读取 QPS**：约 580K/s

### 2.3 存储估算

**单条记录大小估算**

| 字段 | 类型 | 大小 |
|------|------|------|
| `short_code` | VARCHAR(7) | 7 字节 |
| `original_url` | VARCHAR(2048) | 平均 200 字节 |
| `user_id` | BIGINT | 8 字节 |
| `created_at` | TIMESTAMP | 8 字节 |
| `expires_at` | TIMESTAMP | 8 字节 |
| 索引开销 | 估算 | ~250 字节 |
| **合计** | | **~500 字节/条** |

**总存储量**

```
每日写入：100,000,000 条 × 500 字节 = 50 GB / 天
5 年总量：50 GB × 365 × 5 ≈ 91 TB
```

结论：**存储不是瓶颈**，91 TB 对于现代分布式存储完全可控。真正的挑战在于**读取的高并发**（116K+ QPS）。

### 2.4 带宽估算

**写入带宽**

```
1.2K 写 QPS × 500 字节/请求 ≈ 0.6 MB/s（可忽略）
```

**读取带宽**

```
重定向响应体极小（HTTP 302，仅 Header），约 500 字节/次
116K 读 QPS × 500 字节 ≈ 58 MB/s ≈ 0.5 Gbps
```

**结论汇总**

| 维度 | 估算值 | 设计影响 |
|------|--------|----------|
| 写 QPS | ~1.2K（峰值 6K） | 单机数据库可承受，无需立即分片 |
| 读 QPS | ~116K（峰值 580K） | 必须引入缓存层 |
| 存储 5 年 | ~91 TB | 需要分布式存储或归档策略 |
| 读带宽 | ~0.5 Gbps | 标准 CDN/负载均衡可处理 |

---

## 3. API 设计

API 设计需要遵循 RESTful 原则，同时考虑幂等性、错误处理和版本化。

### 3.1 创建短链

**请求**

```
POST /api/v1/urls
Content-Type: application/json
Authorization: Bearer <token>  （可选，用于自定义短码功能）
```

**请求体**

```python
# 请求体结构（Python 伪代码表示）
request_body = {
    "original_url": "https://www.example.com/very/long/path?param=value",  # 必填
    "custom_code": "my-link",      # 可选，用户自定义短码
    "expires_in_days": 30,         # 可选，过期天数，默认永不过期
}
```

**响应（成功 201 Created）**

```python
response_body = {
    "short_code": "aB3dEfG",
    "short_url": "https://short.ly/aB3dEfG",
    "original_url": "https://www.example.com/very/long/path?param=value",
    "created_at": "2026-03-26T10:00:00Z",
    "expires_at": "2026-04-25T10:00:00Z",  # null 表示永不过期
}
```

**错误响应**

| HTTP 状态码 | 场景 |
|-------------|------|
| 400 Bad Request | `original_url` 格式非法 |
| 409 Conflict | 自定义短码已被占用 |
| 422 Unprocessable Entity | 请求体字段缺失或类型错误 |
| 429 Too Many Requests | 超过速率限制 |

### 3.2 短链重定向

**请求**

```
GET /{short_code}
```

这个端点是整个系统中**调用量最大**的接口，116K+ QPS 全部落在这里。

**响应（成功）**

```
HTTP/1.1 301 Moved Permanently   或   HTTP/1.1 302 Found
Location: https://www.example.com/very/long/path?param=value
Cache-Control: max-age=86400
```

> 301 vs 302 的选择是本设计中最重要的权衡之一，详见第 4 节和第 6 节。

**错误响应**

| HTTP 状态码 | 场景 |
|-------------|------|
| 404 Not Found | 短码不存在 |
| 410 Gone | 短链已过期或被删除 |

### 3.3 删除短链（可选）

**请求**

```
DELETE /api/v1/urls/{short_code}
Authorization: Bearer <token>
```

**响应**

```
HTTP/1.1 204 No Content
```

**权限规则**：只有短链的创建者或系统管理员可以删除。

### 3.4 查询短链信息（可选）

**请求**

```
GET /api/v1/urls/{short_code}/info
Authorization: Bearer <token>
```

**响应**

```python
response_body = {
    "short_code": "aB3dEfG",
    "original_url": "https://www.example.com/...",
    "created_at": "2026-03-26T10:00:00Z",
    "expires_at": None,
    "click_count": 42187,  # 如果实现了统计功能
}
```

---

## 4. 高层设计

### 4.1 系统组件概览

```
客户端（Browser / App）
        │
        ▼
  ┌─────────────┐
  │ Load Balancer│  （Nginx / AWS ALB）
  └──────┬──────┘
         │
         ▼
  ┌──────────────┐
  │  URL Service │  （无状态应用层，多实例）
  │  (多实例部署) │
  └──────┬───────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐  ┌──────────┐
│ Cache │  │ Database │
│(Redis)│  │(PostgreSQL│
└───────┘  │/ DynamoDB)│
           └──────────┘
```

**各组件职责**

| 组件 | 技术选型 | 职责 |
|------|----------|------|
| Load Balancer | Nginx / AWS ALB | 流量分发，SSL 终止，健康检查 |
| URL Service | Go / Python（无状态） | 业务逻辑：短码生成、重定向、过期检查 |
| Cache | Redis Cluster | 热点短链缓存，降低数据库压力 |
| Database | PostgreSQL / DynamoDB | 持久化存储，主从复制 |
| ID Generator | Snowflake / 数据库自增 | 分布式唯一 ID 生成 |

### 4.2 读路径（重定向流程）

```python
def redirect(short_code: str) -> str:
    """
    重定向流程（Python 伪代码）
    目标：将延迟控制在 10ms 以内
    """
    # 步骤 1：查询缓存（Redis，~1ms）
    original_url = cache.get(short_code)

    if original_url is None:
        # 步骤 2：缓存未命中，查询数据库（~5ms）
        record = db.query("SELECT original_url, expires_at FROM urls WHERE short_code = ?", short_code)

        if record is None:
            raise NotFoundException(f"Short code {short_code} not found")

        # 步骤 3：检查过期时间
        if record.expires_at and record.expires_at < now():
            raise GoneException(f"Short code {short_code} has expired")

        original_url = record.original_url

        # 步骤 4：回写缓存（Cache-Aside 模式）
        ttl = compute_ttl(record.expires_at)  # 根据过期时间设置缓存 TTL
        cache.set(short_code, original_url, ttl=ttl)

    # 步骤 5：返回重定向响应
    return redirect_response(original_url, status_code=302)
```

### 4.3 写路径（创建短链流程）

```python
def create_short_url(original_url: str, custom_code: str = None, expires_in_days: int = None) -> dict:
    """
    创建短链流程（Python 伪代码）
    """
    # 步骤 1：验证输入
    if not is_valid_url(original_url):
        raise BadRequestException("Invalid URL format")

    # 步骤 2：处理自定义短码
    if custom_code:
        if db.exists("SELECT 1 FROM urls WHERE short_code = ?", custom_code):
            raise ConflictException(f"Custom code '{custom_code}' is already taken")
        short_code = custom_code
    else:
        # 步骤 3：生成短码（详见第 5 节）
        short_code = generate_short_code()

    # 步骤 4：计算过期时间
    expires_at = now() + timedelta(days=expires_in_days) if expires_in_days else None

    # 步骤 5：写入数据库
    db.insert("INSERT INTO urls (short_code, original_url, expires_at, created_at) VALUES (?, ?, ?, ?)",
              short_code, original_url, expires_at, now())

    return {
        "short_code": short_code,
        "short_url": f"https://short.ly/{short_code}",
        "original_url": original_url,
        "expires_at": expires_at,
    }
```

### 4.4 301 vs 302 重定向的选择

这是本设计中一个典型的**架构权衡**，没有绝对正确答案，取决于业务优先级。

| 维度 | 301 Moved Permanently | 302 Found |
|------|----------------------|-----------|
| 浏览器行为 | 缓存重定向结果，后续直接跳转不请求服务器 | 每次都请求服务器 |
| 服务器压力 | 低（用户再次访问不产生服务器请求） | 高（每次访问都经过服务器） |
| 点击统计 | 无法统计（浏览器直接跳转） | 可以在服务器端记录每次点击 |
| 链接变更 | 危险：用户浏览器长期缓存旧目标，无法修改 | 安全：可以随时修改目标 URL |
| 适用场景 | 纯跳转服务，不需要统计，追求极低延迟 | 需要点击统计、A/B 测试、动态修改目标 |

**本设计的选择**：使用 **302**，原因如下：

1. 业务方通常需要点击统计，这是短链服务的核心价值之一
2. 支持目标 URL 的修改（如营销活动临时调整落地页）
3. 302 的服务器压力通过缓存层（Redis）来吸收，延迟仍可控制在 10ms 以内

---

## 5. 组件深入

### 5.1 短码生成算法对比

短码生成是整个系统的核心难题。我们需要在**唯一性**、**安全性**、**性能**和**实现复杂度**之间取得平衡。

#### 算法一：随机生成（UUID 截取）

```python
import uuid

def generate_code_random(length: int = 7) -> str:
    """
    方案一：UUID 截取
    原理：生成 UUID，取前 length 位字符
    """
    # 生成 UUID4（随机），去掉连字符
    full_uuid = uuid.uuid4().hex  # e.g., "a1b2c3d4e5f6..."
    return full_uuid[:length]      # e.g., "a1b2c3"

# 问题：冲突检测（必须有）
def create_with_collision_check(original_url: str) -> str:
    max_retries = 5
    for attempt in range(max_retries):
        candidate = generate_code_random()
        if not db.exists(candidate):
            db.insert(candidate, original_url)
            return candidate
    raise Exception("Failed to generate unique code after max retries")
```

**分析**

| 维度 | 评估 |
|------|------|
| 唯一性 | 7 位十六进制：16^7 ≈ 2.7 亿种，空间不足！ |
| 冲突概率 | 存储 1 亿条后，每次新生成约 37% 概率冲突 |
| 实现复杂度 | 低，但需要数据库冲突检测，高并发下有竞争 |
| 结论 | **不推荐**，冲突率随数据量增长急剧上升 |

#### 算法二：Base62 编码（推荐方案之一）

Base62 使用 `a-z`（26）+ `A-Z`（26）+ `0-9`（10）= 62 个字符。

**7 位 Base62 的组合空间**：

```
62^7 = 3,521,614,606,208 ≈ 3.5 万亿种组合
```

这远超我们 5 年内 `100M × 365 × 5 = 1825 亿`条记录的需求，有足够的空间冗余。

```python
import random
import string

BASE62_CHARS = string.digits + string.ascii_letters  # "0123456789abcdef...xyz..."

def encode_base62(num: int) -> str:
    """
    将整数编码为 Base62 字符串
    这是 Base62 的核心转换函数（类似十进制转十六进制）
    """
    if num == 0:
        return BASE62_CHARS[0]

    result = []
    while num > 0:
        remainder = num % 62
        result.append(BASE62_CHARS[remainder])
        num //= 62

    return ''.join(reversed(result))

def decode_base62(encoded: str) -> int:
    """
    将 Base62 字符串解码为整数
    """
    result = 0
    for char in encoded:
        result = result * 62 + BASE62_CHARS.index(char)
    return result

def generate_code_base62_random(length: int = 7) -> str:
    """
    纯随机 Base62：直接随机选择 length 个 Base62 字符
    组合空间：62^7 ≈ 3.5 万亿
    """
    return ''.join(random.choices(BASE62_CHARS, k=length))
```

**纯随机 Base62 的冲突分析（生日悖论）**

```python
# 生日悖论：在 n 个位置中随机选 k 个，产生冲突的概率约为 k^2 / (2n)
# n = 62^7 ≈ 3.5 万亿
# k = 1825 亿（5 年写入总量）
# 冲突概率 ≈ (1825亿)^2 / (2 × 3.5万亿) ≈ 极低，可接受

collision_probability = (182_500_000_000 ** 2) / (2 * 3_521_614_606_208)
# ≈ 4.73 × 10^12，即约 4.7 万亿次中冲突一次
# 实际上冲突概率非常低，但仍然需要冲突检测机制
```

#### 算法三：哈希（MD5/SHA256 截取）

```python
import hashlib

def generate_code_hash(original_url: str, length: int = 7) -> str:
    """
    方案三：MD5/SHA256 哈希截取
    原理：对原始 URL 哈希，取前若干字符
    """
    # 使用 SHA256 哈希
    hash_bytes = hashlib.sha256(original_url.encode()).hexdigest()

    # 将 16 进制哈希转换为 Base62
    hash_int = int(hash_bytes[:16], 16)  # 取前 16 位十六进制 → 整数
    short_code = encode_base62(hash_int)[:length]

    return short_code

# 哈希方案的冲突检测（不同 URL 可能产生相同截取后的哈希）
def create_with_hash(original_url: str) -> str:
    base_code = generate_code_hash(original_url)

    if not db.exists(base_code):
        db.insert(base_code, original_url)
        return base_code

    # 冲突：在 URL 后加盐重试
    for salt in range(1, 10):
        salted_url = f"{original_url}_{salt}"
        candidate = generate_code_hash(salted_url)
        if not db.exists(candidate):
            db.insert(candidate, original_url)
            return candidate

    raise Exception("Hash collision unresolvable")
```

**哈希方案的问题**

| 问题 | 描述 |
|------|------|
| 同 URL 不同短链 | 同一长 URL 每次传入都生成相同短码（可能是优点也是缺点） |
| 截取冲突 | 不同 URL 截取后的前 7 位可能相同 |
| 依赖数据库检查 | 必须查数据库确认冲突，高并发下有竞争条件 |

#### 算法四：自增 ID + Base62 编码（推荐，生产首选）

这是最简单、最可靠的方案。核心思路：**每条记录对应一个全局唯一的自增整数，将该整数编码为 Base62 字符串作为短码**。

```python
def generate_code_from_id(unique_id: int) -> str:
    """
    方案四（推荐）：自增 ID → Base62 编码

    示例：
    - ID = 1         → Base62 = "1"
    - ID = 62        → Base62 = "10"
    - ID = 1,000,000 → Base62 = "4c92"
    - ID = 62^7 - 1  → Base62 = "zzzzzzz"（7位上限）

    62^7 ≈ 3.5 万亿，足够支撑 5 年 1825 亿条记录
    """
    return encode_base62(unique_id)

# 完整的创建流程
def create_short_url_v2(original_url: str) -> dict:
    """
    推荐方案的完整实现
    """
    # 步骤 1：从 ID 生成器获取全局唯一 ID
    # 方式 A：数据库自增主键（简单，单机适用）
    unique_id = db.insert_and_get_id(
        "INSERT INTO urls (original_url, created_at) VALUES (?, ?)",
        original_url, now()
    )

    # 步骤 2：将 ID 转换为 Base62 短码
    short_code = generate_code_from_id(unique_id)

    # 步骤 3：将短码写回记录（或直接在应用层计算，不存数据库）
    db.update("UPDATE urls SET short_code = ? WHERE id = ?", short_code, unique_id)

    return {
        "short_code": short_code,
        "short_url": f"https://short.ly/{short_code}",
    }
```

**自增 ID 方案的优势**

| 优势 | 说明 |
|------|------|
| 天然唯一 | 数据库自增主键保证全局唯一，无需冲突检测 |
| 无随机冲突 | ID → Base62 是确定性映射，不存在哈希碰撞 |
| 实现简单 | 不需要额外的冲突重试逻辑 |
| 可预测长度 | 10 亿条记录对应 Base62 长度约 5 位，远小于 7 位上限 |

**自增 ID 方案的劣势（及缓解措施）**

| 劣势 | 缓解措施 |
|------|----------|
| 短码可预测（顺序性） | 对 ID 进行简单混淆（XOR、乘以质数）再编码 |
| 单机自增瓶颈 | 使用分布式 ID 生成器（Snowflake） |
| 暴露业务量 | 混淆 ID 或直接接受（大多数场景不在意） |

```python
def obfuscate_id(raw_id: int) -> int:
    """
    ID 混淆：防止短码顺序可预测
    使用一个大质数做乘法混淆 + XOR
    """
    PRIME = 1_000_000_007
    XOR_MASK = 0x5A5A5A5A

    obfuscated = (raw_id * PRIME) ^ XOR_MASK
    # 限制在合理范围内（避免 Base62 编码过长）
    obfuscated = obfuscated % (62 ** 7)
    return obfuscated

def generate_code_obfuscated(raw_id: int) -> str:
    """混淆后的短码生成"""
    obfuscated = obfuscate_id(raw_id)
    return encode_base62(obfuscated).zfill(7)[:7]
```

**算法对比总结**

| 算法 | 唯一性 | 冲突处理 | 实现复杂度 | 推荐度 |
|------|--------|----------|------------|--------|
| UUID 截取 | 低（16^7） | 需要重试 | 低 | 不推荐 |
| 纯随机 Base62 | 高（62^7） | 需要重试 | 低 | 可用 |
| 哈希截取 | 中 | 需要加盐重试 | 中 | 不推荐 |
| 自增 ID + Base62 | 极高 | 无需处理 | 低 | **强烈推荐** |
| Snowflake + Base62 | 极高 | 无需处理 | 高 | 推荐（大规模） |

### 5.2 数据库选型

**数据库表结构**

```python
# PostgreSQL 表设计
CREATE_TABLE_SQL = """
CREATE TABLE urls (
    id          BIGSERIAL PRIMARY KEY,          -- 自增主键，用于 Base62 编码
    short_code  VARCHAR(10) UNIQUE NOT NULL,    -- 短码，唯一索引
    original_url TEXT NOT NULL,                 -- 原始长 URL
    user_id     BIGINT,                         -- 创建者 ID（可为空）
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ,                    -- NULL 表示永不过期
    is_deleted  BOOLEAN NOT NULL DEFAULT FALSE  -- 软删除标志
);

-- 查询短码时的主要索引
CREATE INDEX idx_short_code ON urls (short_code) WHERE is_deleted = FALSE;

-- 过期清理任务的索引
CREATE INDEX idx_expires_at ON urls (expires_at) WHERE expires_at IS NOT NULL;
"""
```

**关系型数据库（PostgreSQL）vs 键值存储（DynamoDB）**

| 维度 | PostgreSQL | DynamoDB |
|------|-----------|---------|
| 数据模型 | 关系型，支持复杂查询 | KV/文档，查询能力有限 |
| 读写性能 | 单机 ~10K QPS，需要主从 | 近乎无限水平扩展 |
| 一致性 | 强一致性（ACID） | 最终一致性（可选强一致） |
| 运维复杂度 | 高（需要 DBA 维护） | 低（全托管） |
| 成本 | 低（自托管） | 按用量计费，高并发成本高 |
| 适合场景 | 中小规模，需要复杂查询 | 超大规模，查询模式固定 |

**本设计的选择**：

- **初期（< 10K 写 QPS）**：PostgreSQL + 主从复制，简单可靠
- **成长期（> 50K 写 QPS）**：迁移至 DynamoDB 或 PostgreSQL + 分片

URL 短链服务的查询模式极其简单（按 `short_code` 查询），天然适合 KV 存储。但初期选择 PostgreSQL 可以获得更强的数据一致性保证和更低的运维成本。

### 5.3 缓存策略

**缓存模式：Cache-Aside（旁路缓存）**

```python
def get_original_url(short_code: str) -> str:
    """
    Cache-Aside 模式实现（Python 伪代码）

    读操作：先读缓存，未命中再读数据库，然后回填缓存
    写操作：写数据库，然后使缓存失效（或直接写缓存）
    """
    # 读：Cache-Aside
    cached = redis.get(f"url:{short_code}")
    if cached:
        return cached  # 缓存命中

    # 缓存未命中：读数据库
    record = db.query_by_short_code(short_code)
    if not record:
        # 缓存空结果防止缓存穿透
        redis.setex(f"url:{short_code}", 60, "__NOT_FOUND__")
        raise NotFoundException()

    # 回填缓存
    ttl = min(86400, seconds_until(record.expires_at))  # 最多缓存 1 天
    redis.setex(f"url:{short_code}", ttl, record.original_url)

    return record.original_url

def delete_url(short_code: str):
    """
    写操作：删除时使缓存失效
    """
    db.soft_delete(short_code)
    redis.delete(f"url:{short_code}")  # 使缓存失效
```

**缓存热点分析**

短链服务天然存在**长尾分布**（80% 的流量来自 20% 的短链），缓存命中率极高。

```python
# 缓存容量估算
# 热点 URL 占总量 20%，即 1825 亿 × 20% = 365 亿条
# 但真正的"热点"（每天被访问超过 1000 次）估计只有 1% 的短链
# 即 1825 亿 × 1% = 18.25 亿条 × 500 字节 ≈ 912 GB
# 实际可以先从 10GB Redis 开始，监控命中率动态扩容

CACHE_CONFIG = {
    "max_memory": "10gb",
    "eviction_policy": "allkeys-lru",  # 最近最少使用驱逐策略
    "key_prefix": "url:",
    "default_ttl": 86400,  # 24 小时
}
```

**缓存穿透防护**

```python
def get_with_penetration_guard(short_code: str) -> str:
    """
    防止缓存穿透：对不存在的 key 也缓存空值
    """
    cached = redis.get(f"url:{short_code}")

    if cached == "__NOT_FOUND__":
        raise NotFoundException()  # 快速失败，不查数据库

    if cached:
        return cached

    # 真正查数据库
    record = db.query_by_short_code(short_code)
    if not record:
        redis.setex(f"url:{short_code}", 60, "__NOT_FOUND__")  # 缓存空结果 60 秒
        raise NotFoundException()

    redis.setex(f"url:{short_code}", 86400, record.original_url)
    return record.original_url
```

### 5.4 分布式 ID 生成（水平扩展场景）

当写入 QPS 超过单机数据库自增的能力（约 5-10K/s），需要引入分布式 ID 生成器。

**Snowflake 算法**

```python
import time
import threading

class SnowflakeIDGenerator:
    """
    Twitter Snowflake 算法（Python 伪代码）
    64 位 ID 结构：
    - 1  位：符号位（始终为 0）
    - 41 位：毫秒时间戳（可用约 69 年）
    - 10 位：机器 ID（最多 1024 台机器）
    - 12 位：序列号（每毫秒最多 4096 个 ID）
    """

    EPOCH = 1_700_000_000_000  # 自定义纪元（2023-11-14）
    MACHINE_ID_BITS = 10
    SEQUENCE_BITS = 12
    MAX_MACHINE_ID = (1 << MACHINE_ID_BITS) - 1   # 1023
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1         # 4095

    def __init__(self, machine_id: int):
        assert 0 <= machine_id <= self.MAX_MACHINE_ID
        self.machine_id = machine_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()

    def generate(self) -> int:
        with self.lock:
            current_ms = int(time.time() * 1000) - self.EPOCH

            if current_ms == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    # 序列号溢出，等待下一毫秒
                    while current_ms <= self.last_timestamp:
                        current_ms = int(time.time() * 1000) - self.EPOCH
            else:
                self.sequence = 0

            self.last_timestamp = current_ms

            # 组装 64 位 ID
            snowflake_id = (
                (current_ms << (self.MACHINE_ID_BITS + self.SEQUENCE_BITS)) |
                (self.machine_id << self.SEQUENCE_BITS) |
                self.sequence
            )
            return snowflake_id

# 每个应用实例创建一个生成器，machine_id 由配置中心分配
id_generator = SnowflakeIDGenerator(machine_id=1)

def create_url_distributed(original_url: str) -> dict:
    """使用 Snowflake ID 的分布式创建流程"""
    unique_id = id_generator.generate()      # 本地生成，无网络调用
    short_code = generate_code_from_id(unique_id)

    db.insert(short_code, original_url, unique_id)

    return {"short_code": short_code, "short_url": f"https://short.ly/{short_code}"}
```

**Snowflake 的优势**：每毫秒每台机器最多生成 4096 个 ID，1024 台机器合计 **4096 × 1024 × 1000 = 约 42 亿/秒**，远超实际需求。

---

## 6. 权衡分析

架构设计的本质是做有意识的权衡。本节将本设计中的所有重要决策及其替代方案并排比较。

### 6.1 短码方案：自增 ID vs 随机码

| 维度 | 自增 ID + Base62 | 纯随机 Base62 |
|------|-----------------|--------------|
| 唯一性保证 | 数据库/Snowflake 保证，天然唯一 | 概率保证，需要冲突检测 |
| 短码可预测性 | 顺序可预测（可混淆缓解） | 不可预测 |
| 实现复杂度 | 低 | 低，但需冲突重试逻辑 |
| 高并发写入 | 需要分布式 ID 生成器 | 无中心依赖，但冲突率随数据量上升 |
| 安全性 | 混淆后可接受 | 更好 |
| **推荐场景** | **大多数生产场景** | **短期项目或极低数据量** |

**决策**：选择自增 ID + Base62，配合 ID 混淆消除可预测性问题。

### 6.2 重定向语义：301 vs 302

| 维度 | 301 永久重定向 | 302 临时重定向 |
|------|--------------|--------------|
| 浏览器缓存 | 长期缓存，后续访问不到服务器 | 不缓存（或短期缓存） |
| 服务器负载 | 首次后极低 | 每次都需要服务器处理 |
| 点击统计 | 无法统计（浏览器直接跳转） | 每次服务器可记录 |
| 目标 URL 可变更 | 不可（缓存无法清除） | 可以随时变更 |
| SEO 影响 | 权重转移至目标页 | 权重保留在短链 |
| **推荐场景** | **纯跳转、极致性能优先** | **需要统计、运营灵活性** |

**决策**：选择 302，业务价值（统计、可变更）优先于性能（由 Redis 缓存补偿）。

### 6.3 数据库选型：SQL vs NoSQL

| 维度 | PostgreSQL（SQL） | DynamoDB（NoSQL） |
|------|-----------------|-----------------|
| 一致性 | 强一致性（ACID） | 最终一致性（默认） |
| 查询灵活性 | 高（支持复杂 JOIN、聚合） | 低（仅按主键/索引查询） |
| 水平扩展 | 需要手动分片，运维复杂 | 原生水平扩展，自动分片 |
| 成本 | 低（自托管） | 高（按用量，高 QPS 昂贵） |
| 运维复杂度 | 高（需要 DBA） | 低（全托管） |
| 适合 QPS | < 50K 读/10K 写 | > 100K 读/50K 写 |
| **推荐场景** | **初期、中小规模** | **大规模、查询模式固定** |

**决策**：初期选择 PostgreSQL，留有明确的迁移路径（查询模式固定，迁移 DynamoDB 风险可控）。

### 6.4 部署规模：单机 vs 分布式

| 维度 | 单机方案 | 分布式方案 |
|------|----------|------------|
| 实现复杂度 | 极低 | 高（需要服务发现、一致性协议） |
| 扩展上限 | 有限（单机 CPU/内存/磁盘） | 近乎无限 |
| 运维成本 | 低 | 高 |
| 故障隔离 | 差（单点故障） | 好（多副本） |
| 延迟 | 低（无网络跳数） | 略高（服务间通信） |
| **推荐场景** | **原型、内部工具、低流量** | **生产、高可用要求** |

**演进策略**（先简单后复杂）：

```
阶段一（MVP）：
  单台应用服务器 + 单台 PostgreSQL + 本地 Redis
  适合：< 1K QPS

阶段二（初步扩展）：
  多台无状态应用服务器（Nginx 负载均衡）
  PostgreSQL 主从复制（读写分离）
  Redis Cluster（3 主 3 从）
  适合：< 50K 读 QPS，< 5K 写 QPS

阶段三（大规模）：
  多 AZ 部署（高可用）
  DynamoDB（无限扩展）+ 全球 CDN
  Snowflake 分布式 ID
  适合：> 100K 读 QPS
```

### 6.5 缓存一致性：Write-Through vs Cache-Aside

| 维度 | Write-Through | Cache-Aside |
|------|--------------|-------------|
| 数据一致性 | 高（写数据库同时写缓存） | 中（异步回填） |
| 写入延迟 | 略高（需要等待缓存写入） | 低 |
| 缓存利用率 | 低（冷数据也会写入缓存） | 高（仅缓存被查询的数据） |
| 实现复杂度 | 低 | 中 |
| **推荐场景** | **写少读多，一致性要求高** | **读多写少，缓存命中率高** |

**决策**：选择 Cache-Aside，URL 短链的缓存命中率极高，且短暂的不一致可以接受。

---

## 7. 总结

### Key Architect Takeaways

**1. 读写分离是核心设计原则**

URL 短链是极端读多写少（100:1）的场景。所有架构决策都应以"如何让读路径尽可能快"为出发点。Redis 缓存在读路径上的投入收益最大，应优先保障。写路径的容量规划（1.2K 写 QPS）远比读路径（116K 读 QPS）宽松，不要过早优化写路径。

**2. 短码生成算法的选择直接决定系统复杂度**

自增 ID + Base62 方案以最低的实现复杂度获得了天然唯一性，避免了分布式冲突检测的并发竞争问题。架构师应优先选择"自然正确"的方案而非"技巧性地规避错误"的方案。当系统需要水平扩展时，Snowflake 算法是自增 ID 方案的自然延伸，无需颠覆现有设计。

**3. 权衡选择必须与业务目标对齐，而非追求技术最优**

301 vs 302 的选择不是技术问题，而是业务问题。选 302 放弃了浏览器缓存带来的极致性能，换取了点击统计能力和目标 URL 可变更能力。技术上的次优选择往往是业务上的正确选择。架构师的价值在于理解这一权衡并做出有意识的决策，而非机械地追求技术指标最优。

**4. 演进式架构优于大而全的一次性设计**

从单机 PostgreSQL 开始，在流量增长时逐步引入 Redis 缓存、读写分离、DynamoDB 迁移。过早引入 Snowflake、DynamoDB 分片等复杂机制只会增加运维负担而不带来实际收益。优秀的架构设计不是预测未来并一步到位，而是在当前约束下做出正确决策，同时保留清晰的扩展路径。

---

### 设计速查表

| 问题 | 推荐答案 | 理由 |
|------|----------|------|
| 短码长度 | 7 位 Base62 | 3.5 万亿空间，够用 50+ 年 |
| 短码生成 | 自增 ID + Base62 + 混淆 | 无冲突，实现简单 |
| 重定向语义 | 302 | 支持统计和 URL 变更 |
| 缓存模式 | Cache-Aside | 命中率高，实现简单 |
| 数据库初期 | PostgreSQL + 主从 | 一致性强，运维成本低 |
| 数据库大规模 | DynamoDB | 原生水平扩展 |
| 分布式 ID | Snowflake | 每秒 42 亿+，无中心依赖 |
| 过期清理 | 定时任务（软删除） | 避免实时删除影响读路径 |

---

*最后更新：2026-03-26*
