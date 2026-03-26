# 系统设计案例：视频流媒体平台（类 YouTube）

> 架构师视角：本文以 YouTube 量级为参考基准，完整走一遍从需求到落地的系统设计过程，重点关注权衡决策而非唯一答案。

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
| 视频上传 | 支持大文件断点续传，上传完成后异步转码 | P0 |
| 视频播放 | 流式播放，支持拖拽进度条，自适应码率 | P0 |
| 视频搜索 | 按标题、标签、描述全文检索 | P1 |
| 评论与点赞 | 视频级评论、嵌套回复、点赞/踩 | P1 |
| 订阅与推荐 | 订阅频道，个性化推荐信息流 | P1 |
| 用户认证 | 注册、登录、OAuth 第三方登录 | P0 |

**核心流程（面试时优先聚焦）：**
- **上传路径**：用户上传原始视频 → 存储 → 转码 → 分发
- **播放路径**：用户请求 → CDN 边缘 → 视频分片回传

### 1.2 非功能需求

| 需求 | 指标 | 设计影响 |
|------|------|----------|
| 高可用 | 99.99% SLA，年停机 < 52 分钟 | 多区域部署，无单点故障 |
| 全球低延迟 | 视频启动延迟 < 2 秒 | CDN 边缘节点覆盖全球 |
| 多分辨率支持 | 360p / 480p / 720p / 1080p / 4K | 转码流水线，自适应码率 |
| 断点续播 | 用户可从上次观看位置继续 | 播放进度持久化到用户服务 |
| 最终一致性可接受 | 订阅数、播放量允许秒级延迟 | 读写分离，异步聚合计数 |
| 存储耐久性 | 视频内容不丢失，11 个 9 耐久性 | 对象存储（S3/OSS）多副本 |

### 1.3 明确不在范围内（Out of Scope）

- 直播功能（RTMP 推流）
- 版权数字水印（DRM）
- 广告插播系统
- 创作者收益分配

> **架构师思考**：明确边界是系统设计的第一步。将直播排除在外使我们可以专注于 VOD（Video on Demand）场景，两者在上传路径、延迟要求和缓存策略上差异显著。

---

## 2. 规模估算

### 2.1 用户与流量

```
DAU（日活跃用户）      = 10 亿
每分钟视频上传量        = 500 小时（YouTube 2023 数据）
用户日均观看时长        = 30 分钟
读写比                 = 读(观看) : 写(上传) ≈ 200:1
```

**上传量估算：**

```python
# 每天上传的原始视频时长
upload_hours_per_day = 500 * 60  # 500小时/分钟 × 60分钟 = 30,000 小时/天
upload_seconds_per_day = upload_hours_per_day * 3600  # = 108,000,000 秒/天
```

**播放请求估算：**

```python
dau = 1_000_000_000           # 10 亿 DAU
avg_watch_per_user = 30 * 60  # 30 分钟 = 1800 秒

total_watch_seconds_per_day = dau * avg_watch_per_user
# = 1.8 × 10^12 秒/天

avg_segment_duration = 6      # HLS 分片 6 秒
total_segment_requests_per_day = total_watch_seconds_per_day / avg_segment_duration
# ≈ 3 × 10^11 次分片请求/天
# ≈ 3,500,000 次/秒（QPS 峰值取均值 3 倍 ≈ 10M QPS，由 CDN 承接）
```

### 2.2 存储估算

**原始视频存储：**

```python
# 假设平均上传视频时长 10 分钟，原始 1080p 约 2GB
avg_raw_size_gb = 2          # GB / 视频
daily_uploads = 500 * 60 / 10  # 500小时/分钟 ÷ 10分钟/视频 = 3000 视频/分钟

# 每分钟原始存储增量
raw_storage_per_min = daily_uploads * avg_raw_size_gb  # = 6000 GB/分钟 = 约 6 TB/分钟

# 每天原始存储增量
raw_storage_per_day = raw_storage_per_min * 60 * 24    # ≈ 8.6 PB/天
```

**多分辨率转码存储（每个视频）：**

| 分辨率 | 码率（Mbps） | 10 分钟视频大小 |
|--------|-------------|----------------|
| 1080p  | 8           | 600 MB         |
| 720p   | 5           | 375 MB         |
| 480p   | 2.5         | 188 MB         |
| 360p   | 1           | 75 MB          |
| **合计** | —         | **~1.2 GB**    |

```python
# 相对原始视频（2GB），转码后总存储 ≈ 1.2GB
# 加上原始视频保留：单视频总存储 ≈ 3.2 GB

transcoded_ratio = 1.2 / 2.0   # 0.6x 原始视频大小
total_storage_multiplier = 1 + transcoded_ratio  # 1.6x

daily_total_storage = raw_storage_per_day * total_storage_multiplier
# ≈ 8.6 PB × 1.6 ≈ 13.8 PB/天

# 5年总存储
five_year_storage = daily_total_storage * 365 * 5
# ≈ 25 EB（艾字节）
```

