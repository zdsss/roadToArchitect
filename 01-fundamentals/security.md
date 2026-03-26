# 安全基础（Security Fundamentals）

## 认证（Authentication）与授权（Authorization）的区别

| 概念 | 回答的问题 | 示例 |
|------|-----------|------|
| 认证（Authentication） | 你是谁？ | 使用用户名/密码登录 |
| 授权（Authorization） | 你能做什么？ | 基于角色的访问控制 |

---

## 常见的认证机制

### 基于会话的认证（Session-Based Auth）
```
Client → POST /login → Server creates session → Returns session cookie
Client → GET /data + cookie → Server validates session → Returns data
```
- 状态存储在服务端
- 易于撤销
- 若无共享会话存储（如 Redis），则难以水平扩展

### JWT（JSON Web Token）
```
Header.Payload.Signature
```
- 无状态——服务端无需存储会话
- 自包含：声明（claims）直接嵌入令牌中
- 无法在不使用令牌黑名单的情况下撤销
- 建议使用较短的过期时间（15分钟）并配合刷新令牌（refresh token）

### OAuth 2.0 授权流程
| 流程 | 适用场景 |
|------|---------|
| 授权码模式（Authorization Code） | 带服务端后端的 Web 应用 |
| 授权码 + PKCE 模式（Authorization Code + PKCE） | 单页应用（SPA）和移动端应用 |
| 客户端凭据模式（Client Credentials） | 机器对机器（M2M）通信 |
| 设备码模式（Device Code） | 电视、CLI 工具 |

### API 密钥（API Keys）
- 使用简单，但默认不设过期时间
- 必须支持轮换，绝不能嵌入客户端代码中
- 适用于服务端对服务端通信，不适用于终端用户认证

---

## 加密（Encryption）

### 对称加密（Symmetric）与非对称加密（Asymmetric）的对比
| | 对称加密 | 非对称加密 |
|--|---------|-----------|
| 密钥 | 一个共享密钥 | 公钥 + 私钥对 |
| 速度 | 快 | 慢 |
| 用途 | 批量数据加密（AES） | 密钥交换、数字签名（RSA、EC） |
| 示例 | AES-256、ChaCha20 | RSA-2048、ECDSA |

### TLS 握手过程（简化版）
```
1. Client Hello (supported cipher suites)
2. Server Hello + Certificate
3. Client verifies certificate (via CA chain)
4. Key exchange → derive session keys
5. Encrypted communication begins
```

### 哈希（Hashing）
- 单向函数：`hash(data) → digest`
- **SHA-256/SHA-3** 用于数据完整性校验
- **bcrypt/Argon2** 用于密码哈希（设计上较慢，且带盐值）
- 切勿明文存储密码；密码哈希中绝不使用 MD5 或 SHA-1

---

## OWASP Top 10（2021 年版）

| 排名 | 漏洞类型 | 缓解措施 |
|------|---------|---------|
| A01 | 访问控制失效（Broken Access Control） | 默认拒绝，在服务端强制执行 |
| A02 | 加密机制失效（Cryptographic Failures） | 使用 TLS、强加密算法，禁用 MD5 |
| A03 | 注入攻击（Injection，含 SQL、NoSQL、OS） | 参数化查询、输入验证 |
| A04 | 不安全设计（Insecure Design） | 威胁建模、在软件开发生命周期（SDLC）中融入安全 |
| A05 | 安全配置错误（Security Misconfiguration） | 使用加固的默认配置，禁用未使用的功能 |
| A06 | 自身存在漏洞和过时的组件（Vulnerable Components） | 依赖扫描，定期打补丁 |
| A07 | 认证和验证机制失效（Auth Failures） | 多因素认证（MFA）、速率限制、安全的会话管理 |
| A08 | 软件和数据完整性故障（Data Integrity Failures） | CI/CD 完整性检查、使用签名软件包 |
| A09 | 安全日志记录和监控不足（Logging Failures） | 集中式日志记录与告警 |
| A10 | 服务端请求伪造（SSRF） | 对出站请求使用白名单，保护云元数据端点 |

---

## 常见攻击与防御措施

### SQL 注入（SQL Injection）
```sql
-- Vulnerable
SELECT * FROM users WHERE name = '" + userInput + "'

-- Safe: parameterized query
SELECT * FROM users WHERE name = ?
```

### XSS（跨站脚本攻击，Cross-Site Scripting）
- **存储型 XSS（Stored XSS）**：恶意脚本保存于数据库中，在其他用户访问时被执行
- **反射型 XSS（Reflected XSS）**：脚本包含在 URL 中，随响应反射回客户端执行
- 防御措施：对输出进行转义、设置 Content-Security-Policy 响应头、使用 HttpOnly Cookie

### CSRF（跨站请求伪造，Cross-Site Request Forgery）
- 攻击者诱使已认证用户提交恶意请求
- 防御措施：使用 CSRF 令牌、设置 Cookie 的 SameSite 属性、校验 Origin 请求头

### SSRF（服务端请求伪造，Server-Side Request Forgery）
- 攻击者使服务端向内部 URL 发起请求（例如 `http://169.254.169.254/` AWS 元数据地址）
- 防御措施：对出站目标使用白名单，屏蔽 RFC-1918 私有地址段

---

## 架构层面的安全设计

### 纵深防御（Defense in Depth）
- 多层防护：WAF → API 网关 → 应用层 → 数据库层
- 安全控制不存在单点故障

### 最小权限原则（Principle of Least Privilege）
- 服务/用户只获得其所需的最小权限
- 为每个服务配置独立的数据库凭据
- IAM 角色仅授予最小化的策略范围

### 零信任（Zero Trust）
- 永不信任，始终验证——即使是内部流量也不例外
- 微服务间使用 mTLS 双向认证
- 网络分段、服务网格（Service Mesh）

### 密钥管理（Secret Management）
- 切勿在代码或 Docker 镜像中硬编码密钥
- 使用 Vault、AWS Secrets Manager 或 GCP Secret Manager
- 定期轮换密钥

---

## 架构师核心要点

1. 认证应在网关层统一处理——不要在每个服务中重复实现。
2. 无状态 API 使用 JWT，但需提前规划令牌撤销方案。
3. 对静态数据和传输中的数据均进行加密——始终使用 TLS 1.2+。
4. 对所有查询使用参数化方式——注入攻击仍是排名第一的漏洞类别。
5. 每个服务账户和 IAM 角色都应遵循最小权限原则。
