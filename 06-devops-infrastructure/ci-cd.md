# CI/CD：持续集成与持续交付

CI/CD 不是工具，而是一种工程实践。它的核心价值是：**缩小批次大小，快速获得反馈，降低发布风险**。从每周发布一次到每天发布数十次，CI/CD 是这种转变的技术基础。

---

## 1. 核心概念辨析

| 概念 | 全称 | 含义 | 关键区别 |
|------|------|------|---------|
| CI | Continuous Integration | 持续集成：代码频繁合并到主干，自动化测试验证 | 代码合并频率和测试自动化 |
| CD（交付） | Continuous Delivery | 持续交付：每次合并后自动构建可部署的产物，但手动触发生产部署 | 有人工审批才能上线 |
| CD（部署） | Continuous Deployment | 持续部署：所有通过测试的代码自动部署到生产 | 全自动，无人工干预 |

```
持续集成（CI）：
    commit → 自动测试 → 通过 → 合并到主干

持续交付（CD-Delivery）：
    commit → 自动测试 → 通过 → 构建镜像 → 部署到 Staging ─[人工批准]→ 部署到 Production

持续部署（CD-Deployment）：
    commit → 自动测试 → 通过 → 构建镜像 → 部署到 Staging → 自动测试 → 自动部署到 Production
```

### 何时选择哪种

| 场景 | 推荐 |
|------|------|
| 初创公司，快速迭代 | 持续部署（最快） |
| 有合规要求（金融、医疗） | 持续交付（需要人工审批） |
| B2B 产品，客户敏感 | 持续交付 + 功能开关 |
| 内部工具 | 持续部署 |

---

## 2. 流水线各阶段

```
代码提交
    │
    ▼
[1. 代码检查]（< 2分钟）
    └── lint: ruff/flake8
    └── 类型检查: mypy
    └── 安全扫描: bandit/semgrep
    │
    ▼
[2. 单元测试]（< 5分钟）
    └── pytest with coverage
    └── 覆盖率门槛检查（< 80% 失败）
    │
    ▼
[3. 构建]（< 3分钟）
    └── docker build（多阶段）
    └── 推送到 Container Registry
    │
    ▼
[4. 集成测试]（< 10分钟）
    └── 启动依赖（PostgreSQL, Redis）
    └── 运行集成测试
    │
    ▼
[5. 部署到 Staging]（< 5分钟）
    └── kubectl apply / helm upgrade
    └── 等待 Pod 就绪
    │
    ▼
[6. E2E 测试]（< 15分钟）
    └── Playwright / Selenium
    └── 核心用户流程验证
    │
    ▼
[7. 部署到 Production]（手动批准 或 自动）
    └── 蓝绿/金丝雀发布
    └── 监控关键指标
    └── 自动回滚条件检查
```

> **快速反馈原则：** 流水线越靠前的阶段越应该快。代码检查应该 < 1分钟，单元测试 < 5分钟——开发者等待时间越短，反馈循环越快。把慢测试放到后面。

---

## 3. GitHub Actions 实战

### 3.1 完整的 Python/FastAPI 流水线

