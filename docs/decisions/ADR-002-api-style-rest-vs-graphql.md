# ADR-002: 选择 REST API 风格（而非 GraphQL 或 gRPC）

**状态：** 已批准
**日期：** 2026-03-26
**决策者：** ShopFlow 开发团队

---

## 背景（Context）

Sprint 2 需要为 ShopFlow 设计 HTTP API，暴露给 Web 前端和移动端。

当前约束：
- 团队规模：1-3 人
- 前端需求：商品浏览、购物车、订单管理，字段需求相对固定
- 团队技术栈：Python（FastAPI），前端未定（可能是 React 或 Vue）
- 项目阶段：MVP，快速迭代优先

可选方案：
1. REST API（基于 HTTP 方法 + 资源 URL）
2. GraphQL（客户端自定义查询字段）
3. gRPC（基于 Protobuf 的 RPC）

---

## 决策（Decision）

选择 **REST API**，使用 FastAPI 实现，遵循 RESTful 设计原则。

---

## 理由（Rationale）

### 选择 REST 的理由

1. **学习成本低**
   团队成员对 REST 熟悉，HTTP 方法（GET/POST/PUT/DELETE）语义清晰，无需额外学习曲线。

2. **前端数据需求不复杂**
   商品详情、订单列表等场景的字段需求相对固定，over-fetching（返回多余字段）问题不显著。

3. **HTTP 缓存天然支持**
   GET 请求可以直接利用 CDN 和浏览器缓存（`Cache-Control`、`ETag`），无需额外配置。

4. **工具链成熟**
   - Postman、curl、浏览器 DevTools 直接可用
   - FastAPI 自动生成 OpenAPI 文档（`/docs`），文档成本接近零
   - 前端 `fetch()` 或 `axios` 直接调用，无需额外库

5. **调试简单**
   HTTP 请求/响应可以直接在浏览器 Network 面板查看，错误排查直观。

---

### 否决 GraphQL 的理由

GraphQL 解决的核心问题是：
- **精确字段选择**：客户端只请求需要的字段，避免 over-fetching
- **多资源聚合**：一次请求获取多个关联资源（如：商品 + 评论 + 库存）

但在当前阶段：
- 前端字段需求固定，over-fetching 不是痛点（多传几个字段对移动端流量影响 < 1KB）
- 多资源聚合场景少（商品详情页可以用 REST 的 `/products/{id}?include=reviews` 实现）

引入 GraphQL 的代价：
- 需要定义 GraphQL Schema（`.graphql` 文件）
- 需要实现 Resolver（每个字段的数据获取逻辑）
- 需要处理 N+1 查询问题（引入 DataLoader）
- 前端需要学习 GraphQL 查询语法和 Apollo Client

**结论：** 当前阶段，GraphQL 的收益 < 成本。

---

### 否决 gRPC 的理由

gRPC 的优势：
- 性能高（Protobuf 二进制序列化，比 JSON 快）
- 强类型（`.proto` 文件定义接口）
- 支持双向流（适合实时通信）

但在当前场景：
- **浏览器不原生支持 gRPC**：需要 gRPC-Web 代理（Envoy），增加部署复杂度
- **团队无 Protobuf 经验**：需要学习 `.proto` 语法和代码生成工具
- **调试困难**：二进制协议无法直接在浏览器 DevTools 查看

**结论：** gRPC 适合微服务间通信（Sprint 10 会引入），不适合面向浏览器的 API。

---

## 后果（Consequences）

### 正面

- **快速上手**：团队可以立即开始开发，无需学习新协议
- **天然支持 HTTP 缓存**：商品列表、详情页可以直接用 CDN 加速
- **OpenAPI 文档自动生成**：FastAPI 的 `/docs` 提供交互式 API 文档

### 负面/代价

1. **移动端可能存在 over-fetching**
   - 问题：返回了前端不需要的字段（如：商品详情返回了 `created_at`，但移动端不显示）
   - 影响：每个请求多传几十字节，对 4G/5G 网络影响可忽略
   - 应对：如果成为问题，可以在特定端点添加 `fields` 参数（如：`GET /products/1?fields=id,name,price`）

2. **没有 GraphQL 的类型自查能力**
   - 问题：前端无法通过 Introspection 查询 API 支持哪些字段
   - 应对：OpenAPI 文档（`/docs`）提供了类似能力，前端可以查看 Schema

3. **多资源聚合需要多次请求**
   - 问题：获取"商品 + 评论 + 库存"需要 3 次 HTTP 请求
   - 应对：在需要时引入 BFF（Backend for Frontend）模式，或在单个端点返回聚合数据

---

## 迁移信号（When to Revisit）

以下情况出现时，应重新评估这个决策：

1. **移动端团队频繁反映带宽浪费、字段不匹配**
   → 考虑为移动端单独提供 GraphQL 端点（REST 和 GraphQL 可以共存）

2. **前端需要复杂数据组合查询**
   → 考虑 BFF（Backend for Frontend）模式：为前端提供定制化的聚合 API

3. **微服务间通信成为性能瓶颈**
   → 考虑在服务间引入 gRPC（Sprint 10），但面向浏览器的 API 仍保持 REST

---

## 参考资料

- FastAPI 官方文档：https://fastapi.tiangolo.com/
- RESTful API 设计最佳实践：`03-system-design/api-design.md`
- GraphQL vs REST 对比：https://www.apollographql.com/blog/graphql-vs-rest/
