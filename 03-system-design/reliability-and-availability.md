# 可靠性与可用性（Reliability and Availability）

系统不会永远正常运行。可靠性（Reliability）的目标不是"永不故障"，而是"故障时优雅降级，快速恢复"。本章从架构师视角审视构建弹性系统的核心模式。

---

## 1. 核心指标：SLA / SLO / SLI

### 1.1 三者关系

| 概念 | 全称 | 含义 | 示例 |
|------|------|------|------|
| SLI | Service Level Indicator | 服务质量的度量指标（实际测量值） | 过去30天的请求成功率 = 99.5% |
| SLO | Service Level Objective | 对 SLI 的内部目标 | 目标：请求成功率 ≥ 99.9% |
| SLA | Service Level Agreement | 与客户签订的合同承诺（违约有赔偿） | 合同：保证 99.9% 可用性，否则退款 |

> **架构师提示：** SLO 应该比 SLA 更严格（内部目标比合同承诺高）。这样即使内部偶尔未达 SLO，对外的 SLA 仍然满足。

### 1.2 可用性与允许宕机时长

| 可用性 | 年停机时间 | 月停机时间 | 适用场景 |
|--------|---------|---------|---------|
| 99% (两个九) | 87.6 小时 | 7.3 小时 | 内部工具 |
| 99.9% (三个九) | 8.76 小时 | 43.8 分钟 | 大多数 B2C 产品 |
| 99.99% (四个九) | 52.6 分钟 | 4.38 分钟 | 支付、金融 |
| 99.999% (五个九) | 5.26 分钟 | 26.3 秒 | 电信、医疗关键系统 |

> 从三个九提升到四个九，难度不是线性的，是指数级的。四个九意味着每次发布都需要极其谨慎，需要蓝绿部署、金丝雀发布等手段。

### 1.3 错误预算（Error Budget）

错误预算 = 1 - SLO。这是允许系统"失败"的时间额度。

```
SLO = 99.9%
月错误预算 = 0.1% × 30天 = 43.8分钟

本月已消耗错误预算：30分钟
剩余错误预算：13.8分钟

→ 如果本月错误预算耗尽，应停止发布新功能，全力保障稳定性
→ 如果本月错误预算充裕，可以适当激进地发布新功能
```

---

## 2. 四个黄金指标（Four Golden Signals）

由 Google SRE 团队提出，监控任何服务都应该先看这四个指标：

| 指标 | 含义 | 典型监控方式 |
|------|------|------------|
| 延迟（Latency） | 处理请求的时间（区分成功与失败请求） | P50, P95, P99 响应时间 |
| 流量（Traffic） | 系统接收的请求量 | QPS（每秒请求数） |
| 错误率（Errors） | 失败请求的比率 | HTTP 5xx 比率，业务错误率 |
| 饱和度（Saturation） | 系统资源的使用程度 | CPU、内存、连接池使用率 |

> 这四个指标是告警设计的基础。每个服务都应该有这四类告警。

---

## 3. 熔断器（Circuit Breaker）

### 3.1 问题背景

当下游服务（如支付网关）出现故障时，如果上游服务不断重试：
- 每次调用都等待超时（如30秒）
- 大量请求积压，耗尽线程池
- 上游服务也跟着崩溃——**级联故障**

### 3.2 三状态熔断器

```
         失败率超阈值
  CLOSED ─────────────→ OPEN
    ↑                      │
    │   成功               │ 等待恢复时间
    │  HALF-OPEN ←─────────┘
    │    │
    │    │ 失败
    │    ↓
    │   OPEN（重新打开）
    │
    └── （测试请求成功，重置失败计数）
```

| 状态 | 行为 |
|------|------|
| CLOSED（关闭）| 正常工作，记录失败次数 |
| OPEN（打开）| 直接拒绝请求（快速失败），不尝试调用下游 |
| HALF-OPEN（半开）| 允许少量测试请求通过，判断下游是否恢复 |

### 3.3 手写实现