> **架构师注**：实际 YouTube 会对长尾低热度视频进行冷存储（Glacier 级别），以降低存储成本。热门视频 Top 1% 可能占据 50% 以上的播放量，存储分级至关重要。

### 2.3 带宽估算

```python
# 并发观看人数估算（假设 DAU 中 10% 同时在线）
concurrent_viewers = dau * 0.10  # = 1 亿并发

# 平均观看码率（多分辨率加权平均，约 4 Mbps）
avg_bitrate_mbps = 4

# 出口带宽（CDN 承接，非源站）
total_bandwidth_tbps = concurrent_viewers * avg_bitrate_mbps / 1_000_000
# = 100,000,000 × 4 Mbps / 1,000,000 = 400 Tbps

# CDN 实际会有 80%+ 命中率，源站带宽
cdn_hit_rate = 0.85
origin_bandwidth_tbps = total_bandwidth_tbps * (1 - cdn_hit_rate)
# = 400 × 0.15 = 60 Tbps（源站出口）
```

---

## 3. API 设计

### 3.1 视频上传 API

```
POST /v1/videos/upload/initiate
```

**请求体：**
```python
{
    "title": "string",
    "description": "string",
    "tags": ["string"],
    "total_size_bytes": 1073741824,   # 1 GB
    "total_chunks": 1024,
    "content_type": "video/mp4"
}
```

**响应：**
```python
{
    "upload_id": "uuid-xxxx",
    "chunk_size_bytes": 1048576,      # 1 MB 每片
    "upload_urls": [                  # 预签名 URL，直接上传到对象存储
        {
            "chunk_index": 0,
            "presigned_url": "https://oss.example.com/...",
            "expires_at": "2026-03-26T12:00:00Z"
        }
        # ...
    ]
}
```

```
PUT /v1/videos/upload/{upload_id}/chunks/{chunk_index}
```
> 客户端直接将分片上传到预签名 URL（绕过应用服务器，减少中间层压力）

```
POST /v1/videos/upload/{upload_id}/complete
```

**请求体：**
```python
{
    "etags": [                        # 每个分片的 ETag，用于完整性校验
        {"chunk_index": 0, "etag": "abc123"},
        # ...
    ]
}
```

**响应：**
```python
{
    "video_id": "v_xxxx",
    "status": "UPLOADED",
    "estimated_ready_at": "2026-03-26T13:00:00Z"
}
```

### 3.2 视频播放 API

```
GET /v1/videos/{video_id}/manifest.m3u8
```

**响应（HLS 主播放列表）：**
```
#EXTM3U
#EXT-X-VERSION:3

#EXT-X-STREAM-INF:BANDWIDTH=8000000,RESOLUTION=1920x1080
1080p/playlist.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1280x720
720p/playlist.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=854x480
480p/playlist.m3u8

#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=640x360
360p/playlist.m3u8
```

```
GET /v1/videos/{video_id}/segments/{resolution}/{segment_id}.ts
```
> 视频分片文件，由 CDN 边缘节点直接服务，对象存储为源站

### 3.3 推荐信息流 API

```
GET /v1/feed?cursor={cursor}&limit={limit}
```

**响应：**
```python
{
    "videos": [
        {
            "video_id": "v_xxxx",
            "title": "string",
            "thumbnail_url": "https://cdn.example.com/thumbnails/...",
            "duration_seconds": 600,
            "view_count": 1500000,
            "like_count": 45000,
            "channel": {
                "channel_id": "c_xxxx",
                "name": "string",
                "avatar_url": "string"
            },
            "published_at": "2026-03-25T10:00:00Z"
        }
        # ...
    ],
    "next_cursor": "eyJ0cyI6MTc0MjkwMDAwMH0="
}
```

### 3.4 评论 API

```
POST /v1/videos/{video_id}/comments
GET  /v1/videos/{video_id}/comments?sort=top&cursor={cursor}
POST /v1/comments/{comment_id}/like
DELETE /v1/comments/{comment_id}
```

### 3.5 搜索 API

```
GET /v1/search?q={query}&filter=video&sort=relevance&page={page}
```

---

## 4. 高层设计

### 4.1 整体架构图（文字描述）

