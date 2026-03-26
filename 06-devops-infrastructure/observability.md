# 可观测性（Observability）

监控（Monitoring）告诉你系统**出了什么问题**；可观测性（Observability）让你能回答关于系统的**任何问题**，包括你从未预料到的问题。两者的区别在于：监控是预先知道要看什么，可观测性是在任何时候都能找到答案。

---

## 1. 监控 vs 可观测性

| 维度 | 监控（Monitoring） | 可观测性（Observability） |
|------|-----------------|----------------------|
| 核心问题 | "系统是否正常？" | "为什么系统表现异常？" |
| 数据类型 | 预先定义的指标（CPU、内存） | Metrics + Logs + Traces |
| 已知 vs 未知 | 已知的故障模式 | 未知的、从未发生过的故障 |
| 调试方式 | 看仪表板，触发告警 | 从症状出发，自由探索数据 |
| 比喻 | 汽车仪表盘（只显示预设指标） | 汽车的行车记录仪+诊断仪（能回答任何问题） |

### 1.1 三大支柱

```
可观测性
    ├── Metrics（指标）：数字，聚合，时序
    │   "过去5分钟的错误率是 0.1%"
    │   "P99 响应时间是 450ms"
    │
    ├── Logs（日志）：事件，有上下文，可查询
    │   "2026-03-26T10:00:01Z user_id=123 order_id=456 ERROR payment failed"
    │
    └── Traces（链路追踪）：分布式请求的完整路径
        "这次下单请求经过了 API Gateway → order-service → inventory-service，
         其中 inventory-service 耗时 380ms（占总耗时 85%）"
```

---

## 2. Metrics（指标）

### 2.1 四个黄金指标（Google SRE）

| 指标 | 含义 | 典型告警阈值 |
|------|------|------------|
| 延迟（Latency） | 请求处理时间（区分成功/失败） | P99 > 500ms 告警 |
| 流量（Traffic） | 每秒请求数（QPS/RPS） | 突降 30% 告警（可能是问题） |
| 错误率（Errors） | 失败请求比率（5xx / 总请求） | 错误率 > 1% 告警 |
| 饱和度（Saturation） | 资源使用程度（CPU、内存、连接池） | CPU > 80% 持续5分钟告警 |

### 2.2 Prometheus 数据类型

| 类型 | 说明 | 适用场景 | 示例 |
|------|------|---------|------|
| Counter | 只增不减的累计值 | 请求总数、错误总数 | `http_requests_total` |
| Gauge | 可增可减的当前值 | 当前连接数、队列长度、内存使用 | `active_connections` |
| Histogram | 观测值分布（桶统计） | 请求延迟分布 | `http_request_duration_seconds` |
| Summary | 类似 Histogram，在客户端计算分位数 | 精确分位数（但合并困难） | 通常用 Histogram 替代 |

### 2.3 Python 集成 Prometheus

```python
# shop/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Counter：请求总数（按路径和状态码）
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

# Histogram：请求延迟（自动计算 P50/P90/P99）
REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# Gauge：活跃连接数
ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

# Gauge：数据库连接池使用率
DB_POOL_USAGE = Gauge(
    'db_pool_usage_ratio',
    'Database connection pool usage ratio'
)


# FastAPI 中间件：自动记录所有请求的指标
from fastapi import Request
import time

async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    ACTIVE_CONNECTIONS.inc()

    response = await call_next(request)

    duration = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = str(response.status_code)

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    ACTIVE_CONNECTIONS.dec()

    return response

# 启动 Prometheus 指标端点（暴露给 Prometheus 抓取）
# 访问 http://localhost:8000/metrics 查看原始数据
```

### 2.4 业务指标 vs 技术指标

```python
# 技术指标（系统层面）
REQUEST_COUNT = Counter(...)              # 请求量
ERROR_RATE = Counter(...)                # 错误率
RESPONSE_TIME = Histogram(...)           # 响应时间

# 业务指标（业务层面，更直接反映用户体验）
ORDER_PLACED = Counter('orders_placed_total', 'Total orders placed', ['status'])
ORDER_REVENUE = Counter('order_revenue_total', 'Total order revenue in CNY')
CART_ABANDONED = Counter('cart_abandoned_total', 'Number of abandoned carts')
PAYMENT_SUCCESS_RATE = Gauge('payment_success_rate', 'Payment success rate in last hour')

# 下单时记录业务指标
def on_order_placed(order: Order):
    ORDER_PLACED.labels(status='success').inc()
    ORDER_REVENUE.inc(order.total)
```

> **架构师提示：** 业务指标比技术指标更重要。CPU 100% 未必是问题（高负载但能处理请求），但"订单成功率降低 10%"一定是问题。告警应该优先基于业务指标（症状），而非技术指标（原因）。

---

## 3. Logs（日志）

### 3.1 结构化日志 vs 非结构化日志