```python
# shop/resilience/circuit_breaker.py
import time
from enum import Enum
from threading import Lock

class State(Enum):
    CLOSED = "closed"       # 正常工作
    OPEN = "open"           # 熔断，快速失败
    HALF_OPEN = "half_open" # 尝试恢复

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,      # 触发熔断的失败次数
        recovery_timeout: float = 60.0,  # OPEN → HALF-OPEN 等待秒数
        half_open_max_calls: int = 3     # HALF-OPEN 状态允许的测试请求数
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls

        self._state = State.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0
        self._lock = Lock()

    @property
    def state(self) -> State:
        with self._lock:
            if self._state == State.OPEN:
                # 检查是否到了恢复时间
                if time.time() - self._last_failure_time >= self._recovery_timeout:
                    self._state = State.HALF_OPEN
                    self._half_open_calls = 0
            return self._state

    def call(self, func, *args, **kwargs):
        """通过熔断器调用函数"""
        state = self.state

        if state == State.OPEN:
            raise CircuitBreakerOpenError("Circuit breaker is OPEN. Fast failing.")

        if state == State.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self._half_open_max_calls:
                    raise CircuitBreakerOpenError("Circuit breaker HALF-OPEN limit reached.")
                self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        with self._lock:
            if self._state == State.HALF_OPEN:
                # 测试成功，恢复正常
                self._state = State.CLOSED
                self._failure_count = 0
                print("[CircuitBreaker] Recovered: HALF-OPEN → CLOSED")
            elif self._state == State.CLOSED:
                self._failure_count = 0  # 成功则重置失败计数

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == State.HALF_OPEN:
                # 测试失败，继续熔断
                self._state = State.OPEN
                print("[CircuitBreaker] Test failed: HALF-OPEN → OPEN")
            elif self._failure_count >= self._failure_threshold:
                self._state = State.OPEN
                print(f"[CircuitBreaker] Threshold reached ({self._failure_count}): CLOSED → OPEN")


class CircuitBreakerOpenError(Exception):
    pass


# 使用示例：保护支付网关调用
payment_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

def charge_customer(order_id: int, amount: float):
    try:
        result = payment_breaker.call(
            payment_gateway.charge,  # 被保护的调用
            amount=amount
        )
        return result
    except CircuitBreakerOpenError:
        # 熔断时的降级策略：将订单标记为"待支付"，稍后重试
        mark_order_pending_payment(order_id)
        return {"status": "pending", "message": "Payment service unavailable, will retry"}
```

---

## 4. 重试机制（Retry with Exponential Backoff）

### 4.1 为什么需要指数退避

```
# 错误示范：立即重试
def call_service():
    for i in range(3):
        try:
            return make_request()
        except Exception:
            continue  # 立即重试 → 打爆已经过载的服务
```

**指数退避：** 每次重试等待更长时间，给下游服务喘息机会。

```python
import time
import random

def retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,    # 初始等待秒数
    max_delay: float = 32.0,    # 最大等待秒数
    jitter: bool = True         # 随机抖动（防止同时重试的惊群）
):
    """
    指数退避重试
    等待时间：base_delay * 2^attempt + random_jitter
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise  # 最后一次失败，不再重试

            delay = min(base_delay * (2 ** attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random() * 0.5)  # ±50% 随机抖动

            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)

# 等待时间序列：1s → 2s → 4s → 8s（+ 随机抖动）
```

### 4.2 哪些错误应该重试

| 错误类型 | 是否重试 | 理由 |
|---------|---------|------|
| 网络超时 | 是 | 瞬时故障，重试有可能成功 |
| HTTP 429（限流） | 是（等 Retry-After） | 等待后重试 |
| HTTP 503（服务不可用） | 是 | 服务可能正在重启 |
| HTTP 500（服务器错误） | 谨慎（依赖幂等性） | 如果操作是幂等的可以重试 |
| HTTP 400（客户端错误） | 否 | 请求本身有问题，重试无意义 |
| HTTP 401/403（认证授权） | 否 | 权限问题，重试无意义 |