```
[用户设备]
    │
    ▼
[全局负载均衡器 / Anycast DNS]
    │
    ├──────────────────────────────────────────────────┐
    ▼                                                  ▼
[CDN 边缘节点]（视频分片、缩略图）          [API 网关]（REST 请求）
    │                                                  │
    │ Cache Miss                              ┌────────┼────────┐
    ▼                                         ▼        ▼        ▼
[对象存储 S3/OSS]                      [上传服务] [播放服务] [推荐服务]
    ▲                                         │        │        │
    │                                         ▼        ▼        ▼
[转码服务集群]◄──[消息队列 Kafka]      [元数据DB] [进度DB] [推荐引擎]
    │                (上传完成事件)      [MySQL]   [Redis]  [ML模型]
    └──────────────────────────────────────────────────┘
                   写回转码结果
```

### 4.2 上传路径详解

```
用户
 │  1. 请求上传初始化（获取预签名 URL）
 ▼
API 网关 → 上传服务
 │  2. 返回分片预签名 URL（直传对象存储，绕过应用层）
 ▼
用户
 │  3. 并行分片直传到对象存储
 ▼
对象存储（S3/OSS）
 │  4. 上传完成事件 → Kafka Topic: video.uploaded
 ▼
Kafka
 │  5. 转码 Worker 消费事件
 ▼
转码服务集群（FFmpeg Workers）
 │  6. 生成多分辨率 + HLS 分片 → 写回对象存储
 │  7. 更新视频状态 PROCESSING → READY
 ▼
对象存储（存储转码后分片）
 │  8. CDN 预热热门视频
 ▼
CDN 边缘节点
```

### 4.3 播放路径详解

```
用户播放器
 │  1. GET /videos/{id}/manifest.m3u8
 ▼
CDN 边缘节点
 │  命中缓存？──YES──► 直接返回 m3u8（< 5ms）
 │  NO
 ▼
对象存储（回源）→ 返回 m3u8 → CDN 缓存 → 用户

用户播放器解析 m3u8，根据当前带宽选择清晰度
 │  2. GET /videos/{id}/segments/720p/seg_001.ts
 ▼
CDN 边缘节点（命中率 85%+）
 │  命中 → 直接传输（< 20ms）
 │  未命中 → 回源对象存储
```

---

## 5. 组件深入

### 5.1 视频上传与断点续传

#### 5.1.1 为什么需要分片上传？

| 问题 | 单次大文件上传 | 分片上传 |
|------|--------------|----------|
| 网络中断 | 重传全部 | 仅重传失败分片 |
| 上传速度 | 单线程 | 并行多线程 |
| 服务器内存 | 需缓冲整个文件 | 每次处理一个小片 |
| 断点续传 | 不支持 | 记录已完成分片，断后续传 |

#### 5.1.2 分片上传伪代码

```python
# 客户端分片上传逻辑（伪代码）

CHUNK_SIZE = 1 * 1024 * 1024  # 1MB 每片

def upload_video(file_path: str, metadata: dict) -> str:
    file_size = os.path.getsize(file_path)
    total_chunks = math.ceil(file_size / CHUNK_SIZE)

    # Step 1: 初始化上传，获取 upload_id 和预签名 URL
    response = api.post("/videos/upload/initiate", {
        "total_size_bytes": file_size,
        "total_chunks": total_chunks,
        **metadata
    })
    upload_id = response["upload_id"]
    presigned_urls = {item["chunk_index"]: item["presigned_url"]
                      for item in response["upload_urls"]}

    # Step 2: 从本地状态恢复已上传的分片（断点续传）
    completed_chunks = load_local_progress(upload_id)  # 读取本地缓存
    etags = completed_chunks.copy()

    # Step 3: 并行上传未完成的分片
    pending_chunks = [i for i in range(total_chunks) if i not in completed_chunks]

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(upload_chunk, file_path, i, presigned_urls[i]): i
            for i in pending_chunks
        }
        for future in as_completed(futures):
            chunk_index = futures[future]
            etag = future.result()  # 上传成功返回 ETag
            etags[chunk_index] = etag
            save_local_progress(upload_id, chunk_index, etag)  # 持久化进度

    # Step 4: 通知服务端合并
    complete_response = api.post(f"/videos/upload/{upload_id}/complete", {
        "etags": [{"chunk_index": i, "etag": etags[i]}
                  for i in range(total_chunks)]
    })
    return complete_response["video_id"]


def upload_chunk(file_path: str, chunk_index: int, presigned_url: str) -> str:
    offset = chunk_index * CHUNK_SIZE
    with open(file_path, "rb") as f:
        f.seek(offset)
        data = f.read(CHUNK_SIZE)

    # 直接 PUT 到对象存储预签名 URL
    response = http.put(presigned_url, data=data)
    response.raise_for_status()
    return response.headers["ETag"]
```

#### 5.1.3 服务端分片合并（对象存储侧）

