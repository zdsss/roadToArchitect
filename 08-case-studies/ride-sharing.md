# 案例研究：网约车系统设计（Ride-Sharing System）

> 架构师视角：本文以 Uber / 滴滴类网约车平台为原型，系统拆解从需求到落地的全链路设计决策。重点聚焦实时位置追踪、地理索引与司机匹配三大核心挑战。

---

## 目录

1. [需求分析](#需求分析)
2. [规模估算](#规模估算)
3. [API 设计](#api-设计)
4. [高层设计](#高层设计)
5. [组件深入](#组件深入)
6. [权衡分析](#权衡分析)
7. [总结](#总结)

---

## 需求分析

### 功能需求

#### 乘客侧

| 功能 | 描述 |
|------|------|
| 叫车请求 | 乘客输入出发地 + 目的地，发起叫车 |
| 实时位置追踪 | 乘客可在地图上实时看到司机位置和预计到达时间 |
| 路线规划 | 系统根据实时路况规划最优路线 |
| 行程计费 | 到达目的地后，按里程 + 时间 + 动态定价自动结算 |
| 历史记录查询 | 乘客可查看过往行程的路线、费用、司机信息 |
| 取消行程 | 在司机接单前或接单后一定时间内可取消 |

#### 司机侧

| 功能 | 描述 |
|------|------|
| 上线/下线 | 司机切换可接单状态 |
| 位置上报 | 司机 App 定期上报 GPS 坐标 |
| 接单/拒单 | 收到派单推送后选择接受或拒绝 |
| 导航引导 | 接单后接收前往乘客位置的导航指令 |
| 行程完成确认 | 到达目的地后标记行程完成，触发计费 |

#### 平台侧

| 功能 | 描述 |
|------|------|
| 司机匹配 | 根据位置、评分、接单率为乘客匹配最优司机 |
| 动态定价 | 根据供需关系实时调整价格系数 |
| 风控与安全 | 行程全程追踪，异常检测（偏离路线等） |

### 非功能需求

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 匹配延迟 | < 2 秒 | 从乘客发起叫车到收到司机信息 |
| 位置更新延迟 | < 1 秒 | 乘客看到司机位置的端到端延迟 |
| 系统可用性 | 99.99% | 每年故障时间 < 52 分钟 |
| 并发处理能力 | 百万级并发连接 | 高峰期司机 + 乘客 WebSocket 连接 |
| 位置数据实时性 | 强实时 | 司机位置最多 4 秒内反映到乘客端 |
| 历史数据持久性 | 永久保留 | 行程记录用于对账、纠纷处理 |
| 位置快照保留 | 短期（7天） | 仅用于行程回放，不需要永久存储 |

### 核心挑战识别

架构师在开始设计前，需要明确本系统的三大核心技术挑战：

1. **高频写入**：10 万在线司机每 4 秒上报一次位置，每秒约 2.5 万次写入，且必须低延迟可查
2. **地理查询**：叫车时需在毫秒级内找出附近空闲司机，传统关系型数据库的范围查询性能不足
3. **实时推送**：位置数据需要以接近实时的速度从司机端流向乘客端，要求高效的消息分发机制

---

## 规模估算

### 用户规模

```
日活跃用户（DAU）：       1,000,000（100 万）
同时在线司机峰值：         100,000（10 万）
同时在线乘客峰值（估算）： 300,000（30 万）
每日完成行程数：           500,000（50 万次）
```

### 位置更新量估算

```
司机上报频率：每 4 秒上报一次

每秒位置写入量 = 同时在线司机数 / 上报间隔
              = 100,000 / 4
              = 25,000 次/秒（25K QPS）

每次位置数据大小（估算）：
  driver_id:    8 bytes (int64)
  latitude:     8 bytes (double)
  longitude:    8 bytes (double)
  timestamp:    8 bytes (int64)
  speed:        4 bytes (float)
  heading:      4 bytes (float)
  单条总计：    ~40 bytes

每秒写入数据量 = 25,000 × 40 bytes = 1 MB/s
每天写入数据量 = 1 MB/s × 86,400s ≈ 86 GB/天
```

### 存储估算

#### 行程记录（永久存储）

```
每次行程记录大小（估算）：~2 KB
  - 乘客/司机 ID、出发/到达坐标、时间戳、费用、路线点序列等

每日新增行程数：500,000 次
每日新增存储：  500,000 × 2 KB = 1 GB/天
5 年累计：      1 GB × 365 × 5 ≈ 1.8 TB（可压缩至 ~500 GB）
```

#### 位置快照（短期保留，7 天）

```
位置数据保留策略：仅保留行程中的轨迹点，非行程时段不持久化

行程中的轨迹点密度：每 4 秒一个点
平均行程时长：20 分钟 = 1,200 秒
每次行程轨迹点数：1,200 / 4 = 300 个点

每日轨迹数据量：500,000 × 300 × 40 bytes = 6 GB/天
7 天滚动保留：  6 GB × 7 = 42 GB（极小，完全可控）
```

#### Redis 内存容量（实时位置）

```
存储对象：所有在线司机的当前位置（无需历史）

每条记录大小：~100 bytes（含 Redis 开销）
总记录数：    100,000 条（10 万在线司机）
总内存需求：  100,000 × 100 bytes = 10 MB

结论：Redis 存储实时位置的内存开销极小，完全可行。
```

### 读写压力汇总

| 操作 | QPS | 读/写 | 存储层 |
|------|-----|-------|--------|
| 司机位置上报 | 25,000 | 写 | Redis + Cassandra |
| 附近司机查询 | ~1,000 | 读 | Redis Geo |
| 行程状态查询 | ~5,000 | 读 | MySQL / PostgreSQL |
| 行程记录写入 | ~6（50万/天） | 写 | MySQL / PostgreSQL |
| WebSocket 推送 | ~300,000 | 双向 | WebSocket 服务 |

---

## API 设计

### 1. 乘客叫车

```
POST /v1/rides/request
Authorization: Bearer <passenger_token>

Request Body:
{
  "pickup": {
    "latitude": 39.9042,
    "longitude": 116.4074,
    "address": "北京市东城区天安门广场"
  },
  "destination": {
    "latitude": 39.9892,
    "longitude": 116.3066,
    "address": "北京市海淀区中关村"
  },
  "ride_type": "standard",       // standard / premium / pool
  "payment_method": "alipay"
}

Response 200:
{
  "ride_id": "ride_abc123",
  "status": "searching",          // 正在寻找司机
  "estimated_fare": {
    "min": 35.0,
    "max": 45.0,
    "currency": "CNY"
  },
  "estimated_wait_seconds": 120,
  "tracking_token": "ws_token_xyz"  // 用于建立 WebSocket 连接
}
```

### 2. 司机上报位置

```
PUT /v1/drivers/{driver_id}/location
Authorization: Bearer <driver_token>

Request Body:
{
  "latitude": 39.9150,
  "longitude": 116.3900,
  "speed": 35.5,                  // km/h
  "heading": 270,                 // 朝向角度（0-360，0=正北）
  "timestamp": 1711440000000      // 毫秒级时间戳（客户端时间）
}

Response 200:
{
  "received": true,
  "server_timestamp": 1711440000050
}
```

**设计说明**：
- 使用 `PUT` 而非 `POST`，因为这是对司机当前位置的幂等覆盖更新
- 客户端时间戳用于检测网络延迟和时钟漂移
- 响应体刻意保持简洁，减少带宽消耗（司机每 4 秒调用一次）

### 3. 查询行程状态

```
GET /v1/rides/{ride_id}/status
Authorization: Bearer <user_token>

Response 200:
{
  "ride_id": "ride_abc123",
  "status": "driver_en_route",    // searching / driver_assigned / driver_en_route / in_progress / completed / cancelled
  "driver": {
    "id": "drv_789",
    "name": "张师傅",
    "rating": 4.92,
    "vehicle": {
      "model": "丰田凯美瑞",
      "plate": "京A·12345",
      "color": "白色"
    },
    "current_location": {
      "latitude": 39.9100,
      "longitude": 116.3950
    },
    "eta_seconds": 180            // 预计到达乘客位置的秒数
  },
  "route": {
    "polyline": "encoded_polyline_string",
    "distance_meters": 3200,
    "duration_seconds": 720
  }
}
```

### 4. WebSocket 实时追踪

```
WS /v1/rides/{ride_id}/tracking
Headers:
  Authorization: Bearer <passenger_token>
  X-Tracking-Token: ws_token_xyz

# 服务端推送消息格式（JSON）
{
  "type": "location_update",
  "driver_location": {
    "latitude": 39.9105,
    "longitude": 116.3945,
    "heading": 90,
    "speed": 28.0
  },
  "eta_seconds": 165,
  "timestamp": 1711440004000
}

# 其他消息类型
{
  "type": "status_change",
  "new_status": "driver_arrived",
  "message": "司机已到达，请尽快上车"
}

{
  "type": "ride_started",
  "start_timestamp": 1711440120000
}
```

### 5. 司机接单/拒单

```
POST /v1/rides/{ride_id}/respond
Authorization: Bearer <driver_token>

Request Body:
{
  "action": "accept"    // accept / reject
}

Response 200（接单成功）:
{
  "success": true,
  "passenger": {
    "name": "李女士",
    "pickup_location": {
      "latitude": 39.9042,
      "longitude": 116.4074,
      "address": "北京市东城区天安门广场"
    },
    "rating": 4.8
  },
  "navigation_url": "maps://route?..."
}

Response 409（已被其他司机接单）:
{
  "success": false,
  "reason": "ride_already_taken",
  "message": "该订单已被其他司机接受"
}
```

---

## 高层设计

### 系统架构总览

```
┌─────────────────────────────────────────────────────────┐
│                     移动客户端                            │
│              乘客 App          司机 App                   │
└──────────────────┬─────────────────┬────────────────────┘
                   │ HTTPS/WSS       │ HTTPS（位置上报）
                   ▼                 ▼
┌──────────────────────────────────────────────────────────┐
│                    API Gateway（负载均衡）                  │
│            路由 / 鉴权 / 限流 / SSL 终止                   │
└────┬──────────────┬──────────────┬──────────────┬────────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│ 行程服务 │  │ 位置服务  │  │ 匹配服务  │  │ WebSocket服务│
│ Trip    │  │ Location │  │ Matching │  │  Tracking   │
│ Service │  │ Service  │  │ Service  │  │  Service    │
└────┬────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘
     │            │             │               │
     ▼            ▼             ▼               ▼
┌─────────┐  ┌─────────┐  ┌─────────┐   ┌──────────────┐
│  MySQL  │  │  Redis  │  │  Redis  │   │ Message Queue│
│（行程   │  │（实时   │  │（Geo    │   │  (Kafka/     │
│  记录） │  │  位置） │  │  索引） │   │  RabbitMQ）  │
└─────────┘  └────┬────┘  └─────────┘   └──────────────┘
                  │
                  ▼
            ┌──────────┐
            │Cassandra │
            │（历史   │
            │  轨迹） │
            └──────────┘
```

### 核心数据流

#### 叫车流程

```
1. 乘客 App → API Gateway → 行程服务（创建 Pending 行程）
2. 行程服务 → 匹配服务（触发匹配任务）
3. 匹配服务 → Redis Geo（查询附近空闲司机）
4. 匹配服务 → 推送服务（向候选司机发送推单通知）
5. 司机 App 接单 → 行程服务（更新行程状态）
6. 行程服务 → 乘客 App（推送司机信息）
```

#### 位置追踪流程

```
1. 司机 App（每 4 秒）→ 位置服务（HTTP PUT）
2. 位置服务 → Redis（更新当前位置）
3. 位置服务 → Kafka（发布位置事件）
4. 位置服务 → Cassandra（异步写入历史轨迹）
5. WebSocket 服务消费 Kafka → 推送给订阅该行程的乘客
```

---

## 组件深入

### 1. 实时位置追踪服务

#### 写入路径设计

```python
# 伪代码：司机位置上报处理逻辑
class LocationService:

    def update_driver_location(self, driver_id: str, location: Location) -> None:
        """
        位置写入采用双写策略：
        - Redis：用于实时读取（当前位置）
        - Kafka：用于异步扇出（历史轨迹 + WebSocket 推送）
        """

        # 1. 写入 Redis（同步，毫秒级）
        redis_key = f"driver:location:{driver_id}"
        redis.hset(redis_key, mapping={
            "lat":       location.latitude,
            "lng":       location.longitude,
            "speed":     location.speed,
            "heading":   location.heading,
            "timestamp": location.timestamp,
        })
        redis.expire(redis_key, 300)  # 5 分钟 TTL：司机下线后自动清除

        # 2. 更新 Redis Geo 索引（用于附近司机查询）
        if driver.status == DriverStatus.AVAILABLE:
            redis.geoadd(
                "drivers:geo",
                location.longitude,
                location.latitude,
                driver_id
            )

        # 3. 发布到 Kafka（异步，不阻塞响应）
        kafka_producer.send(
            topic="driver-location-updates",
            key=driver_id,
            value={
                "driver_id":  driver_id,
                "ride_id":    driver.current_ride_id,  # 行程中才有值
                "latitude":   location.latitude,
                "longitude":  location.longitude,
                "speed":      location.speed,
                "heading":    location.heading,
                "timestamp":  location.timestamp,
            }
        )
        # Kafka 写入是异步的，不等待 ACK，接受极低概率的数据丢失

    def get_driver_current_location(self, driver_id: str) -> Location | None:
        """从 Redis 读取司机当前位置（微秒级延迟）"""
        redis_key = f"driver:location:{driver_id}"
        data = redis.hgetall(redis_key)
        if not data:
            return None
        return Location(
            latitude=float(data["lat"]),
            longitude=float(data["lng"]),
            speed=float(data["speed"]),
            heading=int(data["heading"]),
            timestamp=int(data["timestamp"]),
        )
```

#### 为什么不用 PostgreSQL 存实时位置

| 对比项 | Redis | PostgreSQL |
|--------|-------|------------|
| 写入延迟 | < 1ms（内存操作） | 5-20ms（磁盘 I/O） |
| 25K QPS 写入 | 轻松应对 | 接近瓶颈（需要大量调优） |
| 数据模型 | Key-Value / Hash，结构简单 | 表结构，有 Schema 约束开销 |
| TTL 支持 | 原生支持，自动清理 | 需要定时任务清理 |
| 地理查询 | 内置 GEO 命令，O(N+logM) | PostGIS 扩展，查询较重 |
| 持久性 | 可选（RDB/AOF），但位置数据不需要持久化 | 强持久化 |
| 适用场景 | 高频写入、短生命周期、快速读取 | 复杂查询、事务、强一致性 |

**结论**：实时位置是典型的「写多读多、数据有时效性、不需要复杂查询」场景，Redis 是唯一合理选择。PostgreSQL 用于存储行程记录（低频写、需要事务和复杂查询）。

#### Cassandra 存储历史轨迹

```python
# 伪代码：Kafka 消费者将位置数据写入 Cassandra
class LocationHistoryConsumer:

    def consume(self, event: dict) -> None:
        """仅在行程进行中才持久化轨迹"""
        if event.get("ride_id") is None:
            return  # 非行程状态，不记录

        cassandra.execute("""
            INSERT INTO ride_location_history
                (ride_id, driver_id, timestamp, latitude, longitude, speed, heading)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            USING TTL 604800  -- 7天 TTL，自动过期
        """, (
            event["ride_id"],
            event["driver_id"],
            event["timestamp"],
            event["latitude"],
            event["longitude"],
            event["speed"],
            event["heading"],
        ))

# Cassandra 表设计
# CREATE TABLE ride_location_history (
#     ride_id    UUID,
#     timestamp  TIMESTAMP,
#     driver_id  UUID,
#     latitude   DOUBLE,
#     longitude  DOUBLE,
#     speed      FLOAT,
#     heading    INT,
#     PRIMARY KEY (ride_id, timestamp)   -- ride_id 为分区键，保证同一行程的轨迹在同一节点
# ) WITH CLUSTERING ORDER BY (timestamp ASC)
#   AND default_time_to_live = 604800;   -- 7天自动删除
```

**选择 Cassandra 而非 MySQL 存轨迹的原因**：
- 轨迹数据写多读少（写入频繁，只有行程回放时才读）
- 天然的时序数据模型（按 ride_id 分区，timestamp 聚集排序）
- 线性水平扩展，应对写入峰值无需停机调整
- 内置 TTL，无需额外清理任务

---

### 2. 地理索引：附近司机查找

#### 2.1 Geohash 方案

**Geohash 工作原理**

Geohash 将地球表面划分为层级网格，通过 Base32 字符串编码地理坐标。核心规则：
- 字符串越长，精度越高（网格越小）
- 字符串前缀相同的两个位置，在地理上一定相近
- 但地理上相近的两个位置，前缀不一定完全相同（边界问题）

| Geohash 长度 | 网格尺寸 | 精度说明 |
|-------------|---------|---------|
| 1 字符 | 5,009 km × 4,992 km | 洲级别 |
| 3 字符 | 156 km × 156 km | 省级别 |
| 5 字符 | 4.9 km × 4.9 km | 城市区域 |
| 6 字符 | 1.2 km × 0.6 km | 街道级别 |
| 7 字符 | 153 m × 153 m | 建筑级别 |
| 8 字符 | 38 m × 19 m | 门牌号级别 |

**Geohash 查询附近司机（Python 伪代码）**

```python
import math

# ---- Geohash 编码（简化实现，说明原理） ----

BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"

def encode_geohash(latitude: float, longitude: float, precision: int = 6) -> str:
    """
    将经纬度编码为 Geohash 字符串。
    原理：交替对经度和纬度进行二分，将结果拼接为二进制串，每 5 位转换为一个 Base32 字符。
    """
    lat_range = [-90.0, 90.0]
    lng_range = [-180.0, 180.0]
    bits = []
    is_longitude = True  # 先处理经度

    while len(bits) < precision * 5:
        if is_longitude:
            mid = (lng_range[0] + lng_range[1]) / 2
            if longitude >= mid:
                bits.append(1)
                lng_range[0] = mid
            else:
                bits.append(0)
                lng_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if latitude >= mid:
                bits.append(1)
                lat_range[0] = mid
            else:
                bits.append(0)
                lat_range[1] = mid
        is_longitude = not is_longitude

    # 每 5 位转换为一个 Base32 字符
    result = []
    for i in range(0, len(bits), 5):
        chunk = bits[i:i+5]
        index = int("".join(str(b) for b in chunk), 2)
        result.append(BASE32[index])

    return "".join(result)


def get_geohash_neighbors(geohash: str) -> list[str]:
    """
    获取一个 Geohash 格子的 8 个相邻格子。
    查询附近司机时，必须同时查询目标格子及其所有相邻格子，
    以解决边界问题（乘客在格子边缘时，最近的司机可能在相邻格子中）。
    """
    # 实际实现依赖 geohash 库，这里展示概念
    return [
        geohash_library.neighbor(geohash, direction)
        for direction in ["n", "ne", "e", "se", "s", "sw", "w", "nw"]
    ]


# ---- 基于 Geohash 的附近司机查询 ----

class GeohashDriverIndex:

    GEOHASH_PRECISION = 6  # 精度约 1.2km × 0.6km，适合城市内叫车场景

    def update_driver_location(self, driver_id: str, lat: float, lng: float) -> None:
        """司机位置更新时，同时更新 Geohash 索引"""
        new_hash = encode_geohash(lat, lng, self.GEOHASH_PRECISION)

        # 从旧 Geohash 集合中移除（需要存储司机当前所在的 Geohash）
        old_hash = redis.get(f"driver:geohash:{driver_id}")
        if old_hash:
            redis.srem(f"geohash:drivers:{old_hash}", driver_id)

        # 加入新 Geohash 集合
        redis.sadd(f"geohash:drivers:{new_hash}", driver_id)
        redis.set(f"driver:geohash:{driver_id}", new_hash)

    def find_nearby_drivers(
        self,
        pickup_lat: float,
        pickup_lng: float,
        radius_km: float = 3.0,
        max_results: int = 10
    ) -> list[Driver]:
        """
        查找附近可用司机。
        步骤：
        1. 计算乘客位置的 Geohash
        2. 获取目标格子 + 8 个相邻格子（共 9 个）
        3. 合并所有格子中的司机 ID
        4. 精确计算距离并过滤
        5. 按距离排序，返回最近的 N 个
        """
        # Step 1: 计算乘客位置的 Geohash
        target_hash = encode_geohash(pickup_lat, pickup_lng, self.GEOHASH_PRECISION)

        # Step 2 & 3: 查询目标格子及 8 个相邻格子
        search_hashes = [target_hash] + get_geohash_neighbors(target_hash)
        candidate_driver_ids = set()
        for h in search_hashes:
            drivers_in_cell = redis.smembers(f"geohash:drivers:{h}")
            candidate_driver_ids.update(drivers_in_cell)

        # Step 4: 精确距离过滤（Geohash 是近似的，需要精确过滤）
        nearby_drivers = []
        for driver_id in candidate_driver_ids:
            driver = get_driver_info(driver_id)
            if driver.status != DriverStatus.AVAILABLE:
                continue

            distance_km = haversine_distance(
                pickup_lat, pickup_lng,
                driver.location.latitude, driver.location.longitude
            )
            if distance_km <= radius_km:
                nearby_drivers.append((driver, distance_km))

        # Step 5: 按距离排序
        nearby_drivers.sort(key=lambda x: x[1])
        return [driver for driver, _ in nearby_drivers[:max_results]]


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """计算两点间球面距离（km）"""
    R = 6371  # 地球半径（km）
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))
```

**使用 Redis GEO 命令的替代方案（推荐）**

Redis 内置 GEO 命令集，底层基于 Geohash 实现，API 更简洁：

```python
class RedisGeoDriverIndex:

    GEO_KEY = "drivers:geo"

    def update_driver_location(self, driver_id: str, lat: float, lng: float) -> None:
        """Redis GEOADD 更新司机位置"""
        redis.geoadd(self.GEO_KEY, lng, lat, driver_id)
        # 注意：Redis GEO 命令参数顺序是 longitude, latitude（与直觉相反）

    def remove_driver(self, driver_id: str) -> None:
        """司机下线时从 GEO 索引移除"""
        redis.zrem(self.GEO_KEY, driver_id)  # GEO 底层是 sorted set

    def find_nearby_drivers(
        self,
        pickup_lat: float,
        pickup_lng: float,
        radius_km: float = 3.0,
        max_results: int = 10
    ) -> list[str]:
        """
        使用 GEORADIUS 命令（Redis 6.2+ 推荐用 GEOSEARCH）
        返回半径内司机 ID 列表，按距离排序
        """
        results = redis.geosearch(
            self.GEO_KEY,
            longitude=pickup_lng,
            latitude=pickup_lat,
            radius=radius_km,
            unit="km",
            sort="ASC",
            count=max_results,
            withdist=True,
            withcoord=True,
        )
        # results = [("driver_id_1", distance_km, (lng, lat)), ...]
        return [r[0] for r in results]
```

#### 2.2 QuadTree（四叉树）方案

QuadTree 是另一种常见的地理索引结构，通过递归将地图区域四等分，直到每个叶节点中的对象数量低于阈值。

```python
# 伪代码：QuadTree 数据结构
class BoundingBox:
    def __init__(self, min_lat, min_lng, max_lat, max_lng):
        self.min_lat = min_lat
        self.min_lng = min_lng
        self.max_lat = max_lat
        self.max_lng = max_lng

    def contains(self, lat: float, lng: float) -> bool:
        return (self.min_lat <= lat <= self.max_lat and
                self.min_lng <= lng <= self.max_lng)

    def intersects(self, other: "BoundingBox") -> bool:
        return not (other.min_lat > self.max_lat or
                    other.max_lat < self.min_lat or
                    other.min_lng > self.max_lng or
                    other.max_lng < self.min_lng)

    def subdivide(self) -> tuple["BoundingBox", "BoundingBox", "BoundingBox", "BoundingBox"]:
        """将当前区域四等分"""
        mid_lat = (self.min_lat + self.max_lat) / 2
        mid_lng = (self.min_lng + self.max_lng) / 2
        return (
            BoundingBox(mid_lat, self.min_lng, self.max_lat, mid_lng),  # 西北
            BoundingBox(mid_lat, mid_lng, self.max_lat, self.max_lng),  # 东北
            BoundingBox(self.min_lat, self.min_lng, mid_lat, mid_lng),  # 西南
            BoundingBox(self.min_lat, mid_lng, mid_lat, self.max_lng),  # 东南
        )


class QuadTreeNode:
    MAX_CAPACITY = 50    # 每个叶节点最多存储 50 个司机
    MAX_DEPTH = 20       # 最大深度，防止无限递归

    def __init__(self, boundary: BoundingBox, depth: int = 0):
        self.boundary = boundary
        self.depth = depth
        self.drivers: dict[str, tuple[float, float]] = {}  # driver_id -> (lat, lng)
        self.children: list["QuadTreeNode"] | None = None   # None 表示叶节点

    def insert(self, driver_id: str, lat: float, lng: float) -> bool:
        """插入司机位置"""
        if not self.boundary.contains(lat, lng):
            return False

        if self.children is None:  # 叶节点
            self.drivers[driver_id] = (lat, lng)
            if len(self.drivers) > self.MAX_CAPACITY and self.depth < self.MAX_DEPTH:
                self._subdivide()  # 超出容量时分裂
            return True

        # 内部节点：插入到对应子节点
        return any(child.insert(driver_id, lat, lng) for child in self.children)

    def _subdivide(self) -> None:
        """分裂：将当前叶节点转为内部节点，子区域四等分"""
        sub_boundaries = self.boundary.subdivide()
        self.children = [
            QuadTreeNode(b, self.depth + 1) for b in sub_boundaries
        ]
        # 将当前节点的司机重新插入子节点
        for driver_id, (lat, lng) in self.drivers.items():
            for child in self.children:
                if child.insert(driver_id, lat, lng):
                    break
        self.drivers.clear()

    def query_range(self, search_box: BoundingBox) -> list[str]:
        """查询矩形区域内的所有司机 ID"""
        if not self.boundary.intersects(search_box):
            return []

        results = []
        if self.children is None:  # 叶节点
            for driver_id, (lat, lng) in self.drivers.items():
                if search_box.contains(lat, lng):
                    results.append(driver_id)
        else:
            for child in self.children:
                results.extend(child.query_range(search_box))
        return results


# 查询附近司机（QuadTree 版本）
def find_nearby_drivers_quadtree(
    tree: QuadTreeNode,
    pickup_lat: float,
    pickup_lng: float,
    radius_km: float = 3.0
) -> list[str]:
    """
    将圆形搜索区域转换为近似的矩形边界框（BoundingBox），
    然后用 QuadTree 查询，最后做精确距离过滤。
    """
    # 粗略换算：1度纬度 ≈ 111 km
    delta_lat = radius_km / 111.0
    delta_lng = radius_km / (111.0 * math.cos(math.radians(pickup_lat)))

    search_box = BoundingBox(
        min_lat=pickup_lat - delta_lat,
        min_lng=pickup_lng - delta_lng,
        max_lat=pickup_lat + delta_lat,
        max_lng=pickup_lng + delta_lng,
    )

    candidates = tree.query_range(search_box)

    # 精确过滤（矩形 ⊃ 圆形，需要排除角落的点）
    return [
        driver_id for driver_id in candidates
        if haversine_distance(pickup_lat, pickup_lng,
                              *get_driver_location(driver_id)) <= radius_km
    ]
```

#### 2.3 三种方案对比

| 对比维度 | Geohash（Redis GEO） | QuadTree | PostGIS |
|---------|---------------------|----------|---------|
| 实现复杂度 | 低（Redis 内置命令） | 中（需要自实现树结构） | 低（SQL 扩展） |
| 查询性能 | O(logN)，毫秒级 | O(logN)，毫秒级 | 较高延迟，秒级 |
| 内存使用 | 低（Redis Sorted Set） | 高（树节点开销） | 极低（磁盘存储） |
| 动态更新 | 极佳（GEOADD 原子操作） | 中等（需要删除+重插入） | 较差（磁盘 I/O） |
| 密度自适应 | 差（固定精度） | 优（高密度区域自动细分） | 中等 |
| 边界问题 | 存在（需查 9 个格子） | 无（矩形分割无缝覆盖） | 无 |
| 水平扩展 | 优（Redis Cluster） | 难（树状结构难以分片） | 中等 |
| 适用场景 | 分布式、高并发写 | 内存型、密度差异大 | 低频查询、复杂地理计算 |
| 网约车推荐度 | ★★★★★ | ★★★☆☆ | ★★☆☆☆ |

**架构决策**：对于网约车系统，推荐使用 **Redis GEO（基于 Geohash）**。原因：
1. 运维简单，Redis 已经是系统的必选组件（用于实时位置存储）
2. 天然支持高并发写入（司机位置每秒更新 25K 次）
3. 水平扩展能力强（Redis Cluster）
4. 边界问题可通过查询相邻格子解决，影响可接受

---

### 3. 司机匹配算法

```python
# 伪代码：司机匹配服务核心逻辑
class MatchingService:

    def match_driver(self, ride_request: RideRequest) -> MatchResult:
        """
        司机匹配分三个阶段：
        Phase 1: 候选筛选（地理范围 + 状态过滤）
        Phase 2: 多维排序（距离 + 评分 + 接单率）
        Phase 3: 顺序推送（防止重复接单）
        """

        # === Phase 1: 候选筛选 ===
        nearby_driver_ids = redis_geo.find_nearby_drivers(
            pickup_lat=ride_request.pickup_lat,
            pickup_lng=ride_request.pickup_lng,
            radius_km=3.0,
            max_results=50,  # 获取较多候选，后续排序过滤
        )

        # 过滤非空闲司机（地理查询结果可能包含已接单的司机）
        available_drivers = []
        for driver_id in nearby_driver_ids:
            driver = driver_repository.get(driver_id)
            if (driver.status == DriverStatus.AVAILABLE and
                    driver.ride_type_supported(ride_request.ride_type)):
                available_drivers.append(driver)

        if not available_drivers:
            return MatchResult(success=False, reason="no_drivers_available")

        # === Phase 2: 多维评分排序 ===
        scored_drivers = []
        for driver in available_drivers:
            score = self._calculate_driver_score(driver, ride_request)
            scored_drivers.append((score, driver))

        scored_drivers.sort(key=lambda x: x[0], reverse=True)  # 分数高者优先
        top_drivers = [d for _, d in scored_drivers[:5]]  # 取前 5 名候选

        # === Phase 3: 顺序推送（防止重复接单） ===
        return self._dispatch_to_drivers(ride_request, top_drivers)

    def _calculate_driver_score(self, driver: Driver, request: RideRequest) -> float:
        """
        综合评分模型：
        - 距离分：越近分越高（权重 40%）
        - 评分分：乘客评分越高越好（权重 30%）
        - 接单率：历史接单率越高越好（权重 20%）
        - 完成率：行程完成率（权重 10%）
        """
        distance_km = haversine_distance(
            request.pickup_lat, request.pickup_lng,
            driver.location.latitude, driver.location.longitude
        )

        # 距离得分：3km 以内线性衰减，最远司机得分为 0
        max_radius = 3.0
        distance_score = max(0, (max_radius - distance_km) / max_radius)

        # 评分得分：将 1-5 星归一化为 0-1
        rating_score = (driver.rating - 1.0) / 4.0

        # 接单率：直接用历史接单率（0-1）
        acceptance_rate = driver.acceptance_rate_30d

        # 完成率：行程完成率（0-1）
        completion_rate = driver.completion_rate_30d

        # 加权综合得分
        final_score = (
            distance_score    * 0.40 +
            rating_score      * 0.30 +
            acceptance_rate   * 0.20 +
            completion_rate   * 0.10
        )
        return final_score

    def _dispatch_to_drivers(
        self,
        request: RideRequest,
        candidates: list[Driver]
    ) -> MatchResult:
        """
        顺序推送策略：
        1. 按排序依次向候选司机发推单通知
        2. 每个司机有 15 秒响应窗口
        3. 第一个接受的司机获得订单（原子操作防止竞争）
        4. 全部拒绝则扩大搜索范围重试
        """
        for driver in candidates:
            # 向司机发送推单通知（App Push / WebSocket）
            push_service.send_ride_request(driver.id, request)

            # 等待司机响应（最多 15 秒）
            response = wait_for_driver_response(driver.id, request.id, timeout=15)

            if response == DriverResponse.ACCEPT:
                # 原子性地锁定订单（防止并发情况下多个司机同时接单）
                locked = redis.set(
                    f"ride:lock:{request.id}",
                    driver.id,
                    ex=300,      # 5 分钟过期
                    nx=True,     # NX = Not eXists，只有不存在时才设置（原子操作）
                )
                if locked:
                    # 成功获取锁，订单归该司机
                    self._confirm_assignment(request, driver)
                    return MatchResult(success=True, driver=driver)
                else:
                    # 锁已被其他司机抢占（极端并发情况）
                    push_service.send_ride_taken(driver.id, request.id)
                    continue

            # 超时或拒绝，继续推给下一个司机

        # 所有候选司机均未接单
        return MatchResult(success=False, reason="all_drivers_rejected")
```

**防止重复接单的关键**：使用 Redis `SET NX`（原子操作）作为分布式锁，确保在高并发情况下同一订单只能被一个司机成功接受。

---

### 4. WebSocket 实时通信

#### 架构设计

```
司机 App（位置上报）
     │
     ▼  HTTP PUT /location
位置服务
     │
     ├──► Redis（更新当前位置）
     │
     └──► Kafka Topic: "driver-location-updates"
               │
               ▼
         WebSocket 服务集群（多实例）
         ┌──────────────────────────────┐
         │  消费 Kafka，找到订阅该行程  │
         │  的乘客 WebSocket 连接       │
         │  推送位置更新消息            │
         └──────────────────────────────┘
               │
               ▼  WebSocket Push
         乘客 App（实时看到司机位置）
```

#### WebSocket 服务实现

```python
# 伪代码：WebSocket 服务核心逻辑
import asyncio
from collections import defaultdict

class WebSocketTrackingService:
    """
    维护乘客连接的 WebSocket 服务。
    多实例部署时，需要通过 Redis Pub/Sub 或 Kafka 协调跨实例的消息分发。
    """

    def __init__(self):
        # 本实例维护的连接映射：ride_id -> [WebSocket 连接列表]
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def handle_passenger_connect(
        self,
        websocket: WebSocket,
        ride_id: str,
        passenger_id: str
    ) -> None:
        """乘客建立 WebSocket 连接"""
        await websocket.accept()

        # 注册连接
        self.connections[ride_id].append(websocket)

        # 在 Redis 记录该连接由本实例处理（用于跨实例路由）
        instance_id = get_instance_id()
        redis.sadd(f"ride:watchers:{ride_id}", f"{instance_id}:{passenger_id}")

        try:
            # 立即推送当前司机位置（避免乘客等待下一个位置更新）
            current_location = location_service.get_driver_current_location(
                get_driver_for_ride(ride_id)
            )
            if current_location:
                await websocket.send_json({
                    "type": "location_update",
                    "driver_location": current_location.to_dict(),
                    "timestamp": current_location.timestamp,
                })

            # 保持连接，等待断开
            await websocket.wait_for_disconnect()

        finally:
            # 清理连接
            self.connections[ride_id].remove(websocket)
            redis.srem(f"ride:watchers:{ride_id}", f"{instance_id}:{passenger_id}")

    async def broadcast_location_update(
        self,
        ride_id: str,
        location_event: dict
    ) -> None:
        """向订阅该行程的所有乘客推送位置更新"""
        message = {
            "type":            "location_update",
            "driver_location": {
                "latitude":  location_event["latitude"],
                "longitude": location_event["longitude"],
                "heading":   location_event["heading"],
                "speed":     location_event["speed"],
            },
            "eta_seconds": calculate_eta(ride_id, location_event),
            "timestamp":   location_event["timestamp"],
        }

        dead_connections = []
        for websocket in self.connections.get(ride_id, []):
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                dead_connections.append(websocket)

        # 清理断开的连接
        for ws in dead_connections:
            self.connections[ride_id].remove(ws)


# Kafka 消费者：将位置事件路由到 WebSocket 推送
class LocationEventRouter:

    def __init__(self, ws_service: WebSocketTrackingService):
        self.ws_service = ws_service

    async def consume_location_events(self) -> None:
        """持续消费 Kafka 中的位置事件，并触发 WebSocket 推送"""
        async for event in kafka_consumer.consume("driver-location-updates"):
            ride_id = event.get("ride_id")
            if ride_id is None:
                continue  # 非行程中的位置更新，忽略

            # 检查本实例是否有该行程的订阅者
            if ride_id in self.ws_service.connections:
                await self.ws_service.broadcast_location_update(ride_id, event)
```

#### 跨实例消息路由

当 WebSocket 服务水平扩展为多实例时，同一行程的乘客可能连接到不同实例：

```python
# 跨实例路由方案：使用 Redis Pub/Sub
class CrossInstanceRouter:

    def publish_location_event(self, ride_id: str, event: dict) -> None:
        """位置服务将事件发布到 Redis 频道"""
        channel = f"ride:location:{ride_id}"
        redis.publish(channel, json.dumps(event))

    async def subscribe_to_ride(self, ride_id: str, ws_service: WebSocketTrackingService):
        """每个 WebSocket 实例订阅相关频道"""
        channel = f"ride:location:{ride_id}"
        async with redis.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    event = json.loads(message["data"])
                    await ws_service.broadcast_location_update(ride_id, event)
```

---

## 权衡分析

### 1. Geohash vs QuadTree：实现简单性 vs 密度自适应

| 维度 | Geohash | QuadTree |
|------|---------|----------|
| 实现复杂度 | 低（Redis 内置，几行代码） | 高（需自实现树、分裂、平衡逻辑） |
| 密度自适应 | 差（城市中心和郊区用同一精度） | 优（高密度区域自动细分到更小格子） |
| 边界问题处理 | 需要额外查询 8 个相邻格子 | 无（矩形分割自然覆盖） |
| 分布式部署 | 优（Redis Cluster 天然分片） | 难（树状结构难以跨节点分片） |
| 更新开销 | 极低（O(logN) 的 Sorted Set 操作） | 中等（可能触发节点分裂） |
| 内存开销 | 低 | 较高（树节点本身占用内存） |

**架构师观点**：对于初版系统，Geohash（Redis GEO）是显而易见的选择——零额外开发成本、运维简单、扩展性强。QuadTree 适合以下场景：需要精细的密度自适应（如城市中心司机密度比郊区高 100 倍，需要不同精度），且系统规模足够大到值得付出额外的开发和运维成本。

### 2. WebSocket vs 长轮询（Long Polling）

| 维度 | WebSocket | 长轮询（Long Polling） |
|------|-----------|----------------------|
| 实时性 | 极佳（服务端主动推送，< 100ms） | 良好（轮询间隔决定延迟，通常 1-3s） |
| 服务器资源 | 每个连接维持 TCP 连接（连接数敏感） | 每次请求消耗 HTTP 线程 |
| 实现复杂度 | 较高（需要 WebSocket 服务、Kafka 消费、跨实例路由） | 低（普通 HTTP 接口 + 客户端循环） |
| 网络开销 | 低（无 HTTP Header 重复传输） | 高（每次请求携带完整 HTTP 头） |
| 负载均衡兼容性 | 较差（粘性会话要求） | 好（无状态，任意负载均衡策略） |
| 移动端电量消耗 | 低（维持单一长连接） | 高（频繁建连消耗电量） |
| 断网恢复 | 需要客户端重连逻辑 | 自然恢复（下次轮询即可） |

**架构师观点**：网约车场景的位置追踪要求强实时性（司机每 4 秒更新，乘客应 < 1 秒感知），WebSocket 是正确选择。长轮询可作为降级方案（当 WebSocket 连接失败时回退）。关键注意事项：WebSocket 服务必须设计为可水平扩展，解决跨实例消息路由问题（通过 Kafka 或 Redis Pub/Sub）。

### 3. Redis vs 数据库存实时位置

| 维度 | Redis | 关系型数据库（MySQL/PostgreSQL） |
|------|-------|--------------------------------|
| 读写延迟 | < 1ms（内存） | 5-50ms（含磁盘 I/O） |
| 吞吐量（25K QPS） | 轻松应对（单实例可达 100K QPS） | 需要大量分片和调优 |
| 数据持久性 | 可选持久化（位置数据本身不需要） | 强持久化 |
| 地理查询支持 | 内置 GEO 命令 | 需要 PostGIS 扩展 |
| TTL 支持 | 原生 EXPIRE 命令 | 需要定时清理任务 |
| 运维成本 | 低（简单数据结构） | 高（索引维护、表分区） |
| 故障影响 | Redis 重启后位置数据丢失（可接受，司机下次上报即恢复） | 数据不丢失 |

**架构师观点**：实时位置是「临时性」数据，本质上是司机当前状态的快照，不需要持久化。Redis 丢失后，下一个位置上报周期（4 秒）内即可恢复，业务影响极小。用关系型数据库存储实时位置是典型的过度设计，既带来不必要的性能瓶颈，又增加运维复杂度。

### 4. 同步匹配 vs 异步匹配

| 维度 | 同步匹配（叫车 API 直接返回司机） | 异步匹配（先返回 ride_id，后推送司机） |
|------|--------------------------------|--------------------------------------|
| 用户体验 | 略好（一次响应包含所有信息） | 稍差（需要两步：叫车 + 等待推送） |
| 系统复杂度 | 低（单次 HTTP 请求-响应） | 高（需要 WebSocket 或推送机制） |
| 超时风险 | 高（匹配耗时 > 2s 时 HTTP 超时） | 无（叫车 API 快速返回，匹配在后台进行） |
| 可扩展性 | 差（匹配服务成为同步瓶颈） | 优（匹配可以异步、并行处理） |
| 适用场景 | 小规模、低并发 | 大规模、高并发（推荐） |

**架构决策**：采用异步匹配。叫车 API（`POST /rides/request`）快速返回 `ride_id`，匹配结果通过 WebSocket 或 App Push 推送给乘客。这是 Uber/滴滴的实际做法。

---

## 总结

### Key Architect Takeaways

**1. 分层存储是处理高频时序数据的核心模式**

实时位置数据天然具有时效性梯度：最近 4 秒的数据用于显示、最近 20 分钟的数据用于当前行程、7 天内的数据用于回放、更早的数据可丢弃。对应存储选型：Redis（当前位置）→ Cassandra（短期轨迹）→ 丢弃。强行用一个数据库存所有层级的数据，必然在性能或成本上付出代价。

**2. 地理查询的「近似 + 精确」两阶段模式**

无论是 Geohash 还是 QuadTree，地理索引的查询结果都是近似的（矩形覆盖 vs 圆形目标区域），必须在第二阶段用 Haversine 公式做精确距离过滤。将「粗粒度索引缩小候选集」和「精确计算验证候选」分离，是处理大规模地理查询的标准范式，避免了对所有数据点做昂贵的精确计算。

**3. 竞态条件必须用原子操作解决，而非应用层锁**

司机抢单是典型的分布式竞态场景。用 Redis `SET NX`（原子操作）作为分布式锁，而非在应用层用「先查询、后更新」的逻辑，是防止多个司机同时接单的唯一可靠方案。任何需要「check-then-act」语义的分布式操作，都应寻找原子化的解决方案（Redis 原子命令、数据库乐观锁、CAS 操作等）。

**4. 实时推送系统的设计必须面向水平扩展**

WebSocket 服务是有状态的（每个连接维持在特定实例上），这给水平扩展带来挑战。解决方案是引入消息总线（Kafka/Redis Pub/Sub）作为 WebSocket 实例间的协调层：位置事件发布到 Kafka，所有 WebSocket 实例订阅并将消息路由到本实例维护的连接。这种「有状态服务 + 无状态消息总线」的模式，是构建可扩展实时推送系统的通用架构范式。

---

## 参考架构图（最终版）

```
┌─────────────────────────────────────────────────────────────────────┐
│                          客户端层                                     │
│    ┌─────────────────┐              ┌─────────────────┐             │
│    │   乘客 App       │              │   司机 App       │             │
│    │ WebSocket 追踪   │              │ 位置上报（4s/次）│             │
│    └────────┬────────┘              └────────┬────────┘             │
└─────────────┼──────────────────────────────┼─────────────────────────┘
              │ WSS                          │ HTTPS
              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    API Gateway（Nginx / Kong）                        │
│                鉴权 / 限流 / 路由 / SSL 终止                          │
└────┬─────────────────┬──────────────────┬──────────────┬────────────┘
     │                 │                  │              │
     ▼                 ▼                  ▼              ▼
┌─────────┐     ┌──────────┐      ┌──────────┐   ┌──────────────┐
│ 行程服务 │     │ 位置服务  │      │ 匹配服务  │   │ WebSocket服务│
│ （状态） │     │（写 Redis │      │（地理查询 │   │（推送位置给  │
│         │     │ + Kafka） │      │ + 排序）  │   │  乘客）      │
└────┬────┘     └───┬──────┘      └────┬─────┘   └──────┬───────┘
     │              │                  │                 │
     ▼              ├──────────────────┤                 │
┌─────────┐         │                  │           ┌─────┴─────┐
│  MySQL  │         ▼                  ▼           │   Kafka   │
│ 行程记录 │     ┌─────────┐      ┌─────────┐      │ 位置事件  │
│ 用户信息 │     │  Redis  │      │  Redis  │      │ 消息总线  │
└─────────┘     │当前位置  │      │ GEO索引  │      └───────────┘
                │（Hash）  │      │(Sorted   │
                └─────────┘      │  Set)   │
                     │           └─────────┘
                     ▼
               ┌──────────┐
               │Cassandra │
               │历史轨迹  │
               │(TTL 7天) │
               └──────────┘
```