---

## 5. 限流（Rate Limiting）

### 5.1 令牌桶算法（Token Bucket）

令牌桶是最常用的限流算法，允许短暂突发，同时控制平均速率。

```
桶容量 = 100（最大突发量）
补充速率 = 10个/秒（稳定速率）

时间: 0s  → 令牌 100（满）
时间: 1s  → 请求消耗 80 个令牌 + 补充 10 个 = 30 个
时间: 2s  → 请求消耗 30 个令牌 + 补充 10 个 = 10 个
时间: 3s  → 请求只有 2 个 + 补充 10 个 = 12 个
```

```python
# shop/resilience/rate_limiter.py — Redis 实现令牌桶
import redis
import time

class TokenBucketRateLimiter:
    def __init__(self, redis_client: redis.Redis, capacity: int, refill_rate: float):
        """
        capacity: 桶容量（允许的最大突发量）
        refill_rate: 每秒补充令牌数
        """
        self._redis = redis_client
        self._capacity = capacity
        self._refill_rate = refill_rate

    def is_allowed(self, key: str, tokens_needed: int = 1) -> tuple[bool, dict]:
        """
        检查是否允许请求
        返回：(是否允许, 限流信息)
        """
        now = time.time()
        bucket_key = f"rate_limit:token_bucket:{key}"

        # Lua 脚本保证原子性（避免竞态条件）
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local tokens_needed = tonumber(ARGV[4])
        local ttl = tonumber(ARGV[5])

        local data = redis.call('HMGET', key, 'tokens', 'last_refill')
        local current_tokens = tonumber(data[1]) or capacity
        local last_refill = tonumber(data[2]) or now

        -- 计算应补充的令牌
        local elapsed = now - last_refill
        local refill = elapsed * refill_rate
        current_tokens = math.min(capacity, current_tokens + refill)

        if current_tokens >= tokens_needed then
            -- 允许请求，扣除令牌
            current_tokens = current_tokens - tokens_needed
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, ttl)
            return {1, math.floor(current_tokens)}
        else
            -- 拒绝请求
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, ttl)
            return {0, math.floor(current_tokens)}
        end
        """

        allowed, remaining = self._redis.eval(
            lua_script, 1, bucket_key,
            self._capacity, self._refill_rate, now,
            tokens_needed, int(self._capacity / self._refill_rate) + 60
        )

        return bool(allowed), {
            "allowed": bool(allowed),
            "remaining_tokens": int(remaining),
            "capacity": self._capacity,
            "refill_rate": self._refill_rate
        }


# FastAPI 中间件集成
from fastapi import Request, HTTPException

rate_limiter = TokenBucketRateLimiter(
    redis_client=redis.Redis(),
    capacity=100,
    refill_rate=10  # 每秒10个令牌
)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # 用 IP 或用户 ID 作为限流键
    client_ip = request.client.host
    allowed, info = rate_limiter.is_allowed(f"ip:{client_ip}")

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={
                "X-RateLimit-Limit": str(info["capacity"]),
                "X-RateLimit-Remaining": "0",
                "Retry-After": "1"
            }
        )

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(info["capacity"])
    response.headers["X-RateLimit-Remaining"] = str(info["remaining_tokens"])
    return response
```

### 5.2 滑动窗口算法（对比）

```python
def is_allowed_sliding_window(key: str, window_seconds: int, max_requests: int) -> bool:
    """滑动窗口限流：更准确，但内存消耗较大"""
    now = time.time()
    window_start = now - window_seconds

    pipe = redis.pipeline()
    # 删除窗口外的旧记录
    pipe.zremrangebyscore(key, 0, window_start)
    # 添加当前请求时间戳
    pipe.zadd(key, {str(now): now})
    # 统计窗口内的请求数
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 1)
    results = pipe.execute()

    current_count = results[2]
    return current_count <= max_requests
```

---

## 6. 舱壁模式（Bulkhead Pattern）