```python
# 服务端合并逻辑（伪代码）

def complete_upload(upload_id: str, etags: list) -> dict:
    upload_record = db.get_upload(upload_id)

    # 验证所有分片已上传
    if len(etags) != upload_record.total_chunks:
        raise ValueError("分片数量不匹配")

    # 调用对象存储 Multipart Complete API（如 S3 CompleteMultipartUpload）
    object_key = f"raw/{upload_id}/original.mp4"
    storage.complete_multipart_upload(
        bucket="raw-videos",
        key=object_key,
        upload_id=upload_record.storage_upload_id,
        parts=[{"PartNumber": e["chunk_index"] + 1, "ETag": e["etag"]}
               for e in sorted(etags, key=lambda x: x["chunk_index"])]
    )

    # 更新视频元数据状态
    video_id = upload_record.video_id
    db.update_video_status(video_id, "UPLOADED")

    # 发布转码事件到消息队列
    kafka.produce("video.uploaded", {
        "video_id": video_id,
        "object_key": object_key,
        "uploader_id": upload_record.user_id
    })

    return {"video_id": video_id, "status": "UPLOADED"}
```

### 5.2 转码流水线

#### 5.2.1 转码状态机

```
INITIATED
    │
    │ (用户完成分片上传)
    ▼
UPLOADED
    │
    │ (Kafka 消费者接收事件)
    ▼
PROCESSING ──── 超时/错误 ────► FAILED
    │                               │
    │ (所有分辨率转码完成)           │ (重试策略：指数退避，最多 3 次)
    ▼                               │
  READY ◄─────────────────────────── (重试成功)
    │
    │ (视频对外可见，CDN 预热)
    ▼
PUBLISHED
```

#### 5.2.2 转码 Worker 伪代码

```python
# 转码 Worker（消费 Kafka 事件）

def transcode_worker():
    consumer = KafkaConsumer("video.uploaded", group_id="transcode-workers")

    for message in consumer:
        payload = json.loads(message.value)
        video_id = payload["video_id"]
        object_key = payload["object_key"]

        try:
            db.update_video_status(video_id, "PROCESSING")

            # 下载原始视频到本地临时目录（或使用流式处理）
            local_path = download_from_storage("raw-videos", object_key)

            # 并行转码多个分辨率
            resolutions = [
                {"name": "1080p", "width": 1920, "height": 1080, "bitrate": "8000k"},
                {"name": "720p",  "width": 1280, "height": 720,  "bitrate": "5000k"},
                {"name": "480p",  "width": 854,  "height": 480,  "bitrate": "2500k"},
                {"name": "360p",  "width": 640,  "height": 360,  "bitrate": "1000k"},
            ]

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(transcode_to_hls, local_path,
                                           video_id, res)
                           for res in resolutions]
                results = [f.result() for f in futures]  # 等待全部完成

            # 生成主 m3u8（Master Playlist）
            generate_master_playlist(video_id, resolutions)

            # 上传所有分片到对象存储
            upload_transcoded_segments(video_id)

            db.update_video_status(video_id, "READY")

            # 通知 CDN 预热（热门频道视频）
            if is_popular_channel(payload["uploader_id"]):
                cdn.warm_up(f"videos/{video_id}/")

        except Exception as e:
            logger.error(f"转码失败 video_id={video_id}: {e}")
            db.update_video_status(video_id, "FAILED")
            db.increment_retry_count(video_id)
            # 重新放回队列（带延迟，指数退避）
            if db.get_retry_count(video_id) < 3:
                kafka.produce_delayed("video.uploaded", payload,
                                      delay_seconds=2 ** db.get_retry_count(video_id) * 60)
        finally:
            cleanup_temp_files(local_path)


def transcode_to_hls(input_path: str, video_id: str, resolution: dict):
    """调用 FFmpeg 转码为 HLS 格式"""
    output_dir = f"/tmp/transcoded/{video_id}/{resolution['name']}"
    os.makedirs(output_dir, exist_ok=True)

    # FFmpeg 命令：转码 + 切片
    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", f"scale={resolution['width']}:{resolution['height']}",
        "-c:v", "libx264",
        "-b:v", resolution["bitrate"],
        "-c:a", "aac",
        "-b:a", "128k",
        "-hls_time", "6",              # 每片 6 秒
        "-hls_playlist_type", "vod",
        "-hls_segment_filename", f"{output_dir}/seg_%05d.ts",
        f"{output_dir}/playlist.m3u8"
    ]
    subprocess.run(cmd, check=True)
    return output_dir
```

#### 5.2.3 为什么需要多分辨率？

网络状况是动态变化的，用户可能从 WiFi 切换到 4G 再到 3G。单一分辨率会导致：
- 网络差时：缓冲卡顿（用户流失）
- 网络好时：画质低于实际能力（用户体验差）

多分辨率 + ABR（自适应码率）允许播放器实时感知带宽并无缝切换质量层。

### 5.3 自适应码率（ABR）与 HLS

#### 5.3.1 HLS 工作原理