```
# 非结构化（自由文本，难以查询）
2026-03-26 10:00:01 ERROR Payment failed for user 123 order 456 amount 99.99

# 结构化（JSON，可以精确查询任意字段）
{
    "timestamp": "2026-03-26T10:00:01.123Z",
    "level": "ERROR",
    "service": "order-service",
    "trace_id": "abc-123-def-456",
    "span_id": "789-xyz",
    "user_id": 123,
    "order_id": 456,
    "event": "payment_failed",
    "error": "insufficient_balance",
    "amount": 99.99,
    "duration_ms": 234
}

# 查询示例（Elasticsearch/Loki）：
# 找到 user_id=123 的所有支付失败记录
# 统计过去1小时 event=payment_failed 的次数
# 通过 trace_id=abc-123 找到完整请求链路
```

### 3.2 Python 结构化日志实现

```python
# shop/logging_config.py
import logging
import json
import time
from contextvars import ContextVar

# 用上下文变量存储 Trace ID（在同一个请求的所有调用栈中共享）
current_trace_id: ContextVar[str] = ContextVar('trace_id', default='')
current_user_id: ContextVar[int | None] = ContextVar('user_id', default=None)

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%f"),
            "level": record.levelname,
            "service": "order-service",
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": current_trace_id.get(""),
            "user_id": current_user_id.get(None),
        }

        # 添加额外的上下文字段（通过 extra 参数传入）
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)

# 配置
handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])

# 使用
logger = logging.getLogger("order_service")

def place_order(order_data: dict, trace_id: str, user_id: int):
    current_trace_id.set(trace_id)
    current_user_id.set(user_id)

    logger.info("Order placement started", extra={
        "extra_fields": {
            "event": "order_placement_started",
            "items_count": len(order_data["items"])
        }
    })

    try:
        order = process_order(order_data)
        logger.info("Order placed successfully", extra={
            "extra_fields": {
                "event": "order_placed",
                "order_id": order.id,
                "total": order.total
            }
        })
    except Exception as e:
        logger.error("Order placement failed", extra={
            "extra_fields": {
                "event": "order_placement_failed",
                "error": str(e)
            }
        }, exc_info=True)
        raise
```

### 3.3 日志级别规范

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| DEBUG | 开发调试，不在生产开启 | SQL 查询语句、函数入参 |
| INFO | 正常业务事件 | 用户登录、订单创建 |
| WARN | 潜在问题，但系统仍在运行 | 缓存未命中率高、重试次数多 |
| ERROR | 操作失败，需要关注 | 支付失败、数据库连接失败 |
| FATAL/CRITICAL | 系统级别错误，需要立即处理 | 配置文件缺失、启动失败 |

> **日志采样：** 在 10,000 QPS 的系统中，每个请求都记录 INFO 日志会产生巨量数据。对于正常请求可以采样（如只记录 10%），对于错误请求始终记录 100%。

---

## 4. Traces（链路追踪）

### 4.1 Span 和 Trace

```
一次下单请求（Trace ID: abc-123）：
│
├── [API Gateway] 入口处理              span_id=001, duration=5ms
│   │
│   ├── [order-service] 创建订单        span_id=002, duration=450ms
│   │   │
│   │   ├── [inventory-service] 查库存  span_id=003, duration=380ms ← 瓶颈！
│   │   │
│   │   └── [PostgreSQL] 写订单         span_id=004, duration=30ms
│   │
│   └── [notification-service] 发邮件   span_id=005, duration=80ms（异步）
│
总耗时：535ms
```

通过 Trace，我们立刻知道：`inventory-service` 占了 71% 的时间，需要优化。

### 4.2 OpenTelemetry（OTel）标准化集成

OpenTelemetry 是行业标准的可观测性框架，可以导出到 Jaeger、Zipkin、Grafana Tempo 等后端。

```python
# shop/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def setup_tracing(service_name: str = "order-service"):
    # 配置 Tracer Provider
    provider = TracerProvider()

    # 导出到 Jaeger（通过 OTLP 协议）
    exporter = OTLPSpanExporter(endpoint="http://jaeger:4317")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # 自动 instrument（不需要手动在每个函数里添加代码）
    FastAPIInstrumentor.instrument()    # 自动追踪所有 HTTP 请求
    AsyncPGInstrumentor.instrument()    # 自动追踪数据库查询
    HTTPXClientInstrumentor.instrument()  # 自动追踪对外 HTTP 调用

# 手动创建 Span（用于追踪自定义业务逻辑）
tracer = trace.get_tracer("order_service")

async def calculate_order_total(items: list) -> float:
    with tracer.start_as_current_span("calculate_order_total") as span:
        # 设置 Span 属性（可在 Jaeger 中搜索）
        span.set_attribute("items.count", len(items))

        total = 0.0
        for item in items:
            with tracer.start_as_current_span("fetch_product_price") as child_span:
                child_span.set_attribute("product.id", item["product_id"])
                price = await get_product_price(item["product_id"])
                total += price * item["quantity"]

        span.set_attribute("order.total", total)
        return total
```

