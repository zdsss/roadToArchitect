# 网络基础知识（Networking Fundamentals）

## OSI 模型（OSI Model）

理解网络协议的 7 层模型：

| 层级 | 名称 | 协议示例 | 职责 |
|------|------|----------|------|
| 7 | 应用层 | HTTP, HTTPS, DNS, SMTP | 面向用户的协议 |
| 6 | 表示层 | TLS/SSL, JPEG, JSON | 编码、加密 |
| 5 | 会话层 | RPC, NetBIOS | 会话管理 |
| 4 | 传输层 | TCP, UDP | 可靠/不可靠传输 |
| 3 | 网络层 | IP, ICMP, OSPF | 跨网络路由 |
| 2 | 数据链路层 | Ethernet, ARP, MAC | 同一网络内节点间通信 |
| 1 | 物理层 | 网线、无线电、光纤 | 通过介质传输比特流 |

**架构师提示：** 日常工作主要集中在 L4–L7 层。务必对 TCP 与 UDP 的区别了如指掌。

---

## TCP 与 UDP

| 属性 | TCP | UDP |
|------|-----|-----|
| 连接方式 | 面向连接（三次握手） | 无连接 |
| 可靠性 | 保证投递、有序传输、重传机制 | 尽力而为 |
| 开销 | 高（包头、ACK、流量控制） | 低 |
| 适用场景 | HTTP、数据库连接、文件传输 | DNS、视频流、游戏、VoIP |

### TCP 握手（TCP Handshake）
```
Client → Server: SYN
Server → Client: SYN-ACK
Client → Server: ACK
--- connection established ---
Client → Server: FIN
Server → Client: ACK + FIN
Client → Server: ACK
--- connection closed ---
```

---

## HTTP/HTTPS

### HTTP 方法（HTTP Methods）
| 方法 | 幂等性 | 安全性 | 用途 |
|------|--------|--------|------|
| GET | 是 | 是 | 获取资源 |
| POST | 否 | 否 | 创建资源 |
| PUT | 是 | 否 | 替换资源 |
| PATCH | 否 | 否 | 部分更新 |
| DELETE | 是 | 否 | 删除资源 |

### HTTP 状态码（HTTP Status Codes）
- **2xx** — 成功（200 OK、201 Created、204 No Content）
- **3xx** — 重定向（301 Moved Permanently、304 Not Modified）
- **4xx** — 客户端错误（400 Bad Request、401 Unauthorized、403 Forbidden、404 Not Found、429 Too Many Requests）
- **5xx** — 服务端错误（500 Internal Server Error、502 Bad Gateway、503 Service Unavailable）

### HTTP/1.1 vs HTTP/2 vs HTTP/3
| 版本 | 传输协议 | 多路复用 | 队头阻塞（Head-of-line blocking） |
|------|----------|----------|----------------------------------|
| HTTP/1.1 | TCP | 否（仅支持流水线） | 存在 |
| HTTP/2 | TCP | 是（流式传输） | 存在（TCP 层面） |
| HTTP/3 | QUIC (UDP) | 是 | 不存在 |

---

## DNS（Domain Name System，域名系统）

DNS 将主机名转换为 IP 地址。

### 解析链（Resolution chain）
```
Browser cache → OS cache → Recursive resolver → Root NS → TLD NS → Authoritative NS
```

### 记录类型（Record Types）
| 类型 | 用途 | 示例 |
|------|------|------|
| A | IPv4 地址 | `api.example.com → 1.2.3.4` |
| AAAA | IPv6 地址 | `api.example.com → ::1` |
| CNAME | 别名 | `www → example.com` |
| MX | 邮件服务器 | `example.com → mail.example.com` |
| TXT | 任意文本 | SPF、DKIM 记录 |
| NS | 域名服务器 | 委托区域解析 |

**TTL（生存时间）** 控制解析器缓存记录的时长。TTL 越低，传播越快，但 DNS 负载越高。

---

## 负载均衡（Load Balancing）

### 算法（Algorithms）
- **轮询（Round Robin）** — 请求按顺序均匀分发
- **最少连接（Least Connections）** — 转发到活跃连接数最少的服务器
- **IP 哈希（IP Hash）** — 同一客户端始终路由到同一服务器（会话亲和性）
- **加权（Weighted）** — 将更多流量分配给性能更强的服务器

### L4 与 L7 负载均衡

| | L4（传输层） | L7（应用层） |
|--|-------------|-------------|
| 工作依据 | IP + TCP/UDP | HTTP 头、URL、Cookie |
| 速度 | 较快 | 较慢 |
| 路由逻辑 | 基于 IP/端口 | 基于内容 |
| 示例 | AWS NLB、HAProxy TCP | AWS ALB、Nginx、Envoy |

---

## CDN（内容分发网络，Content Delivery Network）

将静态资源（图片、JS、CSS）分发到靠近用户的边缘节点。

- 通过从最近的 PoP（接入点，Point of Presence）提供服务来降低延迟
- 吸收流量峰值 — 源站只需处理缓存未命中的请求
- **推送型 CDN（Push CDN）**：主动将内容上传到 CDN
- **拉取型 CDN（Pull CDN）**：首次请求时 CDN 从源站拉取内容并缓存，后续直接提供缓存

---

## WebSocket 与长轮询

| 技术 | 描述 | 适用场景 |
|------|------|----------|
| 短轮询（Short polling） | 客户端每隔 N 秒轮询一次 | 简单，但浪费资源 |
| 长轮询（Long polling） | 服务器持有请求直到有数据返回 | 聊天、通知 |
| WebSocket | 持久化全双工 TCP 连接 | 实时、低延迟场景 |
| SSE（Server-Sent Events，服务器推送事件） | 服务器单向推送给客户端 | 实时动态、仪表盘 |

---

## 架构师核心要点

1. 了解何时需要 TCP 的可靠性保证，何时 UDP 的速度优势值得取舍。
2. 使用正确的 HTTP 语义设计 API — 幂等性对于重试机制至关重要。
3. DNS TTL 影响部署策略（蓝绿部署、金丝雀发布）。
4. L7 负载均衡器提供更灵活的路由能力（A/B 测试、认证卸载）。
5. CDN 是应对流量峰值的第一道防线 — 务必善加利用。