```
播放器启动
    │
    ▼
获取 Master Playlist (manifest.m3u8)
    │ 包含所有清晰度及其带宽要求
    ▼
根据当前网络带宽，选择初始质量层（通常从低质量开始）
    │
    ▼
获取对应分辨率的 Media Playlist (720p/playlist.m3u8)
    │ 包含所有分片的 URL 和时长
    ▼
顺序下载分片（.ts 文件），每片 6 秒
    │
    ├── 下载速度 > 当前码率 × 1.5 → 尝试切换更高质量
    │
    └── 下载速度 < 当前码率 × 0.8 → 降低质量
```

#### 5.3.2 m3u8 清单文件结构示例

**主播放列表（Master Playlist）：**
```
#EXTM3U
#EXT-X-VERSION:3

# 1080p
#EXT-X-STREAM-INF:BANDWIDTH=8000000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2"
https://cdn.example.com/videos/v_xxxx/1080p/playlist.m3u8

# 720p
#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1280x720,CODECS="avc1.64001f,mp4a.40.2"
https://cdn.example.com/videos/v_xxxx/720p/playlist.m3u8

# 480p
#EXT-X-STREAM-INF:BANDWIDTH=2500000,RESOLUTION=854x480,CODECS="avc1.64001e,mp4a.40.2"
https://cdn.example.com/videos/v_xxxx/480p/playlist.m3u8

# 360p
#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=640x360,CODECS="avc1.64001e,mp4a.40.2"
https://cdn.example.com/videos/v_xxxx/360p/playlist.m3u8
```

**媒体播放列表（Media Playlist，720p 示例）：**
```
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:6
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-PLAYLIST-TYPE:VOD

#EXTINF:6.000,
https://cdn.example.com/videos/v_xxxx/720p/seg_00000.ts

#EXTINF:6.000,
https://cdn.example.com/videos/v_xxxx/720p/seg_00001.ts

#EXTINF:6.000,
https://cdn.example.com/videos/v_xxxx/720p/seg_00002.ts

# ... 更多分片

#EXT-X-ENDLIST
```

#### 5.3.3 ABR 算法伪代码

```python
# 播放器端 ABR 决策算法（简化版）

class ABRController:
    def __init__(self, available_bitrates: list):
        self.available_bitrates = sorted(available_bitrates)  # 升序
        self.current_index = 0          # 从最低质量开始
        self.buffer_seconds = 0.0
        self.download_history = []      # 最近 N 次下载速度

    def on_segment_downloaded(self, segment_size_bytes: int, download_time_sec: float):
        """每次分片下载完成后调用"""
        measured_throughput_bps = (segment_size_bytes * 8) / download_time_sec
        self.download_history.append(measured_throughput_bps)
        if len(self.download_history) > 5:
            self.download_history.pop(0)

    def select_next_quality(self) -> int:
        """返回下一个分片应使用的质量层索引"""
        # 使用最近 3 次的保守估计（取 80 百分位数，避免带宽抖动导致的频繁切换）
        if len(self.download_history) < 3:
            return self.current_index  # 数据不足时保持当前质量

        estimated_bandwidth = sorted(self.download_history[-3:])[1]  # 取中位数

        # 缓冲区低于 10 秒时，优先保证流畅性，降级
        if self.buffer_seconds < 10:
            target_bitrate = estimated_bandwidth * 0.7  # 保守系数
        else:
            target_bitrate = estimated_bandwidth * 0.85

        # 选择不超过目标带宽的最高质量层
        best_index = 0
        for i, bitrate in enumerate(self.available_bitrates):
            if bitrate <= target_bitrate:
                best_index = i

        # 限制单次切换幅度（不超过 1 层，避免剧烈跳变）
        if best_index > self.current_index + 1:
            best_index = self.current_index + 1

        self.current_index = best_index
        return self.current_index
```

### 5.4 CDN 分发策略

#### 5.4.1 热门内容 vs 长尾内容

```python
# CDN 预热策略（伪代码）

def on_video_published(video_id: str, channel_id: str):
    """视频发布后的 CDN 预热决策"""
    channel_stats = analytics.get_channel_stats(channel_id)

    # 判断是否为热门频道（订阅数 > 100万 或 历史均值播放量 > 10万）
    is_popular = (channel_stats.subscribers > 1_000_000 or
                  channel_stats.avg_views > 100_000)

    if is_popular:
        # 主动预热到全球边缘节点（尤其是频道粉丝集中的地区）
        target_regions = analytics.get_channel_audience_regions(channel_id)
        for region in target_regions:
            cdn.prefetch(
                urls=generate_segment_urls(video_id, resolutions=["720p", "480p"]),
                region=region,
                priority="high"
            )
    else:
        # 长尾视频：按需拉取（懒加载）
        # 第一个用户请求时，CDN miss → 回源对象存储 → 缓存
        pass

    # 无论如何都预热 m3u8 清单（轻量，几 KB）
    cdn.prefetch(
        urls=[f"https://cdn.example.com/videos/{video_id}/manifest.m3u8"],
        region="global"
    )
```