### 4.3 Trace ID 在日志中的传播

```python
# FastAPI 中间件：从请求头读取 Trace ID，注入到日志上下文
from fastapi import Request
from opentelemetry import trace

async def trace_context_middleware(request: Request, call_next):
    # OpenTelemetry 自动从请求头（traceparent）读取 Trace ID
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    if span_context.is_valid:
        trace_id = format(span_context.trace_id, '032x')
        # 注入到日志上下文（所有后续日志自动包含这个 Trace ID）
        current_trace_id.set(trace_id)

    response = await call_next(request)
    # 把 Trace ID 也放到响应头，方便调用方关联
    response.headers["X-Trace-Id"] = current_trace_id.get("")
    return response
```

---

## 5. 告警设计

### 5.1 告警原则

| 原则 | 说明 |
|------|------|
| 基于症状，不基于原因 | 告警"用户下单失败率 > 1%"，而非"CPU > 80%"（CPU 高未必影响用户） |
| 每个告警都需要人工响应 | 如果告警触发后无需任何操作，删除这个告警 |
| 告警要有 Playbook | 收到告警后应该做什么？链接到 Runbook |
| 避免告警疲劳 | 太多告警 = 没有告警（工程师会开始忽略） |

### 5.2 告警分级

| 级别 | 响应时间 | 示例 | 通知方式 |
|------|---------|------|---------|
| P1（严重） | 立即（<5分钟） | 服务完全不可用、支付全部失败 | 电话 + 短信 + 即时消息 |
| P2（高） | 30分钟内 | 错误率 > 5%、P99 延迟 > 2s | 即时消息 + 邮件 |
| P3（中） | 工作时间内 | 磁盘使用率 > 80%、缓存命中率下降 | 邮件 |

### 5.3 Prometheus AlertManager 规则示例

```yaml
# alerts.yaml
groups:
  - name: shopflow_critical
    rules:
      # P1：错误率过高
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 2m  # 持续2分钟才告警（避免瞬时抖动）
        labels:
          severity: critical
        annotations:
          summary: "HTTP error rate > 5%"
          description: "Error rate is {{ $value | humanizePercentage }}"
          runbook: "https://wiki.shopflow.com/runbooks/high-error-rate"

      # P1：P99 延迟过高
      - alert: HighP99Latency
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
          ) > 2.0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "P99 latency > 2s on {{ $labels.endpoint }}"

  - name: shopflow_warning
    rules:
      # P3：数据库连接池接近上限
      - alert: DBPoolNearCapacity
        expr: db_pool_usage_ratio > 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Database connection pool at {{ $value | humanizePercentage }}"
```

---

## 6. 在 ShopFlow 追踪一次下单请求

**场景：** 用户投诉"下单很慢"。通过可观测性三支柱定位问题：

```
步骤1：Metrics（发现问题）
    Grafana 仪表板：P99 延迟从 200ms 升到 1500ms
    时间范围：过去1小时
    影响端点：POST /v1/orders

步骤2：Logs（缩小范围）
    在 Loki 中查询：level=ERROR AND endpoint="/v1/orders"
    发现：order-service 有大量 "inventory service timeout" 日志
    → 问题在 inventory-service

步骤3：Traces（精确定位）
    在 Jaeger 中：找一条慢请求的 Trace（通过 trace_id）
    展开链路：
        order-service: 1500ms 总耗时
        └── inventory-service: 1380ms ← 占 92% 时间！
            └── PostgreSQL: 1350ms ← 慢查询！

    查看 inventory-service 的 PostgreSQL Span：
    SQL: SELECT * FROM inventory WHERE product_id IN (1,2,3,...,100)
    发现：查询没有走索引（EXPLAIN 显示 Seq Scan）

解决方案：
    给 inventory 表的 product_id 列加索引
    CREATE INDEX idx_inventory_product_id ON inventory(product_id);
    效果：P99 延迟从 1500ms 降回 200ms
```

---

## Key Architect Takeaways

- **三大支柱缺一不可**：Metrics 告诉你出了问题，Logs 提供上下文，Traces 显示问题在哪里。只有 Metrics 的系统在复杂故障时会束手无策
- **Trace ID 是串联三支柱的关键**：每个请求的 Trace ID 必须贯穿 Metrics（label）、Logs（字段）、Traces（关联），才能从告警一路追踪到根因
- **告警基于症状，不基于原因**：CPU 80% 可能不是问题，但"用户下单失败率 5%"一定是问题——永远从用户体验出发设计告警
- **业务指标比技术指标更有价值**：订单成功率、支付转化率、P99 延迟是架构师应该盯着的指标，而不是 CPU 和内存
- **OpenTelemetry 是标准选择**：不要自己实现 Trace 传播，用 OTel 标准，可以无缝切换 Jaeger/Zipkin/Tempo 等后端