```yaml
# .github/workflows/ci-cd.yml
name: ShopFlow CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/order-service
  PYTHON_VERSION: "3.12"

jobs:
  # ============================================================
  # Job 1: 代码质量检查（并行运行，快速失败）
  # ============================================================
  lint-and-type-check:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'  # 缓存依赖，加速后续运行

      - name: Install linting tools
        run: pip install ruff mypy

      - name: Run ruff (linting + formatting check)
        run: ruff check . && ruff format --check .

      - name: Run mypy (type checking)
        run: mypy shop/ --ignore-missing-imports

  # ============================================================
  # Job 2: 单元测试（多 Python 版本矩阵测试）
  # ============================================================
  unit-tests:
    name: Unit Tests (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]  # 同时测试两个版本
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests with coverage
        run: |
          pytest tests/unit/ \
            --cov=shop \
            --cov-report=xml \
            --cov-fail-under=80 \
            -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml
          token: ${{ secrets.CODECOV_TOKEN }}

  # ============================================================
  # Job 3: 集成测试（需要真实的数据库和 Redis）
  # ============================================================
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [lint-and-type-check, unit-tests]  # 等待前置 Job 完成

    services:  # GitHub Actions 内置服务容器
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: shopflow_test
          POSTGRES_USER: shopflow
          POSTGRES_PASSWORD: testpassword
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install dependencies
        run: pip install -r requirements.txt pytest pytest-asyncio

      - name: Run database migrations
        env:
          DATABASE_URL: postgresql://shopflow:testpassword@localhost:5432/shopflow_test
        run: python -m alembic upgrade head

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://shopflow:testpassword@localhost:5432/shopflow_test
          REDIS_URL: redis://localhost:6379/0
        run: pytest tests/integration/ -v

  # ============================================================
  # Job 4: 构建并推送 Docker 镜像
  # ============================================================
  build-and-push:
    name: Build & Push Docker Image
    runs-on: ubuntu-latest
    needs: [integration-tests]
    # 只有推送到 main 分支时才构建和推送
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'

    permissions:
      contents: read
      packages: write

    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
      image-digest: ${{ steps.build.outputs.digest }}

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata (tags, labels)
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix={{branch}}-  # main-abc1234
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          # 缓存构建层（大幅加速重复构建）
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ============================================================
  # Job 5: 部署到 Staging
  # ============================================================
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [build-and-push]
    environment: staging  # 需要在 GitHub 仓库设置中配置此环境

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to Kubernetes (Staging)
        env:
          KUBECONFIG: ${{ secrets.STAGING_KUBECONFIG }}
          IMAGE_TAG: ${{ needs.build-and-push.outputs.image-tag }}
        run: |
          kubectl set image deployment/order-service \
            order-service=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }} \
            -n shopflow-staging
          kubectl rollout status deployment/order-service -n shopflow-staging --timeout=5m

      - name: Run smoke tests on Staging
        run: |
          pytest tests/smoke/ \
            --base-url=https://staging.shopflow.com \
            -v

  # ============================================================
  # Job 6: 部署到 Production（需要人工批准）
  # ============================================================
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [deploy-staging]
    environment: production  # 在 GitHub 中配置：需要指定 Reviewer 批准才能继续

    steps:
      - name: Deploy to Production (Blue-Green)
        env:
          KUBECONFIG: ${{ secrets.PROD_KUBECONFIG }}
        run: |
          # 金丝雀部署：先把 10% 流量切到新版本
          kubectl apply -f k8s/canary-deployment.yaml
          echo "Canary deployed. Monitoring for 5 minutes..."
          sleep 300  # 等待5分钟，观察新版本的错误率
          # 如果没有人工取消，完成全量部署
          kubectl apply -f k8s/production-deployment.yaml
          kubectl rollout status deployment/order-service -n shopflow-prod --timeout=10m
```

---

## 4. 部署策略

### 4.1 滚动更新（Rolling Update）— Kubernetes 默认

```yaml
# Kubernetes Deployment 滚动更新配置
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 2        # 最多额外启动2个新 Pod
      maxUnavailable: 1  # 最多同时停止1个旧 Pod
```

```
更新过程：
旧版本（10个Pod）→ 停1个旧 + 启2个新 → 停1个旧 + 启1个新 → ... → 新版本（10个Pod）
特点：流量一直在，但同时有新旧版本并存（需要向后兼容）
```

### 4.2 蓝绿部署（Blue-Green）

```
同时维护两套完全相同的环境（蓝=当前生产，绿=新版本）

流量: 100% → 蓝环境
部署新版本到绿环境 → 测试绿环境
流量切换: 100% → 绿环境（通过负载均衡器，瞬间完成）
保留蓝环境（快速回滚：把流量切回蓝环境）

优点：零停机，回滚瞬间（改一下负载均衡器配置）
缺点：资源成本翻倍，数据库迁移复杂
```

### 4.3 金丝雀发布（Canary Release）

```
流量分配：
    旧版本 ←── 90% 流量
    新版本 ←── 10% 流量（金丝雀）

观察关键指标（15分钟）：
    错误率变化？延迟变化？
    ✅ 正常 → 逐步增加新版本流量（10% → 25% → 50% → 100%）
    ❌ 异常 → 立即把 10% 流量切回旧版本，损失最小
```