#### 5.4.2 地理路由策略

```bash
# DNS 地理就近解析（Anycast / GeoDNS 配置示例）

# 用户请求 cdn.example.com
# DNS 根据客户端 IP 的地理位置，返回最近 PoP 的 IP

# 北美用户 → 返回 us-east-cdn.example.com 的 IP
# 亚太用户 → 返回 ap-southeast-cdn.example.com 的 IP
# 欧洲用户 → 返回 eu-west-cdn.example.com 的 IP

# CDN PoP 节点数量与覆盖（生产级参考）
# - Cloudflare: 300+ 城市
# - AWS CloudFront: 450+ PoP
# - 阿里云 CDN: 3200+ 节点

# 边缘节点缓存配置
Cache-Control: public, max-age=86400, s-maxage=2592000
# 分片文件（.ts）：缓存 30 天（内容不可变）
# m3u8 清单：缓存 1 分钟（直播）或 1 天（VOD）
```

#### 5.4.3 CDN 缓存命中率分析

| 内容类型 | 大小 | 缓存时间 | 命中率 | 备注 |
|----------|------|----------|--------|------|
| m3u8 清单 | < 10 KB | 24 小时 | ~60% | 用户分散，各视频独立请求 |
| 热门视频分片 (.ts) | 3-5 MB/片 | 30 天 | ~95% | Top 20% 视频 |
| 长尾视频分片 (.ts) | 3-5 MB/片 | 30 天 | ~30% | 访问稀少，经常 Cold |
| 缩略图 | < 200 KB | 7 天 | ~90% | 信息流页面大量展示 |

### 5.5 对象存储设计

#### 5.5.1 存储层级策略

```python
# 存储生命周期规则（类 S3 Lifecycle Policy）

lifecycle_rules = [
    {
        "id": "raw-video-archival",
        "prefix": "raw/",
        "transitions": [
            # 原始视频上传后 30 天移至低频存储（转码完成后原始视频很少访问）
            {"days": 30, "storage_class": "STANDARD_IA"},
            # 6 个月后移至归档存储（节省 60% 成本）
            {"days": 180, "storage_class": "GLACIER"},
        ]
    },
    {
        "id": "transcoded-tiering",
        "prefix": "transcoded/",
        "transitions": [
            # 转码后分片：90 天无访问 → 低频
            {"days": 90, "storage_class": "STANDARD_IA",
             "condition": "last_accessed_days_ago > 90"},
            # 365 天无访问 → 归档（长尾视频）
            {"days": 365, "storage_class": "DEEP_ARCHIVE",
             "condition": "last_accessed_days_ago > 365"},
        ]
    }
]
```

**各存储层对比：**

| 存储层 | 月存储费用（$/GB）| 取出延迟 | 访问频率 | 适用场景 |
|--------|-----------------|----------|----------|----------|
| 标准存储 | ~$0.023 | 毫秒级 | 高频 | 热门视频分片，最近上传 |
| 低频存储 IA | ~$0.0125 | 毫秒级 | 月级 | 30-90 天内上传但非热门 |
| 归档 Glacier | ~$0.004 | 分钟级 | 极低 | 6 个月+ 的长尾内容 |
| 深度归档 | ~$0.00099 | 小时级 | 几乎不用 | 法规合规存储 |

#### 5.5.2 为什么不用普通文件服务器？

| 对比维度 | 普通文件服务器（NFS/本地磁盘）| 对象存储（S3/OSS）|
|----------|------------------------------|-------------------|
| 扩展性 | 纵向扩展受限，横向需要复杂分片逻辑 | 无限水平扩展，透明处理 |
| 耐久性 | 单机或小集群，RAID 保护 | 11 个 9（99.999999999%），跨 AZ 复制 |
| 运维成本 | 需要自行管理存储集群 | 全托管，零运维 |
| 并发访问 | 服务器带宽瓶颈 | 与 CDN 深度集成，并发无上限 |
| 预签名 URL | 不支持（文件访问需要代理） | 原生支持，客户端直传 |
| 生命周期管理 | 需要自写脚本 | 内置规则引擎 |

### 5.6 断点续播实现

