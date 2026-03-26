# 容器与编排：Docker & Kubernetes

> 架构师视角：容器不只是打包工具，它是现代分布式系统的基础设施原语。理解容器的隔离机制、镜像分层模型、以及 Kubernetes 的调度哲学，才能在规模化场景下做出正确决策。

---

## 目录

1. [容器解决的问题](#1-容器解决的问题)
2. [Docker 核心概念](#2-docker-核心概念)
3. [Docker Compose](#3-docker-compose)
4. [Kubernetes 核心概念](#4-kubernetes-核心概念)
5. [Kubernetes 实战配置](#5-kubernetes-实战配置)
6. [容器安全](#6-容器安全)

---

## 1. 容器解决的问题

### 1.1 "在我机器上能运行"问题

这是软件开发史上最经典的抱怨。根本原因在于：**运行环境不一致**。

| 不一致的维度 | 典型问题 |
|---|---|
| 操作系统版本 | Ubuntu 20.04 vs CentOS 7，系统调用行为差异 |
| 运行时版本 | Python 3.8 vs Python 3.11，语法与标准库变化 |
| 依赖库版本 | `libssl` 版本不同导致 TLS 握手失败 |
| 环境变量 | 开发机有 `DATABASE_URL`，生产机没配 |
| 文件路径 | `/home/dev/data` 在 CI 环境不存在 |
| 内核参数 | `vm.max_map_count` 影响 Elasticsearch 启动 |

容器通过**将应用与其完整运行时环境打包在一起**，彻底消除这类问题。一个容器镜像包含：操作系统用户空间、运行时、依赖库、配置文件、应用代码。在任何支持容器运行时的机器上，行为完全一致。

### 1.2 VM vs Container 对比

虚拟机（VM）和容器都解决了隔离问题，但实现层次和代价截然不同。

| 对比维度 | 虚拟机（VM） | 容器（Container） |
|---|---|---|
| 隔离层次 | 硬件级（Hypervisor 虚拟化 CPU/内存/磁盘） | 操作系统级（共享宿主机内核） |
| 启动时间 | 分钟级（需启动完整 OS） | 秒级甚至毫秒级 |
| 内存开销 | 每个 VM 需要独立的 OS（通常 1-2GB+） | 仅应用进程本身的内存 |
| 磁盘占用 | 完整 OS 镜像（几 GB 到几十 GB） | 镜像分层共享（通常几百 MB） |
| 安全隔离 | 强（内核级隔离，逃逸难度极高） | 较弱（共享内核，容器逃逸风险存在） |
| 可移植性 | 较差（VM 镜像格式不统一） | 极强（OCI 标准，跨平台） |
| 资源密度 | 低（一台物理机跑几十个 VM） | 高（一台物理机跑数百个容器） |
| 适用场景 | 强隔离需求、异构 OS、有状态重型服务 | 微服务、CI/CD、无状态应用 |

**架构决策原则：**
- 需要运行不同内核（如 Windows 容器在 Linux 上）→ VM
- 需要极强安全隔离（金融、多租户 SaaS）→ VM 或 Kata Containers（轻量 VM + 容器接口）
- 需要高密度部署、快速弹性扩缩容 → 容器

### 1.3 容器 vs 进程：namespace + cgroup

容器本质上是**一组受限制的 Linux 进程**，不是一种新的虚拟化技术。它依赖两个 Linux 内核特性：

#### Linux Namespace（命名空间）——隔离"看到什么"

Namespace 让容器内的进程只能看到属于自己的资源视图：

| Namespace 类型 | 隔离内容 | 容器效果 |
|---|---|---|
| `pid` | 进程 ID 空间 | 容器内 PID 1 是应用进程，看不到宿主机其他进程 |
| `net` | 网络接口、路由表、防火墙规则 | 容器有独立 IP、独立端口空间 |
| `mnt` | 文件系统挂载点 | 容器有独立的根文件系统 |
| `uts` | 主机名和域名 | 容器可设置自己的 hostname |
| `ipc` | System V IPC、POSIX 消息队列 | 容器间 IPC 隔离 |
| `user` | 用户和组 ID | 容器内 root 映射到宿主机非特权用户 |
| `cgroup` | cgroup 根目录 | 容器看不到宿主机 cgroup 树 |

#### Linux cgroup（控制组）——限制"能用多少"

cgroup 对容器可使用的资源量进行硬性限制：

| 资源类型 | 限制效果 |
|---|---|
| CPU | 限制 CPU 使用时间比例（如最多用 1 个核心） |
| 内存 | 超出限制触发 OOM Killer，杀死容器进程 |
| 磁盘 I/O | 限制读写带宽和 IOPS |
| 网络带宽 | 配合 tc（traffic control）限速 |

```bash
# 查看某个容器的 cgroup 限制（Docker 实际创建的 cgroup）
cat /sys/fs/cgroup/memory/docker/<container_id>/memory.limit_in_bytes

# 查看容器使用的 namespace
ls -la /proc/<container_pid>/ns/
```

**关键理解：** 容器没有自己的内核。宿主机内核的漏洞对所有容器都有影响。这是容器安全的根本约束。

### Key Architect Takeaways

- 容器解决的是**环境一致性**问题，不是虚拟化问题。选择 VM 还是容器的核心标准是安全隔离需求和资源密度要求。
- Namespace 提供隔离视图，cgroup 提供资源配额，两者组合才构成"容器"的完整语义。
- 共享内核是容器的安全边界弱点。多租户场景下，需评估是否需要 gVisor、Kata Containers 等沙箱方案。
- 容器的毫秒级启动时间是 Serverless 和弹性伸缩的基础，这是 VM 无法提供的能力。

---

## 2. Docker 核心概念

### 2.1 镜像 vs 容器 vs 仓库

这三个概念的关系类似于**类、实例、代码仓库**：

| 概念 | 类比 | 特征 |
|---|---|---|
| 镜像（Image） | 类定义 / 程序安装包 | 只读，不可变，由多个层组成 |
| 容器（Container） | 类的实例 / 运行中的进程 | 可读写，有生命周期（running/stopped/exited） |
| 仓库（Registry） | GitHub / Maven Central | 存储和分发镜像，支持版本标签（tag） |

```bash
# 拉取镜像（从 Registry 到本地）
docker pull python:3.12-slim

# 从镜像创建并启动容器
docker run -d --name my-app -p 8000:8000 my-python-app:latest

# 列出本地镜像
docker images

# 列出运行中的容器
docker ps

# 推送镜像到 Registry
docker push myregistry.io/myapp:v1.2.3
```

**常见 Registry：**
- Docker Hub：公共默认仓库
- AWS ECR / GCP Artifact Registry / Azure ACR：云厂商托管仓库
- Harbor：企业自托管仓库，支持漏洞扫描、访问控制

### 2.2 分层文件系统（Union FS）

Docker 镜像的每一层对应一条 Dockerfile 指令的文件系统变更。层是**只读且可共享**的。

```
镜像层结构示例：

Layer 5: COPY . /app          ← 应用代码（变化最频繁）
Layer 4: RUN pip install ...   ← 安装依赖（变化较少）
Layer 3: COPY requirements.txt ← 依赖声明
Layer 2: RUN apt-get install   ← 系统包
Layer 1: FROM python:3.12-slim ← 基础镜像（被所有 Python 应用共享）
```

**共享层带来的优势：**

1. **构建缓存**：若某层内容未变化，Docker 直接复用缓存，跳过重新构建
2. **存储节省**：多个基于相同基础镜像的容器共享底层，磁盘占用大幅减少
3. **传输加速**：推拉镜像时只传输有变化的层

**层缓存失效的传播规则：** 某一层缓存失效，其上所有层均需重建。

```dockerfile
# 反例：缓存利用率极差
COPY . /app                    # 代码一改，下面全部重建
RUN pip install -r requirements.txt

# 正例：将稳定的依赖安装放在代码复制之前
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt  # 只有 requirements.txt 变化才重建
COPY . /app                               # 代码变化只影响这一层
```

### 2.3 多阶段构建（Multi-stage Build）

生产镜像应该尽可能小：减少攻击面、加快拉取速度、降低存储成本。多阶段构建允许在构建过程中使用完整工具链，但最终镜像只包含运行所需的最小文件集。

**Java Spring Boot 多阶段构建示例：**

```dockerfile
# ===== 阶段一：构建阶段（使用完整 JDK + Maven）=====
FROM maven:3.9-eclipse-temurin-21 AS builder

WORKDIR /build

# 先复制依赖声明，利用层缓存
COPY pom.xml .
RUN mvn dependency:go-offline -B

# 再复制源码并构建
COPY src ./src
RUN mvn package -DskipTests -B

# 提取 Spring Boot 分层 JAR（进一步优化容器层）
RUN java -Djarmode=layertools -jar target/*.jar extract --destination /build/extracted

# ===== 阶段二：运行阶段（只使用 JRE，不含 JDK/Maven）=====
FROM eclipse-temurin:21-jre-jammy AS runtime

# 安全：创建非 root 用户
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --no-create-home appuser

WORKDIR /app

# 按变化频率从低到高复制分层内容（充分利用层缓存）
COPY --from=builder --chown=appuser:appgroup /build/extracted/dependencies/ ./
COPY --from=builder --chown=appuser:appgroup /build/extracted/spring-boot-loader/ ./
COPY --from=builder --chown=appuser:appgroup /build/extracted/snapshot-dependencies/ ./
COPY --from=builder --chown=appuser:appgroup /build/extracted/application/ ./

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/actuator/health || exit 1

EXPOSE 8080

ENTRYPOINT ["java", \
    "-XX:MaxRAMPercentage=75.0", \
    "-XX:+UseContainerSupport", \
    "org.springframework.boot.loader.launch.JarLauncher"]
```

**对比效果：**

| | 单阶段构建 | 多阶段构建 |
|---|---|---|
| 最终镜像大小 | ~800MB（含 JDK + Maven） | ~250MB（仅 JRE） |
| 攻击面 | 大（含编译工具） | 小 |
| 构建速度 | 慢（每次重下依赖） | 快（层缓存） |

### 2.4 Dockerfile 最佳实践

#### .dockerignore 文件

`.dockerignore` 阻止不必要的文件进入构建上下文，避免缓存失效和镜像臃肿：

```
# .dockerignore
# 版本控制
.git
.gitignore

# Python 缓存
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/

# 虚拟环境（容器内会重新安装依赖）
venv/
.venv/
env/

# 测试与文档
tests/
docs/
*.md

# IDE 配置
.vscode/
.idea/
*.swp

# 本地开发配置（绝对不能进入镜像！）
.env
.env.local
*.env
docker-compose.override.yml

# 构建产物
dist/
build/
*.egg-info/

# 日志
*.log
logs/
```

#### 非 root 用户运行

```dockerfile
# 创建专用系统用户（无 home 目录，无 shell）
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup \
            --no-create-home --shell /bin/false appuser

# 设置文件所有权
COPY --chown=appuser:appgroup . /app

# 切换用户（此后所有指令及容器进程都以此用户身份运行）
USER appuser
```

### 2.5 完整 Python FastAPI 应用 Dockerfile 示例

```dockerfile
# Dockerfile（Python FastAPI 生产级配置）
# ===== 阶段一：依赖安装 =====
FROM python:3.12-slim AS dependency-builder

# 安装构建依赖（编译某些 C 扩展需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /install

# 先复制依赖文件（缓存优化关键步骤）
COPY requirements.txt .

# 安装到独立目录，便于复制到运行阶段
RUN pip install --no-cache-dir --prefix=/install/packages -r requirements.txt

# ===== 阶段二：运行阶段 =====
FROM python:3.12-slim AS runtime

# 只安装运行时必需的系统库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove

# 创建非 root 用户
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup \
            --no-create-home --shell /bin/false appuser

WORKDIR /app

# 从构建阶段复制已安装的依赖
COPY --from=dependency-builder /install/packages /usr/local

# 复制应用代码（放在最后，因为最频繁变化）
COPY --chown=appuser:appgroup ./src /app/src
COPY --chown=appuser:appgroup ./alembic /app/alembic
COPY --chown=appuser:appgroup alembic.ini /app/

# 切换非 root 用户
USER appuser

# 声明端口（文档用途，不实际发布）
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 使用 exec 形式（避免 shell 包装，信号能正确传递）
CMD ["uvicorn", "src.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--no-access-log"]
```

```
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.14.0
pydantic-settings==2.6.0
redis==5.2.0
aio-pika==9.4.3
httpx==0.28.0
```

### Key Architect Takeaways

- 层缓存是 Docker 构建性能的核心。**稳定的层放底部，易变的层放顶部**。`COPY requirements.txt` 必须先于 `COPY . .`，这一条规则能将构建时间从分钟级降到秒级。
- 多阶段构建是生产镜像的标准做法。构建工具（JDK、Maven、GCC）不应出现在运行时镜像中，这不仅减小体积，更重要的是**缩小攻击面**。
- `.dockerignore` 同等重要。`.git` 目录进入构建上下文会导致几百 MB 的无用传输，且任何代码变更都会使后续所有层缓存失效。
- `ENTRYPOINT`/`CMD` 使用 exec 形式（JSON 数组），确保 PID 1 是应用进程本身，使 `SIGTERM` 能正确传递实现优雅关闭。
- 非 root 用户运行是最低安全基线，任何理由都不能跳过这一要求。

---

## 3. Docker Compose

### 3.1 本地开发环境一键启动

Docker Compose 解决了本地开发环境的多服务协调问题。一个 `docker-compose.yml` 定义整个开发栈，任何新成员只需 `docker compose up` 即可获得与其他人完全一致的环境。

**Docker Compose vs Kubernetes 的边界：**

| 场景 | 推荐工具 |
|---|---|
| 本地开发、功能演示 | Docker Compose |
| 单机生产部署（小规模） | Docker Compose / Swarm |
| 多机生产部署、自动伸缩 | Kubernetes |
| CI/CD 集成测试 | Docker Compose（轻量、无需集群） |

### 3.2 ShopFlow 完整 docker-compose.yml 示例

以下是一个电商系统（ShopFlow）的完整本地开发环境配置，包含 FastAPI 后端、PostgreSQL、Redis 和 RabbitMQ：

```yaml
# docker-compose.yml
version: "3.9"

# ===== 网络配置 =====
networks:
  shopflow-net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

# ===== 数据卷配置（持久化存储）=====
volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local
  rabbitmq-data:
    driver: local

services:
  # ===== 基础设施服务 =====

  # PostgreSQL 数据库
  postgres:
    image: postgres:16-alpine
    container_name: shopflow-postgres
    restart: unless-stopped
    networks:
      - shopflow-net
    environment:
      POSTGRES_DB: shopflow
      POSTGRES_USER: shopflow_user
      # 生产环境使用 secrets，这里开发环境用环境变量
      POSTGRES_PASSWORD: shopflow_dev_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
      # 性能调优参数
      POSTGRES_HOST_AUTH_METHOD: scram-sha-256
    volumes:
      - postgres-data:/var/lib/postgresql/data
      # 初始化 SQL 脚本（按字母顺序执行）
      - ./infrastructure/postgres/init:/docker-entrypoint-initdb.d:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shopflow_user -d shopflow"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512m

  # Redis 缓存
  redis:
    image: redis:7.2-alpine
    container_name: shopflow-redis
    restart: unless-stopped
    networks:
      - shopflow-net
    command: >
      redis-server
      --requirepass redis_dev_password
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --appendfsync everysec
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "redis_dev_password", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s
    deploy:
      resources:
        limits:
          memory: 300m

  # RabbitMQ 消息队列
  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    container_name: shopflow-rabbitmq
    restart: unless-stopped
    networks:
      - shopflow-net
    environment:
      RABBITMQ_DEFAULT_USER: shopflow
      RABBITMQ_DEFAULT_PASS: rabbitmq_dev_password
      RABBITMQ_DEFAULT_VHOST: shopflow
      # 内存高水位（超过总内存 40% 开始限流）
      RABBITMQ_VM_MEMORY_HIGH_WATERMARK: 0.4
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
      - ./infrastructure/rabbitmq/definitions.json:/etc/rabbitmq/definitions.json:ro
    ports:
      - "5672:5672"    # AMQP 协议端口
      - "15672:15672"  # Management UI 端口
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 15s
      timeout: 10s
      retries: 5
      start_period: 60s
    deploy:
      resources:
        limits:
          memory: 512m

  # ===== 应用服务 =====

  # FastAPI 主后端服务
  api:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime   # 指定多阶段构建的目标阶段
      args:
        BUILD_ENV: development
    container_name: shopflow-api
    restart: unless-stopped
    networks:
      - shopflow-net
    # 依赖顺序 + 健康检查：只有依赖服务健康才启动
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    environment:
      # 数据库连接
      DATABASE_URL: "postgresql+asyncpg://shopflow_user:shopflow_dev_password@postgres:5432/shopflow"
      # Redis 连接
      REDIS_URL: "redis://:redis_dev_password@redis:6379/0"
      # RabbitMQ 连接
      RABBITMQ_URL: "amqp://shopflow:rabbitmq_dev_password@rabbitmq:5672/shopflow"
      # 应用配置
      APP_ENV: development
      LOG_LEVEL: debug
      SECRET_KEY: "dev-secret-key-change-in-production"
      ALLOWED_HOSTS: "localhost,127.0.0.1,api"
    volumes:
      # 开发模式：挂载源码实现热重载（生产环境不做此挂载）
      - ./src:/app/src:ro
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    deploy:
      resources:
        limits:
          memory: 512m

  # Celery 异步任务工作者
  worker:
    build:
      context: .
      dockerfile: Dockerfile
      target: runtime
    container_name: shopflow-worker
    restart: unless-stopped
    networks:
      - shopflow-net
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    environment:
      DATABASE_URL: "postgresql+asyncpg://shopflow_user:shopflow_dev_password@postgres:5432/shopflow"
      REDIS_URL: "redis://:redis_dev_password@redis:6379/0"
      RABBITMQ_URL: "amqp://shopflow:rabbitmq_dev_password@rabbitmq:5672/shopflow"
      APP_ENV: development
    volumes:
      - ./src:/app/src:ro
    command: ["celery", "-A", "src.worker.celery_app", "worker",
              "--loglevel=info", "--concurrency=4", "-Q", "default,emails,notifications"]
    deploy:
      resources:
        limits:
          memory: 256m

  # Nginx 反向代理（模拟生产环境网关行为）
  nginx:
    image: nginx:1.27-alpine
    container_name: shopflow-nginx
    restart: unless-stopped
    networks:
      - shopflow-net
    depends_on:
      api:
        condition: service_healthy
    volumes:
      - ./infrastructure/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./infrastructure/nginx/conf.d:/etc/nginx/conf.d:ro
    ports:
      - "80:80"
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 5s
      retries: 3
```

### 3.3 依赖顺序（depends_on + healthcheck）

`depends_on` 有两种模式，理解差别至关重要：

```yaml
# 模式一：只等待容器启动（不等待服务就绪）——通常不够用
depends_on:
  - postgres       # postgres 容器一 start 就认为"就绪"，实际 PG 可能还没初始化完

# 模式二：等待健康检查通过——生产推荐
depends_on:
  postgres:
    condition: service_healthy   # 等 postgres healthcheck 返回 healthy
  redis:
    condition: service_healthy
```

**服务启动顺序示意：**

```
postgres ──健康─→ redis ──健康─→ rabbitmq ──健康─→ api ──健康─→ worker
                                                              └→ nginx
```

**healthcheck 参数说明：**

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U myuser"]
  interval: 10s      # 每 10 秒检查一次
  timeout: 5s        # 单次检查超时时间
  retries: 5         # 连续失败 5 次才标记为 unhealthy
  start_period: 30s  # 容器启动后 30 秒内的失败不计入 retries（等待初始化）
```

### 3.4 数据卷（Volumes）持久化

```yaml
volumes:
  postgres-data:        # 命名卷：由 Docker 管理，跨容器重启持久化
    driver: local

# 三种挂载方式对比：
services:
  app:
    volumes:
      # 1. 命名卷（生产数据库、缓存推荐）
      - postgres-data:/var/lib/postgresql/data

      # 2. Bind Mount（开发热重载推荐）
      - ./src:/app/src:ro   # :ro 表示只读，防止容器修改宿主机代码

      # 3. 匿名卷（临时数据，容器删除后丢失）
      - /app/tmp
```

| 卷类型 | 适用场景 | 数据持久性 | 跨机器迁移 |
|---|---|---|---|
| 命名卷（Named Volume） | 数据库、缓存数据 | 容器删除后保留 | 需手动备份迁移 |
| Bind Mount | 开发环境代码热重载 | 宿主机文件系统 | 不可移植 |
| 匿名卷 | 临时缓存、构建产物 | 容器删除后丢失 | 不适用 |

### Key Architect Takeaways

- `depends_on` 不加 `condition: service_healthy` 几乎没有实际价值。应用启动时依赖服务未就绪是最常见的本地环境报错原因，务必配置 healthcheck。
- 开发环境用 Bind Mount 挂载代码（热重载），生产镜像代码必须内嵌（不做挂载）。这两种模式通过同一个 Dockerfile 的不同阶段或 compose override 实现，不应使用两套 Dockerfile。
- Docker Compose 是开发和测试工具，不适合生产多机部署。需要跨机器调度、自动故障恢复、滚动更新时，应迁移到 Kubernetes。
- 数据卷备份策略必须在设计阶段确定。命名卷的数据不会自动备份，需要配合 `pgdump`、Velero 等工具建立备份流程。

---

## 4. Kubernetes 核心概念

### 4.1 为什么需要 Kubernetes

Docker Compose 在以下场景开始力不从心：

| 需求 | Docker Compose | Kubernetes |
|---|---|---|
| 跨多台物理机部署 | 不支持（单机） | 原生支持（集群调度） |
| 自动故障转移 | 不支持（节点宕机服务消失） | 自动将 Pod 调度到健康节点 |
| 滚动更新 / 零停机部署 | 不支持 | 原生支持（RollingUpdate 策略） |
| 自动扩缩容（HPA） | 不支持 | 基于 CPU/内存/自定义指标自动扩缩 |
| 服务发现与负载均衡 | 基于 DNS，功能有限 | Service 提供稳定 VIP + 负载均衡 |
| 配置与密钥管理 | 环境变量，无版本管理 | ConfigMap + Secret，支持动态更新 |
| 资源配额与隔离 | 简单 deploy.resources | Namespace 级 ResourceQuota + LimitRange |
| 自愈能力 | 容器崩溃重启（单机） | Pod 重调度、节点替换 |

**何时从 Compose 迁移到 K8s 的信号：**
- 服务需要部署到 3 台以上节点
- 需要无停机滚动发布
- 服务流量出现显著的峰谷周期，需要自动扩缩容
- 团队超过 5 人，需要环境隔离（dev/staging/prod Namespace）

### 4.2 核心资源

#### Pod

Pod 是 Kubernetes 中最小的调度单元，是一个或多个紧密耦合容器的集合。

```
Pod
├── 容器 A（主应用）
├── 容器 B（Sidecar：日志代理）
└── 共享网络命名空间（同一 IP，不同端口）
   └── 共享存储卷
```

**Pod 的关键特性：**
- Pod 内所有容器共享 `localhost` 网络（端口不能冲突）
- Pod 是临时的（ephemeral）：节点宕机、资源不足、滚动更新都会导致 Pod 被删除重建
- Pod 重建后 IP 会变化，因此不应直接访问 Pod IP

#### Deployment

Deployment 是管理 Pod 的控制器，声明"期望状态"：

```
Deployment（期望：3 个副本）
└── ReplicaSet（确保 3 个 Pod 运行）
    ├── Pod-1
    ├── Pod-2
    └── Pod-3
```

**Deployment 提供的能力：**
- 声明式副本数管理（3 个副本，少了自动创建）
- 滚动更新（逐步用新 Pod 替换旧 Pod）
- 回滚（`kubectl rollout undo`）
- 历史版本记录

#### Service

Service 为一组 Pod 提供稳定的网络访问端点（虚拟 IP + DNS 名称），解决 Pod IP 动态变化问题。

| Service 类型 | 访问范围 | 典型用途 |
|---|---|---|
| `ClusterIP`（默认） | 仅集群内部 | 微服务间通信（如 API 调用数据库） |
| `NodePort` | 集群外，通过节点 IP + 端口 | 测试环境临时暴露服务 |
| `LoadBalancer` | 集群外，通过云厂商 LB | 生产环境暴露服务（AWS ELB 等） |
| `ExternalName` | 将服务名映射到外部 DNS | 访问集群外的外部服务 |

#### Ingress

Ingress 是 7 层（HTTP/HTTPS）路由规则，一个 LoadBalancer 后面路由多个服务：

```
外部流量
    ↓
LoadBalancer（L4，1个公网 IP）
    ↓
Ingress Controller（Nginx/Traefik）
    ↓ 根据 Host / Path 路由
    ├── api.shopflow.com → api-service:8000
    ├── shopflow.com/admin → admin-service:3000
    └── shopflow.com/ → frontend-service:80
```

#### ConfigMap & Secret

```
ConfigMap：存储非敏感配置（环境变量、配置文件）
Secret：存储敏感数据（密码、Token、证书），Base64 编码存储

注意：Secret 只是 Base64 编码，不是加密！
生产环境需配合 Sealed Secrets、Vault、AWS Secrets Manager 等工具加密存储。
```

### 4.3 Pod vs Deployment：为什么不直接用 Pod

```yaml
# 直接创建 Pod（几乎不应该这样做）
apiVersion: v1
kind: Pod
metadata:
  name: my-pod
spec:
  containers:
    - name: app
      image: my-app:v1

# 问题：
# 1. 节点宕机，Pod 不会自动在其他节点重建
# 2. 没有滚动更新能力
# 3. 不能声明副本数
# 4. 更新需要手动删除再创建
```

**何时直接用 Pod：**
- 临时调试（`kubectl run debug --image=busybox --rm -it -- sh`）
- 一次性任务（更适合用 Job 资源）

**何时用 Deployment：**
- 所有长期运行的无状态服务（99% 的情况）

**其他工作负载控制器：**

| 控制器 | 适用场景 |
|---|---|
| Deployment | 无状态服务（API、Web 服务） |
| StatefulSet | 有状态服务（数据库、消息队列），Pod 名称固定、存储持久化 |
| DaemonSet | 每个节点运行一个 Pod（日志代理、监控 Agent） |
| Job / CronJob | 一次性任务 / 定时任务 |

### 4.4 资源限制（requests/limits）：为什么必须设置

```yaml
resources:
  requests:           # 调度时的资源声明（K8s 据此选择节点）
    cpu: "250m"       # 0.25 核
    memory: "256Mi"
  limits:             # 运行时的资源上限（超出会被限制/杀死）
    cpu: "1000m"      # 1 核
    memory: "512Mi"
```

**不设置资源限制的后果：**

| 问题 | 场景 |
|---|---|
| 节点 OOM | 某个服务内存泄漏，耗尽节点内存，导致同节点所有 Pod 被驱逐 |
| CPU 饥饿 | 某个 CPU 密集型任务占满节点 CPU，其他服务响应延迟飙升 |
| 调度失败 | 没有 requests，K8s 无法判断 Pod 需要多少资源，可能过度调度到同一节点 |
| 成本失控 | 没有 limits，HPA 无法基于利用率百分比计算是否需要扩容 |

**CPU requests vs limits 的微妙之处：**
- CPU limits 超出：进程被 CPU throttle（变慢，不被杀死）
- Memory limits 超出：进程被 OOM Kill（直接杀死）
- 因此内存的 requests 和 limits 通常设置为相同值（Guaranteed QoS）

**QoS 等级与驱逐优先级：**

| QoS 等级 | 条件 | 资源紧张时优先被驱逐 |
|---|---|---|
| BestEffort | 没有设置任何 requests/limits | 最先被驱逐 |
| Burstable | 设置了 requests 但 limits > requests | 中等优先级 |
| Guaranteed | requests == limits | 最后被驱逐 |

### Key Architect Takeaways

- Pod 是临时的，永远不要在架构中假设 Pod IP 不变。Service 提供稳定端点，是服务发现的正确方式。
- 资源 requests/limits 是 Kubernetes 调度和稳定性的基础。没有设置限制的集群在流量高峰时会出现级联故障，这是生产事故的高频原因。
- StatefulSet 不是"更稳定的 Deployment"，它有专门的使用场景（有状态服务），滥用 StatefulSet 会带来不必要的运维复杂度。
- Secret 的 Base64 只是编码，不是加密。生产环境的密钥管理必须有额外的加密层（GitOps + Sealed Secrets，或外部密钥管理系统）。
- Ingress 将 7 层路由与 LoadBalancer 解耦，一个 LB 服务多个域名/路径，显著降低云资源成本。

---

## 5. Kubernetes 实战配置

### 5.1 Deployment YAML 示例（含 liveness/readiness probe）

```yaml
# shopflow-api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: shopflow-api
  namespace: shopflow-prod
  labels:
    app: shopflow-api
    version: v2.3.1
    team: backend
spec:
  # 副本数（HPA 启用后此字段由 HPA 管理）
  replicas: 3

  # Pod 选择器（必须与 template.metadata.labels 匹配）
  selector:
    matchLabels:
      app: shopflow-api

  # 滚动更新策略
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1           # 更新期间最多额外多出 1 个 Pod
      maxUnavailable: 0     # 更新期间不允许任何 Pod 不可用（零停机）

  template:
    metadata:
      labels:
        app: shopflow-api
        version: v2.3.1
      annotations:
        # Prometheus 指标采集注解
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"

    spec:
      # 优雅终止等待时间（确保请求处理完成）
      terminationGracePeriodSeconds: 60

      # 安全上下文（Pod 级别）
      securityContext:
        runAsNonRoot: true
        runAsUser: 1001
        runAsGroup: 1001
        fsGroup: 1001

      # 确保 Pod 分散到不同节点（避免单节点宕机影响所有副本）
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: shopflow-api
                topologyKey: kubernetes.io/hostname

      # 初始化容器（运行数据库迁移）
      initContainers:
        - name: db-migration
          image: shopflow-api:v2.3.1
          command: ["alembic", "upgrade", "head"]
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: shopflow-secrets
                  key: database-url
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "500m"
              memory: "256Mi"

      containers:
        - name: api
          image: shopflow-api:v2.3.1
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              protocol: TCP

          # 环境变量（从 ConfigMap 和 Secret 注入）
          env:
            - name: APP_ENV
              valueFrom:
                configMapKeyRef:
                  name: shopflow-config
                  key: app-env
            - name: LOG_LEVEL
              valueFrom:
                configMapKeyRef:
                  name: shopflow-config
                  key: log-level
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: shopflow-secrets
                  key: database-url
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: shopflow-secrets
                  key: redis-url
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  name: shopflow-secrets
                  key: secret-key
            # 注入 Pod 元信息（用于日志和追踪）
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace

          # 资源限制（必须设置）
          resources:
            requests:
              cpu: "250m"
              memory: "256Mi"
            limits:
              cpu: "1000m"
              memory: "512Mi"

          # Liveness Probe：检测应用是否"活着"
          # 失败则重启容器（用于检测死锁、无限循环等无法自恢复的状态）
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 30    # 容器启动后等待 30s 再开始检查
            periodSeconds: 15          # 每 15 秒检查一次
            timeoutSeconds: 5          # 单次检查超时
            failureThreshold: 3        # 连续失败 3 次才重启
            successThreshold: 1

          # Readiness Probe：检测应用是否"准备好接收流量"
          # 失败则从 Service 的端点列表移除（不重启容器）
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
            successThreshold: 1

          # Startup Probe：仅在容器启动阶段使用
          # 解决慢启动应用被 liveness probe 误杀的问题
          startupProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 30       # 最多等待 10*30=300 秒启动完成

          # 容器级安全上下文
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true    # 只读根文件系统
            capabilities:
              drop: ["ALL"]                  # 删除所有 Linux capabilities

          # 挂载点（只读根文件系统需要为临时目录设置 volume）
          volumeMounts:
            - name: tmp-dir
              mountPath: /tmp
            - name: app-config
              mountPath: /app/config
              readOnly: true

      volumes:
        - name: tmp-dir
          emptyDir: {}           # 临时目录，Pod 删除后清除
        - name: app-config
          configMap:
            name: shopflow-config
```

**三种 Probe 的核心区别：**

| Probe | 失败动作 | 检测目的 | 典型端点 |
|---|---|---|---|
| `livenessProbe` | 重启容器 | 应用是否存活（能响应） | `/health/live` |
| `readinessProbe` | 从 Service 摘除流量 | 应用是否就绪（依赖是否正常） | `/health/ready` |
| `startupProbe` | 重启容器（仅启动阶段） | 慢启动应用的启动保护 | 同 liveness |

```python
# FastAPI 健康检查端点示例
from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

app = FastAPI()

@app.get("/health/live")
async def liveness():
    """Liveness: 只检查应用进程本身是否能响应，不检查外部依赖"""
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness: 检查所有外部依赖是否就绪"""
    checks = {}
    overall_healthy = True

    # 检查数据库连接
    try:
        await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall_healthy = False

    # 检查 Redis 连接
    try:
        redis_client = await get_redis()
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        overall_healthy = False

    if not overall_healthy:
        raise HTTPException(status_code=503, detail=checks)

    return {"status": "ready", "checks": checks}
```

### 5.2 Service YAML 示例

```yaml
# shopflow-api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: shopflow-api-svc
  namespace: shopflow-prod
  labels:
    app: shopflow-api
spec:
  # ClusterIP：仅集群内部访问（Ingress 会通过此 Service 访问 Pod）
  type: ClusterIP
  selector:
    app: shopflow-api      # 匹配带此 label 的 Pod
  ports:
    - name: http
      protocol: TCP
      port: 80             # Service 暴露的端口
      targetPort: 8000     # 转发到 Pod 的端口
  # sessionAffinity: ClientIP  # 需要会话保持时启用（基于客户端 IP）
---
# PostgreSQL Service（Headless Service，用于 StatefulSet）
apiVersion: v1
kind: Service
metadata:
  name: shopflow-postgres-svc
  namespace: shopflow-prod
spec:
  clusterIP: None          # Headless Service：不分配 VIP，DNS 直接返回 Pod IP
  selector:
    app: shopflow-postgres
  ports:
    - port: 5432
      targetPort: 5432
```

### 5.3 Ingress YAML 示例

```yaml
# shopflow-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shopflow-ingress
  namespace: shopflow-prod
  annotations:
    # 使用 Nginx Ingress Controller
    kubernetes.io/ingress.class: "nginx"
    # TLS 证书自动申请（cert-manager）
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    # 限流（每个客户端 IP 每秒最多 100 个请求）
    nginx.ingress.kubernetes.io/limit-rps: "100"
    # 请求体大小限制
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    # 超时配置
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "10"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    # 启用 CORS
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://shopflow.com"

spec:
  tls:
    - hosts:
        - api.shopflow.com
        - shopflow.com
      secretName: shopflow-tls-cert    # cert-manager 会自动创建此 Secret

  rules:
    # API 子域名路由
    - host: api.shopflow.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: shopflow-api-svc
                port:
                  number: 80

    # 主域名路由（按路径区分前端和后台）
    - host: shopflow.com
      http:
        paths:
          - path: /admin
            pathType: Prefix
            backend:
              service:
                name: shopflow-admin-svc
                port:
                  number: 80
          - path: /
            pathType: Prefix
            backend:
              service:
                name: shopflow-frontend-svc
                port:
                  number: 80
```

### 5.4 ConfigMap & Secret

```yaml
# shopflow-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: shopflow-config
  namespace: shopflow-prod
data:
  app-env: "production"
  log-level: "info"
  # 也可以存整个配置文件
  app.yaml: |
    server:
      port: 8000
      workers: 4
    cache:
      ttl_seconds: 300
---
# shopflow-secret.yaml
# 注意：实际生产中不应将 Secret YAML 提交到 Git
# 应使用 Sealed Secrets、External Secrets Operator 或 Vault
apiVersion: v1
kind: Secret
metadata:
  name: shopflow-secrets
  namespace: shopflow-prod
type: Opaque
stringData:                       # stringData 会自动 Base64 编码
  database-url: "postgresql+asyncpg://user:pass@postgres:5432/shopflow"
  redis-url: "redis://:password@redis:6379/0"
  secret-key: "your-production-secret-key-here"
```

### 5.5 HPA（Horizontal Pod Autoscaler）：自动扩缩容

HPA 根据实时指标自动调整 Deployment 的副本数：

```yaml
# shopflow-api-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: shopflow-api-hpa
  namespace: shopflow-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: shopflow-api

  minReplicas: 3      # 最少副本数（即使流量为零也保持 3 个）
  maxReplicas: 20     # 最多副本数（防止失控扩容）

  metrics:
    # 基于 CPU 使用率扩缩容
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70    # CPU 使用率超过 70% 触发扩容

    # 基于内存使用率扩缩容
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80

    # 基于自定义指标（需要 Custom Metrics API）
    # 例如：基于请求队列长度扩缩容
    - type: External
      external:
        metric:
          name: rabbitmq_queue_messages_ready
          selector:
            matchLabels:
              queue: "order-processing"
        target:
          type: AverageValue
          averageValue: "100"       # 每个 Pod 平均处理 100 条消息

  # 扩缩容行为配置（防止频繁抖动）
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60     # 扩容冷却：60 秒内只扩容一次
      policies:
        - type: Percent
          value: 100                     # 每次最多翻倍扩容
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300    # 缩容冷却：5 分钟内不重复缩容
      policies:
        - type: Percent
          value: 25                      # 每次最多缩容 25%
          periodSeconds: 60
```

**HPA 工作原理：**

```
每 15 秒（默认）：
  当前副本数 × 当前指标值 / 目标指标值 = 期望副本数

示例：
  3 副本 × CPU 90% / CPU 70% = 3.86 → 向上取整 → 4 副本
  3 副本 × CPU 40% / CPU 70% = 1.71 → 向上取整 → 2 副本（但受缩容冷却限制）
```

**VPA（Vertical Pod Autoscaler）vs HPA：**

| 方案 | 扩展方式 | 适用场景 | 局限性 |
|---|---|---|---|
| HPA | 增加/减少 Pod 副本数（横向） | 无状态服务的流量弹性 | 需要应用是无状态的 |
| VPA | 调整单 Pod 的 CPU/内存 requests | 单体应用、有状态服务 | 需要重启 Pod 生效，不适合生产高可用 |
| Cluster Autoscaler | 增加/减少节点数 | 节点级资源不足 | 云环境，节点启动需要几分钟 |

### Key Architect Takeaways

- Liveness 和 Readiness probe 必须实现不同的逻辑。Readiness 应检查依赖（数据库、缓存）；Liveness 只检查进程本身。将依赖检查放在 Liveness 中，会导致依赖故障时整个应用被无限重启，产生雪崩。
- `maxUnavailable: 0` + `maxSurge: 1` 是零停机滚动更新的标准配置，但需要集群有足够的资源余量（至少能多运行 1 个 Pod）。
- HPA 的 `stabilizationWindowSeconds` 防止抖动。流量有规律的峰谷（如白天高、晚上低），缩容冷却需要设置得比一个波谷周期更长，否则会频繁扩缩容消耗资源。
- Secret 不是加密存储，这是 Kubernetes 最常被误解的安全点。生产环境必须用 Sealed Secrets（GitOps 安全）或 External Secrets Operator（连接 Vault/AWS SM）替代裸 Secret。
- PodAntiAffinity 是高可用的必要配置。不设置时，K8s 调度器可能将所有副本调度到同一节点，节点宕机造成全量故障。

---

## 6. 容器安全

容器安全是一个纵深防御体系，涵盖镜像构建、运行时配置和供应链安全。

### 6.1 不以 Root 运行

**风险：** 容器内 root 用户与宿主机 root 用户具有相同的权限（除非启用了 User Namespace）。容器逃逸后，攻击者直接获得宿主机 root 权限。

```dockerfile
# Dockerfile 中创建非 root 用户
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup \
            --no-create-home --shell /bin/false appuser

USER appuser
```

```yaml
# Kubernetes Pod 安全上下文强制非 root
spec:
  securityContext:
    runAsNonRoot: true        # K8s 级别强制：若镜像以 root 运行，拒绝启动 Pod
    runAsUser: 1001
    runAsGroup: 1001
    fsGroup: 1001             # 挂载卷的所有者 GID

  containers:
    - name: app
      securityContext:
        allowPrivilegeEscalation: false   # 禁止提权（setuid/setgid）
        runAsNonRoot: true
        capabilities:
          drop: ["ALL"]                    # 删除所有 Linux capabilities
          add: ["NET_BIND_SERVICE"]        # 仅在需要绑定 <1024 端口时添加
```

### 6.2 只读文件系统

只读根文件系统阻止攻击者在容器内写入恶意文件（Web Shell、持久化后门）：

```yaml
securityContext:
  readOnlyRootFilesystem: true    # 根文件系统只读

volumeMounts:
  # 应用真正需要写入的目录，用 emptyDir 挂载
  - name: tmp-volume
    mountPath: /tmp
  - name: logs-volume
    mountPath: /app/logs

volumes:
  - name: tmp-volume
    emptyDir:
      sizeLimit: 100Mi    # 限制临时目录大小，防止磁盘耗尽
  - name: logs-volume
    emptyDir:
      sizeLimit: 500Mi
```

**只读文件系统的前提：** 应用不能向 `/app`、`/usr`、`/etc` 等目录写入文件。需要在开发阶段识别所有写入路径并改造。

### 6.3 镜像漏洞扫描

镜像扫描检测基础镜像和应用依赖中的已知 CVE：

```bash
# 使用 Trivy 扫描本地镜像（推荐，开源）
trivy image shopflow-api:v2.3.1

# 扫描并设置严重性阈值（HIGH/CRITICAL 才失败）
trivy image --exit-code 1 --severity HIGH,CRITICAL shopflow-api:v2.3.1

# 扫描 Dockerfile（静态分析，构建前检查）
trivy config Dockerfile

# 示例输出：
# shopflow-api:v2.3.1 (ubuntu 22.04)
# ======================================
# Total: 5 (HIGH: 2, CRITICAL: 0, MEDIUM: 3)
#
# ┌────────────────┬─────────────────────┬──────────┬──────────────────────────┐
# │    Library     │    Vulnerability    │ Severity │         Status           │
# ├────────────────┼─────────────────────┼──────────┼──────────────────────────┤
# │ libssl3        │ CVE-2024-XXXXX      │ HIGH     │ fixed in 3.0.11-1ubuntu3 │
# └────────────────┴─────────────────────┴──────────┴──────────────────────────┘
```

**在 CI/CD 流水线中集成扫描：**

```yaml
# .github/workflows/build.yml 片段（GitHub Actions）
- name: Build Docker image
  run: docker build -t shopflow-api:${{ github.sha }} .

- name: Run Trivy vulnerability scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: "shopflow-api:${{ github.sha }}"
    format: "table"
    exit-code: "1"              # 发现漏洞时让 CI 失败
    ignore-unfixed: true        # 忽略尚无修复版本的漏洞
    severity: "CRITICAL,HIGH"

- name: Push to Registry (only if scan passed)
  run: docker push myregistry.io/shopflow-api:${{ github.sha }}
```

**常见镜像扫描工具：**

| 工具 | 特点 | 集成方式 |
|---|---|---|
| Trivy | 开源，速度快，覆盖广（OS + 语言包） | CI/CD、本地、Harbor 插件 |
| Snyk | SaaS，开发者友好，有免费层 | IDE 插件、CI/CD |
| Grype | Anchore 开源版，可嵌入私有化 | CI/CD |
| Clair | CoreOS 出品，适合自托管 Registry | Harbor 后端 |
| AWS ECR | AWS 原生，扫描推送到 ECR 的镜像 | ECR 托管服务 |

### 6.4 最小镜像（distroless / alpine）

镜像越小，攻击面越小：没有 shell、没有包管理器，攻击者即使进入容器也无处下手。

| 基础镜像 | 大小（参考） | Shell | 包管理器 | 适用场景 |
|---|---|---|---|---|
| `ubuntu:22.04` | ~77MB | bash | apt | 开发调试 |
| `debian:slim` | ~80MB | bash | apt | 通用生产 |
| `alpine:3.20` | ~7MB | sh | apk | 通用生产（musl libc） |
| `python:3.12-slim` | ~130MB | bash | apt（受限） | Python 应用 |
| `python:3.12-alpine` | ~50MB | sh | apk | Python 应用（需测试兼容性） |
| `gcr.io/distroless/python3` | ~52MB | 无 | 无 | Python 应用（最高安全性） |
| `gcr.io/distroless/java21` | ~220MB | 无 | 无 | Java 应用（最高安全性） |
| `scratch` | 0B | 无 | 无 | Go/Rust 静态二进制 |

**distroless 镜像的实际使用：**

```dockerfile
# Go 应用的极简镜像（从 scratch 开始）
FROM golang:1.23-alpine AS builder

WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o app ./cmd/server

# 最终镜像：零大小基础 + 单一二进制
FROM scratch
COPY --from=builder /build/app /app
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
USER 65534:65534    # nobody user
ENTRYPOINT ["/app"]
```

```dockerfile
# Python 使用 distroless（注意：调试时需要 --override）
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target /app/packages -r requirements.txt

FROM gcr.io/distroless/python3-debian12

WORKDIR /app
COPY --from=builder /app/packages /app/packages
COPY src/ /app/src/

ENV PYTHONPATH=/app/packages
USER nonroot:nonroot

CMD ["/app/src/main.py"]
```

**Alpine vs Distroless 的选择：**

| 需求 | Alpine | Distroless |
|---|---|---|
| 生产安全性 | 高 | 极高 |
| 调试能力 | 有 sh，可 exec 进入 | 无 shell，只能查看日志 |
| 兼容性 | musl libc 可能有兼容问题 | glibc，兼容性好 |
| 镜像大小 | 小 | 同样小，有时更小 |
| 推荐场景 | 大多数生产应用 | 安全要求极高的服务 |

### 6.5 Pod Security Standards（PSS）

Kubernetes 1.25+ 内置的 Pod 安全准入控制：

```yaml
# 在 Namespace 上设置安全策略级别
apiVersion: v1
kind: Namespace
metadata:
  name: shopflow-prod
  labels:
    # 三个级别：privileged（无限制）、baseline（基础）、restricted（严格）
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.28
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

`restricted` 级别要求：
- 不允许特权容器
- 不允许 hostPath 挂载
- 必须以非 root 用户运行
- 不允许 `allowPrivilegeEscalation: true`
- 必须删除所有 capabilities（或仅保留允许列表中的）
- 根文件系统必须为只读（或显式声明）

### 6.6 容器安全最佳实践清单

```
镜像构建阶段：
□ 使用最小基础镜像（alpine/distroless/slim）
□ 多阶段构建，运行镜像不含构建工具
□ 在 CI/CD 中运行镜像漏洞扫描（Trivy）
□ 镜像 tag 使用 digest（SHA256）而非 latest
□ 锁定基础镜像版本（FROM python:3.12.7-slim，不用 FROM python:3）
□ .dockerignore 过滤 .env、.git、credentials

运行时配置：
□ runAsNonRoot: true（K8s 级别强制）
□ readOnlyRootFilesystem: true
□ allowPrivilegeEscalation: false
□ capabilities.drop: ["ALL"]
□ 设置 resources.requests 和 resources.limits
□ 使用 Pod Security Standards（restricted 级别）

供应链安全：
□ 私有 Registry（不使用公共 Hub 镜像，或扫描后使用）
□ 镜像签名验证（Cosign + Sigstore）
□ SBOM（软件物料清单）生成
□ 依赖项定期更新（Dependabot/Renovate Bot）
```

### Key Architect Takeaways

- 容器安全是纵深防御，没有银弹。非 root 运行 + 只读文件系统 + 漏洞扫描 + 最小镜像，这四者缺一不可，组合使用才能显著提升安全基线。
- `latest` 标签是生产环境的定时炸弹。基础镜像 `FROM python:3` 在某次 CI 构建时可能拉取了有漏洞的新版本。必须使用精确版本（`python:3.12.7-slim`）或 digest（`python@sha256:abc...`）。
- 镜像扫描必须卡 CI 门禁。发现高危漏洞允许部署上线，等于扫描形同虚设。但要注意处理"unfixed"漏洞的豁免机制，避免误报阻塞发布流程。
- distroless 镜像虽然安全性最高，但无 shell 的特性会显著增加故障排查难度。建议为调试场景准备一套 debug 版镜像（基于相同代码，但使用带 shell 的基础镜像），不发布生产，仅用于紧急排查。
- Kubernetes Secret 的加密问题不是 Secret 本身能解决的。需要在架构层面选择：GitOps + Sealed Secrets（私钥集中管理），或外部密钥管理系统（Vault、AWS Secrets Manager），并在 etcd 层面启用 encryption at rest。

---

## 总结：架构师决策框架

```
你的服务需要容器化吗？
└─→ 是的，除非是纯 Serverless（Lambda/Cloud Functions）

本地开发环境：Docker Compose
└─→ 一键启动所有依赖，环境一致性，不需要集群

单机小规模生产：Docker Compose / Docker Swarm
└─→ 月活 < 10万，团队 < 5人，无需自动扩缩容

多机生产 / 需要弹性：Kubernetes
└─→ 跨节点调度、自动故障恢复、HPA、多团队协作

镜像策略：
└─→ 开发：-slim 或 -alpine（可调试）
    └─→ 生产：-slim / alpine / distroless（安全优先）
        └─→ 极高安全要求：distroless + 只读文件系统 + 非 root

K8s 组件选择：
└─→ 无状态服务 → Deployment + HPA
    └─→ 有状态服务（DB）→ StatefulSet（或直接用托管云服务，强烈推荐）
        └─→ 每节点守护进程 → DaemonSet
            └─→ 定时任务 → CronJob
```

**核心原则：** 容器解决的是"环境"问题，Kubernetes 解决的是"编排"问题。不要因为技术先进就过早引入 Kubernetes——一个 3 人团队用 Docker Compose 跑 Compose 服务，比折腾 K8s 集群更能聚焦业务价值。但当规模和复杂度达到临界点时，Kubernetes 的能力是不可替代的。