```yaml
# Kubernetes + Nginx Ingress 金丝雀配置
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: order-service-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"  # 10% 流量到新版本
spec:
  rules:
    - host: api.shopflow.com
      http:
        paths:
          - path: /v1/orders
            pathType: Prefix
            backend:
              service:
                name: order-service-v2  # 新版本
                port:
                  number: 80
```

### 4.4 部署策略对比

| 策略 | 停机时间 | 资源成本 | 回滚速度 | 风险 | 适用场景 |
|------|---------|---------|---------|------|---------|
| 滚动更新 | 无 | 低（略高于正常） | 慢（再次滚动） | 新旧版本并存 | 大多数场景 |
| 蓝绿部署 | 无 | 高（2倍资源） | 极快（秒级） | 数据库迁移 | 重大版本，需要快速回滚 |
| 金丝雀发布 | 无 | 低 | 快（减少权重） | 最低（影响范围小） | 高风险功能，大流量系统 |
| 功能开关 | 无 | 无 | 极快（改配置） | 功能代码积累 | 功能逐步灰度 |

---

## 5. 回滚策略

### 5.1 快速回滚的设计原则

```
1. 镜像标签用 Git SHA（不用 latest）
   order-service:main-abc1234  ← 可以随时回到这个版本
   order-service:latest        ← 危险！不知道是哪个版本

2. 保留多个历史版本的镜像（Registry 保留策略）
   Registry 策略：保留最近20个版本的镜像

3. Kubernetes 保留历史 Revision
   kubectl rollout undo deployment/order-service          # 回滚到上一版本
   kubectl rollout undo deployment/order-service --to-revision=3  # 回滚到指定版本
```

### 5.2 数据库迁移的向后兼容

数据库迁移是回滚的最大障碍。原则：**每次迁移必须向后兼容（旧版本代码能在新 Schema 上运行）**

```python
# 错误做法：直接重命名列（旧代码会崩溃）
# ALTER TABLE products RENAME COLUMN name TO title;

# 正确做法：扩展-迁移-收缩（Expand-Migrate-Contract）
# Step 1（版本N）: 添加新列（旧代码忽略它，新代码写两列）
# ALTER TABLE products ADD COLUMN title VARCHAR(200);

# Step 2（版本N，数据迁移）: 后台任务把 name 的值复制到 title
# UPDATE products SET title = name WHERE title IS NULL;

# Step 3（版本N+1）: 新代码只用 title，旧列标记为废弃

# Step 4（版本N+2）: 删除旧列（此时旧版本代码已全部下线）
# ALTER TABLE products DROP COLUMN name;
```

---

## 6. 测试金字塔

```
              /\
             /  \
            / E2E \          少量（< 10%）：慢、脆、昂贵
           /  测试  \         但验证了用户真实路径
          /──────────\
         /  集成测试   \      中量（约 20%）：需要启动依赖
        /              \     验证组件间的协作
       /────────────────\
      /   单元测试         \  大量（> 70%）：快、稳、廉价
     /  （领域逻辑为主）    \  验证单个函数/类的行为
    /────────────────────────\
```

| 层次 | 速度 | 覆盖面 | 维护成本 | 推荐比例 |
|------|------|--------|---------|---------|
| 单元测试 | 毫秒 | 函数/类 | 低 | 70%+ |
| 集成测试 | 秒 | 服务+DB+缓存 | 中 | 20% |
| E2E 测试 | 分钟 | 完整用户流程 | 高 | 10% |

---

## Key Architect Takeaways

- **CI/CD 的核心价值是缩小批次大小**：每次合并少量代码比积累大量变更后统一发布风险低得多——小批次意味着小范围的问题
- **流水线要快速失败**：代码检查放第一步（< 2分钟），慢速测试放最后。工程师不应该等待 20 分钟才知道代码格式不对
- **金丝雀发布是高流量系统的标准发布方式**：把 10% 的流量暴露给新版本，在影响最小的情况下验证新代码的表现
- **数据库迁移是回滚的最大风险**：遵循"扩展-迁移-收缩"三步法，确保每个版本的代码都能在新旧 Schema 上运行
- **把 GitHub Actions 的每个 Job 视为独立单元**：并行运行互相独立的 Job（lint、type-check），串行运行有依赖的 Job（构建等待测试通过）——这直接影响流水线总时长