```python
# 播放进度服务（伪代码）

class PlaybackProgressService:

    def save_progress(self, user_id: str, video_id: str, position_seconds: float):
        """每 5 秒由播放器客户端上报一次"""
        key = f"progress:{user_id}:{video_id}"
        # 使用 Redis 存储，TTL 30 天（过期自动清理）
        redis.set(key, {
            "position_seconds": position_seconds,
            "updated_at": time.time()
        }, ttl=30 * 24 * 3600)

        # 异步同步到 MySQL（用于跨设备同步）
        # 使用消息队列解耦，避免每次都写数据库
        mq.enqueue("progress.sync", {
            "user_id": user_id,
            "video_id": video_id,
            "position_seconds": position_seconds
        }, delay_seconds=30)  # 合并 30 秒内的多次写入

    def get_progress(self, user_id: str, video_id: str) -> float:
        """播放器启动时调用"""
        key = f"progress:{user_id}:{video_id}"

        # 优先读 Redis（本设备最新进度）
        cached = redis.get(key)
        if cached:
            return cached["position_seconds"]

        # Redis 未命中，读 MySQL（跨设备）
        record = db.query(
            "SELECT position_seconds FROM playback_progress "
            "WHERE user_id = %s AND video_id = %s",
            (user_id, video_id)
        )
        return record.position_seconds if record else 0.0
```

### 5.7 推荐系统概览

```python
# 推荐信息流生成（离线 + 在线混合架构）

# 离线：每小时批量计算（Spark 作业）
def offline_recommendation_job():
    """
    输入：用户观看历史、点赞、订阅、搜索记录
    模型：协同过滤 + 内容向量相似度（YouTube DNN 论文方案）
    输出：每个用户的 Top-500 候选视频列表，写入 Redis
    """
    user_history = spark.read_parquet("hdfs://user-events/")
    candidate_videos = collaborative_filter(user_history)
    ranked_videos = content_ranker(candidate_videos, user_features)

    for user_id, video_list in ranked_videos.items():
        redis.set(f"reco:{user_id}", video_list, ttl=3600)

# 在线：实时混合（API 请求时）
def get_feed(user_id: str, cursor: str) -> list:
    # 1. 读取离线候选集
    offline_candidates = redis.get(f"reco:{user_id}") or []

    # 2. 混入订阅频道最新视频（高优先级）
    subscriptions = db.get_subscriptions(user_id)
    fresh_videos = db.get_latest_videos(subscriptions, limit=10)

    # 3. 实时特征重排序（CTR 预估模型，考虑时效性）
    merged = merge_and_rerank(offline_candidates, fresh_videos,
                               user_context=get_user_context(user_id))

    # 4. 游标分页
    page_videos, next_cursor = paginate(merged, cursor, page_size=20)
    return page_videos, next_cursor
```

---

## 6. 权衡分析

### 6.1 HLS vs MPEG-DASH（流协议对比）

| 对比维度 | HLS（HTTP Live Streaming）| MPEG-DASH |
|----------|--------------------------|-----------|
| 开发者 | Apple | MPEG 标准委员会 |
| 标准类型 | 私有协议（事实标准）| 开放国际标准 |
| 原生支持 | iOS/macOS/Safari 原生 | 需要 JS 库（dash.js/Shaka Player）|
| Android/Chrome | 通过 Media Source Extensions | 原生支持 |
| 分片格式 | MPEG-TS（.ts）或 fMP4 | fMP4 / WebM |
| 分片时长 | 通常 2-10 秒 | 通常 2-10 秒 |
| 直播支持 | 支持（Low Latency HLS）| 支持 |
| 加密/DRM | AES-128 / FairPlay | Widevine / PlayReady |
| **主要优势** | iOS 覆盖，无需 JS | 更灵活，码率表示更精细 |
| **主要劣势** | 非开放标准 | 移动端需要额外适配 |

**架构师决策**：
- 面向 C 端消费者（含大量 iOS 用户）→ **选 HLS**，原生支持省去兼容成本
- 企业内部/专业播放器 → 可考虑 DASH，标准化带来更好的互操作性
- YouTube 实际使用 DASH（Chrome 原生支持），同时提供 HLS 给 iOS

### 6.2 CDN 预热 vs 按需拉取

| 对比维度 | CDN 主动预热 | 按需拉取（Lazy Loading）|
|----------|------------|------------------------|
| 首次播放延迟 | 极低（< 20ms）| 较高（首次回源可能 100-500ms）|
| CDN 存储成本 | 高（存储所有预热内容）| 低（只存实际访问内容）|
| 带宽成本 | 浪费（预热未访问的内容）| 精准（只传输有需求的内容）|
| 实现复杂度 | 需要热度预测模型 | 简单 |
| 适用场景 | 热门视频、重大发布 | 长尾视频 |

**混合策略（最佳实践）：**

```python
def decide_cdn_strategy(video_id: str, channel_id: str) -> str:
    channel = db.get_channel(channel_id)
    video = db.get_video(video_id)

    # 超大型频道（Top 1%）：全球预热
    if channel.subscribers > 10_000_000:
        return "global_prefetch"

    # 中型频道（Top 10%）：用户集中地区预热
    elif channel.subscribers > 1_000_000:
        return "regional_prefetch"

    # 小频道：按需拉取，CDN 自然缓存
    else:
        return "on_demand"
```