借鉴轮船的水密舱设计：将系统资源隔离，防止一个功能的故障耗尽全部资源。

```python
from concurrent.futures import ThreadPoolExecutor

# 反模式：共用线程池
shared_pool = ThreadPoolExecutor(max_workers=20)

# 正确：按功能隔离线程池
payment_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="payment")
inventory_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="inventory")
notification_pool = ThreadPoolExecutor(max_workers=5, thread_name_prefix="notification")

# 即使支付服务卡死，占满了 payment_pool 的5个线程
# inventory_pool 和 notification_pool 仍然正常工作
# 不会发生级联故障
```

---

## 7. 超时设置（Timeouts）

每个外部调用都必须设置超时。没有超时的调用是定时炸弹。

```python
import httpx

# 分层超时设置
timeout_config = httpx.Timeout(
    connect=2.0,    # 建立连接超时（秒）
    read=5.0,       # 读取响应超时
    write=2.0,      # 发送请求超时
    pool=1.0        # 从连接池获取连接超时
)

async with httpx.AsyncClient(timeout=timeout_config) as client:
    response = await client.get("https://payment-gateway.com/charge")
```

### 超时设置指南

| 调用类型 | 建议超时 |
|---------|---------|
| 用户直接触发（同步请求） | 200ms-1s |
| 内部服务调用 | 1-5s |
| 第三方API | 5-30s |
| 数据库查询（简单） | 1-3s |
| 数据库查询（复杂报表） | 30s |
| 文件上传/下载 | 按文件大小估算 |

---

## 8. 降级策略（Graceful Degradation）

当系统部分不可用时，以有限功能继续运行，而不是完全崩溃。

```python
async def get_product_recommendations(user_id: int) -> list:
    """获取个性化推荐——降级到热门商品"""
    try:
        # 尝试调用推荐服务（有熔断器保护）
        recommendations = await recommendation_service.get_for_user(user_id)
        return recommendations
    except (CircuitBreakerOpenError, TimeoutError):
        # 降级：返回缓存的热门商品（非个性化，但系统可用）
        hot_products = await redis.get("hot_products")
        if hot_products:
            return json.loads(hot_products)
        # 最后兜底：返回空列表（比返回错误好）
        return []

async def get_product_detail(product_id: int) -> dict:
    """获取商品详情——降级示例"""
    try:
        return await db.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
    except Exception:
        # 尝试从缓存读取（即使缓存数据可能稍旧）
        cached = await redis.get(f"product:{product_id}")
        if cached:
            return json.loads(cached)
        raise  # 缓存也没有，只能抛异常
```

---

## 9. 健康检查端点

```python
# 标准健康检查端点设计
@app.get("/health")
async def health_check():
    """简单存活检查（Liveness）"""
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness_check():
    """就绪检查（Readiness）——检查依赖是否可用"""
    checks = {}

    # 检查数据库
    try:
        await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # 检查 Redis
    try:
        await redis.ping()
        checks["cache"] = "ok"
    except Exception as e:
        checks["cache"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content={"status": "ok" if all_ok else "degraded", "checks": checks},
        status_code=200 if all_ok else 503
    )
```

---

## Key Architect Takeaways

- **熔断器是分布式系统的保险丝**：没有熔断器，一个下游服务的故障会通过"等待超时"的方式把所有上游服务拖垮；熔断后快速失败，保护上游资源
- **超时是必选项，不是可选项**：任何外部调用（HTTP、DB、Redis、消息队列）都必须设置超时。"连接超时"和"读取超时"是两个不同的配置，都需要设置
- **指数退避 + 随机抖动**：退避防止打爆恢复中的服务，随机抖动防止大量客户端同时重试（惊群效应）
- **错误预算让稳定性决策变得理性**：与其争论"发布风险大不大"，不如看错误预算还剩多少，用数据驱动决策
- **降级优于不可用**：推荐功能挂了返回热门商品、评论服务挂了隐藏评论区，比返回 500 错误要好得多——永远思考"这个功能挂了，系统能不能继续运行"
