# 结构型模式（Structural Patterns）

结构型模式关注类与对象如何组合，以构成更大的结构。

---

## 1. 适配器模式（Adapter）

### 意图
将一个类的接口转换成客户端所期望的另一种接口，使原本因接口不兼容而无法协作的类能够一起工作。

### 适用场景
- 集成遗留代码或第三方库，但接口不兼容
- 想复用某个已有类，但其接口与需求不匹配

### 结构
```
Client → Target（接口）← Adapter → Adaptee
```

### 伪代码
```python
class LegacyPrinter:
    def print_old_way(self, text): ...

class PrinterAdapter:
    def __init__(self, legacy):
        self.legacy = legacy
    def print(self, text):  # new interface
        self.legacy.print_old_way(text)
```

### 实际案例
- ORM 适配数据库驱动（psycopg2 → SQLAlchemy）
- 支付网关适配器（Stripe/PayPal 统一在同一接口后面）

---

## 2. 装饰器模式（Decorator）

### 意图
动态地为对象附加额外的职责。装饰器提供了比继承更灵活的功能扩展方式。

### 适用场景
- 在不影响其他对象的情况下，为单个对象添加行为
- 行为可以在运行时动态添加和移除
- 通过子类扩展会导致类的数量爆炸式增长

### 结构
```
Component（接口）
├── ConcreteComponent
└── Decorator（包装 Component）
    ├── LoggingDecorator
    ├── CachingDecorator
    └── AuthDecorator
```

### 伪代码
```python
class DataService:
    def fetch(self, id): return db.get(id)

class CachingDecorator:
    def __init__(self, service):
        self.service = service
        self.cache = {}
    def fetch(self, id):
        if id not in self.cache:
            self.cache[id] = self.service.fetch(id)
        return self.cache[id]
```

### 实际案例
- HTTP 中间件调用栈（认证 → 日志 → 限流 → 处理器）
- Python 的 `@functools.lru_cache`、`@property`

---

## 3. 外观模式（Facade）

### 意图
为复杂子系统提供一个简化的统一接口。

### 适用场景
- 简化复杂库或一组 API 的使用方式
- 对子系统进行分层——上层通过外观调用下层
- 减少对复杂子系统内部实现的依赖

### 结构
```
Client → Facade → SubsystemA
                → SubsystemB
                → SubsystemC
```

### 伪代码
```python
class OrderFacade:
    def place_order(self, cart, user):
        inventory.check(cart)
        payment.charge(user, cart.total)
        shipping.schedule(user.address)
        notification.send(user, "Order confirmed")
```

### 实际案例
- API 网关隐藏微服务的复杂性
- SDK 封装复杂的 REST API

---

## 4. 代理模式（Proxy）

### 意图
为另一个对象提供一个代理或占位符，以控制对该对象的访问。

### 类型
| 类型 | 用途 |
|------|------|
| 虚拟代理（Virtual Proxy） | 延迟初始化——推迟开销大的对象的创建 |
| 保护代理（Protection Proxy） | 访问控制 |
| 远程代理（Remote Proxy） | 远程对象的本地代表（RPC 存根） |
| 缓存代理（Caching Proxy） | 缓存开销大的操作结果 |

### 伪代码
```python
class ImageProxy:
    def __init__(self, path):
        self.path = path
        self._image = None
    def display(self):
        if not self._image:
            self._image = RealImage(self.path)  # load only when needed
        self._image.display()
```

### 实际案例
- 服务网格边车代理（Envoy、Linkerd）
- ORM 懒加载关联关系
- API 网关作为反向代理

---

## 5. 组合模式（Composite）

### 意图
将对象组合成树形结构以表示"部分-整体"层次关系，使客户端可以统一对待单个对象与组合对象。

### 适用场景
- 树形结构：文件系统、UI 组件树、组织架构图
- 希望客户端无需区分叶子节点与组合节点

### 伪代码
```python
class Component:
    def render(self): ...

class Leaf(Component):
    def render(self): print(self.text)

class Container(Component):
    def __init__(self):
        self.children = []
    def add(self, c): self.children.append(c)
    def render(self):
        for c in self.children: c.render()
```

### 实际案例
- React 组件树
- HTML DOM
- 文件系统（文件与目录）

---

## 6. 桥接模式（Bridge）

### 意图
将抽象部分与实现部分解耦，使二者可以独立变化。

### 适用场景
- 避免抽象与实现之间产生永久绑定
- 抽象和实现都应该可以通过子类独立扩展

### 伪代码
```python
class Notification:
    def __init__(self, sender):  # sender is the "bridge"
        self.sender = sender
    def send(self, msg): self.sender.deliver(msg)

class EmailSender:
    def deliver(self, msg): ...

class SMSSender:
    def deliver(self, msg): ...
```

### 实际案例
- 支持多渠道的通知系统
- 数据库驱动（抽象层：ORM，实现层：具体数据库）

---

## 架构师核心要点

1. **适配器模式**：当无法修改已有代码但需要互通时使用。
2. **装饰器模式**：用于可组合的中间件管道——HTTP、日志、认证。
3. **外观模式**：用于服务边界——在整洁的 API 背后隐藏复杂性。
4. **代理模式**：用于横切关注点：缓存、认证、熔断。
5. **组合模式**：在领域模型中需要建模树形结构时使用。