### 6.3 转码同步 vs 异步

| 对比维度 | 同步转码（上传后立即转码，阻塞返回）| 异步转码（上传后入队，后台处理）|
|----------|-----------------------------------|---------------------------------|
| 用户体验 | 上传慢（需等待转码完成才返回）| 上传快，但视频有延迟可见期 |
| 资源利用 | 转码资源绑定到上传请求 | 解耦，Worker 独立扩缩容 |
| 错误处理 | 简单（同一请求链路）| 复杂（需要状态轮询或 Webhook）|
| 峰值处理 | 上传高峰时，转码压垮服务 | 队列缓冲，平滑处理 |
| **结论** | 不可接受（YouTube 量级）| **强烈推荐** |

**为什么必须异步？**

1 GB 视频转码为 4 个分辨率的 HLS 需要 **约 5-15 分钟**（取决于 CPU 资源），用户不可能等待这么长时间的 HTTP 响应。异步转码允许系统返回 `202 Accepted`，用户可以关闭上传页面，视频在后台就绪后通过通知或状态轮询告知。

### 6.4 元数据存储：关系型 vs NoSQL

| 数据类型 | 推荐存储 | 理由 |
|----------|----------|------|
| 视频元数据（标题、时长、状态）| MySQL（主从复制）| 结构化，需要事务 |
| 用户信息、订阅关系 | MySQL | 关系明确，JOIN 频繁 |
| 播放进度 | Redis（主）+ MySQL（备）| 高频写，允许最终一致 |
| 评论 | MySQL + 分表 | 结构化，数量可控 |
| 视频播放计数 | Redis（实时）+ HBase（历史）| 极高写入，不需强一致 |
| 搜索索引 | Elasticsearch | 全文检索，倒排索引 |
| 推荐候选集 | Redis（在线）+ HDFS（离线）| 读多写少，批量更新 |

---

## 7. 总结

### Key Architect Takeaways

**1. 上传与播放路径必须完全解耦**

上传是写入密集型操作，播放是读取密集型操作，两者量级差异超过 200:1。通过对象存储 + CDN 的架构，播放路径中用户几乎不经过任何应用层服务器，95% 的请求由 CDN 边缘直接服务。将这两条路径设计为完全独立的子系统，是支撑 YouTube 量级的核心架构决策。

**2. 异步转码流水线是系统弹性的基石**

视频转码是 CPU 密集型操作，执行时间长且不确定。通过 Kafka + Worker 集群的异步架构，系统可以在上传高峰时积累队列，在流量低谷时消化，转码集群可以独立于上传服务进行弹性伸缩。转码状态机（UPLOADED → PROCESSING → READY/FAILED）配合重试策略，保证了即使单次转码失败也能自动恢复。

**3. 热冷数据分层是大规模存储成本控制的关键**

遵循 80/20 法则：Top 20% 的热门视频产生 80% 的流量。通过 CDN 层（边缘缓存）、对象存储标准层（热数据）、低频存储（温数据）、归档存储（冷数据）四级分层，可以在维持用户体验的同时将存储成本降低 60-80%。对象存储的生命周期规则可以自动化完成数据的冷热迁移，无需人工干预。

**4. 自适应码率（ABR）+ HLS 是解决全球网络异构性的标准答案**

全球用户网络环境差异巨大，从城市高速 WiFi 到偏远地区 2G。单一码率无法兼顾两端体验。HLS 将视频切成 6 秒的小片段，配合主播放列表描述多个质量层，让播放器可以根据实时测量的带宽每片动态决策使用哪个质量层。这一机制将视频启动延迟控制在 2 秒内，将卡顿率降低到 1% 以下，是现代视频平台的核心技术之一。

---

### 系统关键数字速查

| 指标 | 数值 |
|------|------|
| DAU | 10 亿 |
| 每分钟上传视频时长 | 500 小时 |
| 每日存储新增 | ~14 PB |
| 并发观看用户（峰值）| ~1 亿 |
| CDN 总出口带宽 | ~400 Tbps |
| 源站出口带宽（CDN Miss）| ~60 Tbps |
| CDN 命中率 | ~85% |
| 视频分片大小 | 3-5 MB（6 秒 @ 720p）|
| HLS 分片时长 | 6 秒 |
| 转码时间（1GB 视频）| 5-15 分钟 |
| 播放进度同步间隔 | 5 秒 |

---

*参考资料：YouTube Engineering Blog、《Designing Data-Intensive Applications》、AWS Architecture Center、Apple HLS 规范（RFC 8216）*
